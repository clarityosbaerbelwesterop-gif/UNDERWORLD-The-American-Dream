"""Hard-surface modelling helpers for spec-driven weapons (T-ART-03 pistol quality pass, Bot 2).

Every part is authored from 2D profiles that are extruded, boolean-cut and bevelled. The same code builds the
bake source (hp=True: round multi-segment bevels, serrations, pins, engraving) and the game mesh (hp=False:
same silhouette, 1-segment chamfers, triangulated, hard edges split in UV) so the high-to-low bake lines up.
Coordinates: metres, Blender axes (barrel -Y, up +Z, gun's left side +X).
Ported/extended from the superseded bot2 pistol prototype (backup: /workspace/bot2_old_pistol_backup).
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

LP_SHARP_DEG = 30   # game mesh hard edges; unwrap splits UV islands at the same angle


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def obj_from_bm(name, bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


def chaikin(pts, it=2, closed=True):
    """Chaikin corner cutting (rounds every corner of a polyline)."""
    pts = [Vector(p) for p in pts]
    for _ in range(it):
        n = len(pts)
        out = [] if closed else [pts[0]]
        for i in range(n if closed else n - 1):
            p, q = pts[i], pts[(i + 1) % n]
            out += [p.lerp(q, 0.25), p.lerp(q, 0.75)]
        if not closed:
            out.append(pts[-1])
        pts = out
    return [tuple(p) for p in pts]


def prism(name, poly, axis, lo, hi):
    """Closed 2D polygon extruded along axis ('X': poly in (y,z); 'Y': poly in (x,z); 'Z': poly in (x,y))."""
    bm = bmesh.new()
    rings = []
    for d in (lo, hi):
        ring = []
        for a, b in poly:
            co = (d, a, b) if axis == "X" else ((a, d, b) if axis == "Y" else (a, b, d))
            ring.append(bm.verts.new(co))
        rings.append(ring)
    n = len(poly)
    for i in range(n):
        bm.faces.new((rings[0][i], rings[0][(i + 1) % n], rings[1][(i + 1) % n], rings[1][i]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[1])
    return obj_from_bm(name, bm)


def box(name, x0, x1, y0, y1, z0, z1):
    return prism(name, [(y0, z0), (y1, z0), (y1, z1), (y0, z1)], "X", x0, x1)


def cyl(name, r, axis, a0, a1, c1, c2, seg=24):
    """Cylinder along axis from a0 to a1; (c1, c2) = centre in the other two axes (X: y,z; Y: x,z; Z: x,y)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=abs(a1 - a0))
    mid = (a0 + a1) / 2
    if axis == "Y":
        bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(math.radians(90), 3, "X"))
        bmesh.ops.translate(bm, verts=bm.verts, vec=(c1, mid, c2))
    elif axis == "X":
        bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
        bmesh.ops.translate(bm, verts=bm.verts, vec=(mid, c1, c2))
    else:
        bmesh.ops.translate(bm, verts=bm.verts, vec=(c1, c2, mid))
    return obj_from_bm(name, bm)


def halfspace(name, point, normal, size=0.5):
    """Cutter filling the half-space on the +normal side of the plane through point."""
    n = Vector(normal).normalized()
    ob = box(name, -size / 2, size / 2, -size / 2, size / 2, 0.0, size)
    ob.matrix_world = Matrix.Translation(Vector(point)) @ n.to_track_quat("Z", "Y").to_matrix().to_4x4()
    return ob


def plane_yz(name, p0, p1, outward):
    """Half-space cutter bounded by the line p0-p1 in the YZ plane (any x); outward=(y,z) hint of the removed side."""
    d = Vector((0, p1[0] - p0[0], p1[1] - p0[1])).normalized()
    n = Vector((0, -d.z, d.y))
    if n.y * outward[0] + n.z * outward[1] < 0:
        n = -n
    return halfspace(name, (0, p0[0], p0[1]), n)


