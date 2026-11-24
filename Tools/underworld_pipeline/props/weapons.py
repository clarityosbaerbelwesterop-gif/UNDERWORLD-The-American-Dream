"""Weapon grammar (P5, T-WPN-01): the 9 combat.json weapons as multi-part, rigged assets.

Contract = REQ-GP02-PISTOL (Docs/Handoffs/REQ_WPN_Pistol_01.md), the same one WPN_Pistol_01 meets:
  * origin at the grip (where the hand socket sits), barrel along Blender -Y = Godot +Z, up +Z
  * separate part objects with engine names: Frame, Slide (bolt/pump/charging handle), Magazine
    (box mag / revolver cylinder / tube), Barrel, Trigger, Hammer
  * empties SOCKET_Grip, SOCKET_Muzzle (+ SOCKET_Eject on firearms)
  * a small rigid rig (WpnRoot + SlideBone/MagBone/TrigBone[/HammerBone]) with actions
    A_<id>_Fire / A_<id>_Reload / A_<id>_Empty; the reload length comes from combat.json
    (`reload_time`), so animation and gameplay cannot drift apart
Original designs only (no real manufacturer's gun is reproduced).
"""
import json
import math
import os

import bpy
from mathutils import Matrix, Vector

AX_Y = (math.pi / 2, 0, 0)          # cylinder axis -> Y (barrels, tubes, scopes)
FPS = 30


# ------------------------------------------------------------------ helpers
def _ycyl(P, y0, y1, r, z, mat, x=0.0, segs=14, r2=None):
    P.cyl((x, (y0 + y1) / 2, z), r, abs(y1 - y0), mat, segs=segs, rot=AX_Y, radius2=r2)


def _prism_yz(P, outline, half_x, mat, bevel=0.0):
    """Flat part: polygon in the YZ plane (list of (y, z), CCW seen from +X) extruded +-half_x."""
    import bmesh as _bm
    area = sum(outline[i][0] * outline[(i + 1) % len(outline)][1] - outline[(i + 1) % len(outline)][0] * outline[i][1]
               for i in range(len(outline)))
    if area < 0:                       # make it CCW seen from +X so every face points outward
        outline = outline[::-1]
    before = set(P.bm.faces)
    L = [P.bm.verts.new((-half_x, y, z)) for (y, z) in outline]
    R = [P.bm.verts.new((half_x, y, z)) for (y, z) in outline]
    P.bm.faces.new(R)
    P.bm.faces.new(L[::-1])
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        P.bm.faces.new((L[i], L[j], R[j], R[i]))
    new = [f for f in P.bm.faces if f not in before]
    if bevel > 0:
        edges = list({e for f in new for e in f.edges})
        _bm.ops.bevel(P.bm, geom=edges, offset=bevel, segments=1, affect="EDGES", clamp_overlap=True)
        new = [f for f in P.bm.faces if f not in before]
    P._tag(new, mat)


def _trigger_guard(P, y_front, y_back, z_top, z_bot, mat):
    P.tube([(0, y_back, z_top), (0, y_back + 0.004, z_bot + 0.006), (0, (y_front + y_back) / 2, z_bot),
            (0, y_front, z_bot + 0.004), (0, y_front, z_top)], 0.003, mat, segs=6)


def _combat(repo_root, wid):
    try:
        with open(os.path.join(repo_root, "GodotProject", "Data", "Content", "combat.json"), encoding="utf-8") as f:
            return json.load(f)["weapons"].get(wid, {})
    except (OSError, KeyError, ValueError):
        return {}


