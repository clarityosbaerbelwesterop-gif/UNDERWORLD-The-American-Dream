"""Building grammar (P3, T-BLDG-01): LA facades from a few rules instead of hand-placed boxes.

Grammar (Houdini/Geometry-Nodes style, plain bmesh):
  building = footprint (w x d) + floors (n x h) + per-wall bays
  wall     = outer face with real openings (reveals of `depth`), filled by glass/door/roll-up
             quads set back in the reveal, sills under windows
  floor    = string course band at every floor line (reads as storeys at distance)
  roof     = flat gravel slab + parapet + cap | hip roof with clay tiles | barrel vault
  extras   = awnings, fire escapes, balconies + railings, signs (label atlas), rooftop units
Front = -Y (TD-004). No interiors: buildings are closed volumes, the glass is dark.
Every name and brand is invented for UNDERWORLD.
"""
import math

from mathutils import Vector

TAU = math.tau


# ------------------------------------------------------------------ frame helpers
def _frame(side, w, d):
    """(origin, normal, length) of a wall seen from outside; u runs to the viewer's right."""
    return {
        "front": ((-w / 2, -d / 2, 0.0), (0, -1, 0), w),
        "right": ((w / 2, -d / 2, 0.0), (1, 0, 0), d),
        "back": ((w / 2, d / 2, 0.0), (0, 1, 0), w),
        "left": ((-w / 2, d / 2, 0.0), (-1, 0, 0), d),
    }[side]


def _P(origin, normal):
    o, n = Vector(origin), Vector(normal).normalized()
    up = Vector((0, 0, 1))
    u = up.cross(n).normalized()
    return (lambda uu, vv, dd=0.0: o + u * uu + up * vv - n * dd), u, n


def _yaw(u):
    return math.atan2(u.y, u.x)


def bays(length, n, win_w, margin=None):
    """Centres of n evenly spaced bays along a wall."""
    m = margin if margin is not None else (length - n * win_w) / (n + 1)
    step = (length - 2 * m - win_w) / max(1, n - 1) if n > 1 else 0
    return [m + win_w / 2 + i * step for i in range(n)] if n > 1 else [length / 2]


def facade(Pb, side, w, d, height, mat, openings, depth=0.22, reveal="concrete", sills=True):
    """openings: [(u0, u1, v0, v1, kind)], kind in glass|door|rollup|store|curtain|dark."""
    origin, normal, length = _frame(side, w, d)
    Pb.wall(origin, normal, length, height, mat, [o[:4] for o in openings], reveal_mat=reveal, depth=depth)
    P, u, n = _P(origin, normal)
    fills = {"glass": "window_glass", "store": "window_glass", "door": "metal_dark", "rollup": "rollup_door",
             "curtain": "curtain_glass", "dark": "metal_dark", "wood_door": "wood"}
    for (u0, u1, v0, v1, kind) in openings:
        dd = depth - 0.01
        Pb.quad(P(u0, v0, dd), P(u1, v0, dd), P(u1, v1, dd), P(u0, v1, dd), fills[kind])
        if kind == "glass" and sills:
            c = P((u0 + u1) / 2, v0 - 0.035, -0.04)
            Pb.box(tuple(c), (u1 - u0 + 0.12, 0.10, 0.07), "concrete", rot=(0, 0, _yaw(u)))
        if kind in ("glass", "store"):                     # mullion
            if u1 - u0 > 1.6:
                for k in range(1, int((u1 - u0) / 1.2) + 1):
                    um = u0 + (u1 - u0) * k / (int((u1 - u0) / 1.2) + 1)
                    c = P(um, (v0 + v1) / 2, dd - 0.03)
                    Pb.box(tuple(c), (0.05, 0.05, v1 - v0), "metal_dark", rot=(0, 0, _yaw(u)))
            if kind == "glass" and v1 - v0 > 1.3:
                c = P((u0 + u1) / 2, v0 + (v1 - v0) * 0.62, dd - 0.03)
                Pb.box(tuple(c), (u1 - u0, 0.05, 0.05), "metal_dark", rot=(0, 0, _yaw(u)))
    return P, u, n, length


def band(Pb, w, d, z, mat, proud=0.05, h=0.14, sides=("front", "right", "back", "left")):
    """String course / cornice band around the building at height z."""
    for s in sides:
        origin, normal, length = _frame(s, w, d)
        P, u, n = _P(origin, normal)
        c = P(length / 2, z, -proud / 2)
        Pb.box(tuple(c), (length + 2 * proud, proud, h), mat, rot=(0, 0, _yaw(u)))


