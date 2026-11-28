"""Real (non-placeholder) facial detail geometry built directly on the morphed hm08 surface.

The production `.mhclo` packs for eyebrows / eyelashes / teeth ship in the MakeHuman *system
asset* archives, which are unreachable from the build sandbox and whose GitHub mirrors are
either AGPL or LFS-pointer only (see Docs/ASSET_LICENSES.md). Instead of shipping a stand-in,
this module derives the geometry from the character itself:

  * **Eyebrows** - ~700 individually modelled hair cards. Each card is planted on the actual
    brow surface (found by ray-casting the morphed head from in front), oriented along the
    local brow flow and arched over the brow ridge, so the brow follows the morphs exactly.
    The card UVs point at one cell of a procedural single-strand atlas.
  * **Eyelashes** - cards planted on the upper lid rim of each eye, curling outward/upward.
  * **Teeth** - two dental arches (upper + lower) as elliptical lofted tooth boxes behind the
    lips; the lower arch carries a `jawOpen` blendshape so it opens with the jaw.

Everything is skinned to the head (brows, lashes) or the jaw, so the details deform with
`Head` / `Jaw` exactly like the face does.
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

# --------------------------------------------------------------------------------------
# surface helpers
# --------------------------------------------------------------------------------------


def _head_bvh(body_ob):
    """BVH of the head region of the (already morphed) body mesh, in object space."""
    me = body_ob.data
    verts = [v.co.copy() for v in me.vertices]
    polys = [list(p.vertices) for p in me.polygons]
    return BVHTree.FromPolygons(verts, polys, all_triangles=False)


def _ray_front(bvh, x: float, z: float, y_start: float = -0.45) -> tuple[Vector, Vector] | None:
    """Cast from in front of the face (+/- along -Y) onto the surface; return (hit, normal)."""
    origin = Vector((x, y_start, z))
    direction = Vector((0.0, 1.0, 0.0))
    hit, normal, _idx, _dist = bvh.ray_cast(origin, direction, 0.6)
    if hit is None:
        return None
    if normal.y > 0.0:            # ensure the normal points out of the face (-Y = front)
        normal = -normal
    return hit, normal.normalized()


def _card(bm, uv_layer, origin, tangent, normal, length, width, arch=0.0012,
          uv_cell=(0.0, 0.0, 1.0, 1.0)):
    """One tapered 2-segment hair card (4 verts -> 2 quads) with per-cell atlas UVs."""
    side = normal.cross(tangent).normalized()
    flow = tangent - normal * tangent.dot(normal)
    if flow.length < 1e-6:
        flow = Vector((1.0, 0.0, 0.0))
    flow.normalize()
    u0, v0, u1, v1 = uv_cell
    rings = []
    for s in range(3):
        t = s / 2.0
        lift = arch * math.sin(math.pi * t ** 0.7)
        w = 0.5 * width * (1.0 - 0.72 * t ** 1.4)
        centre = origin + flow * (length * t) + normal * lift
        rings.append((bm.verts.new(centre - side * w), bm.verts.new(centre + side * w), t))
    for s in range(2):
        vl0, vr0, t0 = rings[s]
        vl1, vr1, t1 = rings[s + 1]
        f = bm.faces.new((vl0, vr0, vr1, vl1))
        f.smooth = True
        tv0 = v0 + (v1 - v0) * t0
        tv1 = v0 + (v1 - v0) * t1
        for loop, uv in zip(f.loops, [(u0, tv0), (u1, tv0), (u1, tv1), (u0, tv1)]):
            loop[uv_layer].uv = uv


def _finish(bm, name, origin=Vector((0, 0, 0))):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.location = origin
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _skin_to_head(ob, body_ob, bone="Head"):
    """Bind helper geometry rigidly to one bone (brows/lashes ride the head exactly)."""
    vg = ob.vertex_groups.new(name=bone)
    vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")


# --------------------------------------------------------------------------------------
# eyebrows
# --------------------------------------------------------------------------------------

#: atlas layout used by the brow material (must match build_brow_cards' UVs)
BROW_ATLAS_COLS, BROW_ATLAS_ROWS = 16, 16


def build_brows(body_ob, lm, obj_name, card_count=1050, width_m=0.0030, length_m=0.0058,
                seed=17):
    """Plant real hair cards on the brow ridge of the morphed head."""
    bvh = _head_bvh(body_ob)
    rng = np.random.default_rng(seed)
    eye_z = lm["eye_z"]
    brow_z = lm["brow_z"]
    face_h = lm["face_h"]
    eye_x = abs(lm["eye_l"].x)

    import bmesh
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    planted = 0
    attempts = 0
    # The brow band used to start at eye_z + face_h * 0.026 and rise to brow_z + face_h * 0.020,
    # which put the cards up to ~1.5 cm above the visible brow ridge: they rendered as thick black
    # arches floating on the forehead, above the real (skin-textured) brow. Keep the band on the
    # ridge: it must not start below the lid crease and must not overshoot brow_z by more than a
    # few millimetres.
    band_bottom = eye_z + face_h * 0.016
    band_top = brow_z + face_h * 0.006
    while planted < card_count and attempts < card_count * 40:
        attempts += 1
        sign = 1.0 if rng.random() < 0.5 else -1.0
        t = rng.random() ** 1.25                     # denser toward the inner third
        x = sign * (eye_x * 0.22 + t * 0.0360)
        # Arched brow line: rises towards the outer third, drops at the tail
        arch = math.exp(-(((t - 0.62) / 0.62) ** 2))
        z = band_bottom + (band_top - band_bottom) * (0.16 + 0.70 * arch) + rng.normal(0.0, 0.0007)
        hit = _ray_front(bvh, x, z)
        if hit is None:
            continue
        pos, nrm = hit
        # Brow hairs grow outward (away from the nose) and slightly upward; tail hairs lie flatter.
        flow_x = sign * (0.92 - 0.55 * t)
        flow_z = 0.34 + 0.42 * arch
        tangent = Vector((flow_x, 0.0, flow_z)).normalized()
        roll = rng.normal(0.0, 0.16)
        ca, sa = math.cos(roll), math.sin(roll)
        tangent = Vector((tangent.x * ca - tangent.z * sa, tangent.y,
                          tangent.x * sa + tangent.z * ca)).normalized()
        ln = length_m * rng.uniform(0.75, 1.25)
        wd = width_m * rng.uniform(0.75, 1.20)
        cell = int(rng.integers(0, BROW_ATLAS_COLS * BROW_ATLAS_ROWS))
        cx = (cell % BROW_ATLAS_COLS) / BROW_ATLAS_COLS + 0.004
        cy = (cell // BROW_ATLAS_COLS) / BROW_ATLAS_ROWS + 0.004
        du = 1.0 / BROW_ATLAS_COLS - 0.008
        dv = 1.0 / BROW_ATLAS_ROWS - 0.008
        _card(bm, uv_layer, pos + nrm * 0.0002, tangent, nrm, ln, wd,
              arch=0.00045, uv_cell=(cx, cy, cx + du, cy + dv))
        planted += 1
    ob = _finish(bm, obj_name)
    ob["uw_allow_uv_overlap"] = True     # stacked hair cards intentionally share atlas cells
    _skin_to_head(ob, body_ob)
    print(f"[FACE] brow cards: {planted} planted on the brow ridge ({attempts} ray casts)")
    return ob


# --------------------------------------------------------------------------------------
# eyelashes
# --------------------------------------------------------------------------------------

LASH_ATLAS_COLS, LASH_ATLAS_ROWS = 8, 8


def build_lashes(body_ob, lm, obj_name_left, obj_name_right, card_count=48, seed=23):
    """Plant lash cards along the upper lid rim (they curl up and outwards)."""
    bvh = _head_bvh(body_ob)
    rng = np.random.default_rng(seed)
    eye_z = lm["eye_z"]
    lids = {"L": lm["eye_l"], "R": lm["eye_r"]}
    out = []
    for side, sign in ((("L"), 1.0), (("R"), -1.0)):
        eye = lids[side]
        import bmesh
        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new("UVMap")
        planted = 0
        attempts = 0
        while planted < card_count and attempts < card_count * 60:
            attempts += 1
            a = rng.uniform(0.12, math.pi - 0.12)       # upper lid rim only
            rx, rz = 0.0132, 0.0088
            x = eye.x + math.cos(a) * rx
            z = eye.z + math.sin(a) * rz
            if z < eye_z + 0.0012:
                continue
            hit = _ray_front(bvh, x, z, y_start=-0.40)
            if hit is None:
                continue
            pos, nrm = hit
            outward = Vector((sign * math.cos(a) * 0.55, 0.0, 1.0)).normalized()
            tangent = outward
            cell = int(rng.integers(0, LASH_ATLAS_COLS * LASH_ATLAS_ROWS))
            cx = (cell % LASH_ATLAS_COLS) / LASH_ATLAS_COLS + 0.006
            cy = (cell // LASH_ATLAS_COLS) / LASH_ATLAS_ROWS + 0.006
            du = 1.0 / LASH_ATLAS_COLS - 0.012
            dv = 1.0 / LASH_ATLAS_ROWS - 0.012
            _card(bm, uv_layer, pos, tangent, nrm, rng.uniform(0.0038, 0.0062),
                  rng.uniform(0.00055, 0.0009), arch=0.0011,
                  uv_cell=(cx, cy, cx + du, cy + dv))
            planted += 1
        name = obj_name_left if sign > 0 else obj_name_right
        ob = _finish(bm, name)
        ob["uw_allow_uv_overlap"] = True
        _skin_to_head(ob, body_ob)
        out.append(ob)
        print(f"[FACE] lash cards {name}: {planted} planted ({attempts} ray casts)")
    return out[0], out[1]


# --------------------------------------------------------------------------------------
# teeth
# --------------------------------------------------------------------------------------


def build_teeth(lm, k, obj_name="Teeth", half_width=0.0225):
    """Upper + lower dental arch. The lower arch carries the `jawOpen` shape key."""
    eye_front_y = lm["eye_front_y"]
    mouth_z = lm["mouth_z"]
    jaw_z = lm["chin_z"]

    verts, faces = [], []
    arc_span = math.radians(100.0)
    for sign_z, n_teeth in ((1.0, 10), (-1.0, 10)):     # upper arch, lower arch
        z0 = mouth_z + sign_z * 0.0062 * k
        z1 = z0 + sign_z * 0.0082 * k
        for t in range(n_teeth):
            a_mid = -arc_span * 0.5 + arc_span * ((t + 0.5) / n_teeth)
            w = (arc_span / n_teeth) * 0.80
            for a in (a_mid - w * 0.5, a_mid + w * 0.5):
                for zz, depth in ((z0, 0.0), (z1, 0.0), (z0, 0.0045 * k), (z1, 0.0045 * k)):
                    x = math.sin(a) * half_width
                    ry = half_width * 0.66
                    y = eye_front_y + 0.0345 - math.cos(a) * ry - depth
                    verts.append((x, y, zz))
    for tooth in range(20):
        b = tooth * 8
        faces.append([b + 0, b + 1, b + 3, b + 2])          # front (visible) plate
        faces.append([b + 4, b + 6, b + 7, b + 5])          # back plate
        faces.append([b + 0, b + 2, b + 6, b + 4])
        faces.append([b + 1, b + 5, b + 7, b + 3])
        faces.append([b + 2, b + 3, b + 7, b + 6])
    me = bpy.data.meshes.new(obj_name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(obj_name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = False

    # UVs: demux every face into its own cell of a 8x13 sheet so all 100 faces have unique
    # texels (a shared square would be "100 % self-overlap" and fail the validator).
    uvl = me.uv_layers.new(name="UVMap")
    n_cols = 8
    for fi, poly in enumerate(me.polygons):
        cu = (fi % n_cols) / n_cols
        cv = (fi // n_cols) / ((len(me.polygons) + n_cols - 1) // n_cols)
        for k, li in enumerate(poly.loop_indices):
            uvl.data[li].uv = (cu + (k % 2) * 0.10 + 0.006,
                               cv + (k // 2) * 0.055 + 0.006)

    # Weights: the whole denture rides the skull; the lower arch opens through its `jawOpen`
    # shape key (the 53-bone SkeletonProfileHumanoid rig has no optional Jaw bone, so nothing
    # references a bone that does not exist).
    vg_head = ob.vertex_groups.new(name="Head")
    vg_head.add(list(range(len(me.vertices))), 1.0, "REPLACE")

    basis = ob.shape_key_add(name="Basis", from_mix=False)   # noqa: F841
    jaw = ob.shape_key_add(name="jawOpen", from_mix=False)
    jaw.value = 0.0
    pivot = Vector((0.0, eye_front_y + 0.05, jaw_z))
    for i, v in enumerate(me.vertices):
        if i < 80:                      # upper arch -> static
            jaw.data[i].co = v.co
            continue
        rel = v.co - pivot
        ang = math.radians(9.0)
        ca, sa = math.cos(ang), math.sin(ang)
        jaw.data[i].co = (pivot.x, pivot.y + rel.y * ca - rel.z * sa,
                          pivot.z + rel.y * sa + rel.z * ca)
    return ob


# --------------------------------------------------------------------------------------
# eyeballs
# --------------------------------------------------------------------------------------


def frame_eyeballs(eyes_ob, iris_half_angle_deg=30.0):
    """Re-parameterise each eyeball's UVs as a spherical cap centred on its cornea.

    The CC0 low-poly eyeball ships a two-eye atlas: one eyeball's iris is painted at
    uv (0.293, 0.292) with a radius of 0.163 (measured from `brown_eye.png`), but the mesh's own
    UVs put the cornea at (0.25, 0.50) with a ~0.05 iris - which is why the first renders showed
    a pin-prick pupil and a grey sclera.

    Here every vertex gets a UV derived from its *direction*: the cornea axis is the mesh's most
    forward vertex (-Y), the polar angle from that axis is mapped linearly onto the atlas iris
    radius, and the azimuth keeps its angle. The iris therefore lands exactly on the cornea at a
    controlled size (a 12 mm iris on a 12 mm eyeball = a 30 deg half-angle).
    """
    import math as _m

    me = eyes_ob.data
    if not me.uv_layers:
        return 0
    uvl = me.uv_layers[0].data
    atlas = {1.0: (_m.radians(iris_half_angle_deg), 0.163, (0.293, 0.292)),
             -1.0: (_m.radians(iris_half_angle_deg), 0.163, (0.709, 0.699))}
    moved = 0
    for sign, (theta_iris, uv_r, (cu0, cv0)) in atlas.items():
        idxs = [v.index for v in me.vertices if v.co.x * sign > 0.0]
        if len(idxs) < 8:
            continue
        co = np.array([tuple(me.vertices[i].co) for i in idxs])
        centre = co.mean(axis=0)
        cornea = co[int(np.argmin(co[:, 1]))]
        axis = cornea - centre
        axis /= max(np.linalg.norm(axis), 1e-9)
        # a stable perpendicular frame for the azimuth
        up = np.array([0.0, 0.0, 1.0])
        if abs(float(np.dot(up, axis))) > 0.95:
            up = np.array([1.0, 0.0, 0.0])
        e1 = up - axis * float(np.dot(up, axis))
        e1 /= max(np.linalg.norm(e1), 1e-9)
        e2 = np.cross(axis, e1)
        for i, p in zip(idxs, co - centre):
            d = p / max(np.linalg.norm(p), 1e-9)
            cos_t = max(min(float(np.dot(d, axis)), 1.0), -1.0)
            theta = _m.acos(cos_t)
            phi = _m.atan2(float(np.dot(p, e2)), float(np.dot(p, e1)))
            r_uv = uv_r * (theta / theta_iris)
            u = cu0 + _m.cos(phi) * r_uv
            v = cv0 + _m.sin(phi) * r_uv
            lim_lo, lim_hi = (0.004, 0.496) if sign > 0 else (0.504, 0.996)
            _u = min(max(u, lim_lo), lim_hi)
            _v = min(max(v, 0.004), 0.996)
            for l in me.loops:
                if l.vertex_index == i:
                    uvl[l.index].uv = (_u, _v)
                    moved += 1
    return moved
