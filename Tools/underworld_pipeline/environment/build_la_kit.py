"""Modular LA Street Environment Kit Generator ("Calloway Avenue", East Hollow — T-ART-03 / M01 Dead Drop).

Generates 2 m-grid-snapped modular architectural & street-prop .blend sources with real CC0
Poly Haven PBR textures (asphalt_02, concrete_pavement, red_brick, plastered_wall, corrugated_iron,
bark_brown_02, metal_plate), ready for `Tools/uwp export` (auto LOD1/LOD2 + trimesh/convex collision):
  1. SM_LA_Road_Straight     (10 x 14 m 2-lane asphalt road + double-yellow centerline)
  2. SM_LA_Sidewalk_Curb     (10 x 4 m concrete sidewalk + beveled granite curb)
  3. SM_LA_Bldg_ShopStucco   (10 x 8 x 7.5 m 2-storey LA stucco storefront "Vega Liquor" w/ awning)
  4. SM_LA_Bldg_GarageM01    (12 x 10 x 5.2 m M01 Dead Drop garage w/ hollow interior, open roll-up door, workbench)
  5. SM_LA_Streetlight       (7.2 m LA gooseneck sodium-vapor streetlamp)
  6. SM_LA_PalmTree          (11.5 m California fan palm w/ curved bark trunk & layered frond crown)
  7. SM_Prop_PackageCrate    (0.6 x 0.4 x 0.4 m M01 sealed delivery crate per M01_DeadDrop.md)
"""
import argparse
import math
import os
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
REPO_ROOT = os.path.abspath(os.path.join(TOOLS_DIR, ".."))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from underworld_pipeline.characters import pbr_textures as PBR  # noqa: E402


def _reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.render.fps, sc.render.fps_base = 30, 1.0
    return sc


def _ph_mat(cache_dir, name, ph_id, tint=(1, 1, 1), tile=2.0, tex_sz=512, rough_bias=0.0, metallic=0.0):
    maps = PBR.find_polyhaven_maps(cache_dir, ph_id)
    if "diff" in maps:
        diff = PBR.tile_array(PBR.load_image_np(maps["diff"], None, False)[:, :, :3], tile, tile, tex_sz)
        nrm = PBR.tile_array(PBR.load_image_np(maps["nor"], None, True)[:, :, :3], tile, tile, tex_sz)
        rough = PBR.tile_array(PBR.load_image_np(maps["rough"], None, True)[:, :, 0:1], tile, tile, tex_sz)[:, :, 0]
        ao = PBR.tile_array(PBR.load_image_np(maps["ao"], None, True)[:, :, 0:1], tile, tile, tex_sz)[:, :, 0]
    else:
        diff = np.full((tex_sz, tex_sz, 3), 0.5, dtype=np.float32)
        nrm = np.full((tex_sz, tex_sz, 3), [0.5, 0.5, 1.0], dtype=np.float32)
        rough = np.full((tex_sz, tex_sz), 0.8, dtype=np.float32)
        ao = np.ones((tex_sz, tex_sz), dtype=np.float32)
    diff = np.clip(diff * np.array(tint, dtype=np.float32)[None, None, :], 0.0, 1.0)
    rough = np.clip(rough + rough_bias, 0.15, 0.96)
    orm = np.stack([ao, rough, np.full_like(rough, metallic)], axis=2)
    img_d = PBR.pack_np_image(f"T_{name}_D", diff, False, "JPEG", 88)
    img_n = PBR.pack_np_image(f"T_{name}_N", nrm, True, "PNG")
    img_orm = PBR.pack_np_image(f"T_{name}_ORM", orm, True, "JPEG", 85)
    return PBR.make_pbr_material(f"M_{name}", img_d, img_n, img_orm, normal_strength=0.9)


def _flat_mat(name, rgba, rough=0.6, met=0.0, emit=0.0):
    m = bpy.data.materials.new(f"M_{name}")
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = met
    if emit > 0 and "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = rgba
        bsdf.inputs["Emission Strength"].default_value = emit
    return m


