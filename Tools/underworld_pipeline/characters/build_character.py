"""Spec-driven realistic character generator CLI (headless Blender 5.2 bpy).

Usage:
  /workspace/tools/blender/blender -b --factory-startup --python-exit-code 1 \\
      --python Tools/underworld_pipeline/characters/build_character.py -- \\
      --spec Config/Characters/SK_Jason.json [--out-blend path.blend] [--no-bake]

Generates a production-grade, game-ready character .blend from a declarative JSON/YAML spec:
  1. CC0 MakeHuman hm08 parametric human base + macro/face morphs + ARKit/viseme facial blendshapes
  2. CC0 MakeHuman eyes, eyebrows (scar-notched when configured), eyelashes, teeth & tongue via .mhclo
  3. Layered fitted separate clothing meshes (t-shirt, jacket, jeans, boots, watch) with anti-clipping
  4. Cycles CPU high-to-low Tangent Normal & AO bake + CC0 Poly Haven / MakeHuman PBR compositing
  5. Layered hair cards + blendshape-bound beard hair cards
  6. 53-bone SkeletonProfileHumanoid rig (Root + 22 body + 30 fingers), normalized <=4 weights, T-pose rest
  7. SOCKET_RightHand_Weapon oriented +Y up / +Z barrel in aim pose
  8. Full 21-clip animation library (CC0 BVH mocap-informed walk + proper two-handed pistol grip)
"""
import argparse
import json
import os
import sys
import time

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
REPO_ROOT = os.path.abspath(os.path.join(TOOLS_DIR, ".."))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from underworld_pipeline.characters import animations as ANIM  # noqa: E402
from underworld_pipeline.characters import clothing as CLOTH  # noqa: E402
from underworld_pipeline.characters import face_details as FACE  # noqa: E402
from underworld_pipeline.characters import hair_beard as HAIR  # noqa: E402
from underworld_pipeline.characters import mh_loader as MH  # noqa: E402
from underworld_pipeline.characters import pbr_textures as PBR  # noqa: E402
from underworld_pipeline.characters import procedural_assets as PROC  # noqa: E402
from underworld_pipeline.characters import retarget as RETARGET  # noqa: E402


def load_spec(path):
    with open(path, "r", encoding="utf-8") as f:
        if path.endswith((".yaml", ".yml")):
            import yaml
            return yaml.safe_load(f)
        return json.load(f)


def _decimate_in_place(ob, ratio):
    if ratio >= 0.99:
        return
    # Preserve shape keys? For teeth inside the mouth, only decimate if no shape keys or apply cleanly.
    if ob.data.shape_keys:
        # Remove non-basis shape keys temporarily if decimating, or skip decimate
        return
    mod = ob.modifiers.new("Decimate", "DECIMATE")
    mod.ratio = ratio
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=mod.name)


def _clean_decimate_teeth(ob, ratio=0.25):
    """Decimate MakeHuman CC0 teeth_base (~7k tris) down to ~1.6k game-ready tris while keeping jawOpen blendshape."""
    # Teeth are rigid to Head (upper) / jawOpen delta (lower). Store relative jawOpen delta before decimate if small.
    has_sk = bool(ob.data.shape_keys)
    jaw_delta = None
    if has_sk and "jawOpen" in ob.data.shape_keys.key_blocks:
        basis = ob.data.shape_keys.key_blocks[0]
        jaw = ob.data.shape_keys.key_blocks["jawOpen"]
        # Measure average displacement of lower teeth (verts that moved > 1mm)
        moved = [jaw.data[i].co - basis.data[i].co for i in range(len(basis.data))
                 if (jaw.data[i].co - basis.data[i].co).length > 0.001]
        if moved:
            jaw_delta = sum(moved, Vector()) / len(moved)
        # Clear shape keys so Decimate modifier can run cleanly
        for kb in list(ob.data.shape_keys.key_blocks)[::-1]:
            ob.shape_key_remove(kb)

    mod = ob.modifiers.new("Decimate", "DECIMATE")
    mod.ratio = ratio
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=mod.name)

    # Restore jawOpen on lower teeth (vertices below mid-mouth Z)
    if jaw_delta is not None:
        zs = [v.co.z for v in ob.data.vertices]
        z_mid = 0.5 * (min(zs) + max(zs))
        ob.shape_key_add(name="Basis", from_mix=False)
        sk = ob.shape_key_add(name="jawOpen", from_mix=False)
        sk.value = 0.0
        for i, v in enumerate(ob.data.vertices):
            if v.co.z < z_mid:
                sk.data[i].co = v.co + jaw_delta


