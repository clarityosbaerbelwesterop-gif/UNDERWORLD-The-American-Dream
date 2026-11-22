"""Independent Blender re-import check of exported .glb files (test helper, bpy).

  blender -b --factory-startup --python tests/verify_glb.py -- --expect expect.json
expect.json: {"assets": [{"glb": ..., "objects": [...], "absent": [...], "armature_bones": [...],
              "actions": [...], "animated_bone": [action, bone, frame], "lod_children": {parent: [children]}}]}
Exit 0 if every expectation holds, else 1.
"""
import json
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
exp = json.load(open(argv[argv.index("--expect") + 1]))
fails = 0


def check(cond, msg):
    global fails
    print(("[VERIFY][PASS] " if cond else "[VERIFY][FAIL] ") + msg)
    fails += 0 if cond else 1


for a in exp["assets"]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=a["glb"])
    objs = bpy.data.objects
    tag = a["glb"].rsplit("/", 1)[-1]
    for n in a.get("objects", []):
        check(n in objs, f"{tag}: object {n} re-imported")
    for n in a.get("absent", []):
        check(n not in objs, f"{tag}: object {n} absent")
    for parent, kids in a.get("lod_children", {}).items():
        p = objs.get(parent)
        got = sorted(c.name for c in p.children) if p else []
        check(p is not None and all(k in got for k in kids), f"{tag}: {parent} has LOD children {kids} (got {got})")
        if p:
            base = len(p.data.polygons)
            for k in kids:
                c = objs.get(k)
                check(c is not None and len(c.data.polygons) < base, f"{tag}: {k} has fewer faces than {parent}")
    if "armature_bones" in a:
        arms = [o for o in objs if o.type == "ARMATURE"]
        check(len(arms) == 1, f"{tag}: one armature")
        if arms:
            got = sorted(b.name for b in arms[0].data.bones)
            check(got == sorted(a["armature_bones"]), f"{tag}: bones {got}")
            sk = [o for o in objs if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)]
            check(len(sk) >= 1, f"{tag}: skinned mesh with Armature modifier re-imported")
    acts = sorted(x.name for x in bpy.data.actions)
    for n in a.get("actions", []):
        check(any(x == n or x.startswith(n) for x in acts), f"{tag}: action {n} re-imported (have {acts})")
    if "animated_bone" in a:
        act_name, bone, frame = a["animated_bone"]
        arm = [o for o in objs if o.type == "ARMATURE"][0]
        act = next(x for x in bpy.data.actions if x.name.startswith(act_name))
        arm.animation_data_create()
        arm.animation_data.action = act
        if act.slots:
            arm.animation_data.action_slot = act.slots[0]
        bpy.context.scene.frame_set(1)
        m1 = arm.pose.bones[bone].matrix.copy()
        bpy.context.scene.frame_set(frame)
        m2 = arm.pose.bones[bone].matrix.copy()
        diff = max(abs(m1[i][j] - m2[i][j]) for i in range(4) for j in range(4))
        check(diff > 0.05, f"{tag}: {act_name} moves bone {bone} between frame 1 and {frame} (max delta {diff:.3f})")

print(f"[VERIFY] RESULT: {'PASS' if fails == 0 else 'FAIL'} ({fails} failures)")
sys.stdout.flush()
import os  # noqa: E402
os._exit(0 if fails == 0 else 1)
