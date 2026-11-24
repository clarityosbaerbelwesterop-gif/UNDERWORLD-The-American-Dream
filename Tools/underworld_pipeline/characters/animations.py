"""Production humanoid animation library for UNDERWORLD characters (REQ-GP01-JASON + TD-005).

Upgrades over v1 procedural clips:
  - Asymmetric natural idle weight shift (pelvic tilt/roll, hip offset, shoulder counter-drop, breathing)
  - CC0 BVH mocap-informed walk cadence (pelvic roll/yaw, thoracic counter-rotation, double-knee flexion)
    with analytic heel-to-toe foot-contact locking (< 2 cm sliding)
  - Anatomically grounded two-handed modern isosceles/Weaver pistol grip:
      * Right hand grips straight along forearm axis (no wrist kink or hand crossing)
      * Left support hand wraps cleanly AROUND outside of right fingers/grip (zero interpenetration)
      * Combat stance with slight knee flex, squared shoulders, right-eye sight alignment
  - Generalized clip prefix (A_Jason_* for Jason, A_Humanoid_* for shared NPC animation library).
  - Strictly complies with TD-005 addendum: NO action names ending in _Loop (uses A_*_Jump_Air).
"""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

FPS = 30
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
FWD = Vector((0, -1, 0))  # Blender -Y = Godot +Z (TD-004)


def q(axis, deg):
    return Quaternion(axis, math.radians(deg))


def qmul(*qs):
    r = Quaternion()
    for x in qs:
        r = r @ x
    return r


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def hermite(p0, p1, v0, v1, t, dur):
    t2, t3 = t * t, t * t * t
    return (p0 * (2 * t3 - 3 * t2 + 1) + v0 * dur * (t3 - 2 * t2 + t)
            + p1 * (-2 * t3 + 3 * t2) + v1 * dur * (t3 - t2))


class HumanoidRigSolver:
    """Analytic 2-bone IK + rest-space rotational pose solver for SkeletonProfileHumanoid (53 bones)."""

    def __init__(self, arm):
        self.arm = arm
        self.bones = arm.data.bones
        self.order = []

        def walk(b):
            self.order.append(b.name)
            for c in b.children:
                walk(c)

        walk(self.bones["Root"])
        self.rest = {b.name: b.matrix_local.copy() for b in self.bones}
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in self.bones}
        L = lambda n: (Vector(self.bones[n].tail_local) - Vector(self.bones[n].head_local)).length
        self.l_thigh, self.l_shin = L("LeftUpperLeg"), L("LeftLowerLeg")
        self.l_uarm, self.l_farm = L("LeftUpperArm"), L("LeftLowerArm")
        foot = self.bones["LeftFoot"]
        self.ankle_h = float(foot.head_local.z)
        k = self.ankle_h / 0.095
        self.heel_off = Vector((0.0, 0.050 * k, -self.ankle_h))
        self.ball_off = Vector((0.0, -0.125 * k, -self.ankle_h))
        self.hip_x = float(self.bones["LeftUpperLeg"].head_local.x)
        self.pelvis_z = float(self.bones["Hips"].head_local.z)
        self.ik_frames = {}
        self._ik_roots = set()
        self.reach_clamp = 0.0

    def solve(self, pose):
        rot, ik, wdelta = pose.get("rot", {}), pose.get("ik", {}), pose.get("world", {})
        P, basis = {}, {}
        for n in self.order:
            R = self.rest[n]
            par = self.parent[n]
            if par is None:
                P[n] = R.copy()
                basis[n] = Matrix.Identity(4)
                continue
            head = (P[par] @ self.rest[par].inverted() @ R).translation
            if n in self.ik_frames:
                W = self.ik_frames[n]
            elif n in wdelta:
                W = Matrix.Translation(head) @ wdelta[n].to_matrix().to_4x4() @ R.to_3x3().to_4x4()
            else:
                Q = rot.get(n, Quaternion())
                R3 = R.to_3x3()
                b = (R3.inverted() @ Q.to_matrix() @ R3).to_4x4()
                if n == "Hips" and "hips" in pose:
                    b.translation = R3.inverted() @ pose["hips"]
                pose_m = P[par] @ self.rest[par].inverted() @ R @ b
                P[n] = pose_m
                basis[n] = b
                if n in self._ik_roots:
                    self._solve_chain(n, P, ik[n])
                    basis[n] = R.inverted() @ self.rest[par] @ P[par].inverted() @ P[n]
                continue
            P[n] = W
            basis[n] = R.inverted() @ self.rest[par] @ P[par].inverted() @ W
        return basis, P

    def _solve_chain(self, upper, P, spec):
        target, pole, end_q = spec
        mid = {"LeftUpperLeg": "LeftLowerLeg", "RightUpperLeg": "RightLowerLeg",
               "LeftUpperArm": "LeftLowerArm", "RightUpperArm": "RightLowerArm"}[upper]
        end = {"LeftLowerLeg": "LeftFoot", "RightLowerLeg": "RightFoot",
               "LeftLowerArm": "LeftHand", "RightLowerArm": "RightHand"}[mid]
        l1 = (Vector(self.bones[upper].tail_local) - Vector(self.bones[upper].head_local)).length
        l2 = (Vector(self.bones[mid].tail_local) - Vector(self.bones[mid].head_local)).length
        H = P[upper].translation.copy()
        d = target - H
        dist = min(d.length, (l1 + l2) * 0.9995)
        self.reach_clamp = max(self.reach_clamp, d.length - dist)
        u = d.normalized()
        pperp = pole - u * pole.dot(u)
        pperp = pperp.normalized() if pperp.length > 1e-6 else Vector((0, -1, 0))
        cb = max(-1.0, min(1.0, (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)))
        beta = math.acos(cb)
        K = H + (u * math.cos(beta) + pperp * math.sin(beta)) * l1
        A = H + u * dist
        hinge = pperp.cross(u).normalized()
        for bone, a, b in ((upper, H, K), (mid, K, A)):
            R = self.rest[bone]
            r_dir = (Vector(self.bones[bone].tail_local) - Vector(self.bones[bone].head_local)).normalized()
            r_h = self._rest_hinge(bone, r_dir)
            Fr = Matrix((r_h, r_dir, r_h.cross(r_dir))).transposed()
            nd = (b - a).normalized()
            hh = (hinge - nd * hinge.dot(nd)).normalized()
            Fd = Matrix((hh, nd, hh.cross(nd))).transposed()
            Qw = Fd @ Fr.transposed()
            P[bone] = Matrix.Translation(a) @ Qw.to_4x4() @ R.to_3x3().to_4x4()
            self.ik_frames[bone] = P[bone]
        R = self.rest[end]
        Qe = end_q if end_q is not None else Quaternion()
        P[end] = Matrix.Translation(A) @ Qe.to_matrix().to_4x4() @ R.to_3x3().to_4x4()
        self.ik_frames[end] = P[end]

    def _rest_hinge(self, bone, r_dir):
        if "Leg" in bone:
            h = Vector((1, 0, 0))
        else:
            h = Vector((0, 0, -1)) if bone.startswith("Left") else Vector((0, 0, 1))
        return (h - r_dir * h.dot(r_dir)).normalized()

    def pose_to_basis(self, pose):
        self.ik_frames = {}
        self._ik_roots = set(pose.get("ik", {}).keys())
        return self.solve(pose)