def flat_roof(Pb, w, d, h, parapet=0.9, wall_mat="concrete", cap="concrete"):
    Pb.quad((-w / 2, -d / 2, h), (w / 2, -d / 2, h), (w / 2, d / 2, h), (-w / 2, d / 2, h), "roof_gravel")
    t = 0.22
    for (cx, cy, sx, sy) in ((0, -d / 2 + t / 2, w, t), (0, d / 2 - t / 2, w, t), (-w / 2 + t / 2, 0, t, d), (w / 2 - t / 2, 0, t, d)):
        Pb.box((cx, cy, h + parapet / 2), (sx, sy, parapet), wall_mat)
        Pb.box((cx, cy, h + parapet + 0.04), (sx + 0.06, sy + 0.06, 0.08), cap)


def hip_roof(Pb, w, d, h, rise, overhang=0.55, mat="roof_tiles"):
    W, D = w + 2 * overhang, d + 2 * overhang
    rx = max(0.0, W / 2 - D / 2)
    z1 = h + rise
    Pb.quad((-W / 2, -D / 2, h), (W / 2, -D / 2, h), (rx, 0, z1), (-rx, 0, z1), mat)
    Pb.quad((W / 2, D / 2, h), (-W / 2, D / 2, h), (-rx, 0, z1), (rx, 0, z1), mat)
    _tri(Pb, (W / 2, -D / 2, h), (W / 2, D / 2, h), (rx, 0, z1), mat)
    _tri(Pb, (-W / 2, D / 2, h), (-W / 2, -D / 2, h), (-rx, 0, z1), mat)
    Pb.quad((-W / 2, D / 2, h - 0.01), (W / 2, D / 2, h - 0.01), (W / 2, -D / 2, h - 0.01), (-W / 2, -D / 2, h - 0.01), "plaster_white")  # soffit
    for (cx, cy, sx, sy) in ((0, -D / 2, W, 0.04), (0, D / 2, W, 0.04), (-W / 2, 0, 0.04, D), (W / 2, 0, 0.04, D)):
        Pb.box((cx, cy, h - 0.08), (sx, sy, 0.18), "metal_dark")                                         # fascia


def _tri(Pb, a, b, c, mat):
    before = set(Pb.bm.faces)
    Pb.bm.faces.new([Pb.bm.verts.new(Vector(p)) for p in (a, b, c)])
    Pb._tag(Pb._new_faces(before), mat)


def awning(Pb, P, u, u0, u1, z, depth=1.4, drop=0.45, mat="canvas"):
    a, b = P(u0 - 0.1, z, 0.0), P(u1 + 0.1, z, 0.0)
    c, d_ = P(u1 + 0.1, z - drop, -depth), P(u0 - 0.1, z - drop, -depth)
    Pb.quad(tuple(d_), tuple(c), tuple(b), tuple(a), mat)               # top (seen from above/front)
    Pb.quad(tuple(a), tuple(b), tuple(c), tuple(d_), mat)               # underside
    Pb.box(tuple(P((u0 + u1) / 2, z - drop - 0.12, -depth)), (u1 - u0 + 0.2, 0.02, 0.25), mat, rot=(0, 0, _yaw(u)))  # valance


def sign(Pb, P, u, uc, z, w, h, label, proud=0.08, mat="metal_dark"):
    Pb.box(tuple(P(uc, z, -proud / 2)), (w, proud, h), mat, rot=(0, 0, _yaw(u)))
    Pb.label(tuple(P(uc, z, -proud - 0.004)), (w * 0.94, h * 0.86), label, rot=(0, 0, _yaw(u)))


def railing(Pb, pts, h=1.0, mat="metal_dark", post_every=1.5):
    top = [(x, y, z + h) for (x, y, z) in pts]
    Pb.tube(top, 0.022, mat, segs=6)
    Pb.tube([(x, y, z + h * 0.5) for (x, y, z) in pts], 0.012, mat, segs=4)
    for (a, b) in zip(pts, pts[1:]):
        A, B = Vector(a), Vector(b)
        n = max(1, int((B - A).length / post_every))
        for k in range(n + 1):
            p = A.lerp(B, k / n)
            Pb.tube([tuple(p), (p.x, p.y, p.z + h)], 0.02, mat, segs=6, closed_ends=False)


