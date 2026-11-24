"""Spec-driven automotive vehicle pipeline for UNDERWORLD (T-ART-04: VH_Sedan_01).

Generates an original late-1990s American full-size crime-drama sedan (~5.05 x 1.88 x 1.44 m,
zero real brands/badges) with:
  - VehicleBody3D-compatible hierarchy: Body, Hood, Trunk, Bumper_F, Bumper_R,
    hinged Door_FL/FR/RL/RR, separate wheel-center-origin Wheel_FL/FR/RL/RR
  - Authored wheel-arch-safe convex collision: UCX_VH_Sedan_01-convcolonly
  - Sockets: SOCKET_Seat_Driver, SOCKET_Seat_Passenger, SOCKET_Exit_Left, SOCKET_Exit_Right,
             SOCKET_Headlight_L/R, SOCKET_Taillight_L/R
  - Automotive PBR materials (clearcoat metallic paint, tinted glass, chrome, dark rubber tires,
    alloy rims, emissive headlight/taillight lenses, dark cabin interior)
  - Documented wheelbase, track width, and wheel radius stored on root extras -> manifest!
"""
import argparse
import json
import math
import os
import sys
import time

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
REPO_ROOT = os.path.abspath(os.path.join(TOOLS_DIR, ".."))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from underworld_pipeline.characters import pbr_textures as PBR  # noqa: E402


def _mat(name, base_rgba, roughness=0.4, metallic=0.0, coat=0.0, coat_rough=0.05, emit=0.0):
    m = bpy.data.materials.new(name)
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = base_rgba
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if coat > 0 and "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = coat_rough
    if emit > 0 and "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = base_rgba
        bsdf.inputs["Emission Strength"].default_value = emit
    return m


def _smart_uv(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    if not ob.data.uv_layers:
        ob.data.uv_layers.new(name="UVMap")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.015, correct_aspect=True, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode="OBJECT")


def _make_obj(bm, name, parent, mat, origin_world=(0, 0, 0), subsurf=0):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
    # Shift vertices into local space around origin_world
    ox, oy, oz = origin_world
    if abs(ox) + abs(oy) + abs(oz) > 1e-6:
        for v in bm.verts:
            v.co -= Vector((ox, oy, oz))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    ob.location = origin_world
    if mat is not None:
        ob.data.materials.append(mat)
    if subsurf > 0:
        s = ob.modifiers.new("Subsurf", "SUBSURF")
        s.levels = subsurf
        s.render_levels = subsurf
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier=s.name)
    _smart_uv(ob)
    return ob


def _add_box(bm, center, size, rot=(0, 0, 0), bevel=0.02, segs=2):
    m = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((size[0], size[1], size[2], 1.0))
    ret = bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    edges = list({e for v in ret["verts"] for e in v.link_edges})
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=segs, affect="EDGES", clamp_overlap=True)
    return ret["verts"]