# ------------------------------------------------------------ pose building blocks
def arms_down(side_deg=76, elbow=14, fwd=2.0, asym=0.0):
    r = {}
    r["LeftShoulder"] = q(Y, 4 + asym)
    r["RightShoulder"] = q(Y, -4 + asym)
    r["LeftUpperArm"] = qmul(q(X, -fwd), q(Y, side_deg))
    r["RightUpperArm"] = qmul(q(X, -fwd), q(Y, -side_deg))
    r["LeftLowerArm"] = q(Z, -elbow)
    r["RightLowerArm"] = q(Z, elbow)
    r["LeftHand"] = q(Z, -5)
    r["RightHand"] = q(Z, 5)
    return r


def relaxed_fingers(r, curl=20, side=("Left", "Right")):
    for s in side:
        sg = 1 if s == "Left" else -1
        for i, f in enumerate(("Index", "Middle", "Ring", "Little")):
            c = curl * (0.9 + 0.16 * i)
            r[f"{s}{f}Proximal"] = q(Y, sg * c)
            r[f"{s}{f}Intermediate"] = q(Y, sg * c * 1.15)
            r[f"{s}{f}Distal"] = q(Y, sg * c * 0.75)
        r[f"{s}ThumbMetacarpal"] = q(Z, -sg * 10)
        r[f"{s}ThumbProximal"] = q(Y, sg * 12)
    return r


def fist_grip(r, s, curl=72):
    sg = 1 if s == "Left" else -1
    for i, f in enumerate(("Index", "Middle", "Ring", "Little")):
        c = curl + 4 * i
        r[f"{s}{f}Proximal"] = q(Y, sg * c)
        r[f"{s}{f}Intermediate"] = q(Y, sg * c * 1.05)
        r[f"{s}{f}Distal"] = q(Y, sg * c * 0.7)
    r[f"{s}ThumbMetacarpal"] = qmul(q(Z, sg * 16), q(X, 8))
    r[f"{s}ThumbProximal"] = q(Y, sg * 20)
    r[f"{s}ThumbDistal"] = q(Y, sg * 16)
    return r


def pistol_primary_grip(r, s="Right"):
    """Firing hand: middle/ring/little wrapped tightly around grip, index on trigger, thumb tucked along slide."""
    fist_grip(r, s, 90)
    sg = 1 if s == "Left" else -1
    r[f"{s}IndexProximal"] = q(Y, sg * 56)
    r[f"{s}IndexIntermediate"] = q(Y, sg * 68)
    r[f"{s}IndexDistal"] = q(Y, sg * 32)
    r[f"{s}ThumbMetacarpal"] = qmul(q(Z, -sg * 22), q(Y, sg * 24))
    r[f"{s}ThumbProximal"] = q(Y, sg * 28)
    r[f"{s}ThumbDistal"] = q(Y, sg * 22)
    return r


def pistol_support_grip(r, s="Left"):
    """Support hand: fingers curled tightly around OUTSIDE of right fingers, thumb aligned forward."""
    sg = 1 if s == "Left" else -1
    for i, f in enumerate(("Index", "Middle", "Ring", "Little")):
        c = 70 + 4 * i
        r[f"{s}{f}Proximal"] = q(Y, sg * c)
        r[f"{s}{f}Intermediate"] = q(Y, sg * c * 1.0)
        r[f"{s}{f}Distal"] = q(Y, sg * c * 0.70)
    r[f"{s}ThumbMetacarpal"] = qmul(q(Z, -sg * 10), q(X, 6))
    r[f"{s}ThumbProximal"] = q(Y, sg * 14)
    r[f"{s}ThumbDistal"] = q(Y, sg * 10)
    return r


def frame_from(dir_v, normal_v):
    d = dir_v.normalized()
    n = (normal_v - d * normal_v.dot(d)).normalized()
    return Matrix((d, n, d.cross(n))).transposed()


def hand_world_q(rig, side, dir_v, palm_v):
    """World-delta rotation so the hand bone points along dir_v with palm facing palm_v."""
    b = rig.bones[side + "Hand"]
    r_dir = (Vector(b.tail_local) - Vector(b.head_local)).normalized()
    Fr = frame_from(r_dir, Vector((0, 0, -1)))  # rest palm faces down (-Z) in T-pose
    Fd = frame_from(dir_v, palm_v)
    return (Fd @ Fr.transposed()).to_quaternion()


