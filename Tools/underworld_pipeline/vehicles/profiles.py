"""Vehicle body profiles (P5, T-VEH-01): VH_Sedan_01's builder generalised to a family of cars.

A profile = dimensions + body stations (cross-sections along the length) + greenhouse + doors
+ extras (light bar, roof sign, scoop, spoiler, livery). Same contract as VH_Sedan_01 and
Scripts/vehicle/vehicle.gd: Body/Cabin/Hood/Trunk/Bumper_F/Bumper_R, hinged Door_* (origin =
hinge), Wheel_FL/FR/RL/RR centred on the hub, UCX_<id>-convcolonly, SOCKET_Seat_Driver/
Passenger, SOCKET_Exit_Left/Right, light sockets, uw_wheel_radius_m on the root.
Original designs, invented liveries only (no real brands, no real police or taxi companies).
"""
import math
import os

import bmesh
import bpy
import numpy as np

from . import build_vehicle as BV
from ..characters import pbr_textures as PBR

SEDAN_STATIONS = [
    (-2.42, 0.82, 0.84, 0.30, 0.72), (-2.10, 0.89, 0.91, 0.27, 0.82), (-1.42, 0.90, 0.93, 0.26, 0.88),
    (-0.82, 0.91, 0.93, 0.24, 0.90), (0.05, 0.91, 0.93, 0.24, 0.91), (0.95, 0.91, 0.93, 0.25, 0.92),
    (1.44, 0.90, 0.93, 0.27, 0.92), (2.15, 0.88, 0.89, 0.29, 0.88), (2.42, 0.81, 0.83, 0.32, 0.84),
]
SEDAN_GH = [(-0.82, 0.86, 0.89), (-0.34, 0.67, 1.41), (0.76, 0.66, 1.43), (1.36, 0.85, 0.92)]
SEDAN_DOORS = [("Door_FL", 1.0, -0.78, -0.30, 0.94), ("Door_FR", -1.0, -0.78, -0.30, 0.94),
               ("Door_RL", 1.0, 0.20, 0.64, 0.86), ("Door_RR", -1.0, 0.20, 0.64, 0.86)]


def _scaled(stations, ys=1.0, dz_bot=0.0, dz_belt=0.0, dw=0.0):
    return [(y * ys, wb + dw, wt + dw, zb + dz_bot, zt + dz_belt) for (y, wb, wt, zb, zt) in stations]


