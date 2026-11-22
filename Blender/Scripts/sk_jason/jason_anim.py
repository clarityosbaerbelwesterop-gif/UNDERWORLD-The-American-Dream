"""SK_Jason animation set (T-ART-02 per REQ-GP01-JASON §4/§5), procedural, in place, 30 fps, frame 0 start.

Pose model: every bone gets a rotation Q expressed in rest *armature* space (composes down the chain),
Hips get a translation offset, legs (and arms when aiming) are solved by analytic 2-bone IK.
Locomotion feet: a planted contact pivot (heel early / ball late in stance) moves backwards at exactly the
clip speed, so foot sliding is ~0 by construction; measured afterwards by measure_sliding().
"""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

FPS = 30
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
FWD = Vector((0, -1, 0))   # character front (Blender -Y = Godot +Z)


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
    return (p0 * (2 * t3 - 3 * t2 + 1) + v0 * dur * (t3 - 2 * t2 + t) + p1 * (-2 * t3 + 3 * t2)
            + v1 * dur * (t3 - t2))


class Rig:
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
        self.ankle_h = foot.head_local.z
        k = self.ankle_h / 0.095
        # contact points relative to the ankle when the foot is flat (heel / ball of the boot sole)
        self.heel_off = Vector((0, 0.050 * k, -self.ankle_h))
        self.ball_off = Vector((0, -0.125 * k, -self.ankle_h))
        self.hip_x = self.bones["LeftUpperLeg"].head_local.x
        self.pelvis_z = self.bones["Hips"].head_local.z

    # ------------------------------------------------------------ solve
    def solve(self, pose):
        """pose: {"rot": {bone: Quaternion}, "hips": Vector, "ik": {bone_chain_root: (target, pole)},
                  "world": {bone: Quaternion world-delta}} -> {bone: matrix_basis}"""
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

    ik_frames = {}
    _ik_roots = set()

    def _solve_chain(self, upper, P, spec):
        """2-bone IK. spec = (target Vector, pole Vector, end_world_delta Quaternion or None)."""
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
        self.reach_clamp = max(getattr(self, "reach_clamp", 0.0), d.length - dist)
        u = d.normalized()
        pperp = (pole - u * pole.dot(u))
        pperp = pperp.normalized() if pperp.length > 1e-6 else Vector((0, -1, 0))
        cb = max(-1.0, min(1.0, (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)))
        beta = math.acos(cb)
        K = H + (u * math.cos(beta) + pperp * math.sin(beta)) * l1
        A = H + u * dist
        hinge = pperp.cross(u).normalized()
        for bone, a, b in ((upper, H, K), (mid, K, A)):
            R = self.rest[bone]
            r_dir = (Vector(self.bones[bone].tail_local) - Vector(self.bones[bone].head_local)).normalized()
            # rest hinge = the rest bend axis (world X for legs, world Z-ish for arms)
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
        # IK chains must be computed when their root is reached; solve() handles that via _ik_roots
        basis, P = self.solve(pose)
        return basis, P


# ------------------------------------------------------------ pose building blocks
def arms_down(side_deg=74, elbow=12, fwd=0.0):
    r = {}
    r["LeftUpperArm"] = qmul(q(X, -fwd), q(Y, side_deg))
    r["RightUpperArm"] = qmul(q(X, -fwd), q(Y, -side_deg))
    r["LeftLowerArm"] = q(Z, -elbow)
    r["RightLowerArm"] = q(Z, elbow)
    r["LeftHand"] = q(Z, -4)
    r["RightHand"] = q(Z, 4)
    return r


def relaxed_fingers(r, curl=18, side=("Left", "Right")):
    for s in side:
        sg = 1 if s == "Left" else -1
        for f in ("Index", "Middle", "Ring", "Little"):
            c = curl * (1 + 0.15 * ("Index", "Middle", "Ring", "Little").index(f))
            r[f"{s}{f}Proximal"] = q(Y, sg * c)
            r[f"{s}{f}Intermediate"] = q(Y, sg * c * 1.2)
            r[f"{s}{f}Distal"] = q(Y, sg * c * 0.8)
        r[f"{s}ThumbMetacarpal"] = q(Z, -sg * 8)
        r[f"{s}ThumbProximal"] = q(Y, sg * 10)
    return r