def _box(bm, center, size, rot=(0, 0, 0), mat_idx=0, bevel=0.0):
    m = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((size[0], size[1], size[2], 1.0))
    before = set(bm.faces)
    ret = bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    if bevel > 0:
        edges = list({e for v in ret["verts"] for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=1, affect="EDGES", clamp_overlap=True)
    for f in bm.faces:
        if f not in before:
            f.material_index = mat_idx


def _finalize_mesh(bm, name, root, mats, smooth=False):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = smooth
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    # Ground-align strictly to z = 0.000
    zmin = min(v.co.z for v in me.vertices)
    if abs(zmin) > 1e-6:
        for v in me.vertices:
            v.co.z -= zmin
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = root
    for m in mats:
        ob.data.materials.append(m)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.015, correct_aspect=True, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


def _save(repo_root, rel_cat, name):
    p = os.path.join(repo_root, "Blender", "Source", rel_cat, name, f"{name}.blend")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=p, compress=True)
    print(f"[ENV] saved {p}")
    return p


def build_road_straight(repo_root, cache_dir):
    sc = _reset()
    name = "SM_LA_Road_Straight"
    root = bpy.data.objects.new(name, None)
    sc.collection.objects.link(root)
    m_asp = _ph_mat(cache_dir, "LA_Asphalt", "asphalt_02", tint=(0.62, 0.62, 0.64), tile=3.0)
    m_yel = _flat_mat("LA_RoadLineYellow", (0.85, 0.64, 0.14, 1.0), rough=0.72)
    m_wht = _flat_mat("LA_RoadLineWhite", (0.82, 0.82, 0.80, 1.0), rough=0.75)

    bm = bmesh.new()
    # 10 m wide x 14 m long asphalt slab (top at z=0.04 -> ground base at z=0)
    _box(bm, (0, 0, 0.02), (10.0, 14.0, 0.04), mat_idx=0)
    # Double-yellow LA centerline stripes
    for sx in (-0.11, 0.11):
        _box(bm, (sx, 0, 0.043), (0.10, 13.9, 0.004), mat_idx=1)
    # Outer white lane edge stripes
    for sx in (-4.3, 4.3):
        _box(bm, (sx, 0, 0.043), (0.12, 13.9, 0.004), mat_idx=2)
    _finalize_mesh(bm, f"{name}_Mesh", root, [m_asp, m_yel, m_wht])
    # Authored collision (T-BUILD-02, B-PT-01): ONE flat slab, top exactly at the asphalt
    # (z = 0.04). The 4 mm paint stripes are render-only; in the old trimesh collision every
    # stripe was a 4 mm wall the player's cylinder snagged on. Adjacent/overlapping road tiles
    # are now coplanar, so walking and driving across tile seams is smooth.
    _flat_collision_slab(root, name, (10.0, 14.0), 0.04)
    return _save(repo_root, "Environment/LA", name)