def fire_escape(Pb, P, u, uc, floors, floor_h, width=3.0, depth=1.1):
    yaw = _yaw(u)
    for f in range(1, floors):
        z = f * floor_h
        c = P(uc, z, -depth / 2)
        Pb.box(tuple(c), (width, depth, 0.05), "metal_dark", rot=(0, 0, yaw))
        a, b = P(uc - width / 2, z, -depth), P(uc + width / 2, z, -depth)
        a2, b2 = P(uc - width / 2, z, 0), P(uc + width / 2, z, 0)
        railing(Pb, [tuple(a2), tuple(a), tuple(b), tuple(b2)], h=0.95, post_every=1.0)
        if f < floors - 1:                                     # stair to the next landing
            s0, s1 = P(uc - width / 2 + 0.4, z + 0.05, -depth / 2), P(uc + width / 2 - 0.4, z + floor_h, -depth / 2)
            mid = (s0 + s1) / 2
            ln = (s1 - s0).length
            pitch = math.atan2(s1.z - s0.z, (Vector((s1.x, s1.y, 0)) - Vector((s0.x, s0.y, 0))).length)
            Pb.box(tuple(mid), (ln, 0.6, 0.04), "metal_dark", rot=(0, -pitch, yaw))
    # drop ladder from the first landing
    Pb.tube([tuple(P(uc + width / 2 - 0.3, floor_h, -depth + 0.1)), tuple(P(uc + width / 2 - 0.3, 2.3, -depth + 0.1))], 0.018, "metal_dark", segs=6)
    Pb.tube([tuple(P(uc + width / 2 - 0.75, floor_h, -depth + 0.1)), tuple(P(uc + width / 2 - 0.75, 2.3, -depth + 0.1))], 0.018, "metal_dark", segs=6)


def rooftop_unit(Pb, x, y, z, s=1.0):
    Pb.box((x, y, z + 0.5 * s), (1.6 * s, 1.1 * s, 1.0 * s), "metal_dark", bevel=0.03)
    Pb.cyl((x + 0.35 * s, y, z + 1.0 * s + 0.02), 0.38 * s, 0.04, "metal_dark", segs=14)


def water_tank(Pb, x, y, z):
    for a in range(4):
        ang = a * TAU / 4 + TAU / 8
        Pb.box((x + math.cos(ang) * 0.9, y + math.sin(ang) * 0.9, z + 1.0), (0.14, 0.14, 2.0), "metal_dark")
    Pb.cyl((x, y, z + 2.9), 1.3, 1.8, "wood", segs=16)
    Pb.cyl((x, y, z + 4.05), 1.35, 0.5, "metal_dark", segs=16, radius2=0.2)


# ------------------------------------------------------------------ buildings
def apartment_4f(Pb):
    """4-storey brick walk-up, 16 x 12 m, fire escape, lobby, water tank (East Hollow)."""
    w, d, fh, nf = 16.0, 12.0, 3.1, 4
    h = fh * nf
    ops = []
    for f in range(nf):
        z = f * fh
        for uc in bays(w, 5, 1.2):
            if f == 0 and abs(uc - w / 2) < 1.0:
                ops.append((uc - 0.8, uc + 0.8, 0.15, 2.6, "door"))
            else:
                ops.append((uc - 0.6, uc + 0.6, z + 0.9, z + 2.5, "glass"))
    P, u, n, L = facade(Pb, "front", w, d, h, "brick", ops)
    for side, ln in (("right", d), ("left", d), ("back", w)):
        o2 = [(uc - 0.6, uc + 0.6, f * fh + 0.9, f * fh + 2.5, "glass") for f in range(nf) for uc in bays(ln, 4 if ln > 13 else 3, 1.2)]
        facade(Pb, side, w, d, h, "brick", o2)
    for f in range(1, nf):
        band(Pb, w, d, f * fh, "concrete", proud=0.04, h=0.12)
    band(Pb, w, d, h - 0.3, "concrete", proud=0.18, h=0.35)                 # cornice
    fire_escape(Pb, P, u, w * 0.30, nf, fh, width=3.4)
    awning(Pb, P, u, w / 2 - 1.1, w / 2 + 1.1, 3.0, depth=1.2, drop=0.3, mat="paint_green")
    sign(Pb, P, u, w / 2, 3.35, 2.2, 0.35, "label:AptName:THE CALLOWAY|f1e6c8|2b2b2b|512x96")
    flat_roof(Pb, w, d, h, parapet=0.8, wall_mat="brick")
    water_tank(Pb, 3.5, 2.0, h)
    rooftop_unit(Pb, -4.0, 1.5, h)
    rooftop_unit(Pb, -1.5, 3.0, h, 0.8)
    Pb.col_box((0, 0, h / 2 + 0.4), (w, d, h + 0.8))


