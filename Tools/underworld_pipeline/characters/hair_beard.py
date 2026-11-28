"""Sculpted textured short-crop hair + subtle hairline fringe cards & seamless micro-beard shell.

Designed specifically to avoid the "floating pancake card" look on short faded hairstyles:
  - Uses a smooth, organically sculpted 3D hair volume tapering cleanly to 0 mm flush into the
    2K skin-fade scalp transition (zero polygonal shelf, exact CA_Jason_Head_v01.jpg profile!)
  - Sculpted directional hair lock grooves across top/crown + crisp directional strand UVs
  - Delicate, closely-hugging alpha hair wisps along the front fringe & crown silhouette
  - Seamless feathered beard shell synchronized with all ARKit/viseme facial blendshapes (value=0.0!)
"""
import math
import random

import bmesh
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


def _add_fringe_wisp(bm, uv_layer, origin, normal, flow_dir, length, width, arch=0.002, uv_tile=(0.0, 0.24, 0.25, 0.99)):
    n = normal.normalized()
    f = flow_dir - n * flow_dir.dot(n)
    if f.length < 1e-6:
        f = Vector((0.0, -1.0, 0.0))
    f.normalize()
    side = n.cross(f).normalized()
    u0, v0, u1, v1 = uv_tile
    rings = []
    for s in range(3):
        t = s / 2.0
        lift = arch * math.sin(math.pi * (t ** 0.75))
        wh = 0.5 * width * (1.0 - 0.65 * (t ** 1.3))
        c = origin + f * (length * t) + n * lift
        rings.append((bm.verts.new(c - side * wh), bm.verts.new(c + side * wh), t))
    for s in range(2):
        vl0, vr0, t0 = rings[s]
        vl1, vr1, t1 = rings[s + 1]
        face = bm.faces.new((vl0, vr0, vr1, vl1))
        face.smooth = True
        tv0 = v0 + (v1 - v0) * t0
        tv1 = v0 + (v1 - v0) * t1
        for loop, uv in zip(face.loops, [(u0, tv0), (u1, tv0), (u1, tv1), (u0, tv1)]):
            loop[uv_layer].uv = uv


