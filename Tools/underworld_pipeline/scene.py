"""Scene classification + geometry helpers (bpy)."""
import re
from contextlib import contextmanager

import bmesh
import bpy
from mathutils import Vector

# Godot 4 scene-import node-name hints (suffixes) we recognise.
GODOT_HINTS = ("-convcolonly", "-colonly", "-convcol", "-col", "-noimp", "-navmesh",
               "-occonly", "-occ", "-rigid", "-vehicle", "-wheel", "-loop", "-cycle")
COLLISION_ONLY_HINTS = ("-colonly", "-convcolonly")
COLLISION_HINTS = COLLISION_ONLY_HINTS + ("-col", "-convcol")
LOD_RE = re.compile(r"_LOD([0-9])$")
# PascalCase parts separated by "_" (parts may be digits / uppercase like LOD0, FL, 01, D)
NAME_RE = re.compile(r"^[A-Z0-9][A-Za-z0-9]*(_[A-Za-z0-9]+)*$")


def split_hint(name):
    for h in GODOT_HINTS:
        if name.endswith(h):
            return name[: -len(h)], h
    return name, None


def lod_level(name):
    base, _ = split_hint(name)
    m = LOD_RE.search(base)
    return int(m.group(1)) if m else 0


def is_collision(ob):
    _, h = split_hint(ob.name)
    return ob.type == "MESH" and (h in COLLISION_HINTS)


def is_collision_only(ob):
    _, h = split_hint(ob.name)
    return ob.type == "MESH" and h in COLLISION_ONLY_HINTS


def is_noimp(ob):
    return split_hint(ob.name)[1] == "-noimp"


def is_skinned(ob):
    return ob.type == "MESH" and any(m.type == "ARMATURE" and m.object for m in ob.modifiers)


def visible_meshes(scene, include_lods=False):
    out = []
    for ob in scene.objects:
        if ob.type != "MESH" or is_collision_only(ob) or is_noimp(ob):
            continue
        if not include_lods and lod_level(ob.name) > 0:
            continue
        out.append(ob)
    return out


def descendants(ob):
    out = []
    for c in ob.children:
        out.append(c)
        out.extend(descendants(c))
    return out


@contextmanager
def rest_pose(scene):
    """Evaluate skinned meshes in rest pose (bbox, tris)."""
    saved = []
    for ob in scene.objects:
        if ob.type == "ARMATURE":
            saved.append((ob.data, ob.data.pose_position))
            ob.data.pose_position = "REST"
    bpy.context.view_layer.update()
    try:
        yield
    finally:
        for arm, pp in saved:
            arm.pose_position = pp
        bpy.context.view_layer.update()


def evaluated_mesh_stats(ob, depsgraph, geometry=True):
    """Triangles, world bbox, and (optionally) topology problems of the evaluated mesh."""
    ev = ob.evaluated_get(depsgraph)
    me = ev.to_mesh()
    try:
        me.calc_loop_triangles()
        mw = ev.matrix_world
        st = {"triangles": len(me.loop_triangles), "vertices": len(me.vertices),
              "uv_layers": len(me.uv_layers), "bbox": None}
        if me.vertices:
            pts = [mw @ v.co for v in me.vertices]
            st["bbox"] = ([min(p[i] for p in pts) for i in range(3)],
                          [max(p[i] for p in pts) for i in range(3)])
        if geometry:
            bm = bmesh.new()
            bm.from_mesh(me)
            st["loose_vertices"] = sum(1 for v in bm.verts if not v.link_edges)
            st["loose_edges"] = sum(1 for e in bm.edges if not e.link_faces)
            st["non_manifold_edges"] = sum(1 for e in bm.edges if len(e.link_faces) > 2)
            st["boundary_edges"] = sum(1 for e in bm.edges if len(e.link_faces) == 1)
            st["non_manifold_vertices"] = sum(1 for v in bm.verts if v.link_edges and not v.is_manifold
                                              and not v.is_boundary)
            st["degenerate_faces"] = sum(1 for f in bm.faces if f.calc_area() < 1e-10)
            bm.free()
        return st
    finally:
        ev.to_mesh_clear()


def merge_bbox(boxes):
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    return ([min(b[0][i] for b in boxes) for i in range(3)], [max(b[1][i] for b in boxes) for i in range(3)])


def to_godot(v):
    """Blender (X, Y, Z) Z-up, front -Y  ->  Godot (X, Y, Z) Y-up, front +Z."""
    return [round(v[0], 4), round(v[2], 4), round(-v[1], 4)]


def bbox_godot(bb):
    lo, hi = bb
    a, b = to_godot(lo), to_godot(hi)
    mn = [min(a[i], b[i]) for i in range(3)]
    mx = [max(a[i], b[i]) for i in range(3)]
    return {"min": mn, "max": mx, "size": [round(mx[i] - mn[i], 4) for i in range(3)]}


def link_like(new_ob, ref_ob):
    cols = ref_ob.users_collection or [bpy.context.scene.collection]
    cols[0].objects.link(new_ob)


def material_images(mat):
    imgs = []
    if mat and mat.node_tree:
        for n in mat.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image:
                imgs.append(n.image)
    return imgs


def vec(v):
    return Vector(v)