def fist_grip(r, s, curl=72):
    sg = 1 if s == "Left" else -1
    for i, f in enumerate(("Index", "Middle", "Ring", "Little")):
        c = curl + 4 * i
        r[f"{s}{f}Proximal"] = q(Y, sg * c)
        r[f"{s}{f}Intermediate"] = q(Y, sg * c * 1.1)
        r[f"{s}{f}Distal"] = q(Y, sg * c * 0.7)
    r[f"{s}ThumbMetacarpal"] = qmul(q(Z, sg * 18), q(X, 10))
    r[f"{s}ThumbProximal"] = q(Y, sg * 25)
    r[f"{s}ThumbDistal"] = q(Y, sg * 20)
    return r


def trigger_grip(r, s="Right"):
    fist_grip(r, s, 78)
    sg = 1 if s == "Left" else -1
    r[f"{s}IndexProximal"] = q(Y, sg * 35)    # trigger finger
    r[f"{s}IndexIntermediate"] = q(Y, sg * 45)
    r[f"{s}IndexDistal"] = q(Y, sg * 20)
    return r


def frame_from(dir_v, normal_v):
    d = dir_v.normalized()
    n = (normal_v - d * normal_v.dot(d)).normalized()
    return Matrix((d, n, d.cross(n))).transposed()


def hand_world_q(rig, side, dir_v, palm_v):
    """World-delta rotation so the hand bone points along dir_v with the palm facing palm_v."""
    b = rig.bones[side + "Hand"]
    r_dir = (Vector(b.tail_local) - Vector(b.head_local)).normalized()
    Fr = frame_from(r_dir, Vector((0, 0, -1)))          # rest palm faces down (T-pose)
    Fd = frame_from(dir_v, palm_v)
    return (Fd @ Fr.transposed()).to_quaternion()


# aim: pistol at shoulder height, both hands, barrel along -Y (Godot +Z)
def aim_upper(rig, r, ik, k, breathe=0.0, recoil=0.0, sway=0.0):
    sh = rig.bones["RightUpperArm"].head_local
    tgt_r = Vector((-0.06 * k, -0.53 * k, sh.z - 0.05 * k + recoil * 0.05 * k + breathe * 0.004))
    tgt_r.y += recoil * 0.04 * k
    tgt_r.x += sway * 0.004
    hand_dir = Vector((0.0, -0.93, -0.36 - recoil * 0.6))
    rq = hand_world_q(rig, "Right", hand_dir, Vector((1, 0, 0)))
    ik["RightUpperArm"] = (tgt_r, Vector((-0.4, 0.3, -1)), rq)
    tgt_l = tgt_r + Vector((0.045 * k, 0.030 * k, -0.030 * k))
    lq = hand_world_q(rig, "Left", Vector((-0.45, -0.75, -0.35)), Vector((-1, 0.1, -0.2)))
    ik["LeftUpperArm"] = (tgt_l, Vector((0.4, 0.3, -1)), lq)
    r["RightShoulder"] = q(Y, 4)
    r["LeftShoulder"] = qmul(q(Z, 10), q(Y, -4))
    trigger_grip(r, "Right")
    fist_grip(r, "Left", 60)
    r["UpperChest"] = qmul(r.get("UpperChest", Quaternion()), q(X, 4 - recoil * 3))
    r["Head"] = qmul(r.get("Head", Quaternion()), q(X, 6))
    return r, ik


def stand_legs(rig, ik, hips_z, k, foot_dx=0.0, r_back=0.0):
    for s, sx in (("Left", 1), ("Right", -1)):
        a = Vector((sx * (rig.hip_x + foot_dx), (r_back if s == "Right" else -0.3 * r_back), rig.ankle_h))
        ik[s + "UpperLeg"] = (a, Vector((0, -1, 0)), None)


