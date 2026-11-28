"""Light aircraft generator (P5, T-VEH-03): VH_Plane_Small_01 - an ORIGINAL four-seat high-wing
single-engine plane (no real type, no real registration), for M1 "Arrival" (private hangar) and
M5 "Wings" (the escape to New York).

Parts (glTF nodes, TD-005 functional names): Body (fuselage, wing, struts, tail, cabin glass,
interior, gear legs), Propeller (spins about its local Y = Blender -Y nose axis, origin on the
hub), Wheel_NG / Wheel_ML / Wheel_MR (nose + mains, origin on the axle). Sockets:
SOCKET_Seat_Driver (pilot, left), SOCKET_Seat_Passenger, SOCKET_Exit_Left/Right (under the wing),
SOCKET_Prop. Collision: two convex hulls (fuselage+gear, wing) - a single hull would fill the
space under the wing. Axes: Blender -Y = nose (Godot +Z), metres (TD-004).
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

from underworld_pipeline.vehicles import build_vehicle as BV
from underworld_pipeline.vehicles import interior as INT

REG = "UW-HOLLOW"          # fictional marking, deliberately not a valid national registration


def _loft(bm, sections, mat_idx=0):
    """sections: [(y, half_w, z_bot, z_top)] -> closed 10-point rounded fuselage loft."""
    rings = []
    for y, hw, zb, zt in sections:
        zm = 0.5 * (zb + zt)
        hh = 0.5 * (zt - zb)
        pts = []
        for k in range(10):
            a = 2 * math.pi * k / 10
            # superellipse-ish: boxy cabin, round belly
            cx, cz = math.cos(a), math.sin(a)
            sx = math.copysign(abs(cx) ** 0.7, cx)
            sz = math.copysign(abs(cz) ** (0.6 if cz > 0 else 0.9), cz)
            pts.append((hw * sx, y, zm + hh * sz))
        rings.append([bm.verts.new(p) for p in pts])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(10):
            j = (k + 1) % 10
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = mat_idx
    f0 = bm.faces.new(rings[0][::-1])
    f1 = bm.faces.new(rings[-1])
    f0.material_index = f1.material_index = mat_idx
    return rings


def _wing_panel(bm, y_le, chord, span0, span1, z, thick, mat_idx, dihedral=0.0, taper=1.0):
    """Wing panel from span0..span1 (x), leading edge at y_le (Blender -Y forward), thin airfoil box."""
    out = []
    for x, c in ((span0, chord), (span1, chord * taper)):
        zz = z + abs(x) * math.tan(math.radians(dihedral))
        le = y_le
        pts = [(x, le, zz), (x, le + c * 0.25, zz + thick * 0.5), (x, le + c, zz + thick * 0.05),
               (x, le + c * 0.25, zz - thick * 0.25)]
        out.append([bm.verts.new(p) for p in pts])
    a, b = out
    for k in range(4):
        j = (k + 1) % 4
        f = bm.faces.new((a[k], a[j], b[j], b[k]) if span1 > span0 else (a[k], b[k], b[j], a[j]))
        f.material_index = mat_idx
    for ring, rev in ((a, span1 > span0), (b, span1 <= span0)):
        f = bm.faces.new(ring[::-1] if rev else ring)
        f.material_index = mat_idx


def build_plane(spec, repo_root):
    name = spec["asset_name"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system, sc.unit_settings.scale_length = "METRIC", 1.0
    sc.render.fps = 30
    root = bpy.data.objects.new(name, None)
    sc.collection.objects.link(root)

    m_paint = BV._mat(f"M_{name}_Paint", tuple(spec.get("paint_rgba", (0.92, 0.92, 0.90, 1.0))), roughness=0.3, metallic=0.1, coat=1.0, coat_rough=0.05)
    m_stripe = BV._mat(f"M_{name}_Stripe", tuple(spec.get("stripe_rgba", (0.08, 0.22, 0.45, 1.0))), roughness=0.3, metallic=0.1, coat=1.0)
    m_glass = INT.glass_material(f"M_{name}_Glass")
    m_metal = BV._mat(f"M_{name}_Trim", (0.12, 0.12, 0.13, 1.0), roughness=0.45, metallic=0.7)
    m_tire = BV._mat(f"M_{name}_Tire", (0.045, 0.045, 0.048, 1.0), roughness=0.85)
    m_rim = BV._mat(f"M_{name}_Rim", (0.72, 0.74, 0.76, 1.0), roughness=0.25, metallic=0.9)
    m_prop = BV._mat(f"M_{name}_Prop", (0.05, 0.05, 0.055, 1.0), roughness=0.4, metallic=0.3)
    m_fab = INT.fabric_material(f"M_{name}_Interior")
    m_paint.use_backface_culling = False
    mats = [m_paint, m_stripe, m_glass, m_metal, m_fab]       # Body slots 0..4

    # ---------------------------------------------------------------- fuselage
    bm = bmesh.new()
    secs = [  # (y, half width, z bottom, z top) nose -> tail
        (-3.55, 0.20, 0.95, 1.30), (-3.30, 0.42, 0.78, 1.42), (-2.70, 0.52, 0.72, 1.50),
        (-1.80, 0.56, 0.70, 1.62), (-1.10, 0.58, 0.68, 2.02), (0.60, 0.58, 0.70, 2.02),
        (1.40, 0.48, 0.82, 1.84), (2.60, 0.30, 1.00, 1.62), (3.90, 0.14, 1.22, 1.52), (4.60, 0.06, 1.30, 1.46)]
    _loft(bm, secs, 0)
    # cabin glass: windscreen + side windows are separate thin panels just proud of the skin
    for sx in (-1, 1):
        x = sx * 0.585
        for (y0, y1) in ((-1.0, -0.15), (0.0, 0.55)):
            v = [bm.verts.new((x, y0, 1.42)), bm.verts.new((x, y1, 1.42)), bm.verts.new((x, y1 - 0.05, 1.92)), bm.verts.new((x, y0 + 0.08, 1.92))]
            f = bm.faces.new(v if sx > 0 else v[::-1])
            f.material_index = 2
    ws = [bm.verts.new(p) for p in ((-0.52, -1.80, 1.58), (0.52, -1.80, 1.58), (0.50, -1.12, 1.98), (-0.50, -1.12, 1.98))]
    f = bm.faces.new(ws[::-1])
    f.material_index = 2
    # cheat line stripe along the fuselage
    for sx in (-1, 1):
        x = sx * 0.60
        v = [bm.verts.new((x, -3.0, 1.12)), bm.verts.new((x, 3.6, 1.36)), bm.verts.new((x, 3.6, 1.44)), bm.verts.new((x, -3.0, 1.22))]
        f = bm.faces.new(v if sx > 0 else v[::-1])
        f.material_index = 1
    # ---------------------------------------------------------------- wing (high, on the cabin roof) + struts
    y_le, chord = -1.25, 1.55
    _wing_panel(bm, y_le, chord, 0.0, 5.6, 2.04, 0.16, 0, dihedral=1.5, taper=0.82)
    _wing_panel(bm, y_le, chord, 0.0, -5.6, 2.04, 0.16, 0, dihedral=1.5, taper=0.82)
    for sx in (-1, 1):                                   # wing tips in stripe colour
        BV._add_box(bm, (sx * 5.62, y_le + 0.6, 2.20), (0.06, 1.2, 0.12), bevel=0.02, segs=1)
    n_before = len(bm.faces)
    for sx in (-1, 1):
        for (ya, yb) in ((-0.95, -0.75), (-0.2, -0.25)):
            p0, p1 = Vector((sx * 0.55, ya, 0.85)), Vector((sx * 2.6, yb, 2.0))
            d = p1 - p0
            rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
            bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.035, radius2=0.035, depth=d.length, matrix=Matrix.Translation((p0 + p1) / 2) @ rot)
    for f in bm.faces[n_before:] if hasattr(bm.faces, "__getitem__") else []:
        f.material_index = 3
    bm.faces.ensure_lookup_table()
    for f in list(bm.faces)[n_before:]:
        f.material_index = 3
    # ---------------------------------------------------------------- tail
    _wing_panel(bm, 3.55, 0.85, 0.0, 1.75, 1.38, 0.09, 0, taper=0.7)
    _wing_panel(bm, 3.55, 0.85, 0.0, -1.75, 1.38, 0.09, 0, taper=0.7)
    fin = [bm.verts.new(p) for p in ((0, 3.35, 1.48), (0, 4.62, 1.46), (0, 4.75, 2.85), (0, 4.25, 2.85))]
    fin2 = [bm.verts.new((0.04 if i == 0 else 0.04, v.co.y, v.co.z)) for i, v in enumerate(fin)]
    for v in fin:
        v.co.x = -0.04
    bm.faces.new(fin[::-1]).material_index = 1
    bm.faces.new(fin2).material_index = 1
    for k in range(4):
        j = (k + 1) % 4
        bm.faces.new((fin[k], fin[j], fin2[j], fin2[k])).material_index = 1
    # ---------------------------------------------------------------- gear legs + cowling details
    n_before = len(bm.faces)
    for sx in (-1, 1):                                    # spring steel main legs
        BV._add_box(bm, (sx * 0.95, -0.25, 0.55), (0.75, 0.10, 0.04), rot=(0, math.radians(-sx * 32), 0), bevel=0.0, segs=1)
    BV._add_box(bm, (0, -2.95, 0.55), (0.06, 0.06, 0.55), bevel=0.0, segs=1)  # nose strut
    BV._add_box(bm, (0, -3.42, 1.02), (0.30, 0.14, 0.18), bevel=0.02, segs=1)  # air intake
    for f in list(bm.faces)[n_before:]:
        f.material_index = 3
    body = BV._make_obj(bm, "Body", root, mats[0], subsurf=0)
    for m in mats[1:]:
        body.data.materials.append(m)
    body["uw_allow_uv_overlap"] = 1
    # interior: 2 + 2 seats, panel, yokes (reuse the car kit around the pilot H-point)
    seat = (0.28, -0.55, 0.98)
    ib = bmesh.new()
    for x, y in ((0.28, -0.55), (-0.28, -0.55), (0.28, 0.35), (-0.28, 0.35)):
        INT._seat(ib, x, y, 0.98, 0.42)
    n_fab = len(ib.faces)
    INT._box(ib, (0, -1.55, 1.42), (1.05, 0.25, 0.32), bevel=0.02)            # instrument panel
    for x in (0.28, -0.28):
        INT._cyl(ib, (x, -1.42, 1.38), (x, -1.15, 1.38), 0.015, 8)              # yoke shaft
        INT._box(ib, (x, -1.13, 1.38), (0.30, 0.04, 0.07), bevel=0.01)          # yoke
    INT._box(ib, (0, -0.3, 0.70), (1.05, 2.4, 0.04), bevel=0.0)                 # floor
    for i, f in enumerate(ib.faces):
        f.material_index = 0 if i < n_fab else 1
    me = bpy.data.meshes.new("Interior")
    ib.to_mesh(me)
    ib.free()
    interior = bpy.data.objects.new("Interior", me)
    sc.collection.objects.link(interior)
    interior.parent = root
    me.materials.append(m_fab)
    me.materials.append(m_metal)
    BV._smart_uv(interior)
    # ---------------------------------------------------------------- propeller (separate, spins)
    pb = bmesh.new()
    hx, hy, hz = 0.0, -3.62, 1.12                          # hub, in WORLD space (_make_obj re-centres)
    bmesh.ops.create_cone(pb, cap_ends=True, segments=16, radius1=0.16, radius2=0.02, depth=0.32,
                          matrix=Matrix.Translation((hx, hy - 0.16, hz)) @ Matrix.Rotation(math.radians(90), 4, "X"))
    for sz in (-1, 1):
        BV._add_box(pb, (hx, hy + 0.02, hz + sz * 0.48), (0.13, 0.03, 0.82), rot=(0, math.radians(sz * 8), 0), bevel=0.01, segs=1)
    prop = BV._make_obj(pb, "Propeller", root, m_prop, origin_world=(hx, hy, hz))
    # ---------------------------------------------------------------- wheels (origin on the axle)
    for wname, c, r, w in (("Wheel_NG", (0.0, -2.95, 0.20), 0.20, 0.12), ("Wheel_ML", (1.32, -0.25, 0.24), 0.24, 0.14), ("Wheel_MR", (-1.32, -0.25, 0.24), 0.24, 0.14)):
        BV._build_wheel(wname, root, c, r, w, m_tire, m_rim)
    # ---------------------------------------------------------------- collision: 2 convex hulls
    for i, boxes in enumerate(([((0, -0.4, 1.25), (1.2, 8.0, 1.2)), ((0, -0.25, 0.25), (2.9, 0.6, 0.5))], [((0, -0.5, 2.1), (11.2, 1.6, 0.2))])):
        bc = bmesh.new()
        for (cc, ss) in boxes:
            BV._add_box(bc, cc, ss, bevel=0.0, segs=1)
        res = bmesh.ops.convex_hull(bc, input=bc.verts)
        hull = set(f for f in res["geom"] if isinstance(f, bmesh.types.BMFace))
        bmesh.ops.delete(bc, geom=[f for f in bc.faces if f not in hull], context="FACES_ONLY")
        bmesh.ops.delete(bc, geom=[e for e in bc.edges if not e.link_faces], context="EDGES")
        bmesh.ops.delete(bc, geom=[v for v in bc.verts if not v.link_edges], context="VERTS")
        mc = bpy.data.meshes.new(f"UCX_{name}_{i:02d}-convcolonly")
        bc.to_mesh(mc)
        bc.free()
        oc = bpy.data.objects.new(f"UCX_{name}_{i:02d}-convcolonly", mc)
        sc.collection.objects.link(oc)
        oc.parent = root
    # ---------------------------------------------------------------- sockets
    for sname, loc in (("SOCKET_Seat_Driver", seat), ("SOCKET_Seat_Passenger", (-0.28, -0.55, 0.98)),
                       ("SOCKET_Exit_Left", (1.35, -0.55, 0.0)), ("SOCKET_Exit_Right", (-1.35, -0.55, 0.0)),
                       ("SOCKET_Prop", (0.0, -3.62, 1.12))):
        s = bpy.data.objects.new(sname, None)
        s.empty_display_type, s.empty_display_size = "ARROWS", 0.25
        sc.collection.objects.link(s)
        s.parent, s.location = root, loc
    root["uw_kind"] = "aircraft"
    root["uw_registration"] = REG
    p = os.path.join(repo_root, "Blender", "Source", "Vehicles", name, f"{name}.blend")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=p, compress=True)
    print(f"[VEHICLE] built {name} (aircraft, span 11.2 m, length 8.3 m) -> {os.path.relpath(p, repo_root)}")
    return p