def sweep(name, centre, thick, half_w):
    """Rectangular band along an open YZ centre line (trigger, guard)."""
    pts = [Vector(p) for p in centre]
    bm = bmesh.new()
    rows = []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        t = (b - a).normalized()
        nrm = Vector((-t.y, t.x))
        row = []
        for x in (-half_w, half_w):
            for s in (-1, 1):
                q = p + nrm * (s * thick / 2)
                row.append(bm.verts.new((x, q.x, q.y)))
        rows.append(row)
    quad_idx = [(0, 1), (1, 3), (3, 2), (2, 0)]
    for r0, r1 in zip(rows, rows[1:]):
        for i, j in quad_idx:
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new((rows[0][0], rows[0][2], rows[0][3], rows[0][1]))
    bm.faces.new((rows[-1][1], rows[-1][3], rows[-1][2], rows[-1][0]))
    return obj_from_bm(name, bm)


def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
    ob.modifiers.clear()
    old = ob.data
    ob.data = me
    bpy.data.meshes.remove(old)
    return ob


def apply_loc(ob):
    ob.data.transform(ob.matrix_basis)
    ob.matrix_basis = Matrix.Identity(4)
    return ob


def boolean(target, cutters, op="DIFFERENCE"):
    """Exact boolean with each cutter in turn (cutters are deleted)."""
    for c in cutters:
        apply_loc(c)
        m = target.modifiers.new("Bool", "BOOLEAN")
        m.object, m.operation, m.solver = c, op, "EXACT"
        apply_mods(target)
        bpy.data.objects.remove(c)
    return target


def cut_batch(target, cutters):
    """Join many small cutters into one object first (fast for serrations/slots)."""
    if not cutters:
        return target
    for c in cutters:
        apply_loc(c)
    c = join(cutters, "c_batch")
    return boolean(target, [c])


def bevel(ob, width, segs, angle=40, profile=0.5, harden=False):
    m = ob.modifiers.new("Bevel", "BEVEL")
    m.width, m.segments, m.limit_method = width, segs, "ANGLE"
    m.angle_limit = math.radians(angle)
    m.profile = profile
    m.harden_normals = harden
    m.miter_outer = "MITER_ARC"
    m.use_clamp_overlap = True
    return apply_mods(ob)


def set_mat(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    return ob


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name, ob.data.name = name, name
    return ob


def engraving(text, x, y, z, size, depth=0.0004, side=1):
    """Text cutter on a side face (normal +X for side=1, -X for side=-1), reading front-to-back."""
    cd = bpy.data.curves.new("txt", "FONT")
    cd.body = text
    cd.size = size
    cd.extrude = depth
    cd.align_x, cd.align_y = "CENTER", "CENTER"
    t = link(bpy.data.objects.new("txt", cd))
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(t.evaluated_get(dg), depsgraph=dg)
    bpy.data.objects.remove(t)
    ob = link(bpy.data.objects.new("c_txt", me))
    if side > 0:   # text X -> +Y? reads muzzle->rear seen from +X means text X -> -(-Y) ... local X -> +Y
        rot = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    else:
        rot = Matrix(((0, 0, -1, 0), (-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    ob.matrix_world = Matrix.Translation((x, y, z)) @ rot
    return ob


def finish(ob, hp):
    """Clean topology; game mesh is triangulated (identical triangulation for bake + glTF) with hard edges."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-6)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if not hp:
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="BEAUTY")
        flat = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(1.0) < math.radians(0.5)]
        bmesh.ops.beautify_fill(bm, faces=list({f for e in flat for f in e.link_faces}), edges=flat)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges)
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(ob.data)
    bm.free()
    for p in ob.data.polygons:
        p.use_smooth = True
    ob.data.set_sharp_from_angle(angle=math.radians(LP_SHARP_DEG if not hp else 50))
    if hp:   # face-area weighted normals keep big flat faces flat next to rounded bevels
        m = ob.modifiers.new("WN", "WEIGHTED_NORMAL")
        m.mode, m.keep_sharp, m.weight = "FACE_AREA", True, 100
        apply_mods(ob)
    else:    # seams on hard edges so the tangent-space bake has no smoothing seams
        for e in ob.data.edges:
            e.use_seam = e.use_edge_sharp
    return ob
