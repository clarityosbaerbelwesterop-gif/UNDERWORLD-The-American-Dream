"""WPN_Pistol_01 geometry (Bot 2). Every part is built twice from the same profiles:
hp=True  -> bake source: rounder bevels, serrations, roll-mark engraving, pins, sight dots (several materials)
hp=False -> game mesh: same silhouette with chamfers + weighted normals, everything small baked into maps.
Modelling coordinates: barrel along -Y, up +Z, gun's LEFT side = +X (shooter behind the gun facing -Y),
units metres; build_wpn_pistol_01.py moves the grip point to the origin afterwards.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

RAKE = math.radians(18)
LP_SHARP_DEG = 20      # game mesh hard edges; build unwrap splits UV islands at the same angle
SH = math.tan(RAKE)          # grip shear: y += -z * SH (bottom further back)


# ----------------------------------------------------------------------------- helpers
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
    """Chaikin corner cutting (rounds every corner)."""
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


def prism(name, poly, axis, lo, hi, shear=0.0):
    """Closed 2D polygon extruded along axis ('X': poly in (y,z); 'Y': poly in (x,z); 'Z': poly in (x,y))."""
    bm = bmesh.new()
    rings = []
    for d in (lo, hi):
        ring = []
        for a, b in poly:
            if axis == "X":
                co = (d, a - b * shear, b)
            elif axis == "Y":
                co = (a, d, b)
            else:
                co = (a, b, d)
            ring.append(bm.verts.new(co))
        rings.append(ring)
    n = len(poly)
    for i in range(n):
        bm.faces.new((rings[0][i], rings[0][(i + 1) % n], rings[1][(i + 1) % n], rings[1][i]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[1])
    return obj_from_bm(name, bm)


def support_loops(ob, cuts):
    """Subdivide the edges running along Y (inserts loops across the part)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    ed = [e for e in bm.edges if abs((e.verts[0].co - e.verts[1].co).normalized().y) > 0.99]
    bmesh.ops.subdivide_edges(bm, edges=ed, cuts=cuts, use_grid_fill=True)
    bm.to_mesh(ob.data)
    bm.free()


def plane_cut(py, pz, deg):
    """Cutter removing everything in front of (y < py) a plane through (py, pz) tilted by deg about X:
    deg < 0 -> cuts above the pivot (top chamfer), deg > 0 -> cuts below it (bottom recedes)."""
    c = box("c_plane", -0.05, 0.05, py - 0.05, py, pz - 0.05, pz + 0.05)
    c.matrix_world = Matrix.Translation((0, py, pz)) @ Matrix.Rotation(math.radians(deg), 4, "X") @ Matrix.Translation((0, -py, -pz))
    return c


def box(name, x0, x1, y0, y1, z0, z1, shear=0.0):
    return prism(name, [(y0, z0), (y1, z0), (y1, z1), (y0, z1)], "X", x0, x1, shear)