def rig_and_sockets(P, objs, muzzle, eject=None, bones=None, actions=None):
    """Sockets + rigid rig. bones: {bone: (part, head, tail)}; actions: {suffix: (frames, {bone: [(f, delta)]})}."""
    sc = bpy.context.scene
    socks = [("SOCKET_Grip", (0, 0, 0)), ("SOCKET_Muzzle", muzzle)] + ([("SOCKET_Eject", eject)] if eject else [])
    for sname, loc in socks:
        s = bpy.data.objects.new(sname, None)
        s.empty_display_type, s.empty_display_size = "ARROWS", 0.03
        sc.collection.objects.link(s)
        s.parent, s.location = P.root, loc
    if not bones:
        return
    arm_d = bpy.data.armatures.new("WeaponRig")
    arm = bpy.data.objects.new("WeaponRig", arm_d)
    sc.collection.objects.link(arm)
    arm.parent = P.root
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    rb = arm_d.edit_bones.new("WpnRoot")
    rb.head, rb.tail = (0, 0, 0), (0, -0.05, 0)
    for b, (_part, head, tail) in bones.items():
        eb = arm_d.edit_bones.new(b)
        eb.head, eb.tail, eb.parent = head, tail, rb
    bpy.ops.object.mode_set(mode="OBJECT")
    for b, (part, _h, _t) in bones.items():
        ob = objs.get(part)
        if ob is None:
            continue
        ob.parent = arm
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.modifiers.new("Armature", "ARMATURE").object = arm
        ob.vertex_groups.new(name=b).add([v.index for v in ob.data.vertices], 1.0, "REPLACE")
    arm.animation_data_create()
    for suffix, (frame_end, keys) in (actions or {}).items():
        act = bpy.data.actions.new(f"A_{P.name}_{suffix}")
        act.use_fake_user = True
        arm.animation_data.action = act
        for b, kfs in keys.items():
            pb = arm.pose.bones[b]
            R3 = pb.bone.matrix_local.to_3x3()
            for fr, delta in kfs:
                pb.location = R3.inverted() @ Vector(delta)
                pb.keyframe_insert("location", frame=fr, group=b)
            pb.location = (0, 0, 0)
        act.use_frame_range = True
        act.frame_start, act.frame_end = 0, frame_end
        act["loop"] = False
    first = next(iter(actions)) if actions else None
    if first:
        arm.animation_data.action = bpy.data.actions[f"A_{P.name}_{first}"]
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)


def _std_actions(reload_s, slide_travel, mag_out, extra_fire=None, pump_after=False):
    rf = max(12, int(round(reload_s * FPS)))
    fire = {"SlideBone": [(0, (0, 0, 0)), (1, (0, slide_travel, 0)), (3, (0, 0, 0))],
            "TrigBone": [(0, (0, 0, 0)), (1, (0, 0.005, 0)), (3, (0, 0, 0))]}
    if pump_after:                                    # pump: shot, then rack back and forward
        fire = {"TrigBone": [(0, (0, 0, 0)), (1, (0, 0.005, 0)), (3, (0, 0, 0))],
                "SlideBone": [(0, (0, 0, 0)), (6, (0, 0, 0)), (11, (0, slide_travel, 0)), (16, (0, 0, 0))]}
    if extra_fire:
        fire.update(extra_fire)
    fire_end = max(k[-1][0] for k in fire.values())
    a, b = int(rf * 0.2), int(rf * 0.35)
    c, d = int(rf * 0.6), int(rf * 0.72)
    reload = {"MagBone": [(0, (0, 0, 0)), (a, (0, 0, 0)), (b, mag_out), (c, mag_out), (d, (0, 0, 0)), (rf, (0, 0, 0))],
              "SlideBone": [(0, (0, 0, 0)), (int(rf * 0.8), (0, 0, 0)), (int(rf * 0.86), (0, slide_travel, 0)),
                            (int(rf * 0.92), (0, 0, 0)), (rf, (0, 0, 0))]}
    empty = {"SlideBone": [(0, (0, slide_travel, 0)), (2, (0, slide_travel, 0))]}
    return {"Fire": (fire_end, fire), "Reload": (rf, reload), "Empty": (2, empty)}