PROFILES = {
    "VH_Police_01": dict(
        doc="Police cruiser (fictional 'HOLLOW PD' livery): sedan body, black/white two-tone, light bar, push bar.",
        paint=(0.02, 0.02, 0.025, 1.0), door_paint=(0.86, 0.86, 0.84, 1.0),
        stations=SEDAN_STATIONS, gh=SEDAN_GH, doors=SEDAN_DOORS,
        wheel_r=0.34, wheel_w=0.24, wheelbase=2.86, track=1.58, y_front=-1.42,
        hood=((0.0, -1.56, 0.83), (1.42, 1.24, 0.045), 4.5), trunk=((0.0, 1.84, 0.85), (1.40, 0.82, 0.045), -3.0),
        extras=["lightbar", "pushbar"], livery=("HOLLOW PD", "ffffff", "0a0a0c", "To protect and to serve"),
        seat=(0.42, -0.10, 0.52), col=((1.82, 4.92, 0.64, 0.66), (1.42, 2.05, 0.48, 1.18, 0.22))),
    "VH_Taxi_NY_01": dict(
        doc="New York taxi (fictional 'CITY CAB' livery): sedan body, cab yellow, roof sign, checker stripe.",
        paint=(0.80, 0.56, 0.04, 1.0),
        stations=SEDAN_STATIONS, gh=SEDAN_GH, doors=SEDAN_DOORS,
        wheel_r=0.34, wheel_w=0.24, wheelbase=2.86, track=1.58, y_front=-1.42,
        hood=((0.0, -1.56, 0.83), (1.42, 1.24, 0.045), 4.5), trunk=((0.0, 1.84, 0.85), (1.40, 0.82, 0.045), -3.0),
        extras=["roofsign"], livery=("CITY CAB  4K17", "111111", "d9a514", "NYC  -  1.75 / MILE"),
        seat=(0.42, -0.10, 0.52), col=((1.82, 4.92, 0.64, 0.66), (1.42, 2.05, 0.48, 1.18, 0.22))),
    "VH_Muscle_01": dict(
        doc="Late-60s style muscle coupe (original): long hood, low roof, 2 long doors, hood scoop, ducktail.",
        paint=(0.42, 0.04, 0.03, 1.0),
        stations=_scaled(SEDAN_STATIONS, ys=0.98, dz_belt=-0.04, dw=0.02),
        gh=[(-0.50, 0.86, 0.86), (-0.02, 0.66, 1.29), (0.66, 0.64, 1.30), (1.42, 0.84, 0.88)],
        doors=[("Door_FL", 1.0, -0.52, 0.06, 1.16), ("Door_FR", -1.0, -0.52, 0.06, 1.16)],
        wheel_r=0.34, wheel_w=0.27, wheelbase=2.80, track=1.60, y_front=-1.40,
        hood=((0.0, -1.48, 0.80), (1.44, 1.86, 0.045), 3.0), trunk=((0.0, 1.88, 0.84), (1.40, 0.76, 0.045), -2.0),
        extras=["scoop", "ducktail", "stripes"], livery=None,
        seat=(0.42, 0.20, 0.46), col=((1.86, 4.84, 0.60, 0.62), (1.40, 1.90, 0.42, 1.10, 0.30))),
    "VH_Pickup_01": dict(
        doc="Late-90s full-size crew-cab pickup (original): tall body, flat bed with tonneau cover, 4 doors.",
        paint=(0.26, 0.29, 0.30, 1.0),
        stations=[(-2.78, 0.86, 0.88, 0.50, 0.98), (-2.45, 0.93, 0.95, 0.46, 1.10), (-1.75, 0.95, 0.97, 0.44, 1.14),
                  (-1.00, 0.96, 0.98, 0.42, 1.16), (0.00, 0.96, 0.98, 0.42, 1.16), (0.80, 0.96, 0.98, 0.43, 1.14),
                  (1.80, 0.96, 0.98, 0.44, 1.14), (2.55, 0.95, 0.97, 0.46, 1.13), (2.80, 0.92, 0.94, 0.48, 1.12)],
        gh=[(-1.05, 0.90, 1.16), (-0.55, 0.76, 1.86), (0.62, 0.76, 1.88), (0.78, 0.88, 1.16)],
        doors=[("Door_FL", 1.0, -0.98, -0.48, 1.00), ("Door_FR", -1.0, -0.98, -0.48, 1.00),
               ("Door_RL", 1.0, 0.02, 0.36, 0.70), ("Door_RR", -1.0, 0.02, 0.36, 0.70)],
        wheel_r=0.40, wheel_w=0.28, wheelbase=3.50, track=1.70, y_front=-1.80,
        hood=((0.0, -1.95, 1.17), (1.60, 1.50, 0.045), 3.0), trunk=None,
        extras=["bedrails", "tailgate"], livery=None, belt_trim=1.16,
        seat=(0.44, -0.30, 0.78), col=((1.94, 5.56, 0.78, 0.86), (1.56, 1.85, 0.70, 1.52, -0.22))),
    "VH_Van_01": dict(
        doc="Delivery van (M01 wave 2, original): one-box body, sliding side doors, rear cargo doors, roof rack.",
        paint=(0.84, 0.84, 0.82, 1.0),
        stations=[(-2.60, 0.86, 0.88, 0.40, 0.95), (-2.30, 0.95, 0.97, 0.36, 1.08), (-1.70, 0.97, 0.99, 0.34, 1.12),
                  (-1.00, 0.98, 1.00, 0.34, 1.14), (0.50, 0.98, 1.00, 0.34, 1.14), (1.80, 0.98, 1.00, 0.35, 1.14),
                  (2.55, 0.97, 0.99, 0.37, 1.14), (2.70, 0.95, 0.97, 0.39, 1.12)],
        gh=[(-1.90, 0.92, 1.14), (-1.25, 0.90, 2.22), (2.55, 0.90, 2.28), (2.70, 0.93, 1.14)],
        glass_y_max=-1.05,
        doors=[("Door_FL", 1.0, -1.55, -1.15, 0.80), ("Door_FR", -1.0, -1.55, -1.15, 0.80),
               ("Door_RL", 1.0, -0.55, 0.05, 1.20), ("Door_RR", -1.0, -0.55, 0.05, 1.20)],
        door_h=(0.78, 0.62),
        wheel_r=0.36, wheel_w=0.25, wheelbase=3.30, track=1.72, y_front=-1.80,
        hood=((0.0, -2.20, 1.10), (1.70, 0.70, 0.045), 12.0), trunk=None,
        extras=["roofrack", "reardoors"], livery=("HOLLOW FREIGHT", "1f3d5c", "e8e8e4", "Calloway Ave  -  Since 1971"),
        seat=(0.46, -1.10, 0.80), col=((1.96, 5.36, 0.92, 0.82), (1.80, 3.90, 1.00, 1.70, 0.40))),
}