def cyl(name, r, axis, a0, a1, c1, c2, seg=24):
    """Cylinder along axis from a0 to a1; (c1, c2) = centre in the other two axes (X: y,z; Y: x,z)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=abs(a1 - a0))
    if axis == "Y":
        bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(math.radians(90), 3, "X"))
        bmesh.ops.translate(bm, verts=bm.verts, vec=(c1, (a0 + a1) / 2, c2))
    else:
        bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
        bmesh.ops.translate(bm, verts=bm.verts, vec=((a0 + a1) / 2, c1, c2))
    return obj_from_bm(name, bm)


def sweep(name, centre, thick, half_w, samples=1):
    """Rectangular band along an open YZ centre line (trigger guard / trigger)."""
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
        rows.append(row)   # order: (-w,in) (-w,out) (+w,in) (+w,out)
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


def cut(target, cutters, op="DIFFERENCE"):
    for c in cutters:
        m = target.modifiers.new("Bool", "BOOLEAN")
        m.object, m.operation, m.solver = c, op, "EXACT"
        apply_mods(target)
        bpy.data.objects.remove(c)
    return target


def bevel(ob, width, segs, angle=40, harden=False, profile=0.5):
    m = ob.modifiers.new("Bevel", "BEVEL")
    m.width, m.segments, m.limit_method = width, segs, "ANGLE"
    m.angle_limit = math.radians(angle)
    m.profile = profile
    m.harden_normals = harden
    m.miter_outer = "MITER_ARC"
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


def finish(ob, hp):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-6)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    for p in ob.data.polygons:
        p.use_smooth = True
    # game mesh: hard edges above 35 deg (UV islands are split at the same angle, see build unwrap);
    # caps are triangulated now so bake and glTF export use the identical triangulation
    if not hp:
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="BEAUTY")
        # flip diagonals inside flat regions so no long slivers remain (they shade as dark lines)
        flat = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(1.0) < math.radians(0.5)]
        bmesh.ops.beautify_fill(bm, faces=list({f for e in flat for f in e.link_faces}), edges=flat)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="BEAUTY")
        bm.to_mesh(ob.data)
        bm.free()
    ob.data.set_sharp_from_angle(angle=math.radians(LP_SHARP_DEG if not hp else 50))
    if hp:   # bake source: face-area weighted normals keep big flat faces flat next to rounded bevels
        m = ob.modifiers.new("WN", "WEIGHTED_NORMAL")
        m.mode, m.keep_sharp, m.weight = "FACE_AREA", True, 100
        apply_mods(ob)
    return ob


# ----------------------------------------------------------------------------- parts
def slide(hp, M):
    seg = 3 if hp else 1
    # cross-section: flat sides, 45-degree top chamfers (the slide's signature line)
    sec = [(-0.0128, 0.020), (0.0128, 0.020), (0.0128, 0.0470), (0.0090, 0.0540), (-0.0090, 0.0540), (-0.0128, 0.0470)]
    s = prism("Slide_body", sec, "Y", -0.150, 0.028)
    cutters = []
    # nose: top-front chamfer and bottom-front chamfer
    cutters.append(plane_cut(-0.1500, 0.0475, -45))     # top-front chamfer
    cutters.append(plane_cut(-0.1500, 0.0230, 35))      # bottom-front relief
    # ejection port on the RIGHT side (-X) reaching over the top (real pistols eject right)
    cutters.append(box("c_port", -0.03, 0.0035, -0.046, -0.015, 0.0385, 0.07))
    # muzzle recess
    cutters.append(cyl("c_muz", 0.0074, "Y", -0.152, -0.147, 0.0, 0.0365, 32 if hp else 20))
    # spring guide hole
    cutters.append(cyl("c_guide", 0.0030, "Y", -0.152, -0.146, 0.0, 0.0245, 16 if hp else 10))
    if hp:
        # rear cocking serrations (8 per side) and front serrations (5 per side), slightly raked
        for sx in (1, -1):
            for i in range(8):
                c = box("c_ser", -0.0012, 0.0012, -0.0007, 0.0007, 0.0225, 0.0470)
                c.matrix_world = Matrix.Translation((sx * 0.0134, 0.0035 + i * 0.0031, 0)) @ Matrix.Rotation(math.radians(-8), 4, "X")
                cutters.append(c)
            for i in range(5):
                c = box("c_ser", -0.0012, 0.0012, -0.0006, 0.0006, 0.0260, 0.0470)
                c.matrix_world = Matrix.Translation((sx * 0.0134, -0.1405 + i * 0.0028, 0)) @ Matrix.Rotation(math.radians(-8), 4, "X")
                cutters.append(c)
        # roll mark engraving on the left side (+X)
        cutters.append(engraving("UW-17   9x19", 0.0128, -0.070, 0.0300, 0.0042))
        cutters.append(engraving("UNDERWORLD ARMS", 0.0128, -0.118, 0.0405, 0.0024))
    cut(s, cutters)
    s = bevel(s, 0.0007 if hp else 0.0006, seg, angle=30)
    parts = [set_mat(s, M["steel"])]
    # barrel: hood visible in the port, muzzle crown in front
    hood = box("Hood", -0.0090, 0.0090, -0.046, -0.013, 0.0275, 0.0505)
    hood = bevel(hood, 0.0006, seg)
    parts.append(set_mat(hood, M["barrel"]))
    br = cyl("Barrel", 0.0068, "Y", -0.1492, -0.120, 0.0, 0.0365, 32 if hp else 20)
    cut(br, [cyl("c_bore", 0.0046, "Y", -0.153, -0.125, 0.0, 0.0365, 24 if hp else 12)])
    br = bevel(br, 0.0004, seg, angle=50)
    parts.append(set_mat(br, M["barrel"]))
    # extractor on the right (port) side
    ex = box("Extractor", -0.0134, -0.0122, -0.0150, 0.0030, 0.0405, 0.0455)
    parts.append(set_mat(bevel(ex, 0.0003, seg), M["steel"]))
    # sights (dovetailed steel, white dots)
    fs = prism("FrontSight", [(-0.146, 0.0535), (-0.139, 0.0535), (-0.1405, 0.0598), (-0.1445, 0.0598)], "X", -0.0017, 0.0017)
    parts.append(set_mat(bevel(fs, 0.0003, seg), M["steel"]))
    rs = prism("RearSight", [(0.016, 0.0535), (0.026, 0.0535), (0.026, 0.0598), (0.0185, 0.0608)], "X", -0.0095, 0.0095)
    cut(rs, [box("c_notch", -0.0019, 0.0019, 0.0, 0.04, 0.0565, 0.07)])
    parts.append(set_mat(bevel(rs, 0.0004, seg), M["steel"]))
    if hp:
        parts.append(set_mat(cyl("Dot_F", 0.0009, "Y", -0.1396, -0.1388, 0.0, 0.0573, 16), M["white"]))
        for sx in (1, -1):
            parts.append(set_mat(cyl("Dot_R", 0.0009, "Y", 0.0259, 0.0266, sx * 0.0058, 0.0577, 16), M["white"]))
    return parts


def engraving(text, x, y, z, size):
    cd = bpy.data.curves.new("txt", "FONT")
    cd.body = text
    cd.size = size
    cd.extrude = 0.0004
    cd.align_x, cd.align_y = "CENTER", "CENTER"
    t = link(bpy.data.objects.new("txt", cd))
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(t.evaluated_get(dg), depsgraph=dg)
    bpy.data.objects.remove(t)
    ob = link(bpy.data.objects.new("c_txt", me))
    # text plane XY (normal +Z) -> side plane: local X -> +Y (reads front-to-back seen from +X), Y -> +Z, Z -> +X
    rot = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    ob.matrix_world = Matrix.Translation((x - 0.0001, y, z)) @ rot
    ob.data.transform(Matrix.Identity(4))
    return ob


def frame(hp, M):
    seg = 3 if hp else 1
    parts = []
    # dust cover / upper frame
    dc = box("DustCover", -0.0118, 0.0118, -0.136, 0.024, -0.0045, 0.0205)
    support_loops(dc, 8)    # supporting loops: no long sliver triangles on the flat sides after the nose cut
    cut(dc, [plane_cut(-0.136, 0.0205, 12)])
    dc = bevel(dc, 0.0012 if hp else 0.0010, seg + 1, angle=35)
    parts.append(set_mat(dc, M["polymer"]))
    # front nose of the dust cover (angled)
    rail = box("Rail", -0.0090, 0.0090, -0.132, -0.092, -0.0085, -0.0035)
    if hp:
        cut(rail, [box("c_slot", -0.02, 0.02, -0.124 + i * 0.011, -0.120 + i * 0.011, -0.0095, -0.0062) for i in range(4)])
    parts.append(set_mat(bevel(rail, 0.0005, seg), M["polymer"]))
    # grip: raked side profile with finger-groove front strap, palm swell and beavertail
    front = []
    for i in range(13):
        t = i / 12.0
        z = -0.004 + t * (-0.0640)
        y = -0.0060 - 0.0016 * math.sin(math.pi * 3 * t) ** 2 * (1 if 0.05 < t < 0.95 else 0)
        front.append((y, z))
    back = []
    for i in range(10):
        t = i / 9.0
        z = -0.068 + t * 0.066
        y = 0.0380 + 0.0022 * math.sin(math.pi * t)       # palm swell
        back.append((y, z))
    beaver = [(0.0405, 0.0040), (0.0445, 0.0090), (0.0445, 0.0140), (0.0400, 0.0185), (0.0300, 0.0205)]
    prof = front + [(0.0, -0.0705), (0.0300, -0.0705)] + back + beaver + [(-0.0060, 0.0205)]
    prof = chaikin(prof, 2 if hp else 1)
    g = prism("Grip", prof, "X", -0.0142, 0.0142, shear=SH)
    # magazine well (bottom opening, flared) and grip relief under the guard
    well = prism("c_well", [(0.0015, -0.090), (0.0310, -0.090), (0.0310, -0.040), (0.0015, -0.040)], "X", -0.0106, 0.0106, shear=SH)
    flare = prism("c_flare", [(-0.0010, -0.090), (0.0335, -0.090), (0.0315, -0.0665), (0.0010, -0.0665)], "X", -0.0120, 0.0120, shear=SH)
    cut(g, [well, flare])
    g = bevel(g, 0.0055 if hp else 0.0050, 5 if hp else 2, angle=50, profile=0.6)
    parts.append(set_mat(g, M["stipple"] if hp else M["polymer"]))
    # trigger guard (squared front, undercut where it meets the grip)
    gc = [(-0.0065, -0.0040), (-0.0080, -0.0170), (-0.0200, -0.0265), (-0.0450, -0.0285), (-0.0620, -0.0270),
          (-0.0690, -0.0200), (-0.0700, -0.0080), (-0.0695, 0.0010)]
    gc = chaikin(gc, 3 if hp else 2, closed=False)
    tg = sweep("Guard", gc, 0.0042, 0.0060)
    parts.append(set_mat(bevel(tg, 0.0010 if hp else 0.0008, seg + 1, angle=35), M["polymer"]))
    # trigger with safety blade
    tc = chaikin([(-0.0255, 0.0080), (-0.0270, -0.0010), (-0.0300, -0.0090), (-0.0340, -0.0150)], 2, closed=False)
    tr = sweep("Trigger", tc, 0.0042, 0.0030)
    parts.append(set_mat(bevel(tr, 0.0008, seg, angle=35), M["polymer"]))
    if hp:
        sb = sweep("Safety", chaikin([(-0.0285, 0.0010), (-0.0305, -0.0060), (-0.0335, -0.0120)], 2, closed=False), 0.0030, 0.0009)
        sb.location.y -= 0.0012
        apply_loc(sb)
        parts.append(set_mat(bevel(sb, 0.0003, 2), M["polymer"]))
    # controls on the LEFT side (+X): slide stop with thumb tab, magazine release; takedown lever both sides
    ss = prism("SlideStop", [(-0.046, 0.0080), (-0.014, 0.0080), (-0.012, 0.0125), (-0.020, 0.0150), (-0.030, 0.0130), (-0.046, 0.0125)],
               "X", 0.0116, 0.0133)
    parts.append(set_mat(bevel(ss, 0.0004, seg), M["steel"]))
    for sx in (1, -1):
        td = box("Takedown", min(sx * 0.0116, sx * 0.0128), max(sx * 0.0116, sx * 0.0128), -0.064, -0.056, 0.0080, 0.0135)
        parts.append(set_mat(bevel(td, 0.0003, seg), M["steel"]))
    mr = box("MagRelease", 0.0128, 0.0150, -0.0105, -0.0035, -0.0140, -0.0050)
    parts.append(set_mat(bevel(mr, 0.0007, seg + 1), M["polymer"]))
    if hp:
        for (y, z) in ((-0.040, 0.0030), (-0.0190, 0.0040), (0.0080, 0.0120)):
            parts.append(set_mat(cyl("Pin", 0.0013, "X", -0.0121, 0.0121, y, z, 20), M["steel"]))
    return parts


def apply_loc(ob):
    ob.data.transform(ob.matrix_basis)
    ob.matrix_basis = Matrix.Identity(4)


def magazine(hp, M):
    seg = 3 if hp else 1
    body = prism("MagBody", [(0.0020, -0.0700), (0.0295, -0.0700), (0.0295, -0.0050), (0.0040, -0.0020), (0.0020, -0.0050)],
                 "X", -0.0098, 0.0098, shear=SH)
    body = bevel(body, 0.0008, seg)
    plate = prism("MagPlate", chaikin([(-0.0030, -0.0765), (0.0345, -0.0765), (0.0335, -0.0700), (-0.0015, -0.0700), (-0.0045, -0.0725)], 1),
                  "X", -0.0125, 0.0125, shear=SH)
    plate = bevel(plate, 0.0015 if hp else 0.0012, seg + 1, angle=40)
    return [set_mat(body, M["magsteel"]), set_mat(plate, M["polymer"])]