def motel(Pb):
    """Two-storey motel, 30 x 9 m: room doors on an open gallery, stair, pole sign."""
    w, d, fh = 30.0, 9.0, 3.0
    h = 2 * fh
    rooms = 8
    rw = w / rooms
    ops = []
    for f in range(2):
        for r in range(rooms):
            u0 = r * rw
            ops.append((u0 + 0.5, u0 + 1.4, f * fh + 0.05, f * fh + 2.2, "door"))
            ops.append((u0 + 1.9, u0 + 3.3, f * fh + 0.95, f * fh + 2.2, "glass"))
    P, u, n, L = facade(Pb, "front", w, d, h, "stucco_cream", ops)
    for side, ln in (("right", d), ("left", d)):
        facade(Pb, side, w, d, h, "stucco_cream", [(ln / 2 - 0.7, ln / 2 + 0.7, f * fh + 1.0, f * fh + 2.1, "glass") for f in range(2)])
    facade(Pb, "back", w, d, h, "stucco_cream", [(uc - 0.4, uc + 0.4, f * fh + 1.5, f * fh + 2.2, "glass") for f in range(2) for uc in bays(w, rooms, 0.8)])
    # gallery slab + railing + posts
    gd = 1.8
    Pb.box((0, -d / 2 - gd / 2, fh), (w + 0.4, gd, 0.2), "concrete")
    railing(Pb, [(-w / 2 - 0.2, -d / 2 - gd, fh + 0.1), (w / 2 + 0.2, -d / 2 - gd, fh + 0.1)], h=1.0, mat="paint_white", post_every=2.0)
    for k in range(rooms + 1):
        Pb.box((-w / 2 + k * rw, -d / 2 - gd + 0.1, fh / 2), (0.18, 0.18, fh), "paint_white")
    Pb.box((0, -d / 2 - gd / 2, h + 0.05), (w + 0.6, gd + 0.4, 0.12), "paint_white")          # roof overhang
    # stair at the right end
    s0, s1 = Vector((w / 2 + 1.0, -d / 2 - 0.8, 0.0)), Vector((w / 2 + 1.0, -d / 2 + 3.5, fh))
    mid = (s0 + s1) / 2
    Pb.box(tuple(mid), (1.1, (s1 - s0).length, 0.15), "concrete", rot=(math.atan2(fh, 4.3), 0, 0))
    for r in range(rooms):
        for f in range(2):
            num = (f + 1) * 100 + r + 1
            Pb.label(tuple(P(r * rw + 0.95, f * fh + 2.35, -0.006)), (0.3, 0.14), f"label:Room{num}:{num}|2b2b2b|e8dcc0|128x64")
    band(Pb, w, d, h - 0.2, "paint_white", proud=0.12, h=0.3)
    flat_roof(Pb, w, d, h, parapet=0.5, wall_mat="stucco_cream", cap="paint_white")
    # pole sign
    Pb.cyl((-w / 2 - 2.5, -d / 2 - 3.5, 4.5), 0.18, 9.0, "metal_dark", segs=12)
    Pb.box((-w / 2 - 2.5, -d / 2 - 3.5, 8.6), (3.6, 0.4, 1.8), "paint_red", bevel=0.05)
    Pb.label((-w / 2 - 2.5, -d / 2 - 3.705, 8.6), (3.4, 1.6), "label:MotelSign:SUNNY DAYS\\nMOTEL|ffe9a8|b22412|512x256")
    Pb.box((-w / 2 - 2.5, -d / 2 - 3.5, 7.3), (2.4, 0.3, 0.6), "metal_dark")
    Pb.label((-w / 2 - 2.5, -d / 2 - 3.655, 7.3), (2.3, 0.5), "label:Vacancy:VACANCY|ff4fa0|1a0a12|512x112")
    Pb.col_box((0, 0, h / 2), (w, d, h + 0.5))
    Pb.col_box((0, -d / 2 - gd / 2, fh), (w + 0.4, gd, 0.2))
    Pb.col_box((-w / 2 - 2.5, -d / 2 - 3.5, 4.5), (0.4, 0.4, 9.0))