def _flat_collision_slab(root, name, size_xy, top_z):
    bm = bmesh.new()
    _box(bm, (0, 0, top_z * 0.5), (size_xy[0], size_xy[1], top_z), mat_idx=0)
    me = bpy.data.meshes.new(f"UCX_{name}-colonly")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(f"UCX_{name}-colonly", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = root
    return ob


def build_sidewalk_curb(repo_root, cache_dir):
    sc = _reset()
    name = "SM_LA_Sidewalk_Curb"
    root = bpy.data.objects.new(name, None)
    sc.collection.objects.link(root)
    m_con = _ph_mat(cache_dir, "LA_Concrete", "concrete_pavement", tint=(0.82, 0.80, 0.76), tile=3.0)
    bm = bmesh.new()
    # 10 m along street (Y) x 4 m deep (X), 0.16 m high curb + sidewalk slab
    _box(bm, (0, 0, 0.08), (4.0, 10.0, 0.16), mat_idx=0, bevel=0.018)
    _finalize_mesh(bm, f"{name}_Mesh", root, [m_con])
    return _save(repo_root, "Environment/LA", name)


def build_shop_stucco(repo_root, cache_dir):
    sc = _reset()
    name = "SM_LA_Bldg_ShopStucco"
    root = bpy.data.objects.new(name, None)
    sc.collection.objects.link(root)
    m_stucco = _ph_mat(cache_dir, "LA_Stucco", "plastered_wall", tint=(0.86, 0.76, 0.62), tile=3.0)
    m_brick = _ph_mat(cache_dir, "LA_TrimBrick", "red_brick", tint=(0.75, 0.58, 0.48), tile=2.0)
    m_awn = _flat_mat("LA_Awning", (0.52, 0.14, 0.12, 1.0), rough=0.82)
    m_win = _flat_mat("LA_StoreGlass", (0.08, 0.13, 0.18, 1.0), rough=0.10, met=0.15)
    m_sign = _flat_mat("LA_SignBoard", (0.12, 0.24, 0.34, 1.0), rough=0.45, emit=0.35)

    bm = bmesh.new()
    # Main 2-storey LA stucco mass (10 m wide x 8 m deep x 7.2 m tall)
    _box(bm, (0, 0, 3.6), (10.0, 8.0, 7.2), mat_idx=0)
    # Brick lower wainscot band
    _box(bm, (0, -4.02, 0.65), (10.06, 0.12, 1.3), mat_idx=1)
    # Rooftop parapet cornice
    _box(bm, (0, 0, 7.38), (10.3, 8.3, 0.38), mat_idx=1, bevel=0.02)
    # Storefront awning protruding over sidewalk (-Y front)
    _box(bm, (0, -4.65, 3.35), (9.6, 1.4, 0.28), rot=(math.radians(14), 0, 0), mat_idx=2, bevel=0.02)
    # Original invented business sign fascia ("Vega Liquor" block)
    _box(bm, (0, -4.08, 4.15), (7.6, 0.22, 0.95), mat_idx=4, bevel=0.02)
    # Ground-floor shopfront windows + door recess
    for wx in (-2.8, 2.8):
        _box(bm, (wx, -4.04, 1.95), (3.1, 0.12, 1.85), mat_idx=3)
    _box(bm, (0.0, -4.04, 1.35), (1.35, 0.12, 2.35), mat_idx=3)
    # Second-floor apartment windows (4 bays)
    for wx in (-3.4, -1.15, 1.15, 3.4):
        _box(bm, (wx, -4.04, 5.65), (1.35, 0.14, 1.55), mat_idx=3)
    _finalize_mesh(bm, f"{name}_Mesh", root, [m_stucco, m_brick, m_awn, m_win, m_sign])
    return _save(repo_root, "Environment/LA", name)


def build_garage_m01(repo_root, cache_dir):
    sc = _reset()
    name = "SM_LA_Bldg_GarageM01"
    root = bpy.data.objects.new(name, None)
    sc.collection.objects.link(root)
    m_stucco = _ph_mat(cache_dir, "LA_GarageWall", "plastered_wall", tint=(0.68, 0.64, 0.58), tile=3.0)
    m_iron = _ph_mat(cache_dir, "LA_RollupDoor", "corrugated_iron", tint=(0.55, 0.58, 0.62), tile=2.0, metallic=0.65)
    m_floor = _ph_mat(cache_dir, "LA_GarageFloor", "concrete_pavement", tint=(0.56, 0.55, 0.53), tile=3.0)
    m_bench = _flat_mat("LA_Workbench", (0.34, 0.24, 0.16, 1.0), rough=0.78)

    bm = bmesh.new()
    # Hollow M01 Dead Drop Garage interior (12 m wide x 10 m deep x 4.8 m tall, open 4.8 m roll-up bay on -Y!)
    _box(bm, (0, 0, 0.08), (12.0, 10.0, 0.16), mat_idx=2)           # concrete floor slab
    _box(bm, (0, 0, 4.75), (12.2, 10.2, 0.30), mat_idx=0)           # flat roof slab
    _box(bm, (0, 4.85, 2.40), (12.0, 0.30, 4.64), mat_idx=0)        # back wall
    _box(bm, (-5.85, 0, 2.40), (0.30, 10.0, 4.64), mat_idx=0)       # left wall
    _box(bm, (5.85, 0, 2.40), (0.30, 10.0, 4.64), mat_idx=0)        # right wall
    # Front wall flanking the 4.8 m open garage bay
    _box(bm, (-4.2, -4.85, 2.40), (3.6, 0.30, 4.64), mat_idx=0)
    _box(bm, (4.2, -4.85, 2.40), (3.6, 0.30, 4.64), mat_idx=0)
    _box(bm, (0.0, -4.85, 4.10), (4.8, 0.30, 1.24), mat_idx=0)
    # Partially rolled-up corrugated metal door tucked at top of opening
    _box(bm, (0.0, -4.78, 3.35), (4.76, 0.12, 0.55), mat_idx=1)
    # Interior workbench along back wall (holds M01 Pickup_Package crate!)
    _box(bm, (0.0, 3.95, 0.90), (2.8, 0.90, 0.08), mat_idx=3)
    for lx in (-1.25, 1.25):
        for ly in (3.60, 4.30):
            _box(bm, (lx, ly, 0.45), (0.08, 0.08, 0.88), mat_idx=3)
    _finalize_mesh(bm, f"{name}_Mesh", root, [m_stucco, m_iron, m_floor, m_bench])

    sock = bpy.data.objects.new("SOCKET_PackageBench", None)
    sc.collection.objects.link(sock)
    sock.parent = root
    sock.location = (0.0, 3.95, 0.94)
    return _save(repo_root, "Environment/LA", name)


def build_streetlight(repo_root, cache_dir):
    sc = _reset()
    name = "SM_LA_Streetlight"
    root = bpy.data.objects.new(name, None)
    sc.collection.objects.link(root)
    m_pole = _ph_mat(cache_dir, "LA_LampMetal", "metal_plate", tint=(0.35, 0.37, 0.39), tile=2.0, metallic=0.82)
    m_lamp = _flat_mat("LA_SodiumLamp", (1.0, 0.78, 0.42, 1.0), rough=0.15, emit=4.0)

    bm = bmesh.new()
    # Base plinth + tapered 7.0 m pole + overhanging LA cobra-head luminaire extending -Y over roadway
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.18, radius2=0.14, depth=0.45, matrix=Matrix.Translation((0, 0, 0.225)))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.11, radius2=0.065, depth=6.6, matrix=Matrix.Translation((0, 0, 3.70)))
    # Horizontal cantilevered arm
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.045, radius2=0.035, depth=1.8,
                          matrix=Matrix.Translation((0, -0.88, 6.95)) @ Euler((math.radians(82), 0, 0)).to_matrix().to_4x4())
    # Cobra lamp housing + glowing sodium lens
    _box(bm, (0, -1.80, 7.08), (0.34, 0.62, 0.14), mat_idx=0, bevel=0.02)
    _box(bm, (0, -1.80, 6.99), (0.26, 0.48, 0.04), mat_idx=1)
    _finalize_mesh(bm, f"{name}_Mesh", root, [m_pole, m_lamp], smooth=True)
    return _save(repo_root, "Environment/LA", name)


