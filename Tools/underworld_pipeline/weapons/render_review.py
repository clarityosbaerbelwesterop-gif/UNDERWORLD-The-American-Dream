"""Cycles CPU review renders for weapons (quality gate: before/after, render-compare-improve loop).

  Tools/uwp-blender -b <Weapon>.blend --python Tools/underworld_pipeline/weapons/render_review.py -- \
      --out-dir <dir> [--views left,right,top,front,q3,q3r,q3back,low,serrations,stipple,sights,port,muzzle,guard] [--clay] [--res 1200] [--samples 64]
      [--action A_WPN_Pistol_01_Empty --frame 1] [--jpeg 90]

Same cameras/lights every run so passes are directly comparable. Never saves the .blend.
Coordinates follow REQ_WPN_Pistol_01 (origin = grip, barrel -Y, up +Z, gun's right side = -X).
"""
import argparse
import os
import sys

import bpy
from mathutils import Vector

C = (0.0, -0.062, -0.004)          # whole-gun framing target
# name: (direction from target to camera, target, distance, lens, aspect). "top" gets an explicit roll (see _aim).
VIEWS = {
    "left": ((1, 0, 0.0), C, 0.60, 85, 1.5),
    "right": ((-1, 0, 0.0), C, 0.60, 85, 1.5),
    "top": ((0.0, 0.0, 1), (0, -0.062, 0.0), 0.60, 85, 1.5),
    "front": ((0.0, -1, 0.05), (0, -0.06, -0.006), 0.46, 85, 1.5),
    "q3": ((0.85, -0.85, 0.42), C, 0.60, 85, 1.5),
    "q3r": ((-0.85, -0.85, 0.42), C, 0.60, 85, 1.5),
    "q3back": ((-0.75, 0.85, 0.45), C, 0.60, 85, 1.5),
    "low": ((0.9, -0.35, -0.45), C, 0.60, 85, 1.5),
    "serrations": ((0.75, 0.55, 0.35), (0, 0.010, 0.040), 0.16, 85, 1.5),
    "stipple": ((1, 0.15, -0.05), (0, 0.008, -0.030), 0.24, 85, 1.5),
    "sights": ((0.25, 1.0, 0.30), (0, 0.010, 0.050), 0.14, 85, 1.5),
    "port": ((-1, -0.25, 0.75), (0, -0.046, 0.045), 0.15, 85, 1.5),
    "muzzle": ((0.45, -1, 0.22), (0, -0.160, 0.035), 0.14, 85, 1.5),
    "guard": ((0.8, -0.3, -0.25), (0, -0.062, 0.000), 0.17, 85, 1.5),
    "backstrap": ((0.8, 0.6, 0.1), (0.006, 0.024, -0.012), 0.16, 85, 1.5),
}


def _aim(cam, v, d):
    if v == "top":   # look straight down; screen right = rear (+Y) like the left view, screen up = gun's right (-X)
        from mathutils import Matrix
        cam.rotation_euler = Matrix(((0, -1, 0), (1, 0, 0), (0, 0, 1))).to_euler()
    else:
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()


LIGHT_GAIN = 0.3


def _area(sc, name, loc, tgt, energy, size, size_y=None):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy * LIGHT_GAIN
    if size_y:
        ld.shape, ld.size, ld.size_y = "RECTANGLE", size, size_y
    else:
        ld.size = size
    lo = bpy.data.objects.new(name, ld)
    lo.location = loc
    lo.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(lo)
    return lo


def setup(res, aspect, samples):
    """Product-shot rig for dark metal/polymer: big soft key + strip lights so black parts show form through
    reflections, a bright gradient world (reflections) and a mid-grey seamless floor."""
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
        sc.view_settings.look = "AgX - Base Contrast"
    except Exception:
        pass
    sc.view_settings.exposure = 0.0
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
    ramp.color_ramp.elements[0].color = (0.10, 0.10, 0.11, 1)
    ramp.color_ramp.elements[1].color = (0.85, 0.87, 0.90, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.30
    tgt = (0, -0.06, 0.0)
    _area(sc, "UW_Key", (0.45, -0.35, 0.55), tgt, 16, 0.55)
    _area(sc, "UW_Fill", (-0.55, -0.20, 0.25), tgt, 6, 0.8)
    _area(sc, "UW_StripL", (0.30, 0.05, 0.18), tgt, 5, 0.06, 0.60)
    _area(sc, "UW_StripR", (-0.30, 0.05, 0.18), tgt, 5, 0.06, 0.60)
    _area(sc, "UW_Rim", (0.05, 0.60, 0.45), tgt, 10, 0.30)
    _area(sc, "UW_Top", (0.0, -0.08, 0.75), tgt, 8, 0.9, 0.5)
    me = bpy.data.meshes.new("UW_Backdrop")
    z = -0.085
    me.from_pydata([(-3, -3, z), (3, -3, z), (3, 3, z), (-3, 3, z)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new("UW_Backdrop", me)
    gm = bpy.data.materials.new("UW_BackdropMat")
    gm.use_nodes = True
    p = gm.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (0.045, 0.045, 0.048, 1)
    p.inputs["Roughness"].default_value = 0.9
    me.materials.append(gm)
    sc.collection.objects.link(g)
    cd = bpy.data.cameras.new("UW_Cam")
    cam = bpy.data.objects.new("UW_Cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam, g


def clay(sc):
    m = bpy.data.materials.new("UW_Clay")
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (0.55, 0.55, 0.55, 1)
    p.inputs["Roughness"].default_value = 0.55
    for ob in sc.objects:
        if ob.type == "MESH":
            for s in ob.material_slots:
                s.link = "OBJECT"
                s.material = m


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
    ap.add_argument("--clay", action="store_true", help="grey clay override (geometry check)")
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
    if a.clay:
        clay(sc)
    cam, backdrop = setup(a.res, 1.5, a.samples)
    if a.clay:
        sc.view_settings.exposure = -1.6
    os.makedirs(a.out_dir, exist_ok=True)
    if a.jpeg:
        sc.render.image_settings.file_format = "JPEG"
        sc.render.image_settings.quality = a.jpeg
    ext = ".jpg" if a.jpeg else ".png"
    for v in a.views.split(","):
        d, tgt, dist, lens, aspect = VIEWS[v]
        d = Vector(d).normalized()
        backdrop.hide_render = v in ("top", "low")
        cam.data.lens = lens
        cam.data.clip_start = 0.005
        cam.location = Vector(tgt) + d * dist
        _aim(cam, v, d)
        sc.render.filepath = os.path.join(a.out_dir, f"{a.prefix}{v}{ext}")
        bpy.ops.render.render(write_still=True)
        print("[RENDER]", sc.render.filepath, flush=True)


main()
sys.stdout.flush()
os._exit(0)
