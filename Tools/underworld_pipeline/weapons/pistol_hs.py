"""WPN_Pistol_01 parts: generic modern polymer-frame striker pistol (no real-world brand/logo).

Proportions from the reference board Docs/ArtDirection/References/WPN_Pistol_01/ (full-size slide on a compact
grip, ~0.19 m x 0.13 m x 0.03 m). Built directly in contract coordinates (REQ_WPN_Pistol_01, TD-004):
origin = grip point, barrel -Y, up +Z, bore axis z = 0.041, gun's right side = -X (ejection port).
Each function returns {node_name: [objects]}; hp=True adds bake-only detail.
"""
import math

from . import hardsurface as H

# ---- key dimensions (m)
SL_R, SL_F = 0.0280, -0.1580          # slide rear / front face
SL_B, SL_T = 0.0275, 0.0540           # slide bottom / top flat (~27 mm slide height like the board)
SL_W = 0.01275                        # slide half width
SL_CH = 0.0500                        # top chamfer starts here (sides vertical below)
BORE_Z = 0.041
PORT_Y = (-0.0650, -0.0290)           # ejection port (right side, -X)
FR_W = 0.0115                         # dust cover half width
GR_W = 0.0148                         # grip half width
GUARD_W = 0.0048                      # trigger guard half width
GRIP_BOT = -0.0655
TRIG_Y = -0.0530
RAKE = math.radians(20.0)             # grip rake measured on board tile R3 (front strap 21 deg, back strap ~20 deg)
GUIDE_Z = 0.0285                      # recoil spring guide rod axis (half in slide, half in dust cover)
MAG_YB = -0.0098                      # magazine body front at the grip bottom
MAG_D = 0.0322                        # magazine fore-aft depth (double stack 9 mm)


def _interp(tab, z, smooth=True):
    for (z0, v0), (z1, v1) in zip(tab, tab[1:]):
        if z <= z1:
            f = min(max((z - z0) / (z1 - z0), 0.0), 1.0)
            if smooth:
                f = f * f * (3 - 2 * f)      # smoothstep between keys (back strap curves); front strap stays straight
            return v0 + (v1 - v0) * f
    return tab[-1][1]


# grip side profile (z -> y), measured from board tile R3 scaled to the 0.186 m slide
GRIP_BACK = [(GRIP_BOT, 0.0405), (-0.050, 0.0352), (-0.035, 0.0312), (-0.0136, 0.0222), (0.000, 0.0168),
             (0.010, 0.0148), (0.017, 0.0168), (0.022, 0.0250), (0.0255, 0.0300), (SL_B, 0.0312)]
GRIP_FRONT = [(GRIP_BOT, -0.0152), (-0.0136, -0.0340), (-0.0040, -0.0362), (SL_B, -0.0362)]
GRIP_HALF_W = [(GRIP_BOT, 0.0156), (-0.052, 0.0149), (0.004, 0.0148), (0.014, 0.0116), (SL_B, 0.0116)]


def grip_shell(hp):
    """Raked grip as a superellipse loft: front/back strap from GRIP_FRONT/GRIP_BACK, palm swell, beavertail tang
    up under the slide, slight flare at the magazine well."""
    seg, nz = (64, 44) if hp else (32, 16)   # LP: enough segments that no grip edge exceeds the 30 deg hard-edge angle (no seams on the straps)
    zs = [GRIP_BOT + (SL_B - GRIP_BOT) * (i / (nz - 1)) for i in range(nz)]
    rings = []
    for z in zs:
        yf, yb, w = _interp(GRIP_FRONT, z, smooth=False), _interp(GRIP_BACK, z), _interp(GRIP_HALF_W, z)
        rings.append([(x, y, z) for x, y in H.superellipse(0.0, (yf + yb) / 2, w, (yb - yf) / 2, 2.7, seg)])
    return H.loft("Grip", rings)


def sbox(name, sx, inner, outer, y0, y1, z0, z1):
    """Box on the side sx (+1 left/+X, -1 right/-X) spanning |x| in [inner, outer]."""
    a, b = sx * inner, sx * outer
    return H.box(name, min(a, b), max(a, b), y0, y1, z0, z1)


