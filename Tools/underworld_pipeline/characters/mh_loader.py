"""CC0 MakeHuman/MPFB2 parametric human loader, morph engine, .mhclo binder & SkeletonProfileHumanoid rig.

Reads ONLY CC0-1.0 data files from .cache/uwp_sources/ (base.obj, *.target[.gz], *.mhclo,
rig.game_engine.json, weights.game_engine.json, faceunits01, visemes01). No GPLv3 code is imported.

Coordinate conversion (TD-004):
  MakeHuman OBJ space: decimetres, +X = character left, +Y = up, +Z = front
  Blender space:       metres,     +X = character left, -Y = front (Godot +Z), +Z = up (Godot +Y)
  Mapping: (x, y, z)_mh -> (x * 0.1, -z * 0.1, y * 0.1)_blender, then ground-shifted so min_z = 0
  and uniformly scaled to spec['height_m'].
"""
import gzip
import json
import math
import os
import re

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

# Exact 1:1 mapping from MakeHuman CC0 game_engine rig (53 bones) -> Godot SkeletonProfileHumanoid
# (53 bones matching Blender/Scripts/sk_jason/expected_bones.txt & REQ-GP01-JASON §3).
MH_TO_HUMANOID = {
    "Root": "Root",
    "pelvis": "Hips",
    "spine_01": "Spine",
    "spine_02": "Chest",
    "spine_03": "UpperChest",
    "neck_01": "Neck",
    "head": "Head",
    "clavicle_l": "LeftShoulder",
    "upperarm_l": "LeftUpperArm",
    "lowerarm_l": "LeftLowerArm",
    "hand_l": "LeftHand",
    "clavicle_r": "RightShoulder",
    "upperarm_r": "RightUpperArm",
    "lowerarm_r": "RightLowerArm",
    "hand_r": "RightHand",
    "thigh_l": "LeftUpperLeg",
    "calf_l": "LeftLowerLeg",
    "foot_l": "LeftFoot",
    "ball_l": "LeftToes",
    "thigh_r": "RightUpperLeg",
    "calf_r": "RightLowerLeg",
    "foot_r": "RightFoot",
    "ball_r": "RightToes",
    "thumb_01_l": "LeftThumbMetacarpal",
    "thumb_02_l": "LeftThumbProximal",
    "thumb_03_l": "LeftThumbDistal",
    "index_01_l": "LeftIndexProximal",
    "index_02_l": "LeftIndexIntermediate",
    "index_03_l": "LeftIndexDistal",
    "middle_01_l": "LeftMiddleProximal",
    "middle_02_l": "LeftMiddleIntermediate",
    "middle_03_l": "LeftMiddleDistal",
    "ring_01_l": "LeftRingProximal",
    "ring_02_l": "LeftRingIntermediate",
    "ring_03_l": "LeftRingDistal",
    "pinky_01_l": "LeftLittleProximal",
    "pinky_02_l": "LeftLittleIntermediate",
    "pinky_03_l": "LeftLittleDistal",
    "thumb_01_r": "RightThumbMetacarpal",
    "thumb_02_r": "RightThumbProximal",
    "thumb_03_r": "RightThumbDistal",
    "index_01_r": "RightIndexProximal",
    "index_02_r": "RightIndexIntermediate",
    "index_03_r": "RightIndexDistal",
    "middle_01_r": "RightMiddleProximal",
    "middle_02_r": "RightMiddleIntermediate",
    "middle_03_r": "RightMiddleDistal",
    "ring_01_r": "RightRingProximal",
    "ring_02_r": "RightRingIntermediate",
    "ring_03_r": "RightRingDistal",
    "pinky_01_r": "RightLittleProximal",
    "pinky_02_r": "RightLittleIntermediate",
    "pinky_03_r": "RightLittleDistal",
}

HUMANOID_ORDER = list(MH_TO_HUMANOID.values())


def mh_to_blender_coords(pts_mh):
    """Convert (N, 3) MakeHuman decimetre Y-up +Z-front -> Blender metre Z-up -Y-front."""
    arr = np.asarray(pts_mh, dtype=np.float64)
    out = np.empty_like(arr)
    out[..., 0] = arr[..., 0] * 0.1
    out[..., 1] = -arr[..., 2] * 0.1
    out[..., 2] = arr[..., 1] * 0.1
    return out


def parse_obj(path, keep_groups=None):
    """Parse Wavefront OBJ returning verts (N,3), uvs (M,2), faces [(v_idx_list, uv_idx_list)], group_per_face."""
    verts, uvs, faces, fgroups = [], [], [], []
    cur_g = "default"
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("v "):
                parts = line.split()
                verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif line.startswith("vt "):
                parts = line.split()
                uvs.append((float(parts[1]), float(parts[2])))
            elif line.startswith("g "):
                cur_g = line.split()[1] if len(line.split()) > 1 else "default"
            elif line.startswith("f "):
                if keep_groups is not None and cur_g not in keep_groups:
                    continue
                vs, ts = [], []
                for tok in line.split()[1:]:
                    p = tok.split("/")
                    vs.append(int(p[0]) - 1)
                    ts.append(int(p[1]) - 1 if len(p) > 1 and p[1] else -1)
                if len(vs) >= 3:
                    faces.append((vs, ts))
                    fgroups.append(cur_g)
    return np.array(verts, dtype=np.float64), np.array(uvs, dtype=np.float64) if uvs else np.zeros((0, 2)), faces, fgroups