# ------------------------------------------------------------ locomotion
def foot_track(rig, phase, speed, T, stance, move_dir, pitch_amp, lift, offset_fwd, bias=0.0):
    """Ankle target + foot world rotation for one leg at gait phase in [0,1)."""
    d = move_dir.normalized()
    s = speed * stance * T                      # stance travel (m)
    fwd = (d.dot(FWD) >= -0.1)                  # forward-ish gait rolls heel->ball
    if speed == 0:
        return Vector((0, 0, rig.ankle_h)), Quaternion(), 0.0

    def contact(ps):                            # planted sole point (under ankle when flat)
        return d * (s / 2 + offset_fwd) - d * (speed * ps * stance * T) + bias * Vector((0, 0, 0))

    def stance_pitch(ps):
        if fwd:
            if ps < 0.15:
                return -pitch_amp * 0.4 * (1 - ps / 0.15)          # toes up at heel strike
            if ps > 0.55:
                return pitch_amp * smooth((ps - 0.55) / 0.45)     # heel off, roll onto the ball
            return 0.0
        if ps < 0.15:
            return pitch_amp * 0.4 * (1 - ps / 0.15)
        if ps > 0.55:
            return -pitch_amp * 0.4 * smooth((ps - 0.55) / 0.45)
        return 0.0

    def ankle_from(cpt, pitch):
        Rq = q(X, pitch)
        if pitch > 0:     # pivot on ball (sole point at ground level)
            off = rig.ball_off
        elif pitch < 0:   # pivot on heel
            off = rig.heel_off
        else:
            off = None
        if off is not None:
            piv = cpt + Vector((off.x, off.y, 0.0))
            return piv + Rq @ (-off), Rq
        return cpt + Vector((0, 0, rig.ankle_h)), Rq

    if phase < stance:
        ps = phase / stance
        a, Rq = ankle_from(contact(ps), math.degrees(0) + stance_pitch(ps))
        return a, Rq, 1.0
    u = (phase - stance) / (1 - stance)
    Ts = (1 - stance) * T
    a0, _ = ankle_from(contact(1.0), stance_pitch(1.0))
    a1, _ = ankle_from(contact(0.0), stance_pitch(0.0))
    v = -d * speed
    a = hermite(a0, a1, v * 0.6, v * 0.6, u, Ts)
    a.z += lift * math.sin(math.pi * u) ** 1.2
    p0, p1 = stance_pitch(1.0), stance_pitch(0.0)
    pitch = p0 + (p1 - p0) * smooth(u) - 0.25 * pitch_amp * math.sin(math.pi * u)
    if fwd and pitch > 0:
        a.z += 0.0
    return a, q(X, pitch), 0.0


def locomotion_pose(rig, k, phase, P):
    """P: gait parameters dict. Returns pose dict."""
    T = P["frames"] / FPS
    d = P.get("dir", FWD)
    r, ik = {}, {}
    st = P["stance"]
    for s, sx, off in (("Left", 1, 0.0), ("Right", -1, 0.5)):
        ph = (phase + off) % 1.0
        a, Rq, _ = foot_track(rig, ph, P["speed"], T, st, d, P["pitch"], P["lift"] * k, P.get("offset", 0.0) * k)
        a = a + Vector((sx * (rig.hip_x + P.get("foot_dx", 0.0) * k), 0, 0))
        if P.get("lateral_avoid") and abs(d.x) > 0.5:
            # strafing: the swinging foot passes behind the planted one
            if ph >= st:
                u = (ph - st) / (1 - st)
                a.y += 0.11 * k * math.sin(math.pi * u)
        ik[s + "UpperLeg"] = (a, Vector((0, -1, 0)), Rq)
    w = 2 * math.pi * phase
    bob = P.get("bob", 0.02) * k
    hz = P["hips_z"] * k - rig.pelvis_z + bob * math.cos(2 * w - 2 * math.pi * P.get("bob_phase", 0.3))
    sway = P.get("sway", 0.012) * k * math.sin(w)
    pose = {"hips": Vector((sway, P.get("hips_y", 0.0) * k, hz)), "rot": r, "ik": ik}
    twist = P.get("twist", 6)
    lean = P.get("lean", 4)
    r["Hips"] = qmul(q(Z, -twist * math.sin(w)), q(X, lean * 0.3))
    r["Spine"] = qmul(q(Z, twist * 0.6 * math.sin(w)), q(X, lean * 0.5))
    r["Chest"] = qmul(q(Z, twist * 0.6 * math.sin(w)), q(X, lean * 0.3))
    r["UpperChest"] = q(Z, twist * 0.2 * math.sin(w))
    r["Neck"] = q(X, -lean * 0.5)
    r["Head"] = q(Z, twist * -0.2 * math.sin(w))
    if P.get("aim"):
        r["Hips"] = q(X, lean * 0.3)
        r["Spine"] = q(Z, 0.0)
        r["Chest"] = q(Z, 0.0)
        aim_upper(rig, r, ik, k, breathe=math.sin(2 * w))
        r["Head"] = q(X, 6)
    else:
        sw = P.get("arm_swing", 20)
        el = P.get("elbow", 15)
        swing = sw * math.sin(w)
        r.update({
            "LeftUpperArm": qmul(q(X, swing), q(Y, P.get("arm_side", 72))),
            "RightUpperArm": qmul(q(X, -swing), q(Y, -P.get("arm_side", 72))),
            "LeftLowerArm": q(Z, -(el + max(0.0, -swing) * P.get("elbow_gain", 0.5))),
            "RightLowerArm": q(Z, el + max(0.0, swing) * P.get("elbow_gain", 0.5)),
            "LeftHand": q(Z, -6), "RightHand": q(Z, 6),
        })
        if P.get("fist"):
            fist_grip(r, "Left", 55)
            fist_grip(r, "Right", 55)
        else:
            relaxed_fingers(r)
    return pose