def gas_station(Pb):
    """Kiosk 10 x 8 m + canopy 16 x 10 m on 4 columns + 2 pump islands + price sign."""
    kw, kd, kh = 10.0, 8.0, 4.0
    ky = 6.0                                                   # kiosk sits behind the canopy
    ops = [(1.0, 4.2, 0.4, 3.0, "store"), (4.6, 6.2, 0.05, 2.6, "door"), (6.6, 9.0, 0.4, 3.0, "store")]
    # kiosk walls via a shifted frame: build with an offset footprint
    def fr(side):
        o, nrm, ln = _frame(side, kw, kd)
        return (o[0], o[1] + ky, o[2]), nrm, ln
    for side, opl, mat in (("front", ops, "stucco_sand"), ("right", [(3.0, 4.2, 1.2, 2.4, "glass")], "stucco_sand"),
                           ("back", [], "stucco_sand"), ("left", [], "stucco_sand")):
        o, nrm, ln = fr(side)
        Pb.wall(o, nrm, ln, kh, mat, [x[:4] for x in opl], reveal_mat="paint_white", depth=0.2)
        P, u, n = _P(o, nrm)
        for (u0, u1, v0, v1, kind) in opl:
            fill = {"store": "window_glass", "door": "window_glass", "glass": "window_glass"}[kind]
            Pb.quad(P(u0, v0, 0.19), P(u1, v0, 0.19), P(u1, v1, 0.19), P(u0, v1, 0.19), fill)
        if side == "front":
            sign(Pb, P, u, kw / 2, kh - 0.45, 6.0, 0.6, "label:KioskSign:FOOD MART  -  ICE  -  COLD DRINKS|ffffff|0e4a7a|1024x112")
    Pb.quad((-kw / 2, ky - kd / 2, kh), (kw / 2, ky - kd / 2, kh), (kw / 2, ky + kd / 2, kh), (-kw / 2, ky + kd / 2, kh), "roof_gravel")
    Pb.box((0, ky, kh + 0.25), (kw + 0.2, kd + 0.2, 0.5), "paint_white")
    # canopy
    cw, cd, ch = 16.0, 10.0, 5.2
    Pb.box((0, -4.0, ch + 0.35), (cw, cd, 0.7), "paint_white", bevel=0.04)
    Pb.label((0, -4.0 - cd / 2 - 0.005, ch + 0.35), (6.0, 0.6), "label:CanopyBrand:COASTLINE FUEL|ffffff|c2461b|1024x112")
    Pb.quad((-cw / 2, -4.0 + cd / 2, ch - 0.002), (cw / 2, -4.0 + cd / 2, ch - 0.002), (cw / 2, -4.0 - cd / 2, ch - 0.002), (-cw / 2, -4.0 - cd / 2, ch - 0.002), "light_panel")
    for x in (-5.0, 5.0):
        for y in (-7.0, -1.0):
            Pb.box((x, y, ch / 2), (0.45, 0.45, ch), "paint_white", bevel=0.02)
    # pump islands
    for x in (-5.0, 5.0):
        Pb.box((x, -4.0, 0.1), (1.2, 5.0, 0.2), "concrete", bevel=0.03)
        for y in (-5.4, -2.6):
            Pb.box((x, y, 0.95), (0.75, 0.5, 1.5), "paint_white", bevel=0.03)
            Pb.box((x, y - 0.255, 1.25), (0.5, 0.01, 0.35), "window_glass")
            Pb.label((x, y - 0.256, 1.62), (0.6, 0.18), f"label:Pump{int(x)}{int(y * 10)}:COASTLINE|ffffff|c2461b|256x64")
            Pb.tube([(x + 0.38, y, 1.2), (x + 0.55, y - 0.2, 0.7), (x + 0.42, y - 0.3, 1.0)], 0.02, "metal_dark", segs=6)
        Pb.box((x, -7.6, 0.45), (0.3, 0.3, 0.9), "paint_white")                          # bollards
        Pb.box((x, -0.4, 0.45), (0.3, 0.3, 0.9), "paint_white")
    # price sign
    Pb.cyl((9.5, -9.5, 3.0), 0.15, 6.0, "metal_dark", segs=12)
    Pb.box((9.5, -9.5, 6.3), (2.2, 0.35, 2.4), "paint_white", bevel=0.04)
    Pb.label((9.5, -9.68, 6.3), (2.0, 2.2), "label:PriceSign:COASTLINE\\nREG  4.19\\nPLUS 4.39\\nDIESEL 4.59|1a1a1a|f4f1e6|256x320")
    Pb.col_box((0, ky, kh / 2), (kw, kd, kh + 0.5))
    for x in (-5.0, 5.0):
        Pb.col_box((x, -4.0, 0.9), (1.2, 5.0, 1.8))
        for y in (-7.0, -1.0):
            Pb.col_box((x, y, ch / 2), (0.45, 0.45, ch))
    Pb.col_box((0, -4.0, ch + 0.35), (cw, cd, 0.7))
    Pb.col_box((9.5, -9.5, 3.0), (0.3, 0.3, 6.0))


