"""Spec-driven hard-surface weapon generator with a real high-to-low Cycles CPU bake (T-ART-03 quality pass).

Contract: Docs/Handoffs/REQ_WPN_Pistol_01.md (unchanged by the quality pass)
  - Origin at grip (fits SK_Jason SOCKET_RightHand_Weapon with zero rotation)
  - Barrel points Blender -Y -> Godot +Z; Up = Blender +Z -> Godot +Y
  - Separate named nodes: Frame, Slide, Magazine, Barrel, Trigger (rigid-skinned to a 4-bone WeaponRig)
  - Sockets: SOCKET_Muzzle (+Z out), SOCKET_Eject, SOCKET_Grip (origin)
  - 3 actions: A_WPN_Pistol_01_Fire (0.10 s), A_WPN_Pistol_01_Reload (1.60 s), A_WPN_Pistol_01_Empty
  - Budget <= 8,000 tris LOD0; ONE glTF PBR material M_<Name> (D / N / ORM), hero tier 2048^2

Pipeline (see Docs/PIPELINE_WEAPONS.md):
  1. parts from 2D profiles (weapons/pistol_hs.py, helpers weapons/hardsurface.py), built twice:
     high-poly bake source (round bevels, serrations, pins, engraving, stipple + micro bump in the shader)
     and game low-poly (same silhouette, chamfers, triangulated, hard edges = UV seams)
  2. one shared UV atlas for all parts (smart project + average scale + pack)
  3. Cycles CPU selected-to-active bakes: base colour, roughness, metallic, AO, tangent normal
     (curvature/edge-wear is evaluated in the HP shaders, weapons/hs_materials.py)
  4. pack D/N/ORM into the .blend, glTF-ready Principled material, delete HP sources
  5. sockets, rig, actions (contract above)
Spec keys: asset_name, texture_size, bake_samples_ao, finishes{slide,barrel,frame:{base,rough}}, stipple_zone.
Env UWP_WEAPON_FAST=1 -> 512 px / 8 AO samples (iteration only, never commit).
"""
import argparse
import json
import os
import sys
import tempfile
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
REPO_ROOT = os.path.abspath(os.path.join(TOOLS_DIR, ".."))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from underworld_pipeline.characters import pbr_textures as PBR  # noqa: E402
from underworld_pipeline.weapons import baker as BK  # noqa: E402
from underworld_pipeline.weapons import hardsurface as H  # noqa: E402
from underworld_pipeline.weapons import hs_materials as HM  # noqa: E402
from underworld_pipeline.weapons import pistol_hs as P  # noqa: E402

NODES = ("Frame", "Slide", "Barrel", "Trigger", "Magazine")


def _pack(name, rgb, non_color, fmt, quality=92):
    """Write a numpy RGB image (Blender bottom-up order) without any view transform, reload and pack it."""
    h, w = rgb.shape[:2]
    im = bpy.data.images.new(name + "_tmp", w, h, alpha=False)
    im.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    rgba = np.concatenate([np.clip(rgb, 0, 1), np.ones((h, w, 1), np.float32)], axis=2).astype(np.float32)
    im.pixels.foreach_set(rgba.ravel())
    ext = ".jpg" if fmt == "JPEG" else ".png"
    with tempfile.TemporaryDirectory(prefix="uwp_wtex_") as td:
        path = os.path.join(td, name + ext)
        im.filepath_raw = path
        im.file_format = fmt
        if fmt == "JPEG":
            im.save(filepath=path, quality=quality)
        else:
            im.save(filepath=path)
        bpy.data.images.remove(im)
        out = bpy.data.images.load(path, check_existing=False)
        out.name = name
        out.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
        out.pack()
    return out


def _build_set(hp, M):
    objs = {}
    for nm, parts in P.build(hp, M).items():
        ob = H.join(parts, nm + ("_HP" if hp else ""))
        H.finish(ob, hp)
        objs[nm] = ob
    return objs