# ------------------------------------------------------------------ firearms
def revolver(P, repo_root):
    """Double-action six-shot revolver, 6" barrel, wood grip (original design)."""
    P.part("Frame")
    _prism_yz(P, [(0.035, 0.025), (-0.055, 0.025), (-0.06, 0.07), (0.03, 0.075), (0.045, 0.06)], 0.011, "steel_bright", bevel=0.002)
    _prism_yz(P, [(0.045, 0.03), (0.012, 0.022), (0.02, -0.085), (0.052, -0.09), (0.062, -0.02)], 0.015, "wood_stock", bevel=0.004)
    P.box((0, -0.13, 0.071), (0.008, 0.15, 0.008), "steel_bright", bevel=0.001)                      # top rib
    P.box((0, -0.198, 0.078), (0.003, 0.008, 0.01), "steel_bright")                                  # front sight
    _trigger_guard(P, -0.03, 0.005, 0.024, -0.012, "steel_bright")
    P.part("Barrel")
    _ycyl(P, -0.06, -0.205, 0.0105, 0.058, "steel_bright", segs=16)
    _ycyl(P, -0.06, -0.15, 0.007, 0.036, "steel_bright", segs=10)                                    # ejector rod
    P.part("Magazine")                                                                               # cylinder
    _ycyl(P, -0.012, -0.056, 0.02, 0.047, "steel_bright", segs=12)
    for k in range(6):
        a = k * math.tau / 6
        _ycyl(P, -0.0115, -0.0125, 0.0045, 0.047 + 0.012 * math.sin(a), "gunmetal", x=0.012 * math.cos(a), segs=6)
    P.part("Hammer")
    _prism_yz(P, [(0.03, 0.06), (0.042, 0.06), (0.052, 0.085), (0.044, 0.088)], 0.004, "steel_bright")
    P.part("Trigger")
    _prism_yz(P, [(-0.006, 0.022), (-0.012, 0.0), (-0.004, -0.004), (0.0, 0.022)], 0.003, "steel_bright")
    P.col_box((0, -0.07, 0.0), (0.04, 0.28, 0.18))
    c = _combat(repo_root, P.name)
    acts = _std_actions(float(c.get("reload_time", 2.4)), 0.0, (-0.03, 0.0, 0.0))
    acts["Fire"][1]["HammerBone"] = [(0, (0, 0, 0)), (1, (0, 0.012, -0.006)), (3, (0, 0, 0))]
    acts["Fire"][1].pop("SlideBone")
    acts["Reload"][1].pop("SlideBone")
    acts["Empty"] = (2, {"HammerBone": [(0, (0, 0, 0)), (2, (0, 0, 0))]})
    return dict(muzzle=(0, -0.205, 0.058), eject=(0.02, -0.034, 0.047),
                bones={"MagBone": ("Magazine", (0, -0.034, 0.047), (0, -0.054, 0.047)),
                       "TrigBone": ("Trigger", (0, -0.006, 0.01), (0, -0.006, -0.01)),
                       "HammerBone": ("Hammer", (0, 0.04, 0.07), (0, 0.04, 0.09))}, actions=acts)


def smg(P, repo_root):
    """Compact 9 mm submachine gun: box receiver, shrouded barrel, mag well ahead of the grip, wire stock."""
    P.part("Frame")
    P.box((0, -0.03, 0.055), (0.042, 0.27, 0.06), "gunmetal", bevel=0.004)                          # receiver
    _prism_yz(P, [(0.025, 0.026), (-0.012, 0.026), (-0.004, -0.09), (0.03, -0.095), (0.04, 0.0)], 0.014, "polymer", bevel=0.003)
    P.box((0, -0.075, 0.012), (0.03, 0.05, 0.03), "gunmetal", bevel=0.003)                          # mag well
    _trigger_guard(P, -0.035, 0.005, 0.024, -0.016, "polymer")
    P.tube([(0.018, 0.10, 0.07), (0.018, 0.30, 0.07), (0.018, 0.31, 0.0), (-0.018, 0.31, 0.0), (-0.018, 0.30, 0.07), (-0.018, 0.10, 0.07)], 0.005, "gunmetal", segs=6)
    P.box((0, 0.312, 0.035), (0.05, 0.014, 0.085), "polymer", bevel=0.003)                           # butt plate
    P.box((0, 0.08, 0.092), (0.012, 0.012, 0.016), "gunmetal")                                        # rear sight
    P.box((0, -0.15, 0.092), (0.006, 0.01, 0.016), "gunmetal")                                        # front sight
    P.part("Barrel")
    _ycyl(P, -0.165, -0.245, 0.016, 0.058, "gunmetal", segs=14)
    _ycyl(P, -0.245, -0.275, 0.008, 0.058, "gunmetal", segs=10)
    P.part("Magazine")
    _prism_yz(P, [(-0.058, 0.0), (-0.092, 0.0), (-0.1, -0.16), (-0.066, -0.162)], 0.013, "gunmetal", bevel=0.002)
    P.part("Slide")                                                                                    # bolt handle
    P.cyl((-0.03, -0.06, 0.07), 0.006, 0.03, "polymer", segs=8, rot=(0, math.pi / 2, 0))
    P.part("Trigger")
    _prism_yz(P, [(-0.008, 0.024), (-0.014, 0.0), (-0.006, -0.004), (-0.002, 0.024)], 0.003, "gunmetal")
    P.col_box((0, 0.02, -0.02), (0.06, 0.6, 0.27))
    c = _combat(repo_root, P.name)
    return dict(muzzle=(0, -0.275, 0.058), eject=(0.022, -0.02, 0.06),
                bones={"SlideBone": ("Slide", (-0.03, -0.06, 0.07), (-0.03, -0.08, 0.07)),
                       "MagBone": ("Magazine", (0, -0.075, -0.02), (0, -0.075, -0.06)),
                       "TrigBone": ("Trigger", (0, -0.008, 0.01), (0, -0.008, -0.01))},
                actions=_std_actions(float(c.get("reload_time", 2.0)), 0.045, (0.0, -0.01, -0.16)))