def _label_mat(name, text, fg, bg, w=512, h=128):
    from ..props.kit import text_image
    img = PBR.pack_np_image(f"T_{name}_D", text_image(text, fg, bg, w, h), False, "JPEG", 90)
    m = PBR.make_pbr_material(f"M_{name}", img, None, None, roughness=0.35, metallic=0.0)
    return m


def _decal_uv(ob, mat_index):
    """Fit 0..1 UVs (text upright) on the faces of one material slot of an object."""
    me = ob.data
    uv = me.uv_layers.active.data
    from mathutils import Vector
    for p in me.polygons:
        if p.material_index != mat_index:
            continue
        n = p.normal
        up = Vector((0, 0, 1))
        u_ax = up.cross(n).normalized() if abs(n.z) < 0.9 else Vector((1, 0, 0))
        v_ax = n.cross(u_ax).normalized()
        cos = [me.vertices[me.loops[li].vertex_index].co for li in p.loop_indices]
        us = [c.dot(u_ax) for c in cos]
        vs = [c.dot(v_ax) for c in cos]
        du, dv = (max(us) - min(us)) or 1.0, (max(vs) - min(vs)) or 1.0
        for li, a, b in zip(p.loop_indices, us, vs):
            uv[li].uv = ((a - min(us)) / du, (b - min(vs)) / dv)


def _quad(bm, pts):
    return bm.faces.new([bm.verts.new(p) for p in pts])