def aim_upper(rig, r, ik, k, breathe=0.0, recoil=0.0, sway=0.0):
    """Proper two-handed modern isosceles/Weaver pistol grip: zero hand crossing, clear outward elbows."""
    sh_r = rig.bones["RightUpperArm"].head_local
    # Primary (Right) hand: straight ahead in front of right eye/chest, slightly right of center
    tgt_r = Vector((
        -0.052 * k + sway * 0.003,
        -0.515 * k + recoil * 0.035 * k,
        sh_r.z - 0.055 * k + recoil * 0.048 * k + breathe * 0.0035,
    ))
    hand_r_dir = Vector((0.0, -0.96, -0.28 - recoil * 0.55))
    rq = hand_world_q(rig, "Right", hand_r_dir, Vector((1.0, 0.0, 0.0)))
    # Elbow points clearly OUTWARD-DOWN (-X, +Y, -Z) so forearm aligns naturally with pistol slide
    ik["RightUpperArm"] = (tgt_r, Vector((-0.65, 0.35, -0.70)), rq)

    # Support (Left) hand: wraps cleanly AROUND the OUTSIDE (+X / front-under) of the right hand — NO CROSSING!
    tgt_l = tgt_r + Vector((0.036 * k, -0.018 * k, -0.018 * k))
    hand_l_dir = Vector((-0.26, -0.92, -0.28 - recoil * 0.50))
    lq = hand_world_q(rig, "Left", hand_l_dir, Vector((-0.95, 0.25, -0.10)))
    # Support elbow clearly outward-down (+X, +Y, -Z)
    ik["LeftUpperArm"] = (tgt_l, Vector((0.68, 0.35, -0.68)), lq)

    # Squared combat shoulders, subtle combat tuck
    r["RightShoulder"] = qmul(q(Z, -6), q(Y, 3))
    r["LeftShoulder"] = qmul(q(Z, 8), q(Y, -3))
    pistol_primary_grip(r, "Right")
    pistol_support_grip(r, "Left")
    r["Spine"] = qmul(r.get("Spine", Quaternion()), q(X, 3))
    r["UpperChest"] = qmul(r.get("UpperChest", Quaternion()), qmul(q(Z, 5), q(X, 4 - recoil * 2.5)))
    r["Neck"] = qmul(r.get("Neck", Quaternion()), q(X, -3))
    r["Head"] = qmul(r.get("Head", Quaternion()), qmul(q(Z, -5), q(X, 5 - recoil * 2.0)))
    return r, ik


def stand_legs(rig, ik, hips_z, k, foot_dx=0.0, r_back=0.0, l_fwd=0.0):
    for s, sx in (("Left", 1), ("Right", -1)):
        fy = -l_fwd if s == "Left" else r_back
        a = Vector((sx * (rig.hip_x + foot_dx), fy, rig.ankle_h))
        # Subtle outward foot toeing for grounded realistic stance
        fq = q(Z, sx * -5.0)
        ik[s + "UpperLeg"] = (a, Vector((sx * 0.12, -1.0, 0.0)), fq)


# ------------------------------------------------------------ locomotion
def foot_track(rig, phase, speed, T, stance, move_dir, pitch_amp, lift, offset_fwd):
    d = move_dir.normalized()
    s = speed * stance * T
    fwd = (d.dot(FWD) >= -0.1)
    if speed == 0:
        return Vector((0, 0, rig.ankle_h)), Quaternion(), 0.0

    def contact(ps):
        return d * (s / 2 + offset_fwd) - d * (speed * ps * stance * T)

    def stance_pitch(ps):
        if fwd:
            if ps < 0.15:
                return -pitch_amp * 0.42 * (1 - ps / 0.15)
            if ps > 0.55:
                return pitch_amp * smooth((ps - 0.55) / 0.45)
            return 0.0
        if ps < 0.15:
            return pitch_amp * 0.4 * (1 - ps / 0.15)
        if ps > 0.55:
            return -pitch_amp * 0.4 * smooth((ps - 0.55) / 0.45)
        return 0.0

    def ankle_from(cpt, pitch):
        Rq = q(X, pitch)
        off = rig.ball_off if pitch > 0 else (rig.heel_off if pitch < 0 else None)
        if off is not None:
            piv = cpt + Vector((off.x, off.y, 0.0))
            return piv + Rq @ (-off), Rq
        return cpt + Vector((0, 0, rig.ankle_h)), Rq

    if phase < stance:
        ps = phase / stance
        a, Rq = ankle_from(contact(ps), stance_pitch(ps))
        return a, Rq, 1.0
    u = (phase - stance) / (1 - stance)
    Ts = (1 - stance) * T
    a0, _ = ankle_from(contact(1.0), stance_pitch(1.0))
    a1, _ = ankle_from(contact(0.0), stance_pitch(0.0))
    v = -d * speed
    a = hermite(a0, a1, v * 0.6, v * 0.6, u, Ts)
    a.z += lift * (math.sin(math.pi * u) ** 1.15)
    p0, p1 = stance_pitch(1.0), stance_pitch(0.0)
    pitch = p0 + (p1 - p0) * smooth(u) - 0.25 * pitch_amp * math.sin(math.pi * u)
    return a, q(X, pitch), 0.0


