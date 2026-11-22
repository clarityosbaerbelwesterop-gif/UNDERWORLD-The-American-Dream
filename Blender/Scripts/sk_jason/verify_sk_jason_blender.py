"""Re-import SK_Jason.glb in an empty Blender scene and check it against the manifest (Bot 2, T-ART-01/02).
  blender -b --factory-startup --python verify_sk_jason_blender.py -- SK_Jason.glb SK_Jason.manifest.json
"""
import json
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
glb, man = argv[0], json.load(open(argv[1]))
fails = 0


def check(c, msg):
    global fails
    print(("[JASON-BLENDER][PASS] " if c else "[JASON-BLENDER][FAIL] ") + msg)
    fails += 0 if c else 1


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps, bpy.context.scene.render.fps_base = 30, 1.0  # factory default is 24 fps
bpy.ops.import_scene.gltf(filepath=glb)
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
check(len(arms) == 1, f"one armature ({len(arms)})")
arm = arms[0]
bones = [l.strip() for l in open(os.path.join(os.path.dirname(__file__), "expected_bones.txt")) if l.strip()]
names = set(arm.data.bones.keys())
check(set(bones) <= names, f"{len(bones)} expected bones present (missing {sorted(set(bones) - names)}), total {len(names)}")
check(arm.data.bones["Hips"].parent and arm.data.bones["Hips"].parent.name == "Root", "Hips parented to Root")
meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SK_Jason")]  # skip importer bone shapes
print("[JASON-BLENDER] meshes:", sorted(o.name for o in meshes))
zs = []
dg = bpy.context.evaluated_depsgraph_get()
arm.data.pose_position = "REST"
dg.update()
for o in meshes:
    e = o.evaluated_get(dg)
    zs += [(e.matrix_world @ v.co).z for v in e.data.vertices]
check(abs(max(zs) - min(zs) - 1.82) <= 0.02 and abs(min(zs)) < 0.005, f"rest height {max(zs) - min(zs):.4f} m, min z {min(zs):.4f}")
tris = sum(len(o.data.loop_triangles) for o in meshes if not o.data.calc_loop_triangles())
check(tris <= 40000, f"{tris} tris <= 40000")
socks = [o for o in bpy.data.objects if o.name.startswith("SOCKET_RightHand_Weapon")]
check(socks and socks[0].parent_type == "BONE" and socks[0].parent_bone == "RightHand", "SOCKET_RightHand_Weapon bone-parented to RightHand")
acts = {a.name.split("_Armature")[0]: a for a in bpy.data.actions}
for a in man["animations"]:
    act = next((v for k, v in acts.items() if k.startswith(a["name"])), None)
    fr = tuple(act.frame_range) if act else None
    check(act is not None and abs(fr[0]) < 1e-3 and abs(fr[1] - a["frames"]) < 1e-3, f"{a['name']} frames 0..{a['frames']} (got {fr})")
print(f"[JASON-BLENDER] RESULT: {'PASS' if fails == 0 else 'FAIL'} ({fails} failures)")
sys.stdout.flush()
os._exit(0 if fails == 0 else 1)