def read_target(path):
    """Load MakeHuman .target or .target.gz -> (indices ndarray[int32], deltas ndarray[float64, (K,3)])."""
    opener = gzip.open if path.endswith(".gz") else open
    idxs, deltas = [], []
    with opener(path, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            p = s.split()
            if len(p) >= 4:
                idxs.append(int(p[0]))
                deltas.append((float(p[1]), float(p[2]), float(p[3])))
    if not idxs:
        return np.zeros((0,), dtype=np.int32), np.zeros((0, 3), dtype=np.float64)
    return np.array(idxs, dtype=np.int32), np.array(deltas, dtype=np.float64)


def _piecewise_weights(val, stops):
    """Piecewise linear interpolation weights across ordered [(name, pos), ...]."""
    val = max(stops[0][1], min(stops[-1][1], float(val)))
    for i in range(len(stops) - 1):
        n0, x0 = stops[i]
        n1, x1 = stops[i + 1]
        if x0 <= val <= x1:
            t = (val - x0) / max(x1 - x0, 1e-9)
            out = {}
            if 1.0 - t > 1e-6:
                out[n0] = 1.0 - t
            if t > 1e-6:
                out[n1] = t
            return out
    return {stops[-1][0]: 1.0}


class MakeHumanBase:
    """In-memory parametric MakeHuman hm08 human model with morphs, blendshapes, .mhclo binder, and rig."""

    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.mpfb_data = os.path.join(cache_dir, "mpfb2", "src", "mpfb", "data")
        if not os.path.isdir(self.mpfb_data):
            raise FileNotFoundError(f"MPFB2 CC0 data missing at {self.mpfb_data}; run fetch_sources.py")
        obj_path = os.path.join(self.mpfb_data, "3dobjs", "base.obj")
        self.base_verts_mh, self.base_uvs, self.body_faces, _ = parse_obj(obj_path, keep_groups={"body"})
        self.verts_mh = self.base_verts_mh.copy()

        vg_path = os.path.join(self.mpfb_data, "mesh_metadata", "basemesh_vertex_groups.json")
        self.vgroups = json.load(open(vg_path))
        self.body_vert_indices = self._expand_ranges(self.vgroups["body"])
        self.body_vert_set = set(self.body_vert_indices)

        self.target_index = self._index_targets()
        self.target_catalog = json.load(open(os.path.join(self.mpfb_data, "targets", "target.json")))

        # Filled after finalize_scale()
        self.scale_k = 1.0
        self.z_shift = 0.0
        self.verts_bl = None
        self.shape_deltas_mh = {}  # name -> sparse (idxs, deltas_mh)
        self.mh_weights = json.load(open(os.path.join(self.mpfb_data, "rigs", "standard", "weights.game_engine.json")))["weights"]
        self.mh_rig_def = json.load(open(os.path.join(self.mpfb_data, "rigs", "standard", "rig.game_engine.json")))

    @staticmethod
    def _expand_ranges(ranges):
        out = []
        for s, e in ranges:
            out.extend(range(int(s), int(e) + 1))
        return out

    def _index_targets(self):
        idx = {}
        troot = os.path.join(self.mpfb_data, "targets")
        for dp, _, fns in os.walk(troot):
            for fn in fns:
                if fn.endswith(".target.gz") or fn.endswith(".target"):
                    stem = fn[:-10] if fn.endswith(".target.gz") else fn[:-7]
                    rel = os.path.relpath(os.path.join(dp, fn), troot)
                    idx[rel] = os.path.join(dp, fn)
                    idx.setdefault(stem, os.path.join(dp, fn))
        return idx

    def _apply_target_file(self, path, weight):
        if abs(weight) < 1e-6 or not path or not os.path.isfile(path):
            return
        idxs, deltas = read_target(path)
        if len(idxs):
            self.verts_mh[idxs] += deltas * float(weight)

    def apply_macro(self, macro):
        """Apply MakeHuman macrodetails: gender, age, muscle, weight, proportions, height_morph, ethnicity."""
        gender = float(macro.get("gender", 1.0))          # 0=female, 1=male
        age = float(macro.get("age", 0.56))               # 0.50=young (~25), 0.58=~34, 0.78=~60
        muscle = float(macro.get("muscle", 0.65))         # 0..1
        weight = float(macro.get("weight", 0.45))         # 0..1
        proportions = float(macro.get("proportions", 0.65))
        height_morph = float(macro.get("height_morph", 0.65))
        eth = macro.get("ethnicity", {"caucasian": 0.65, "asian": 0.25, "african": 0.10})
        eth_sum = sum(eth.values()) or 1.0
        eth = {k: float(v) / eth_sum for k, v in eth.items()}

        gw = _piecewise_weights(gender, [("female", 0.0), ("male", 1.0)])
        aw = _piecewise_weights(age, [("baby", 0.0), ("child", 0.1875), ("young", 0.5), ("old", 1.0)])
        mw = _piecewise_weights(muscle, [("minmuscle", 0.0), ("averagemuscle", 0.5), ("maxmuscle", 1.0)])
        ww = _piecewise_weights(weight, [("minweight", 0.0), ("averageweight", 0.5), ("maxweight", 1.0)])

        md = os.path.join(self.mpfb_data, "targets", "macrodetails")

        # 1. Universal gender/age/muscle/weight
        for g, wg in gw.items():
            for a, wa in aw.items():
                for m, wm in mw.items():
                    for w, wwt in ww.items():
                        c = wg * wa * wm * wwt
                        p = os.path.join(md, f"universal-{g}-{a}-{m}-{w}.target.gz")
                        self._apply_target_file(p, c)

        # 2. Ethnicity
        for e, we in eth.items():
            if we <= 1e-6:
                continue
            for g, wg in gw.items():
                for a, wa in aw.items():
                    p = os.path.join(md, f"{e}-{g}-{a}.target.gz")
                    self._apply_target_file(p, we * wg * wa)

        # 3. Height morph
        if abs(height_morph - 0.5) > 1e-4:
            htag = "maxheight" if height_morph > 0.5 else "minheight"
            hf = abs(height_morph - 0.5) * 2.0
            for g, wg in gw.items():
                for a, wa in aw.items():
                    for m, wm in mw.items():
                        for w, wwt in ww.items():
                            p = os.path.join(md, "height", f"{g}-{a}-{m}-{w}-{htag}.target.gz")
                            self._apply_target_file(p, hf * wg * wa * wm * wwt)

        # 4. Proportions morph
        if abs(proportions - 0.5) > 1e-4:
            ptag = "idealproportions" if proportions > 0.5 else "uncommonproportions"
            pf = abs(proportions - 0.5) * 2.0
            for g, wg in gw.items():
                for a, wa in aw.items():
                    if a == "baby":
                        continue
                    for m, wm in mw.items():
                        for w, wwt in ww.items():
                            p = os.path.join(md, "proportions", f"{g}-{a}-{m}-{w}-{ptag}.target.gz")
                            self._apply_target_file(p, pf * wg * wa * wm * wwt)

    def apply_morphs(self, morphs):
        """Apply fine-grained named targets (either direct target stem/relpath or target.json category name)."""
        # Build lookup of target.json category entries for signed [-1..1] symmetric sliders
        cat_map = {}
        for _, grp in self.target_catalog.items():
            for c in grp.get("categories", []):
                cat_map[c["name"]] = c
        applied = 0
        for key, val in (morphs or {}).items():
            val = float(val)
            if abs(val) < 1e-6:
                continue
            if key in cat_map:
                c = cat_map[key]
                opp = c.get("opposites", {})
                if c.get("has_left_and_right"):
                    t_l = opp.get("positive-left") if val > 0 else opp.get("negative-left")
                    t_r = opp.get("positive-right") if val > 0 else opp.get("negative-right")
                    for tn in (t_l, t_r):
                        if tn and tn in self.target_index:
                            self._apply_target_file(self.target_index[tn], abs(val))
                            applied += 1
                else:
                    tn = opp.get("positive-unsided") if val > 0 else opp.get("negative-unsided")
                    if tn and tn in self.target_index:
                        self._apply_target_file(self.target_index[tn], abs(val))
                        applied += 1
            elif key in self.target_index:
                self._apply_target_file(self.target_index[key], val)
                applied += 1
            else:
                print(f"[CHAR][WARN] unknown morph target '{key}' (skipped)")
        return applied

    def _mpfb_expression_paths(self):
        """Map the 36 CC0 expression units bundled with MPFB2 (targets/expression/units/*)."""
        base = os.path.join(self.mpfb_data, "targets", "expression", "units")
        if not os.path.isdir(base):
            return {}
        eth = sorted(os.listdir(base))
        folder = os.path.join(base, "caucasian" if "caucasian" in eth else (eth[0] if eth else ""))
        out = {}
        if os.path.isdir(folder):
            for fn in sorted(os.listdir(folder)):
                if fn.endswith(".target.gz"):
                    out[fn[:-10]] = os.path.join(folder, fn)
                elif fn.endswith(".target"):
                    out[fn[:-7]] = os.path.join(folder, fn)
        return out

    def load_blendshape_targets(self, shape_names=None):
        """Load CC0 facial expression morphs into self.shape_deltas_mh.

        Priority 1: MPFB2's bundled expression units (already CC0 and on disk):
          eye-*-closure (blink), eyebrows-*-inner-up/down, mouth-open (jawOpen),
          mouth-*-retraction (smile/frown), nose-*-elevation, mouth-pursing (visemes).
        Priority 2: the MakeHuman `faceunits01.zip` / `visemes01.zip` packs when present,
          which use ARKit names. Missing targets are simply skipped, never faked.
        """
        fu_dir = os.path.join(self.cache_dir, "faceunits01", "targets", "faceunits")
        vi_dir = os.path.join(self.cache_dir, "visemes01", "targets", "visemes")

        # Default compact production facial set (ARKit expressions + core visemes)
        default_map = {
            # Expressions (ARKit names)
            "eyeBlinkLeft": os.path.join(fu_dir, "eyeBlinkLeft.target"),
            "eyeBlinkRight": os.path.join(fu_dir, "eyeBlinkRight.target"),
            "browDownLeft": os.path.join(fu_dir, "browDownLeft.target"),
            "browDownRight": os.path.join(fu_dir, "browDownRight.target"),
            "browInnerUp": os.path.join(fu_dir, "browInnerUp.target"),
            "mouthSmileLeft": os.path.join(fu_dir, "mouthSmileLeft.target"),
            "mouthSmileRight": os.path.join(fu_dir, "mouthSmileRight.target"),
            "mouthFrownLeft": os.path.join(fu_dir, "mouthFrownLeft.target"),
            "mouthFrownRight": os.path.join(fu_dir, "mouthFrownRight.target"),
            "jawOpen": os.path.join(fu_dir, "jawOpen.target"),
            "noseSneerLeft": os.path.join(fu_dir, "noseSneerLeft.target"),
            "noseSneerRight": os.path.join(fu_dir, "noseSneerRight.target"),
            "cheekSquintLeft": os.path.join(fu_dir, "cheekSquintLeft.target"),
            "cheekSquintRight": os.path.join(fu_dir, "cheekSquintRight.target"),
            # Visemes (mapped from visemes01)
            "viseme_aa": os.path.join(vi_dir, "aa_02.target"),
            "viseme_E": os.path.join(vi_dir, "ey_eh_uh_04.target"),
            "viseme_I": os.path.join(vi_dir, "iy_ih_06.target"),
            "viseme_O": os.path.join(vi_dir, "ow_08.target"),
            "viseme_U": os.path.join(vi_dir, "uw_07.target"),
            "viseme_PP": os.path.join(vi_dir, "p_b_m_21.target"),
            "viseme_FF": os.path.join(vi_dir, "f_v_18.target"),
            "viseme_SS": os.path.join(vi_dir, "s_z_15.target"),
        }
        units = self._mpfb_expression_paths()
        mpfb_map = {
            "eyeBlinkLeft": "eye-left-closure",
            "eyeBlinkRight": "eye-right-closure",
            "browDownLeft": "eyebrows-left-down",
            "browDownRight": "eyebrows-right-down",
            "browInnerUp": "eyebrows-left-inner-up",
            "jawOpen": "mouth-open",
            "mouthSmileLeft": "mouth-corner-puller",
            "mouthSmileRight": "mouth-corner-puller",
            "mouthFrownLeft": "mouth-depression",
            "mouthFrownRight": "mouth-depression",
            "noseSneerLeft": "nose-left-elevation",
            "noseSneerRight": "nose-right-elevation",
            "viseme_O": "mouth-pursing",
            "viseme_U": "mouth-protusion",
            "viseme_aa": "mouth-part-later",
        }
        want = shape_names or sorted(set(default_map) | set(mpfb_map))
        for nm in want:
            p = default_map.get(nm)
            if not (p and os.path.isfile(p)):
                src = units.get(mpfb_map.get(nm, ""))
                p = src
            if p and os.path.isfile(p):
                idxs, deltas = read_target(p)
                if len(idxs):
                    self.shape_deltas_mh[nm] = (idxs, deltas)
        return sorted(self.shape_deltas_mh.keys())

    def finalize_scale(self, target_height_m=1.82, sole_extra_m=0.0):
        """Convert morphed MH coords to Blender coords, ground-align, and scale to exact target_height_m.

        If sole_extra_m > 0 (e.g. boot sole thickness beneath bare foot), bare soles sit at z = sole_extra_m
        and crown reaches z = target_height_m so total character with boots hits exactly target_height_m.
        """
        raw_bl = mh_to_blender_coords(self.verts_mh)
        body_z = raw_bl[self.body_vert_indices, 2]
        zmin, zmax = float(body_z.min()), float(body_z.max())
        raw_h = zmax - zmin
        # Scale body so bare height = target_height_m - sole_extra_m, shifted so bare sole = sole_extra_m
        self.scale_k = (target_height_m - sole_extra_m) / raw_h
        self.z_shift = -zmin * self.scale_k + sole_extra_m
        self.verts_bl = raw_bl * self.scale_k
        self.verts_bl[:, 2] += self.z_shift
        return self.scale_k

    def mh_point_to_bl(self, pt_mh):
        p = mh_to_blender_coords(pt_mh) * self.scale_k
        p[..., 2] += self.z_shift
        return p

    def mh_delta_to_bl(self, d_mh):
        return mh_to_blender_coords(d_mh) * self.scale_k

    def joint_cube_center_bl(self, cube_name):
        idxs = self._expand_ranges(self.vgroups[cube_name])
        return Vector(self.verts_bl[idxs].mean(axis=0))

    def face_landmarks_bl(self):
        """Exact 3D facial landmarks derived from morphed MakeHuman joint cubes (Blender Z-up, -Y front)."""
        eye_l = self.joint_cube_center_bl("joint-l-eye")
        eye_r = self.joint_cube_center_bl("joint-r-eye")
        head_c = self.joint_cube_center_bl("joint-head")
        head_top = self.joint_cube_center_bl("joint-head-2")
        neck = self.joint_cube_center_bl("joint-neck")
        jaw = self.joint_cube_center_bl("joint-jaw")
        mouth_p = self.joint_cube_center_bl("joint-mouth")
        lid_l = self.joint_cube_center_bl("joint-l-upperlid")

        body_pts = self.verts_bl[self.body_vert_indices]
        crown_z = float(body_pts[:, 2].max())
        # Nose tip = frontmost vertex (min Y) in eye-to-mouth band
        nose_band = body_pts[(body_pts[:, 2] > jaw.z + 0.02) & (body_pts[:, 2] < eye_l.z + 0.01) & (np.abs(body_pts[:, 0]) < 0.025)]
        nose_tip = Vector(nose_band[int(np.argmin(nose_band[:, 1]))]) if len(nose_band) else Vector((0.0, lid_l.y - 0.02, eye_l.z - 0.032))
        eye_z = 0.5 * (eye_l.z + eye_r.z)
        face_h = crown_z - jaw.z  # full head height (~0.21-0.23m)
        return {
            "eye_l": eye_l,
            "eye_r": eye_r,
            "eye_z": eye_z,
            "brow_z": eye_z + face_h * 0.092,
            "nose_tip": nose_tip,
            "mouth_z": jaw.z + face_h * 0.165,
            "upper_lip_z": jaw.z + face_h * 0.215,
            "lower_lip_z": jaw.z + face_h * 0.130,
            "chin_pt": jaw,
            "chin_z": jaw.z,
            "head_center": head_c,
            "neck_z": neck.z,
            "crown_z": crown_z,
            "face_h": face_h,
            "eye_front_y": lid_l.y,
        }

    def build_body_mesh(self, obj_name, delete_face_pred=None):
        """Create the Blender body mesh object with clean UVs, vertex groups (humanoid weights) and shape keys.

        delete_face_pred(face_center_bl, face_verts_orig_idxs) -> bool allows culling fully occluded
        under-clothing body faces while preserving exact vertex-index mapping for weights & shape keys.
        """
        # Filter body faces if culling occluded polygons
        kept_faces = []
        used_orig = set()
        for vs, ts in self.body_faces:
            if delete_face_pred is not None:
                c = self.verts_bl[vs].mean(axis=0)
                if delete_face_pred(c, vs):
                    continue
            kept_faces.append((vs, ts))
            used_orig.update(vs)

        orig_list = sorted(used_orig)
        orig_to_local = {ov: i for i, ov in enumerate(orig_list)}
        local_verts = [tuple(self.verts_bl[ov]) for ov in orig_list]
        local_faces = [[orig_to_local[ov] for ov in vs] for vs, _ in kept_faces]

        me = bpy.data.meshes.new(obj_name)
        me.from_pydata(local_verts, [], local_faces)
        me.update()

        # Assign UVs from base.obj
        uv_layer = me.uv_layers.new(name="UVMap")
        uv_data = uv_layer.data
        for poly, (_, ts) in zip(me.polygons, kept_faces):
            for li, ti in zip(poly.loop_indices, ts):
                if 0 <= ti < len(self.base_uvs):
                    uv_data[li].uv = (float(self.base_uvs[ti][0]), float(self.base_uvs[ti][1]))

        for p in me.polygons:
            p.use_smooth = True

        ob = bpy.data.objects.new(obj_name, me)
        bpy.context.scene.collection.objects.link(ob)

        # Assign artist-painted CC0 weights mapped to SkeletonProfileHumanoid bone names
        self._apply_base_weights(ob, orig_to_local)

        # Add facial blendshapes (Basis + ARKit/viseme keys, ALL initialized to value=0.0!)
        if self.shape_deltas_mh:
            ob.shape_key_add(name="Basis", from_mix=False)
            for sname, (idxs, deltas_mh) in self.shape_deltas_mh.items():
                sk = ob.shape_key_add(name=sname, from_mix=False)
                sk.value = 0.0
                d_bl = self.mh_delta_to_bl(deltas_mh)
                for oi, dv in zip(idxs, d_bl):
                    li = orig_to_local.get(int(oi))
                    if li is not None:
                        sk.data[li].co = Vector(local_verts[li]) + Vector(dv)

        return ob, orig_to_local

    def _apply_base_weights(self, ob, orig_to_local):
        for mh_name, hum_name in MH_TO_HUMANOID.items():
            entries = self.mh_weights.get(mh_name)
            if not entries:
                continue
            vg = ob.vertex_groups.get(hum_name) or ob.vertex_groups.new(name=hum_name)
            for vi, w in entries:
                li = orig_to_local.get(int(vi))
                if li is not None and w > 1e-5:
                    vg.add([li], float(w), "ADD")
        self._clean_normalize_weights(ob)

    @staticmethod
    def _clean_normalize_weights(ob, max_inf=4):
        """Enforce <= max_inf bone influences and exact normalization (sum = 1.0) on every vertex."""
        vgs = ob.vertex_groups
        for v in ob.data.vertices:
            pairs = [(g.group, g.weight) for g in v.groups if g.weight > 1e-5]
            if not pairs:
                continue
            pairs.sort(key=lambda x: x[1], reverse=True)
            kept = pairs[:max_inf]
            dropped = pairs[max_inf:]
            for gi, _ in dropped:
                vgs[gi].remove([v.index])
            tot = sum(w for _, w in kept)
            if tot > 1e-8:
                for gi, w in kept:
                    vgs[gi].add([v.index], w / tot, "REPLACE")

    def load_mhclo(self, mhclo_path, obj_name, inherit_shapes=True, offset_normal_m=0.0):
        """Load a CC0 MakeHuman .mhclo asset (eyes, teeth, tongue, eyebrows, eyelashes, clothes).

        Returns (Blender mesh object, delete_verts_set_on_basemesh).
        Propagates morphed positions, facial blendshapes, and artist-painted bone weights
        via exact barycentric binding!
        """
        folder = os.path.dirname(mhclo_path)
        obj_file = None
        scales = {}
        bindings = []
        delete_verts = set()
        in_verts = False
        in_delete = False
        with open(mhclo_path, "r", encoding="utf-8", errors="ignore") as f:
            for raw in f:
                s = raw.strip()
                if not s or s.startswith("#"):
                    continue
                if s.startswith("obj_file "):
                    obj_file = s.split(None, 1)[1].strip()
                elif s.startswith(("x_scale ", "y_scale ", "z_scale ")):
                    parts = s.split()
                    scales[parts[0][0]] = (int(parts[1]), int(parts[2]), float(parts[3]))
                elif s.startswith("verts "):
                    in_verts, in_delete = True, False
                elif s.startswith("delete_verts"):
                    in_verts, in_delete = False, True
                elif in_delete:
                    for tok in s.split():
                        if "-" in tok:
                            a, b = tok.split("-", 1)
                            delete_verts.update(range(int(a), int(b) + 1))
                        elif tok.isdigit():
                            delete_verts.add(int(tok))
                elif in_verts:
                    p = s.split()
                    if len(p) == 1 and p[0].isdigit():
                        bindings.append((int(p[0]),))
                    elif len(p) >= 9:
                        bindings.append((
                            int(p[0]), int(p[1]), int(p[2]),
                            float(p[3]), float(p[4]), float(p[5]),
                            float(p[6]), float(p[7]), float(p[8]),
                        ))

        obj_path = os.path.join(folder, obj_file)
        orig_v, uvs, faces, _ = parse_obj(obj_path)
        V = self.verts_mh

        def axis_scale(axis_ch, axis_i):
            if axis_ch not in scales:
                return 1.0
            i0, i1, denom = scales[axis_ch]
            if abs(denom) < 1e-9:
                return 1.0
            return abs(V[i1, axis_i] - V[i0, axis_i]) / denom

        sx, sy, sz = axis_scale("x", 0), axis_scale("y", 1), axis_scale("z", 2)
        n_v = len(orig_v)
        out_mh = np.zeros((n_v, 3), dtype=np.float64)
        for i in range(n_v):
            if i < len(bindings):
                b = bindings[i]
                if len(b) == 1:
                    out_mh[i] = V[b[0]]
                else:
                    v0, v1, v2, w0, w1, w2, ox, oy, oz = b
                    out_mh[i] = (w0 * V[v0] + w1 * V[v1] + w2 * V[v2]
                                 + np.array([ox * sx, oy * sy, oz * sz]))
            else:
                out_mh[i] = orig_v[i]

        out_bl = self.mh_point_to_bl(out_mh)
        local_faces = [vs for vs, _ in faces]
        me = bpy.data.meshes.new(obj_name)
        me.from_pydata([tuple(p) for p in out_bl], [], local_faces)
        me.update()

        if abs(offset_normal_m) > 1e-6:
            for v in me.vertices:
                v.co += v.normal * offset_normal_m
            me.update()

        uv_layer = me.uv_layers.new(name="UVMap")
        for poly, (_, ts) in zip(me.polygons, faces):
            for li, ti in zip(poly.loop_indices, ts):
                if 0 <= ti < len(uvs):
                    uv_layer.data[li].uv = (float(uvs[ti][0]), float(uvs[ti][1]))
        for p in me.polygons:
            p.use_smooth = True

        ob = bpy.data.objects.new(obj_name, me)
        bpy.context.scene.collection.objects.link(ob)

        # Transfer exact barycentric bone weights from base mesh
        # Build quick map: base_v -> [(hum_bone, weight), ...]
        base_w = {}
        for mh_b, hum_b in MH_TO_HUMANOID.items():
            for vi, w in self.mh_weights.get(mh_b, []):
                if w > 1e-5:
                    base_w.setdefault(int(vi), []).append((hum_b, float(w)))

        bone_vgs = {}
        for i in range(min(n_v, len(bindings))):
            b = bindings[i]
            acc = {}
            if len(b) == 1:
                for hb, w in base_w.get(b[0], []):
                    acc[hb] = acc.get(hb, 0.0) + w
            else:
                for vi, bw in ((b[0], b[3]), (b[1], b[4]), (b[2], b[5])):
                    for hb, w in base_w.get(vi, []):
                        acc[hb] = acc.get(hb, 0.0) + w * bw
            if not acc:
                acc["Head"] = 1.0
            for hb, w in acc.items():
                if w > 1e-5:
                    vg = bone_vgs.get(hb)
                    if vg is None:
                        vg = ob.vertex_groups.new(name=hb)
                        bone_vgs[hb] = vg
                    vg.add([i], w, "REPLACE")
        self._clean_normalize_weights(ob)

        # Propagate facial blendshapes via exact barycentric delta (all initialized to value=0.0!)
        if inherit_shapes and self.shape_deltas_mh:
            ob.shape_key_add(name="Basis", from_mix=False)
            for sname, (idxs, deltas_mh) in self.shape_deltas_mh.items():
                dmap = {int(oi): self.mh_delta_to_bl(dv) for oi, dv in zip(idxs, deltas_mh)}
                sk = ob.shape_key_add(name=sname, from_mix=False)
                sk.value = 0.0
                for i in range(min(n_v, len(bindings))):
                    b = bindings[i]
                    dv = np.zeros(3, dtype=np.float64)
                    if len(b) == 1:
                        if b[0] in dmap:
                            dv = dmap[b[0]]
                    else:
                        for vi, bw in ((b[0], b[3]), (b[1], b[4]), (b[2], b[5])):
                            if vi in dmap:
                                dv += dmap[vi] * bw
                    if np.linalg.norm(dv) > 1e-7:
                        sk.data[i].co = Vector(me.vertices[i].co) + Vector(dv)

        return ob, delete_verts

    def build_armature(self, root_obj):
        """Build the 53-bone SkeletonProfileHumanoid armature directly from morphed MakeHuman joints."""
        data = bpy.data.armatures.new("Armature")
        arm = bpy.data.objects.new("Armature", data)
        bpy.context.scene.collection.objects.link(arm)
        arm.parent = root_obj
        data.display_type = "STICK"

        def eval_joint(spec):
            if spec.get("strategy") == "CUBE":
                return self.joint_cube_center_bl(spec["cube_name"])
            if spec.get("strategy") == "MEAN":
                idxs = spec["vertex_indices"]
                return Vector(self.verts_bl[idxs].mean(axis=0))
            return Vector(spec["default_position"])

        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="EDIT")

        eb_map = {}
        for mh_name, hum_name in MH_TO_HUMANOID.items():
            bdef = self.mh_rig_def[mh_name]
            eb = data.edit_bones.new(hum_name)
            if hum_name == "Root":
                eb.head = Vector((0.0, 0.0, 0.0))
                eb.tail = Vector((0.0, 0.0, 0.20))
            else:
                h = eval_joint(bdef["head"])
                t = eval_joint(bdef["tail"])
                if (t - h).length < 1e-4:
                    t = h + Vector((0.0, 0.0, 0.02))
                eb.head = h
                eb.tail = t
            eb_map[hum_name] = eb

        # Parent hierarchy matching SkeletonProfileHumanoid
        for mh_name, hum_name in MH_TO_HUMANOID.items():
            bdef = self.mh_rig_def[mh_name]
            mp = bdef.get("parent") or ""
            if mp and mp in MH_TO_HUMANOID:
                eb = eb_map[hum_name]
                par = eb_map[MH_TO_HUMANOID[mp]]
                eb.parent = par
                eb.use_connect = (par.tail - eb.head).length < 1e-4

        # Clean bone rolls aligned with TD-004 (-Y front, +Z up)
        for hum_name, eb in eb_map.items():
            if "Thumb" in hum_name or hum_name.endswith(("Foot", "Toes")):
                eb.align_roll(Vector((0.0, 0.0, 1.0)))
            else:
                eb.align_roll(Vector((0.0, -1.0, 0.0)))

        # MakeHuman Foot/Toes check: ensure Foot points forward (-Y) toward ball and Toes points forward (-Y)
        for side in ("Left", "Right"):
            foot = eb_map[side + "Foot"]
            toes = eb_map[side + "Toes"]
            if (foot.tail - foot.head).y > -0.02:
                foot.tail = Vector((foot.head.x, foot.head.y - 0.12, max(0.025, foot.head.z * 0.45)))
            toes.head = foot.tail.copy()
            toes.tail = toes.head + Vector((0.0, -0.075, 0.0))
            toes.use_connect = True

        bpy.ops.object.mode_set(mode="OBJECT")
        return arm