def build_from_profile(name, repo_root):
    P = PROFILES[name]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system, sc.unit_settings.scale_length = "METRIC", 1.0
    sc.render.fps = 30
    root = bpy.data.objects.new(name, None)
    sc.collection.objects.link(root)
    paint = tuple(P["paint"])
    m_paint = BV._mat(f"M_{name}_Paint", paint, roughness=0.24, metallic=0.5, coat=1.0, coat_rough=0.05)
    m_glass = BV._mat(f"M_{name}_Glass", (0.04, 0.06, 0.08, 1.0), roughness=0.06, metallic=0.10, coat=1.0, coat_rough=0.02)
    m_chrome = BV._mat(f"M_{name}_Chrome", (0.82, 0.84, 0.86, 1.0), roughness=0.12, metallic=0.96)
    m_trim = BV._mat(f"M_{name}_Trim", (0.06, 0.06, 0.07, 1.0), roughness=0.62, metallic=0.05)
    m_tire = BV._mat(f"M_{name}_Tire", (0.045, 0.045, 0.048, 1.0), roughness=0.82, metallic=0.0)
    m_rim = BV._mat(f"M_{name}_Rim", (0.72, 0.74, 0.76, 1.0), roughness=0.22, metallic=0.90)
    m_head = BV._mat(f"M_{name}_Headlight", (0.95, 0.92, 0.82, 1.0), roughness=0.08, metallic=0.2, emit=1.5)
    m_tail = BV._mat(f"M_{name}_Taillight", (0.72, 0.05, 0.04, 1.0), roughness=0.12, metallic=0.1, emit=1.2)
    m_door = BV._mat(f"M_{name}_DoorPaint", tuple(P["door_paint"]), roughness=0.24, metallic=0.4, coat=1.0, coat_rough=0.05) if P.get("door_paint") else m_paint
    st = P["stations"]
    y0, y1 = st[0][0], st[-1][0]

    # Body loft (same 8-point sedan section)
    bm = bmesh.new()
    rings = []
    for y, wb, wt, zb, zt in st:
        zm = 0.5 * (zb + zt)
        pts = [(-wb * 0.85, y, zb), (-wb, y, zb + 0.08), (-wt, y, zm + 0.05), (-wt * 0.96, y, zt),
               (wt * 0.96, y, zt), (wt, y, zm + 0.05), (wb, y, zb + 0.08), (wb * 0.85, y, zb)]
        rings.append([bm.verts.new(p) for p in pts])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(8):
            j = (i + 1) % 8
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    body = BV._make_obj(bm, "Body", root, m_paint, subsurf=1)

    # Greenhouse
    gh = P["gh"]
    bm = bmesh.new()
    gr = []
    for y, hw, z in gh:
        bump = 0.025 if z > 1.2 else 0.0
        gr.append([bm.verts.new(p) for p in ((-hw, y, z), (-hw * 0.55, y, z + bump), (hw * 0.55, y, z + bump), (hw, y, z))])
    for r0, r1 in zip(gr, gr[1:]):
        for i in range(3):
            bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i]))
    zb0 = gh[0][2]
    for k in range(len(gh) - 1):
        a = bm.verts.new((gh[k][1], gh[k][0], zb0 - 0.02))
        b = bm.verts.new((gh[k + 1][1], gh[k + 1][0], zb0 - 0.01))
        bm.faces.new((a, b, gr[k + 1][3], gr[k][3]))
        c = bm.verts.new((-gh[k][1], gh[k][0], zb0 - 0.02))
        d = bm.verts.new((-gh[k + 1][1], gh[k + 1][0], zb0 - 0.01))
        bm.faces.new((d, c, gr[k][0], gr[k + 1][0]))
    for sx in (-1.0, 1.0):
        BV._add_box(bm, (sx * (st[3][2] + 0.01), gh[0][0] + 0.25, zb0 + 0.07), (0.14, 0.09, 0.07), bevel=0.015, segs=2)
    cabin = BV._make_obj(bm, "Cabin", root, m_paint, subsurf=0)
    for m in (m_glass, m_chrome, m_trim, m_head, m_tail):
        body.data.materials.append(m)
        cabin.data.materials.append(m)
    roof_z = max(z for (_y, _w, z) in gh)
    gy_max = P.get("glass_y_max", 99.0)
    for p in cabin.data.polygons:
        c = p.center
        if c.z < roof_z - 0.03 and abs(c.x) < max(w for (_y, w, _z) in gh) + 0.02 and c.y < gy_max:
            p.material_index = 1
    for p in body.data.polygons:
        c = p.center
        if c.y < y0 + 0.12 and abs(c.x) < 0.42 and 0.4 < c.z < st[0][4] + 0.02:
            p.material_index = 2                                  # grille
        elif c.y < y0 + 0.16 and 0.46 < abs(c.x) < 0.86 and 0.45 < c.z < st[0][4] + 0.02:
            p.material_index = 4                                  # headlights
        elif c.y > y1 - 0.16 and 0.35 < abs(c.x) < 0.86 and 0.5 < c.z < st[-1][4] + 0.02:
            p.material_index = 5                                  # taillights

    # Panels
    if P.get("hood"):
        (c, s, tilt) = P["hood"]
        bm = bmesh.new()
        BV._add_box(bm, c, s, rot=(math.radians(tilt), 0, 0), bevel=0.014, segs=2)
        BV._make_obj(bm, "Hood", root, m_paint, origin_world=(c[0], c[1] + s[1] / 2, c[2] + 0.03))
    if P.get("trunk"):
        (c, s, tilt) = P["trunk"]
        bm = bmesh.new()
        BV._add_box(bm, c, s, rot=(math.radians(tilt), 0, 0), bevel=0.014, segs=2)
        BV._make_obj(bm, "Trunk", root, m_paint, origin_world=(c[0], c[1] - s[1] / 2, c[2] + 0.02))
    for bname, yb, zb in (("Bumper_F", y0 + 0.10, st[0][3] + 0.10), ("Bumper_R", y1 - 0.10, st[-1][3] + 0.10)):
        bm = bmesh.new()
        BV._add_box(bm, (0.0, yb, zb), (st[1][1] * 1.9, 0.22, 0.21), bevel=0.035, segs=2)
        BV._make_obj(bm, bname, root, m_chrome if "pushbar" in P["extras"] and bname == "Bumper_F" else m_trim, origin_world=(0.0, yb, zb))

    # Doors (+ livery decal on the front doors)
    dz, dh = P.get("door_h", (st[3][3] + (st[3][4] - st[3][3]) * 0.55, (st[3][4] - st[3][3]) * 0.82))
    livery = P.get("livery")
    m_liv = m_liv2 = None
    if livery:
        m_liv = _label_mat(f"{name}_Livery", livery[0], livery[1], livery[2], 512, 128)
        m_liv2 = _label_mat(f"{name}_LiverySub", livery[3], livery[1], livery[2], 512, 64)
    for dname, sx, yh, ymid, dlen in P["doors"]:
        bm = bmesh.new()
        xw = st[3][2] - 0.035
        BV._add_box(bm, (sx * xw, ymid, dz), (0.040, dlen, dh), bevel=0.012, segs=2)
        BV._add_box(bm, (sx * (xw + 0.027), ymid + dlen * 0.30, dz + dh * 0.28), (0.018, 0.11, 0.030), bevel=0.006, segs=1)
        n_before = len(bm.faces)
        has_liv = m_liv is not None and dname in ("Door_FL", "Door_FR", "Door_RL", "Door_RR")
        if has_liv:
            x = sx * (xw + 0.0215)
            hl = dlen * 0.42
            ztop, zbot = dz + dh * 0.12, dz - dh * 0.12
            # quad faces outward (+x for sx>0) and reads front-to-back from outside
            if sx > 0:
                _quad(bm, [(x, ymid + hl, zbot), (x, ymid - hl, zbot), (x, ymid - hl, ztop), (x, ymid + hl, ztop)])
            else:
                _quad(bm, [(x, ymid - hl, zbot), (x, ymid + hl, zbot), (x, ymid + hl, ztop), (x, ymid - hl, ztop)])
        ob = _make_door(bm, dname, root, m_door, (sx * (xw - 0.015), yh, dz), n_before, m_liv if has_liv else None)
    # Wheels
    tw, wb, yf, wr = P["track"], P["wheelbase"], P["y_front"], P["wheel_r"]
    for wname, wx, wy in (("Wheel_FL", tw / 2, yf), ("Wheel_FR", -tw / 2, yf), ("Wheel_RL", tw / 2, yf + wb), ("Wheel_RR", -tw / 2, yf + wb)):
        BV._build_wheel(wname, root, (wx, wy, wr), wr, P["wheel_w"], m_tire, m_rim)

    # Extras (merged into Cabin-free 'Body' children would change names: keep them in a trim mesh named Bumper-safe)
    bm = bmesh.new()
    mats = [m_trim]
    if "lightbar" in P["extras"]:
        m_red = BV._mat(f"M_{name}_LightRed", (0.9, 0.05, 0.05, 1.0), roughness=0.1, emit=2.0)
        m_blue = BV._mat(f"M_{name}_LightBlue", (0.05, 0.2, 0.95, 1.0), roughness=0.1, emit=2.0)
        mats += [m_red, m_blue]
        BV._add_box(bm, (0.0, 0.10, roof_z + 0.07), (1.20, 0.26, 0.05), bevel=0.01, segs=1)
        for sx, mi in ((0.33, 1), (-0.33, 2)):
            for v in BV._add_box(bm, (sx, 0.10, roof_z + 0.14), (0.52, 0.24, 0.10), bevel=0.02, segs=1):
                pass
    if "pushbar" in P["extras"]:
        for sx in (-0.35, 0.35):
            BV._add_box(bm, (sx, y0 - 0.12, st[0][3] + 0.32), (0.06, 0.06, 0.55), bevel=0.01, segs=1)
        BV._add_box(bm, (0.0, y0 - 0.12, st[0][3] + 0.52), (0.86, 0.06, 0.06), bevel=0.01, segs=1)
    if "roofsign" in P["extras"]:
        m_sign = _label_mat(f"{name}_RoofSign", "TAXI", "1a1a1a", "f4e7a2", 256, 128)
        mats.append(m_sign)
        BV._add_box(bm, (0.0, 0.15, roof_z + 0.16), (0.62, 0.18, 0.26), bevel=0.02, segs=1)
    if "scoop" in P["extras"]:
        BV._add_box(bm, (0.0, -1.35, 0.90), (0.50, 0.70, 0.09), rot=(math.radians(3), 0, 0), bevel=0.03, segs=2)
    if "ducktail" in P["extras"]:
        BV._add_box(bm, (0.0, y1 - 0.30, st[-2][4] + 0.05), (1.50, 0.14, 0.05), bevel=0.02, segs=1)
    if "roofrack" in P["extras"]:
        for sx in (-0.75, 0.75):
            BV._add_box(bm, (sx, 0.6, roof_z + 0.10), (0.05, 3.2, 0.05), bevel=0.01, segs=1)
        for yy in (-0.6, 0.2, 1.0, 1.8):
            BV._add_box(bm, (0.0, yy, roof_z + 0.12), (1.55, 0.05, 0.04), bevel=0.01, segs=1)
    if "bedrails" in P["extras"]:
        for sx in (-0.93, 0.93):
            BV._add_box(bm, (sx, 1.80, (P.get("belt_trim") or 1.1) + 0.03), (0.08, 1.90, 0.05), bevel=0.01, segs=1)
    if "tailgate" in P["extras"]:
        BV._add_box(bm, (0.0, y1 + 0.005, 0.86), (1.70, 0.03, 0.40), bevel=0.01, segs=1)
    if "reardoors" in P["extras"]:
        BV._add_box(bm, (0.0, y1 + 0.005, 1.25), (0.02, 0.03, 1.60), bevel=0.0, segs=1)
    if "stripes" in P["extras"]:
        m_white = BV._mat(f"M_{name}_Stripe", (0.88, 0.88, 0.86, 1.0), roughness=0.25, metallic=0.3, coat=1.0)
        mats.append(m_white)
        for sx in (-0.16, 0.16):
            BV._add_box(bm, (sx, -1.48, 0.86), (0.14, 1.86, 0.008), rot=(math.radians(3), 0, 0), bevel=0.0, segs=1)
    if bm.faces:
        # 'Frame' is an allowed functional name (TD-005): light bar, racks, scoops ride on it
        fr = BV._make_obj(bm, "Frame", root, mats[0], subsurf=0)
        for m in mats[1:]:
            fr.data.materials.append(m)
        if "lightbar" in P["extras"]:
            for p in fr.data.polygons:
                if p.center.z > roof_z + 0.10 and abs(p.center.y - 0.10) < 0.13:
                    p.material_index = 1 if p.center.x > 0 else 2
        if "roofsign" in P["extras"]:
            mi = mats.index(m_sign)
            for p in fr.data.polygons:
                if p.center.z > roof_z + 0.05 and abs(p.normal.y) > 0.9 and abs(p.center.x) < 0.28:
                    p.material_index = mi
            _decal_uv(fr, mi)
            fr["uw_allow_uv_overlap"] = 1
        if "stripes" in P["extras"]:
            mi = mats.index(m_white)
            for p in fr.data.polygons:
                if p.center.y < -0.4 and p.center.z < 0.95 and abs(p.center.x) < 0.3 and p.center.z > 0.8:
                    p.material_index = mi

    # Collision: convex hull of the lower body + cabin boxes (wheel arches stay clear)
    (lx, ly, lz, lzc), (cx, cy, cz, czc, cyo) = P["col"]
    bm = bmesh.new()
    BV._add_box(bm, (0.0, 0.0, lzc), (lx, ly, lz), bevel=0.05, segs=1)
    BV._add_box(bm, (0.0, cyo, czc), (cx, cy, cz), bevel=0.05, segs=1)
    res = bmesh.ops.convex_hull(bm, input=bm.verts)
    hull = {g for g in res["geom"] if isinstance(g, bmesh.types.BMFace)}
    # keep ONLY the hull: the source boxes' faces would stay inside it as non-manifold junk
    # (VH_Sedan_01's collision fails the release gate for exactly this reason)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in hull], context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context="EDGES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges], context="VERTS")
    me = bpy.data.meshes.new(f"UCX_{name}-convcolonly")
    bm.to_mesh(me)
    bm.free()
    co = bpy.data.objects.new(f"UCX_{name}-convcolonly", me)
    sc.collection.objects.link(co)
    co.parent = root

    sx_, sy_, sz_ = P["seat"]
    half_w = st[3][2]
    for sname, loc in (("SOCKET_Seat_Driver", (sx_, sy_, sz_)), ("SOCKET_Seat_Passenger", (-sx_, sy_, sz_)),
                       ("SOCKET_Exit_Left", (half_w + 0.45, sy_ - 0.08, 0.0)), ("SOCKET_Exit_Right", (-half_w - 0.45, sy_ - 0.08, 0.0)),
                       ("SOCKET_Headlight_L", (0.68, y0 - 0.02, st[0][4] - 0.07)), ("SOCKET_Headlight_R", (-0.68, y0 - 0.02, st[0][4] - 0.07)),
                       ("SOCKET_Taillight_L", (0.68, y1 + 0.02, st[-1][4] - 0.12)), ("SOCKET_Taillight_R", (-0.68, y1 + 0.02, st[-1][4] - 0.12))):
        s = bpy.data.objects.new(sname, None)
        s.empty_display_type, s.empty_display_size = "ARROWS", 0.25
        sc.collection.objects.link(s)
        s.parent, s.location = root, loc
    root["uw_wheel_radius_m"] = wr
    root["uw_wheelbase_m"] = wb
    root["uw_track_width_m"] = tw
    p = os.path.join(repo_root, "Blender", "Source", "Vehicles", name, f"{name}.blend")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=p, compress=True)
    print(f"[VEHICLE] built {name} (wheel_r={wr}, wheelbase={wb}, track={tw}) -> {os.path.relpath(p, repo_root)}")
    return p