def warehouse(Pb):
    """M01 delivery warehouse 30 x 20 x 8 m: corrugated shell, loading dock, 3 roll-up doors."""
    w, d, h = 30.0, 20.0, 8.0
    dock_h = 1.2
    ops = []
    for uc in bays(w, 3, 3.6):
        ops.append((uc - 1.8, uc + 1.8, dock_h, dock_h + 3.6, "rollup"))
    ops.append((w - 2.2, w - 1.1, 0.05, 2.2, "door"))
    for uc in bays(w, 6, 2.4):
        ops.append((uc - 1.2, uc + 1.2, h - 1.7, h - 0.8, "glass"))
    P, u, n, L = facade(Pb, "front", w, d, h, "corrugated", ops, depth=0.25, reveal="metal_dark", sills=False)
    for side, ln in (("right", d), ("left", d), ("back", w)):
        facade(Pb, side, w, d, h, "corrugated",
               [(uc - 1.2, uc + 1.2, h - 1.7, h - 0.8, "glass") for uc in bays(ln, 4 if ln > 25 else 3, 2.4)], depth=0.2, reveal="metal_dark", sills=False)
    band(Pb, w, d, 1.0, "concrete", proud=0.06, h=2.0)                           # concrete plinth
    Pb.box((0, -d / 2 - 1.6, dock_h / 2), (w - 4.0, 3.2, dock_h), "concrete", bevel=0.04)    # dock
    for uc in bays(w, 3, 3.6):                                                    # dock bumpers
        for du in (-1.6, 1.6):
            c = P(uc + du, dock_h - 0.35, 3.2 + 0.08)
            Pb.box(tuple(c), (0.25, 0.16, 0.45), "metal_dark")
    Pb.box((w / 2 - 1.0, -d / 2 - 2.5, 0.6), (1.2, 1.6, 1.2), "concrete")         # steps (end)
    sign(Pb, P, u, w / 2, h - 2.6, 8.0, 1.0, "label:WarehouseSign:HOLLOW FREIGHT & STORAGE|ffffff|1f3d5c|1024x128")
    for uc in bays(w, 3, 3.6):
        Pb.label(tuple(P(uc, dock_h + 3.9, -0.005)), (0.9, 0.35), f"label:Bay{int(uc)}:BAY {bays(w, 3, 3.6).index(uc) + 1}|111111|e6c014|128x64")
        Pb.box(tuple(P(uc, dock_h + 4.1, -0.25)), (0.5, 0.3, 0.18), "metal_dark", rot=(0, 0, _yaw(u)))     # dock light
    flat_roof(Pb, w, d, h, parapet=0.6, wall_mat="corrugated", cap="metal_dark")
    for x in (-8.0, 0.0, 8.0):
        rooftop_unit(Pb, x, 3.0, h, 1.2)
    Pb.col_box((0, 0, h / 2 + 0.3), (w, d, h + 0.6))
    Pb.col_box((0, -d / 2 - 1.6, dock_h / 2), (w - 4.0, 3.2, dock_h))


def hangar(Pb):
    """Private airfield hangar 30 x 26 m, barrel-vault roof (rise 6 m on 6 m walls), sliding doors."""
    w, d, hw, rise = 30.0, 26.0, 6.0, 5.0
    seg = 16
    arc = [(-w / 2 + w * k / seg, hw + rise * (1 - (2 * k / seg - 1) ** 2)) for k in range(seg + 1)]
    for (x0, z0), (x1, z1) in zip(arc, arc[1:]):                                    # vault (outside, +Z-ish normal)
        Pb.quad((x0, d / 2, z0), (x0, -d / 2, z0), (x1, -d / 2, z1), (x1, d / 2, z1), "corrugated")
    door = (2.0, w - 2.0, 0.0, hw - 0.4)
    P, u, n, L = facade(Pb, "front", w, d, hw, "corrugated", [door + ("rollup",)], depth=0.35, reveal="metal_dark", sills=False)
    for side in ("right", "left"):
        o, nrm, ln = _frame(side, w, d)
        facade(Pb, side, w, d, hw, "corrugated", [(uc - 1.0, uc + 1.0, 3.6, 4.8, "glass") for uc in bays(ln, 4, 2.0)], depth=0.2, reveal="metal_dark", sills=False)
    facade(Pb, "back", w, d, hw, "corrugated", [(w / 2 - 0.6, w / 2 + 0.6, 0.05, 2.2, "door")], depth=0.2, reveal="metal_dark", sills=False)
    for y, flip in ((-d / 2, False), (d / 2, True)):                                # gable (arc) walls
        for (x0, z0), (x1, z1) in zip(arc, arc[1:]):
            if abs(z0 - hw) < 1e-6 or abs(z1 - hw) < 1e-6:          # end segments are triangles
                top = (x1, y, z1) if abs(z0 - hw) < 1e-6 else (x0, y, z0)
                tri = [(x0, y, hw), (x1, y, hw), top]
                _tri(Pb, *(tri[::-1] if flip else tri), "corrugated")
                continue
            if flip:
                Pb.quad((x1, y, hw), (x0, y, hw), (x0, y, z0), (x1, y, z1), "corrugated")
            else:
                Pb.quad((x0, y, hw), (x1, y, hw), (x1, y, z1), (x0, y, z0), "corrugated")
    sign(Pb, P, u, w / 2, hw + 2.0, 9.0, 1.1, "label:HangarSign:SAN ARDO AIRFIELD  -  HANGAR 3|ffffff|263a26|1024x128")
    for k in range(5):                                                               # door rails/panels
        c = P(door[0] + (door[1] - door[0]) * (k + 0.5) / 5, (hw - 0.4) / 2, 0.33)
        Pb.box(tuple(c), (0.06, 0.08, hw - 0.4), "metal_dark", rot=(0, 0, _yaw(u)))
    Pb.box(tuple(P(w / 2, hw - 0.2, -0.1)), (w, 0.25, 0.25), "metal_dark", rot=(0, 0, _yaw(u)))
    Pb.col_box((0, 0, (hw + rise) / 2), (w, d, hw + rise))