def _build_wheel(name, parent, center, radius, width, mat_tire, mat_rim):
    """Build detailed multi-spoke alloy wheel + treaded rubber tire centered at exact wheel origin (0,0,0)."""
    bm = bmesh.new()
    # Tire torus/cylinder with beveled sidewalls
    n_seg = 28
    # Outer tire profile (x along axle, yz circle)
    profile = [
        (-width * 0.50, radius * 0.62),
        (-width * 0.52, radius * 0.88),
        (-width * 0.44, radius * 0.99),
        (-width * 0.20, radius * 1.00),
        (width * 0.20, radius * 1.00),
        (width * 0.44, radius * 0.99),
        (width * 0.52, radius * 0.88),
        (width * 0.50, radius * 0.62),
    ]
    rings = []
    for px, pr in profile:
        rings.append([bm.verts.new((px, math.cos(2 * math.pi * i / n_seg) * pr, math.sin(2 * math.pi * i / n_seg) * pr)) for i in range(n_seg)])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n_seg):
            j = (i + 1) % n_seg
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = 0
            f.smooth = True
    # Inner alloy rim barrel & hub dish
    hub_l = bm.verts.new((-width * 0.35, 0, 0))
    hub_r = bm.verts.new((width * 0.35, 0, 0))
    for i in range(n_seg):
        j = (i + 1) % n_seg
        f1 = bm.faces.new((rings[0][j], rings[0][i], hub_l))
        f1.material_index = 1
        f2 = bm.faces.new((rings[-1][i], rings[-1][j], hub_r))
        f2.material_index = 1
    # 5 chunky 90s alloy spokes on outer wheel face
    side_sign = 1.0 if center[0] > 0 else -1.0
    for s in range(5):
        ang = 2.0 * math.pi * s / 5.0
        sy, sz = math.cos(ang) * radius * 0.34, math.sin(ang) * radius * 0.34
        m = Matrix.Translation((side_sign * width * 0.38, sy, sz)) @ Euler((ang, 0, 0)).to_matrix().to_4x4() @ Matrix.Diagonal((0.032, radius * 0.54, 0.052, 1.0))
        ret = bmesh.ops.create_cube(bm, size=1.0, matrix=m)
        for v in ret["verts"]:
            for f in v.link_faces:
                f.material_index = 1
                f.smooth = True

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    ob.location = center
    ob.data.materials.append(mat_tire)
    ob.data.materials.append(mat_rim)
    _smart_uv(ob)
    return ob


# Greenhouse sections (y, half_w, z): windshield base -> roof front -> roof rear -> rear glass base
GH = [(-0.82, 0.86, 0.89), (-0.34, 0.67, 1.41), (0.76, 0.66, 1.43), (1.36, 0.85, 0.92)]


