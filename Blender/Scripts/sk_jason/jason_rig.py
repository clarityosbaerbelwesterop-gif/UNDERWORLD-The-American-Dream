"""SK_Jason armature (Godot SkeletonProfileHumanoid names, REQ-GP01-JASON §3), skin weights, weapon socket."""
import bpy
from mathutils import Vector

# bone: (head, tail, parent) in the pre-scale authoring space (see jason_model.py), T-pose, faces -Y.
_L = {
    "Shoulder": ((0.030, 0.012, 1.440), (0.180, 0.012, 1.455), "UpperChest"),
    "UpperArm": ((0.180, 0.012, 1.455), (0.450, 0.012, 1.465), "Shoulder"),
    "LowerArm": ((0.450, 0.012, 1.465), (0.695, 0.008, 1.465), "UpperArm"),
    "Hand": ((0.695, 0.008, 1.465), (0.795, -0.004, 1.460), "LowerArm"),
    "UpperLeg": ((0.095, 0.004, 0.885), (0.095, -0.010, 0.520), "Hips"),
    "LowerLeg": ((0.095, -0.010, 0.520), (0.095, 0.000, 0.095), "UpperLeg"),
    "Foot": ((0.095, 0.000, 0.095), (0.095, -0.125, 0.045), "LowerLeg"),
    "Toes": ((0.095, -0.125, 0.045), (0.095, -0.195, 0.042), "Foot"),
}
BONES = {
    "Root": ((0, 0, 0), (0, 0, 0.20), None),
    "Hips": ((0, 0.005, 0.930), (0, 0.000, 1.040), "Root"),
    "Spine": ((0, 0.000, 1.040), (0, -0.002, 1.140), "Hips"),
    "Chest": ((0, -0.002, 1.140), (0, -0.006, 1.270), "Spine"),
    "UpperChest": ((0, -0.006, 1.270), (0, 0.004, 1.420), "Chest"),
    "Neck": ((0, 0.012, 1.500), (0, 0.010, 1.625), "UpperChest"),
    "Head": ((0, 0.010, 1.625), (0, 0.000, 1.800), "Neck"),
}


def _finger_bones():
    """Fingers follow the skin graph in jason_model (same coordinates)."""
    from jason_model import _body_graph
    nodes, _ = _body_graph()
    pos = {k: Vector(p) for k, p, _ in nodes}
    out = {}
    names = {"Index": ("Proximal", "Intermediate", "Distal"), "Middle": ("Proximal", "Intermediate", "Distal"),
             "Ring": ("Proximal", "Intermediate", "Distal"), "Little": ("Proximal", "Intermediate", "Distal"),
             "Thumb": ("Metacarpal", "Proximal", "Distal")}
    for f, segs in names.items():
        parent = "Hand"
        for i, seg in enumerate(segs):
            h, t = pos[f"L_{f}{i}"], pos[f"L_{f}{i + 1}"]
            out[f"{f}{seg}"] = (tuple(h), tuple(t), parent)
            parent = f"{f}{seg}"
    return out


def bone_table(k=1.0):
    tab = dict(BONES)
    left = dict(_L)
    left.update(_finger_bones())
    for side, sx in (("Left", 1), ("Right", -1)):
        for n, (h, t, p) in left.items():
            par = p if p in ("Hips", "UpperChest") else side + p
            tab[side + n] = ((h[0] * sx, h[1], h[2]), (t[0] * sx, t[1], t[2]), par)
    return {n: (tuple(c * k for c in h), tuple(c * k for c in t), p) for n, (h, t, p) in tab.items()}


def build_armature(root_obj, k):
    tab = bone_table(k)
    data = bpy.data.armatures.new("Armature")
    arm = bpy.data.objects.new("Armature", data)
    bpy.context.scene.collection.objects.link(arm)
    arm.parent = root_obj
    data.display_type = "STICK"
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for n, (h, t, p) in tab.items():
        eb = data.edit_bones.new(n)
        eb.head, eb.tail = h, t
    for n, (h, t, p) in tab.items():
        eb = data.edit_bones[n]
        if p:
            eb.parent = data.edit_bones[p]
            eb.use_connect = (Vector(data.edit_bones[p].tail) - Vector(h)).length < 1e-5
        if "Thumb" in n or n.endswith("Foot") or n.endswith("Toes"):
            eb.align_roll(Vector((0, 0, 1)))
        else:
            eb.align_roll(Vector((0, -1, 0)))
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def skin(arm, meshes, head_meshes, chest_meshes):
    """Bone-heat weights for body/collar, rigid weights for head parts and buttons,
    then limit to 4 influences, normalise, and fill any unweighted vertex from the nearest bone."""
    root = arm.data.bones["Root"]
    root.use_deform = False                      # keep Root weight-free (in-place root, REQ §4)
    for ob in meshes:
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    for ob, bone in [(o, "Head") for o in head_meshes] + [(o, "UpperChest") for o in chest_meshes]:
        ob.parent = arm
        ob.matrix_parent_inverse = arm.matrix_world.inverted()
        ob.modifiers.new("Armature", "ARMATURE").object = arm
        ob.vertex_groups.new(name=bone).add([v.index for v in ob.data.vertices], 1.0, "REPLACE")
    root.use_deform = True
    deform = [b for b in arm.data.bones if b.use_deform and b.name != "Root"]
    for ob in meshes:
        _fill_unweighted(ob, arm, deform)
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
        bpy.ops.object.vertex_group_clean(group_select_mode="ALL", limit=0.001)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
        _fill_unweighted(ob, arm, deform)


def _fill_unweighted(ob, arm, deform):
    names = {g.index: g.name for g in ob.vertex_groups}
    segs = [(b.name, Vector(b.head_local), Vector(b.tail_local)) for b in deform]
    miss = 0
    for v in ob.data.vertices:
        if sum(g.weight for g in v.groups if g.weight > 1e-4 and names.get(g.group) in {s[0] for s in segs}) > 1e-4:
            continue
        p = v.co
        best = min(segs, key=lambda s: _seg_dist(p, s[1], s[2]))
        g = ob.vertex_groups.get(best[0]) or ob.vertex_groups.new(name=best[0])
        names[g.index] = g.name
        g.add([v.index], 1.0, "REPLACE")
        miss += 1
    if miss:
        print(f"[JASON] {ob.name}: {miss} unweighted vertices filled from nearest bone")


def _seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
    return (a + ab * t - p).length