GAITS = {  # frames per cycle -> length = frames/30 s; speeds per REQ §5
    "A_Jason_Walk": dict(frames=32, speed=1.4, stance=0.60, pitch=32, lift=0.07, hips_z=0.912, bob=0.018,
                         arm_swing=20, elbow=14, twist=6, lean=3, offset=0.06),
    "A_Jason_Run": dict(frames=20, speed=3.5, stance=0.36, pitch=40, lift=0.17, hips_z=0.885, bob=0.03,
                        arm_swing=38, elbow=78, elbow_gain=0.2, twist=12, lean=10, offset=0.06, fist=True, bob_phase=0.18),
    "A_Jason_Sprint": dict(frames=16, speed=6.0, stance=0.30, pitch=45, lift=0.26, hips_z=0.875, bob=0.035,
                           arm_swing=55, elbow=88, elbow_gain=0.1, twist=14, lean=16, offset=0.09, fist=True, bob_phase=0.15),
    "A_Jason_Crouch_Walk": dict(frames=36, speed=1.2, stance=0.65, pitch=22, lift=0.06, hips_z=0.66, bob=0.012,
                                arm_swing=10, elbow=40, twist=4, lean=24, offset=0.03, foot_dx=0.03, sway=0.006),
    "A_Jason_Aim_Pistol_Walk_F": dict(frames=24, speed=2.0, stance=0.55, pitch=20, lift=0.07, hips_z=0.89, bob=0.012,
                                      twist=0, lean=4, aim=True, offset=0.05, sway=0.006),
    "A_Jason_Aim_Pistol_Walk_B": dict(frames=24, speed=2.0, stance=0.55, pitch=15, lift=0.07, hips_z=0.89, bob=0.012,
                                      twist=0, lean=4, aim=True, dir=Vector((0, 1, 0)), offset=0.0, sway=0.006),
    "A_Jason_Aim_Pistol_Walk_L": dict(frames=24, speed=2.0, stance=0.55, pitch=6, lift=0.07, hips_z=0.88, bob=0.012,
                                      twist=0, lean=4, aim=True, dir=Vector((1, 0, 0)), offset=0.0, sway=0.0,
                                      lateral_avoid=True, foot_dx=0.03),
    "A_Jason_Aim_Pistol_Walk_R": dict(frames=24, speed=2.0, stance=0.55, pitch=6, lift=0.07, hips_z=0.88, bob=0.012,
                                      twist=0, lean=4, aim=True, dir=Vector((-1, 0, 0)), offset=0.0, sway=0.0,
                                      lateral_avoid=True, foot_dx=0.03),
}