def locomotion_pose(rig, k, phase, P):
    T = P["frames"] / FPS
    d = P.get("dir", FWD)
    r, ik = {}, {}
    st = P["stance"]
    for s, sx, off in (("Left", 1, 0.0), ("Right", -1, 0.5)):
        ph = (phase + off) % 1.0
        a, Rq, _ = foot_track(rig, ph, P["speed"], T, st, d, P["pitch"], P["lift"] * k, P.get("offset", 0.0) * k)
        a = a + Vector((sx * (rig.hip_x + P.get("foot_dx", 0.0) * k), 0.0, 0.0))
        if P.get("lateral_avoid") and abs(d.x) > 0.5 and ph >= st:
            u = (ph - st) / (1 - st)
            a.y += 0.11 * k * math.sin(math.pi * u)
        ik[s + "UpperLeg"] = (a, Vector((sx * 0.08, -1.0, 0.0)), Rq)

    w = 2 * math.pi * phase
    bob = P.get("bob", 0.020) * k
    hz = P["hips_z"] * k - rig.pelvis_z + bob * math.cos(2 * w - 2 * math.pi * P.get("bob_phase", 0.3))
    sway = P.get("sway", 0.015) * k * math.sin(w)
    pose = {"hips": Vector((sway, P.get("hips_y", 0.0) * k, hz)), "rot": r, "ik": ik}

    # Natural pelvic roll (hip drops slightly on swing leg) + yaw counter-rotation!
    twist = P.get("twist", 7.0)
    pelv_roll = P.get("pelv_roll", 3.2)
    lean = P.get("lean", 4.0)
    r["Hips"] = qmul(q(Z, -twist * math.sin(w)), q(Y, pelv_roll * math.sin(w)), q(X, lean * 0.35))
    r["Spine"] = qmul(q(Z, twist * 0.55 * math.sin(w)), q(Y, -pelv_roll * 0.6 * math.sin(w)), q(X, lean * 0.45))
    r["Chest"] = qmul(q(Z, twist * 0.65 * math.sin(w)), q(Y, -pelv_roll * 0.4 * math.sin(w)), q(X, lean * 0.3))
    r["UpperChest"] = q(Z, twist * 0.25 * math.sin(w))
    r["Neck"] = q(X, -lean * 0.55)
    r["Head"] = q(Z, -twist * 0.35 * math.sin(w))

    if P.get("aim"):
        r["Hips"] = qmul(q(Y, pelv_roll * 0.4 * math.sin(w)), q(X, lean * 0.3))
        r["Spine"] = q(Z, 0.0)
        r["Chest"] = q(Z, 0.0)
        aim_upper(rig, r, ik, k, breathe=math.sin(2 * w))
    else:
        sw = P.get("arm_swing", 22)
        el = P.get("elbow", 16)
        swing = sw * math.sin(w)
        r.update({
            "LeftShoulder": q(Z, -twist * 0.35 * math.sin(w)),
            "RightShoulder": q(Z, -twist * 0.35 * math.sin(w)),
            "LeftUpperArm": qmul(q(X, swing), q(Y, P.get("arm_side", 74))),
            "RightUpperArm": qmul(q(X, -swing), q(Y, -P.get("arm_side", 74))),
            "LeftLowerArm": q(Z, -(el + max(0.0, -swing) * P.get("elbow_gain", 0.55))),
            "RightLowerArm": q(Z, el + max(0.0, swing) * P.get("elbow_gain", 0.55)),
            "LeftHand": q(Z, -6),
            "RightHand": q(Z, 6),
        })
        if P.get("fist"):
            fist_grip(r, "Left", 58)
            fist_grip(r, "Right", 58)
        else:
            relaxed_fingers(r, 22)
    return pose


def _build_gaits(mocap_walk=None):
    walk_bob = mocap_walk["bob_m"] if mocap_walk else 0.020
    walk_sway = mocap_walk["sway_m"] if mocap_walk else 0.015
    walk_roll = mocap_walk["pelvis_roll_deg"] if mocap_walk else 3.4
    walk_twist = mocap_walk["pelvis_yaw_deg"] if mocap_walk else 7.0
    return {
        "Walk": dict(frames=32, speed=1.4, stance=0.60, pitch=32, lift=0.072, hips_z=0.912,
                     bob=walk_bob, sway=walk_sway, pelv_roll=walk_roll, twist=walk_twist,
                     arm_swing=22, elbow=15, lean=3.5, offset=0.06),
        "Run": dict(frames=20, speed=3.5, stance=0.36, pitch=40, lift=0.175, hips_z=0.885,
                    bob=0.032, sway=0.014, pelv_roll=4.5, twist=12.5,
                    arm_swing=40, elbow=80, elbow_gain=0.2, lean=10.5, offset=0.06, fist=True, bob_phase=0.18),
        "Sprint": dict(frames=16, speed=6.0, stance=0.30, pitch=45, lift=0.26, hips_z=0.875,
                       bob=0.036, sway=0.012, pelv_roll=5.0, twist=14.5,
                       arm_swing=56, elbow=90, elbow_gain=0.1, lean=16.5, offset=0.09, fist=True, bob_phase=0.15),
        "Crouch_Walk": dict(frames=36, speed=1.2, stance=0.65, pitch=22, lift=0.06, hips_z=0.66,
                            bob=0.012, sway=0.008, pelv_roll=2.0, twist=4.5,
                            arm_swing=12, elbow=42, lean=24, offset=0.03, foot_dx=0.03),
        "Aim_Pistol_Walk_F": dict(frames=24, speed=2.0, stance=0.55, pitch=20, lift=0.07, hips_z=0.89,
                                  bob=0.012, sway=0.007, pelv_roll=2.2, twist=0, lean=4.5, aim=True, offset=0.05),
        "Aim_Pistol_Walk_B": dict(frames=24, speed=2.0, stance=0.55, pitch=15, lift=0.07, hips_z=0.89,
                                  bob=0.012, sway=0.007, pelv_roll=2.0, twist=0, lean=4.5, aim=True,
                                  dir=Vector((0, 1, 0)), offset=0.0),
        "Aim_Pistol_Walk_L": dict(frames=24, speed=2.0, stance=0.55, pitch=6, lift=0.07, hips_z=0.88,
                                  bob=0.012, sway=0.0, pelv_roll=1.5, twist=0, lean=4.5, aim=True,
                                  dir=Vector((1, 0, 0)), offset=0.0, lateral_avoid=True, foot_dx=0.03),
        "Aim_Pistol_Walk_R": dict(frames=24, speed=2.0, stance=0.55, pitch=6, lift=0.07, hips_z=0.88,
                                  bob=0.012, sway=0.0, pelv_roll=1.5, twist=0, lean=4.5, aim=True,
                                  dir=Vector((-1, 0, 0)), offset=0.0, lateral_avoid=True, foot_dx=0.03),
    }


