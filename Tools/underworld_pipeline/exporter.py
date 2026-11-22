"""glTF export, preview render, GLB inspection and Blender round-trip verification."""
import json
import math
import os
import struct

import bpy
from mathutils import Vector

from . import scene as S

GLTF_SETTINGS = dict(
    export_format="GLB",
    export_yup=True,                 # Blender Z-up -> glTF/Godot Y-up (TD-004)
    export_apply=True,               # apply modifiers (not the Armature modifier: skins are kept)
    export_materials="EXPORT",
    export_image_format="AUTO",      # embed textures (PNG/JPEG as authored)
    export_texcoords=True,
    export_normals=True,
    export_tangents=True,            # normal maps
    export_extras=True,              # custom props -> glTF extras (uw_lod, uw_visibility_range, ...)
    export_cameras=False,
    export_lights=False,
    export_animations=True,
    export_animation_mode="ACTIONS", # every action -> one glTF animation named like the action
    export_force_sampling=True,
    export_anim_slide_to_zero=True,  # first frame of every action at t=0 (clean loops in Godot)
    export_skins=True,
    export_influence_nb=4,
    export_def_bones=True,           # deform bones only in the Skeleton3D
    export_leaf_bone=False,
    export_morph=True,
    export_reset_pose_bones=True,
    export_rest_position_armature=True,
    use_active_scene=True,
)


def export_glb(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        os.remove(path)
    res = bpy.ops.export_scene.gltf(filepath=path, **GLTF_SETTINGS)
    return "FINISHED" in res and os.path.isfile(path)


def read_glb_json(path):
    with open(path, "rb") as f:
        data = f.read()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError(f"not a valid glTF 2.0 binary: {path}")
    clen, ctype = struct.unpack_from("<I4s", data, 12)
    if ctype != b"JSON":
        raise ValueError("first GLB chunk is not JSON")
    return json.loads(data[20:20 + clen])


def glb_summary(path):
    g = read_glb_json(path)
    nodes = g.get("nodes", [])
    return {
        "nodes": [n.get("name") for n in nodes],
        "node_extras": {n.get("name"): n["extras"] for n in nodes if "extras" in n},
        "meshes": len(g.get("meshes", [])),
        "materials": [m.get("name") for m in g.get("materials", [])],
        "images": len(g.get("images", [])),
        "skins": [{"name": s.get("name"), "joints": len(s.get("joints", []))} for s in g.get("skins", [])],
        "joint_names": sorted({nodes[j].get("name") for s in g.get("skins", []) for j in s.get("joints", [])}),
        "animations": [a.get("name") for a in g.get("animations", [])],
        "asset_generator": g.get("asset", {}).get("generator"),
        "bytes": os.path.getsize(path),
    }


def render_preview(ctx, path, bbox):
    """Cycles CPU 3/4 front view (front = Blender -Y). LOD>0 and collision hidden."""
    sc = bpy.context.scene
    pv = ctx.cfg.get("preview") or {}
    for ob in sc.objects:
        if ob.type == "MESH" and (S.is_collision_only(ob) or S.lod_level(ob.name) > 0):
            ob.hide_render = True
    lo, hi = Vector(bbox[0]), Vector(bbox[1])
    centre = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 0.05)
    cam_data = bpy.data.cameras.new("UW_PreviewCam")
    cam_data.lens = 50
    cam = bpy.data.objects.new("UW_PreviewCam", cam_data)
    sc.collection.objects.link(cam)
    direction = Vector((0.75, -1.0, 0.55)).normalized()
    fov = 2 * math.atan(cam_data.sensor_width / (2 * cam_data.lens))
    dist = radius / math.sin(fov / 2) * 1.1
    cam.location = centre + direction * dist
    cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    cam_data.clip_end = dist * 10
    sc.camera = cam
    sun_d = bpy.data.lights.new("UW_PreviewSun", "SUN")
    sun_d.energy = 3.0
    sun = bpy.data.objects.new("UW_PreviewSun", sun_d)
    sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    sc.collection.objects.link(sun)
    world = sc.world or bpy.data.worlds.new("UW_PreviewWorld")
    sc.world = world
    bg = world.node_tree.nodes.get("Background") if world.node_tree else None
    if bg:
        bg.inputs["Color"].default_value = (0.35, 0.33, 0.3, 1)
        bg.inputs["Strength"].default_value = 0.8
    r = sc.render
    r.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = int(pv.get("samples", 16))
    sc.cycles.use_denoising = False
    r.resolution_x = r.resolution_y = int(pv.get("resolution", 320))
    r.resolution_percentage = 100
    r.image_settings.file_format = "PNG"
    r.film_transparent = False
    r.filepath = path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.render.render(write_still=True)
    return os.path.isfile(path)


def verify_roundtrip(glb, expected):
    """Re-import the .glb into an empty scene and compare against what was exported.

    expected: {"nodes": [...], "animations": [...], "lod_nodes": [...], "collision_nodes": [...],
               "armatures": n}
    Returns (ok, details). Destroys the current scene (call last).
    """
    problems = []
    summ = glb_summary(glb)
    names = set(summ["nodes"])
    for n in expected["nodes"]:
        if n not in names:
            problems.append(f"node '{n}' missing in glb")
    for a in expected["animations"]:
        if a not in summ["animations"]:
            problems.append(f"animation '{a}' missing in glb")
    for n in expected["lod_nodes"] + expected["collision_nodes"]:
        if n not in names:
            problems.append(f"generated node '{n}' missing in glb")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    objs = {o.name: o.type for o in bpy.data.objects}
    for n in expected["nodes"]:
        if n not in objs:
            problems.append(f"object '{n}' missing after Blender re-import")
    arms = [n for n, t in objs.items() if t == "ARMATURE"]
    if len(arms) != expected["armatures"]:
        problems.append(f"re-import armatures {len(arms)} != {expected['armatures']}")
    if len(bpy.data.actions) < len(expected["animations"]):
        problems.append(f"re-import actions {len(bpy.data.actions)} < {len(expected['animations'])}")
    details = {"glb": summ, "reimport_objects": sorted(objs), "reimport_actions": sorted(a.name for a in bpy.data.actions),
               "problems": problems}
    return not problems, details