def shotgun(P, repo_root):
    """12-gauge pump-action, wood furniture, bead sight."""
    P.part("Frame")
    P.box((0, -0.11, 0.06), (0.044, 0.19, 0.07), "gunmetal", bevel=0.004)                           # receiver
    _prism_yz(P, [(-0.015, 0.03), (0.04, 0.04), (0.12, 0.05), (0.37, 0.075), (0.37, -0.075), (0.30, -0.06),
                  (0.10, -0.03), (0.035, -0.06), (0.005, -0.055), (0.0, 0.0)], 0.02, "wood_stock", bevel=0.004)
    P.box((0, 0.372, 0.0), (0.045, 0.012, 0.15), "polymer", bevel=0.003)                             # recoil pad
    _trigger_guard(P, -0.04, 0.0, 0.026, -0.012, "gunmetal")
    P.sphere((0, -0.715, 0.086), 0.0035, "steel_bright", segs=8, rings=4)                            # bead
    P.part("Barrel")
    _ycyl(P, -0.2, -0.72, 0.0115, 0.074, "gunmetal", segs=16)
    P.part("Magazine")                                                                                 # tube mag
    _ycyl(P, -0.2, -0.64, 0.0115, 0.044, "gunmetal", segs=14)
    _ycyl(P, -0.64, -0.655, 0.013, 0.044, "steel_bright", segs=14)
    P.part("Slide")                                                                                    # pump
    P.lathe([(0.021, 0.0), (0.024, 0.01), (0.024, 0.17), (0.021, 0.18)], "wood_stock", segs=14, center=(0, 0, 0), cap_top=True, cap_bottom=True)
    import mathutils
    for v in P.bm.verts:                       # lathe axis Z -> along -Y under the barrel (a rotation)
        co = v.co.copy()
        v.co = mathutils.Vector((co.x, -0.33 - co.z, 0.047 + co.y))
    P.part("Trigger")
    _prism_yz(P, [(-0.008, 0.026), (-0.014, 0.0), (-0.006, -0.004), (-0.002, 0.026)], 0.003, "gunmetal")
    P.col_box((0, -0.17, 0.0), (0.06, 1.1, 0.16))
    c = _combat(repo_root, P.name)
    return dict(muzzle=(0, -0.72, 0.074), eject=(0.023, -0.1, 0.07),
                bones={"SlideBone": ("Slide", (0, -0.42, 0.047), (0, -0.44, 0.047)),
                       "MagBone": ("Magazine", (0, -0.6, 0.044), (0, -0.62, 0.044)),
                       "TrigBone": ("Trigger", (0, -0.008, 0.012), (0, -0.008, -0.008))},
                actions=_std_actions(float(c.get("reload_time", 3.0)), 0.085, (0.0, 0.0, 0.0), pump_after=True))