def convert_apose_to_tpose(arm, skinned_meshes):
    """Smoothly rotate MakeHuman's A-pose arms (~40° down) up into a crisp T-pose rest pose.

    Applies the Armature modifier into each mesh's Basis AND shape keys, then applies Pose as Rest Pose
    on the armature and re-attaches Armature modifiers cleanly!
    """
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")

    for side, sx in (("Left", 1.0), ("Right", -1.0)):
        uarm = arm.pose.bones[side + "UpperArm"]
        larm = arm.pose.bones[side + "LowerArm"]
        hand = arm.pose.bones[side + "Hand"]

        # Align UpperArm to horizontal (+/-X, 0, 0)
        for pb, target_dir in [
            (uarm, Vector((sx, 0.0, 0.0))),
            (larm, Vector((sx, 0.0, 0.0))),
            (hand, Vector((sx, 0.0, 0.0))),
        ]:
            bpy.context.view_layer.update()
            cur_dir = (pb.tail - pb.head).normalized()
            rot_q = cur_dir.rotation_difference(target_dir)
            # Express world delta rotation in bone's local pose space
            m3 = pb.matrix.to_3x3()
            local_q = (m3.inverted() @ rot_q.to_matrix() @ m3).to_quaternion()
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = pb.rotation_quaternion @ local_q
            bpy.context.view_layer.update()

        # Straighten fingers slightly along +/-X (except thumb angled slightly forward -Y)
        for fname in ("Index", "Middle", "Ring", "Little"):
            for seg in ("Proximal", "Intermediate", "Distal"):
                pb = arm.pose.bones.get(f"{side}{fname}{seg}")
                if not pb:
                    continue
                bpy.context.view_layer.update()
                cur_dir = (pb.tail - pb.head).normalized()
                tgt = Vector((sx, 0.0, 0.0))
                rot_q = cur_dir.rotation_difference(tgt)
                # Blend 85% toward straight horizontal so natural slight finger splay remains
                rot_q = Quaternion().slerp(rot_q, 0.85)
                m3 = pb.matrix.to_3x3()
                local_q = (m3.inverted() @ rot_q.to_matrix() @ m3).to_quaternion()
                pb.rotation_mode = "QUATERNION"
                pb.rotation_quaternion = pb.rotation_quaternion @ local_q

    bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="OBJECT")

    # Bake posed vertex positions into each mesh (preserving shape keys!)
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in skinned_meshes:
        # Ensure mesh has an Armature modifier referencing arm
        has_mod = any(m.type == "ARMATURE" and m.object == arm for m in ob.modifiers)
        if not has_mod:
            ob.modifiers.new("Armature", "ARMATURE").object = arm

        # Save shape key deltas relative to Basis before deforming
        sk_deltas = []
        if ob.data.shape_keys and len(ob.data.shape_keys.key_blocks) > 1:
            basis = ob.data.shape_keys.key_blocks[0]
            # Disable all shape keys when evaluating rest->T-pose Basis
            for kb in ob.data.shape_keys.key_blocks[1:]:
                kb.value = 0.0
                # Facial shape keys are on the head (unaffected by arm T-pose rotation), so world delta is exact
                deltas = [kb.data[i].co - basis.data[i].co for i in range(len(basis.data))]
                sk_deltas.append((kb.name, deltas))

        dg.update()
        ev = ob.evaluated_get(dg)
        ev_me = ev.to_mesh()
        new_cos = [v.co.copy() for v in ev_me.vertices]
        ev.to_mesh_clear()

        if ob.data.shape_keys:
            basis = ob.data.shape_keys.key_blocks[0]
            for i, co in enumerate(new_cos):
                basis.data[i].co = co
                ob.data.vertices[i].co = co
            for kb_name, deltas in sk_deltas:
                kb = ob.data.shape_keys.key_blocks[kb_name]
                for i, (co, dv) in enumerate(zip(new_cos, deltas)):
                    kb.data[i].co = co + dv
        else:
            for i, co in enumerate(new_cos):
                ob.data.vertices[i].co = co
        ob.data.update()

    # Apply pose as rest pose on Armature
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode="OBJECT")

    # Re-align bone rolls cleanly after T-pose bake
    bpy.ops.object.mode_set(mode="EDIT")
    for eb in arm.data.edit_bones:
        if "Thumb" in eb.name or eb.name.endswith(("Foot", "Toes")):
            eb.align_roll(Vector((0.0, 0.0, 1.0)))
        else:
            eb.align_roll(Vector((0.0, -1.0, 0.0)))
    bpy.ops.object.mode_set(mode="OBJECT")