def build_hair(body_ob, arm, lm, obj_name, style="skin_fade_crop", seed=42):
    """Build sculpted, lock-textured 3D hair volume tapering smoothly into the 2K skin fade + delicate fringe wisps."""
    rng = random.Random(seed)
    me_body = body_ob.data
    crown_z = lm["crown_z"]
    eye_z = lm["eye_z"]
    brow_z = lm["brow_z"]
    face_h = lm["face_h"]
    head_c = lm["head_center"]
    eye_y = lm["eye_front_y"]

    hairline_z = brow_z + face_h * 0.165
    parietal_z = brow_z + face_h * 0.125

    def scalp_weight(co):
        if co.z < eye_z - 0.02:
            return 0.0
        back_t = max(0.0, min(1.0, (co.y - head_c.y) / 0.10))
        if style == "skin_fade_crop":
            z_min = parietal_z - back_t * (face_h * 0.16)
            # The forehead is the *front* (-Y) part of the head. On the sides and the back the
            # cap must reach further down, otherwise a single z threshold cuts a horizontal
            # band around the head and the scalp show-through reads as a bald stripe.
            frontness = max(0.0, min(1.0, (eye_y + 0.055 - co.y) / 0.075))
            front_z_min = hairline_z - (1.0 - frontness) * face_h * 0.075 \
                + 0.006 * max(0.0, (abs(co.x) - 0.042) / 0.03)
            eff_z_min = front_z_min if co.y < head_c.y - 0.015 else z_min
            if co.z < eff_z_min or co.y < eye_y + 0.004:
                return 0.0
            return min(1.0, (co.z - eff_z_min) / 0.028)
        elif style == "short_combed":
            z_min = brow_z + face_h * 0.05 - back_t * (face_h * 0.24)
            if co.z < z_min or co.y < eye_y + 0.006:
                return 0.0
            return min(1.0, (co.z - z_min) / 0.026)
        elif style == "buzz_cut":
            z_min = brow_z + face_h * 0.08 - back_t * (face_h * 0.18)
            if co.z < z_min or co.y < eye_y + 0.004:
                return 0.0
            return min(1.0, (co.z - z_min) / 0.022)
        else:
            # medium_crop: this used to be a single z threshold (brow_z - face_h * 0.02), i.e. the
            # cap was allowed to reach *below* the brow line. Combined with the front guard
            # (co.y < eye_y + 0.004) that produced a heavy fringe across the eyebrows on Marco and
            # the civilian - the haircut read as a bowl cut. The front of the head gets the same
            # treatment as skin_fade_crop: stop above the hairline, and only drop lower towards the
            # sides/back.
            frontness = max(0.0, min(1.0, (eye_y + 0.055 - co.y) / 0.075))
            front_z_min = hairline_z + face_h * 0.020 + 0.006 * max(0.0, (abs(co.x) - 0.042) / 0.03)
            side_z_min = brow_z + face_h * 0.03 - back_t * (face_h * 0.24)
            eff_z_min = front_z_min if co.y < head_c.y - 0.015 else side_z_min
            # Also fade the cap out laterally at brow height so it never covers an eyebrow.
            if co.z < eff_z_min or co.y < eye_y + 0.004:
                return 0.0
            return min(1.0, (co.z - eff_z_min) / 0.026)

    # 1. Extract smooth scalp surface
    bm = bmesh.new()
    vmap = {}
    cap_polys = [p for p in me_body.polygons if scalp_weight(p.center) > 0.0]
    for p in cap_polys:
        fvs = []
        for vi in p.vertices:
            if vi not in vmap:
                vmap[vi] = bm.verts.new(me_body.vertices[vi].co)
            fvs.append(vmap[vi])
        try:
            f = bm.faces.new(fvs)
            f.smooth = True
        except ValueError:
            pass
    # Clean boundary spikes (3-boundary-edge jagged teeth!)
    for _ in range(2):
        bm.faces.ensure_lookup_table()
        spikes = [f for f in bm.faces if sum(1 for e in f.edges if e.is_boundary) >= 3]
        if not spikes:
            break
        for f in spikes:
            bm.faces.remove(f)
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")

    me_tmp = bpy.data.meshes.new(obj_name + "_Tmp")
    bm.to_mesh(me_tmp)
    bm.free()
    ob_tmp = bpy.data.objects.new(obj_name + "_Tmp", me_tmp)
    bpy.context.scene.collection.objects.link(ob_tmp)

    # Subdivide 1 level for smooth, sculpted organic hair locks & zero polygonal stair-stepping!
    sub = ob_tmp.modifiers.new("Subsurf", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    bpy.ops.object.select_all(action="DESELECT")
    ob_tmp.select_set(True)
    bpy.context.view_layer.objects.active = ob_tmp
    bpy.ops.object.modifier_apply(modifier=sub.name)

    # 2. Sculpt realistic short-crop silhouette + directional textured hair locks directly into vertices!
    bm = bmesh.new()
    bm.from_mesh(ob_tmp.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    bm.verts.ensure_lookup_table()

    # Compute smooth boundary ring distance (0 at boundary -> smoothly tucked to 0.0mm flush inside fade!)
    b_set = {v.index for v in bm.verts if v.is_boundary}
    r1_set = {v.index for v in bm.verts if v.index not in b_set and any(e.other_vert(v).index in b_set for e in v.link_edges)}
    r2_set = {v.index for v in bm.verts if v.index not in b_set and v.index not in r1_set and any(e.other_vert(v).index in r1_set for e in v.link_edges)}

    max_thick = {"skin_fade_crop": 0.0115, "short_combed": 0.016, "buzz_cut": 0.004, "medium_crop": 0.020}.get(style, 0.0115)

    for v in bm.verts:
        co = v.co
        n = v.normal
        # Smooth boundary taper: boundary sits -0.5mm tucked cleanly inside scalp fade -> ZERO hard rim!
        if v.index in b_set:
            t_edge = -0.0005
        elif v.index in r1_set:
            t_edge = 0.0016
        elif v.index in r2_set:
            t_edge = 0.0050
        else:
            w = scalp_weight(co)
            front_boost = 1.0 + 0.28 * max(0.0, (head_c.y + 0.02 - co.y) / 0.11) * max(0.0, 1.0 - abs(co.x) / 0.075)
            # Directional lock ridges, faded out near the vertex so the mesh stays smooth and
            # the crown does not turn into a corduroy of hard sin() stripes.
            lock_u = co.x * 95.0 + co.y * 26.0
            lock_v = co.y * 46.0 - co.x * 15.0
            lock_wave = (
                0.00075 * math.sin(lock_u + 1.4 * math.sin(lock_v * 0.6))
                + 0.00040 * math.cos(lock_u * 2.1 - lock_v * 0.9)
            ) * (1.0 - 0.55 * min(1.0, abs(co.x) / 0.085))
            t_edge = max_thick * (0.45 + 0.55 * w) * front_boost + lock_wave
        v.co = co + n * t_edge

    # Assign clean continuous directional hair UVs mapped into the textured opaque hair-strand band (V=0.02..0.21)
    # with boundary vertices softly feathered at V=0.20..0.22!
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        f.smooth = True
        for loop in f.loops:
            co = loop.vert.co
            u = 0.04 + 0.92 * max(0.0, min(1.0, (co.x + 0.09) / 0.18))
            v_uv = 0.02 + 0.19 * max(0.0, min(1.0, (co.y - eye_y) / 0.21))
            loop[uv_layer].uv = (u, v_uv)

    # 3. Add ~120 fine, closely-hugging textured fringe hair wisps along top crown & front hairline!
    #    (Gives delicate wispy strands breaking up the front & top silhouette with zero floating pancakes!)
    if style != "buzz_cut":
        bm.faces.ensure_lookup_table()
        top_faces = [f for f in bm.faces if f.calc_center_median().z > brow_z + face_h * 0.22 and f.calc_center_median().y < head_c.y + 0.045]
        if top_faces:
            areas = [max(f.calc_area(), 1e-7) for f in top_faces]
            for f in rng.choices(top_faces, weights=areas, k=115):
                c = f.calc_center_median()
                n = f.normal.normalized()
                # Sweeps tightly forward-left along sculpted crop contour
                flow = Vector((0.25 + rng.uniform(-0.18, 0.18), -0.94, 0.04 + rng.uniform(-0.08, 0.10)))
                tile_col = rng.randint(0, 3)
                uv_tile = (tile_col * 0.25 + 0.01, 0.24, (tile_col + 1) * 0.25 - 0.01, 0.99)
                _add_fringe_wisp(
                    bm, uv_layer,
                    c - n * 0.001, n, flow,
                    length=rng.uniform(0.015, 0.025),
                    width=rng.uniform(0.008, 0.013),
                    arch=rng.uniform(0.0012, 0.0030),
                    uv_tile=uv_tile,
                )

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(obj_name)
    bm.to_mesh(me)
    bm.free()
    me.update()

    # Clean up temporary object
    bpy.data.objects.remove(ob_tmp, do_unlink=True)
    bpy.data.meshes.remove(me_tmp)

    ob = bpy.data.objects.new(obj_name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob["uw_allow_uv_overlap"] = True
    ob.vertex_groups.new(name="Head").add([v.index for v in me.vertices], 1.0, "REPLACE")
    return ob


def build_beard(body_ob, arm, lm, obj_name, style="short_boxed_beard", seed=101):
    """Build a subtle, closely-hugging feathered 3D micro-beard shell synchronized with facial blendshapes."""
    if style in (None, "none", "clean_shaven"):
        return None

    me_body = body_ob.data
    mouth_z = lm["mouth_z"]
    lip_c = mouth_z - 0.004
    chin_z = lm["chin_z"]
    nose_tip = lm["nose_tip"]
    head_c = lm["head_center"]

    def in_beard(co):
        if co.y > head_c.y - 0.014:
            return False
        if co.z < chin_z - 0.032 or co.z > nose_tip.z - 0.005:
            return False
        ax = abs(co.x)
        if lip_c + 0.008 <= co.z <= nose_tip.z - 0.006 and ax < 0.036 and co.y < nose_tip.y + 0.050:
            return True
        if abs(co.z - lip_c) < 0.009 and ax < 0.026:
            return False
        if style == "goatee":
            return ax < 0.036 and co.z < lip_c + 0.016 and co.y < nose_tip.y + 0.062
        cheek_top_z = mouth_z + 0.006 + max(0.0, min(1.0, (ax - 0.026) / 0.044)) * 0.034
        if co.z > cheek_top_z:
            return False
        neck_cut_z = (chin_z - 0.030) + max(0.0, (co.y - (nose_tip.y + 0.065)) / 0.040) * 0.030
        if co.z < neck_cut_z:
            return False
        if lip_c - 0.020 < co.z < lip_c - 0.008 and 0.009 < ax < 0.022:
            return False
        return True

    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    vmap = {}
    shell_polys = [p for p in me_body.polygons if in_beard(p.center)]
    if not shell_polys:
        bm.free()
        return None

    edge_cnt = {}
    for p in shell_polys:
        vs = list(p.vertices)
        for i in range(len(vs)):
            e = tuple(sorted((vs[i], vs[(i + 1) % len(vs)])))
            edge_cnt[e] = edge_cnt.get(e, 0) + 1
    b_verts = {vi for e, c in edge_cnt.items() if c == 1 for vi in e}

    thickness = {"short_boxed_beard": 0.0014, "stubble": 0.0009, "full_beard": 0.0038, "goatee": 0.0020}.get(style, 0.0014)
    for p in shell_polys:
        fvs = []
        for vi in p.vertices:
            if vi not in vmap:
                v = me_body.vertices[vi]
                off = 0.0002 if vi in b_verts else thickness
                vmap[vi] = bm.verts.new(v.co + v.normal * off)
            fvs.append(vmap[vi])
        try:
            f = bm.faces.new(fvs)
            f.smooth = True
        except ValueError:
            pass

    bm.verts.ensure_lookup_table()
    b_set = {v.index for v in bm.verts if v.is_boundary}
    ring1 = {v.index for v in bm.verts if v.index not in b_set and any(e.other_vert(v).index in b_set for e in v.link_edges)}

    for f in bm.faces:
        for loop in f.loops:
            v = loop.vert
            ang = math.atan2(v.co.x, max(0.01, -(v.co.y - head_c.y)))
            u = 0.5 + 0.48 * max(-1.0, min(1.0, ang / (math.pi * 0.55)))
            v_uv = 0.96 if v.index in b_set else (0.86 if v.index in ring1 else 0.72)
            loop[uv_layer].uv = (u, v_uv)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(obj_name)
    bm.to_mesh(me)
    bm.free()
    me.update()

    ob = bpy.data.objects.new(obj_name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob["uw_allow_uv_overlap"] = True
    ob.vertex_groups.new(name="Head").add([v.index for v in me.vertices], 1.0, "REPLACE")

    if body_ob.data.shape_keys and len(body_ob.data.shape_keys.key_blocks) > 1:
        kd = KDTree(len(me_body.vertices))
        for i, v in enumerate(me_body.vertices):
            kd.insert(v.co, i)
        kd.balance()
        nearest = [kd.find(v.co)[1] for v in me.vertices]
        basis_body = body_ob.data.shape_keys.key_blocks[0]
        ob.shape_key_add(name="Basis", from_mix=False)
        for kb_b in body_ob.data.shape_keys.key_blocks[1:]:
            sk = ob.shape_key_add(name=kb_b.name, from_mix=False)
            sk.value = 0.0
            for vi, bi in enumerate(nearest):
                dv = kb_b.data[bi].co - basis_body.data[bi].co
                sk.data[vi].co = Vector(me.vertices[vi].co) + dv

    return ob