def rifle(P, repo_root):
    """5.56 carbine: flat-top upper with red-dot, railed handguard, curved magazine, collapsible stock."""
    P.part("Frame")
    P.box((0, -0.05, 0.025), (0.034, 0.21, 0.05), "gunmetal", bevel=0.003)                          # lower
    P.box((0, -0.06, 0.08), (0.036, 0.25, 0.06), "gunmetal", bevel=0.003)                           # upper
    P.box((0, -0.06, 0.113), (0.022, 0.25, 0.008), "gunmetal")                                        # top rail
    P.box((0, -0.30, 0.072), (0.05, 0.24, 0.06), "polymer", bevel=0.008)                             # handguard
    for zz in (0.104, 0.04):
        P.box((0, -0.30, zz), (0.02, 0.24, 0.006), "gunmetal")
    _prism_yz(P, [(0.02, 0.0), (-0.012, 0.0), (-0.002, -0.085), (0.03, -0.09), (0.04, -0.005)], 0.014, "polymer", bevel=0.003)
    _trigger_guard(P, -0.04, 0.0, 0.0, -0.022, "gunmetal")
    _ycyl(P, 0.065, 0.25, 0.015, 0.075, "gunmetal", segs=12)                                         # buffer tube
    _prism_yz(P, [(0.17, 0.10), (0.29, 0.11), (0.30, -0.04), (0.26, -0.03), (0.20, 0.04), (0.17, 0.055)], 0.02, "polymer", bevel=0.004)
    _ycyl(P, -0.02, -0.07, 0.016, 0.135, "gunmetal", segs=12)                                        # red-dot
    P.box((0, -0.045, 0.12), (0.02, 0.04, 0.012), "gunmetal")
    P.cyl((0, -0.071, 0.135), 0.013, 0.002, "lens", segs=12, rot=AX_Y)
    P.part("Barrel")
    _ycyl(P, -0.42, -0.52, 0.0095, 0.075, "gunmetal", segs=12)
    _ycyl(P, -0.52, -0.56, 0.013, 0.075, "gunmetal", segs=8)                                         # brake
    P.part("Magazine")
    for k in range(3):
        y0 = -0.065 - k * 0.012
        _prism_yz(P, [(y0, 0.0 - k * 0.06), (y0 - 0.034, 0.0 - k * 0.06), (y0 - 0.046, -0.062 - k * 0.06), (y0 - 0.012, -0.062 - k * 0.06)], 0.012, "gunmetal", bevel=0.0015)
    P.part("Slide")                                                                                    # charging handle
    P.box((0, 0.075, 0.103), (0.03, 0.016, 0.008), "gunmetal")
    P.part("Trigger")
    _prism_yz(P, [(-0.008, 0.004), (-0.014, -0.02), (-0.006, -0.024), (-0.002, 0.004)], 0.003, "gunmetal")
    P.col_box((0, -0.12, 0.0), (0.06, 0.9, 0.3))
    c = _combat(repo_root, P.name)
    return dict(muzzle=(0, -0.56, 0.075), eject=(0.02, -0.04, 0.08),
                bones={"SlideBone": ("Slide", (0, 0.075, 0.103), (0, 0.095, 0.103)),
                       "MagBone": ("Magazine", (0, -0.08, -0.03), (0, -0.09, -0.07)),
                       "TrigBone": ("Trigger", (0, -0.008, -0.004), (0, -0.008, -0.02))},
                actions=_std_actions(float(c.get("reload_time", 2.4)), 0.06, (0.0, 0.02, -0.18)))