def slide(hp, M):
    seg = 3 if hp else 1
    sec = [(-SL_W, SL_B), (SL_W, SL_B), (SL_W, SL_CH), (SL_W - 0.0032, SL_T), (-SL_W + 0.0032, SL_T), (-SL_W, SL_CH)]
    s = H.prism("Slide_body", sec, "Y", SL_F, SL_R)
    cut = [
        # nose: top-front chamfer, bottom-front taper, side tapers (modern "dehorned" nose)
        H.plane_yz("c_nose_top", (SL_F + 0.0060, SL_T + 0.0001), (SL_F - 0.0001, SL_T - 0.0045), (-1, 1)),
        H.plane_yz("c_nose_bot", (SL_F + 0.0060, SL_B - 0.0001), (SL_F - 0.0001, SL_B + 0.0012), (-1, -1)),
        H.halfspace("c_nose_l", (SL_W - 0.0016, SL_F, 0), (0.98, -0.20, 0)),
        H.halfspace("c_nose_r", (-SL_W + 0.0016, SL_F, 0), (-0.98, -0.20, 0)),
        # rear: slight undercut so the slide rear does not look like a brick
        H.plane_yz("c_rear_top", (SL_R - 0.0030, SL_T + 0.0001), (SL_R + 0.0001, SL_T - 0.0025), (1, 1)),
        # ejection port: right side (-X) and over the top
        H.box("c_port", -0.030, 0.0045, PORT_Y[0], PORT_Y[1], 0.0330, 0.070),
        # muzzle opening for the barrel + recoil spring guide hole
        H.cyl("c_muz", 0.0071, "Y", SL_F - 0.01, SL_F + 0.016, 0.0, BORE_Z, 48 if hp else 28),
        H.cyl("c_guide", 0.0031, "Y", SL_F - 0.01, SL_F + 0.012, 0.0, GUIDE_Z, 32 if hp else 16),
    ]
    if hp:
        cut.append(H.box("c_plate", -0.0078, 0.0078, SL_R - 0.0004, SL_R + 0.01, 0.0310, SL_T - 0.0060))   # slide cover plate
    H.boolean(s, cut)
    # cocking serrations are real geometry in BOTH meshes (silhouette at the top chamfer, proper shading at close range)
    ser = []
    for sx in (1, -1):
        for i in range(10):          # rear cocking serrations
            y = 0.0240 - i * 0.0031
            ser.append(sbox("c_ser", sx, SL_W - 0.0007, SL_W + 0.003, y - 0.00065, y + 0.00065, SL_B + 0.0022, SL_T + 0.002))
        for i in range(7):           # front serrations
            y = SL_F + 0.0115 + i * 0.0031
            ser.append(sbox("c_ser", sx, SL_W - 0.0007, SL_W + 0.003, y - 0.00065, y + 0.00065, SL_B + 0.0040, SL_T + 0.002))
    H.cut_batch(s, ser)
    if hp:
        H.boolean(s, [H.engraving("9x19", SL_W - 0.0002, -0.092, 0.0385, 0.0042, side=1)])
    s = H.bevel(s, 0.0007 if hp else 0.0006, seg, angle=30)
    parts = [H.set_mat(s, M["steel"])]
    # extractor (right side, behind the port) and sights (dovetailed steel, three white dots)
    ex = H.box("Extractor", -SL_W - 0.0004, -SL_W + 0.0010, PORT_Y[1] + 0.0004, PORT_Y[1] + 0.0170, 0.0400, 0.0442)
    parts.append(H.set_mat(H.bevel(ex, 0.0003, seg), M["steel"]))
    fs = H.prism("FrontSight", [(-0.1505, SL_T - 0.0006), (-0.1440, SL_T - 0.0006), (-0.1445, SL_T + 0.0045), (-0.1490, SL_T + 0.0045)], "X", -0.0017, 0.0017)
    parts.append(H.set_mat(H.bevel(fs, 0.0003, seg), M["steel"]))
    rs = H.prism("RearSight", [(0.0120, SL_T - 0.0006), (0.0222, SL_T - 0.0006), (0.0222, SL_T + 0.0047), (0.0160, SL_T + 0.0049), (0.0130, SL_T + 0.0033)],
                 "X", -0.0088, 0.0088)
    H.boolean(rs, [H.box("c_notch", -0.0017, 0.0017, 0.0, 0.04, SL_T + 0.0023, 0.08)])
    parts.append(H.set_mat(H.bevel(rs, 0.0004, seg), M["steel"]))
    if hp:
        parts.append(H.set_mat(H.cyl("Dot_F", 0.0008, "Y", -0.1444, -0.1436, 0.0, SL_T + 0.0034, 16), M["white"]))
        for sx in (1, -1):
            parts.append(H.set_mat(H.cyl("Dot_R", 0.0008, "Y", 0.0221, 0.0228, sx * 0.0052, SL_T + 0.0036, 16), M["white"]))
    return {"Slide": parts}


