"""RETIRED (Bot 1, 2026-11-22): SK_Jason v1 procedural builder - superseded by SK_Jason v2 (T-PIPE-03).

Running this would overwrite the v2 source Blender/Source/Characters/SK_Jason/SK_Jason.blend with the
v1 "stickman" build. It now refuses to run. Build Jason with the v2 spec-driven pipeline instead:

  /workspace/tools/blender/blender -b --factory-startup --python-exit-code 1 \\
      --python Tools/underworld_pipeline/characters/build_character.py -- --spec Config/Characters/SK_Jason.json

(see Docs/PIPELINE_CHARACTERS.md). The v1 code below is kept only for reference; set
UW_ALLOW_V1_JASON=1 to run it into a scratch location at your own risk.
"""
import os as _os
import sys as _sys

if _os.environ.get("UW_ALLOW_V1_JASON") != "1":
    _sys.stderr.write(
        "[build_sk_jason] RETIRED: SK_Jason v1 builder would overwrite SK_Jason v2. Use\n"
        "  blender -b --factory-startup --python Tools/underworld_pipeline/characters/build_character.py "
        "-- --spec Config/Characters/SK_Jason.json\n"
        "(Docs/PIPELINE_CHARACTERS.md).\n")
    _sys.exit(2)

"""Build SK_Jason (T-ART-01 + T-ART-02, Bot 2) fully procedurally and save the source .blend.

  /workspace/tools/blender/blender -b --factory-startup --python-exit-code 1 \\
      --python Blender/Scripts/sk_jason/build_sk_jason.py -- [--repo .] [--no-p2]

Writes Blender/Source/Characters/SK_Jason/SK_Jason.blend and
Assets/Characters/SK_Jason/SK_Jason.anim_report.json (clip lengths, speeds, measured foot sliding, socket).
Then export with:  Tools/uwp export Blender/Source/Characters/SK_Jason/SK_Jason.blend
Contract: Docs/Handoffs/REQ_SK_Jason_Controller.md (Bot 3, REQ-GP01-JASON), TD-004/005/006.
"""
import argparse
import json
import os
import sys
import time

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jason_anim as JA  # noqa: E402
import jason_model as JM  # noqa: E402
import jason_rig as JR  # noqa: E402

HEIGHT = 1.82  # m, Config/asset_budgets.json reference_heights_m.Jason


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.path.abspath(os.path.join(HERE, "..", "..", "..")))
    ap.add_argument("--no-p2", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.render.fps, sc.render.fps_base = JA.FPS, 1.0

    root = bpy.data.objects.new("SK_Jason", None)
    sc.collection.objects.link(root)
    parts = JM.build_all()
    top = max(v.co.z for o in parts.values() for v in o.data.vertices)
    k = HEIGHT / top
    for o in parts.values():
        o.data.transform(Matrix.Scale(k, 4))
    print(f"[JASON] modelled top={top:.4f} m -> scale k={k:.5f}")

    arm = JR.build_armature(root, k)
    JR.skin(arm, [parts["body"], parts["collar"]], [parts["head"], parts["hair"], parts["eyes"]], [parts["buttons"]])
    for o in parts.values():
        o.parent = arm
        o.matrix_parent_inverse = Matrix.Identity(4)

    rig = JA.Rig(arm)
    # weapon socket: identity orientation in the aim pose = Blender +Z up, -Y barrel
    #  = Godot +Y up, +Z barrel (REQ §3)
    aim = JA.idle_pose(rig, k, 0.0, aim=True)
    _, P = rig.pose_to_basis(aim)
    hand_rest = arm.data.bones["RightHand"].matrix_local
    hp = P["RightHand"]
    hdir = (hp.to_3x3() @ hand_rest.to_3x3().inverted() @ (Vector(arm.data.bones["RightHand"].tail_local) - Vector(arm.data.bones["RightHand"].head_local))).normalized()
    grip = hp.translation + hdir * 0.048 * k + Vector((1, 0, 0)) * 0.012 * k + Vector((0, 0, -0.02 * k))
    desired_aim = Matrix.Translation(grip)
    sock_rest = hand_rest @ hp.inverted() @ desired_aim
    sock = bpy.data.objects.new("SOCKET_RightHand_Weapon", None)
    sock.empty_display_type = "ARROWS"
    sock.empty_display_size = 0.08
    sc.collection.objects.link(sock)
    sock.parent = arm
    sock.parent_type = "BONE"
    sock.parent_bone = "RightHand"
    bpy.context.view_layer.update()
    sock.matrix_world = arm.matrix_world @ sock_rest
    bpy.context.view_layer.update()

    clips = JA.build_actions(rig, k, include_p2=not a.no_p2)
    sliding = {}
    for name, info in clips.items():
        if info["speed"] > 0:
            P_ = JA.GAITS.get(name) or JA.GAITS_P2.get(name)
            sl = JA.measure_sliding(rig, name, info["speed"], P_.get("dir", JA.FWD))
            info["foot_sliding_m"] = round(sl, 4)
            sliding[name] = sl
            print(f"[JASON] {name}: speed {info['speed']} m/s, cycle {info['frames']} f, sliding {sl * 100:.2f} cm, clamp {info['reach_clamp_m']}")
        info["length_s"] = round(info["frames"] / JA.FPS, 4)
    arm.animation_data.action = bpy.data.actions["A_Jason_Idle"]
    arm.animation_data.action_slot = bpy.data.actions["A_Jason_Idle"].slots[0]
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    sc.frame_start, sc.frame_end = 0, 60
    sc.frame_set(0)

    src = os.path.join(a.repo, "Blender", "Source", "Characters", "SK_Jason", "SK_Jason.blend")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=src, compress=True)
    out_dir = os.path.join(a.repo, "Assets", "Characters", "SK_Jason")
    os.makedirs(out_dir, exist_ok=True)
    tris = {}
    for n, o in parts.items():
        o.data.calc_loop_triangles()
        tris[o.name] = len(o.data.loop_triangles)
    sp = P["RightHand"]
    rep = {
        "asset": "SK_Jason", "status": "WIP (procedural v1, T-ART-01/02)", "height_m": HEIGHT, "scale_k": round(k, 5),
        "triangles": tris, "triangles_total": sum(tris.values()),
        "bones": [b.name for b in arm.data.bones], "bone_count": len(arm.data.bones),
        "rest_pose": "T-pose", "front": "Blender -Y = Godot +Z", "root_motion": "none (in place); Root bone has no keys",
        "fps": JA.FPS, "clips": clips,
        "socket": {"name": "SOCKET_RightHand_Weapon", "parent_bone": "RightHand",
                   "convention": "local +Y up, +Z barrel in Godot (= Blender local +Z up, -Y barrel); identity orientation in A_Jason_Aim_Pistol_Idle",
                   "aim_pose_position_godot": [round(grip.x, 4), round(grip.z, 4), round(-grip.y, 4)]},
        "max_foot_sliding_m": round(max(sliding.values()) if sliding else 0.0, 4),
        "build_seconds": round(time.time() - t0, 1),
    }
    with open(os.path.join(out_dir, "SK_Jason.anim_report.json"), "w") as f:
        json.dump(rep, f, indent=2)
        f.write("\n")
    print("[JASON] saved", src, "tris", rep["triangles_total"], "max sliding", rep["max_foot_sliding_m"], f"({rep['build_seconds']} s)")


main()
sys.stdout.flush()
os._exit(0)