def build_sedan_from_spec(spec_path, repo_root=REPO_ROOT):
    t0 = time.time()
    spec = json.load(open(spec_path))
    if spec.get("kind") == "aircraft":                      # T-VEH-03: same command, other body plan
        from underworld_pipeline.vehicles import aircraft as AC
        return AC.build_plane(spec, repo_root)
    name = spec["asset_name"]
    paint_rgba = tuple(spec.get("paint_rgba", [0.09, 0.14, 0.21, 1.0]))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.render.fps, sc.render.fps_base = 30, 1.0

    root = bpy.data.objects.new(name, None)
    sc.collection.objects.link(root)

    # Automotive PBR Materials (TD-005 M_ prefix, <= 8 materials)
    m_paint = _mat(f"M_{name}_Paint", paint_rgba, roughness=0.22, metallic=0.55, coat=1.0, coat_rough=0.04)
    from underworld_pipeline.vehicles import interior as INT   # late: interior imports this module
    m_glass = INT.glass_material(f"M_{name}_Glass")                 # T-VEH-02: see-through, tinted
    m_paint.use_backface_culling = False                             # the open cabin shows the shell's inside
    m_chrome = _mat(f"M_{name}_Chrome", (0.82, 0.84, 0.86, 1.0), roughness=0.12, metallic=0.96)
    m_trim = _mat(f"M_{name}_Trim", (0.06, 0.06, 0.07, 1.0), roughness=0.62, metallic=0.05)
    m_tire = _mat(f"M_{name}_Tire", (0.045, 0.045, 0.048, 1.0), roughness=0.82, metallic=0.0)
    m_rim = _mat(f"M_{name}_Rim", (0.72, 0.74, 0.76, 1.0), roughness=0.22, metallic=0.90)
    m_head = _mat(f"M_{name}_Headlight", (0.95, 0.92, 0.82, 1.0), roughness=0.08, metallic=0.2, emit=1.5)
    m_tail = _mat(f"M_{name}_Taillight", (0.72, 0.05, 0.04, 1.0), roughness=0.12, metallic=0.1, emit=1.2)

    # Full-size late-90s American sedan dimensions (Blender -Y = Front -> Godot +Z!)
    # Length 5.04 m (y in [-2.52, +2.52]), Width 1.88 m (x in [-0.94, +0.94]), Height 1.44 m (z in [0, 1.44])
    wheel_r = 0.34
    wheel_w = 0.24
    wheelbase = 2.86
    track_w = 1.58
    y_front_axle = -1.42
    y_rear_axle = y_front_axle + wheelbase  # +1.44

    # 1. Sculpted Main Unibody Chassis (`Body`)
    bm = bmesh.new()
    # Lower body tub (sculpted multi-station loft along Y from front nose -2.42 to rear tail +2.42!)
    stations = [
        # (y, half_w_bot, half_w_belt, z_bot, z_belt)
        (-2.42, 0.82, 0.84, 0.30, 0.72),
        (-2.10, 0.89, 0.91, 0.27, 0.82),
        (-1.42, 0.90, 0.93, 0.26, 0.88),  # front axle fender peak
        (-0.82, 0.91, 0.93, 0.24, 0.90),  # cowl / A-pillar base
        (0.05,  0.91, 0.93, 0.24, 0.91),  # B-pillar
        (0.95,  0.91, 0.93, 0.25, 0.92),  # C-pillar base
        (1.44,  0.90, 0.93, 0.27, 0.92),  # rear axle fender
        (2.15,  0.88, 0.89, 0.29, 0.88),
        (2.42,  0.81, 0.83, 0.32, 0.84),
    ]
    rings = []
    for y, wb, wt, zb, zt in stations:
        # 8-point sculpted sedan cross-section per station (tumblehome + rocker panel tuck + crown)
        zm = 0.5 * (zb + zt)
        pts = [
            (-wb * 0.85, y, zb),
            (-wb, y, zb + 0.08),
            (-wt, y, zm + 0.05),
            (-wt * 0.96, y, zt),
            (wt * 0.96, y, zt),
            (wt, y, zm + 0.05),
            (wb, y, zb + 0.08),
            (wb * 0.85, y, zb),
        ]
        rings.append([bm.verts.new(p) for p in pts])
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for i in range(len(r0)):
            if i == 3 and INT.open_cabin_faces(GH[0][0], GH[-1][0], stations[k][0], stations[k + 1][0]):
                continue                                              # T-VEH-02: no lid over the cabin
            j = (i + 1) % len(r0)
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    # Cap front & rear noses
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])

    body_ob = _make_obj(bm, "Body", root, m_paint, subsurf=1)

    # Greenhouse / Cabin (Bot 1 fix 2026-11-22): separate, NOT subdivided mesh. The open greenhouse strip used
    # to sit inside the subsurf'd Body and Catmull-Clark collapsed it into a crumpled blob (see T-PIPE-04 renders).
    bm = bmesh.new()
    # Greenhouse / Cabin roof loft (windshield -> roof -> rear glass)
    gh = GH
    gh_rings = []
    for y, hw, z in gh:
        pts = [(-hw, y, z), (-hw * 0.55, y, z + (0.025 if z > 1.2 else 0.0)), (hw * 0.55, y, z + (0.025 if z > 1.2 else 0.0)), (hw, y, z)]
        gh_rings.append([bm.verts.new(p) for p in pts])
    # Side cabin pillars & roof skin
    for r0, r1 in zip(gh_rings, gh_rings[1:]):
        for i in range(3):
            f = bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i]))
            # Front windshield (idx 0) & rear window (idx 2) = glass material slot 1
    # Close side greenhouse windows cleanly (flush with beltline!)
    for idx_g in range(len(gh_rings) - 1):
        v_bl = bm.verts.new((gh[idx_g][1], gh[idx_g][0], 0.87))
        v_bl2 = bm.verts.new((gh[idx_g + 1][1], gh[idx_g + 1][0], 0.88))
        bm.faces.new((v_bl, v_bl2, gh_rings[idx_g + 1][3], gh_rings[idx_g][3]))
        v_br = bm.verts.new((-gh[idx_g][1], gh[idx_g][0], 0.87))
        v_br2 = bm.verts.new((-gh[idx_g + 1][1], gh[idx_g + 1][0], 0.88))
        bm.faces.new((v_br2, v_br, gh_rings[idx_g][0], gh_rings[idx_g + 1][0]))

    # Side mirrors
    for sx in (-1.0, 1.0):
        _add_box(bm, (sx * 0.94, -0.58, 0.95), (0.14, 0.09, 0.07), bevel=0.015, segs=2)

    cabin_ob = _make_obj(bm, "Cabin", root, m_paint, subsurf=0)
    _interior, fit = INT.build_interior(name, root, (0.42, -0.10, 0.52), stations, GH, INT.fabric_material(f"M_{name}_Interior"), m_trim)
    root["uw_interior_fit"] = str(fit)
    # Assign multi-materials to Body (0=Paint, 1=Glass, 2=Chrome, 3=Trim, 4=Headlight, 5=Taillight)
    for m in (m_glass, m_chrome, m_trim, m_head, m_tail):
        body_ob.data.materials.append(m)
    for m in (m_glass, m_chrome, m_trim, m_head, m_tail):
        cabin_ob.data.materials.append(m)
    for p in cabin_ob.data.polygons:
        c = p.center
        # roof skin + mirrors stay paint; windshield, rear glass and side windows -> glass
        if c.z < 1.38 and abs(c.x) < 0.90:
            p.material_index = 1
    for p in body_ob.data.polygons:
        c = p.center
        if False:
            p.material_index = 1
        elif c.y < -2.30 and abs(c.x) < 0.42 and 0.46 < c.z < 0.72:
            p.material_index = 2
        elif c.y < -2.26 and 0.46 < abs(c.x) < 0.84 and 0.50 < c.z < 0.72:
            p.material_index = 4
        elif c.y > 2.26 and 0.35 < abs(c.x) < 0.84 and 0.56 < c.z < 0.80:
            p.material_index = 5

    # 2. Flush Damage-Ready & Hinged Panels (Hood, Trunk, Bumper_F, Bumper_R, Door_FL/FR/RL/RR)
    bm_h = bmesh.new()
    _add_box(bm_h, (0.0, -1.56, 0.83), (1.42, 1.24, 0.045), rot=(math.radians(4.5), 0, 0), bevel=0.014, segs=2)
    _make_obj(bm_h, "Hood", root, m_paint, origin_world=(0.0, -0.94, 0.86))

    bm_tr = bmesh.new()
    _add_box(bm_tr, (0.0, 1.84, 0.85), (1.40, 0.82, 0.045), rot=(math.radians(-3.0), 0, 0), bevel=0.014, segs=2)
    _make_obj(bm_tr, "Trunk", root, m_paint, origin_world=(0.0, 1.44, 0.87))

    bm_bf = bmesh.new()
    _add_box(bm_bf, (0.0, -2.32, 0.39), (1.74, 0.22, 0.21), bevel=0.035, segs=2)
    _make_obj(bm_bf, "Bumper_F", root, m_trim, origin_world=(0.0, -2.32, 0.39))

    bm_br = bmesh.new()
    _add_box(bm_br, (0.0, 2.32, 0.41), (1.74, 0.22, 0.21), bevel=0.035, segs=2)
    _make_obj(bm_br, "Bumper_R", root, m_trim, origin_world=(0.0, 2.32, 0.41))

    # 4 Hinged Doors (flush with sculpted side beltline, pivoted at front hinge edge per T-ART-04!)
    for dname, sx, y_hinge, y_mid, d_len in (
        ("Door_FL", 1.0, -0.78, -0.30, 0.94),
        ("Door_FR", -1.0, -0.78, -0.30, 0.94),
        ("Door_RL", 1.0, 0.20, 0.64, 0.86),
        ("Door_RR", -1.0, 0.20, 0.64, 0.86),
    ):
        bm_d = bmesh.new()
        _add_box(bm_d, (sx * 0.895, y_mid, 0.60), (0.040, d_len, 0.50), bevel=0.012, segs=2)
        _add_box(bm_d, (sx * 0.922, y_mid + d_len * 0.30, 0.74), (0.018, 0.11, 0.030), bevel=0.006, segs=1)
        _make_obj(bm_d, dname, root, m_paint, origin_world=(sx * 0.88, y_hinge, 0.60))

    # 3. 4 Separate Wheels centered at EXACT wheel hubs (resting cleanly on z = 0.000!)
    for wname, wx, wy in (
        ("Wheel_FL", track_w * 0.5, y_front_axle),
        ("Wheel_FR", -track_w * 0.5, y_front_axle),
        ("Wheel_RL", track_w * 0.5, y_rear_axle),
        ("Wheel_RR", -track_w * 0.5, y_rear_axle),
    ):
        _build_wheel(wname, root, (wx, wy, wheel_r), wheel_r, wheel_w, m_tire, m_rim)

    # 4. Wheel-arch-safe authored convex collision (UCX_VH_Sedan_01-convcolonly) keeping underside >= 0.32m clear for VehicleWheel3D!
    bm_c = bmesh.new()
    _add_box(bm_c, (0.0, 0.0, 0.66), (1.82, 4.92, 0.64), bevel=0.05, segs=1)
    _add_box(bm_c, (0.0, 0.22, 1.18), (1.42, 2.05, 0.48), bevel=0.05, segs=1)
    res = bmesh.ops.convex_hull(bm_c, input=bm_c.verts)
    # keep ONLY the hull's faces (T-VEH-02, as in profiles.py): the beveled source boxes left
    # interior faces behind -> NON_MANIFOLD in the release gate. Same convex shape for physics.
    hull = set(f for f in res["geom"] if isinstance(f, bmesh.types.BMFace))
    bmesh.ops.delete(bm_c, geom=[f for f in bm_c.faces if f not in hull], context="FACES_ONLY")
    bmesh.ops.delete(bm_c, geom=[e for e in bm_c.edges if not e.link_faces], context="EDGES")
    bmesh.ops.delete(bm_c, geom=[v for v in bm_c.verts if not v.link_edges], context="VERTS")
    me_c = bpy.data.meshes.new(f"UCX_{name}-convcolonly")
    bm_c.to_mesh(me_c)
    bm_c.free()
    col_ob = bpy.data.objects.new(f"UCX_{name}-convcolonly", me_c)
    sc.collection.objects.link(col_ob)
    col_ob.parent = root

    # 5. Required Vehicle Sockets (T-ART-04 / M01_DeadDrop.md)
    for sname, sloc in (
        ("SOCKET_Seat_Driver", (0.42, -0.10, 0.52)),
        ("SOCKET_Seat_Passenger", (-0.42, -0.10, 0.52)),
        ("SOCKET_Exit_Left", (1.38, -0.18, 0.0)),
        ("SOCKET_Exit_Right", (-1.38, -0.18, 0.0)),
        ("SOCKET_Headlight_L", (0.68, -2.44, 0.65)),
        ("SOCKET_Headlight_R", (-0.68, -2.44, 0.65)),
        ("SOCKET_Taillight_L", (0.68, 2.44, 0.72)),
        ("SOCKET_Taillight_R", (-0.68, 2.44, 0.72)),
    ):
        s = bpy.data.objects.new(sname, None)
        s.empty_display_type = "ARROWS"
        s.empty_display_size = 0.25
        sc.collection.objects.link(s)
        s.parent = root
        s.location = sloc

    # Store VehicleBody3D metadata as glTF extras on root!
    root["uw_wheel_radius_m"] = wheel_r
    root["uw_wheelbase_m"] = wheelbase
    root["uw_track_width_m"] = track_w

    blend_path = os.path.join(repo_root, "Blender", "Source", "Vehicles", name, f"{name}.blend")
    os.makedirs(os.path.dirname(blend_path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True)
    print(f"[VEHICLE] built {name} (wheel_r={wheel_r}, wheelbase={wheelbase}, track={track_w}, {time.time() - t0:.1f}s) -> {blend_path}")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--repo", default=REPO_ROOT)
    a = ap.parse_args(argv)
    build_sedan_from_spec(a.spec, a.repo)
    sys.stdout.flush()
    os._exit(0)