def barrel(hp, M):
    seg = 3 if hp else 1
    br = H.cyl("Barrel_tube", 0.0069, "Y", SL_F + 0.0003, PORT_Y[0] - 0.002, 0.0, BORE_Z, 48 if hp else 28)
    H.boolean(br, [H.cyl("c_bore", 0.0045, "Y", SL_F - 0.01, SL_F + 0.030, 0.0, BORE_Z, 40 if hp else 20)])
    br = H.bevel(br, 0.0005 if hp else 0.0004, seg, angle=50)
    hood = H.box("Hood", -0.0094, 0.0094, PORT_Y[0] - 0.0020, PORT_Y[1] + 0.0020, 0.0335, SL_T - 0.0007)
    if hp:   # loaded-chamber witness notch + breech face chamfer
        H.boolean(hood, [H.box("c_witness", -0.0012, 0.0012, PORT_Y[1] + 0.0005, PORT_Y[1] + 0.0030, SL_T - 0.0020, 0.06)])
    hood = H.bevel(hood, 0.0006 if hp else 0.0005, seg, angle=40)
    parts = [H.set_mat(br, M["barrel"]), H.set_mat(hood, M["barrel"])]
    if hp:   # dark bore interior
        parts.append(H.set_mat(H.cyl("Bore", 0.00455, "Y", SL_F + 0.0015, SL_F + 0.028, 0.0, BORE_Z, 32), M["bore"]))
    return {"Barrel": parts}


def frame(hp, M):
    seg = 3 if hp else 1
    # upper frame: dust cover + trigger guard (solid; the opening is cut below) + area above the grip
    up = [(-0.1545, SL_B), (-0.1552, 0.0190), (-0.1535, 0.0158), (-0.1000, 0.0154), (-0.0938, 0.0150),
          (-0.0952, 0.0030), (-0.0962, -0.0065), (-0.0945, -0.0118), (-0.0900, -0.0142), (-0.0500, -0.0147),
          (-0.0400, -0.0152), (-0.0330, -0.0165), (-0.0300, -0.0040), (-0.0280, SL_B)]
    upper = H.prism("Upper", up, "X", -FR_W, FR_W)
    grip = grip_shell(hp)
    if not hp:   # tag the game-mesh grip faces (survives the unions) so the baker unwraps them as one seamless sheet
        H.set_mat(grip, M["grip_lp"])
    if not hp:
        H.set_mat(upper, M["polymer"])
    H.boolean(upper, [grip], op="UNION", transfer_materials=not hp)
    fr = upper
    fr.name = "Frame_body"
    # trigger guard opening + narrow guard sides
    hole = [(-0.0848, 0.0128), (-0.0862, 0.0020), (-0.0868, -0.0060), (-0.0848, -0.0094), (-0.0800, -0.0102),
            (-0.0490, -0.0102), (-0.0430, -0.0092), (-0.0402, -0.0040), (-0.0404, 0.0040), (-0.0420, 0.0128)]
    hole = H.chaikin(hole, 2)
    side = [(-0.1100, 0.0118), (-0.0420, 0.0118), (-0.0395, 0.0040), (-0.0375, -0.0200), (-0.1100, -0.0200)]
    H.boolean(fr, [H.prism("c_hole", hole, "X", -0.05, 0.05),
                   H.prism("c_gs_l", side, "X", GUARD_W, 0.05), H.prism("c_gs_r", side, "X", -0.05, -GUARD_W)])
    # magazine well (flared opening at the bottom of the grip)
    yb = MAG_YB - 0.0008
    t = math.tan(RAKE)
    well = [(yb + 0.010 * t, GRIP_BOT - 0.01), (yb + MAG_D + 0.0016 + 0.010 * t, GRIP_BOT - 0.01),
            (yb + MAG_D + 0.0016 + (GRIP_BOT + 0.053) * t, -0.0530), (yb + (GRIP_BOT + 0.053) * t, -0.0530)]
    H.boolean(fr, [H.prism("c_well", well, "X", -0.0099, 0.0099)])
    # recoil-spring guide channel under the barrel (rod cap visible at the nose)
    H.boolean(fr, [H.cyl("c_guide", 0.0031, "Y", SL_F - 0.01, SL_F + 0.024, 0.0, GUIDE_Z, 32 if hp else 16)])
    # accessory rail under the dust cover
    rail = H.box("Rail", -0.0095, 0.0095, -0.1500, -0.1030, 0.0118, 0.0160)
    H.cut_batch(rail, [H.box("c_slot", -0.02, 0.02, y - 0.0021, y + 0.0021, 0.0100, 0.0137) for y in (-0.1420, -0.1315, -0.1210, -0.1105)])
    H.boolean(fr, [rail], op="UNION")
    fr = H.bevel(fr, 0.0010 if hp else 0.0008, seg, angle=35)
    parts = [H.set_mat(fr, M["polymer"]) if hp else fr]   # LP keeps the grip-sheet tag from the union
    # controls (steel): slide stop (left), takedown lever (both sides), polymer magazine release (left)
    ss = H.prism("SlideStop", [(-0.0360, 0.0234), (-0.0205, 0.0234), (-0.0195, 0.0262), (-0.0230, 0.0272),
                               (-0.0360, 0.0272)], "X", 0.0110, 0.0127)
    parts.append(H.set_mat(H.bevel(ss, 0.0004, seg), M["steel"]))
    for sx in (1, -1):
        td = H.box("Takedown", min(sx * 0.0108, sx * 0.0122), max(sx * 0.0108, sx * 0.0122), -0.0725, -0.0645, 0.0200, 0.0255)
        parts.append(H.set_mat(H.bevel(td, 0.0003, seg), M["steel"]))
    mr = H.box("MagRelease", 0.0128, 0.0156, -0.0352, -0.0268, -0.0092, -0.0016)
    if hp:
        H.cut_batch(mr, [H.box("c_mrs", 0.0153, 0.02, y - 0.0003, y + 0.0003, -0.02, 0.01) for y in (-0.0332, -0.0317, -0.0302, -0.0287)])
    parts.append(H.set_mat(H.bevel(mr, 0.0005, seg), M["polymer_plain"]))
    if hp:
        for (y, z, hw) in ((-0.0580, 0.0215, FR_W + 0.0002), (-0.0130, 0.0175, 0.0120), (-0.0345, 0.0085, 0.0123)):
            parts.append(H.set_mat(H.cyl("Pin", 0.0012, "X", -hw, hw, y, z, 20), M["steel"]))
    rod = H.cyl("GuideRod", 0.0025, "Y", SL_F + 0.0035, SL_F + 0.030, 0.0, GUIDE_Z, 24 if hp else 12)
    if hp:
        H.boolean(rod, [H.cyl("c_rod", 0.0011, "Y", SL_F, SL_F + 0.006, 0.0, GUIDE_Z, 16)])
    parts.append(H.set_mat(H.bevel(rod, 0.0003, seg, angle=50), M["barrel"]))
    return {"Frame": parts}


