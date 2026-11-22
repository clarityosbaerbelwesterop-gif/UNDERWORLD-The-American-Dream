"""Cycles CPU review renders for weapons (quality gate: before/after, render-compare-improve loop).

  Tools/uwp-blender -b <Weapon>.blend --python Tools/underworld_pipeline/weapons/render_review.py -- \
      --out-dir <dir> [--views left,right,top,q3,q3back,serrations,stipple,sights,port,muzzle] [--res 1200] [--samples 64]
      [--action A_WPN_Pistol_01_Empty --frame 1] [--jpeg 90]

Same cameras/lights every run so passes are directly comparable. Never saves the .blend.
Coordinates follow REQ_WPN_Pistol_01 (origin = grip, barrel -Y, up +Z, gun's right side = -X).
"""
import argparse
import os
import sys

import bpy
from mathutils import Vector

C = (0.0, -0.062, -0.006)          # whole-gun framing target
VIEWS = {  # name: (direction from target to camera, target, distance, lens, aspect)
    "left": ((1, 0, 0.0), C, 0.66, 85, 1.5),
    "right": ((-1, 0, 0.0), C, 0.66, 85, 1.5),
    "top": ((0.0, 0.0001, 1), (0, -0.065, 0.0), 0.66, 85, 1.5),
    "q3": ((0.85, -0.85, 0.42), C, 0.66, 85, 1.5),
    "q3back": ((-0.75, 0.85, 0.45), C, 0.66, 85, 1.5),
    "serrations": ((0.75, 0.55, 0.35), (0, 0.010, 0.040), 0.16, 85, 1.5),
    "stipple": ((1, 0.15, -0.05), (0, 0.008, -0.030), 0.24, 85, 1.5),
    "sights": ((0.25, 1.0, 0.30), (0, 0.010, 0.050), 0.14, 85, 1.5),
    "port": ((-1, -0.25, 0.75), (0, -0.046, 0.045), 0.15, 85, 1.5),
    "muzzle": ((0.45, -1, 0.22), (0, -0.160, 0.035), 0.14, 85, 1.5),
}


def setup(res, aspect, samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = res, int(res / aspect)
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    w = bpy.data.worlds.new("UW_ReviewWorld")
    w.use_nodes = True
    sc.world = w
    nt = w.node_tree
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].color = (0.04, 0.04, 0.045, 1)
    ramp.color_ramp.elements[1].color = (0.62, 0.64, 0.68, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.35
    tgt = Vector((0, -0.06, 0.0))
    for name, loc, energy, size in (("UW_Key", (0.40, -0.30, 0.50), 14, 0.35), ("UW_Fill", (-0.50, -0.15, 0.10), 5, 0.6),
                                    ("UW_Rim", (0.05, 0.55, 0.40), 12, 0.25), ("UW_Top", (0.0, -0.1, 0.8), 6, 0.8)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size = energy, size
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        lo.rotation_euler = (tgt - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(lo)
    me = bpy.data.meshes.new("UW_Backdrop")
    z = -0.095
    me.from_pydata([(-3, -3, z), (3, -3, z), (3, 3, z), (-3, 3, z)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new("UW_Backdrop", me)
    gm = bpy.data.materials.new("UW_BackdropMat")
    gm.use_nodes = True
    p = gm.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (0.16, 0.16, 0.17, 1)
    p.inputs["Roughness"].default_value = 0.85
    me.materials.append(gm)
    sc.collection.objects.link(g)
    cd = bpy.data.cameras.new("UW_Cam")
    cam = bpy.data.objects.new("UW_Cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam, g


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--prefix", default="")
    ap.add_argument("--views", default=",".join(VIEWS))
    ap.add_argument("--res", type=int, default=1200)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--action")
    ap.add_argument("--frame", type=int, default=0)
    ap.add_argument("--jpeg", type=int, default=0, help="write JPEG with this quality instead of PNG")
    a = ap.parse_args(argv)
    sc = bpy.context.scene
    for ob in sc.objects:
        if ob.type == "MESH" and ("UCX_" in ob.name or "_LOD" in ob.name or ob.name.endswith("_HP")):
            ob.hide_render = True
        if ob.type == "EMPTY":
            ob.hide_render = True
    rig = next((o for o in sc.objects if o.type == "ARMATURE"), None)
    if rig is not None:
        rig.animation_data_create()
        if a.action:
            rig.animation_data.action = bpy.data.actions[a.action]
            sc.frame_set(a.frame)
        else:
            rig.animation_data.action = None
            for pb in rig.pose.bones:
                pb.location = (0, 0, 0)
                pb.rotation_quaternion = (1, 0, 0, 0)
    cam, backdrop = setup(a.res, 1.5, a.samples)
    os.makedirs(a.out_dir, exist_ok=True)
    if a.jpeg:
        sc.render.image_settings.file_format = "JPEG"
        sc.render.image_settings.quality = a.jpeg
    ext = ".jpg" if a.jpeg else ".png"
    for v in a.views.split(","):
        d, tgt, dist, lens, aspect = VIEWS[v]
        d = Vector(d).normalized()
        backdrop.hide_render = v == "top"
        cam.data.lens = lens
        cam.data.clip_start = 0.005
        cam.location = Vector(tgt) + d * dist
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(a.out_dir, f"{a.prefix}{v}{ext}")
        bpy.ops.render.render(write_still=True)
        print("[RENDER]", sc.render.filepath, flush=True)


main()
sys.stdout.flush()
os._exit(0)