def build_pistol_from_spec(spec_path, repo_root=REPO_ROOT, cache_dir=None):
    t0 = time.time()
    spec = json.load(open(spec_path))
    name = spec["asset_name"]
    fast = os.environ.get("UWP_WEAPON_FAST") == "1"
    tex_sz = 512 if fast else int(spec.get("texture_size", 2048))
    ao_samples = 8 if fast else int(spec.get("bake_samples_ao", 64))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.render.fps, sc.render.fps_base = 30, 1.0
    sc.view_settings.view_transform = "Standard"

    root = bpy.data.objects.new(name, None)
    sc.collection.objects.link(root)

    # 1. high-poly bake source + game low-poly from the same profiles
    M = HM.library(spec)
    hps = _build_set(True, M)
    lps = _build_set(False, M)
    tris = {nm: sum(len(p.vertices) - 2 for p in ob.data.polygons) for nm, ob in lps.items()}
    print(f"[WEAPON] LP tris {tris} total {sum(tris.values())}; HP tris "
          f"{sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in hps.values())}", flush=True)

    # 2. shared atlas
    BK.unwrap([lps[n] for n in NODES], H.LP_SHARP_DEG + 1, margin=float(spec.get("uv_margin", 0.004)),
              sheet_material=HM.GRIP_SHEET)   # grip = one seamless sheet (no stipple seams on the straps)

    # 3. bake
    maps, times = BK.bake_all({n: (hps[n], lps[n]) for n in NODES}, tex_sz, samples_ao=ao_samples)
    D, N, ORM, cover = BK.post(maps)
    print(f"[WEAPON] bake {tex_sz}px coverage {cover:.2%} times {times}", flush=True)

    # 4. game material
    img_d = _pack(f"T_{name}_D", D, False, "JPEG", 94)
    img_n = _pack(f"T_{name}_N", N, True, "PNG")
    img_orm = _pack(f"T_{name}_ORM", ORM, True, "JPEG", 94)
    mat = PBR.make_pbr_material(f"M_{name}", img_d, img_n, img_orm, normal_strength=1.0)
    for nm in NODES:
        lp = lps[nm]
        lp.data.materials.clear()
        lp.data.materials.append(mat)
        lp.data.uv_layers[0].name = "UVMap"
    for ob in hps.values():
        me = ob.data
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
    for m in list(bpy.data.materials):
        if m is not mat:
            bpy.data.materials.remove(m)
    for nm in NODES:
        lps[nm].parent = root
    frame_ob, slide_ob, barrel_ob, trig_ob, mag_ob = (lps[n] for n in NODES)

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

    def _fcurves(act):
        if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])):
            return list(act.fcurves)
        out = []   # Blender 5 layered actions
        for layer in getattr(act, "layers", []):
            for strip in layer.strips:
                for cb in strip.channelbags:
                    out += list(cb.fcurves)
        return out

    def make_rig_action(act_name, bone_keys, frame_end, loop=False, ease_map=None):
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
        # timing feel (key frames unchanged = contract): segment easing keyed by the segment's start frame
        for fc in _fcurves(act):
            bname = fc.data_path.split('"')[1]
            for kp in fc.keyframe_points:
                interp, ease = (ease_map or {}).get((bname, int(round(kp.co.x))), ("LINEAR", "AUTO"))
                kp.interpolation = interp
                kp.easing = ease
        act.use_frame_range = True
        act.frame_start, act.frame_end = 0, frame_end
        act.use_cyclic = loop
        act["loop"] = bool(loop)
        return act

    make_rig_action(f"A_{name}_Fire", {
        "SlideBone": [(0, (0, 0, 0)), (1, (0, 0.038, 0)), (3, (0, 0, 0))],
        "TrigBone": [(0, (0, 0, 0)), (1, (0, 0.005, 0)), (3, (0, 0, 0))],
    }, 3, loop=False, ease_map={("SlideBone", 0): ("LINEAR", "AUTO"), ("SlideBone", 1): ("QUAD", "EASE_IN"),
                                 ("TrigBone", 1): ("QUAD", "EASE_OUT")})   # blowback snaps back, spring returns

    mag_drop = (0.0, 0.036, -0.125)
    make_rig_action(f"A_{name}_Reload", {
        "MagBone": [(0, (0, 0, 0)), (9, (0, 0, 0)), (15, mag_drop), (26, mag_drop), (32, (0, 0, 0)), (48, (0, 0, 0))],
        "SlideBone": [(0, (0, 0, 0)), (36, (0, 0, 0)), (40, (0, 0.038, 0)), (44, (0, 0, 0)), (48, (0, 0, 0))],
    }, 48, loop=False, ease_map={("MagBone", 9): ("QUAD", "EASE_IN"),       # released mag falls (gravity)
                                  ("MagBone", 26): ("CUBIC", "EASE_OUT"),    # new mag pushed in, decelerates as it seats
                                  ("SlideBone", 36): ("SINE", "EASE_IN_OUT"),  # hand racks the slide
                                  ("SlideBone", 40): ("QUAD", "EASE_IN")})     # spring snaps it forward

    make_rig_action(f"A_{name}_Empty", {
        "SlideBone": [(0, (0, 0.038, 0)), (2, (0, 0.038, 0))],
    }, 2, loop=False)

    arm.animation_data.action = bpy.data.actions[f"A_{name}_Fire"]
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)

    blend_path = os.path.join(repo_root, "Blender", "Source", "Weapons", name, f"{name}.blend")
    os.makedirs(os.path.dirname(blend_path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True)
    print(f"[WEAPON] built {name}: {sum(tris.values())} tris, 5 nodes, 3 sockets, 3 anims, {tex_sz}px maps "
          f"({time.time() - t0:.1f}s) -> {blend_path}")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--repo", default=REPO_ROOT)
    a = ap.parse_args(argv)
    build_pistol_from_spec(a.spec, a.repo)
    sys.stdout.flush()
    os._exit(0)
