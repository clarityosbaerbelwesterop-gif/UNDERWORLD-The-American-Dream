"""Procedurally build the T-PIPE-01 test assets (bpy, headless).

  blender -b --factory-startup --python tests/make_test_assets.py -- --out-dir /tmp/uwp_test/src

Writes (all PT_ = pipeline test placeholders, never ship):
  PT_UWP_Barrel.blend   static prop: 2 meshes (bevel modifier unapplied), packed 256² texture, socket, NO collision
  PT_UWP_RigTest.blend  skinned tube on a 3-bone armature, socket on a bone, 2 actions (one cyclic)
  PT_UWP_Humanoid.blend      humanoid skeleton (REQ-GP01-JASON names), faces -Y (valid as Characters)
  PT_UWP_HumanoidBack.blend  same, faces +Y -> FRONT_AXIS error
  PT_UWP_Broken.blend   deliberately broken asset (naming, transforms, UVs, materials, loose geo,
                        tri budget, ground offset, 2048² texture, 5 bone influences, bad action name)
"""
import argparse
import math
import os
import sys

import bpy

EXPECTED_BROKEN_CODES = ["ROOT_MISSING", "OUTSIDE_ROOT", "NAME_OBJECT", "TRANSFORM_SCALE", "NO_UVS", "NO_MATERIAL",
                         "LOOSE_GEOMETRY", "TRI_BUDGET", "ORIGIN_GROUND", "NAME_MATERIAL", "TEXTURE_SIZE",
                         "BONE_INFLUENCES", "NAME_ACTION"]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = "METRIC"
    s.unit_settings.scale_length = 1.0
    s.render.fps = 30
    s.render.fps_base = 1.0