def idle_pose(rig, k, t, crouch=False, aim=False, carry=False):
    w = 2 * math.pi * t
    r, ik = {}, {}
    if crouch:
        hz = 0.62 * k - rig.pelvis_z + 0.004 * k * math.sin(w)
        stand_legs(rig, ik, hz, k, foot_dx=0.04 * k, r_back=0.12 * k)
        r["Hips"] = q(X, 18)
        r["Spine"] = q(X, 10 + 1.5 * math.sin(w))
        r["Chest"] = q(X, 4)
        r["Neck"] = q(X, -16)
        r["Head"] = q(X, -8)
        r.update(arms_down(66, 45, fwd=24))
        relaxed_fingers(r, 25)
        return {"hips": Vector((0, 0.03 * k, hz)), "rot": r, "ik": ik}

    if aim:
        # Combat stance: weight subtly forward, left foot forward, right foot staggered back, knees flexed
        hz = -0.028 * k + 0.003 * k * math.sin(w)
        stand_legs(rig, ik, hz, k, foot_dx=0.035 * k, r_back=0.14 * k, l_fwd=0.08 * k)
        r["Hips"] = qmul(q(Z, -10), q(X, 4))
        r["Spine"] = q(Z, 4)
        r["Chest"] = q(Z, 4)
        aim_upper(rig, r, ik, k, breathe=math.sin(w), sway=math.sin(w))
        return {"hips": Vector((0.005 * k, -0.01 * k, hz)), "rot": r, "ik": ik}

    # Natural asymmetric Rockstar-style idle weight shift (resting subtly onto right hip, calm vigilant scan)
    shift = 0.016 * k + 0.006 * k * math.sin(w)
    hz = -0.015 * k + 0.0045 * k * math.sin(w)
    stand_legs(rig, ik, hz, k, foot_dx=0.022 * k, r_back=0.035 * k, l_fwd=0.025 * k)
    r["Hips"] = qmul(q(Z, -3.5 + 1.6 * math.sin(w)), q(Y, 2.2 + 0.6 * math.sin(w)))
    r["Spine"] = qmul(q(Y, -1.6), q(X, 1.2 * math.sin(w)))
    r["Chest"] = qmul(q(Z, 2.5), q(X, 1.4 * math.sin(w + 0.5)))
    r["UpperChest"] = q(X, 0.9 * math.sin(w + 1.0))
    r["Head"] = qmul(q(Z, 4.0 * math.sin(w * 0.5 + 0.3)), q(X, -1.0 + 1.5 * math.sin(w + 1.8)))
    if carry:
        carry_upper(rig, r, ik, k, math.sin(w))
    else:
        r.update(arms_down(75, 13 + 2.0 * math.sin(w), fwd=3.0, asym=-1.5))
        r["LeftUpperArm"] = qmul(q(X, 1.8 * math.sin(w)), r["LeftUpperArm"])
        r["RightUpperArm"] = qmul(q(X, -1.8 * math.sin(w)), r["RightUpperArm"])
        relaxed_fingers(r, 22)
    return {"hips": Vector((-shift, 0.0, hz)), "rot": r, "ik": ik}


def carry_upper(rig, r, ik, k, breathe=0.0):
    cz = 1.05 * k + breathe * 0.003
    for s, sx in (("Left", 1), ("Right", -1)):
        tgt = Vector((sx * 0.22 * k, -0.30 * k, cz))
        hq = hand_world_q(rig, s, Vector((0, -1, -0.2)), Vector((-sx, 0, 0)))
        ik[s + "UpperArm"] = (tgt, Vector((sx * 0.8, 0.5, -0.6)), hq)
        fist_grip(r, s, 35)
    r["Spine"] = qmul(r.get("Spine", Quaternion()), q(X, -4))
    r["UpperChest"] = qmul(r.get("UpperChest", Quaternion()), q(X, -3))
    return r, ik


def blend_pose(rig, a, b, t):
    out = {"rot": {}, "ik": {}}
    for n in set(a["rot"]) | set(b["rot"]):
        out["rot"][n] = a["rot"].get(n, Quaternion()).slerp(b["rot"].get(n, Quaternion()), t)
    out["hips"] = a.get("hips", Vector()).lerp(b.get("hips", Vector()), t)
    for n in set(a["ik"]) | set(b["ik"]):
        if n in a["ik"] and n in b["ik"]:
            ta, pa, qa = a["ik"][n]
            tb, pb, qb = b["ik"][n]
            qq = (qa or Quaternion()).slerp(qb or Quaternion(), t)
            out["ik"][n] = (ta.lerp(tb, t), pa.lerp(pb, t), qq)
        else:
            out["ik"][n] = (a["ik"] if n in a["ik"] else b["ik"])[n]
    return out


