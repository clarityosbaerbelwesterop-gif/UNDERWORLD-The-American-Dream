"""Vehicle interior kit (T-VEH-02): front seats, rear bench, dashboard + instrument hood, steering
wheel + column, centre console, floor - one `Interior` object (fabric + trim slots).

Built AGAINST the sit contract of the shared animation library (characters/animations.py
SIT_*): the seat sockets are the H-points, so the seats, the wheel rim and the floor land where
the seated Jason / Marco actually are. `check_fit()` refuses a car whose cabin cannot hold that
pose (head through the roof, feet through the floor, wheel through the windscreen) - the profile
must change, not the character.

Axes: Blender, -Y forward, +X = left = driver side (LHD), +Z up (TD-004).
"""
import math

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

from underworld_pipeline.vehicles import build_vehicle as BV


def _box(bm, center, size, rot=(0, 0, 0), bevel=0.02, segs=2):
    """BV._add_box with the bevel clamped to a quarter of the thinnest side (no zero-area faces)."""
    return BV._add_box(bm, center, size, rot=rot, bevel=min(bevel, 0.25 * min(size)), segs=segs)

# keep in sync with characters/animations.py (not imported: that module needs the rig solver)
SIT_SOLE_Z, SIT_HAND_Y, SIT_HAND_Z, SIT_HEAD_TOP = -0.22, -0.36, 0.34, 0.83
GRIP = 0.08                      # wrist -> grip centre along the hand
HAND_DIR = Vector((0.0, -0.55, 0.83)).normalized()
WHEEL_R = 0.19


def wheel_frame(seat):
    """Centre, unit normal (towards the driver) and rim radius of the steering wheel."""
    sx, sy, sz = seat
    grip = Vector((sx, sy + SIT_HAND_Y, sz + SIT_HAND_Z)) + HAND_DIR * GRIP
    n = Vector((1, 0, 0)).cross(HAND_DIR)          # plane spanned by X and the grip tangent
    if n.y < 0:
        n = -n
    return grip, n.normalized(), WHEEL_R


def _z_on(gh, y, i0, i1):
    (ya, _wa, za), (yb, _wb, zb) = gh[i0], gh[i1]
    t = (y - ya) / (yb - ya) if abs(yb - ya) > 1e-6 else 0.0
    return za + max(0.0, min(1.0, t)) * (zb - za)


def cabin_from(stations, gh):
    """Cabin numbers from a body section list [(y, w_bot, w_belt, z_bot, z_belt)] and greenhouse
    [(y, half_w, z)]: opening (y0, y1), floor, roof, inner half width."""
    y0, y1 = gh[0][0], gh[-1][0]
    inside = [s for s in stations if y0 - 1e-6 <= s[0] <= y1 + 1e-6]
    near = inside or stations
    return dict(
        y0=y0, y1=y1,
        open_y1=max([s[0] for s in inside] or [y0]),
        floor_z=min(s[3] for s in near) + 0.06,          # 6 cm floor pan inside the sills
        belt_z=min(s[4] for s in near),
        roof_z=max(z for (_y, _w, z) in gh),
        half_w=min(s[2] for s in near) - 0.10,
    )


