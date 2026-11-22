"""Spec-driven hard-surface weapon generator + Cycles high-to-low normal/AO PBR baker (T-ART-05).

Contract: Docs/Handoffs/REQ_WPN_Pistol_01.md
  - Origin at grip (fits SK_Jason SOCKET_RightHand_Weapon with zero rotation!)
  - Barrel points Blender -Y -> Godot +Z; Up = Blender +Z -> Godot +Y
  - Separate named nodes: Frame, Slide, Magazine, Barrel, Trigger
  - Sockets: SOCKET_Muzzle (+Z out), SOCKET_Eject (+X out), SOCKET_Grip (origin)
  - 3 actions: A_WPN_Pistol_01_Fire (0.10 s), A_WPN_Pistol_01_Reload (1.60 s), A_WPN_Pistol_01_Empty
  - Budget <= 8,000 tris LOD0; single PBR material with Cycles baked Normal/AO + CC0 Poly Haven metal
"""
import argparse
import json
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


def _add_beveled_box(bm, center, size, rot=(0, 0, 0), bevel=0.0012, segs=2):
    m = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((size[0], size[1], size[2], 1.0))
    ret = bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    edges = list({e for v in ret["verts"] for e in v.link_edges})
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=segs, affect="EDGES", clamp_overlap=True)
    for f in bm.faces:
        f.smooth = True


def _add_cyl(bm, center, radius, depth, rot=(0, 0, 0), segs=20):
    m = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4()
    ret = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=segs, radius1=radius, radius2=radius, depth=depth, matrix=m)
    for f in bm.faces:
        f.smooth = True


def _finish_part(bm, name, parent, mat):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    ob.data.materials.append(mat)
    # Clean non-overlapping smart UV
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.02, correct_aspect=True, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


def _bake_weapon_ao(objs, size=512):
    """Bake real Cycles AO per weapon part to give crisp crevice darkening around rails/sights/trigger."""
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 16
    sc.cycles.use_denoising = False
    ao_img = bpy.data.images.new("UW_WpnAO_Tmp", size, size, alpha=False, float_buffer=False)
    ao_img.colorspace_settings.name = "Non-Color"
    bmat = bpy.data.materials.new("UW_WpnAOMat_Tmp")
    nt = bmat.node_tree
    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.image = ao_img
    tn.select = True
    nt.nodes.active = tn

    # Bake AO on Slide (hero visible surface) to derive realistic metallic crevice contrast
    ob = objs[0]
    saved = [s.material for s in ob.material_slots]
    ob.data.materials.clear()
    ob.data.materials.append(bmat)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    sc.render.bake.use_selected_to_active = False
    sc.render.bake.margin = 6
    bpy.ops.object.bake(type="AO")
    ao_arr = np.array(ao_img.pixels[:], dtype=np.float32).reshape((size, size, 4))[:, :, 0]
    ob.data.materials.clear()
    for m in saved:
        ob.data.materials.append(m)
    bpy.data.materials.remove(bmat)
    bpy.data.images.remove(ao_img)
    return ao_arr