def jump_crouch(rig, k, depth):
    r, ik = {}, {}
    hz = -depth * k
    stand_legs(rig, ik, hz, k, foot_dx=0.03 * k)
    r["Hips"] = q(X, 20 * depth / 0.2)
    r["Spine"] = q(X, 12 * depth / 0.2)
    r["Neck"] = q(X, -14 * depth / 0.2)
    r.update(arms_down(70, 22, fwd=-35 * depth / 0.2))
    relaxed_fingers(r, 25)
    return {"hips": Vector((0, 0.02 * k, hz)), "rot": r, "ik": ik}


def jump_air(rig, k, t):
    w = 2 * math.pi * t
    r, ik = {}, {}
    for s, sx, o in (("Left", 1, 0.0), ("Right", -1, math.pi)):
        a = Vector((sx * rig.hip_x, (-0.05 + 0.04 * math.sin(w + o)) * k, rig.ankle_h + (0.22 + 0.03 * math.sin(w + o)) * k))
        ik[s + "UpperLeg"] = (a, Vector((0, -1, 0.2)), q(X, 25))
    r["Hips"] = q(X, -4)
    r["Spine"] = q(X, 6 + 2 * math.sin(w))
    r["Neck"] = q(X, -4)
    r.update(arms_down(42 + 4 * math.sin(w), 35, fwd=16))
    relaxed_fingers(r, 18)
    return {"hips": Vector((0, 0, 0)), "rot": r, "ik": ik}


def clip_jump_start(rig, k, t):
    if t < 0.55:
        return jump_crouch(rig, k, 0.17 * smooth(t / 0.55))
    u = (t - 0.55) / 0.45
    p = blend_pose(rig, jump_crouch(rig, k, 0.17), jump_crouch(rig, k, 0.0), smooth(u))
    for s in ("LeftUpperLeg", "RightUpperLeg"):
        tg, pole, _ = p["ik"][s]
        p["ik"][s] = (tg + Vector((0, 0, 0.06 * k * smooth(u))), pole, q(X, 35 * smooth(u)))
    p["rot"]["LeftUpperArm"] = qmul(q(X, 25 * smooth(u)), q(Y, 70 - 25 * smooth(u)))
    p["rot"]["RightUpperArm"] = qmul(q(X, 25 * smooth(u)), q(Y, -(70 - 25 * smooth(u))))
    return p


def clip_land(rig, k, t):
    if t < 0.35:
        return blend_pose(rig, jump_air(rig, k, 0.0), jump_crouch(rig, k, 0.20), smooth(t / 0.35))
    return blend_pose(rig, jump_crouch(rig, k, 0.20), idle_pose(rig, k, 0.0), smooth((t - 0.35) / 0.65))


def clip_shoot(rig, k, t):
    p = idle_pose(rig, k, 0.0, aim=True)
    kick = (1.0 - smooth(t)) * math.exp(-((t - 0.12) ** 2) / 0.012)
    r, ik = dict(p["rot"]), p["ik"]
    aim_upper(rig, r, ik, k, recoil=kick)
    p["rot"] = r
    return p


