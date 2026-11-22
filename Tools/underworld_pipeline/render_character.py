"""Render a built character .blend to PNG turntable/portrait sheets (Cycles CPU, headless).

This is the visual acceptance tool the project has been missing: the build sandbox has no GPU,
but Cycles renders on the CPU, so every asset can be looked at instead of only being validated
by node/triangle counts.

  blender -b --factory-startup --python-exit-code 5 \
      --python Tools/underworld_pipeline/render_character.py -- \
      --blend Blender/Source/Characters/SK_Jason/SK_Jason.blend \
      --out Docs/ArtDirection/Renders/SK_Jason --views portrait,face,three_quarter,full \
      --size 640 --samples 64

Outputs `<out>/<view>.png` plus `render.json` with engine/samples/time so a reviewer can tell
exactly how the image was produced (no claim of "final" quality without it).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import bpy
from mathutils import Euler, Vector

#: Calibrated studio exposure. At light_scale = 0.22 the rendered sRGB of a mid-grey sphere
#: matches its albedo 1:1 (measured: albedo 0.80 -> sRGB 0.813), so material colours in the
#: preview are trustworthy instead of a filmic reinterpretation of them.
STUDIO_LIGHT_SCALE = 0.22
STUDIO_WORLD_STRENGTH = 0.22

VIEWS = {
    # name -> (camera offset from the target in metres, target height, lens mm, framing)
    "portrait": ((0.0, -1.05, 0.02), "head", 85),
    # 100 mm at 0.52 m frames only 0.19 m of height on a square sensor: that cropped the mouth
    # out of every face preview. 85 mm at 0.78 m frames ~0.33 m, i.e. the whole head with the
    # neck line in shot - what a face-inspection render needs to be.
    "face": ((0.0, -0.78, 0.01), "eyes", 85),
    "three_quarter": ((0.62, -0.80, 0.06), "head", 85),
    "profile": ((1.05, -0.10, 0.02), "head", 85),
    "full": ((0.0, -4.4, 0.10), "pelvis", 70),
    "full_back": ((0.0, 4.4, 0.10), "pelvis", 70),
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--views", default="portrait,three_quarter,full,face")
    ap.add_argument("--size", type=int, default=640)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--exposure", type=float, default=0.0)
    ap.add_argument("--rest-pose", action="store_true", help="render the T-pose rest instead of Idle")
    ap.add_argument("--view-transform", default="Standard",
                    help="Standard = albedo-faithful technical render (default); AgX = filmic look")
    ap.add_argument("--light-scale", type=float, default=STUDIO_LIGHT_SCALE,
                    help="multiplier on the studio rig; 0.22 reproduces albedo 1:1 (calibrated)")
    return ap.parse_args(argv)


def clear_lights_and_cameras():
    for ob in list(bpy.data.objects):
        if ob.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(ob, do_unlink=True)


def area_light(name, loc, rot, energy, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.size = size
    ob = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def studio(light_scale=STUDIO_LIGHT_SCALE, world_strength=STUDIO_WORLD_STRENGTH):
    """Three-point key/fill/rim setup + neutral grey world (matches Docs/ArtDirection lighting)."""
    clear_lights_and_cameras()
    area_light("Key", (1.5, -2.0, 2.3), (math.radians(55), math.radians(8), math.radians(38)),
               420 * light_scale, 1.6)
    area_light("Fill", (-2.1, -1.4, 1.7), (math.radians(70), math.radians(-10), math.radians(-58)),
               130 * light_scale, 2.2)
    area_light("Rim", (-0.5, 2.2, 2.1), (math.radians(65), 0.0, math.radians(192)),
               300 * light_scale, 1.2)

    world = bpy.data.worlds.new("RenderWorld")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.19, 0.20, 0.22, 1.0)
    bg.inputs[1].default_value = world_strength
    bpy.context.scene.world = world


def character_bounds():
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        for corner in ob.bound_box:
            w = ob.matrix_world @ Vector(corner)
            lo = Vector((min(lo.x, w.x), min(lo.y, w.y), min(lo.z, w.z)))
            hi = Vector((max(hi.x, w.x), max(hi.y, w.y), max(hi.z, w.z)))
    return lo, hi


def make_camera(target_height, lens):
    cam_data = bpy.data.cameras.new("RenderCam")
    cam_data.lens = lens
    cam = bpy.data.objects.new("RenderCam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    target = bpy.data.objects.new("CamTarget", None)
    bpy.context.scene.collection.objects.link(target)
    bpy.context.scene.camera = cam
    return cam, target


def main():
    args = parse_args()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(args.blend))
    sc = bpy.context.scene

    lo, hi = character_bounds()
    height = hi.z - lo.z
    head_z = lo.z + height * 0.935
    # The eye anchor sat at 0.940 of body height, i.e. on the brow ridge, so the "face" framing
    # (100 mm lens, 0.52 m away, ~24 cm frame height) cropped the mouth and filled the frame with
    # forehead + nose. Measured on SK_NPC_Sam: eyes 1.653..1.681 m of 1.793 m body = 0.930, so the
    # anchor goes on the eye line (human adults: eyes at ~93 % of stature).
    eyes_z = lo.z + height * 0.930
    pelvis_z = lo.z + height * 0.52
    anchor = {"head": Vector((0.0, 0.0, head_z)),
              "eyes": Vector((0.0, 0.0, eyes_z)),
              "pelvis": Vector((0.0, 0.0, pelvis_z))}

    studio(args.light_scale)
    # Pose the rig with the character's own Idle clip at frame 0 (arms down) unless --rest-pose.
    for ob in bpy.data.objects:
        if ob.type != "ARMATURE":
            continue
        act = None
        if not args.rest_pose:
            prefix = ob.name.replace("SK_", "")
            idle = [a for a in bpy.data.actions if a.name.endswith("_Idle")]
            plain = [a for a in idle
                     if not any(k in a.name for k in ("Aim", "Crouch", "Carry"))]
            act = (plain or idle or [None])[0]
        if act is not None:
            ob.animation_data_create()
            ob.animation_data.action = act
            if getattr(act, "slots", None):
                try:
                    ob.animation_data.action_slot = act.slots[0]
                except Exception:
                    pass
            sc.frame_set(0)
            ob.data.pose_position = "POSE"
            print(f"[RENDER] posed with action {act.name}")
        else:
            ob.data.pose_position = "REST"

    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = args.samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.render.resolution_x = args.size
    sc.render.resolution_y = args.size
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = args.view_transform
    sc.view_settings.exposure = args.exposure

    os.makedirs(args.out, exist_ok=True)
    report = {"blend": os.path.abspath(args.blend), "engine": "CYCLES/CPU",
              "samples": args.samples, "size": args.size, "views": {},
              "view_transform": args.view_transform, "light_scale": args.light_scale,
              "exposure": args.exposure}

    for view in [v.strip() for v in args.views.split(",") if v.strip()]:
        if view not in VIEWS:
            print(f"[RENDER] unknown view {view}, skipping")
            continue
        offset, anchor_key, lens = VIEWS[view]
        cam, target = make_camera(anchor_key, lens)
        pos = anchor[anchor_key]
        target.location = pos + Vector((0.0, 0.0, 0.0))
        cam.location = pos + Vector(offset)
        con = cam.constraints.new("TRACK_TO")
        con.target = target
        con.track_axis = "TRACK_NEGATIVE_Z"
        con.up_axis = "UP_Y"
        bpy.context.view_layer.update()

        path = os.path.join(args.out, f"{view}.png")
        sc.render.filepath = path
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        dt = round(time.time() - t0, 1)
        report["views"][view] = {"file": path, "seconds": dt}
        print(f"[RENDER] {view} -> {path} ({dt}s)")
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.objects.remove(target, do_unlink=True)

    report["bounds_m"] = {"min": [round(v, 4) for v in lo], "max": [round(v, 4) for v in hi],
                          "height": round(height, 4)}
    with open(os.path.join(args.out, "render.json"), "w") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    print("[RENDER] DONE", json.dumps(report["views"]))


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    os._exit(0)
