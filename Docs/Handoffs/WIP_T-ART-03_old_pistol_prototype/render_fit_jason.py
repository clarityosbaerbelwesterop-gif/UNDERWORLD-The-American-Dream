"""Fit check: WPN_Pistol_01 on SK_Jason's SOCKET_RightHand_Weapon in A_Jason_Aim_Pistol_Idle (Bot 2).
Opens SK_Jason.blend read-only (never saved), appends the pistol, parents its root to the socket with identity.
  blender -b Blender/Source/Characters/SK_Jason/SK_Jason.blend --python render_fit_jason.py -- --out-prefix P [--action A --frame N]"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PISTOL = os.path.join(REPO, "Blender", "Source", "Weapons", "WPN_Pistol_01", "WPN_Pistol_01.blend")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out-prefix", required=True)
ap.add_argument("--action", default="A_Jason_Aim_Pistol_Idle")
ap.add_argument("--frame", type=int, default=0)
ap.add_argument("--res", type=int, default=800)
ap.add_argument("--samples", type=int, default=32)
a = ap.parse_args(argv)
sc = bpy.context.scene
with bpy.data.libraries.load(PISTOL, link=False) as (src, dst):
    dst.objects = [n for n in src.objects]
for ob in dst.objects:
    sc.collection.objects.link(ob)
    if ob.type == "MESH" and ("UCX_" in ob.name or "_LOD" in ob.name):
        ob.hide_render = True
root = bpy.data.objects["WPN_Pistol_01"]
sock = bpy.data.objects["SOCKET_RightHand_Weapon"]
root.parent = sock
root.matrix_parent_inverse = Matrix.Identity(4)
root.matrix_basis = Matrix.Identity(4)
arm = next(o for o in sc.objects if o.type == "ARMATURE")
act = bpy.data.actions[a.action]
arm.animation_data.action = act
arm.animation_data.action_slot = act.slots[0]
sc.frame_set(a.frame)
bpy.context.view_layer.update()
mz = bpy.data.objects["SOCKET_Muzzle"].matrix_world
gp = bpy.data.objects["SOCKET_Grip"].matrix_world
print("[FIT] grip at", tuple(round(c, 3) for c in gp.translation), "muzzle at", tuple(round(c, 3) for c in mz.translation),
      "barrel dir", tuple(round(c, 3) for c in (mz.to_3x3() @ Vector((0, -1, 0)))))
# render
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = a.samples
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = a.res, int(a.res * 0.75)
sc.view_settings.view_transform = "AgX"
w = sc.world or bpy.data.worlds.new("W")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.4, 0.4, 0.42, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5
for name, rot, e in (("Key", (50, 0, -40), 3.5), ("Rim", (60, 0, 150), 2.0)):
    ld = bpy.data.lights.new(name, "SUN")
    ld.energy, ld.angle = e, math.radians(6)
    lo = bpy.data.objects.new(name, ld)
    lo.rotation_euler = [math.radians(v) for v in rot]
    sc.collection.objects.link(lo)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
sc.collection.objects.link(cam)
sc.camera = cam
tgt = gp.translation.copy()
views = {"hands_3q": ((0.9, -1.0, 0.35), tgt + Vector((0.0, -0.05, 0.02)), 0.75, 60),
         "hands_side": ((-1.0, -0.05, 0.1), tgt + Vector((0.0, 0.05, 0.0)), 0.9, 60),
         "hands_top": ((-0.2, 0.3, 1.0), tgt + Vector((0, 0.0, 0.0)), 0.7, 60),
         "body_3q": ((0.9, -1.0, 0.25), Vector((0, 0, 1.0)), 4.2, 60)}
for v, (d, t, dist, lens) in views.items():
    d = Vector(d).normalized()
    cam.data.lens = lens
    cam.location = t + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{a.out_prefix}_{v}.png"
    bpy.ops.render.render(write_still=True)
    print("[FIT]", sc.render.filepath, flush=True)
sys.stdout.flush()
os._exit(0)