def trigger(hp, M):
    seg = 3 if hp else 1
    c = H.chaikin([(TRIG_Y + 0.0012, 0.0150), (TRIG_Y + 0.0004, 0.0060), (TRIG_Y - 0.0016, 0.0000), (TRIG_Y - 0.0046, -0.0048)], 2, closed=False)
    tr = H.sweep("Trigger_blade", c, 0.0040, 0.0029)
    tr = H.bevel(tr, 0.0008 if hp else 0.0006, seg, angle=35)
    parts = [H.set_mat(tr, M["polymer_plain"])]
    sb = H.sweep("Safety", H.chaikin([(TRIG_Y - 0.0012, 0.0040), (TRIG_Y - 0.0030, -0.0010), (TRIG_Y - 0.0055, -0.0042)], 2, closed=False),
                 0.0030, 0.0009)
    sb.location.y -= 0.0010
    H.apply_loc(sb)
    parts.append(H.set_mat(H.bevel(sb, 0.0003, 2 if hp else 1), M["polymer_plain"]))
    return {"Trigger": parts}


def magazine(hp, M):
    seg = 3 if hp else 1
    t = math.tan(RAKE)
    yb = MAG_YB
    h = -0.0100 - GRIP_BOT
    body = [(yb, GRIP_BOT), (yb + MAG_D, GRIP_BOT), (yb + MAG_D - h * t, -0.0100), (yb - h * t, -0.0100)]
    b = H.prism("MagBody", body, "X", -0.0092, 0.0092)
    b = H.bevel(b, 0.0008, seg)
    plate = H.chaikin([(yb - 0.0036, GRIP_BOT + 0.0002), (0.0402, GRIP_BOT + 0.0002), (0.0410, GRIP_BOT - 0.0040),
                       (0.0392, GRIP_BOT - 0.0068), (yb - 0.0008, GRIP_BOT - 0.0068), (yb - 0.0044, GRIP_BOT - 0.0044)], 1)
    p = H.prism("MagPlate", plate, "X", -0.0140, 0.0140)
    p = H.bevel(p, 0.0014 if hp else 0.0012, seg + 1, angle=40)
    return {"Magazine": [H.set_mat(b, M["magsteel"]), H.set_mat(p, M["polymer_plain"])]}


def build(hp, M):
    out = {}
    for fn in (frame, slide, barrel, trigger, magazine):
        out.update(fn(hp, M))
    return out