def office_downtown(Pb):
    """8-storey office block 20 x 20 m: concrete frame, ribbon curtain glass, glass lobby, penthouse."""
    w, d, fh, nf = 20.0, 20.0, 3.6, 8
    h = fh * nf
    for side in ("front", "right", "back", "left"):
        ops = []
        for f in range(nf):
            z = f * fh
            if f == 0:
                if side == "front":
                    ops += [(1.0, 8.2, 0.3, 3.3, "store"), (8.6, 11.4, 0.05, 3.0, "door"), (11.8, 19.0, 0.3, 3.3, "store")]
                else:
                    ops += [(1.0, 19.0, 0.6, 3.2, "store")]
            else:
                ops.append((0.7, w - 0.7, z + 0.85, z + 3.25, "curtain"))
        P, u, n, L = facade(Pb, side, w, d, h, "concrete_wall", ops, depth=0.3, reveal="concrete", sills=False)
        if side == "front":
            frontP, front_u = P, u
    for f in range(1, nf):
        band(Pb, w, d, f * fh + 0.42, "concrete_wall", proud=0.12, h=0.84)
    Pb.box(tuple(frontP(w / 2, 3.6, -1.2)), (5.0, 2.4, 0.25), "metal_dark", rot=(0, 0, _yaw(front_u)))          # entrance canopy
    sign(Pb, frontP, front_u, w / 2, 4.15, 6.0, 0.6, "label:OfficeSign:ONE HOLLOW PLAZA|e8e8e8|1b1b1b|1024x112", proud=0.05)
    flat_roof(Pb, w, d, h, parapet=1.1, wall_mat="concrete_wall")
    Pb.box((2.0, 3.0, h + 1.8), (8.0, 6.0, 3.6), "concrete_wall", bevel=0.05)                                     # penthouse
    Pb.box((2.0, 3.0, h + 3.65), (8.3, 6.3, 0.1), "concrete")
    Pb.cyl((-5.0, 5.0, h + 4.5), 0.08, 9.0, "metal_dark", segs=8)                                               # antenna
    rooftop_unit(Pb, -5.5, -4.0, h, 1.4)
    rooftop_unit(Pb, 6.0, -5.0, h, 1.4)
    Pb.col_box((0, 0, h / 2 + 0.55), (w, d, h + 1.1))


def villa_crestmont(Pb):
    """Crestmont Hills villa (Sam): 2 floors, white plaster, clay hip roof, balcony, garage."""
    w, d, fh = 18.0, 12.0, 3.3
    h = 2 * fh
    front = [(1.2, 4.8, 0.05, 2.6, "rollup"),                  # garage
             (6.2, 8.0, 0.05, 2.7, "wood_door"), (8.8, 11.6, 0.6, 2.8, "store"), (12.6, 16.8, 0.6, 2.8, "store"),
             (1.6, 4.4, fh + 0.9, fh + 2.6, "glass"), (6.0, 11.8, fh + 0.05, fh + 2.8, "store"), (13.0, 16.4, fh + 0.9, fh + 2.6, "glass")]
    P, u, n, L = facade(Pb, "front", w, d, h, "plaster_white", front, depth=0.25, reveal="concrete")
    for side, ln in (("right", d), ("left", d)):
        facade(Pb, side, w, d, h, "plaster_white", [(uc - 0.8, uc + 0.8, f * fh + 0.9, f * fh + 2.5, "glass") for f in range(2) for uc in bays(ln, 2, 1.6)])
    facade(Pb, "back", w, d, h, "plaster_white", [(2.0, 16.0, 0.05, 2.8, "store")] + [(uc - 1.0, uc + 1.0, fh + 0.9, fh + 2.6, "glass") for uc in bays(w, 4, 2.0)])
    band(Pb, w, d, fh, "plaster_white", proud=0.06, h=0.18)
    # balcony over the entrance with glass rail
    Pb.box(tuple(P(8.9, fh, -0.9)), (6.4, 1.8, 0.22), "plaster_white", rot=(0, 0, _yaw(u)))
    Pb.box(tuple(P(8.9, fh + 0.6, -1.78)), (6.4, 0.03, 1.0), "window_glass", rot=(0, 0, _yaw(u)))
    Pb.tube([tuple(P(5.7, fh + 1.12, -1.78)), tuple(P(12.1, fh + 1.12, -1.78))], 0.025, "metal_dark", segs=6)
    for uu in (6.0, 11.8):                                                                      # entrance columns
        Pb.cyl(tuple(P(uu, fh / 2, -1.6)), 0.16, fh, "plaster_white", segs=14)
    hip_roof(Pb, w, d, h, rise=2.6)
    Pb.box((5.0, 2.0, h + 1.6), (0.9, 0.7, 2.2), "plaster_white")                               # chimney
    Pb.box(tuple(P(3.0, 0.1, -3.0)), (3.8, 6.0, 0.2), "concrete", rot=(0, 0, _yaw(u)))           # driveway
    Pb.label(tuple(P(7.1, 2.9, -0.006)), (0.4, 0.14), "label:HouseNo:1408|2b2b2b|e4ddd0|128x48")
    Pb.col_box((0, 0, h / 2 + 0.8), (w, d, h + 1.6))


