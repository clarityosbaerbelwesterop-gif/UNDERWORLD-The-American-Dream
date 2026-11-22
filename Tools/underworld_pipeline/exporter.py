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


def _setup_studio_lighting(sc):
    """3-point studio lighting + neutral studio backdrop + floor for clean inspection renders."""
    created = []
    world = sc.world or bpy.data.worlds.new("UW_PreviewWorld")
    sc.world = world
    bg = world.node_tree.nodes.get("Background") if world.node_tree else None
    if bg:
        bg.inputs["Color"].default_value = (0.74, 0.74, 0.76, 1.0)
        bg.inputs["Strength"].default_value = 0.85

    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, -0.001))
    fl = bpy.context.active_object
    fl.name = "UW_StudioFloor"
    fmat = bpy.data.materials.new("UW_StudioFloorMat")
    bsdf = next(n for n in fmat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.76, 0.76, 0.78, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.92
    fl.data.materials.append(fmat)
    created.append(fl)

    for name, loc, tgt, energy, size, col in (
        ("UW_Key", (-1.8, -2.8, 2.5), (0, 0, 1.0), 175.0, 2.0, (1.0, 0.97, 0.94)),
        ("UW_Fill", (2.3, -2.0, 1.8), (0, 0, 1.0), 82.0, 2.5, (0.90, 0.94, 1.0)),
        ("UW_Rim", (0.5, 2.5, 2.3), (0, 0, 1.2), 110.0, 1.6, (1.0, 0.98, 0.95)),
    ):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        ld.color = col
        lo = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(lo)
        lo.location = Vector(loc)
        lo.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        created.append(lo)
    return created


def render_character_previews(ctx, out_dir, name, bbox):
    """Render studio Cycles CPU multi-view previews for Characters (front, 3/4, side, back, face, face_side, aim).

    Writes `<Name>_preview.png` (= 3/4 view for backwards compatibility) plus dedicated view PNGs.
    Returns dict {view_name: filepath}.
    """
    sc = bpy.context.scene
    for ob in sc.objects:
        if ob.type == "MESH" and (S.is_collision_only(ob) or S.lod_level(ob.name) > 0):
            ob.hide_render = True

    _setup_studio_lighting(sc)
    cam_data = bpy.data.cameras.new("UW_CharPreviewCam")
    cam = bpy.data.objects.new("UW_CharPreviewCam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam

    r = sc.render
    r.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 32
    sc.cycles.use_denoising = True
    r.resolution_percentage = 100
    r.image_settings.file_format = "PNG"
    r.film_transparent = False

    lo, hi = Vector(bbox[0]), Vector(bbox[1])
    h = max(hi.z - lo.z, 0.5)
    mid_z = 0.5 * (lo.z + hi.z)

    arm = next((o for o in sc.objects if o.type == "ARMATURE"), None)

    def set_action(exact_or_sub=None, frame=0, exclude=()):
        if not arm:
            return False
        if exact_or_sub is None:
            arm.data.pose_position = "REST"
            bpy.context.view_layer.update()
            return True
        act = next(
            (a for a in bpy.data.actions
             if exact_or_sub in a.name and not any(ex in a.name for ex in exclude)),
            None,
        )
        if act is None:
            return False
        arm.data.pose_position = "POSE"
        arm.animation_data_create()
        arm.animation_data.action = act
        if act.slots:
            arm.animation_data.action_slot = act.slots[0]
        sc.frame_set(frame)
        bpy.context.view_layer.update()
        return True

    def shoot(fpath, loc, tgt, lens=65, rx=512, ry=680):
        r.resolution_x, r.resolution_y = rx, ry
        cam_data.lens = lens
        cam.location = Vector(loc)
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        cam_data.clip_end = 50.0
        r.filepath = fpath
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        bpy.ops.render.render(write_still=True)
        return os.path.isfile(fpath)

    # Use standing Idle pose (explicitly excluding Aim/Crouch/Carry!) for concept-art turnaround match
    if not set_action("_Idle", 0, exclude=("Aim", "Crouch", "Carry")):
        set_action(None)

    # Frame head dynamically from actual posed Head bone so face close-up is always dead-center!
    head_z = hi.z - 0.135
    head_y = -0.02
    if arm and "Head" in arm.pose.bones:
        hb = arm.pose.bones["Head"]
        hc = arm.matrix_world @ ((hb.head + hb.tail) * 0.5)
        head_z = hc.z - 0.015
        head_y = hc.y - 0.02

    dist = h * 2.15
    views = {}
    specs = [
        ("front", f"{name}_preview_front.png", (0.0, -dist, mid_z + 0.02), (0.0, 0.0, mid_z), 65, 512, 680),
        ("3q", f"{name}_preview_3q.png", (-dist * 0.52, -dist * 0.87, mid_z + 0.06), (0.0, 0.0, mid_z), 65, 512, 680),
        ("side", f"{name}_preview_side.png", (-dist, 0.0, mid_z + 0.02), (0.0, 0.0, mid_z), 65, 512, 680),
        ("back", f"{name}_preview_back.png", (0.0, dist, mid_z + 0.02), (0.0, 0.0, mid_z), 65, 512, 680),
        ("face", f"{name}_preview_face.png", (0.0, head_y - 0.76, head_z + 0.01), (0.0, head_y, head_z), 95, 512, 512),
        ("face_side", f"{name}_preview_face_side.png", (-0.76, head_y, head_z + 0.01), (0.0, head_y, head_z), 95, 512, 512),
    ]
    for vkey, fname, loc, tgt, lens, rx, ry in specs:
        fp = os.path.join(out_dir, fname)
        if shoot(fp, loc, tgt, lens, rx, ry):
            views[vkey] = fp

    # Also copy 3/4 view to canonical <Name>_preview.png so legacy tools/manifests always find it!
    if "3q" in views:
        import shutil
        main_pv = os.path.join(out_dir, f"{name}_preview.png")
        shutil.copyfile(views["3q"], main_pv)
        views["default"] = main_pv

    # Aim pose preview if Aim action exists!
    if set_action("Aim_Pistol_Idle", 0) or set_action("_Aim", 0):
        fp_aim = os.path.join(out_dir, f"{name}_preview_aim.png")
        if shoot(fp_aim, (-dist * 0.55, -dist * 0.78, mid_z + 0.20), (0.0, -0.15, mid_z + 0.05), 62, 512, 680):
            views["aim"] = fp_aim

    set_action(None)
    return views


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
    sc.cycles.use_denoising = True
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
