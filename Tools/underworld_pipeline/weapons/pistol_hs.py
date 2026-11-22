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
SL_B, SL_T = 0.0275, 0.0515           # slide bottom / top flat
SL_W = 0.01275                        # slide half width
SL_CH = 0.0475                        # top chamfer starts here (sides vertical below)
BORE_Z = 0.041
PORT_Y = (-0.0650, -0.0290)           # ejection port (right side, -X)
FR_W = 0.0115                         # dust cover half width
GR_W = 0.0148                         # grip half width
GUARD_W = 0.0062                      # trigger guard half width
GRIP_BOT = -0.0655
TRIG_Y = -0.0530
RAKE = math.radians(17.0)
GUIDE_Z = 0.0285                      # recoil spring guide rod axis (half in slide, half in dust cover)
MAG_YB = -0.0400 + 0.0615 * math.tan(RAKE) + 0.0030   # magazine body front at the grip bottom


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
        H.cyl("c_muz", 0.0071, "Y", SL_F - 0.01, SL_F + 0.016, 0.0, BORE_Z, 40 if hp else 20),
        H.cyl("c_guide", 0.0031, "Y", SL_F - 0.01, SL_F + 0.012, 0.0, GUIDE_Z, 32 if hp else 16),
    ]
    if hp:
        cut.append(H.box("c_plate", -0.0078, 0.0078, SL_R - 0.0004, SL_R + 0.01, 0.0305, 0.0460))   # slide cover plate
    H.boolean(s, cut)
    if hp:
        ser = []
        for sx in (1, -1):
            for i in range(10):          # rear cocking serrations
                y = 0.0240 - i * 0.0031
                ser.append(sbox("c_ser", sx, SL_W - 0.0007, SL_W + 0.003, y - 0.00065, y + 0.00065, SL_B + 0.0022, SL_T + 0.002))
            for i in range(7):           # front serrations
                y = SL_F + 0.0115 + i * 0.0031
                ser.append(sbox("c_ser", sx, SL_W - 0.0007, SL_W + 0.003, y - 0.00065, y + 0.00065, SL_B + 0.0040, SL_T + 0.002))
        H.cut_batch(s, ser)
        H.boolean(s, [H.engraving("9x19", SL_W - 0.0002, -0.092, 0.0385, 0.0042, side=1)])
    s = H.bevel(s, 0.0007 if hp else 0.0006, seg, angle=30)
    parts = [H.set_mat(s, M["steel"])]
    # extractor (right side, behind the port) and sights (dovetailed steel, three white dots)
    ex = H.box("Extractor", -SL_W - 0.0004, -SL_W + 0.0010, PORT_Y[1] + 0.0004, PORT_Y[1] + 0.0170, 0.0400, 0.0442)
    parts.append(H.set_mat(H.bevel(ex, 0.0003, seg), M["steel"]))
    fs = H.prism("FrontSight", [(-0.1505, SL_T - 0.0006), (-0.1440, SL_T - 0.0006), (-0.1445, 0.0560), (-0.1490, 0.0560)], "X", -0.0017, 0.0017)
    parts.append(H.set_mat(H.bevel(fs, 0.0003, seg), M["steel"]))
    rs = H.prism("RearSight", [(0.0120, SL_T - 0.0006), (0.0222, SL_T - 0.0006), (0.0222, 0.0562), (0.0160, 0.0564), (0.0130, 0.0548)],
                 "X", -0.0088, 0.0088)
    H.boolean(rs, [H.box("c_notch", -0.0017, 0.0017, 0.0, 0.04, 0.0538, 0.07)])
    parts.append(H.set_mat(H.bevel(rs, 0.0004, seg), M["steel"]))
    if hp:
        parts.append(H.set_mat(H.cyl("Dot_F", 0.0008, "Y", -0.1444, -0.1436, 0.0, 0.0549, 16), M["white"]))
        for sx in (1, -1):
            parts.append(H.set_mat(H.cyl("Dot_R", 0.0008, "Y", 0.0221, 0.0228, sx * 0.0052, 0.0551, 16), M["white"]))
    return {"Slide": parts}


