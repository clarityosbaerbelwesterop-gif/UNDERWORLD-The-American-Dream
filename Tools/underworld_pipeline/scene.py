"""Scene classification + geometry helpers (bpy)."""
import math
import re
from contextlib import contextmanager

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

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


def uv_overlap_ratio(ob, grid=256):
    """Estimate fraction of covered UV area that overlaps itself using exact barycentric rasterization.

    Returns (overlap_fraction in [0..1], covered_uv_fraction in [0..1]).
    Fast O(N_tris) on a 256x256 grid; ignores shared triangle edges cleanly via strict interior test.
    """
    me = ob.data
    if not me.uv_layers or not me.polygons:
        return 0.0, 0.0
    me.calc_loop_triangles()
    uv_data = me.uv_layers.active.data
    hits = np.zeros((grid, grid), dtype=np.int32)
    scale = grid - 1

    for lt in me.loop_triangles:
        u0, v0 = uv_data[lt.loops[0]].uv
        u1, v1 = uv_data[lt.loops[1]].uv
        u2, v2 = uv_data[lt.loops[2]].uv
        x0, y0 = u0 * scale, v0 * scale
        x1, y1 = u1 * scale, v1 * scale
        x2, y2 = u2 * scale, v2 * scale
        denom = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(denom) < 1e-4:
            continue
        ix0 = max(0, int(math.floor(min(x0, x1, x2))))
        ix1 = min(grid - 1, int(math.ceil(max(x0, x1, x2))))
        iy0 = max(0, int(math.floor(min(y0, y1, y2))))
        iy1 = min(grid - 1, int(math.ceil(max(y0, y1, y2))))
        if ix1 <= ix0 or iy1 <= iy0:
            continue
        # Sample pixel centers (ix + 0.5, iy + 0.5)
        xs = np.arange(ix0, ix1 + 1, dtype=np.float32) + 0.5
        ys = np.arange(iy0, iy1 + 1, dtype=np.float32) + 0.5
        gx, gy = np.meshgrid(xs, ys)
        inv = 1.0 / denom
        a = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) * inv
        b = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) * inv
        c = 1.0 - a - b
        # Strict interior (> 0.01) avoids double-counting shared edges between adjacent polygons
        inside = (a > 0.01) & (b > 0.01) & (c > 0.01)
        if inside.any():
            hits[iy0:iy1 + 1, ix0:ix1 + 1] += inside

    covered = int((hits > 0).sum())
    if covered == 0:
        return 0.0, 0.0
    overlapped = int((hits > 1).sum())
    return round(overlapped / covered, 4), round(covered / (grid * grid), 4)


def texel_density_stats(ob):
    """Compute median texel density (pixels per metre) on `ob` using its largest image texture."""
    me = ob.data
    if not me.uv_layers or not me.polygons:
        return None
    tex_dim = 0
    for s in ob.material_slots:
        if s.material:
            for img in material_images(s.material):
                tex_dim = max(tex_dim, img.size[0], img.size[1])
    if tex_dim == 0:
        return None
    me.calc_loop_triangles()
    uv_data = me.uv_layers.active.data
    mw = ob.matrix_world
    densities = []
    for lt in me.loop_triangles:
        p0 = mw @ me.vertices[lt.vertices[0]].co
        p1 = mw @ me.vertices[lt.vertices[1]].co
        p2 = mw @ me.vertices[lt.vertices[2]].co
        w_area = 0.5 * (p1 - p0).cross(p2 - p0).length
        if w_area < 1e-8:
            continue
        u0, v0 = uv_data[lt.loops[0]].uv
        u1, v1 = uv_data[lt.loops[1]].uv
        u2, v2 = uv_data[lt.loops[2]].uv
        uv_area = 0.5 * abs((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0))
        if uv_area < 1e-10:
            continue
        densities.append(math.sqrt(uv_area * tex_dim * tex_dim / w_area))
    if not densities:
        return None
    arr = np.array(densities, dtype=np.float64)
    return {
        "texture_px": tex_dim,
        "median_px_per_m": round(float(np.median(arr)), 1),
        "p10_px_per_m": round(float(np.percentile(arr, 10)), 1),
        "p90_px_per_m": round(float(np.percentile(arr, 90)), 1),
    }


def check_layered_clipping(scene, depsgraph, max_probe_m=0.014, poke_thresh_m=0.0025):
    """Check whether inner layered character meshes poke through outer clothing shells (rest pose).

    Pairs checked automatically by naming convention:
      *_Body vs (*_TShirt, *_Jeans, *_Boots, *_Jacket)
      *_TShirt vs *_Jacket
    Only evaluates inner vertices whose nearest point on the outer shell is an INTERIOR (non-boundary)
    triangle of the outer mesh within `max_probe_m` so open necklines/cuffs/open-front jacket edges
    never cause false positives!
    """
    meshes = {o.name: o for o in visible_meshes(scene)}
    body = next((o for n, o in meshes.items() if n.endswith("_Body")), None)
    tshirt = next((o for n, o in meshes.items() if n.endswith("_TShirt")), None)
    jacket = next((o for n, o in meshes.items() if n.endswith("_Jacket")), None)
    jeans = next((o for n, o in meshes.items() if n.endswith("_Jeans")), None)
    boots = next((o for n, o in meshes.items() if n.endswith("_Boots")), None)

    pairs = []
    for outer in (tshirt, jeans, boots, jacket):
        if body and outer:
            pairs.append((body, outer))
    if tshirt and jacket:
        pairs.append((tshirt, jacket))

    results = []
    for inner, outer in pairs:
        # Identify outer boundary faces (within 1 edge of open garment borders like collar/cuff/open-front)
        bm_o = bmesh.new()
        bm_o.from_mesh(outer.data)
        b_verts = {v.index for v in bm_o.verts if v.is_boundary}
        # Expand boundary ring by 2 hops to exclude turned-in hem/lapel/collar rims (inward-facing rim quads)
        b_verts2 = set(b_verts)
        for _ in range(2):
            nxt = set(b_verts2)
            for v in bm_o.verts:
                if v.index in b_verts2:
                    for e in v.link_edges:
                        nxt.add(e.other_vert(v).index)
            b_verts2 = nxt
        border_faces = {f.index for f in bm_o.faces if any(v.index in b_verts2 for v in f.verts)}
        bm_o.free()

        bvh = BVHTree.FromObject(outer, depsgraph)
        mw_i = inner.matrix_world
        mw_o_inv = outer.matrix_world.inverted()
        tested = 0
        clipped = 0
        for v in inner.data.vertices:
            p_local_o = mw_o_inv @ (mw_i @ v.co)
            loc, nrm, face_idx, dist = bvh.find_nearest(p_local_o)
            if loc is None or dist > max_probe_m or face_idx in border_faces:
                continue
            tested += 1
            # Positive dot with outward normal of outer garment means inner mesh poked OUTSIDE the outer layer!
            if (p_local_o - loc).dot(nrm) > poke_thresh_m:
                clipped += 1
        frac = round(clipped / max(tested, 1), 4)
        results.append({
            "inner": inner.name,
            "outer": outer.name,
            "tested_vertices": tested,
            "clipped_vertices": clipped,
            "clipped_fraction": frac,
        })
    return results