def _make_door(bm, name, parent, mat, origin, n_body_faces, m_liv):
    """Like build_vehicle._make_obj (hinge origin, smart UV) but keeps the livery quad's winding
    (no global recalc) and gives it its own material + upright 0..1 UVs."""
    from mathutils import Vector
    body_faces = list(bm.faces)[:n_body_faces]
    bmesh.ops.recalc_face_normals(bm, faces=body_faces)
    for f in bm.faces:
        f.smooth = True
    for i, f in enumerate(bm.faces):
        f.material_index = 0 if i < n_body_faces else 1
    for v in bm.verts:
        v.co -= Vector(origin)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    ob.location = origin
    me.materials.append(mat)
    if m_liv is not None:
        me.materials.append(m_liv)
    BV._smart_uv(ob)
    if m_liv is not None:
        _decal_uv(ob, 1)
        ob["uw_allow_uv_overlap"] = 1        # livery decal has its own 0..1 UVs over the panel
    return ob


def build_vehicles(repo_root, only=None):
    names = list(PROFILES) if not only else [n.strip() for n in only.split(",")]
    bad = [n for n in names if n not in PROFILES]
    if bad:
        raise SystemExit(f"[VEHICLE] unknown id(s): {bad}; known: {sorted(PROFILES)}")
    return [build_from_profile(n, repo_root) for n in names]