def _setup_socket(arm, rig, k):
    """Place SOCKET_RightHand_Weapon parented to RightHand, oriented +Y up / +Z barrel in aim pose."""
    aim = ANIM.idle_pose(rig, k, 0.0, aim=True)
    _, P = rig.pose_to_basis(aim)
    hand_rest = arm.data.bones["RightHand"].matrix_local
    hp = P["RightHand"]
    hdir = (hp.to_3x3() @ hand_rest.to_3x3().inverted() @ (
        Vector(arm.data.bones["RightHand"].tail_local) - Vector(arm.data.bones["RightHand"].head_local)
    )).normalized()
    grip = hp.translation + hdir * 0.046 * k + Vector((1, 0, 0)) * 0.010 * k + Vector((0, 0, -0.018 * k))
    desired_aim = Matrix.Translation(grip)
    sock_rest = hand_rest @ hp.inverted() @ desired_aim

    sock = bpy.data.objects.new("SOCKET_RightHand_Weapon", None)
    sock.empty_display_type = "ARROWS"
    sock.empty_display_size = 0.08
    bpy.context.scene.collection.objects.link(sock)
    sock.parent = arm
    sock.parent_type = "BONE"
    sock.parent_bone = "RightHand"
    bpy.context.view_layer.update()
    sock.matrix_world = arm.matrix_world @ sock_rest
    bpy.context.view_layer.update()
    return sock, grip