def sniper(P, repo_root):
    """Bolt-action precision rifle: polymer stock with cheek riser, 4-14x scope, folded bipod."""
    P.part("Frame")
    _prism_yz(P, [(-0.50, 0.06), (-0.04, 0.06), (0.02, 0.03), (0.06, 0.06), (0.43, 0.09), (0.45, -0.07), (0.38, -0.07),
                  (0.12, -0.02), (0.04, -0.07), (0.005, -0.065), (-0.02, 0.0), (-0.50, 0.015)], 0.022, "polymer", bevel=0.005)
    P.box((0, 0.27, 0.088), (0.034, 0.16, 0.03), "polymer", bevel=0.006)                            # cheek riser
    _ycyl(P, 0.05, -0.16, 0.018, 0.075, "gunmetal", segs=14)                                         # action
    _ycyl(P, 0.07, -0.25, 0.017, 0.15, "gunmetal", segs=16)                                          # scope tube
    _ycyl(P, 0.07, 0.11, 0.022, 0.15, "gunmetal", segs=16)
    _ycyl(P, -0.25, -0.30, 0.026, 0.15, "gunmetal", segs=16, r2=0.02)
    P.cyl((0, -0.301, 0.15), 0.022, 0.002, "lens", segs=14, rot=AX_Y)
    P.cyl((0, 0.111, 0.15), 0.018, 0.002, "lens", segs=14, rot=AX_Y)
    for yy in (0.02, -0.12):
        P.box((0, yy, 0.11), (0.03, 0.02, 0.06), "gunmetal")                                         # rings
    P.cyl((0.0, -0.05, 0.17), 0.009, 0.02, "gunmetal", segs=10)                                      # turret
    for x in (-0.012, 0.012):
        P.tube([(x, -0.46, 0.02), (x, -0.30, 0.004)], 0.005, "gunmetal", segs=6)                    # bipod (folded)
    _trigger_guard(P, -0.04, 0.0, 0.02, -0.02, "gunmetal")
    P.part("Barrel")
    _ycyl(P, -0.16, -0.80, 0.012, 0.075, "gunmetal", segs=14, r2=0.009)
    _ycyl(P, -0.80, -0.85, 0.014, 0.075, "gunmetal", segs=8)
    P.part("Magazine")
    P.box((0, -0.065, 0.0), (0.03, 0.07, 0.05), "gunmetal", bevel=0.003)
    P.part("Slide")                                                                                    # bolt handle
    P.tube([(0.015, 0.035, 0.078), (0.045, 0.038, 0.06)], 0.004, "gunmetal", segs=6)
    P.sphere((0.05, 0.039, 0.057), 0.009, "polymer", segs=10, rings=6)
    P.part("Trigger")
    _prism_yz(P, [(-0.008, 0.02), (-0.014, -0.002), (-0.006, -0.006), (-0.002, 0.02)], 0.003, "gunmetal")
    P.col_box((0, -0.2, 0.04), (0.08, 1.3, 0.24))
    c = _combat(repo_root, P.name)
    return dict(muzzle=(0, -0.85, 0.075), eject=(0.02, -0.03, 0.085),
                bones={"SlideBone": ("Slide", (0.03, 0.036, 0.07), (0.03, 0.056, 0.07)),
                       "MagBone": ("Magazine", (0, -0.065, -0.01), (0, -0.065, -0.04)),
                       "TrigBone": ("Trigger", (0, -0.008, 0.008), (0, -0.008, -0.01))},
                actions=_std_actions(float(c.get("reload_time", 3.2)), 0.07, (0.0, 0.0, -0.09), pump_after=True))


# ------------------------------------------------------------------ melee + throwables
def knife(P, repo_root):
    """Fixed-blade combat knife, clip point, polymer handle with guard."""
    P.part("Frame")
    P.box((0, 0.0, 0.0), (0.024, 0.115, 0.03), "grip_tape", bevel=0.008)
    P.box((0, -0.062, 0.0), (0.03, 0.008, 0.05), "gunmetal", bevel=0.002)
    P.box((0, 0.06, 0.0), (0.026, 0.008, 0.032), "gunmetal", bevel=0.003)                          # pommel
    _prism_yz(P, [(-0.066, 0.014), (-0.066, -0.014), (-0.19, -0.012), (-0.235, 0.0), (-0.215, 0.006), (-0.17, 0.014)], 0.0022, "steel_bright")
    P.col_box((0, -0.08, 0.0), (0.04, 0.32, 0.06))
    return dict(muzzle=(0, -0.235, 0.0))