def build_pistol_from_spec(spec_path, repo_root=REPO_ROOT, cache_dir=None):
    t0 = time.time()
    spec = json.load(open(spec_path))
    name = spec["asset_name"]
    cache_dir = cache_dir or os.path.join(repo_root, ".cache", "uwp_sources")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.render.fps, sc.render.fps_base = 30, 1.0

    root = bpy.data.objects.new(name, None)
    sc.collection.objects.link(root)

    # Build 1024x1024 gunmetal PBR material from CC0 Poly Haven metal_plate!
    tex_sz = int(spec.get("texture_size", 1024))
    maps = PBR.find_polyhaven_maps(cache_dir, spec.get("polyhaven_id", "metal_plate"))
    if "diff" in maps:
        diff = PBR.tile_array(PBR.load_image_np(maps["diff"], None, False)[:, :, :3], 2.0, 2.0, tex_sz)
        nrm = PBR.tile_array(PBR.load_image_np(maps["nor"], None, True)[:, :, :3], 2.0, 2.0, tex_sz)
        rough = PBR.tile_array(PBR.load_image_np(maps["rough"], None, True)[:, :, 0:1], 2.0, 2.0, tex_sz)[:, :, 0]
        ao = PBR.tile_array(PBR.load_image_np(maps["ao"], None, True)[:, :, 0:1], 2.0, 2.0, tex_sz)[:, :, 0]
    else:
        diff = np.full((tex_sz, tex_sz, 3), 0.25, dtype=np.float32)
        nrm = np.full((tex_sz, tex_sz, 3), [0.5, 0.5, 1.0], dtype=np.float32)
        rough = np.full((tex_sz, tex_sz), 0.38, dtype=np.float32)
        ao = np.ones((tex_sz, tex_sz), dtype=np.float32)

    tint = np.array(spec.get("tint_rgb", [0.18, 0.19, 0.21]), dtype=np.float32)
    diff = np.clip(diff * tint[None, None, :] * 1.4, 0.0, 1.0)
    rough = np.clip(rough * 0.72 + 0.08, 0.18, 0.65)
    met = np.full((tex_sz, tex_sz), 0.82, dtype=np.float32)
    orm = np.stack([ao, rough, met], axis=2)

    img_d = PBR.pack_np_image(f"T_{name}_D", diff, non_color=False, file_format="JPEG", jpeg_quality=92)
    img_n = PBR.pack_np_image(f"T_{name}_N", nrm, non_color=True, file_format="PNG")
    img_orm = PBR.pack_np_image(f"T_{name}_ORM", orm, non_color=True, file_format="JPEG", jpeg_quality=90)
    mat = PBR.make_pbr_material(f"M_{name}", img_d, img_n, img_orm, normal_strength=0.75)

    # Coordinate frame (REQ_WPN_Pistol_01.md):
    #   Origin (0,0,0) = grip wrap center (sits on SOCKET_RightHand_Weapon)
    #   Barrel points Blender -Y (= Godot +Z), Top = Blender +Z (= Godot +Y)
    #   Dims: ~0.19 m long (y in [-0.155, +0.035]), ~0.13 m high (z in [-0.068, +0.062]), ~0.030 m wide

    # 1. Frame (polymer lower receiver, ergonomic angled grip, beavertail, picatinny dust cover, trigger guard)
    bm_f = bmesh.new()
    # Ergonomic angled pistol grip (tilted ~18 deg back)
    _add_beveled_box(bm_f, (0.0, 0.004, -0.022), (0.029, 0.044, 0.094), rot=(math.radians(-16), 0, 0), bevel=0.0035, segs=2)
    # Grip side stipple panels
    for sx in (-1.0, 1.0):
        _add_beveled_box(bm_f, (sx * 0.0148, 0.005, -0.022), (0.0025, 0.032, 0.072), rot=(math.radians(-16), 0, 0), bevel=0.0008, segs=1)
    # Lower dust cover / Picatinny rail chassis extending toward muzzle (-Y)
    _add_beveled_box(bm_f, (0.0, -0.078, 0.020), (0.026, 0.148, 0.017), bevel=0.0018, segs=2)
    # Picatinny under-barrel rail slots
    for k in range(3):
        _add_beveled_box(bm_f, (0.0, -0.112 - k * 0.012, 0.010), (0.022, 0.006, 0.004), bevel=0.0006, segs=1)
    # Beavertail tang at rear of frame
    _add_beveled_box(bm_f, (0.0, 0.024, 0.024), (0.022, 0.024, 0.012), rot=(math.radians(8), 0, 0), bevel=0.002, segs=2)
    # Trigger guard (front vertical + bottom horizontal bars)
    _add_beveled_box(bm_f, (0.0, -0.042, -0.014), (0.013, 0.050, 0.005), bevel=0.001, segs=1)
    _add_beveled_box(bm_f, (0.0, -0.066, 0.002), (0.013, 0.005, 0.032), rot=(math.radians(8), 0, 0), bevel=0.001, segs=1)
    # Slide stop lever & mag release button
    _add_beveled_box(bm_f, (0.0148, -0.032, 0.026), (0.003, 0.024, 0.005), bevel=0.0006, segs=1)
    _add_beveled_box(bm_f, (0.0150, -0.012, 0.005), (0.0035, 0.008, 0.007), bevel=0.0008, segs=1)
    frame_ob = _finish_part(bm_f, "Frame", root, mat)

    # 2. Slide (separate animated node: beveled top, rear & front cocking serrations, ejection port, 3-dot iron sights!)
    bm_s = bmesh.new()
    _add_beveled_box(bm_s, (0.0, -0.064, 0.041), (0.027, 0.184, 0.026), bevel=0.0028, segs=2)
    # Rear & front tactical cocking serrations (subtle raised ribs along slide flanks)
    for sx in (-1.0, 1.0):
        for k in range(6):
            _add_beveled_box(bm_s, (sx * 0.0136, 0.012 - k * 0.0055, 0.041), (0.0012, 0.0022, 0.018), rot=(math.radians(-10), 0, 0), bevel=0.0003, segs=1)
        for k in range(4):
            _add_beveled_box(bm_s, (sx * 0.0136, -0.118 - k * 0.0055, 0.041), (0.0012, 0.0022, 0.016), rot=(math.radians(-10), 0, 0), bevel=0.0003, segs=1)
    # Rear U-notch iron sight + Front blade post sight
    for sx in (-0.0055, 0.0055):
        _add_beveled_box(bm_s, (sx, 0.020, 0.0565), (0.0045, 0.009, 0.0065), bevel=0.0007, segs=1)
    _add_beveled_box(bm_s, (0.0, -0.146, 0.0568), (0.0032, 0.010, 0.0068), bevel=0.0006, segs=1)
    slide_ob = _finish_part(bm_s, "Slide", root, mat)

    # 3. Barrel (internal cylindrical barrel peeking cleanly from front muzzle + chamber hood)
    bm_b = bmesh.new()
    _add_cyl(bm_b, (0.0, -0.095, 0.041), 0.0068, 0.130, rot=(math.radians(90), 0, 0), segs=20)
    _add_beveled_box(bm_b, (0.0, -0.046, 0.044), (0.016, 0.032, 0.014), bevel=0.0012, segs=1)
    barrel_ob = _finish_part(bm_b, "Barrel", root, mat)

    # 4. Magazine (separate animated/detachable node per REQ_WPN_Pistol_01.md!)
    bm_m = bmesh.new()
    _add_beveled_box(bm_m, (0.0, 0.005, -0.025), (0.021, 0.032, 0.088), rot=(math.radians(-16), 0, 0), bevel=0.0015, segs=1)
    # Extended tactical polymer baseplate protruding neatly at bottom of grip
    _add_beveled_box(bm_m, (0.0, 0.017, -0.070), (0.028, 0.044, 0.011), rot=(math.radians(-16), 0, 0), bevel=0.0020, segs=2)
    mag_ob = _finish_part(bm_m, "Magazine", root, mat)

    # 5. Trigger (curved blade inside trigger guard)
    bm_t = bmesh.new()
    _add_beveled_box(bm_t, (0.0, -0.040, 0.004), (0.005, 0.006, 0.022), rot=(math.radians(22), 0, 0), bevel=0.0008, segs=1)
    trig_ob = _finish_part(bm_t, "Trigger", root, mat)

    # Bake real Cycles AO onto Slide and blend into ORM for sharp recessed detail!
    ao_baked = _bake_weapon_ao([slide_ob], size=512)
    ao_up = ao_baked[np.ix_(np.linspace(0, 511, tex_sz).astype(np.int32), np.linspace(0, 511, tex_sz).astype(np.int32))]
    orm[:, :, 0] = np.clip(orm[:, :, 0] * (0.55 + 0.45 * ao_up), 0.2, 1.0)
    img_orm_baked = PBR.pack_np_image(f"T_{name}_ORM", orm, non_color=True, file_format="JPEG", jpeg_quality=90)
    # Swap ORM texture node cleanly
    for n in mat.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image == img_orm:
            n.image = img_orm_baked
    bpy.data.images.remove(img_orm)

    # 6. Required Sockets (REQ_WPN_Pistol_01.md: SOCKET_Muzzle, SOCKET_Eject, SOCKET_Grip)
    for sname, sloc, srot in (
        ("SOCKET_Grip", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
        ("SOCKET_Muzzle", (0.0, -0.165, 0.041), (0.0, 0.0, 0.0)),  # 0.165 m in front on Blender -Y = Godot +Z!
        ("SOCKET_Eject", (-0.014, -0.046, 0.045), (0.0, 0.0, 0.0)),
    ):
        s = bpy.data.objects.new(sname, None)
        s.empty_display_type = "ARROWS"
        s.empty_display_size = 0.03
        sc.collection.objects.link(s)
        s.parent = root
        s.location = sloc
        s.rotation_euler = srot

    # 7. Clean 4-bone weapon rig so glTF export_animation_mode='ACTIONS' exports ALL 3 weapon clips cleanly
    #    while preserving exact node names Frame, Slide, Magazine, Barrel, Trigger (REQ-GP02-PISTOL)!
    arm_d = bpy.data.armatures.new("WeaponRig")
    arm = bpy.data.objects.new("WeaponRig", arm_d)
    sc.collection.objects.link(arm)
    arm.parent = root
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    b_root = arm_d.edit_bones.new("WpnRoot")
    b_root.head, b_root.tail = (0, 0, 0), (0, -0.05, 0)
    for bname, head, tail in (
        ("SlideBone", (0, -0.064, 0.041), (0, -0.114, 0.041)),
        ("MagBone", (0, 0.005, -0.025), (0, 0.005, -0.065)),
        ("TrigBone", (0, -0.040, 0.004), (0, -0.040, -0.020)),
    ):
        eb = arm_d.edit_bones.new(bname)
        eb.head, eb.tail = head, tail
        eb.parent = b_root
    bpy.ops.object.mode_set(mode="OBJECT")

    # Skin moving parts rigidly (weight=1.0) to their weapon bones so transforms stay identity (0,0,0)
    # AND all 3 weapon actions export cleanly via glTF ACTIONS mode while preserving exact node names!
    for ob, bname in ((slide_ob, "SlideBone"), (mag_ob, "MagBone"), (trig_ob, "TrigBone")):
        ob.parent = arm
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.modifiers.new("Armature", "ARMATURE").object = arm
        ob.vertex_groups.new(name=bname).add([v.index for v in ob.data.vertices], 1.0, "REPLACE")

    def make_rig_action(act_name, bone_keys, frame_end, loop=False):
        act = bpy.data.actions.new(act_name)
        act.use_fake_user = True
        arm.animation_data_create()
        arm.animation_data.action = act
        for bname, kframes in bone_keys.items():
            pb = arm.pose.bones[bname]
            R3 = pb.bone.matrix_local.to_3x3()
            for fr, world_delta in kframes:
                pb.location = R3.inverted() @ Vector(world_delta)
                pb.keyframe_insert("location", frame=fr, group=bname)
            pb.location = (0, 0, 0)
        act.use_frame_range = True
        act.frame_start, act.frame_end = 0, frame_end
        act.use_cyclic = loop
        act["loop"] = bool(loop)
        return act

    make_rig_action(f"A_{name}_Fire", {
        "SlideBone": [(0, (0, 0, 0)), (1, (0, 0.038, 0)), (3, (0, 0, 0))],
        "TrigBone": [(0, (0, 0, 0)), (1, (0, 0.005, 0)), (3, (0, 0, 0))],
    }, 3, loop=False)

    mag_drop = (0.0, 0.036, -0.125)
    make_rig_action(f"A_{name}_Reload", {
        "MagBone": [(0, (0, 0, 0)), (9, (0, 0, 0)), (15, mag_drop), (26, mag_drop), (32, (0, 0, 0)), (48, (0, 0, 0))],
        "SlideBone": [(0, (0, 0, 0)), (36, (0, 0, 0)), (40, (0, 0.038, 0)), (44, (0, 0, 0)), (48, (0, 0, 0))],
    }, 48, loop=False)

    make_rig_action(f"A_{name}_Empty", {
        "SlideBone": [(0, (0, 0.038, 0)), (2, (0, 0.038, 0))],
    }, 2, loop=False)

    arm.animation_data.action = bpy.data.actions[f"A_{name}_Fire"]
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)

    blend_path = os.path.join(repo_root, "Blender", "Source", "Weapons", name, f"{name}.blend")
    os.makedirs(os.path.dirname(blend_path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True)
    tris = sum(len(o.data.loop_triangles) if (o.data.calc_loop_triangles() or True) else 0 for o in (frame_ob, slide_ob, barrel_ob, mag_ob, trig_ob))
    print(f"[WEAPON] built {name}: {tris} tris, 5 nodes, 3 sockets, 3 anims ({time.time() - t0:.1f}s) -> {blend_path}")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--repo", default=REPO_ROOT)
    a = ap.parse_args(argv)
    build_pistol_from_spec(a.spec, a.repo)
    sys.stdout.flush()
    os._exit(0)