def build_from_spec(spec_path, repo_root=REPO_ROOT, cache_dir=None, out_blend=None, do_bake=True):
    t0 = time.time()
    spec = load_spec(spec_path)
    name = spec["asset_name"]
    prefix = name[3:] if name.startswith("SK_") else name
    height_m = float(spec.get("height_m", 1.82))
    cache_dir = cache_dir or os.path.join(repo_root, ".cache", "uwp_sources")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.render.fps, sc.render.fps_base = ANIM.FPS, 1.0

    root = bpy.data.objects.new(name, None)
    sc.collection.objects.link(root)

    # 1. Load CC0 MakeHuman base, apply macro + facial/body morphs + facial blendshapes
    print(f"[CHAR] === Building {name} ({height_m:.2f} m) from {os.path.basename(spec_path)} ===")
    mh = MH.MakeHumanBase(cache_dir)
    mh.apply_macro(spec.get("macro", {}))
    n_morphs = mh.apply_morphs(spec.get("morphs", {}))
    # For NPCs with npc_decimate_body, skip shape keys during build so Blender Decimate can optimize body cleanly to <= 25k tris!
    npc_dec = float(spec.get("npc_decimate_body", 1.0))
    shapes = [] if npc_dec < 0.99 else mh.load_blendshape_targets(spec.get("blendshapes"))
    sole_extra = float(spec.get("boot_sole_extra_m", 0.024))
    mh.finalize_scale(target_height_m=height_m, sole_extra_m=sole_extra)
    print(f"[CHAR] morphed hm08 base: {n_morphs} custom targets, {len(shapes)} facial blendshapes, scale_k={mh.scale_k:.4f}")

    # Build full un-culled body mesh in A-pose (needed for clothing surface fitting & 3D skin baking!)
    body_ob, _ = mh.build_body_mesh(f"{name}_Body")
    arm = mh.build_armature(root)
    lm = mh.face_landmarks_bl()

    # 2. Load CC0 eyes (low-poly single-shell eyeball + 1 smooth subsurf -> crisp brown iris, 688 tris!),
    #    eyebrows (eyebrow009 thick masculine), eyelashes, teeth via .mhclo barycentric binding
    eyes_cfg = spec.get("eyes", {})
    eye_mhclo = os.path.join(cache_dir, eyes_cfg.get("mhclo", "mh_eyes/low-poly.mhclo"))
    eyes_ob, _ = mh.load_mhclo(eye_mhclo, f"{name}_Eyes", inherit_shapes=False)
    # Apply 1-level smooth subdivision to low-poly eye sphere for crisp glossy curvature (~688 tris)
    if "low-poly" in eye_mhclo:
        sub = eyes_ob.modifiers.new("Subsurf", "SUBSURF")
        sub.levels = 1
        sub.render_levels = 1
        bpy.ops.object.select_all(action="DESELECT")
        eyes_ob.select_set(True)
        bpy.context.view_layer.objects.active = eyes_ob
        bpy.ops.object.modifier_apply(modifier=sub.name)
        # The low-poly CC0 eyeball maps a two-eye iris/sclera atlas across the whole 0..1 UV
        # square. Frame each eyeball into its own atlas quadrant and scale the iris ~3.5x so it
        # reads as a human iris (raw atlas = three 7 mm irises per eye).
        FACE.frame_eyeballs(eyes_ob)

    # 2b. Brows / lashes: use the CC0 .mhclo cards when the system-asset pack is on disk,
    #     otherwise derive the geometry from the morphed face itself (see face_details.py).
    brow_cfg = spec.get("eyebrows", {})
    lash_cfg = spec.get("eyelashes", {})
    brow_mhclo = os.path.join(cache_dir, brow_cfg.get("mhclo", "makehuman_system_assets/eyebrows/eyebrow009/eyebrow009.mhclo"))
    lash_mhclo = os.path.join(cache_dir, lash_cfg.get("mhclo", "makehuman_system_assets/eyelashes/eyelashes01/eyelashes01.mhclo"))
    brows_ob = lashes_ob = None
    lashes_r_ob = None
    procedural_face = False
    if os.path.isfile(brow_mhclo) and os.path.isfile(lash_mhclo):
        brows_ob, _ = mh.load_mhclo(brow_mhclo, f"{name}_Eyebrows", inherit_shapes=True, offset_normal_m=0.0006)
        lashes_ob, _ = mh.load_mhclo(lash_mhclo, f"{name}_Eyelashes", inherit_shapes=True, offset_normal_m=0.0003)
        print("[CHAR] eyebrows/eyelashes from CC0 MakeHuman cards")
    else:
        procedural_face = True
        # NPCs get fewer brow cards: they keep the same silhouette but stay inside the
        # Characters/SK_NPC triangle budget (TD-009).
        # NPC brow cards are a fixed count, but the band change (face_details.build_brows)
        # means almost no ray is rejected now, so 300 landed every card and pushed Sam to
        # 25 046 tris - over the 25 000 budget. 256 leaves ~700 tris of headroom.
        brow_cards = 1050 if npc_dec >= 0.99 else 256
        brows_ob = FACE.build_brows(body_ob, lm, f"{name}_Eyebrows", card_count=brow_cards)
        lashes_ob, lashes_r_ob = FACE.build_lashes(body_ob, lm, f"{name}_Eyelashes_L", f"{name}_Eyelashes_R")
        print(f"[CHAR] eyebrows/lashes built as hair cards on the morphed face "
              f"({len(brows_ob.data.polygons) // 2} brow quads, "
              f"{len(lashes_ob.data.polygons) // 2}+{len(lashes_r_ob.data.polygons) // 2} lash quads; "
              f"CC0 cards unavailable)")

    teeth_ob = None
    if spec.get("teeth", {}).get("enabled", True):
        teeth_mhclo = os.path.join(cache_dir, "makehuman_system_assets/teeth/teeth_base/teeth_base.mhclo")
        if os.path.isfile(teeth_mhclo):
            teeth_ob, _ = mh.load_mhclo(teeth_mhclo, f"{name}_Teeth", inherit_shapes=True)
            _clean_decimate_teeth(teeth_ob, ratio=float(spec.get("teeth", {}).get("decimate_ratio", 0.20)))
        else:
            teeth_ob = FACE.build_teeth(lm, height_m / 1.82, f"{name}_Teeth")
            print(f"[CHAR] teeth arch generated ({len(teeth_ob.data.polygons)} faces, jawOpen blendshape; CC0 teeth unavailable)")

    # 3. Build fitted separate clothing meshes in A-pose (zero clipping, real seams/folds/rims!)
    outfit = spec.get("outfit", {})
    garment_objs = {}
    tshirt_ob = None
    jacket_ob = None
    jeans_ob = None
    boots_ob = None
    watch_ob = None

    if outfit.get("tshirt", {}).get("enabled", True):
        tshirt_ob = CLOTH.build_tshirt(body_ob, arm, f"{name}_TShirt", style=outfit["tshirt"].get("style", "crew_tshirt"))
        garment_objs["TShirt"] = tshirt_ob
    if outfit.get("jeans", {}).get("enabled", True):
        jeans_ob = CLOTH.build_jeans(body_ob, arm, f"{name}_Jeans", style=outfit["jeans"].get("style", "straight_jeans"))
        garment_objs["Jeans"] = jeans_ob
    if outfit.get("boots", {}).get("enabled", True):
        boots_ob = CLOTH.build_boots(body_ob, arm, f"{name}_Boots")
        garment_objs["Boots"] = boots_ob
    if outfit.get("jacket", {}).get("enabled", True):
        jacket_ob = CLOTH.build_bomber_jacket(body_ob, tshirt_ob, arm, f"{name}_Jacket", style=outfit["jacket"].get("style", "bomber_jacket"))
        garment_objs["Jacket"] = jacket_ob
    if outfit.get("watch", {}).get("enabled", True):
        watch_ob = CLOTH.build_wristwatch(body_ob, arm, f"{name}_Watch")
        garment_objs["Watch"] = watch_ob

    # 4. Transfer region-isolated artist-painted weights from full body_ob BEFORE culling hidden body polygons!
    for part_key, gob in garment_objs.items():
        if part_key == "Watch":
            CLOTH.transfer_weights_from_body(gob, body_ob, arm, rigid_bone="LeftLowerArm", smooth_iters=0)
        else:
            CLOTH.transfer_weights_from_body(
                gob, body_ob, arm,
                allowed_bones=CLOTH.GARMENT_ALLOWED_BONES.get(part_key),
                smooth_iters=2 if part_key == "Boots" else 3,
            )

    # 5. Build layered Hair cards & seamless feathered 3D Beard shell (using exact MakeHuman face landmarks!)
    hair_cfg = spec.get("hair", {})
    hair_ob = HAIR.build_hair(body_ob, arm, lm, f"{name}_Hair", style=hair_cfg.get("style", "skin_fade_crop"), seed=int(hair_cfg.get("seed", 42)))
    beard_cfg = spec.get("beard", {})
    beard_ob = HAIR.build_beard(body_ob, arm, lm, f"{name}_Beard", style=beard_cfg.get("style", "short_boxed_beard"), seed=int(beard_cfg.get("seed", 101)))

    # 6. Build 2K Hero Skin PBR (3D-baked skin fade, beard stubble, left eyebrow scar on exact landmarks!)
    skin_mat = PBR.build_hero_skin_material(body_ob, lm, cache_dir, prefix, spec.get("skin", {}))
    body_ob.data.materials.append(skin_mat)

    # 7. Cull fully occluded body skin faces underneath opaque clothing (saves ~11k tris + eliminates internal clip!)
    culled = CLOTH.cull_occluded_body_faces(
        body_ob, arm,
        has_jacket=jacket_ob is not None,
        has_tshirt=tshirt_ob is not None,
        has_jeans=jeans_ob is not None,
        has_boots=boots_ob is not None,
    )
    print(f"[CHAR] culled {culled} hidden under-clothing body faces")
    if npc_dec < 0.99:
        for ob_d, ratio_d in [(body_ob, npc_dec)] + [(g, min(0.70, npc_dec + 0.08)) for g in garment_objs.values()]:
            if ob_d is not None and not ob_d.data.shape_keys:
                dm = ob_d.modifiers.new("NPCDecimate", "DECIMATE")
                dm.ratio = ratio_d
                bpy.ops.object.select_all(action="DESELECT")
                ob_d.select_set(True)
                bpy.context.view_layer.objects.active = ob_d
                bpy.ops.object.modifier_apply(modifier=dm.name)
                MH.MakeHumanBase._clean_normalize_weights(ob_d, max_inf=4)

    # 8. Cycles High-to-Low Normal & AO Bake + CC0 Poly Haven PBR Compositing for every garment!
    bake_profiles = {
        "TShirt": (0.0014, 34.0, 12),
        "Jacket": (0.0020, 28.0, 12),
        "Jeans": (0.0018, 30.0, 12),
        "Boots": (0.0012, 40.0, 12),
        "Watch": (0.0, 0.0, 0),
    }
    for part_key, gob in garment_objs.items():
        mspec = outfit.get(part_key.lower(), {})
        bnrm, bao = None, None
        fs, ff, smp = bake_profiles.get(part_key, (0.0016, 30.0, 12))
        if do_bake and fs > 0.0 and mspec.get("bake_high_to_low", True):
            t_b = time.time()
            bnrm, bao = CLOTH.bake_high_to_low(
                gob,
                tex_size=int(mspec.get("bake_size", 512)),
                fold_strength=fs,
                fold_freq=ff,
                ao_samples=smp,
                prefix=f"T_{prefix}_{part_key}",
            )
            print(f"[CHAR] Cycles high-to-low baked {part_key} normal+AO ({time.time() - t_b:.1f}s)")
        mat = PBR.build_garment_material(gob, cache_dir, prefix, part_key, mspec, baked_nrm=bnrm, baked_ao=bao)
        gob.data.materials.append(mat)

    # 9. Materials for Eyes, Hair/Beard, Eyebrows/Eyelashes, Teeth (10 materials total = within max_materials!)
    eye_mat = PBR.build_eye_material(
        cache_dir, prefix,
        iris_rel=eyes_cfg.get("iris_texture", "makehuman_system_assets/eyes/materials/brown_eye.png"),
        iris_tint=(tuple(eyes_cfg["iris_tint"]) if eyes_cfg.get("iris_tint") else None),
    )
    eyes_ob.data.materials.append(eye_mat)

    hair_rgb = tuple(hair_cfg.get("color_rgb", [0.038, 0.030, 0.025]))
    hair_mat = PBR.build_hair_material(prefix, hair_rgb=hair_rgb, tex_size=512)
    hair_ob.data.materials.append(hair_mat)
    if beard_ob is not None:
        beard_ob.data.materials.append(hair_mat)

    for lash_side in (lashes_r_ob,):
        if lash_side is not None:
            lash_side.data.materials.clear()
    brow_lash_mat = PBR.build_brows_and_lashes_material(
        cache_dir, prefix,
        eyebrow_png_rel=brow_cfg.get("texture", "makehuman_system_assets/eyebrows/eyebrow009/eyebrow009.png"),
        eyelash_png_rel=lash_cfg.get("texture", "makehuman_system_assets/eyelashes/eyelashes01/eyelashes01.png"),
        brows_ob=brows_ob,
        lashes_ob=lashes_ob,
        hair_rgb=hair_rgb,
        scar_notch=bool(brow_cfg.get("scar_notch", True)),
        lashes_r_ob=lashes_r_ob,
        uv_atlas_ready=procedural_face,
    )
    brows_ob.data.materials.append(brow_lash_mat)
    lashes_ob.data.materials.append(brow_lash_mat)
    if lashes_r_ob is not None:
        lashes_r_ob.data.materials.append(brow_lash_mat)

    if teeth_ob is not None:
        teeth_mat = PBR.build_teeth_material(cache_dir, prefix)
        teeth_ob.data.materials.append(teeth_mat)

    # 10. Parent all meshes to Armature, attach Armature modifier, convert A-pose -> crisp T-pose rest pose!
    all_meshes = [m for m in [body_ob, eyes_ob, brows_ob, lashes_ob, lashes_r_ob, teeth_ob, hair_ob, beard_ob,
                              tshirt_ob, jacket_ob, jeans_ob, boots_ob, watch_ob] if m is not None]
    for ob in all_meshes:
        ob.parent = arm
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.modifiers.new("Armature", "ARMATURE").object = arm

    MH.convert_apose_to_tpose(arm, all_meshes)

    # Final post-T-pose anti-clipping clearance pass so rest-pose layered garments have 0.0% clipping!
    if tshirt_ob is not None:
        CLOTH._enforce_clearance(tshirt_ob, [body_ob], min_clearance=0.0045, passes=2)
    if jeans_ob is not None:
        CLOTH._enforce_clearance(jeans_ob, [body_ob], min_clearance=0.0055, passes=2)
    if jacket_ob is not None:
        CLOTH._enforce_clearance(jacket_ob, [body_ob, tshirt_ob], min_clearance=0.010, passes=3)
        CLOTH._tuck_inner_behind_outer(tshirt_ob, jacket_ob, margin=0.0060, max_probe=0.020)
        CLOTH._tuck_inner_behind_outer(tshirt_ob, jacket_ob, margin=0.0060, max_probe=0.020)
        if not body_ob.data.shape_keys:
            CLOTH._tuck_inner_behind_outer(body_ob, jacket_ob, margin=0.0055, max_probe=0.020)

    # Clean any zero-area degenerate faces on clothing after post-T-pose clearance (0 warnings!)
    for gob in garment_objs.values():
        import bmesh as _bm
        bm_c = _bm.new()
        bm_c.from_mesh(gob.data)
        zf = [f for f in bm_c.faces if f.calc_area() < 1e-9]
        if zf:
            _bm.ops.delete(bm_c, geom=zf, context="FACES")
            le = [e for e in bm_c.edges if not e.link_faces]
            if le:
                _bm.ops.delete(bm_c, geom=le, context="EDGES")
            lv = [v for v in bm_c.verts if not v.link_faces]
            if lv:
                _bm.ops.delete(bm_c, geom=lv, context="VERTS")
            bm_c.to_mesh(gob.data)
            gob.data.update()
        bm_c.free()

    # Post-T-pose ground & exact target-height verification (micro-adjust Z if T-pose changed crown/sole by <1mm)
    all_zs = [v.co.z for ob in all_meshes for v in ob.data.vertices]
    zmin, zmax = min(all_zs), max(all_zs)
    if abs(zmin) > 1e-5:
        for ob in all_meshes:
            for v in ob.data.vertices:
                v.co.z -= zmin
            if ob.data.shape_keys:
                for kb in ob.data.shape_keys.key_blocks:
                    for pt in kb.data:
                        pt.co.z -= zmin
            ob.data.update()
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="EDIT")
        for eb in arm.data.edit_bones:
            if eb.name != "Root":
                eb.head.z -= zmin
                eb.tail.z -= zmin
        bpy.ops.object.mode_set(mode="OBJECT")

    # Re-verify weight normalization & <=4 influences across all meshes
    for ob in all_meshes:
        MH.MakeHumanBase._clean_normalize_weights(ob, max_inf=4)

    # 11. Weapon Socket + Full Animation Set (with CC0 BVH mocap-informed walk rhythm!)
    rig = ANIM.HumanoidRigSolver(arm)
    k_rig = height_m / 1.82
    sock, grip = _setup_socket(arm, rig, k_rig)

    anim_cfg = spec.get("animations", {})
    mocap_bvh = anim_cfg.get("mocap_walk_bvh")
    mocap_walk = None
    if mocap_bvh:
        bvh_abs = os.path.join(cache_dir, mocap_bvh) if not os.path.isabs(mocap_bvh) else mocap_bvh
        mocap_walk = RETARGET.extract_walk_mocap_profile(bvh_abs)
        if mocap_walk:
            print(f"[CHAR] CC0 mocap walk profile loaded from {mocap_walk['source_bvh']}: {mocap_walk}")

    clip_prefix = anim_cfg.get("clip_prefix", f"A_{prefix}_")
    include_p2 = bool(anim_cfg.get("include_p2", True))
    clips, gait_lookup = ANIM.build_all_actions(rig, k_rig, prefix=clip_prefix, include_p2=include_p2, mocap_walk=mocap_walk)

    sliding = {}
    for cname, info in clips.items():
        if info["speed"] > 0:
            P_ = gait_lookup[cname]
            sl = ANIM.measure_sliding(rig, cname, info["speed"], P_.get("dir", ANIM.FWD))
            info["foot_sliding_m"] = round(sl, 4)
            sliding[cname] = sl
            print(f"[CHAR] {cname}: speed={info['speed']} m/s, {info['frames']}f, sliding={sl * 100:.2f} cm, clamp={info['reach_clamp_m']}")
        info["length_s"] = round(info["frames"] / ANIM.FPS, 4)

    # Leave armature in clean Idle frame 0 (rest pose evaluated by uwp via rest_pose())
    idle_act = bpy.data.actions[clip_prefix + "Idle"]
    arm.animation_data.action = idle_act
    if idle_act.slots:
        arm.animation_data.action_slot = idle_act.slots[0]
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    sc.frame_start, sc.frame_end = 0, 60
    sc.frame_set(0)

    # Attach character spec metadata on root object so uwp knows concept art reference & layering!
    root["uw_character_spec"] = os.path.relpath(os.path.abspath(spec_path), repo_root)
    if spec.get("concept_art", {}).get("turnaround"):
        root["uw_concept_turnaround"] = spec["concept_art"]["turnaround"]
    if spec.get("concept_art", {}).get("head"):
        root["uw_concept_head"] = spec["concept_art"]["head"]

    # 12. Save .blend and anim_report.json
    cat = spec.get("category", "Characters")
    blend_path = out_blend or os.path.join(repo_root, "Blender", "Source", cat, name, f"{name}.blend")
    os.makedirs(os.path.dirname(blend_path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True)

    tris = {}
    for ob in all_meshes:
        ob.data.calc_loop_triangles()
        tris[ob.name] = len(ob.data.loop_triangles)
    total_tris = sum(tris.values())

    out_dir = os.path.join(repo_root, "Assets", cat, name)
    os.makedirs(out_dir, exist_ok=True)
    rep = {
        "asset": name,
        "status": f"v2 production pipeline (T-PIPE-03, spec {os.path.basename(spec_path)})",
        "height_m": round(max(v.co.z for ob in all_meshes for v in ob.data.vertices), 4),
        "triangles": tris,
        "triangles_total": total_tris,
        "materials": sorted({s.material.name for ob in all_meshes for s in ob.material_slots if s.material}),
        "bones": [b.name for b in arm.data.bones],
        "bone_count": len(arm.data.bones),
        "blendshapes": shapes,
        "blendshape_count": len(shapes),
        "rest_pose": "T-pose (baked from MakeHuman CC0 hm08 A-pose)",
        "front": "Blender -Y = Godot +Z",
        "root_motion": "none (in place); Root bone has no keys",
        "mocap_walk_profile": mocap_walk,
        "fps": ANIM.FPS,
        "clips": clips,
        "socket": {
            "name": "SOCKET_RightHand_Weapon",
            "parent_bone": "RightHand",
            "convention": "local +Y up, +Z barrel in Godot (= Blender local +Z up, -Y barrel); identity orientation in Aim_Pistol_Idle",
            "aim_pose_position_godot": [round(grip.x, 4), round(grip.z, 4), round(-grip.y, 4)],
        },
        "max_foot_sliding_m": round(max(sliding.values()) if sliding else 0.0, 4),
        "build_seconds": round(time.time() - t0, 1),
    }
    if not out_blend:
        with open(os.path.join(out_dir, f"{name}.anim_report.json"), "w") as f:
            json.dump(rep, f, indent=2)
            f.write("\n")

    print(f"[CHAR] DONE {name}: {total_tris} tris across {len(all_meshes)} meshes, {len(rep['materials'])} mats, "
          f"{len(shapes)} blendshapes, max sliding {rep['max_foot_sliding_m']*100:.2f} cm ({rep['build_seconds']}s)")
    print(f"[CHAR] per-mesh tris: {tris}")
    print(f"[CHAR] saved -> {blend_path}")
    return rep


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(description="Build a realistic character .blend from a JSON/YAML spec.")
    ap.add_argument("--spec", required=True, help="Character spec JSON/YAML path")
    ap.add_argument("--repo", default=REPO_ROOT)
    ap.add_argument("--cache", default=None)
    ap.add_argument("--out-blend", default=None, help="Override output .blend path (for staging v2 before replacing v1)")
    ap.add_argument("--no-bake", action="store_true", help="Skip Cycles high-to-low garment baking (fast iteration)")
    args = ap.parse_args(argv)
    build_from_spec(args.spec, repo_root=args.repo, cache_dir=args.cache, out_blend=args.out_blend, do_bake=not args.no_bake)


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    os._exit(0)