def barrel(hp, M):
    seg = 3 if hp else 1
    br = H.cyl("Barrel_tube", 0.0069, "Y", SL_F + 0.0003, PORT_Y[0] - 0.002, 0.0, BORE_Z, 40 if hp else 20)
    H.boolean(br, [H.cyl("c_bore", 0.0045, "Y", SL_F - 0.01, SL_F + 0.030, 0.0, BORE_Z, 32 if hp else 16)])
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
    # grip: raked front strap (17 deg), palm-swell back strap, beavertail
    t = math.tan(RAKE)
    front = [(-0.0400 if z > -0.004 else -0.0400 + (-0.004 - z) * t, z)
             for z in (0.0100, -0.0040, -0.0120, -0.0220, -0.0320, -0.0420, -0.0520, -0.0600)]
    flare = [(-0.0238, -0.0635), (-0.0236, GRIP_BOT)]
    back = [(0.0395, GRIP_BOT), (0.0408, -0.0620), (0.0404, -0.0500), (0.0393, -0.0380), (0.0372, -0.0240),
            (0.0350, -0.0110), (0.0338, 0.0010), (0.0343, 0.0090), (0.0366, 0.0150), (0.0372, 0.0205),
            (0.0350, 0.0245), (0.0300, SL_B), (-0.0280, SL_B)]
    gprof = H.chaikin(front + flare + back, 1)
    grip = H.prism("Grip", gprof, "X", -GR_W, GR_W)
    # taper the grip to the slide width above the thumb line
    H.boolean(grip, [H.halfspace("c_gt_l", (0.0118, 0, 0.0100), (0.95, 0, 0.31)),
                     H.halfspace("c_gt_r", (-0.0118, 0, 0.0100), (-0.95, 0, 0.31)),
                     H.box("c_top_l", 0.0118, 0.05, -0.1, 0.1, 0.0100, 0.05),
                     H.box("c_top_r", -0.05, -0.0118, -0.1, 0.1, 0.0100, 0.05)])
    grip = H.bevel(grip, 0.0045 if hp else 0.0040, 5 if hp else 2, angle=50, profile=0.6)
    H.boolean(upper, [grip], op="UNION")
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
    well = [(yb + 0.010 * t, GRIP_BOT - 0.01), (yb + 0.0326 + 0.010 * t, GRIP_BOT - 0.01),
            (yb + 0.0326 + (0.048 + GRIP_BOT) * t, -0.0480), (yb + (0.048 + GRIP_BOT) * t, -0.0480)]
    H.boolean(fr, [H.prism("c_well", well, "X", -0.0102, 0.0102)])
    # recoil-spring guide channel under the barrel (rod cap visible at the nose)
    H.boolean(fr, [H.cyl("c_guide", 0.0031, "Y", SL_F - 0.01, SL_F + 0.024, 0.0, GUIDE_Z, 32 if hp else 16)])
    # accessory rail under the dust cover
    rail = H.box("Rail", -0.0095, 0.0095, -0.1500, -0.1030, 0.0118, 0.0160)
    H.cut_batch(rail, [H.box("c_slot", -0.02, 0.02, y - 0.0021, y + 0.0021, 0.0100, 0.0137) for y in (-0.1420, -0.1315, -0.1210, -0.1105)])
    H.boolean(fr, [rail], op="UNION")
    if hp:   # dust cover side rail groove
        H.cut_batch(fr, [sbox("c_dg", sx, FR_W - 0.0004, FR_W + 0.002, -0.1500, -0.0980, 0.0198, 0.0210) for sx in (1, -1)])
    fr = H.bevel(fr, 0.0010 if hp else 0.0008, seg, angle=35)
    parts = [H.set_mat(fr, M["polymer"])]
    # controls (steel): slide stop (left), takedown lever (both sides), polymer magazine release (left)
    ss = H.prism("SlideStop", [(-0.0360, 0.0234), (-0.0205, 0.0234), (-0.0195, 0.0262), (-0.0230, 0.0272),
                               (-0.0360, 0.0272)], "X", 0.0110, 0.0127)
    parts.append(H.set_mat(H.bevel(ss, 0.0004, seg), M["steel"]))
    for sx in (1, -1):
        td = H.box("Takedown", min(sx * 0.0108, sx * 0.0122), max(sx * 0.0108, sx * 0.0122), -0.0725, -0.0645, 0.0200, 0.0255)
        parts.append(H.set_mat(H.bevel(td, 0.0003, seg), M["steel"]))
    mr = H.box("MagRelease", 0.0130, 0.0158, -0.0385, -0.0300, -0.0095, -0.0012)
    if hp:
        H.cut_batch(mr, [H.box("c_mrs", 0.0153, 0.02, y - 0.0003, y + 0.0003, -0.02, 0.01) for y in (-0.0365, -0.0350, -0.0335, -0.0320)])
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
    body = [(yb, GRIP_BOT), (yb + 0.0310, GRIP_BOT), (yb + 0.0310 - h * t, -0.0100), (yb - h * t, -0.0100)]
    b = H.prism("MagBody", body, "X", -0.0094, 0.0094)
    b = H.bevel(b, 0.0008, seg)
    plate = H.chaikin([(yb - 0.0040, GRIP_BOT + 0.0002), (0.0372, GRIP_BOT + 0.0002), (0.0382, GRIP_BOT - 0.0045),
                       (0.0362, GRIP_BOT - 0.0073), (yb - 0.0010, GRIP_BOT - 0.0073), (yb - 0.0048, GRIP_BOT - 0.0048)], 1)
    p = H.prism("MagPlate", plate, "X", -0.0128, 0.0128)
    p = H.bevel(p, 0.0014 if hp else 0.0012, seg + 1, angle=40)
    return {"Magazine": [H.set_mat(b, M["magsteel"]), H.set_mat(p, M["polymer_plain"])]}


def build(hp, M):
    out = {}
    for fn in (frame, slide, barrel, trigger, magazine):
        out.update(fn(hp, M))
    return out