# ------------------------------------------------------------ non-cyclic / idle clips (pose functions of t in [0,1])
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
        r.update(arms_down(66, 45, fwd=25))
        relaxed_fingers(r, 25)
        return {"hips": Vector((0, 0.03 * k, hz)), "rot": r, "ik": ik}
    hz = -0.012 * k + 0.004 * k * math.sin(w)
    stand_legs(rig, ik, hz, k, foot_dx=0.025 * k, r_back=0.06 * k if aim else 0.0)
    r["Hips"] = q(Z, 1.5 * math.sin(w))
    r["Spine"] = q(X, 1.0 * math.sin(w))
    r["Chest"] = q(X, 1.2 * math.sin(w + 0.5))
    r["UpperChest"] = q(X, 0.8 * math.sin(w + 1.0))
    r["Head"] = qmul(q(Z, 3 * math.sin(w * 0.5 + 0.3)), q(X, -1 + 1.5 * math.sin(w + 2)))
    if aim:
        aim_upper(rig, r, ik, k, breathe=math.sin(w), sway=math.sin(w))
    elif carry:
        carry_upper(rig, r, ik, k, math.sin(w))
    else:
        r.update(arms_down(73, 10 + 2 * math.sin(w), fwd=2))
        r["LeftUpperArm"] = qmul(q(X, 1.5 * math.sin(w)), r["LeftUpperArm"])
        r["RightUpperArm"] = qmul(q(X, -1.5 * math.sin(w)), r["RightUpperArm"])
        relaxed_fingers(r)
    return {"hips": Vector((0.004 * k * math.sin(w), 0, hz)), "rot": r, "ik": ik}


def carry_upper(rig, r, ik, k, breathe=0.0):
    """Hold a 0.6 x 0.4 x 0.4 m crate in front of the belly (hands on its sides)."""
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
    """Linear blend of two pose dicts (rot slerp, hips lerp, IK targets lerp)."""
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
    r.update(arms_down(70, 20, fwd=-35 * depth / 0.2))
    relaxed_fingers(r, 25)
    return {"hips": Vector((0, 0.02 * k, hz)), "rot": r, "ik": ik}


def jump_air(rig, k, t):
    """Airborne: legs tucked (knees up), arms raised slightly. Feet relative to hips."""
    w = 2 * math.pi * t
    r, ik = {}, {}
    hz = 0.0
    for s, sx, o in (("Left", 1, 0.0), ("Right", -1, math.pi)):
        a = Vector((sx * rig.hip_x, (-0.05 + 0.04 * math.sin(w + o)) * k, rig.ankle_h + (0.22 + 0.03 * math.sin(w + o)) * k))
        ik[s + "UpperLeg"] = (a, Vector((0, -1, 0.2)), q(X, 25))
    r["Hips"] = q(X, -4)
    r["Spine"] = q(X, 6 + 2 * math.sin(w))
    r["Neck"] = q(X, -4)
    r.update(arms_down(40 + 4 * math.sin(w), 35, fwd=15))
    relaxed_fingers(r, 15)
    return {"hips": Vector((0, 0, hz)), "rot": r, "ik": ik}


def stand_pose(rig, k):
    return idle_pose(rig, k, 0.0)


def clip_jump_start(rig, k, t):        # 0.25 s: dip then extend onto the toes
    if t < 0.55:
        return jump_crouch(rig, k, 0.17 * smooth(t / 0.55))
    u = (t - 0.55) / 0.45
    a = jump_crouch(rig, k, 0.17)
    b = jump_crouch(rig, k, 0.0)
    p = blend_pose(rig, a, b, smooth(u))
    for s in ("LeftUpperLeg", "RightUpperLeg"):
        tg, pole, _ = p["ik"][s]
        tg = tg + Vector((0, 0, 0.06 * k * smooth(u)))          # heels lift (toes push off)
        p["ik"][s] = (tg, pole, q(X, 35 * smooth(u)))
    p["rot"]["LeftUpperArm"] = qmul(q(X, 25 * smooth(u)), q(Y, 70 - 25 * smooth(u)))
    p["rot"]["RightUpperArm"] = qmul(q(X, 25 * smooth(u)), q(Y, -(70 - 25 * smooth(u))))
    return p