def material(name, rgba, image=None):
    m = bpy.data.materials.new(name)
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.7
    if image is not None:
        tex = m.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = image
        m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def packed_image(name, size):
    img = bpy.data.images.new(name, size, size, alpha=False)
    px = [0.0] * (size * size * 4)
    for y in range(size):
        for x in range(size):
            i = (y * size + x) * 4
            v = 0.25 + 0.5 * (((x // 16) + (y // 16)) % 2)
            px[i:i + 4] = (v, v * 0.6, v * 0.3, 1.0)
    img.pixels = px
    img.pack()
    return img


def root_empty(name):
    r = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(r)
    return r


def finish(ob, name, parent):
    ob.name = name
    ob.data.name = name
    ob.parent = parent


def apply_transforms(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def make_barrel(path):
    reset()
    name = "PT_UWP_Barrel"
    root = root_empty(name)
    img = packed_image("T_PT_UWP_Barrel_D", 256)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.3, depth=0.9, location=(0, 0, 0.45))
    body = bpy.context.active_object
    bev = body.modifiers.new("Bevel", "BEVEL")  # left unapplied on purpose: exporter applies it
    bev.width = 0.02
    bev.segments = 2
    body.data.materials.append(material("M_PT_UWP_Barrel_Metal", (0.2, 0.35, 0.6, 1), img))
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.27, depth=0.04, location=(0, 0, 0.92))
    lid = bpy.context.active_object
    lid.data.materials.append(material("M_PT_UWP_Barrel_Lid", (0.1, 0.1, 0.1, 1)))
    finish(body, "SM_PT_UWP_Barrel_Body", root)
    finish(lid, "SM_PT_UWP_Barrel_Lid", root)
    bpy.ops.object.select_all(action="DESELECT")
    for o in (body, lid):
        o.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    sock = bpy.data.objects.new("SOCKET_Top", None)
    bpy.context.scene.collection.objects.link(sock)
    sock.location = (0, 0, 0.94)
    sock.parent = root
    bpy.ops.wm.save_as_mainfile(filepath=path)


def weight_tube(mesh_ob, bones, height):
    """Linear blend between the two nearest bones along Z (max 2 influences)."""
    groups = [mesh_ob.vertex_groups.new(name=b) for b in bones]
    seg = height / len(bones)
    for v in mesh_ob.data.vertices:
        t = max(0.0, min(len(bones) - 1.0, v.co.z / seg - 0.5))
        i = int(math.floor(t))
        f = t - i
        groups[i].add([v.index], 1.0 - f, "REPLACE")
        if i + 1 < len(bones) and f > 1e-4:
            groups[i + 1].add([v.index], f, "REPLACE")


def add_action(arm, name, keys, frame_end, cyclic):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    for frame, rots in keys:
        for bone, (x, y, z) in rots.items():
            pb = arm.pose.bones[bone]
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = (x, y, z)
            pb.keyframe_insert("rotation_euler", frame=frame, group=bone)
    act.use_frame_range = True
    act.frame_start, act.frame_end = 1, frame_end
    act.use_cyclic = cyclic
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
    return act


def make_armature(name, parent, bones, height):
    data = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(arm)
    arm.parent = parent
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    seg = height / len(bones)
    prev = None
    for i, b in enumerate(bones):
        eb = data.edit_bones.new(b)
        eb.head = (0, 0, i * seg)
        eb.tail = (0, 0, (i + 1) * seg)
        if prev:
            eb.parent = prev
            eb.use_connect = True
        prev = eb
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def make_rig(path):
    reset()
    name = "PT_UWP_RigTest"
    root = root_empty(name)
    bones = ["Base", "Mid", "Tip"]
    h = 1.5
    arm = make_armature("Armature", root, bones, h)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.12, depth=h, location=(0, 0, h / 2))
    tube = bpy.context.active_object
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    # horizontal loop cuts so the tube can bend
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(tube.data)
    side = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1e-4]
    bmesh.ops.subdivide_edges(bm, edges=side, cuts=11, use_grid_fill=True)
    bm.to_mesh(tube.data)
    bm.free()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    tube.data.materials.append(material("M_PT_UWP_Rig", (0.8, 0.5, 0.1, 1)))
    tube.name = tube.data.name = "SK_PT_UWP_RigTest_Tube"
    tube.parent = arm
    mod = tube.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    weight_tube(tube, bones, h)
    sock = bpy.data.objects.new("SOCKET_Tip", None)
    bpy.context.scene.collection.objects.link(sock)
    sock.parent = arm
    sock.parent_type = "BONE"
    sock.parent_bone = "Tip"
    sock.location = (0, 0, 0)  # at bone tail
    r = math.radians
    add_action(arm, "A_PT_UWP_RigTest_Twist", [(1, {"Base": (0, 0, 0)}), (16, {"Base": (0, 0, r(90))})], 16, False)
    add_action(arm, "A_PT_UWP_RigTest_Bend",
               [(1, {"Mid": (0, 0, 0), "Tip": (0, 0, 0)}), (16, {"Mid": (r(35), 0, 0), "Tip": (r(45), 0, 0)}),
                (31, {"Mid": (0, 0, 0), "Tip": (0, 0, 0)})], 31, True)
    arm.animation_data.action = bpy.data.actions["A_PT_UWP_RigTest_Bend"]
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=path)


def make_broken(path):
    reset()
    # no root named PT_UWP_Broken -> ROOT_MISSING / OUTSIDE_ROOT
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=6, radius=0.5, location=(0, 0, 2.0))  # ~20k tris, floating above ground
    s = bpy.context.active_object
    s.name = "bad name"
    s.scale = (2, 2, 2)                                   # unapplied scale
    while s.data.uv_layers:
        s.data.uv_layers.remove(s.data.uv_layers[0])     # no UVs, no material
    s.data.vertices.add(3)                               # loose vertices
    for v in s.data.vertices[-3:]:
        v.co = (0.5, 0.5, 0.6)
    bpy.ops.mesh.primitive_cube_add(size=0.5, location=(2, 0, 0.6))  # floating: ORIGIN_GROUND
    c = bpy.context.active_object
    c.name = "SM_Broken_Box"
    c.data.materials.append(material("Material", (1, 1, 1, 1), packed_image("T_Broken_Big_D", 2048)))
    arm = make_armature("Armature", None, ["B1", "B2", "B3", "B4", "B5"], 0.5)
    arm.location = (2, 0, 0)
    for b in ["B1", "B2", "B3", "B4", "B5"]:
        g = c.vertex_groups.new(name=b)
        g.add([v.index for v in c.data.vertices], 0.2, "REPLACE")   # 5 influences everywhere
    c.modifiers.new("Armature", "ARMATURE").object = arm
    act = bpy.data.actions.new("Wave")
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    arm.pose.bones["B1"].keyframe_insert("rotation_quaternion", frame=1)
    act2 = bpy.data.actions.new("A_PT_UWP_Broken_Jump_loop")   # TD-005 addendum: loop suffix -> NAME_ACTION_LOOP
    act2.use_fake_user = True
    arm.animation_data.action = act2
    arm.pose.bones["B1"].keyframe_insert("rotation_quaternion", frame=1)
    arm.animation_data.action = act
    bpy.ops.wm.save_as_mainfile(filepath=path)


