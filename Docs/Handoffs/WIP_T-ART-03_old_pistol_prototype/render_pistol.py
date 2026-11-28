"""Close-up Cycles CPU review renders of WPN_Pistol_01 (render-compare-improve loop), Bot 2.
  blender -b WPN_Pistol_01.blend --python render_pistol.py -- --out-prefix /tmp/p/v1 [--views left,right,q3,rear,grip,muzzle,top] [--res 900] [--samples 48] [--action A --frame N]
Same cameras every run so passes are comparable. Never saves the .blend."""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

VIEWS = {  # name: (camera direction from target, target, distance, lens)
    # world coords: origin = grip point; slide top ~ z 0.08, muzzle (0, -0.172, 0.061)
    "left": ((1, 0, 0.12), (0, -0.065, 0.02), 0.60, 85),
    "right": ((-1, 0, 0.12), (0, -0.065, 0.02), 0.60, 85),
    "q3": ((0.8, -0.9, 0.45), (0, -0.065, 0.02), 0.62, 85),
    "q3back": ((-0.7, 0.8, 0.5), (0, -0.065, 0.03), 0.62, 85),
    "rear": ((0.30, 1.0, 0.45), (0, 0.0, 0.075), 0.17, 85),
    "port": ((-1, -0.2, 0.7), (0, -0.05, 0.07), 0.17, 85),
    "grip": ((1, 0.25, -0.05), (0, 0.012, -0.015), 0.24, 85),
    "muzzle": ((0.45, -1, 0.25), (0, -0.168, 0.055), 0.15, 85),
    "top": ((0.0, 0.0001, 1), (0, -0.065, 0.05), 0.60, 85),
}


def setup(res, samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    try:
        sc.cycles.use_denoising = True
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        sc.cycles.use_denoising = False
    sc.render.resolution_x, sc.render.resolution_y = res, int(res * 0.7)
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    w = bpy.data.worlds.new("W")
    w.use_nodes = True
    sc.world = w
    nt = w.node_tree
    bg = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexGradient")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].color = (0.05, 0.05, 0.055, 1)
    ramp.color_ramp.elements[1].color = (0.55, 0.57, 0.6, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.25
    del sky
    for name, loc, energy, size in (("Key", (0.35, -0.25, 0.45), 9, 0.3), ("Fill", (-0.45, -0.1, 0.15), 3, 0.5),
                                    ("Rim", (0.0, 0.45, 0.35), 8, 0.25)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size = energy, size
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        lo.rotation_euler = (Vector((0, -0.06, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(lo)
    # backdrop
    me = bpy.data.meshes.new("Backdrop")
    me.from_pydata([(-2, -2, -0.09), (2, -2, -0.09), (2, 2, -0.09), (-2, 2, -0.09)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new("Backdrop", me)
    gm = bpy.data.materials.new("BackdropMat")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.06, 0.06, 0.065, 1)
    gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
    me.materials.append(gm)
    sc.collection.objects.link(g)
    cd = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-prefix", required=True)
    ap.add_argument("--views", default="left,right,q3,rear,grip,muzzle")
    ap.add_argument("--res", type=int, default=900)
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--action")
    ap.add_argument("--frame", type=int, default=0)
    a = ap.parse_args(argv)
    sc = bpy.context.scene
    for ob in sc.objects:
        if ob.type == "MESH" and ("UCX_" in ob.name or "_LOD" in ob.name):
            ob.hide_render = True
    if a.action:
        act = bpy.data.actions[a.action]
        for ob in sc.objects:
            if ob.animation_data is not None or ob.name in ("Slide", "Magazine"):
                slot = next((s for s in act.slots if s.identifier == "OB" + ob.name), None)
                if slot:
                    ob.animation_data_create()
                    ob.animation_data.action = act
                    ob.animation_data.action_slot = slot
        sc.frame_set(a.frame)
    cam = setup(a.res, a.samples)
    os.makedirs(os.path.dirname(os.path.abspath(a.out_prefix)), exist_ok=True)
    for v in a.views.split(","):
        d, tgt, dist, lens = VIEWS[v]
        d = Vector(d).normalized()
        cam.data.lens = lens
        cam.data.clip_start = 0.005
        cam.location = Vector(tgt) + d * dist
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = f"{a.out_prefix}_{v}.png"
        bpy.ops.render.render(write_still=True)
        print("[RENDER]", sc.render.filepath, flush=True)


main()
sys.stdout.flush()
os._exit(0)