def build_palm_tree(repo_root, cache_dir):
    sc = _reset()
    name = "SM_LA_PalmTree"
    root = bpy.data.objects.new(name, None)
    sc.collection.objects.link(root)
    m_bark = _ph_mat(cache_dir, "LA_PalmBark", "bark_brown_02", tint=(0.76, 0.68, 0.58), tile=3.0)
    m_frond = _flat_mat("LA_PalmFrond", (0.16, 0.30, 0.12, 1.0), rough=0.72)

    bm = bmesh.new()
    # Iconic tall subtly-curved LA Mexican fan palm trunk (10.5 m)
    segs = 14
    n_ring = 10
    rings = []
    for k in range(segs + 1):
        t = k / segs
        z = t * 10.5
        bend_x = 0.42 * math.sin(t * math.pi * 0.85)
        bend_y = -0.22 * (t ** 1.6)
        r = 0.28 * (1.0 - 0.52 * t) * (1.0 + 0.04 * (k % 2))
        rings.append([bm.verts.new((bend_x + math.cos(2 * math.pi * i / n_ring) * r,
                                    bend_y + math.sin(2 * math.pi * i / n_ring) * r, z)) for i in range(n_ring)])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n_ring):
            j = (i + 1) % n_ring
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = 0
    bm.faces.new(rings[0][::-1]).material_index = 0
    bm.faces.new(rings[-1]).material_index = 0

    # 16 gracefully arching palm fronds radiating from crown top
    top_c = Vector((0.42 * math.sin(math.pi * 0.85), -0.22, 10.45))
    for i in range(16):
        ang = (2.0 * math.pi * i / 16.0) + (0.15 if i % 2 else 0.0)
        pitch = 0.25 if i % 2 == 0 else -0.18
        f_len = 2.45 if i % 2 == 0 else 2.15
        d_xy = Vector((math.cos(ang), math.sin(ang), 0.0))
        side = Vector((-math.sin(ang), math.cos(ang), 0.0))
        prev = None
        for s in range(6):
            u = s / 5.0
            w = 0.48 * math.sin(math.pi * max(0.08, u ** 0.8))
            p = top_c + d_xy * (f_len * u) + Vector((0, 0, pitch * u * f_len - 1.15 * (u ** 2.1)))
            vl = bm.verts.new(p - side * w)
            vc = bm.verts.new(p + Vector((0, 0, 0.06 * math.sin(math.pi * u))))
            vr = bm.verts.new(p + side * w)
            if prev is not None:
                for quad in ((prev[0], prev[1], vc, vl), (prev[1], prev[2], vr, vc)):
                    f = bm.faces.new(quad)
                    f.material_index = 1
            prev = (vl, vc, vr)

    _finalize_mesh(bm, f"{name}_Mesh", root, [m_bark, m_frond], smooth=True)
    return _save(repo_root, "Environment/LA", name)