def clip_land(rig, k, t):              # 0.3 s: impact absorb and recover
    if t < 0.35:
        return blend_pose(rig, jump_air(rig, k, 0.0), jump_crouch(rig, k, 0.20), smooth(t / 0.35))
    return blend_pose(rig, jump_crouch(rig, k, 0.20), stand_pose(rig, k), smooth((t - 0.35) / 0.65))


def clip_shoot(rig, k, t):             # 0.25 s recoil, upper body
    p = idle_pose(rig, k, 0.0, aim=True)
    kick = math.sin(math.pi * min(1.0, t / 0.35)) if t < 0.35 else max(0.0, 1 - (t - 0.35) / 0.65) * 0.25 * math.sin(math.pi * 0.5)
    kick = (1 - smooth(t / 1.0)) * math.exp(-((t - 0.12) ** 2) / 0.012) * 1.0 + 0.0
    r, ik = {}, p["ik"]
    r.update({n: qq for n, qq in p["rot"].items()})
    aim_upper(rig, r, ik, k, recoil=kick)
    r["Head"] = qmul(q(X, 6 - 3 * kick), Quaternion())
    p["rot"] = r
    return p


def clip_reload(rig, k, t):            # 1.6 s: drop mag, insert new from belt, rack slide
    p = idle_pose(rig, k, t * 0.8, aim=False)
    r, ik = p["rot"], p["ik"]
    for n in list(r):
        if "Arm" in n or "Hand" in n or any(f in n for f in ("Index", "Middle", "Ring", "Little", "Thumb")):
            del r[n]
    # gun hand lowered/tilted toward the chest
    sh = rig.bones["RightUpperArm"].head_local
    gun = Vector((-0.06 * k, -0.36 * k, sh.z - 0.20 * k))
    tilt = math.sin(math.pi * min(1.0, t / 0.25)) if t < 0.25 else (0.0 if t < 0.3 else 0.0)
    gq = hand_world_q(rig, "Right", Vector((0.25, -0.85, -0.25 + 0.3 * tilt)), Vector((1, 0, 0.2)))
    ik["RightUpperArm"] = (gun, Vector((-0.4, 0.3, -1)), gq)
    trigger_grip(r, "Right")
    # support hand path: gun -> belt (left hip) -> gun (insert) -> over slide (rack) -> grip
    belt = Vector((0.16 * k, -0.06 * k, 0.98 * k))
    near = gun + Vector((0.05 * k, 0.04 * k, -0.05 * k))
    rack = gun + Vector((0.02 * k, 0.10 * k, 0.05 * k))
    keys = [(0.0, near), (0.18, near), (0.38, belt), (0.48, belt), (0.68, near), (0.80, rack + Vector((0, -0.08 * k, 0))),
            (0.88, rack), (1.0, near)]
    for (t0, p0), (t1, p1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            lt = p0.lerp(p1, smooth((t - t0) / max(t1 - t0, 1e-6)))
            break
    lq = hand_world_q(rig, "Left", Vector((-0.3, -0.8, -0.3)), Vector((-1, 0, -0.3)))
    ik["LeftUpperArm"] = (lt, Vector((0.4, 0.4, -1)), lq)
    fist_grip(r, "Left", 50)
    r["Head"] = q(X, 18)
    r["Neck"] = q(X, 6)
    r["UpperChest"] = q(X, 4)
    return p


def clip_death(rig, k, t):             # ~1.5 s: knees buckle, fall backwards-left to the ground
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
    """Car enter/exit at the left door: step toward +X... approximated as a sit-down/stand-up with a turn.
    Enter: from standing at SOCKET_Exit_Left to seated (driver seat pose); Exit = reverse."""
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


# name: (frames, loop, fn(rig, k, t)) with t in [0, 1] over the clip; cyclic clips have frame N == frame 0
CLIPS_P1 = {
    "A_Jason_Idle": (60, True, lambda rig, k, t: idle_pose(rig, k, t)),
    "A_Jason_Crouch_Idle": (60, True, lambda rig, k, t: idle_pose(rig, k, t, crouch=True)),
    "A_Jason_Jump_Start": (8, False, clip_jump_start),
    "A_Jason_Jump_Loop": (20, True, jump_air),
    "A_Jason_Land": (9, False, clip_land),
    "A_Jason_Aim_Pistol_Idle": (60, True, lambda rig, k, t: idle_pose(rig, k, t, aim=True)),
    "A_Jason_Shoot_Pistol": (8, False, clip_shoot),
    "A_Jason_Reload_Pistol": (48, False, clip_reload),
}
CLIPS_P2 = {
    "A_Jason_Carry_Idle": (60, True, lambda rig, k, t: idle_pose(rig, k, t, carry=True)),
    "A_Jason_Death": (45, False, clip_death),
    "A_Jason_Car_Enter_L": (45, False, lambda rig, k, t: clip_car(rig, k, t, True)),
    "A_Jason_Car_Exit_L": (45, False, lambda rig, k, t: clip_car(rig, k, t, False)),
}
GAITS_P2 = {
    "A_Jason_Carry_Walk": dict(frames=32, speed=1.4, stance=0.60, pitch=28, lift=0.06, hips_z=0.905, bob=0.015,
                               twist=2, lean=2, offset=0.05, carry=True, sway=0.008),
}


def carry_loco(rig, k, phase, P):
    pose = locomotion_pose(rig, k, phase, dict(P, arm_swing=0))
    r, ik = pose["rot"], pose["ik"]
    for n in [n for n in r if "Arm" in n or "Hand" in n]:
        del r[n]
    carry_upper(rig, r, ik, k, math.sin(4 * math.pi * phase))
    return pose


# ------------------------------------------------------------ keying
def key_action(rig, name, frames, loop, fn, slot_owner):
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
            if n in prev and prev[n].dot(qq) < 0:       # keep quaternion hemisphere continuous
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


def build_actions(rig, k, include_p2=True):
    out = {}
    for name, P in GAITS.items():
        act, clamp = key_action(rig, name, P["frames"], True, lambda t, P=P: locomotion_pose(rig, k, t % 1.0, P), rig.arm)
        out[name] = {"frames": P["frames"], "loop": True, "speed": P["speed"], "reach_clamp_m": round(clamp, 4)}
    for name, (frames, loop, fn) in CLIPS_P1.items():
        act, clamp = key_action(rig, name, frames, loop, lambda t, fn=fn: fn(rig, k, t), rig.arm)
        out[name] = {"frames": frames, "loop": loop, "speed": 0.0, "reach_clamp_m": round(clamp, 4)}
    if include_p2:
        for name, P in GAITS_P2.items():
            act, clamp = key_action(rig, name, P["frames"], True, lambda t, P=P: carry_loco(rig, k, t % 1.0, P), rig.arm)
            out[name] = {"frames": P["frames"], "loop": True, "speed": P["speed"], "reach_clamp_m": round(clamp, 4)}
        for name, (frames, loop, fn) in CLIPS_P2.items():
            act, clamp = key_action(rig, name, frames, loop, lambda t, fn=fn: fn(rig, k, t), rig.arm)
            out[name] = {"frames": frames, "loop": loop, "speed": 0.0, "reach_clamp_m": round(clamp, 4)}
    for name, info in out.items():  # manifest: animations[].speed_mps (REQ §5: list loop/speed/frames)
        bpy.data.actions[name]["speed_mps"] = float(info["speed"])
    rig.arm.animation_data.action = bpy.data.actions["A_Jason_Idle"]
    return out


# ------------------------------------------------------------ verification: foot sliding
def measure_sliding(rig, name, speed, move_dir=FWD, thresh=0.015):
    """Max horizontal drift (m) of the heel/ball contact points while they touch the ground, in world space
    with the character moving at `speed` along move_dir (in-place clip + root translation)."""
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
            for f in range(f0, f1 * 2 + 1):                 # two cycles to catch wrap-around contacts
                sc.frame_set(f0 + (f - f0) % (f1 - f0))
                pb = arm.pose.bones[side + "Foot"]
                M = arm.matrix_world @ pb.matrix
                # contact point = foot pose applied to the rest offset from the ankle
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
