"""Re-import WPN_Pistol_01.glb in an empty Blender scene and check the REQ-GP02-PISTOL contract (Bot 2).
  blender -b --factory-startup --python verify_wpn_pistol_01_blender.py -- WPN_Pistol_01.glb"""
import json
import os
import struct
import sys

import bpy

glb = sys.argv[sys.argv.index("--") + 1:][0]
fails = 0


def check(c, msg):
    global fails
    print(("[PISTOL-BLENDER][PASS] " if c else "[PISTOL-BLENDER][FAIL] ") + msg)
    fails += 0 if c else 1


# glTF JSON chunk: material maps
with open(glb, "rb") as f:
    f.read(12)
    ln, _ = struct.unpack("<II", f.read(8))
    gj = json.loads(f.read(ln))
mats = gj.get("materials", [])
check(len(mats) == 1 and mats[0]["name"] == "M_WPN_Pistol_01", f"one material M_WPN_Pistol_01 ({[m['name'] for m in mats]})")
m = mats[0]
pbr = m.get("pbrMetallicRoughness", {})
check("baseColorTexture" in pbr and "metallicRoughnessTexture" in pbr and "normalTexture" in m and "occlusionTexture" in m,
      "glTF PBR: baseColor + metallicRoughness + normal + occlusion textures")
check(m.get("occlusionTexture", {}).get("index") == pbr.get("metallicRoughnessTexture", {}).get("index"), "occlusion packed in the ORM texture (R)")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30
bpy.ops.import_scene.gltf(filepath=glb)
obs = {o.name: o for o in bpy.data.objects}
for nm in ("WPN_Pistol_01", "Frame", "Slide", "Magazine", "SOCKET_Muzzle", "SOCKET_Eject", "SOCKET_Grip"):
    check(nm in obs, f"node {nm}")
# the importer leaves the last action applied: back to the rest pose before measuring
for o in bpy.data.objects:
    if o.animation_data:
        o.animation_data.action = None
for nm in ("Slide", "Magazine"):
    obs[nm].location, obs[nm].scale = (0, 0, 0), (1, 1, 1)
bpy.context.view_layer.update()
mz = obs["SOCKET_Muzzle"].matrix_world.translation
check(0.16 <= -mz.y <= 0.20, f"muzzle {-mz.y:.3f} m in front of the origin (Blender -Y)")
tris = 0
for o in bpy.data.objects:
    if o.type == "MESH" and "_LOD" not in o.name and not o.name.startswith("UCX_"):
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
check(tris <= 8000, f"LOD0 {tris} tris <= 8000")
check(any(n.startswith("Frame_LOD1") for n in obs) and any(n.startswith("UCX_") for n in obs), "LOD1/LOD2 + UCX collision present")
want = {"A_WPN_Pistol_01_Fire": 3, "A_WPN_Pistol_01_Reload": 48, "A_WPN_Pistol_01_Empty": 1}
names = [a.name for a in bpy.data.actions]
for an, fe in want.items():
    acts = [a for a in bpy.data.actions if a.name.startswith(an)]
    rng = [tuple(round(x, 2) for x in a.frame_range) for a in acts]
    check(acts and all(abs(r[0]) < 1e-3 and abs(r[1] - fe) < 1e-3 for r in rng), f"{an} frames 0..{fe} ({rng})")
print(f"[PISTOL-BLENDER] actions: {names}")
print(f"[PISTOL-BLENDER] RESULT: {'PASS' if fails == 0 else 'FAIL'} ({fails} failures)")
sys.stdout.flush()
os._exit(0 if fails == 0 else 1)
