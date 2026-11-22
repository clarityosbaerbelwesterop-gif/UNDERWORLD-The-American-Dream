"""Cycles CPU turnaround previews (front / side / three-quarter) of an opened scene.

  blender -b SK_Jason.blend --python render_previews.py -- --out-prefix /path/SK_Jason [--res 512] [--samples 32] [--frame N --action A_...]
Writes <prefix>_front.png, <prefix>_side.png, <prefix>_3q.png. Never saves the .blend.
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector


def setup(res, samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.render.resolution_x = int(res * 0.75)
    sc.render.resolution_y = res
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    w = sc.world or bpy.data.worlds.new("W")
    sc.world = w
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.42, 0.40, 0.38, 1)
    bg.inputs["Strength"].default_value = 0.6
    for name, rot, energy in (("Key", (55, 0, -35), 3.5), ("Rim", (60, 0, 160), 2.0)):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = energy
        ld.angle = math.radians(8)
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_euler = [math.radians(a) for a in rot]
        sc.collection.objects.link(lo)
    # ground
    me = bpy.data.meshes.new("Ground")
    me.from_pydata([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new("PreviewGround", me)
    gm = bpy.data.materials.new("PreviewGroundMat")
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.25, 0.24, 0.23, 1)
    me.materials.append(gm)
    sc.collection.objects.link(g)
    cd = bpy.data.cameras.new("Cam")
    cd.lens = 70
    cam = bpy.data.objects.new("PreviewCam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def shoot(cam, direction, target, dist, path):
    d = Vector(direction).normalized()
    cam.location = target + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[PREVIEW]", path)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-prefix", required=True)
    ap.add_argument("--res", type=int, default=512)
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--action")
    ap.add_argument("--frame", type=float, default=0)
    ap.add_argument("--views", default="front,side,3q")
    ap.add_argument("--rest", action="store_true", help="render the rest (T-) pose")
    a = ap.parse_args(argv)
    sc = bpy.context.scene
    for ob in sc.objects:
        if ob.type == "MESH" and ("UCX_" in ob.name or "_LOD" in ob.name):
            ob.hide_render = True
    if a.action:
        arm = next(o for o in sc.objects if o.type == "ARMATURE")
        act = bpy.data.actions[a.action]
        arm.animation_data_create()
        arm.animation_data.action = act
        if act.slots:
            arm.animation_data.action_slot = act.slots[0]
        sc.frame_set(int(a.frame))
    if a.rest:
        for o in sc.objects:
            if o.type == "ARMATURE":
                o.data.pose_position = "REST"
    cam = setup(a.res, a.samples)
    os.makedirs(os.path.dirname(os.path.abspath(a.out_prefix)), exist_ok=True)
    body = (Vector((0, 0, 0.92)), 4.6)
    face = (Vector((0, 0, 1.70)), 1.0)
    views = {"front": ((0, -1, 0.08), body), "side": ((1, 0, 0.08), body), "3q": ((0.8, -1, 0.25), body),
             "back": ((0, 1, 0.08), body), "face": ((0.35, -1, 0.1), face), "faceside": ((1, 0, 0.05), face)}
    for v in a.views.split(","):
        d, (tgt, dist) = views[v]
        shoot(cam, d, tgt, dist, f"{a.out_prefix}_{v}.png")


main()
sys.stdout.flush()
os._exit(0)
