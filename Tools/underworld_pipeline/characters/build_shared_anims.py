"""Build the shared 53-bone SkeletonProfileHumanoid animation library GLB (`A_Humanoid_Locomotion.glb`).

Exports the canonical 53-bone SkeletonProfileHumanoid armature + all 21 in-place 30 fps humanoid
animations (`A_Humanoid_*`) into `Assets/Characters/Shared/A_Humanoid_Locomotion.glb` (with manifest)
so every NPC sharing the SkeletonProfileHumanoid skeleton can play the full library without duplicating
animation tracks inside each character mesh.
"""
import argparse
import json
import os
import sys

import bpy
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
REPO_ROOT = os.path.abspath(os.path.join(TOOLS_DIR, ".."))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from underworld_pipeline import exporter as EXP  # noqa: E402
from underworld_pipeline.characters import animations as ANIM  # noqa: E402
from underworld_pipeline.characters import mh_loader as MH  # noqa: E402
from underworld_pipeline.characters import retarget as RETARGET  # noqa: E402


def build_shared_library(repo_root=REPO_ROOT, cache_dir=None):
    cache_dir = cache_dir or os.path.join(repo_root, ".cache", "uwp_sources")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.render.fps, sc.render.fps_base = ANIM.FPS, 1.0

    root = bpy.data.objects.new("A_Humanoid_Locomotion", None)
    sc.collection.objects.link(root)

    mh = MH.MakeHumanBase(cache_dir)
    mh.apply_macro({"gender": 1.0, "age": 0.55, "muscle": 0.55, "weight": 0.50})
    mh.finalize_scale(1.82, sole_extra_m=0.024)
    body, _ = mh.build_body_mesh("TmpBody")
    arm = mh.build_armature(root)
    body.parent = arm
    body.modifiers.new("Armature", "ARMATURE").object = arm
    MH.convert_apose_to_tpose(arm, [body])
    # Remove temporary mesh so the animation library GLB is ultra-lightweight (~300 KB, skeleton + 21 actions!)
    bpy.data.objects.remove(body, do_unlink=True)

    rig = ANIM.HumanoidRigSolver(arm)
    bvh_path = os.path.join(cache_dir, "mocap/makehuman_walk1.bvh")
    mocap_walk = RETARGET.extract_walk_mocap_profile(bvh_path) if os.path.isfile(bvh_path) else None
    clips, _ = ANIM.build_all_actions(rig, 1.0, prefix="A_Humanoid_", include_p2=True, mocap_walk=mocap_walk)

    out_dir = os.path.join(repo_root, "Assets", "Characters", "Shared")
    os.makedirs(out_dir, exist_ok=True)
    glb_path = os.path.join(out_dir, "A_Humanoid_Locomotion.glb")
    if not EXP.export_glb(glb_path):
        raise RuntimeError("Failed to export shared animation library GLB")

    # Manifest compatible with uw_post_import.gd (auto-sets all 21 loop modes on Godot import!)
    anims_man = []
    for nm, info in sorted(clips.items()):
        anims_man.append({
            "name": nm,
            "frame_start": 0.0,
            "frame_end": float(info["frames"]),
            "frames": info["frames"],
            "fps": float(ANIM.FPS),
            "duration_s": round(info["frames"] / ANIM.FPS, 4),
            "loop": bool(info["loop"]),
            "speed_mps": float(info["speed"]),
        })
    manifest = {
        "asset": "A_Humanoid_Locomotion",
        "status": "READY FOR REVIEW",
        "category": "Characters",
        "export_glb": "Assets/Characters/Shared/A_Humanoid_Locomotion.glb",
        "skeleton_profile": "SkeletonProfileHumanoid (53 bones, Root + 22 body + 30 fingers)",
        "mocap_source": mocap_walk,
        "animations": anims_man,
        "glb_bytes": os.path.getsize(glb_path),
    }
    with open(os.path.join(out_dir, "A_Humanoid_Locomotion.manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(f"[ANIMLIB] exported {glb_path} ({manifest['glb_bytes'] // 1024} KB, {len(anims_man)} clips)")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO_ROOT)
    a = ap.parse_args(argv)
    build_shared_library(a.repo)
    sys.stdout.flush()
    os._exit(0)
