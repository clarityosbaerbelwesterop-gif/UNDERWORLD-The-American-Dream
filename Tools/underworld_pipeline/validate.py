"""Validation of an opened asset scene against Config/asset_budgets.json + TD-004/005/009."""
import os

import bpy

from . import scene as S
from .config import CATEGORY_PREFIXES

EPS = 1e-5


def _is_identity_rot(ob):
    if ob.rotation_mode == "QUATERNION":
        q = ob.rotation_quaternion
        return abs(abs(q[0]) - 1) < EPS and all(abs(x) < EPS for x in q[1:])
    if ob.rotation_mode == "AXIS_ANGLE":
        return abs(ob.rotation_axis_angle[0]) < EPS
    return all(abs(x) < EPS for x in ob.rotation_euler)


def _unit_scale(v):
    return all(abs(x - 1.0) < EPS for x in v)


def validate(ctx):
    """Runs all checks, fills ctx.issues, returns a stats dict for the manifest/report."""
    cfg, iss, name, cat = ctx.cfg, ctx.issues, ctx.asset_name, ctx.category
    top = cfg.top(cat)
    sc = bpy.context.scene
    tol = cfg.get("tolerances")
    stats = {}

    # --- units (TD-004)
    us = sc.unit_settings
    if us.system != "METRIC" or abs(us.scale_length - 1.0) > EPS:
        iss.error("UNITS", f"scene units must be METRIC with unit scale 1.0 (got {us.system}, {us.scale_length})")

    # --- asset name + root (TD-005)
    if not S.NAME_RE.match(name):
        iss.error("NAME_ASSET", f"asset name '{name}' is not ASCII PascalCase_parts")
    allowed = CATEGORY_PREFIXES.get(top, ()) + ("PT_",)
    if not name.startswith(allowed):
        iss.error("NAME_PREFIX", f"asset '{name}' in category {cat} must start with one of {allowed}")
    root = sc.objects.get(name)
    if root is None:
        iss.error("ROOT_MISSING", f"no root object named '{name}' (asset root empty/armature at the origin)")
    else:
        if root.parent is not None:
            iss.error("ROOT_PARENTED", "asset root must be top-level", root.name)
        if any(abs(x) > EPS for x in root.location) or not _is_identity_rot(root) or not _unit_scale(root.scale):
            iss.error("ROOT_TRANSFORM", "asset root must sit at the world origin with identity transform", root.name)
        inside = set(S.descendants(root)) | {root}
        for ob in sc.objects:
            if ob not in inside and ob.type not in ("CAMERA", "LIGHT"):
                iss.error("OUTSIDE_ROOT", f"object is not parented under root '{name}'", ob.name)
    for ob in sc.objects:
        if ob.type in ("CAMERA", "LIGHT"):
            iss.info("NOT_EXPORTED", f"{ob.type.lower()} is ignored by the exporter", ob.name)

    # --- object naming, transforms
    for ob in sc.objects:
        if ob.type in ("CAMERA", "LIGHT"):
            continue
        base, hint = S.split_hint(ob.name)
        if not S.NAME_RE.match(base):
            iss.error("NAME_OBJECT", f"'{ob.name}': ASCII PascalCase parts separated by '_' required (+ optional Godot hint)", ob.name)
        if ob.type == "MESH":
            if base.startswith("UCX_") and hint not in S.COLLISION_HINTS:
                iss.error("UCX_NO_HINT", "UCX_ collision proxy needs a Godot hint (-colonly/-convcolonly/-col)", ob.name)
            if hint in S.COLLISION_ONLY_HINTS and not base.startswith("UCX_"):
                iss.warn("COLLISION_PREFIX", "collision-only mesh should start with UCX_", ob.name)
            if not base.startswith(("SM_", "SK_", "UCX_", "PT_")):
                iss.warn("NAME_MESH_PREFIX", "mesh objects should start with SM_/SK_/UCX_ (TD-005); allowed for named parts like Body/Wheel_FL", ob.name)
        if ob.type == "EMPTY" and ob is not root and not base.startswith("SOCKET_"):
            iss.warn("NAME_EMPTY", "empties other than the root should be sockets named SOCKET_<Name>", ob.name)
        is_socket = ob.type == "EMPTY" and base.startswith("SOCKET_")
        if not _unit_scale(ob.scale) or not _unit_scale(ob.delta_scale):
            if is_socket:
                iss.warn("SOCKET_SCALE", "socket has non-unit scale", ob.name)
            else:
                iss.error("TRANSFORM_SCALE", f"scale not applied {tuple(round(x, 4) for x in ob.scale)}", ob.name)
        if not is_socket and ob.type in ("MESH", "ARMATURE") and (not _is_identity_rot(ob) or any(abs(x) > EPS for x in ob.delta_rotation_euler)):
            iss.error("TRANSFORM_ROTATION", "rotation not applied", ob.name)
        if ob.type == "MESH" and ob.matrix_world.determinant() < 0:
            iss.error("NEGATIVE_SCALE", "negative scale / mirrored transform", ob.name)

    # --- meshes: tris, UVs, topology, materials, textures
    dg = bpy.context.evaluated_depsgraph_get()
    mats = set()
    meshes = S.visible_meshes(sc)
    per_obj = {}
    max_tex, tex_tier = cfg.max_texture_size(cat)
    with S.rest_pose(sc):
        dg = bpy.context.evaluated_depsgraph_get()
        for ob in sc.objects:
            if ob.type != "MESH":
                continue
            st = S.evaluated_mesh_stats(ob, dg)
            per_obj[ob.name] = st
            visible = ob in meshes
            if st["triangles"] == 0:
                iss.error("EMPTY_MESH", "mesh has no faces", ob.name)
            if st["loose_vertices"] or st["loose_edges"]:
                iss.error("LOOSE_GEOMETRY", f"{st['loose_vertices']} loose vertices, {st['loose_edges']} loose edges", ob.name)
            if st["non_manifold_edges"] or st["non_manifold_vertices"]:
                iss.warn("NON_MANIFOLD", f"{st['non_manifold_edges']} edges with >2 faces, {st['non_manifold_vertices']} non-manifold vertices", ob.name)
            if st["boundary_edges"]:
                (iss.warn if S.split_hint(ob.name)[1] in ("-colonly", "-col") else iss.info)(
                    "OPEN_BOUNDARY", f"{st['boundary_edges']} open boundary edges (mesh not closed)", ob.name)
            if st["degenerate_faces"]:
                iss.warn("DEGENERATE_FACES", f"{st['degenerate_faces']} zero-area faces", ob.name)
            if not visible:
                continue
            if st["uv_layers"] == 0:
                iss.error("NO_UVS", "visible mesh has no UV map", ob.name)
            slots = ob.material_slots
            if not slots:
                iss.error("NO_MATERIAL", "visible mesh has no material", ob.name)
            for s in slots:
                if s.material is None:
                    iss.error("EMPTY_MATERIAL_SLOT", "empty material slot", ob.name)
                else:
                    mats.add(s.material)
        bboxes = [per_obj[o.name]["bbox"] for o in meshes]
    bb = S.merge_bbox(bboxes)

    tris_lod0 = sum(per_obj[o.name]["triangles"] for o in meshes)
    budget = cfg.max_triangles(ctx.budget_key) if ctx.budget_key else None
    if budget is None:
        iss.error("NO_BUDGET", f"no max_triangles budget for category '{cat}' / asset '{name}' in {os.path.relpath(cfg.budgets_path, cfg.repo)} (use --budget-key)")
    elif tris_lod0 > budget:
        iss.error("TRI_BUDGET", f"LOD0 has {tris_lod0} triangles > budget {budget} ({ctx.budget_key})", tris=tris_lod0, budget=budget)
    stats["triangles_lod0"] = tris_lod0
    stats["triangle_budget"] = budget
    stats["per_object"] = {k: {"triangles": v["triangles"], "vertices": v["vertices"]} for k, v in per_obj.items()}

    for m in mats:
        if not S.NAME_RE.match(m.name) or not m.name.startswith("M_"):
            iss.error("NAME_MATERIAL", "material must be named M_<PascalCase>", m.name)
    max_mats = cfg.per_category("max_materials", cat)
    if max_mats and len(mats) > max_mats:
        iss.warn("MATERIAL_COUNT", f"{len(mats)} materials > recommended {max_mats} (draw calls)")
    textures = []
    for m in sorted(mats, key=lambda m: m.name):
        for img in S.material_images(m):
            w, h = img.size[:]
            entry = {"image": img.name, "material": m.name, "size": [w, h],
                     "packed": bool(img.packed_file), "filepath": img.filepath}
            textures.append(entry)
            path = bpy.path.abspath(img.filepath) if img.filepath else ""
            if not img.packed_file and (not path or not os.path.isfile(path)) and img.source == "FILE":
                iss.error("TEXTURE_MISSING", f"image file not found: {img.filepath}", img.name)
            if max(w, h) > max_tex:
                iss.error("TEXTURE_SIZE", f"{w}x{h} > {max_tex} ({tex_tier} tier)", img.name)
            if w and h and (w & (w - 1) or h & (h - 1)):
                iss.warn("TEXTURE_POT", f"{w}x{h} is not power-of-two", img.name)
            if not img.name.startswith("T_"):
                iss.warn("NAME_TEXTURE", "texture should be named T_<Name>_D/_N/_ORM (TD-005)", img.name)
    stats["materials"] = sorted(m.name for m in mats)
    stats["textures"] = textures
    stats["max_texture_size"] = max_tex

    # --- UV overlap & texel density checks (T-PIPE-03 quality gates)
    uv_warn = float(tol.get("uv_overlap_warn", 0.08))
    uv_err = float(tol.get("uv_overlap_error", 0.35))
    td_min = float(tol.get("texel_density_min_hero", 256) if tex_tier == "hero" else tol.get("texel_density_min_default", 128))
    uv_overlaps = {}
    texel_densities = {}
    for ob in meshes:
        if ob.data.uv_layers:
            if not ob.get("uw_allow_uv_overlap"):
                ov, cov = S.uv_overlap_ratio(ob)
                uv_overlaps[ob.name] = {"overlap_fraction": ov, "uv_coverage": cov}
                if ov > uv_err:
                    iss.error("UV_OVERLAP", f"UV self-overlap {ov * 100:.1f}% > {uv_err * 100:.0f}% (set uw_allow_uv_overlap for intentional stacked cards)", ob.name, overlap=ov)
                elif ov > uv_warn:
                    iss.warn("UV_OVERLAP", f"UV self-overlap {ov * 100:.1f}% > {uv_warn * 100:.0f}%", ob.name, overlap=ov)
            td = S.texel_density_stats(ob)
            if td:
                texel_densities[ob.name] = td
                if td["median_px_per_m"] < td_min:
                    iss.info("TEXEL_DENSITY", f"median texel density {td['median_px_per_m']} px/m < target {td_min} px/m", ob.name, **td)
    stats["uv_overlap"] = uv_overlaps
    stats["texel_density"] = texel_densities

    # --- layered clothing clipping check (Characters, rest pose)
    clipping = []
    if top == "Characters":
        clip_err = float(tol.get("clipping_error_frac", 0.03))
        with S.rest_pose(sc):
            dg_clip = bpy.context.evaluated_depsgraph_get()
            clipping = S.check_layered_clipping(sc, dg_clip)
        for c in clipping:
            if c["tested_vertices"] >= 20 and c["clipped_fraction"] > clip_err:
                iss.error("MESH_CLIPPING",
                          f"{c['inner']} clips through {c['outer']}: {c['clipped_vertices']}/{c['tested_vertices']} verts ({c['clipped_fraction']*100:.1f}% > {clip_err*100:.1f}%)",
                          c["inner"], **c)
            elif c["clipped_vertices"] > 0:
                iss.info("MESH_CLIPPING",
                         f"{c['inner']} vs {c['outer']}: {c['clipped_vertices']}/{c['tested_vertices']} verts ({c['clipped_fraction']*100:.2f}%)",
                         c["inner"], **c)
    stats["clipping"] = clipping

    # --- origin / pivot (TD-004)
    if bb:
        stats["bbox_blender"] = [[round(x, 4) for x in bb[0]], [round(x, 4) for x in bb[1]]]
        size = [bb[1][i] - bb[0][i] for i in range(3)]
        if top != "Weapons" and abs(bb[0][2]) > tol["ground_m"]:
            iss.error("ORIGIN_GROUND", f"lowest point z={bb[0][2]:.4f} m; origin must be on the ground (bottom) for {top}")
        if top in ("Props", "Characters", "Vehicles", "Test"):
            for i, ax in ((0, "X"), (1, "Y")):
                c = (bb[0][i] + bb[1][i]) / 2
                if abs(c) > tol["centre_m"] + tol["centre_rel"] * size[i]:
                    iss.warn("ORIGIN_CENTRE", f"bbox centre {ax}={c:.3f} m; origin should be centred for {top}")
        hk, href = cfg.reference_height(name)
        if href and abs(size[2] - href) > tol["height_m"]:
            iss.error("REFERENCE_HEIGHT", f"height {size[2]:.3f} m != reference {href} m ({hk}) ±{tol['height_m']}")

    # --- front direction for named front markers (TD-004: front = Blender -Y)
    for ob in meshes:
        if "Front" in S.split_hint(ob.name)[0]:
            st = per_obj[ob.name]
            if st["bbox"]:
                cy = (st["bbox"][0][1] + st["bbox"][1][1]) / 2
                if cy >= 0:
                    iss.error("FRONT_AXIS", f"front marker centre y={cy:.3f} >= 0: asset front must be Blender -Y (Godot +Z)", ob.name)
    if top == "Vehicles" and bb:
        if (bb[1][0] - bb[0][0]) > (bb[1][1] - bb[0][1]):
            iss.warn("FRONT_AXIS", "vehicle is longer in X than Y: long axis must be Blender Y (front -Y -> Godot +Z)")

    # --- skinning + armature
    max_inf = cfg.get("max_bone_influences") or 4
    arms = [o for o in sc.objects if o.type == "ARMATURE"]
    stats["armatures"] = {}
    for arm in arms:
        deform = {b.name for b in arm.data.bones if b.use_deform}
        stats["armatures"][arm.name] = {"bones": [b.name for b in arm.data.bones], "deform_bones": len(deform)}
        for b in arm.data.bones:
            if not S.NAME_RE.match(b.name):
                iss.warn("NAME_BONE", f"bone '{b.name}' not PascalCase ASCII", arm.name)
        if top == "Characters":
            names = {b.name for b in arm.data.bones}
            missing = [b for b in cfg.get("humanoid_required_bones") if b not in names]
            if missing:
                iss.error("HUMANOID_BONES", f"missing SkeletonProfileHumanoid bones: {missing}", arm.name)
            # facing (TD-004 / REQ-GP01-JASON §2): character faces Blender -Y -> Godot +Z
            bl, mw = arm.data.bones, arm.matrix_world
            if "LeftUpperArm" in bl and "RightUpperArm" in bl:
                lx = (mw @ bl["LeftUpperArm"].head_local).x
                rx = (mw @ bl["RightUpperArm"].head_local).x
                if lx <= rx:
                    iss.error("FRONT_AXIS", f"LeftUpperArm x={lx:.3f} <= RightUpperArm x={rx:.3f}: character must face Blender -Y (Godot +Z, TD-004)", arm.name)
            for side in ("Left", "Right"):
                fb = bl.get(side + "Foot")
                if fb is not None:
                    d = (mw @ fb.tail_local) - (mw @ fb.head_local)
                    if d.y > 0.01:
                        iss.error("FRONT_AXIS", f"{side}Foot points to +Y: character must face Blender -Y (Godot +Z, TD-004)", arm.name)
            opt = [b for b in cfg.get("humanoid_optional_bones") if b not in names]
            if opt:
                iss.info("HUMANOID_OPTIONAL", f"optional humanoid bones absent: {opt}", arm.name)
    for ob in sc.objects:
        if ob.type != "MESH" or S.is_collision_only(ob):
            continue
        mods = [m for m in ob.modifiers if m.type == "ARMATURE"]
        if not mods:
            if ob.name.startswith("SK_"):
                iss.error("SK_NOT_SKINNED", "SK_ mesh has no Armature modifier", ob.name)
            continue
        arm = mods[0].object
        if arm is None:
            iss.error("ARMATURE_MOD_EMPTY", "Armature modifier without armature object", ob.name)
            continue
        deform = {b.name for b in arm.data.bones if b.use_deform}
        gidx = {g.index: g.name for g in ob.vertex_groups}
        w_tol = float(tol.get("weight_sum_tol", 0.02))
        over, unweighted, unnorm, max_seen = 0, 0, 0, 0
        for v in ob.data.vertices:
            ws = [g.weight for g in v.groups if g.weight > 1e-4 and gidx.get(g.group) in deform]
            n = len(ws)
            max_seen = max(max_seen, n)
            if n > max_inf:
                over += 1
            elif n == 0:
                unweighted += 1
            elif abs(sum(ws) - 1.0) > w_tol:
                unnorm += 1
        if over:
            iss.error("BONE_INFLUENCES", f"{over} vertices have > {max_inf} bone influences (max {max_seen})", ob.name)
        if unweighted:
            iss.error("UNWEIGHTED_VERTICES", f"{unweighted} vertices have no deform-bone weight", ob.name)
        if unnorm:
            iss.error("WEIGHT_UNNORMALIZED", f"{unnorm} vertices have deform weight sum outside 1.0 ± {w_tol}", ob.name)
        stray = sorted(set(gidx.values()) - {b.name for b in arm.data.bones})
        if stray:
            iss.info("VGROUP_NO_BONE", f"vertex groups without bone (ignored for skinning): {stray[:8]}", ob.name)
        if ob.parent is not arm:
            iss.warn("SKIN_PARENT", f"skinned mesh should be parented to its armature '{arm.name}'", ob.name)

    # --- animations
    fps = sc.render.fps / sc.render.fps_base
    anims = []
    for a in sorted(bpy.data.actions, key=lambda a: a.name):
        if a.users == 0:
            continue
        fs, fe = a.frame_range
        anims.append({"name": a.name, "frame_start": round(fs, 3), "frame_end": round(fe, 3), "fps": fps,
                      "duration_s": round((fe - fs) / fps, 4),
                      "frames": int(round(fe - fs)),
                      "loop": bool(a.get("loop", a.use_frame_range and a.use_cyclic)),
                      "speed_mps": float(a["speed_mps"]) if "speed_mps" in a else None,
                      "slots": [s.identifier for s in a.slots]})
        if not a.name.startswith("A_") or not S.NAME_RE.match(a.name):
            iss.error("NAME_ACTION", "animation actions must be named A_<Asset>_<Name> (TD-005)", a.name)
        if a.is_empty:
            iss.warn("ACTION_EMPTY", "action has no keyframes", a.name)
    if anims and abs(fps - 30) > 1e-3:
        iss.warn("ANIM_FPS", f"scene fps {fps} != 30 (T-ART-02)")
    for an in anims:
        nm = an["name"]
        if top == "Characters" and abs(an["frame_start"]) > 1e-3:
            iss.warn("ANIM_START_FRAME", f"action starts at frame {an['frame_start']} (REQ-GP01-JASON: start at frame 0; exporter slides to t=0 anyway)", nm)
        low = nm.lower()
        if low.endswith(("_loop", "-loop", "_cycle", "-cycle")) or "$loop" in low or "$cycle" in low:
            # TD-005 addendum (director, 2026-11-22): Godot's scene importer matches these hints case-insensitively,
            # strips them from the name (verified 4.7.2: "A_Jason_Jump_Loop" -> "A_Jason_Jump") and forces looping,
            # so the engine would not find the clip by its Blender name. Loop mode comes only from the manifest.
            iss.error("NAME_ACTION_LOOP", "action names must not end in _Loop/-Loop/_Cycle/-Cycle (any case, TD-005 addendum): "
                      "Godot strips the suffix on import; set looping via the action's loop flag (manifest) instead", nm)
    stats["animations"] = anims

    # --- sockets
    stats["sockets"] = {}
    for ob in sc.objects:
        if ob.type == "EMPTY" and ob.name.startswith("SOCKET_"):
            stats["sockets"][ob.name] = {"parent": ob.parent.name if ob.parent else None,
                                         "parent_bone": ob.parent_bone or None,
                                         "position_godot": S.to_godot(ob.matrix_world.translation)}
    req = (cfg.get("required_sockets") or {}).get(ctx.budget_key or "", {})
    for sock, bone in req.items():
        info = stats["sockets"].get(sock)
        if info is None:
            iss.error("SOCKET_MISSING", f"required socket {sock} missing (parent bone {bone})")
        elif bone and info["parent_bone"] != bone:
            iss.error("SOCKET_PARENT", f"{sock} must be parented to bone {bone} (got {info['parent_bone']})", sock)
    stats["bbox"] = bb
    return stats