def liquor_store(Pb):
    """Corner liquor store 12 x 10 x 4.6 m: storefront with security bars, awning, roof sign."""
    w, d, h = 12.0, 10.0, 4.6
    ops = [(0.8, 4.6, 0.6, 3.0, "store"), (5.1, 6.9, 0.05, 2.6, "door"), (7.4, 11.2, 0.6, 3.0, "store")]
    P, u, n, L = facade(Pb, "front", w, d, h, "stucco_peach", ops, depth=0.22)
    facade(Pb, "right", w, d, h, "stucco_peach", [(1.0, 4.0, 0.6, 2.6, "store")])
    facade(Pb, "back", w, d, h, "stucco_peach", [(w - 2.0, w - 1.0, 0.05, 2.2, "door")])
    facade(Pb, "left", w, d, h, "stucco_peach", [])
    for (u0, u1, v0, v1, k) in ops:                                     # security bars on the shop windows
        if k == "store":
            nb = int((u1 - u0) / 0.16)
            for b in range(1, nb):
                uu = u0 + (u1 - u0) * b / nb
                Pb.box(tuple(P(uu, (v0 + v1) / 2, -0.03)), (0.02, 0.02, v1 - v0), "metal_dark", rot=(0, 0, _yaw(u)))
            Pb.box(tuple(P((u0 + u1) / 2, v1 - 0.05, -0.03)), (u1 - u0, 0.03, 0.04), "metal_dark", rot=(0, 0, _yaw(u)))
    awning(Pb, P, u, 0.6, 11.4, 3.55, depth=1.3, drop=0.5, mat="paint_red")
    sign(Pb, P, u, w / 2, 4.15, 7.5, 0.7, "label:LiquorSign:VEGA LIQUOR & DELI|fff2c2|7a1010|1024x112")
    # side mural panel
    o, nrm, ln = _frame("left", w, d)
    Pl, ul, nl = _P(o, nrm)
    Pb.label(tuple(Pl(ln / 2, 2.4, -0.006)), (7.0, 2.6), "label:Mural:COLD BEER\\nLOTTO  -  ATM  -  ICE|f6d36b|1d3f73|512x192", rot=(0, 0, _yaw(ul)))
    flat_roof(Pb, w, d, h, parapet=0.7, wall_mat="stucco_peach", cap="paint_white")
    Pb.box((0, -d / 2 + 0.11, h + 1.3), (5.0, 0.22, 1.2), "stucco_peach")                         # stepped parapet
    rooftop_unit(Pb, 2.5, 2.5, h)
    Pb.col_box((0, 0, h / 2 + 0.35), (w, d, h + 0.7))


BUILDINGS = {
    "SM_LA_Bldg_Apartment4F": (apartment_4f, "Environment/LA"),
    "SM_LA_Bldg_Motel": (motel, "Environment/LA"),
    "SM_LA_Bldg_GasStation": (gas_station, "Environment/LA"),
    "SM_LA_Bldg_Warehouse": (warehouse, "Environment/LA"),
    "SM_LA_Bldg_Hangar": (hangar, "Environment/LA"),
    "SM_LA_Bldg_OfficeDowntown": (office_downtown, "Environment/LA"),
    "SM_LA_Bldg_VillaCrestmont": (villa_crestmont, "Environment/LA"),
    "SM_LA_Bldg_LiquorStore": (liquor_store, "Environment/LA"),
}