def bat(P, repo_root):
    """Ash baseball bat 0.84 m with taped handle; origin at the hands."""
    import mathutils
    P.part("Frame")
    mk = P.mark()
    P.lathe([(0.0, -0.1), (0.022, -0.098), (0.024, -0.09), (0.014, -0.082), (0.0125, 0.05), (0.016, 0.25),
             (0.031, 0.5), (0.033, 0.7), (0.03, 0.735), (0.0, 0.74)], "wood_stock", segs=16)
    P.transform_since(mk, lambda co: mathutils.Vector((co.x, -co.z, co.y)))
    mk = P.mark()
    P.lathe([(0.0136, -0.08), (0.0136, 0.1)], "grip_tape", segs=16, cap_top=False, cap_bottom=False)
    P.transform_since(mk, lambda co: mathutils.Vector((co.x, -co.z, co.y)))
    P.col_box((0, -0.32, 0.0), (0.07, 0.85, 0.07))
    return dict(muzzle=(0, -0.74, 0.0))


def grenade(P, repo_root):
    """Fragmentation grenade: olive body, fuze, spoon (Trigger part) and pin ring."""
    P.part("Frame")
    P.lathe([(0.0, -0.035), (0.022, -0.033), (0.031, -0.018), (0.032, 0.0), (0.029, 0.02), (0.018, 0.034), (0.0, 0.036)], "olive_paint", segs=18)
    P.cyl((0, 0, 0.045), 0.011, 0.022, "steel_bright", segs=10)                                     # fuze
    P.tube([(0.011, 0, 0.05), (0.022, 0.0, 0.05)], 0.0025, "steel_bright", segs=6)                   # pin
    P.tube([(0.022 + 0.008 * math.cos(a), 0.008 * math.sin(a), 0.05) for a in [k * math.tau / 10 for k in range(11)]], 0.0015, "steel_bright", segs=4)
    P.part("Trigger")                                                                                   # spoon
    P.tube([(0.0, 0.0, 0.058), (-0.012, 0.0, 0.058), (-0.03, 0.0, 0.035), (-0.036, 0.0, 0.0), (-0.032, 0.0, -0.025)], 0.004, "olive_paint", segs=6)
    P.col_box((0, 0, 0.005), (0.07, 0.07, 0.1))
    return dict(muzzle=(0, 0, 0.06))


def molotov(P, repo_root):
    """Glass bottle with fuel and a soaked rag fuse."""
    P.part("Frame")
    P.lathe([(0.0, -0.11), (0.036, -0.108), (0.038, -0.1), (0.038, 0.04), (0.03, 0.065), (0.013, 0.085), (0.013, 0.12),
             (0.015, 0.122), (0.015, 0.128), (0.0, 0.129)], "glass_bottle", segs=16)
    P.tube([(0.0, 0.0, 0.125), (0.004, -0.004, 0.15), (0.012, -0.01, 0.17), (0.02, -0.022, 0.16), (0.024, -0.03, 0.13)], 0.008, "rag", segs=7)
    P.label((0.0, -0.0385, -0.03), (0.05, 0.06), "label:BottleLabel:SUNDOWN|f4e6c0|6b2a12|128x160")
    P.col_box((0, 0, 0.01), (0.08, 0.08, 0.26))
    return dict(muzzle=(0.024, -0.03, 0.13))


WEAPONS = {
    "WPN_Revolver_01": revolver,
    "WPN_SMG_01": smg,
    "WPN_Shotgun_01": shotgun,
    "WPN_Rifle_01": rifle,
    "WPN_Sniper_01": sniper,
    "WPN_Knife_01": knife,
    "WPN_Bat_01": bat,
    "WPN_Grenade_01": grenade,
    "WPN_Molotov_01": molotov,
}


def build_weapons(repo_root, only=None, cache_dir=None):
    from . import kit
    cache_dir = cache_dir or os.environ.get("UWP_CACHE") or os.path.join(repo_root, ".cache", "uwp_sources")
    names = list(WEAPONS) if not only else [n.strip() for n in only.split(",")]
    bad = [n for n in names if n not in WEAPONS]
    if bad:
        raise SystemExit(f"[WEAPONS] unknown id(s): {bad}; known: {sorted(WEAPONS)}")
    out = []
    for n in names:
        P = kit.Prop(n, "Weapons", cache_dir)
        spec = WEAPONS[n](P, repo_root)
        out.append(P.finish(repo_root, ground=False,
                            before_save=lambda P_, objs, spec=spec: rig_and_sockets(P_, objs, **spec)))
    return out