def check_fit(name, seat, cab, gh):
    """Raises if the sit pose does not fit this cabin (see module doc)."""
    sx, sy, sz = seat
    errs = []
    roof_inner = cab["roof_z"] - 0.03
    if sz + SIT_HEAD_TOP > roof_inner - 0.01:
        errs.append(f"head top {sz + SIT_HEAD_TOP:.2f} > roof inner {roof_inner:.2f} - 0.01")
    if sz + SIT_SOLE_Z < cab["floor_z"] - 0.005:
        errs.append(f"soles {sz + SIT_SOLE_Z:.2f} below the floor {cab['floor_z']:.2f}")
    c, n, r = wheel_frame(seat)
    top = c + n.cross(Vector((1, 0, 0))).normalized() * r       # 12 o'clock
    if top.z < c.z:
        top = c - n.cross(Vector((1, 0, 0))).normalized() * r
    ws = _z_on(gh, top.y, 0, 1)
    if top.z > ws - 0.02:
        errs.append(f"wheel top z {top.z:.2f} > windscreen {ws:.2f} - 0.02 at y {top.y:.2f}")
    if errs:
        raise SystemExit(f"[INTERIOR] {name}: sit pose does not fit: " + "; ".join(errs))
    return {"head_clear_m": round(roof_inner - (sz + SIT_HEAD_TOP), 3),
            "sole_above_floor_m": round(sz + SIT_SOLE_Z - cab["floor_z"], 3),
            "wheel_windscreen_clear_m": round(ws - top.z, 3)}


def _torus(bm, center, normal, R, r, nu=28, nv=8):
    n = Vector(normal).normalized()
    a = Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0))
    u = (a - n * a.dot(n)).normalized()
    v = n.cross(u)
    rings = []
    for i in range(nu):
        th = 2 * math.pi * i / nu
        radial = u * math.cos(th) + v * math.sin(th)
        c = Vector(center) + radial * R
        rings.append([bm.verts.new(c + (radial * math.cos(2 * math.pi * j / nv) + n * math.sin(2 * math.pi * j / nv)) * r)
                      for j in range(nv)])
    for i in range(nu):
        r0, r1 = rings[i], rings[(i + 1) % nu]
        for j in range(nv):
            bm.faces.new((r0[j], r1[j], r1[(j + 1) % nv], r0[(j + 1) % nv]))


def _cyl(bm, a, b, r, segs=10):
    a, b = Vector(a), Vector(b)
    d = b - a
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    m = Matrix.Translation((a + b) * 0.5) @ rot
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r, radius2=r, depth=d.length, matrix=m)


def _seat(bm, x, hy, hz, width, rear=False, max_top=None):
    """Seat for an H-point at (x, hy, hz): cushion under the pelvis (sitting bones 12 cm below the
    hip joint, front raised 10 deg), backrest reclined 12 deg (= the seated spine), headrest."""
    top = hz - 0.12
    _box(bm, (x, hy - 0.11, top - 0.065), (width, 0.56, 0.13), rot=(math.radians(-10), 0, 0), bevel=0.03, segs=2)
    tilt = math.radians(-12)
    h = 0.58 if rear else 0.64
    if max_top is not None:
        h = max(0.30, min(h, max_top - top))
    cy = hy + 0.13 + 0.06 + (h * 0.5) * math.tan(-tilt)
    _box(bm, (x, cy, top + h * 0.5), (width, 0.12, h), rot=(tilt, 0, 0), bevel=0.03, segs=2)
    if not rear:
        _box(bm, (x, hy + 0.13 + 0.07 + (h + 0.09) * math.tan(-tilt), top + h + 0.10), (0.26, 0.10, 0.19), rot=(tilt, 0, 0), bevel=0.03, segs=2)
        for sx in (-0.12, 0.12):
            _cyl(bm, (x + sx, hy + 0.20 + h * math.tan(-tilt), top + h - 0.02), (x + sx, hy + 0.22 + h * math.tan(-tilt), top + h + 0.03), 0.008, 6)