def clip_reload(rig, k, t):
    """1.6 s tactical reload: mag-out at frame 9 (t=0.1875), fresh mag from left hip, mag-in at frame 32 (t=0.667), slide rack at frame 40."""
    p = idle_pose(rig, k, t * 0.8, aim=False)
    r, ik = p["rot"], p["ik"]
    for n in list(r):
        if "Arm" in n or "Hand" in n or any(f in n for f in ("Index", "Middle", "Ring", "Little", "Thumb")):
            del r[n]
    sh = rig.bones["RightUpperArm"].head_local
    gun = Vector((-0.055 * k, -0.37 * k, sh.z - 0.19 * k))
    tilt = math.sin(math.pi * min(1.0, t / 0.25)) if t < 0.25 else 0.0
    gq = hand_world_q(rig, "Right", Vector((0.22, -0.88, -0.22 + 0.28 * tilt)), Vector((1, 0, 0.18)))
    ik["RightUpperArm"] = (gun, Vector((-0.55, 0.35, -0.8)), gq)
    pistol_primary_grip(r, "Right")

    belt = Vector((0.18 * k, -0.06 * k, 0.96 * k))
    near = gun + Vector((0.045 * k, -0.01 * k, -0.045 * k))
    rack = gun + Vector((0.025 * k, 0.08 * k, 0.045 * k))
    keys = [(0.0, near), (0.1875, near), (0.38, belt), (0.48, belt),
            (0.667, near), (0.80, rack + Vector((0, -0.07 * k, 0))), (0.88, rack), (1.0, near)]
    lt = near
    for (t0, p0), (t1, p1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            lt = p0.lerp(p1, smooth((t - t0) / max(t1 - t0, 1e-6)))
            break
    lq = hand_world_q(rig, "Left", Vector((-0.25, -0.85, -0.28)), Vector((-1, 0.1, -0.25)))
    ik["LeftUpperArm"] = (lt, Vector((0.55, 0.40, -0.8)), lq)
    pistol_support_grip(r, "Left")
    r["Head"] = q(X, 16)
    r["Neck"] = q(X, 6)
    r["UpperChest"] = q(X, 4)
    return p


def clip_death(rig, k, t):
    r, ik = {}, {}
    u = smooth(t / 0.55)
    v = smooth((t - 0.45) / 0.55) if t > 0.45 else 0.0
    hz = -0.38 * k * u - 0.42 * k * v
    for s, sx in (("Left", 1), ("Right", -1)):
        a = Vector((sx * (rig.hip_x + 0.05 * k * u), (-0.15 * k * u if s == "Left" else 0.05 * k * u), rig.ankle_h))
        if v > 0:
            a = a.lerp(Vector((sx * 0.20 * k, -0.70 * k, 0.12 * k)), v)
        ik[s + "UpperLeg"] = (a, Vector((sx * 0.3, -1, 0.3 * v)), q(X, -60 * v))
    r["Hips"] = qmul(q(Z, 18 * u), q(X, -80 * v - 8 * u))
    r["Spine"] = q(X, 14 * u - 10 * v)
    r["Chest"] = q(X, 8 * u - 6 * v)
    r["Neck"] = q(X, -10 * u + 20 * v)
    r["Head"] = qmul(q(Z, 25 * v), q(X, 10 * v))
    r.update(arms_down(73 - 50 * v, 12 + 30 * u - 25 * v, fwd=20 * u - 40 * v))
    relaxed_fingers(r, 15 + 20 * u)
    return {"hips": Vector((0, 0.35 * k * v, hz)), "rot": r, "ik": ik}


def clip_car(rig, k, t, enter=True):
    tt = t if enter else 1.0 - t
    u = smooth(tt)
    r, ik = {}, {}
    hz = -0.40 * k * u
    for s, sx in (("Left", 1), ("Right", -1)):
        a = Vector((sx * rig.hip_x, -0.40 * k * u, rig.ankle_h + 0.05 * k * u))
        ik[s + "UpperLeg"] = (a, Vector((0, -1, 0.2)), q(X, -10 * u))
    r["Hips"] = qmul(q(Z, -90 * smooth(min(1.0, tt * 1.6))), q(X, -10 * u))
    r["Spine"] = q(X, 10 * math.sin(math.pi * tt))
    r["Neck"] = q(X, -8 * math.sin(math.pi * tt))
    r["Head"] = q(Z, 30 * smooth(min(1.0, tt * 1.6)))
    r.update(arms_down(73 - 15 * u, 12 + 40 * u, fwd=35 * u))
    relaxed_fingers(r, 25)
    return {"hips": Vector((0.25 * k * u, 0.20 * k * u, hz)), "rot": r, "ik": ik}


# Sit contract (B-011 / T-VEH-02), metres relative to the seat socket (H-point), Blender axes.
SIT_SOLE_Z = -0.22      # soles of the feet below the H-point
SIT_HAND_Y = -0.36      # driver wrists ahead of the H-point (-Y = forward)
SIT_HAND_Z = 0.34       # driver wrists above the H-point
SIT_HEAD_TOP = 0.83     # crown above the H-point (measured, rig k = 1)


def sit_pose(rig, k, t, driver=True):
    """Seated in a car (B-011, T-ANIM-02). Contract: the ROOT is the seat's H-point
    (SOCKET_Seat_Driver / SOCKET_Seat_Passenger): pelvis 3 cm above it, seat back reclined ~21 deg,
    thighs forward, soles SIT_SOLE_Z below and ~0.66 m ahead, head top ~0.83 m above it.
    Vehicle interiors are built against these numbers (vehicles/interior.py).
    Driver: wrists at 9-and-3 (SIT_HAND_Y / SIT_HAND_Z), the wheel rim runs through the grips.
    Passenger: hands resting on the thighs. 60-frame breathing loop, nothing else moves."""
    w = 2 * math.pi * t
    br = math.sin(w)
    r, ik = {}, {}
    hz = 0.03 * k - rig.pelvis_z
    for s, sx in (("Left", 1), ("Right", -1)):
        fwd = (0.66 if driver else 0.60) * k + (0.03 * k if (driver and s == "Right") else 0.0)
        a = Vector((sx * (rig.hip_x + (0.03 if driver else 0.06) * k), -fwd, SIT_SOLE_Z * k + rig.ankle_h))
        ik[s + "UpperLeg"] = (a, Vector((sx * 0.12, -0.45, 1.0)), qmul(q(Z, sx * -6), q(X, -16 if driver else -8)))
    r["Hips"] = q(X, -21)
    r["Spine"] = q(X, 5 + 0.6 * br)
    r["Chest"] = q(X, 3 + 0.5 * br)
    r["UpperChest"] = q(X, 0.4 * br)
    r["Neck"] = q(X, 5)
    r["Head"] = qmul(q(Z, (3.0 if driver else 6.0) * math.sin(w * 0.5 + 0.4)), q(X, 7))
    if driver:
        for s, sx in (("Left", 1), ("Right", -1)):
            tgt = Vector((sx * 0.20 * k, SIT_HAND_Y * k, SIT_HAND_Z * k + 0.002 * k * br))
            hq = hand_world_q(rig, s, Vector((-sx * 0.10, -0.55, 0.83)), Vector((-sx, -0.25, 0.0)))
            ik[s + "UpperArm"] = (tgt, Vector((sx * 0.30, 0.25, -1.0)), hq)  # elbows down, inside the door card
            fist_grip(r, s, 62)
    else:
        for s, sx in (("Left", 1), ("Right", -1)):
            tgt = Vector((sx * 0.15 * k, -0.27 * k, 0.27 * k + 0.002 * k * br))  # palms on top of the thighs
            hq = hand_world_q(rig, s, Vector((sx * 0.05, -1.0, -0.12)), Vector((0, 0, -1.0)))
            ik[s + "UpperArm"] = (tgt, Vector((sx * 0.35, 0.6, -0.8)), hq)
        relaxed_fingers(r, 28)
    return {"hips": Vector((0, 0.0, hz)), "rot": r, "ik": ik}


def carry_loco(rig, k, phase, P):
    pose = locomotion_pose(rig, k, phase, dict(P, arm_swing=0))
    r, ik = pose["rot"], pose["ik"]
    for n in [n for n in r if "Arm" in n or "Hand" in n]:
        del r[n]
    carry_upper(rig, r, ik, k, math.sin(4 * math.pi * phase))
    return pose


def key_action(rig, name, frames, loop, fn):
    arm = rig.arm
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    rig.reach_clamp = 0.0
    prev = {}
    for f in range(frames + 1):
        t = f / frames
        pose = fn(t)
        basis, _ = rig.pose_to_basis(pose)
        for n in rig.order:
            if n == "Root":
                continue
            pb = arm.pose.bones[n]
            m = basis[n]
            qq = m.to_quaternion()
            if n in prev and prev[n].dot(qq) < 0:
                qq.negate()
            prev[n] = qq
            pb.rotation_quaternion = qq
            pb.keyframe_insert("rotation_quaternion", frame=f, group=n)
            if n == "Hips":
                pb.location = m.translation
                pb.keyframe_insert("location", frame=f, group=n)
    act.use_frame_range = True
    act.frame_start, act.frame_end = 0, frames
    act.use_cyclic = loop
    act["loop"] = bool(loop)
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    return act, rig.reach_clamp


def build_all_actions(rig, k, prefix="A_Jason_", include_p2=True, mocap_walk=None):
    gaits = _build_gaits(mocap_walk)
    clips_p1 = {
        "Idle": (60, True, lambda rg, kk, t: idle_pose(rg, kk, t)),
        "Crouch_Idle": (60, True, lambda rg, kk, t: idle_pose(rg, kk, t, crouch=True)),
        "Jump_Start": (8, False, clip_jump_start),
        "Jump_Air": (20, True, jump_air),
        "Land": (9, False, clip_land),
        "Aim_Pistol_Idle": (60, True, lambda rg, kk, t: idle_pose(rg, kk, t, aim=True)),
        "Shoot_Pistol": (8, False, clip_shoot),
        "Reload_Pistol": (48, False, clip_reload),
    }
    clips_p2 = {
        "Carry_Idle": (60, True, lambda rg, kk, t: idle_pose(rg, kk, t, carry=True)),
        "Death": (45, False, clip_death),
        "Car_Enter_L": (45, False, lambda rg, kk, t: clip_car(rg, kk, t, True)),
        "Car_Exit_L": (45, False, lambda rg, kk, t: clip_car(rg, kk, t, False)),
        # B-011: seated loops - the root is the seat socket (H-point), see sit_pose().
        "Sit_Driver": (60, True, lambda rg, kk, t: sit_pose(rg, kk, t, True)),
        "Sit_Passenger": (60, True, lambda rg, kk, t: sit_pose(rg, kk, t, False)),
    }
    gaits_p2 = {
        "Carry_Walk": dict(frames=32, speed=1.4, stance=0.60, pitch=28, lift=0.06, hips_z=0.905,
                           bob=0.015, sway=0.008, pelv_roll=2.2, twist=2.5, lean=2, offset=0.05, carry=True),
    }

    out = {}
    gait_lookup = {}
    for stem, P in gaits.items():
        nm = prefix + stem
        gait_lookup[nm] = P
        act, clamp = key_action(rig, nm, P["frames"], True, lambda t, P=P: locomotion_pose(rig, k, t % 1.0, P))
        out[nm] = {"frames": P["frames"], "loop": True, "speed": P["speed"], "reach_clamp_m": round(clamp, 4)}
    for stem, (frames, loop, fn) in clips_p1.items():
        nm = prefix + stem
        act, clamp = key_action(rig, nm, frames, loop, lambda t, fn=fn: fn(rig, k, t))
        out[nm] = {"frames": frames, "loop": loop, "speed": 0.0, "reach_clamp_m": round(clamp, 4)}
    if include_p2:
        for stem, P in gaits_p2.items():
            nm = prefix + stem
            gait_lookup[nm] = P
            act, clamp = key_action(rig, nm, P["frames"], True, lambda t, P=P: carry_loco(rig, k, t % 1.0, P))
            out[nm] = {"frames": P["frames"], "loop": True, "speed": P["speed"], "reach_clamp_m": round(clamp, 4)}
        for stem, (frames, loop, fn) in clips_p2.items():
            nm = prefix + stem
            act, clamp = key_action(rig, nm, frames, loop, lambda t, fn=fn: fn(rig, k, t))
            out[nm] = {"frames": frames, "loop": loop, "speed": 0.0, "reach_clamp_m": round(clamp, 4)}

    for nm, info in out.items():
        bpy.data.actions[nm]["speed_mps"] = float(info["speed"])
        if nm.endswith("Reload_Pistol"):
            bpy.data.actions[nm]["mag_out_frame"] = 9
            bpy.data.actions[nm]["mag_in_frame"] = 32
    rig.arm.animation_data.action = bpy.data.actions[prefix + "Idle"]
    return out, gait_lookup


def measure_sliding(rig, name, speed, move_dir=FWD, thresh=0.015):
    arm = rig.arm
    act = bpy.data.actions[name]
    arm.animation_data.action = act
    if act.slots:
        arm.animation_data.action_slot = act.slots[0]
    sc = bpy.context.scene
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    d = move_dir.normalized()
    worst = 0.0
    for side in ("Left", "Right"):
        for off in (rig.heel_off, rig.ball_off):
            runs, cur = [], []
            for f in range(f0, f1 * 2 + 1):
                sc.frame_set(f0 + (f - f0) % (f1 - f0))
                pb = arm.pose.bones[side + "Foot"]
                M = arm.matrix_world @ pb.matrix
                R = pb.bone.matrix_local
                local = R.inverted() @ (Vector(pb.bone.head_local) + off)
                p = M @ local
                world = p + d * speed * ((f - f0) / FPS)
                if p.z < thresh:
                    cur.append(world)
                elif cur:
                    runs.append(cur)
                    cur = []
            if cur:
                runs.append(cur)
            for run in runs:
                if len(run) < 2:
                    continue
                xs = [w.x for w in run]
                ys = [w.y for w in run]
                worst = max(worst, math.hypot(max(xs) - min(xs), max(ys) - min(ys)))
    return worst