def build_package_crate(repo_root, cache_dir):
    """M01 'Dead Drop' sealed 0.6 x 0.4 x 0.4 m crate per Docs/Missions/M01_DeadDrop.md."""
    sc = _reset()
    name = "SM_Prop_PackageCrate"
    root = bpy.data.objects.new(name, None)
    sc.collection.objects.link(root)
    m_wood = _ph_mat(cache_dir, "Prop_CrateWood", "bark_brown_02", tint=(0.68, 0.56, 0.42), tile=2.0)
    m_strap = _ph_mat(cache_dir, "Prop_CrateMetal", "metal_plate", tint=(0.24, 0.25, 0.27), tile=2.0, metallic=0.80)

    bm = bmesh.new()
    _box(bm, (0, 0, 0.20), (0.60, 0.40, 0.40), mat_idx=0, bevel=0.008)
    # Corner metal reinforcement straps + lid seam
    for sx in (-0.24, 0.24):
        _box(bm, (sx, 0, 0.20), (0.04, 0.412, 0.412), mat_idx=1, bevel=0.002)
    _box(bm, (0, 0, 0.36), (0.612, 0.412, 0.025), mat_idx=1, bevel=0.002)
    _finalize_mesh(bm, f"{name}_Mesh", root, [m_wood, m_strap])
    return _save(repo_root, "Props", name)


BUILDERS = {
    "SM_LA_Road_Straight": build_road_straight,
    "SM_LA_Sidewalk_Curb": build_sidewalk_curb,
    "SM_LA_Bldg_ShopStucco": build_shop_stucco,
    "SM_LA_Bldg_GarageM01": build_garage_m01,
    "SM_LA_Streetlight": build_streetlight,
    "SM_LA_PalmTree": build_palm_tree,
    "SM_Prop_PackageCrate": build_package_crate,
}


def build_all(repo_root=REPO_ROOT, cache_dir=None, only=None):
    cache_dir = cache_dir or os.path.join(repo_root, ".cache", "uwp_sources")
    names = [only] if only else list(BUILDERS.keys())
    paths = []
    for n in names:
        paths.append(BUILDERS[n](repo_root, cache_dir))
    return paths


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO_ROOT)
    ap.add_argument("--only", default=None)
    a = ap.parse_args(argv)
    build_all(a.repo, only=a.only)
    sys.stdout.flush()
    os._exit(0)