def build_interior(name, root, seat, stations, gh, m_fabric, m_trim, rear_bench=None):
    """Adds the `Interior` object and returns (object, fit report). `seat` = driver socket."""
    cab = cabin_from(stations, gh)
    fit = check_fit(name, seat, cab, gh)
    sx, sy, sz = seat
    hw = cab["half_w"]
    bm = bmesh.new()
    # --- fabric: seats ---------------------------------------------------------------
    for x in (sx, -sx):
        _seat(bm, x, sy, sz, 0.50)
    if rear_bench is None:
        rear_bench = cab["open_y1"] - sy > 1.0
    if rear_bench:
        ry = cab["open_y1"] - 0.30
        back_y = ry + 0.30
        _seat(bm, 0.0, ry, sz + 0.02, 2 * hw - 0.08, rear=True, max_top=_z_on(gh, back_y, len(gh) - 2, len(gh) - 1) - 0.05)
    n_fab = len(bm.faces)
    # --- trim: floor, dash, instrument hood, console, wheel, column --------------------
    f0, f1 = cab["y0"] - 0.10, cab["open_y1"]
    _box(bm, (0.0, (f0 + f1) * 0.5, cab["floor_z"] - 0.03), (2 * hw, f1 - f0, 0.06), bevel=0.0, segs=1)
    d_rear = sy - 0.56                                     # rear face, 11 cm ahead of the knees
    depth = max(0.30, d_rear - (cab["y0"] - 0.04))
    d_front = d_rear - depth
    d_top = min(cab["belt_z"], _z_on(gh, d_rear, 0, 1)) - 0.03
    d_bot = sz + 0.16          # shins pass under it
    _box(bm, (0.0, d_rear - depth * 0.5, (d_top + d_bot) * 0.5), (2 * hw, depth, d_top - d_bot), bevel=0.025, segs=2)
    # footwell / firewall under the dash
    _box(bm, (0.0, d_front + 0.02, (d_bot + cab["floor_z"]) * 0.5), (2 * hw, 0.04, d_bot - cab["floor_z"]), bevel=0.0, segs=1)
    ih_y = d_rear - 0.10
    _box(bm, (sx, ih_y, d_top + 0.025), (0.42, 0.20, 0.05), bevel=0.015, segs=1)
    _box(bm, (0.0, sy - 0.05, (cab["floor_z"] + sz - 0.02) * 0.5), (0.22, 0.70, sz - 0.02 - cab["floor_z"]), bevel=0.02, segs=1)
    c, n, r = wheel_frame(seat)
    _torus(bm, c, n, r, 0.017)
    _cyl(bm, c - n * 0.01, c - n * 0.07, 0.055, 14)                       # hub / airbag cover
    up = n.cross(Vector((1, 0, 0))).normalized()
    if up.z < 0:
        up = -up
    for d in (Vector((1, 0, 0)), Vector((-1, 0, 0)), -up):                   # 9, 3, 6 o'clock spokes
        _cyl(bm, c - n * 0.04 + d * 0.05, c - n * 0.01 + d * (r - 0.012), 0.012, 6)
    col_end = c - n * 0.34
    _cyl(bm, c - n * 0.06, col_end, 0.035, 10)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for i, f in enumerate(bm.faces):
        f.smooth = True
        f.material_index = 0 if i < n_fab else 1
    me = bpy.data.meshes.new("Interior")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Interior", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = root
    me.materials.append(m_fabric)
    me.materials.append(m_trim)
    BV._smart_uv(ob)
    fit.update({"rear_bench": bool(rear_bench), "wheel_centre": [round(v, 3) for v in c]})
    return ob, fit


def open_cabin_faces(y0, y1, sy0, sy1):
    """True if the body-loft top (lid) quad between stations sy0..sy1 lies inside the cabin."""
    return y0 - 1e-6 <= min(sy0, sy1) and max(sy0, sy1) <= y1 + 1e-6


def glass_material(name):
    """Tinted see-through automotive glass (alpha blend, double-sided, clear coat)."""
    m = BV._mat(name, (0.05, 0.07, 0.085, 1.0), roughness=0.03, metallic=0.0, coat=1.0, coat_rough=0.01)
    bsdf = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Alpha"].default_value = 0.34
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"
    if hasattr(m, "blend_method"):
        try:
            m.blend_method = "BLEND"
        except (TypeError, AttributeError):
            pass
    m.use_backface_culling = False
    return m


def fabric_material(name):
    return BV._mat(name, (0.075, 0.072, 0.068, 1.0), roughness=0.88, metallic=0.0)