HUMANOID = {  # bone: (head, tail, parent)  T-pose, facing Blender -Y, left side at +X
    "Hips": ((0, 0, 0.95), (0, 0, 1.05), None), "Spine": ((0, 0, 1.05), (0, 0, 1.18), "Hips"),
    "Chest": ((0, 0, 1.18), (0, 0, 1.30), "Spine"), "UpperChest": ((0, 0, 1.30), (0, 0, 1.42), "Chest"),
    "Neck": ((0, 0, 1.42), (0, 0, 1.52), "UpperChest"), "Head": ((0, 0, 1.52), (0, 0, 1.75), "Neck"),
    "LeftShoulder": ((0.03, 0, 1.40), (0.18, 0, 1.40), "UpperChest"), "LeftUpperArm": ((0.18, 0, 1.40), (0.46, 0, 1.40), "LeftShoulder"),
    "LeftLowerArm": ((0.46, 0, 1.40), (0.72, 0, 1.40), "LeftUpperArm"), "LeftHand": ((0.72, 0, 1.40), (0.82, 0, 1.40), "LeftLowerArm"),
    "LeftUpperLeg": ((0.10, 0, 0.95), (0.10, 0, 0.52), "Hips"), "LeftLowerLeg": ((0.10, 0, 0.52), (0.10, 0, 0.08), "LeftUpperLeg"),
    "LeftFoot": ((0.10, 0, 0.08), (0.10, -0.12, 0.02), "LeftLowerLeg"), "LeftToes": ((0.10, -0.12, 0.02), (0.10, -0.18, 0.02), "LeftFoot"),
}
for _k, (_h, _t, _p) in list(HUMANOID.items()):
    if _k.startswith("Left"):
        HUMANOID["Right" + _k[4:]] = ((-_h[0], _h[1], _h[2]), (-_t[0], _t[1], _t[2]), _p and _p.replace("Left", "Right"))


def make_humanoid(path, name, facing_back=False):
    """Minimal humanoid skeleton (REQ-GP01-JASON bone names) + a box skinned to Hips.
    facing_back=True mirrors Y (character faces +Y) -> must fail FRONT_AXIS."""
    reset()
    root = root_empty(name)
    data = bpy.data.armatures.new("Armature")
    arm = bpy.data.objects.new("Armature", data)
    bpy.context.scene.collection.objects.link(arm)
    arm.parent = root
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    fy = -1 if facing_back else 1
    for b, (h, t, p) in HUMANOID.items():
        eb = data.edit_bones.new(b)
        eb.head = (h[0] * fy, h[1] * fy, h[2])
        eb.tail = (t[0] * fy, t[1] * fy, t[2])
    for b, (h, t, p) in HUMANOID.items():
        if p:
            data.edit_bones[b].parent = data.edit_bones[p]
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.mesh.primitive_cube_add(size=0.3, location=(0, 0, 0.15))
    box = bpy.context.active_object
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    box.name = box.data.name = f"SK_{name}_Body"
    box.data.materials.append(material(f"M_{name}", (0.5, 0.5, 0.5, 1)))
    box.parent = arm
    box.modifiers.new("Armature", "ARMATURE").object = arm
    box.vertex_groups.new(name="Hips").add([v.index for v in box.data.vertices], 1.0, "REPLACE")
    bpy.ops.wm.save_as_mainfile(filepath=path)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    make_barrel(os.path.join(a.out_dir, "PT_UWP_Barrel.blend"))
    make_rig(os.path.join(a.out_dir, "PT_UWP_RigTest.blend"))
    make_broken(os.path.join(a.out_dir, "PT_UWP_Broken.blend"))
    make_humanoid(os.path.join(a.out_dir, "PT_UWP_Humanoid.blend"), "PT_UWP_Humanoid")
    make_humanoid(os.path.join(a.out_dir, "PT_UWP_HumanoidBack.blend"), "PT_UWP_HumanoidBack", facing_back=True)
    print("[TEST] assets written to", a.out_dir)
    sys.stdout.flush()
    os._exit(0)
