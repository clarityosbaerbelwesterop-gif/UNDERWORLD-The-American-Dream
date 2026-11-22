"""Tailored, body-fitted realistic clothing generator with bone-region weight isolation & Cycles high-to-low bake.

Builds clean, single-sided outer garment shells with crisp turned-in cuff/collar/lapel rims
(avoiding doubled interior polygons so poly counts stay well under budget and Cycles bakes never
self-occlude!), enforces BVHTree non-clipping clearance, and isolates bone weight transfer per
garment region (so jeans/pockets NEVER pick up hand/finger weights in A-pose!).
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

# Anatomical bone-group whitelists per garment type (eliminates cross-limb weight bleeding in A-pose!)
GARMENT_ALLOWED_BONES = {
    "TShirt": {
        "Hips", "Spine", "Chest", "UpperChest", "Neck",
        "LeftShoulder", "LeftUpperArm", "RightShoulder", "RightUpperArm",
    },
    "Jacket": {
        "Hips", "Spine", "Chest", "UpperChest", "Neck",
        "LeftShoulder", "LeftUpperArm", "LeftLowerArm",
        "RightShoulder", "RightUpperArm", "RightLowerArm",
    },
    "Jeans": {
        "Hips", "Spine",
        "LeftUpperLeg", "LeftLowerLeg", "LeftFoot",
        "RightUpperLeg", "RightLowerLeg", "RightFoot",
    },
    "Boots": {
        "LeftLowerLeg", "LeftFoot", "LeftToes",
        "RightLowerLeg", "RightFoot", "RightToes",
    },
}


def _arm_landmarks(arm, body_ob):
    b = arm.data.bones
    pts = np.array([v.co[:] for v in body_ob.data.vertices], dtype=np.float64)
    return {
        "hips_z": float(b["Hips"].head_local.z),
        "spine_z": float(b["Spine"].head_local.z),
        "chest_z": float(b["Chest"].head_local.z),
        "uchest_z": float(b["UpperChest"].head_local.z),
        "neck_z": float(b["Neck"].head_local.z),
        "head_z": float(b["Head"].head_local.z),
        "sh_l": Vector(b["LeftUpperArm"].head_local),
        "sh_r": Vector(b["RightUpperArm"].head_local),
        "elb_l": Vector(b["LeftLowerArm"].head_local),
        "elb_r": Vector(b["RightLowerArm"].head_local),
        "wri_l": Vector(b["LeftHand"].head_local),
        "wri_r": Vector(b["RightHand"].head_local),
        "hip_l": Vector(b["LeftUpperLeg"].head_local),
        "hip_r": Vector(b["RightUpperLeg"].head_local),
        "knee_l": Vector(b["LeftLowerLeg"].head_local),
        "knee_r": Vector(b["RightLowerLeg"].head_local),
        "ank_l": Vector(b["LeftFoot"].head_local),
        "ank_r": Vector(b["RightFoot"].head_local),
        "toe_l": Vector(b["LeftToes"].tail_local),
        "toe_r": Vector(b["RightToes"].tail_local),
        "body_pts": pts,
    }


def _arm_param(p, sh, elb, wri):
    ab = elb - sh
    l0 = ab.length
    t0 = max(0.0, min(1.0, (p - sh).dot(ab) / max(l0 * l0, 1e-8)))
    q0 = sh + ab * t0
    d0 = (p - q0).length

    bc = wri - elb
    l1 = bc.length
    t1 = max(0.0, min(1.0, (p - elb).dot(bc) / max(l1 * l1, 1e-8)))
    q1 = elb + bc * t1
    d1 = (p - q1).length

    if d0 <= d1:
        return t0, d0, q0
    return 1.0 + t1, d1, q1


def _extract_submesh(body_ob, face_pred, name):
    me_src = body_ob.data
    bm = bmesh.new()
    vmap = {}
    for p in me_src.polygons:
        vcos = [me_src.vertices[vi].co for vi in p.vertices]
        if face_pred(p.center, vcos):
            fvs = []
            for vi in p.vertices:
                if vi not in vmap:
                    vmap[vi] = bm.verts.new(me_src.vertices[vi].co)
                fvs.append(vmap[vi])
            try:
                f = bm.faces.new(fvs)
                f.smooth = True
            except ValueError:
                pass
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    # Keep only connected islands >= 12 faces
    visited = set()
    for f in bm.faces:
        if f.index in visited:
            continue
        stack, comp = [f], []
        while stack:
            cur = stack.pop()
            if cur.index in visited:
                continue
            visited.add(cur.index)
            comp.append(cur)
            for e in cur.edges:
                for nf in e.link_faces:
                    if nf.index not in visited:
                        stack.append(nf)
        if len(comp) < 12:
            for cf in comp:
                bm.faces.remove(cf)
    # Remove boundary ear/spike faces & any bow-tie non-manifold verts/loose edges cleanly!
    for _ in range(3):
        bm.faces.ensure_lookup_table()
        spikes = [f for f in bm.faces if sum(1 for e in f.edges if e.is_boundary) >= 3]
        if spikes:
            for f in spikes:
                bm.faces.remove(f)
        loose_e = [e for e in bm.edges if not e.link_faces]
        if loose_e:
            bmesh.ops.delete(bm, geom=loose_e, context="EDGES")
        loose_v = [v for v in bm.verts if not v.link_faces]
        if loose_v:
            bmesh.ops.delete(bm, geom=loose_v, context="VERTS")
        # Remove any face attached to a bow-tie non-manifold vertex
        nm_v = [v for v in bm.verts if v.link_edges and not v.is_manifold and not v.is_boundary]
        if nm_v:
            nm_faces = list({f for v in nm_v for f in v.link_faces if sum(1 for e in f.edges if e.is_boundary) >= 1})
            if nm_faces:
                for f in nm_faces[:len(nm_v)]:
                    if f.is_valid:
                        bm.faces.remove(f)
                continue
        if not spikes:
            break
    loose_e = [e for e in bm.edges if not e.link_faces]
    if loose_e:
        bmesh.ops.delete(bm, geom=loose_e, context="EDGES")
    loose_v = [v for v in bm.verts if not v.link_faces]
    if loose_v:
        bmesh.ops.delete(bm, geom=loose_v, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _laplacian_smooth(ob, iterations=4, factor=0.42, smooth_boundary=True):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    for _ in range(iterations):
        new_pos = {}
        for v in bm.verts:
            if v.is_boundary:
                if not smooth_boundary:
                    continue
                nbs = [e.other_vert(v).co for e in v.link_edges if e.other_vert(v).is_boundary]
                if len(nbs) == 2:
                    new_pos[v.index] = v.co.lerp(0.5 * (nbs[0] + nbs[1]), 0.55)
            else:
                nbs = [e.other_vert(v).co for e in v.link_edges]
                if nbs:
                    avg = sum(nbs, Vector()) / len(nbs)
                    new_pos[v.index] = v.co.lerp(avg, factor)
        for idx, co in new_pos.items():
            bm.verts[idx].co = co
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def _add_turned_rim(ob, depth=0.0045, inset=0.0035):
    """Turn all open boundary edges neatly inward by `depth` to give solid garment thickness WITHOUT doubling interior faces!"""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    b_edges = [e for e in bm.edges if e.is_boundary]
    if not b_edges:
        bm.free()
        return
    # Extrude boundary edges once, then tuck the new ring inward along vertex normals
    ret = bmesh.ops.extrude_edge_only(bm, edges=b_edges)
    new_verts = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
    # Record normals from linked old edges before moving
    for v in new_verts:
        # Move inward opposite to vertex normal
        v.co -= v.normal * depth
        # Also pull gently toward neighbor interior centroid to round the hem/cuff lip
        in_nbs = [e.other_vert(v).co for e in v.link_edges if e.other_vert(v) not in new_verts]
        if in_nbs:
            v.co = v.co.lerp(in_nbs[0], 0.15)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.dissolve_degenerate(bm, dist=2e-4, edges=bm.edges)
    # Remove any remaining zero-area faces & convert any >4-gon created by dissolve_degenerate into tris
    zero_f = [f for f in bm.faces if f.calc_area() < 1e-8]
    if zero_f:
        bmesh.ops.delete(bm, geom=zero_f, context="FACES")
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def _enforce_clearance(outer_ob, inner_obs, min_clearance=0.003, passes=2):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    bvhs = [BVHTree.FromObject(iob, dg) for iob in inner_obs if iob is not None]
    if not bvhs:
        return 0
    pushed_total = 0
    for _ in range(passes):
        bm = bmesh.new()
        bm.from_mesh(outer_ob.data)
        bm.normal_update()
        pushed = 0
        for v in bm.verts:
            p = v.co
            for bvh in bvhs:
                loc, nrm, _, dist = bvh.find_nearest(p)
                if loc is None:
                    continue
                signed = (p - loc).dot(nrm)
                if dist < 0.032 and signed < min_clearance:
                    push_dir = nrm if nrm.length > 1e-6 else v.normal
                    v.co = loc + push_dir.normalized() * (min_clearance + 0.0006)
                    pushed += 1
                    break
        if pushed:
            bm.to_mesh(outer_ob.data)
            outer_ob.data.update()
            pushed_total += pushed
        bm.free()
        if not pushed:
            break
    return pushed_total


def _tuck_inner_behind_outer(inner_ob, outer_ob, margin=0.0035, max_probe=0.015):
    """Gently tuck any interior vertex of inner_ob that protrudes outside outer_ob back inside by `margin`."""
    if inner_ob is None or outer_ob is None:
        return 0
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    bm_o = bmesh.new()
    bm_o.from_mesh(outer_ob.data)
    b_verts = {v.index for v in bm_o.verts if v.is_boundary}
    b_verts2 = set(b_verts)
    for _ in range(2):
        nxt = set(b_verts2)
        for v in bm_o.verts:
            if v.index in b_verts2:
                for e in v.link_edges:
                    nxt.add(e.other_vert(v).index)
        b_verts2 = nxt
    border_faces = {f.index for f in bm_o.faces if any(v.index in b_verts2 for v in f.verts)}
    bm_o.free()

    bvh = BVHTree.FromObject(outer_ob, dg)
    bm_i = bmesh.new()
    bm_i.from_mesh(inner_ob.data)
    tucked = 0
    for v in bm_i.verts:
        loc, nrm, fidx, dist = bvh.find_nearest(v.co)
        if loc is None or dist > max_probe or fidx in border_faces:
            continue
        if (v.co - loc).dot(nrm) > 0.0005:
            v.co = loc - nrm.normalized() * margin
            tucked += 1
    if tucked:
        bm_i.to_mesh(inner_ob.data)
        inner_ob.data.update()
    bm_i.free()
    return tucked


def _clean_uv_unwrap(ob, angle_limit_deg=60.0, island_margin=0.015):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    if not ob.data.uv_layers:
        ob.data.uv_layers.new(name="UVMap")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(
        angle_limit=math.radians(angle_limit_deg),
        island_margin=island_margin,
        correct_aspect=True,
        scale_to_bounds=True,
    )
    bpy.ops.object.mode_set(mode="OBJECT")


def _add_box_detail(bm, center, size, rot_euler=(0, 0, 0), bevel=0.001):
    m = Matrix.Translation(center) @ Euler(rot_euler).to_matrix().to_4x4() @ Matrix.Diagonal((size[0], size[1], size[2], 1.0))
    ret = bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    verts = ret["verts"]
    edges = list({e for v in verts for e in v.link_edges})
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=1, affect="EDGES", clamp_overlap=True)
    for v in bm.verts:
        for f in v.link_faces:
            f.smooth = True


# ==============================================================================
# GARMENT 1: Crew-Neck T-Shirt (clean circular neckline, natural cotton drape)
# ==============================================================================
def build_tshirt(body_ob, arm, obj_name, style="crew_tshirt"):
    lm = _arm_landmarks(arm, body_ob)
    hips_z = lm["hips_z"]
    neck_z = lm["neck_z"]
    sh_l, elb_l, wri_l = lm["sh_l"], lm["elb_l"], lm["wri_l"]
    sh_r, elb_r, wri_r = lm["sh_r"], lm["elb_r"], lm["wri_r"]
    arm_cut_t = (0.08 if style == "under_jacket_tshirt"
                 else (0.52 if style == "crew_tshirt"
                       else (1.72 if style == "long_sleeve" else 0.42)))

    def pred(c, vcos):
        if c.z < hips_z - 0.032 or c.z > neck_z + 0.012:
            return False
        # Crisp smooth crew-neck circular opening (slightly lower in front)
        r_neck = math.hypot(c.x * 1.0, (c.y + 0.015) * 0.95)
        neck_cut_z = neck_z - 0.005 - (0.042 if c.y < 0.0 else 0.005) * max(0.0, 1.0 - r_neck / 0.11)
        if c.z > neck_cut_z and r_neck < 0.098:
            return False
        if c.x > sh_l.x + 0.018:
            t, _, _ = _arm_param(c, sh_l, elb_l, wri_l)
            if t > arm_cut_t:
                return False
        elif c.x < sh_r.x - 0.018:
            t, _, _ = _arm_param(c, sh_r, elb_r, wri_r)
            if t > arm_cut_t:
                return False
        return True

    ob = _extract_submesh(body_ob, pred, obj_name)

    # Smooth crisp crew-neck neckline & horizontal bottom hem!
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    for v in bm.verts:
        co = v.co
        off = 0.0048
        if abs(co.x) < 0.14 and hips_z - 0.02 < co.z < lm["uchest_z"] + 0.02:
            if co.y < 0.0:
                fold = 0.0008 * math.sin(co.z * 22.0 + co.x * 8.0) * math.exp(-((co.z - lm["spine_z"]) / 0.14) ** 2)
                co.y -= 0.005 + max(0.0, 0.006 * (1.0 - abs(co.x) / 0.11)) + fold
            else:
                co.y += 0.004 * max(0.0, 1.0 - abs(co.x) / 0.09)
        v.co += v.normal * off
    # Snap bottom hem boundary cleanly to a smooth straight hem line (zero jagged teeth!)
    for v in bm.verts:
        if v.is_boundary and v.co.z < hips_z + 0.03 and abs(v.co.x) < 0.24:
            v.co.z = hips_z - 0.030
    bm.to_mesh(ob.data)
    bm.free()

    _laplacian_smooth(ob, iterations=5, factor=0.45, smooth_boundary=True)
    _enforce_clearance(ob, [body_ob], min_clearance=0.004, passes=2)
    _add_turned_rim(ob, depth=0.0032)
    _clean_uv_unwrap(ob, angle_limit_deg=60.0, island_margin=0.015)
    return ob


# ==============================================================================
# GARMENT 2: Worn Dark-Brown Leather Bomber Jacket (single-sided + crisp turned rim!)
# ==============================================================================
def build_bomber_jacket(body_ob, tshirt_ob, arm, obj_name, style="bomber_jacket"):
    lm = _arm_landmarks(arm, body_ob)
    hips_z = lm["hips_z"]
    neck_z = lm["neck_z"]
    uchest_z = lm["uchest_z"]
    sh_l, elb_l, wri_l = lm["sh_l"], lm["elb_l"], lm["wri_l"]
    sh_r, elb_r, wri_r = lm["sh_r"], lm["elb_r"], lm["wri_r"]
    hem_z = hips_z - (0.042 if style == "bomber_jacket" else 0.115)
    open_front_half = 0.072 if style == "bomber_jacket" else 0.048

    def pred(c, vcos):
        if c.z < hem_z or c.z > neck_z + 0.024:
            return False
        # Clean straight vertical open front showing grey crew-neck t-shirt!
        if c.y < -0.015 and abs(c.x) < open_front_half:
            return False
        # Exclude neck above collar
        if c.z > neck_z + 0.014 and abs(c.x) < 0.095:
            return False
        # Trim sleeves cleanly right above wrist watch on left wrist!
        if c.x > sh_l.x + 0.015:
            t, _, _ = _arm_param(c, sh_l, elb_l, wri_l)
            if t > 1.80:
                return False
        elif c.x < sh_r.x - 0.015:
            t, _, _ = _arm_param(c, sh_r, elb_r, wri_r)
            if t > 1.84:
                return False
        return True

    ob = _extract_submesh(body_ob, pred, obj_name)

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()

    for v in bm.verts:
        co = v.co
        n = v.normal
        in_arm_l = co.x > sh_l.x + 0.025
        in_arm_r = co.x < sh_r.x - 0.025

        if in_arm_l or in_arm_r:
            sh, elb, wri = (sh_l, elb_l, wri_l) if in_arm_l else (sh_r, elb_r, wri_r)
            t, _, qpt = _arm_param(co, sh, elb, wri)
            radial = co - qpt
            rdir = radial.normalized() if radial.length > 1e-6 else n
            if t > 1.60:
                # Snug ribbed bomber wrist cuff (slightly wider & clearly structured!)
                cuff_off = 0.011 + 0.0012 * math.cos(math.atan2(rdir.z, rdir.y) * 18.0)
                v.co += rdir * cuff_off
            else:
                # Bold relaxed leather bomber sleeve with genuine leather creases & blouson above cuff
                elbow_crease = 0.0048 * math.sin(t * 26.0) * math.exp(-((t - 1.0) / 0.42) ** 2)
                cuff_stack = 0.0055 * math.sin((t - 1.42) * 38.0) * math.exp(-((t - 1.50) / 0.16) ** 2)
                sh_pad = 0.012 * max(0.0, 1.0 - t / 0.36) * max(0.0, rdir.z)
                v.co += rdir * (0.022 + sh_pad + elbow_crease + cuff_stack)
        else:
            if co.z < hem_z + 0.058:
                # Ribbed bomber bottom waistband hem (snugger than blouson body above it!)
                hem_t = (co.z - hem_z) / 0.058
                rib = 0.0012 * math.cos(co.x * 115.0)
                v.co += n * (0.015 + 0.006 * hem_t + rib)
                # Bridge lower-back sacral dimple completely flat!
                if co.y > 0.02 and abs(co.x) < 0.095:
                    v.co.y += 0.016 * (1.0 - abs(co.x) / 0.095)
            elif co.z > neck_z - 0.018 and abs(co.x) < 0.118:
                # Standing ribbed bomber collar curving cleanly around neck
                col_t = max(0.0, min(1.0, (co.z - (neck_z - 0.018)) / 0.042))
                v.co += n * (0.014 + 0.004 * col_t) + Vector((0.0, 0.0, 0.012 * col_t))
            else:
                # Structured distressed leather bomber torso (masculine broad shoulders + relaxed blouson)
                back_yoke = 0.0024 * math.exp(-((co.z - (uchest_z + 0.018)) / 0.007) ** 2) if co.y > 0.03 else 0.0
                blouson = 0.0095 * math.sin(math.pi * max(0.0, min(1.0, (co.z - hem_z) / (neck_z - hem_z))))
                sh_boost = 0.010 * max(0.0, (abs(co.x) - 0.12) / 0.08) * max(0.0, (co.z - uchest_z) / 0.12)
                drape = 0.0025 * math.sin(co.z * 30.0 + co.x * 9.0)
                v.co += n * (0.019 + blouson + sh_boost + back_yoke + drape)
                if co.y > 0.02:
                    # Bridge back spine & lower lumbar hollow cleanly!
                    v.co.y += 0.014 * max(0.0, 1.0 - abs(co.x) / 0.11)
                elif co.y < -0.02:
                    v.co.y -= 0.0045

    # Straighten front open zipper edges, smooth top collar rim, & smooth bottom hem cleanly
    for v in bm.verts:
        if v.is_boundary and v.co.y < -0.04 and hem_z + 0.01 < v.co.z < neck_z - 0.015:
            if abs(abs(v.co.x) - open_front_half) < 0.035:
                v.co.x = math.copysign(open_front_half, v.co.x)
        if v.is_boundary and v.co.z < hem_z + 0.030 and abs(v.co.x) < 0.28:
            v.co.z = hem_z
        if v.is_boundary and v.co.z > neck_z - 0.010 and abs(v.co.x) < 0.115:
            v.co.z = neck_z + 0.016

    bm.to_mesh(ob.data)
    bm.free()

    _laplacian_smooth(ob, iterations=4, factor=0.38, smooth_boundary=True)
    _enforce_clearance(ob, [tshirt_ob, body_ob], min_clearance=0.0055, passes=3)
    # Crisp 4.5 mm turned-in lapel/collar/cuff/hem rim — solid look with ONLY ~450 extra tris (NOT 5,000!)
    _add_turned_rim(ob, depth=0.0045)
    _clean_uv_unwrap(ob, angle_limit_deg=58.0, island_margin=0.014)
    return ob


# ==============================================================================
# GARMENT 3: Dark Indigo Relaxed-Straight Jeans (clean tailored silhouette, zero floating boxes!)
# ==============================================================================
def build_jeans(body_ob, arm, obj_name, style="straight_jeans"):
    lm = _arm_landmarks(arm, body_ob)
    hips_z = lm["hips_z"]
    knee_z = 0.5 * (lm["knee_l"].z + lm["knee_r"].z)
    ank_z = 0.5 * (lm["ank_l"].z + lm["ank_r"].z)
    waist_z = hips_z + 0.036
    cuff_z = ank_z + 0.002  # sits cleanly right over top of boot collar without shoelace poke-through!

    def pred(c, vcos):
        # Strictly exclude A-pose hands/fingers hanging at |x| > 0.28!
        return cuff_z <= c.z <= waist_z and abs(c.x) < 0.28

    ob = _extract_submesh(body_ob, pred, obj_name)

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()

    hip_lx, hip_rx = lm["hip_l"].x, lm["hip_r"].x
    ank_lx, ank_rx = lm["ank_l"].x, lm["ank_r"].x
    knee_lx, knee_rx = lm["knee_l"].x, lm["knee_r"].x
    crotch_z = hips_z - 0.115

    for v in bm.verts:
        co = v.co
        n = v.normal
        if co.z < crotch_z:
            is_l = co.x >= 0.0
            t_leg = max(0.0, min(1.0, (crotch_z - co.z) / max(crotch_z - cuff_z, 1e-4)))
            if co.z >= knee_z:
                u = (crotch_z - co.z) / max(crotch_z - knee_z, 1e-4)
                cx = (hip_lx if is_l else hip_rx) * (1.0 - u) + (knee_lx if is_l else knee_rx) * u
                cy = lm["hip_l"].y * (1.0 - u) + lm["knee_l"].y * u
            else:
                u = (knee_z - co.z) / max(knee_z - cuff_z, 1e-4)
                cx = (knee_lx if is_l else knee_rx) * (1.0 - u) + (ank_lx if is_l else ank_rx) * u
                cy = lm["knee_l"].y * (1.0 - u) + lm["ank_l"].y * u
            rad_v = Vector((co.x - cx, co.y - cy, 0.0))
            r = rad_v.length
            rdir = rad_v.normalized() if r > 1e-5 else Vector((n.x, n.y, 0.0)).normalized()
            # Straight-leg denim fit matching CA_Jason_Turnaround_v01.jpg (roomy thigh -> straight knee -> clean cuff)
            min_r = 0.095 * (1.0 - t_leg) + 0.080 * t_leg
            extra = 0.011 + 0.006 * t_leg
            stack = 0.0038 * math.sin((co.z - cuff_z) * 52.0) * math.exp(-((co.z - cuff_z) / 0.13) ** 2)
            knee_fold = 0.0020 * math.sin((co.z - knee_z) * 44.0) * math.exp(-((co.z - knee_z) / 0.08) ** 2)
            target_r = max(r + extra, min_r) + stack + knee_fold
            v.co.x = cx + rdir.x * target_r
            v.co.y = cy + rdir.y * target_r
        else:
            off = 0.0095
            if co.z > waist_z - 0.036:
                off += 0.0028  # clean waistband contour
            # Subtle flush sculptural ridge for back patch pockets (integral to mesh — never floats!)
            if co.y > 0.04 and (0.032 < abs(co.x) < 0.135) and (hips_z - 0.11 < co.z < hips_z + 0.005):
                off += 0.0024
            v.co += n * off
            if co.y > 0.02 and abs(co.x) < 0.068:
                v.co.y += 0.013 * (1.0 - abs(co.x) / 0.068)
            if co.y < -0.02 and abs(co.x) < 0.055 and co.z < hips_z - 0.03:
                v.co.y -= 0.006 * (1.0 - abs(co.x) / 0.055)

    bm.to_mesh(ob.data)
    bm.free()

    _laplacian_smooth(ob, iterations=4, factor=0.40, smooth_boundary=True)
    _enforce_clearance(ob, [body_ob], min_clearance=0.006, passes=3)
    _add_turned_rim(ob, depth=0.0040)
    _clean_uv_unwrap(ob, angle_limit_deg=60.0, island_margin=0.014)
    return ob


# ==============================================================================
# GARMENT 4: Worn Brown Leather Work Boots with Lugged Outsole (z = 0.000 exact)
# ==============================================================================
def _build_one_boot(bm, foot_pts, ank_pt, toe_pt, side_sign):
    x_min, x_max = float(foot_pts[:, 0].min()), float(foot_pts[:, 0].max())
    y_toe, y_heel = float(foot_pts[:, 1].min()), float(foot_pts[:, 1].max())
    cx = 0.5 * (x_min + x_max)
    half_w = max(0.052, 0.5 * (x_max - x_min) + 0.011)
    boot_y_toe = y_toe - 0.022
    boot_y_heel = y_heel + 0.018
    boot_len = boot_y_heel - boot_y_toe
    ank_top_z = ank_pt.z + 0.068  # tucks cleanly inside jeans cuff

    def planform_xy(theta, len_scale=1.0, wid_scale=1.0, y_shift=0.0):
        s, c = math.sin(theta), math.cos(theta)
        w_mod = 1.0 if c > 0 else (0.76 + 0.24 * (1.0 + c))
        arch = -0.09 * side_sign * math.exp(-((theta - (math.pi * 0.55 if side_sign > 0 else -math.pi * 0.55)) / 0.45) ** 2)
        y_norm = -(c ** 0.85) if c > 0 else ((-c) ** 0.92)
        ym = 0.5 * (boot_y_toe + boot_y_heel) + y_shift
        half_l = 0.5 * boot_len * len_scale
        return cx + (s * w_mod + arch) * half_w * wid_scale, ym + y_norm * half_l

    n_ring = 28
    sole_levels = [
        (0.000, 0.96, 0.95),
        (0.007, 1.02, 1.03),
        (0.020, 1.03, 1.04),
        (0.025, 1.06, 1.07),
        (0.030, 1.00, 1.01),
    ]
    rings = []
    for z, ls, ws in sole_levels:
        ring = []
        for i in range(n_ring):
            th = 2.0 * math.pi * i / n_ring
            x, y = planform_xy(th, ls, ws)
            if 0.001 < z < 0.016 and (i % 2 == 0):
                dx, dy = x - cx, y - 0.5 * (boot_y_toe + boot_y_heel)
                x -= dx * 0.035
                y -= dy * 0.025
            z_cur = max(z, 0.008) if (z < 0.009 and abs(y - (boot_y_toe + boot_len * 0.56)) < boot_len * 0.14) else z
            ring.append(bm.verts.new((x, y, z_cur)))
        rings.append(ring)

    bot_c = bm.verts.new((cx, 0.5 * (boot_y_toe + boot_y_heel), 0.000))
    for i in range(n_ring):
        j = (i + 1) % n_ring
        bm.faces.new((bot_c, rings[0][j], rings[0][i])).smooth = False
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n_ring):
            j = (i + 1) % n_ring
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).smooth = True

    upper_specs = [
        (0.048, 0.000, 0.96, 0.96, 0.002),
        (0.068, 0.008, 0.86, 0.90, 0.018),
        (0.088, 0.022, 0.66, 0.84, 0.046),
        (0.112, 0.000, 0.45, 0.78, 0.072),
        (ank_top_z - 0.020, 0.000, 0.42, 0.76, 0.078),
        (ank_top_z, 0.000, 0.43, 0.77, 0.078),
    ]
    prev_ring = rings[-1]
    for idx_u, (zb, zdrop, ls, ws, ysh) in enumerate(upper_specs):
        ring = []
        for i in range(n_ring):
            th = 2.0 * math.pi * i / n_ring
            c = math.cos(th)
            if idx_u >= 3:
                r_ank = 0.055 if idx_u < 5 else 0.058
                x = ank_pt.x + math.sin(th) * r_ank * 0.92
                y = ank_pt.y - math.cos(th) * r_ank * 1.06
                z = zb - (0.008 if c < -0.5 else 0.0)
            else:
                x, y = planform_xy(th, ls, ws, y_shift=ysh)
                blend_a = idx_u / 3.0
                x = x * (1.0 - 0.25 * blend_a) + (ank_pt.x + math.sin(th) * 0.056) * (0.25 * blend_a)
                z = zb - zdrop * max(0.0, c)
            ring.append(bm.verts.new((x, y, z)))
        for i in range(n_ring):
            j = (i + 1) % n_ring
            bm.faces.new((prev_ring[i], prev_ring[j], ring[j], ring[i])).smooth = True
        prev_ring = ring

    top_in = [bm.verts.new((ank_pt.x + (v.co.x - ank_pt.x) * 0.78, ank_pt.y + (v.co.y - ank_pt.y) * 0.78, v.co.z - 0.006)) for v in prev_ring]
    for i in range(n_ring):
        j = (i + 1) % n_ring
        bm.faces.new((prev_ring[i], prev_ring[j], top_in[j], top_in[i])).smooth = True
    top_c = bm.verts.new((ank_pt.x, ank_pt.y, ank_top_z - 0.015))
    for i in range(n_ring):
        j = (i + 1) % n_ring
        bm.faces.new((top_in[i], top_in[j], top_c)).smooth = True

    # Laces & metal eyelets (kept cleanly below jeans cuff at z <= ank_pt.z - 0.002!)
    for k in range(4):
        t = k / 3.0
        lz = 0.068 + t * (max(0.095, ank_pt.z - 0.008) - 0.068)
        ly = (boot_y_toe + boot_len * 0.36) * (1.0 - t) + (ank_pt.y - 0.056) * t
        lw = 0.034 * (1.0 - 0.14 * t)
        _add_box_detail(bm, Vector((cx, ly - 0.002, lz)), (lw, 0.005, 0.0045), rot_euler=(math.radians(28), 0.0, 0.0), bevel=0.0012)
        for sx in (-1.0, 1.0):
            _add_box_detail(bm, Vector((cx + sx * (lw * 0.54), ly + 0.001, lz)), (0.005, 0.005, 0.005), bevel=0.0014)


def build_boots(body_ob, arm, obj_name):
    lm = _arm_landmarks(arm, body_ob)
    pts = lm["body_pts"]
    ank_z = 0.5 * (lm["ank_l"].z + lm["ank_r"].z)
    bm = bmesh.new()
    for sx, ank, toe in ((1.0, lm["ank_l"], lm["toe_l"]), (-1.0, lm["ank_r"], lm["toe_r"])):
        fmask = (pts[:, 2] < ank_z + 0.03) & ((pts[:, 0] > 0.0) if sx > 0 else (pts[:, 0] < 0.0))
        fpts = pts[fmask]
        if len(fpts) >= 10:
            _build_one_boot(bm, fpts, ank, toe, sx)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(obj_name)
    bm.to_mesh(me)
    bm.free()
    zmin = min(v.co.z for v in me.vertices)
    if abs(zmin) > 1e-6:
        for v in me.vertices:
            v.co.z -= zmin
    me.update()

    ob = bpy.data.objects.new(obj_name, me)
    bpy.context.scene.collection.objects.link(ob)
    _clean_uv_unwrap(ob, angle_limit_deg=55.0, island_margin=0.015)
    return ob


# ==============================================================================
# GARMENT 5: Left Wristwatch (properly bounded local wrist measurement!)
# ==============================================================================
def build_wristwatch(body_ob, arm, obj_name):
    lm = _arm_landmarks(arm, body_ob)
    elb = lm["elb_l"]
    wri = lm["wri_l"]
    arm_dir = (wri - elb).normalized()
    w_center = wri - arm_dir * 0.022

    # Strictly filter vertices within 8.5 cm Euclidean distance of w_center (NEVER torso/legs!)
    pts = lm["body_pts"]
    rel = pts - np.array(w_center[:])
    dists = np.linalg.norm(rel, axis=1)
    along = rel @ np.array(arm_dir[:])
    mask = (dists < 0.085) & (np.abs(along) < 0.018)
    near = pts[mask]
    if len(near) >= 6:
        perp = near - (np.array(w_center[:]) + np.outer(along[mask], np.array(arm_dir[:])))
        r_wrist = float(np.clip(np.percentile(np.linalg.norm(perp, axis=1), 92), 0.025, 0.040))
    else:
        r_wrist = 0.031

    z_loc = Vector((0.0, 0.35, 0.94))
    z_loc = (z_loc - arm_dir * z_loc.dot(arm_dir)).normalized()
    y_loc = z_loc.cross(arm_dir).normalized()
    frame = Matrix((arm_dir, y_loc, z_loc)).transposed().to_4x4()
    frame.translation = w_center

    bm = bmesh.new()
    r_in = r_wrist + 0.0025
    r_out = r_in + 0.0040
    n_seg = 24
    half_sw = 0.010
    rings_in, rings_out = [], []
    for xoff in (-half_sw, half_sw):
        ri, ro = [], []
        for i in range(n_seg):
            th = 2.0 * math.pi * i / n_seg
            cy, cz = math.sin(th) * 1.05, math.cos(th) * 0.92
            ri.append(bm.verts.new(frame @ Vector((xoff, cy * r_in, cz * r_in))))
            ro.append(bm.verts.new(frame @ Vector((xoff, cy * r_out, cz * r_out))))
        rings_in.append(ri)
        rings_out.append(ro)
    for i in range(n_seg):
        j = (i + 1) % n_seg
        bm.faces.new((rings_out[0][i], rings_out[0][j], rings_out[1][j], rings_out[1][i])).smooth = True
        bm.faces.new((rings_in[0][j], rings_in[0][i], rings_in[1][i], rings_in[1][j])).smooth = True
        bm.faces.new((rings_in[0][i], rings_out[0][i], rings_out[0][j], rings_in[0][j])).smooth = False
        bm.faces.new((rings_out[1][i], rings_in[1][i], rings_in[1][j], rings_out[1][j])).smooth = False

    case_base_z = r_in * 0.90
    case_r = 0.020
    case_h = 0.009
    c_levels = [
        (case_base_z, case_r * 0.96),
        (case_base_z + case_h * 0.65, case_r),
        (case_base_z + case_h * 0.88, case_r * 0.94),
        (case_base_z + case_h, case_r * 0.86),
        (case_base_z + case_h * 0.86, case_r * 0.80),
    ]
    n_c = 24
    c_rings = []
    for cz, cr in c_levels:
        c_rings.append([bm.verts.new(frame @ Vector((math.cos(2 * math.pi * i / n_c) * cr, math.sin(2 * math.pi * i / n_c) * cr, cz))) for i in range(n_c)])
    bot_c = bm.verts.new(frame @ Vector((0.0, 0.0, case_base_z)))
    top_c = bm.verts.new(frame @ Vector((0.0, 0.0, case_base_z + case_h * 0.86)))
    for i in range(n_c):
        j = (i + 1) % n_c
        bm.faces.new((bot_c, c_rings[0][j], c_rings[0][i])).smooth = False
        bm.faces.new((c_rings[-1][i], c_rings[-1][j], top_c)).smooth = False
    for r0, r1 in zip(c_rings, c_rings[1:]):
        for i in range(n_c):
            j = (i + 1) % n_c
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).smooth = True

    crown_m = frame @ Matrix.Translation((case_r + 0.002, 0.0, case_base_z + case_h * 0.5)) @ Matrix.Diagonal((0.004, 0.0055, 0.005, 1.0))
    bmesh.ops.create_cube(bm, size=1.0, matrix=crown_m)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(obj_name)
    bm.to_mesh(me)
    bm.free()
    me.update()

    ob = bpy.data.objects.new(obj_name, me)
    bpy.context.scene.collection.objects.link(ob)
    _clean_uv_unwrap(ob, angle_limit_deg=55.0, island_margin=0.02)
    return ob


# ==============================================================================
# REGION-ISOLATED WEIGHT TRANSFER & OCCLUDED BODY FACE CULLING
# ==============================================================================
def transfer_weights_from_body(target_ob, body_ob, arm, rigid_bone=None, allowed_bones=None, smooth_iters=2):
    """Transfer SkeletonProfileHumanoid bone weights from body_ob with strict garment bone isolation."""
    target_ob.vertex_groups.clear()
    if rigid_bone is not None:
        vg = target_ob.vertex_groups.new(name=rigid_bone)
        vg.add([v.index for v in target_ob.data.vertices], 1.0, "REPLACE")
        return

    b_me = body_ob.data
    b_gnames = {g.index: g.name for g in body_ob.vertex_groups}
    deform = {b.name for b in arm.data.bones if b.use_deform and b.name != "Root"}
    if allowed_bones is not None:
        deform = deform & set(allowed_bones)

    # Index ONLY body vertices that carry weight in `allowed_bones` (prevents A-pose hands polluting jeans!)
    valid_b_indices = []
    b_weights = {}
    for v in b_me.vertices:
        ws = [(b_gnames[g.group], g.weight) for g in v.groups if g.weight > 1e-4 and b_gnames.get(g.group) in deform]
        if ws:
            s = sum(w for _, w in ws)
            b_weights[v.index] = [(bn, w / s) for bn, w in ws]
            valid_b_indices.append(v.index)

    kd = KDTree(len(valid_b_indices))
    for k_i, b_vi in enumerate(valid_b_indices):
        kd.insert(b_me.vertices[b_vi].co, b_vi)
    kd.balance()

    t_me = target_ob.data
    per_v = []
    fallback_bone = next(iter(deform)) if deform else "Hips"
    for v in t_me.vertices:
        nbs = kd.find_n(v.co, 4)
        acc = {}
        for _, bi, dist in nbs:
            w_inv = 1.0 / max(dist, 0.002)
            for bn, bw in b_weights[bi]:
                acc[bn] = acc.get(bn, 0.0) + bw * w_inv
        if not acc:
            acc[fallback_bone] = 1.0
        top = sorted(acc.items(), key=lambda x: x[1], reverse=True)[:4]
        s = sum(w for _, w in top) or 1.0
        per_v.append({bn: w / s for bn, w in top})

    if smooth_iters > 0:
        adj = [[] for _ in range(len(t_me.vertices))]
        for e in t_me.edges:
            a, b = e.vertices[0], e.vertices[1]
            adj[a].append(b)
            adj[b].append(a)
        for _ in range(smooth_iters):
            nxt = []
            for i, cur in enumerate(per_v):
                if not adj[i]:
                    nxt.append(cur)
                    continue
                acc = {k: v * 0.55 for k, v in cur.items()}
                w_nb = 0.45 / len(adj[i])
                for j in adj[i]:
                    for k, v in per_v[j].items():
                        acc[k] = acc.get(k, 0.0) + v * w_nb
                top = sorted(acc.items(), key=lambda x: x[1], reverse=True)[:4]
                s = sum(w for _, w in top) or 1.0
                nxt.append({bn: w / s for bn, w in top})
            per_v = nxt

    vgs = {}
    for i, d in enumerate(per_v):
        for bn, w in d.items():
            if w > 1e-5:
                vg = vgs.get(bn)
                if vg is None:
                    vg = target_ob.vertex_groups.new(name=bn)
                    vgs[bn] = vg
                vg.add([i], w, "REPLACE")


def cull_occluded_body_faces(body_ob, arm, has_jacket=True, has_tshirt=True, has_jeans=True, has_boots=True):
    lm = _arm_landmarks(arm, body_ob)
    hips_z = lm["hips_z"]
    neck_z = lm["neck_z"]
    uchest_z = lm["uchest_z"]
    sh_l, elb_l, wri_l = lm["sh_l"], lm["elb_l"], lm["wri_l"]
    sh_r, elb_r, wri_r = lm["sh_r"], lm["elb_r"], lm["wri_r"]

    me = body_ob.data
    to_del_faces = set()
    for p in me.polygons:
        c = p.center
        if c.z > neck_z - 0.048:
            continue
        if c.z > uchest_z + 0.012 and c.y < 0.0 and abs(c.x) < 0.095:
            continue
        if has_tshirt and (hips_z - 0.02 < c.z < uchest_z + 0.025):
            if abs(c.x) < sh_l.x + 0.035:
                to_del_faces.add(p.index)
                continue
        if has_jacket:
            if c.x > sh_l.x + 0.008:
                t, _, _ = _arm_param(c, sh_l, elb_l, wri_l)
                if 0.0 <= t <= 1.62:
                    to_del_faces.add(p.index)
                    continue
            elif c.x < sh_r.x - 0.008:
                t, _, _ = _arm_param(c, sh_r, elb_r, wri_r)
                if 0.0 <= t <= 1.66:
                    to_del_faces.add(p.index)
                    continue
        if has_jeans and (lm["ank_l"].z + 0.01 <= c.z <= hips_z + 0.015):
            to_del_faces.add(p.index)
            continue
        if has_boots and c.z < lm["ank_l"].z + 0.045:
            to_del_faces.add(p.index)
            continue

    if not to_del_faces:
        return 0

    bpy.ops.object.select_all(action="DESELECT")
    body_ob.select_set(True)
    bpy.context.view_layer.objects.active = body_ob
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(me)
    bm.faces.ensure_lookup_table()
    del_f = [bm.faces[i] for i in to_del_faces if i < len(bm.faces)]
    bmesh.ops.delete(bm, geom=del_f, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.update_edit_mesh(me)
    bpy.ops.object.mode_set(mode="OBJECT")
    return len(del_f)


# ==============================================================================
# CLEAN CYCLES HIGH-TO-LOW NORMAL + AO BAKING (NO ZEBRA SELF-OCCLUSION!)
# ==============================================================================
def bake_high_to_low(low_ob, tex_size=512, fold_strength=0.0018, fold_freq=34.0, ao_samples=16, prefix="T_Bake"):
    """High-to-low Cycles Tangent Normal + AO bake with organic subtle cloth folds (zero zebra banding)."""
    sc = bpy.context.scene
    prev_engine = sc.render.engine
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = ao_samples
    sc.cycles.use_denoising = False

    hi = low_ob.copy()
    hi.data = low_ob.data.copy()
    hi.name = low_ob.name + "_HiBakeTmp"
    hi.modifiers.clear()
    bpy.context.scene.collection.objects.link(hi)

    sub = hi.modifiers.new("Subsurf", "SUBSURF")
    sub.levels = 2
    sub.render_levels = 2
    bpy.ops.object.select_all(action="DESELECT")
    hi.select_set(True)
    bpy.context.view_layer.objects.active = hi
    bpy.ops.object.modifier_apply(modifier=sub.name)

    # Organic, gentle multi-octave garment wrinkles (never harsh regular zebra stripes!)
    bm = bmesh.new()
    bm.from_mesh(hi.data)
    bm.normal_update()
    for v in bm.verts:
        p = v.co
        # Soft modulated cloth creases that break up along X/Y/Z smoothly
        env = 0.5 + 0.5 * math.sin(p.x * 11.0 + p.y * 9.0)
        w1 = math.sin(p.z * fold_freq + math.sin(p.x * 19.0) * 2.1 + math.cos(p.y * 17.0) * 1.7)
        w2 = 0.45 * math.sin(p.z * (fold_freq * 1.75) - p.x * 23.0 + p.y * 15.0)
        w3 = 0.25 * math.cos(p.x * 41.0 + p.y * 37.0 + p.z * 29.0)
        v.co += v.normal * (fold_strength * env * (0.55 * w1 + 0.30 * w2 + 0.15 * w3))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(hi.data)
    bm.free()
    hi.data.update()

    nrm_img = bpy.data.images.new(f"{prefix}_HiNrmTmp", tex_size, tex_size, alpha=False, float_buffer=False)
    nrm_img.colorspace_settings.name = "Non-Color"
    ao_img = bpy.data.images.new(f"{prefix}_HiAoTmp", tex_size, tex_size, alpha=False, float_buffer=False)
    ao_img.colorspace_settings.name = "Non-Color"

    saved_mats = [s.material for s in low_ob.material_slots]
    bake_mat = bpy.data.materials.new(f"{prefix}_BakeMatTmp")
    bake_mat.use_nodes = True
    nt = bake_mat.node_tree
    tex_node = nt.nodes.new("ShaderNodeTexImage")
    tex_node.select = True
    nt.nodes.active = tex_node
    low_ob.data.materials.clear()
    low_ob.data.materials.append(bake_mat)

    hidden = []
    for o in sc.objects:
        if o not in (low_ob, hi) and not o.hide_render:
            o.hide_render = True
            hidden.append(o)

    # Normal bake (selected-to-active from high-poly to low-poly)
    tex_node.image = nrm_img
    bpy.ops.object.select_all(action="DESELECT")
    hi.select_set(True)
    low_ob.select_set(True)
    bpy.context.view_layer.objects.active = low_ob
    sc.render.bake.use_selected_to_active = True
    sc.render.bake.cage_extrusion = 0.012
    sc.render.bake.max_ray_distance = 0.025
    sc.render.bake.margin = 8
    sc.render.bake.normal_space = "TANGENT"
    sc.cycles.samples = 4
    bpy.ops.object.bake(type="NORMAL")
    nrm_arr = np.array(nrm_img.pixels[:], dtype=np.float32).reshape((tex_size, tex_size, 4))[:, :, :3]

    # Ambient Occlusion bake directly on low_ob (clean, zero cage self-hit artifacts!)
    hi.select_set(False)
    hi.hide_render = True
    tex_node.image = ao_img
    sc.render.bake.use_selected_to_active = False
    sc.cycles.samples = ao_samples
    bpy.ops.object.bake(type="AO")
    ao_arr = np.array(ao_img.pixels[:], dtype=np.float32).reshape((tex_size, tex_size, 4))[:, :, 0]

    for o in hidden:
        o.hide_render = False
    low_ob.data.materials.clear()
    for m in saved_mats:
        low_ob.data.materials.append(m)
    bpy.data.objects.remove(hi, do_unlink=True)
    bpy.data.materials.remove(bake_mat)
    bpy.data.images.remove(nrm_img)
    bpy.data.images.remove(ao_img)
    sc.render.engine = prev_engine

    return nrm_arr, ao_arr
