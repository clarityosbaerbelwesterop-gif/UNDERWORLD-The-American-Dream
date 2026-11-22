"""PBR texture compositing, 3D-space Cycles skin-detail baking, CC0 Poly Haven material blending & Godot setup.

Uses exact morphed MakeHuman face landmarks (`lm`) so skin fades, beard contours, and eyebrow scars
land with sub-millimetre precision on every character. Uses RNM normal blending for Cycles high-to-low
baked garment maps + CC0 Poly Haven PBR micro-textures, and rich concept-art-matched grading.
"""
import math
import os
import tempfile
import zlib

import bpy
import numpy as np

from underworld_pipeline.characters import procedural_assets as PROC


def load_image_np(path, size=None, non_color=False):
    img = bpy.data.images.load(path, check_existing=False)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    if size is not None and (img.size[0] != size[0] or img.size[1] != size[1]):
        img.scale(size[0], size[1])
    w, h = img.size[0], img.size[1]
    arr = np.array(img.pixels[:], dtype=np.float32).reshape((h, w, 4))
    bpy.data.images.remove(img)
    return arr


def _pil():
    """Pillow, if importable. It is the only reliable encoder here (see pack_np_image)."""
    try:
        from PIL import Image as PILImage
        return PILImage
    except Exception:
        return None


def pack_np_image(name, arr_rgba, non_color=False, file_format="PNG", jpeg_quality=90):
    """Encode a float array to a packed Blender image.

    Why this does not use bpy's save_render any more: saving the image buffer through the scene
    (image.save_render(tmp, scene=sc)) wrote a *broken* file whenever the sky/background or the
    film needed to be evaluated - the packed skin diffuse came out as a black field with a few
    correctly coloured islands (mean 0.05 instead of 0.57), and every character rendered with
    black blotches over the parts of the body that sampled it. The bytes on disk were fine, only
    the packed copy was wrong, so no renderer-side setting could explain it.

    Encoding with Pillow from the same numpy buffer is deterministic and independent of any scene
    state. Blender is only used to hold the packed image afterwards.

    Colour management: the buffer holds *display-referred* values (the pipeline composes the maps
    that way), so the file gets written as-is and the image is tagged sRGB for colour maps /
    Non-Color for data maps.
    """
    arr = np.asarray(arr_rgba, dtype=np.float32)
    # A NaN anywhere in a map renders as pure black and is invisible in the .json reports, so it
    # must never reach the packer. It is a bug in the compositor, not "bad input": say so loudly.
    n_nan = int(np.isnan(arr).sum())
    if n_nan:
        print(f"[TEX][WARN] {name}: {n_nan} NaN values in the source array - replaced by 0. "
              f"This is a fault in the map compositor, not in the asset.")
        arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)
    arr = np.clip(arr, 0.0, 1.0)
    h, w = arr.shape[:2]
    has_alpha = (arr.shape[2] == 4) and (file_format == "PNG")
    if arr.shape[2] == 3:
        rgba = np.ones((h, w, 4), dtype=np.float32)
        rgba[:, :, :3] = arr
    else:
        rgba = arr
    rgba = np.ascontiguousarray(rgba)

    img = bpy.data.images.new(name, w, h, alpha=has_alpha, float_buffer=False)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(rgba.ravel())

    ext = ".jpg" if file_format == "JPEG" else ".png"
    with tempfile.TemporaryDirectory(prefix="uwp_tex_") as td:
        tmp = os.path.join(td, name + ext)
        PILImage = _pil()
        if PILImage is not None:
            u8 = np.clip(rgba * 255.0 + 0.5, 0.0, 255.0).astype(np.uint8)
            # Blender's pixel buffer is bottom-up; PNG/JPEG are top-down.
            u8 = u8[::-1]
            pil_img = PILImage.fromarray(u8[:, :, :4] if has_alpha else u8[:, :, :3],
                                         mode="RGBA" if has_alpha else "RGB")
            if file_format == "JPEG":
                pil_img.save(tmp, format="JPEG", quality=int(jpeg_quality), subsampling=0)
            else:
                pil_img.save(tmp, format="PNG", compress_level=6)
        else:
            # Fallback: let Blender encode, but never through the scene's display transform.
            sc = bpy.context.scene
            prev = (sc.render.image_settings.file_format, sc.render.image_settings.color_mode,
                    sc.render.image_settings.quality, sc.view_settings.view_transform,
                    sc.view_settings.look, sc.view_settings.exposure, sc.view_settings.gamma)
            sc.render.image_settings.file_format = file_format
            sc.render.image_settings.color_mode = "RGBA" if has_alpha else "RGB"
            sc.render.image_settings.quality = jpeg_quality
            sc.view_settings.view_transform = "Standard"
            sc.view_settings.look = "None"
            sc.view_settings.exposure = 0.0
            sc.view_settings.gamma = 1.0
            img.save_render(tmp, scene=sc)
            (sc.render.image_settings.file_format, sc.render.image_settings.color_mode,
             sc.render.image_settings.quality, sc.view_settings.view_transform,
             sc.view_settings.look, sc.view_settings.exposure,
             sc.view_settings.gamma) = prev

        bpy.data.images.remove(img)
        packed = bpy.data.images.load(tmp, check_existing=False)
        packed.name = name
        if non_color:
            packed.colorspace_settings.name = "Non-Color"
        packed.pack()
        return packed


def tile_array(arr, repeat_x, repeat_y, out_size):
    h, w, c = arr.shape
    ys = (np.linspace(0, repeat_y * h, out_size, endpoint=False).astype(np.int32)) % h
    xs = (np.linspace(0, repeat_x * w, out_size, endpoint=False).astype(np.int32)) % w
    return arr[np.ix_(ys, xs)]


def blend_normals_rnm(n1_rgb, n2_rgb, strength1=1.0, strength2=1.0):
    t = n1_rgb * 2.0 - 1.0
    t[:, :, :2] *= strength1
    t[:, :, 2] = np.maximum(t[:, :, 2], 0.05)
    t /= np.maximum(np.linalg.norm(t, axis=2, keepdims=True), 1e-6)
    t[:, :, 2] += 1.0

    u = n2_rgb * 2.0 - 1.0
    u[:, :, :2] *= strength2
    u[:, :, 2] = np.maximum(u[:, :, 2], 0.05)
    u /= np.maximum(np.linalg.norm(u, axis=2, keepdims=True), 1e-6)
    u[:, :, :2] *= -1.0

    dot = np.sum(t * u, axis=2, keepdims=True)
    r = t * dot / np.maximum(t[:, :, 2:3], 1e-6) - u
    r /= np.maximum(np.linalg.norm(r, axis=2, keepdims=True), 1e-6)
    return np.clip(r * 0.5 + 0.5, 0.0, 1.0).astype(np.float32)


def find_polyhaven_maps(cache_dir, asset_id):
    d = os.path.join(cache_dir, "textures", asset_id)
    if not os.path.isdir(d):
        return {}
    out = {}
    for fn in sorted(os.listdir(d)):
        low = fn.lower()
        fp = os.path.join(d, fn)
        if "_diff_" in low or "_albedo_" in low:
            out["diff"] = fp
        elif "_nor_gl_" in low:
            out["nor"] = fp
        elif "_rough_" in low:
            out["rough"] = fp
        elif "_ao_" in low:
            out["ao"] = fp
        elif "_arm_" in low:
            out["arm"] = fp
        elif "_metal_" in low:
            out["metal"] = fp
    return out


def make_pbr_material(name, albedo_img, normal_img=None, orm_img=None,
                      base_color=(1, 1, 1, 1), roughness=0.7, metallic=0.0,
                      normal_strength=1.0, alpha_mode=None, sss_weight=0.0, sss_scale=0.008,
                      coat_weight=0.0, coat_roughness=0.08, specular_ior=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic

    if sss_weight > 0.0 and "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = sss_weight
        if "Subsurface Scale" in bsdf.inputs:
            bsdf.inputs["Subsurface Scale"].default_value = sss_scale
        if "Subsurface Radius" in bsdf.inputs:
            bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.20)
    if specular_ior is not None and "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = specular_ior
    if coat_weight > 0.0 and "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat_weight
        bsdf.inputs["Coat Roughness"].default_value = coat_roughness

    if albedo_img is not None:
        tex_d = nt.nodes.new("ShaderNodeTexImage")
        tex_d.image = albedo_img
        tex_d.location = (-450, 260)
        nt.links.new(tex_d.outputs["Color"], bsdf.inputs["Base Color"])
        if alpha_mode:
            nt.links.new(tex_d.outputs["Alpha"], bsdf.inputs["Alpha"])
            if hasattr(mat, "blend_method"):
                mat.blend_method = alpha_mode
            if alpha_mode == "CLIP" and hasattr(mat, "alpha_threshold"):
                mat.alpha_threshold = 0.35

    if orm_img is not None:
        tex_orm = nt.nodes.new("ShaderNodeTexImage")
        tex_orm.image = orm_img
        tex_orm.location = (-560, -40)
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        sep.location = (-280, -40)
        nt.links.new(tex_orm.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
        gltf_grp = bpy.data.node_groups.get("glTF Settings") or bpy.data.node_groups.new("glTF Settings", "ShaderNodeTree")
        if "Occlusion" not in [i.name for i in gltf_grp.interface.items_tree if i.in_out == "INPUT"]:
            gltf_grp.interface.new_socket(name="Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
        gnode = nt.nodes.new("ShaderNodeGroup")
        gnode.node_tree = gltf_grp
        gnode.location = (0, -240)
        nt.links.new(sep.outputs["Red"], gnode.inputs["Occlusion"])

    if normal_img is not None:
        tex_n = nt.nodes.new("ShaderNodeTexImage")
        tex_n.image = normal_img
        tex_n.location = (-520, -340)
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = normal_strength
        nmap.location = (-240, -340)
        nt.links.new(tex_n.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    return mat


def _bake_3d_position_uv(ob, size=1024):
    """Bake object-space (X, Y, Z) coordinates of `ob` onto its UV map via Cycles Emit bake."""
    sc = bpy.context.scene
    prev_engine = sc.render.engine
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 1
    sc.cycles.use_denoising = False

    pos_img = bpy.data.images.new("UW_PosBakeTmp", size, size, alpha=False, float_buffer=True)
    pos_img.colorspace_settings.name = "Non-Color"

    saved_mats = [s.material for s in ob.material_slots]
    mat = bpy.data.materials.new("UW_PosBakeMatTmp")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    vadd = nt.nodes.new("ShaderNodeVectorMath")
    vadd.operation = "ADD"
    vadd.inputs[1].default_value = (2.0, 2.0, 2.0)
    vscale = nt.nodes.new("ShaderNodeVectorMath")
    vscale.operation = "SCALE"
    vscale.inputs["Scale"].default_value = 0.25
    nt.links.new(geo.outputs["Position"], vadd.inputs[0])
    nt.links.new(vadd.outputs["Vector"], vscale.inputs[0])
    nt.links.new(vscale.outputs["Vector"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])

    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = pos_img
    tex.select = True
    nt.nodes.active = tex

    ob.data.materials.clear()
    ob.data.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    sc.render.bake.use_selected_to_active = False
    sc.render.bake.margin = 4
    bpy.ops.object.bake(type="EMIT")

    arr = np.array(pos_img.pixels[:], dtype=np.float32).reshape((size, size, 4))[:, :, :3]
    pos_xyz = arr * 4.0 - 2.0

    ob.data.materials.clear()
    for m in saved_mats:
        ob.data.materials.append(m)
    bpy.data.materials.remove(mat)
    bpy.data.images.remove(pos_img)
    sc.render.engine = prev_engine
    return pos_xyz


# ==============================================================================
# 2K HERO SKIN PBR: CC0 PHOTO SKIN + EXACT 3D SKIN FADE + BEARD STUBBLE + SCAR
# ==============================================================================
def build_hero_skin_material(body_ob, lm, cache_dir, asset_prefix, skin_spec):
    tex_size = int(skin_spec.get("texture_size", 2048))
    rng = np.random.default_rng(int(skin_spec.get("seed", 77)))

    skin_diff_path = os.path.join(cache_dir, skin_spec.get(
        "base_diffuse",
        "skins02/skins/toigo_light_skin_male_bronze/young_lightskinned_male_diffuse_Bronze.png",
    ))
    skin_nrm_path = os.path.join(cache_dir, skin_spec.get(
        "base_normal",
        "skins02/skins/mindfront_aksel_skin/Aksel_Skin_NRM.png",
    ))
    skin_spec_path = os.path.join(cache_dir, skin_spec.get(
        "base_spec",
        "skins02/skins/mindfront_aksel_skin/Aksel_Skin_SPEC.png",
    ))
    tint = np.array(skin_spec.get("tint_rgb", [0.94, 0.85, 0.76]), dtype=np.float32)
    gamma = float(skin_spec.get("gamma", 1.08))

    if os.path.isfile(skin_diff_path):
        diff = load_image_np(skin_diff_path, (tex_size, tex_size), non_color=False)[:, :, :3]
        nrm = load_image_np(skin_nrm_path, (tex_size, tex_size), non_color=True)[:, :, :3] if os.path.isfile(skin_nrm_path) else np.full((tex_size, tex_size, 3), [0.5, 0.5, 1.0], dtype=np.float32)
        if os.path.isfile(skin_spec_path):
            sp = load_image_np(skin_spec_path, (tex_size, tex_size), non_color=True)[:, :, 0]
            rough = np.clip(0.74 - sp * 0.28, 0.42, 0.84)
        else:
            rough = np.full((tex_size, tex_size), 0.52, dtype=np.float32)
        diff = np.clip((diff ** gamma) * tint[None, None, :], 0.0, 1.0)
    else:
        # CC0 photo-skin pack not on disk (host unreachable) -> build the maps ourselves
        proc_sz = min(tex_size, 1024)
        diff, nrm, rough = PROC.skin_maps(proc_sz, int(skin_spec.get("seed", 77)))
        # Our generator already applies the tint; keep the spec tint only as a light grade.
        diff = np.clip(diff ** (gamma / 1.08), 0.0, 1.0)
        if proc_sz != tex_size:
            idx = np.linspace(0, proc_sz - 1, tex_size).astype(np.int32)
            diff = diff[np.ix_(idx, idx)]
            nrm = nrm[np.ix_(idx, idx)]
            rough = rough[np.ix_(idx, idx)]
        print(f"[PBR] procedural skin maps ({tex_size}px, seed {skin_spec.get('seed', 77)}) - CC0 photo skin unavailable")

    # Bake 3D coordinates onto UV layout
    bake_sz = min(tex_size, 1024)
    pos_s = _bake_3d_position_uv(body_ob, size=bake_sz)
    if bake_sz != tex_size:
        idx = np.linspace(0, bake_sz - 1, tex_size).astype(np.int32)
        pos = pos_s[np.ix_(idx, idx)]
    else:
        pos = pos_s
    X, Y, Z = pos[:, :, 0], pos[:, :, 1], pos[:, :, 2]
    eye_z = float(lm["eye_z"])
    brow_z = float(lm["brow_z"])
    mouth_z = float(lm["mouth_z"])
    upper_lip_z = float(lm["upper_lip_z"])
    lower_lip_z = float(lm["lower_lip_z"])
    chin_z = float(lm["chin_z"])
    nose_y, nose_z = float(lm["nose_tip"].y), float(lm["nose_tip"].z)
    head_cy = float(lm["head_center"].y)
    eye_y = float(lm["eye_front_y"])
    crown_z = float(lm["crown_z"])
    face_h = float(lm["face_h"])

    # High-resolution natural hair follicle stipple
    noise = rng.random((tex_size, tex_size), dtype=np.float32)
    n2 = np.repeat(np.repeat(noise[::2, ::2], 2, axis=0), 2, axis=1)
    follicle = np.clip(0.60 * noise + 0.40 * n2, 0.0, 1.0)

    hair_col = np.array(skin_spec.get("hair_color_rgb", [0.036, 0.028, 0.024]), dtype=np.float32)
    ao = np.ones((tex_size, tex_size), dtype=np.float32)

    # 1. Barber Skin Fade on sides & back (matches CA_Jason_Head_v01.jpg profile cleanly!)
    fade_cfg = skin_spec.get("skin_fade")
    if fade_cfg:
        # Smooth barber fade: begins around ear-mid (eye_z - 0.015), reaches full density at parietal ridge (brow_z + 0.035)
        back_dip = np.clip((Y - head_cy) / 0.11, 0.0, 1.0) * 0.042
        fade_bot = eye_z - 0.018 - back_dip
        fade_top = brow_z + face_h * 0.145 - back_dip * 0.55
        fade_t = np.clip((Z - fade_bot) / np.maximum(fade_top - fade_bot, 1e-4), 0.0, 1.0) ** 1.15

        # Crisp straight forehead hairline + sharp temple corner dropping into sideburns!
        hairline_z = brow_z + face_h * 0.118
        # On forehead (|X| < 0.046): cut cleanly above hairline_z
        forehead_mask = np.clip((Z - hairline_z) / 0.005, 0.0, 1.0)
        # On sides/temples (|X| >= 0.046): clean vertical temple edge around Y > eye_y + 0.032
        temple_y = eye_y + 0.030 + np.clip((np.abs(X) - 0.045) / 0.035, 0.0, 1.0) * 0.024
        side_mask = np.clip((Y - temple_y) / 0.006, 0.0, 1.0)
        is_forehead = np.clip((0.052 - np.abs(X)) / 0.010, 0.0, 1.0) * (Y < head_cy - 0.01).astype(np.float32)
        region_mask = np.maximum(forehead_mask * is_forehead, side_mask * (1.0 - is_forehead))

        # Strictly keep ears skin-colored (ears stick out laterally at |X| > 0.072 around Y ~ head_cy)
        ear_dist2 = ((np.abs(X) - 0.082) / 0.018) ** 2 + ((Z - (eye_z - 0.012)) / 0.036) ** 2 + ((Y - (head_cy + 0.004)) / 0.028) ** 2
        ear_clear = 1.0 - np.exp(-ear_dist2)

        fade_mask = fade_t * region_mask * ear_clear * (Z > lm["neck_z"] + 0.015).astype(np.float32)
        # Crown under-hair completely darkened so zero skin shines between hair cards
        crown_fill = np.clip((Z - (brow_z + face_h * 0.098)) / 0.014, 0.0, 1.0) * np.clip((Y - (eye_y + 0.004)) / 0.006, 0.0, 1.0)
        fade_mask = np.maximum(fade_mask, crown_fill * 0.96)

        stipple = np.clip(fade_mask * (0.72 + 0.45 * follicle), 0.0, 0.96)
        diff = diff * (1.0 - stipple[:, :, None]) + hair_col[None, None, :] * stipple[:, :, None]
        rough = np.clip(rough + stipple * 0.22, 0.25, 0.92)
        ao = np.clip(ao - stipple * 0.14, 0.5, 1.0)

    # 1b. Lips: geometry mask first, colour later
    # The beard (step 2) must end at the vermilion border instead of around a rectangle, so the
    # shape is computed before the stubble and only painted afterwards.
    # Landmarks: lower_lip_z < mouth_z < upper_lip_z. Each lobe is a half-ellipse that reaches zero
    # exactly at its border (sin^p profile). A clipped superellipse - the previous version - has a
    # *plateau* with a hard edge, which renders as a flat dark block painted on the face.
    lip_col = np.array(skin_spec.get("lip_rgb", [0.42, 0.21, 0.19]), dtype=np.float32)
    on_front_of_face = (Y < head_cy - 0.035).astype(np.float32)
    lip_half_w = 0.0230
    # Lobe shape lives in PROC.lip_mask() so it can be unit-tested without Blender.
    lip_m = PROC.lip_mask(X, Z, mouth_z, upper_lip_z, lower_lip_z, half_w=lip_half_w) * on_front_of_face
    lip_mask = np.clip(lip_m, 0.0, 1.0)
    # Lower lip is the fuller, slightly lighter one; the upper lip turns under and reads darker.
    lip_tint = np.where((Z < mouth_z)[:, :, None], lip_col * 1.12, lip_col * 0.92)
    lip_mix = np.clip(lip_mask * 0.88, 0.0, 0.94)[:, :, None]

    # 2. Lush, groomed short beard & mustache stubble on skin (exact CA_Jason_Head_v01.jpg full chin+jaw+mustache!)
    beard_cfg = skin_spec.get("beard_stubble")
    if beard_cfg and beard_cfg.get("density", 0.0) > 0.0:
        dens = float(beard_cfg.get("density", 0.80))
        ax = np.abs(X)

        # Groomed diagonal cheek line: rises softly from mouth corner up to sideburn in front of ear
        cheek_top = mouth_z + 0.008 + np.clip((ax - 0.026) / 0.044, 0.0, 1.0) * 0.038
        below_cheek = np.clip((cheek_top - Z) / 0.015, 0.0, 1.0)
        # Clean neck line wrapping ALL the way under the chin bottom (z=chin_z-0.025) and ONLY rising behind throat (Y > -0.098)!
        neck_cut = (chin_z - 0.032) + np.clip((Y - (nose_y + 0.068)) / 0.040, 0.0, 1.0) * 0.032
        above_neck = np.clip((Z - neck_cut) / 0.012, 0.0, 1.0)
        # Strictly IN FRONT of the ears!
        in_front_of_ears = np.clip(((head_cy - 0.010) - Y) / 0.014, 0.0, 1.0)

        # Full mustache with softly curved upper border (organic curve, not boxy rectangle!)
        lip_center_z = mouth_z - 0.004
        m_top_curve = (nose_z - 0.004) - 0.006 * ((ax / 0.038) ** 2)
        m_z = np.clip((Z - (lip_center_z + 0.007)) / 0.004, 0.0, 1.0) * np.clip((m_top_curve - Z) / 0.007, 0.0, 1.0)
        m_x = np.clip((0.039 - ax) / 0.010, 0.0, 1.0)
        mustache = m_z * m_x * (Y < nose_y + 0.055).astype(np.float32)

        # Mouth corner connectors linking mustache smoothly into jaw/chin beard!
        corner_conn = (
            np.exp(-(((ax - 0.029) / 0.009) ** 2))
            * np.clip((Z - (lip_center_z - 0.012)) / 0.005, 0.0, 1.0)
            * np.clip(((lip_center_z + 0.014) - Z) / 0.005, 0.0, 1.0)
            * (Y < nose_y + 0.055).astype(np.float32)
        )

        # Lip cut-out: same lobed shape that the vermilion is painted with, slightly dilated so the
        # stubble stops on the lip border. The old cut was an axis-aligned superellipse, which left a
        # pale rectangle of bare skin around the mouth (visible as a pale band in the face render).
        lip_cut = np.clip(lip_mask * 1.18, 0.0, 1.0)
        # Subtle soul patch flanking skin patches below lower lip (center |X|<0.010 stays dark soul patch, chin below z=lip_center_z-0.022 stays full beard!)
        soul_gap = np.exp(-(((Z - (lip_center_z - 0.015)) / 0.008) ** 2 + ((ax - 0.016) / 0.0065) ** 2))

        # Sideburn tapered softly upward into skin fade
        sb_fade = np.clip((eye_z + 0.025 - Z) / 0.025, 0.0, 1.0) * np.clip((Z - mouth_z) / 0.015, 0.0, 1.0)
        sideburn = (
            np.exp(-(((ax - 0.067) / 0.010) ** 2))
            * np.exp(-(((Y - (head_cy - 0.020)) / 0.010) ** 2))
            * sb_fade
        )

        bmask = np.maximum(below_cheek * above_neck * in_front_of_ears, mustache)
        bmask = np.maximum(bmask, corner_conn * 0.92)
        bmask = np.maximum(bmask, sideburn * 0.65)
        bmask = np.clip(bmask * (1.0 - lip_cut * 0.99) * (1.0 - soul_gap * 0.72), 0.0, 1.0)

        # Natural dense dark trimmed beard look (soft organic follicle transition!)
        bstip = np.clip(bmask * dens * (0.58 + 0.52 * follicle), 0.0, 0.86)
        diff = diff * (1.0 - bstip[:, :, None]) + hair_col[None, None, :] * bstip[:, :, None]
        rough = np.clip(rough + bstip * 0.22, 0.25, 0.92)
        nrm[:, :, 0] = np.clip(nrm[:, :, 0] + (follicle - 0.5) * bstip * 0.14, 0.0, 1.0)
        nrm[:, :, 1] = np.clip(nrm[:, :, 1] + (noise - 0.5) * bstip * 0.14, 0.0, 1.0)

    # 2b. Lip colour on top of the stubble pass (so the vermilion is never tinted by beard)
    diff = diff * (1.0 - lip_mix) + lip_tint * lip_mix
    rough = np.clip(rough - lip_mask * 0.07, 0.44, 0.92)

    # mouth line: a narrow crease exactly at mouth_z
    # The opening: a lens, not a bar. It must be widest in the middle, taper to nothing at the
    # corners and stay inside the vermilion - the previous version ran 26.5 mm wide (3 mm past the
    # lips) at constant strength and read as a black rectangle painted across the mouth.
    # ... and it must stop short of the commissures, otherwise the taper reads as a slit that is
    # cut into the beard rather than as lips meeting.
    mouth_line = (np.exp(-((Z - mouth_z) / 0.0012) ** 2)
                  * np.clip(1.0 - (np.abs(X) / (lip_half_w * 0.88)) ** 2, 0.0, 1.0) ** 0.9
                  * on_front_of_face)
    diff = diff * (1.0 - mouth_line[:, :, None] * 0.30)
    nrm[:, :, 1] = np.clip(nrm[:, :, 1] - mouth_line * 0.16, 0.0, 1.0)

    # nose tip / cheeks a touch warmer (capillary flush), ears slightly pink as well
    nose_glow = np.exp(-(((Z - nose_z) / 0.014) ** 2 + ((np.abs(X) - 0.0) / 0.020) ** 2)) * on_front_of_face
    cheek_glow = np.exp(-(((np.abs(X) - 0.043) / 0.024) ** 2 + ((Z - (eye_z - 0.028)) / 0.022) ** 2)) * on_front_of_face
    warm = np.clip(nose_glow * 0.55 + cheek_glow * 0.35, 0.0, 1.0)
    diff[:, :, 0] = np.clip(diff[:, :, 0] * (1.0 + 0.10 * warm), 0.0, 1.0)
    diff[:, :, 1] = np.clip(diff[:, :, 1] * (1.0 - 0.03 * warm), 0.0, 1.0)
    diff[:, :, 2] = np.clip(diff[:, :, 2] * (1.0 - 0.06 * warm), 0.0, 1.0)

    # 3. Distinctive diagonal scar slicing across Jason's LEFT eyebrow (anatomical +X, exact brow_z!)
    scar_cfg = skin_spec.get("eyebrow_scar")
    if scar_cfg:
        sx0 = float(scar_cfg.get("x_m", 0.039))
        sz0 = brow_z + float(scar_cfg.get("z_offset_m", 0.001))
        ang = math.radians(float(scar_cfg.get("angle_deg", 64.0)))
        slen = float(scar_cfg.get("length_m", 0.021))
        swid = float(scar_cfg.get("width_m", 0.0017))

        dx = X - sx0
        dz = Z - sz0
        along = dx * math.cos(ang) + dz * math.sin(ang)
        across = -dx * math.sin(ang) + dz * math.cos(ang)
        on_front = ((Y < head_cy - 0.03) & (X > 0.015)).astype(np.float32)
        scar_mask = np.exp(-((across / swid) ** 2)) * np.clip(1.0 - (np.abs(along) / (slen * 0.5)) ** 4, 0.0, 1.0) * on_front

        scar_col = np.array([0.85, 0.68, 0.58], dtype=np.float32)
        diff = diff * (1.0 - scar_mask[:, :, None] * 0.72) + scar_col[None, None, :] * (scar_mask[:, :, None] * 0.72)
        rough = np.clip(rough - scar_mask * 0.12, 0.25, 0.90)
        scar_grad = np.clip(-across / max(swid, 1e-5), -1.0, 1.0) * scar_mask
        nrm[:, :, 0] = np.clip(nrm[:, :, 0] + scar_grad * 0.30, 0.0, 1.0)

    orm = np.stack([ao, rough, np.zeros_like(rough)], axis=2)
    img_d = pack_np_image(f"T_{asset_prefix}_Skin_D", diff, non_color=False, file_format="JPEG", jpeg_quality=92)
    # Pack skin normal at 1024x1024 (keeps crisp pore detail while cutting GLB LFS footprint by ~6 MB!)
    nrm_sz = min(tex_size, 1024)
    if nrm_sz != tex_size:
        nidx = np.linspace(0, tex_size - 1, nrm_sz).astype(np.int32)
        nrm_out = nrm[np.ix_(nidx, nidx)]
    else:
        nrm_out = nrm
    img_n = pack_np_image(f"T_{asset_prefix}_Skin_N", nrm_out, non_color=True, file_format="PNG")
    img_orm = pack_np_image(f"T_{asset_prefix}_Skin_ORM", orm, non_color=True, file_format="JPEG", jpeg_quality=90)

    return make_pbr_material(
        f"M_{asset_prefix}_Skin",
        albedo_img=img_d,
        normal_img=img_n,
        orm_img=img_orm,
        sss_weight=float(skin_spec.get("sss_weight", 0.18)),
        sss_scale=float(skin_spec.get("sss_scale", 0.008)),
        normal_strength=0.75,
    )


# ==============================================================================
# CLOTHING PBR COMPOSITOR (CC0 Poly Haven PBR + Cycles High-to-Low Normal & AO)
# ==============================================================================
def build_garment_material(ob, cache_dir, asset_prefix, part_name, mat_spec, baked_nrm=None, baked_ao=None):
    tex_size = int(mat_spec.get("texture_size", 1024))
    ph_id = mat_spec.get("polyhaven_id")
    tile_uv = float(mat_spec.get("tile", 4.0))
    tint = np.array(mat_spec.get("tint_rgb", [1.0, 1.0, 1.0]), dtype=np.float32)
    lift = float(mat_spec.get("gamma", 1.0))
    rough_bias = float(mat_spec.get("roughness_bias", 0.0))
    rough_scale = float(mat_spec.get("roughness_scale", 1.0))
    metallic = float(mat_spec.get("metallic", 0.0))

    maps = find_polyhaven_maps(cache_dir, ph_id) if ph_id else {}
    if "diff" in maps:
        raw_d = load_image_np(maps["diff"], None, non_color=False)[:, :, :3]
        diff = tile_array(raw_d, tile_uv, tile_uv, tex_size)
    else:
        # No CC0 Poly Haven set on disk -> generate a seamless weave/grain for this family.
        gen_sz = min(tex_size, 512)
        diff_g, nrm_g, rough_g, ao_g = PROC.fabric_maps(str(ph_id), gen_sz, seed=zlib.crc32(str(ph_id).encode()) % 10007)
        if gen_sz != tex_size:
            gi = np.linspace(0, gen_sz - 1, tex_size).astype(np.int32)
            diff = diff_g[np.ix_(gi, gi)]
        else:
            diff = diff_g
        maps = dict(maps)
        maps["_proc"] = (nrm_g, rough_g, ao_g, gen_sz)

    if "nor" in maps:
        raw_n = load_image_np(maps["nor"], None, non_color=True)[:, :, :3]
        micro_n = tile_array(raw_n, tile_uv, tile_uv, tex_size)
    elif "_proc" in maps:
        nrm_g = maps["_proc"][0]
        gi = np.linspace(0, nrm_g.shape[0] - 1, tex_size).astype(np.int32)
        micro_n = nrm_g[np.ix_(gi, gi)]
    else:
        micro_n = np.full((tex_size, tex_size, 3), [0.5, 0.5, 1.0], dtype=np.float32)

    if "_proc" in maps and "rough" not in maps and "arm" not in maps:
        r_g = maps["_proc"][1]
        gi = np.linspace(0, r_g.shape[0] - 1, tex_size).astype(np.int32)
        rough = r_g[np.ix_(gi, gi)]
    elif "rough" in maps:
        raw_r = load_image_np(maps["rough"], None, non_color=True)[:, :, 0:1]
        rough = tile_array(raw_r, tile_uv, tile_uv, tex_size)[:, :, 0]
    elif "arm" in maps:
        raw_a = load_image_np(maps["arm"], None, non_color=True)[:, :, 1:2]
        rough = tile_array(raw_a, tile_uv, tile_uv, tex_size)[:, :, 0]
    else:
        rough = np.full((tex_size, tex_size), 0.72, dtype=np.float32)

    if "ao" in maps:
        raw_ao = load_image_np(maps["ao"], None, non_color=True)[:, :, 0:1]
        ao = tile_array(raw_ao, tile_uv, tile_uv, tex_size)[:, :, 0]
    elif "_proc" in maps:
        a_g = maps["_proc"][2]
        gi = np.linspace(0, a_g.shape[0] - 1, tex_size).astype(np.int32)
        ao = a_g[np.ix_(gi, gi)]
    else:
        ao = np.ones((tex_size, tex_size), dtype=np.float32)

    # Normalize & color-grade base diffuse accurately so dark source textures don't crush to black!
    desat = float(mat_spec.get("desaturate", 0.0))
    if desat > 0.0:
        lum = 0.299 * diff[:, :, 0:1] + 0.587 * diff[:, :, 1:2] + 0.114 * diff[:, :, 2:3]
        diff = diff * (1.0 - desat) + lum * desat
    if abs(lift - 1.0) > 1e-3:
        diff = np.power(np.clip(diff, 1e-5, 1.0), lift)
    diff = np.clip(diff * tint[None, None, :], 0.0, 1.0)

    if baked_nrm is not None:
        if baked_nrm.shape[0] != tex_size:
            idx = np.linspace(0, baked_nrm.shape[0] - 1, tex_size).astype(np.int32)
            bn = baked_nrm[np.ix_(idx, idx)]
        else:
            bn = baked_nrm
        nrm = blend_normals_rnm(
            bn, micro_n,
            strength1=float(mat_spec.get("bake_normal_strength", 0.75)),
            strength2=float(mat_spec.get("micro_normal_strength", 0.85)),
        )
    else:
        nrm = micro_n

    if baked_ao is not None:
        if baked_ao.shape[0] != tex_size:
            idx = np.linspace(0, baked_ao.shape[0] - 1, tex_size).astype(np.int32)
            bao = baked_ao[np.ix_(idx, idx)]
        else:
            bao = baked_ao
        ao = np.clip(ao * (0.65 + 0.35 * bao), 0.25, 1.0)
        diff = np.clip(diff * (0.82 + 0.18 * bao[:, :, None]), 0.0, 1.0)

    rough = np.clip(rough * rough_scale + rough_bias, 0.14, 0.96)
    met_map = np.full((tex_size, tex_size), metallic, dtype=np.float32)

    # 3D-projected tailored garment details (ribbed bomber hem/collar/cuffs + zipper, denim wash/seams, boot rubber sole!)
    zone_mode = mat_spec.get("zone_mode")
    if zone_mode in ("boot_sole", "bomber_trim", "denim_wash"):
        pos_s = _bake_3d_position_uv(ob, size=min(tex_size, 512))
        idx = np.linspace(0, pos_s.shape[0] - 1, tex_size).astype(np.int32)
        pos = pos_s[np.ix_(idx, idx)]
        X, Y, Z = pos[:, :, 0], pos[:, :, 1], pos[:, :, 2]

        if zone_mode == "boot_sole":
            sole_m = np.clip((0.0255 - Z) / 0.0022, 0.0, 1.0)
            sole_col = np.array([0.055, 0.048, 0.044], dtype=np.float32)
            diff = diff * (1.0 - sole_m[:, :, None]) + sole_col[None, None, :] * sole_m[:, :, None]
            rough = rough * (1.0 - sole_m) + 0.88 * sole_m
            # Subtle lighter worn-leather highlights on toe cap & vamp
            toe_wear = np.clip((Z - 0.030) / 0.035, 0.0, 1.0) * np.clip((0.075 - Z) / 0.035, 0.0, 1.0)
            diff = np.clip(diff * (1.0 + 0.16 * toe_wear[:, :, None]), 0.0, 1.0)

        elif zone_mode == "bomber_trim":
            pts_z = np.array([v.co.z for v in ob.data.vertices])
            z_lo, z_hi = float(pts_z.min()), float(pts_z.max())
            # Ribbed matte dark-brown knit hem (bottom 5.5cm) & bomber collar (top 4.5cm)
            hem_m = np.clip((z_lo + 0.055 - Z) / 0.008, 0.0, 1.0)
            col_m = np.clip((Z - (z_hi - 0.045)) / 0.008, 0.0, 1.0)
            # Ribbed wrist cuffs: radial distance from A-pose sleeve cuff ends (straight wrap around wrists!)
            pts_all = np.array([v.co[:] for v in ob.data.vertices])
            l_end = pts_all[int(np.argmax(pts_all[:, 0]))]
            r_end = pts_all[int(np.argmin(pts_all[:, 0]))]
            dl = np.sqrt((X - l_end[0]) ** 2 + (Z - l_end[2]) ** 2)
            dr = np.sqrt((X - r_end[0]) ** 2 + (Z - r_end[2]) ** 2)
            cuff_m = np.maximum(
                np.clip((0.075 - dl) / 0.012, 0.0, 1.0),
                np.clip((0.075 - dr) / 0.012, 0.0, 1.0),
            ) * (np.abs(X) > 0.25).astype(np.float32)
            # Crisp metallic front zipper edge along |X| ~ 0.072 on front (Y < -0.06)
            zip_m = np.clip((0.007 - np.abs(np.abs(X) - 0.073)) / 0.0025, 0.0, 1.0) * (Y < -0.06).astype(np.float32) * (Z > z_lo + 0.008).astype(np.float32)
            # Subtle back yoke topstitch seam line & front welt pocket dark seam lines
            yoke_line = np.exp(-(((Z - (z_hi - 0.14)) / 0.003) ** 2)) * (Y > 0.04).astype(np.float32)
            # Ribbing modulation on knit zones
            knit_m = np.maximum(np.maximum(hem_m, col_m), cuff_m) * (1.0 - zip_m)
            rib_pat = 0.85 + 0.15 * np.cos(X * 320.0 + Y * 320.0)
            knit_col = np.array([0.085, 0.056, 0.040], dtype=np.float32) * rib_pat[:, :, None]
            diff = diff * (1.0 - knit_m[:, :, None]) + knit_col * knit_m[:, :, None]
            rough = rough * (1.0 - knit_m) + 0.90 * knit_m
            # Darken back yoke seam gently
            diff = np.clip(diff * (1.0 - 0.25 * yoke_line[:, :, None]), 0.0, 1.0)
            # Brushed dark steel zipper teeth
            teeth_pat = 0.72 + 0.28 * np.sin(Z * 1200.0)
            zip_col = np.array([0.46, 0.43, 0.40], dtype=np.float32) * teeth_pat[:, :, None]
            diff = diff * (1.0 - zip_m[:, :, None]) + zip_col * zip_m[:, :, None]
            rough = rough * (1.0 - zip_m) + 0.30 * zip_m
            met_map = np.maximum(met_map, zip_m * 0.88)

        elif zone_mode == "denim_wash":
            pts_z = np.array([v.co.z for v in ob.data.vertices])
            z_lo, z_hi = float(pts_z.min()), float(pts_z.max())
            # Authentic worn denim thigh/knee fade (slightly lighter & warmer along front thighs/knees!)
            thigh_fade = (
                np.exp(-(((Z - (z_lo + (z_hi - z_lo) * 0.56)) / 0.22) ** 2))
                * np.exp(-(((np.abs(X) - 0.115) / 0.055) ** 2))
                * (Y < -0.01).astype(np.float32)
            )
            diff = np.clip(diff * (1.0 + 0.28 * thigh_fade[:, :, None]), 0.0, 1.0)
            # Subtle warm copper/gold jeans topstitching on waistband & back pocket borders
            wb_stitch = np.exp(-(((Z - (z_hi - 0.032)) / 0.0025) ** 2))
            bp_border = (
                (np.exp(-(((Z - (z_hi - 0.08)) / 0.0028) ** 2)) + np.exp(-(((Z - (z_hi - 0.20)) / 0.0028) ** 2)))
                * ((np.abs(X) > 0.035) & (np.abs(X) < 0.135) & (Y > 0.05)).astype(np.float32)
            )
            stitch = np.clip(wb_stitch + bp_border, 0.0, 1.0)
            st_col = np.array([0.45, 0.33, 0.18], dtype=np.float32)
            diff = diff * (1.0 - stitch[:, :, None] * 0.55) + st_col[None, None, :] * (stitch[:, :, None] * 0.55)

    orm = np.stack([ao, rough, met_map], axis=2)
    img_d = pack_np_image(f"T_{asset_prefix}_{part_name}_D", diff, non_color=False, file_format="JPEG", jpeg_quality=90)
    # Pack clothing normal at 512-1024 (configurable via normal_size; default 512 for compact LFS < 12 MB GLB)
    n_sz = int(mat_spec.get("normal_size", min(tex_size, 512)))
    if n_sz != tex_size:
        nidx = np.linspace(0, tex_size - 1, n_sz).astype(np.int32)
        nrm_out = nrm[np.ix_(nidx, nidx)]
    else:
        nrm_out = nrm
    img_n = pack_np_image(f"T_{asset_prefix}_{part_name}_N", nrm_out, non_color=True, file_format="PNG")
    img_orm = pack_np_image(f"T_{asset_prefix}_{part_name}_ORM", orm, non_color=True, file_format="JPEG", jpeg_quality=88)

    return make_pbr_material(
        f"M_{asset_prefix}_{part_name}",
        albedo_img=img_d,
        normal_img=img_n,
        orm_img=img_orm,
        normal_strength=float(mat_spec.get("normal_strength", 0.95)),
    )


# ==============================================================================
# HAIR / BEARD STRAND ATLAS + THICK MASCULINE EYEBROW (LEFT SCAR ONLY!) + EYES + TEETH
# ==============================================================================
def build_hair_material(asset_prefix, hair_rgb=(0.038, 0.030, 0.025), tex_size=512):
    rng = np.random.default_rng(31415)
    u = np.linspace(0.0, 1.0, tex_size, dtype=np.float32)
    v = np.linspace(0.0, 1.0, tex_size, dtype=np.float32)
    U, V = np.meshgrid(u, v)

    col_u = (U * 4.0) % 1.0
    col_id = np.floor(U * 4.0).astype(np.int32)
    v_card = np.clip((V - 0.22) / 0.78, 0.0, 1.0)

    strand_alpha = np.zeros((tex_size, tex_size), dtype=np.float32)
    strand_shade = np.ones((tex_size, tex_size), dtype=np.float32)
    strand_nx = np.zeros((tex_size, tex_size), dtype=np.float32)

    for c in range(4):
        cmask = (col_id == c)
        for _ in range(48):
            x0 = float(rng.uniform(0.06, 0.94))
            w_s = float(rng.uniform(0.018, 0.044))
            wave_a = float(rng.uniform(-0.04, 0.04))
            wave_f = float(rng.uniform(2.0, 5.0))
            tip_len = float(rng.uniform(0.62, 0.99))
            bright = float(rng.uniform(0.65, 1.40))

            cx = x0 + wave_a * np.sin(v_card * wave_f)
            w_cur = w_s * (1.0 - 0.65 * np.clip(v_card / tip_len, 0.0, 1.0))
            dist = (col_u - cx) / np.maximum(w_cur, 1e-4)
            s_a = np.exp(-(dist ** 2) * 2.1) * np.clip((tip_len - v_card) / 0.16, 0.0, 1.0)
            s_a *= np.clip(v_card / 0.10 + 0.30, 0.0, 1.0)
            s_a = np.where(cmask, s_a, 0.0)

            better = s_a > strand_alpha
            strand_shade = np.where(better, bright, strand_shade)
            strand_nx = np.where(better, np.clip(-dist * 0.5, -1.0, 1.0), strand_nx)
            strand_alpha = np.maximum(strand_alpha, s_a)

    # Dense directional strand texture for sculpted crop volume (V < 0.22)
    root_wave = np.sin(U * 380.0 + 3.0 * np.sin(V * 95.0)) * 0.5 + 0.5
    root_fine = np.sin(U * 920.0 - V * 140.0) * 0.5 + 0.5
    root_tex = 0.55 + 0.35 * root_wave + 0.22 * root_fine
    root_nx = np.cos(U * 380.0 + 3.0 * np.sin(V * 95.0)) * 0.65
    alpha = np.where(V < 0.22, 1.0, np.clip(strand_alpha * 1.45, 0.0, 1.0))
    shade = np.where(V < 0.22, root_tex, strand_shade * (0.65 + 0.45 * v_card))
    nx_comb = np.where(V < 0.22, root_nx, strand_nx)

    base = np.array(hair_rgb, dtype=np.float32)[None, None, :]
    rgb = np.clip(base * shade[:, :, None], 0.0, 1.0)
    rgba = np.concatenate([rgb, alpha[:, :, None]], axis=2)

    nrm = np.zeros((tex_size, tex_size, 3), dtype=np.float32)
    nrm[:, :, 0] = np.clip(nx_comb * 0.45 + 0.5, 0.0, 1.0)
    nrm[:, :, 1] = 0.52
    nrm[:, :, 2] = 0.90

    img_d = pack_np_image(f"T_{asset_prefix}_Hair_D", rgba, non_color=False, file_format="PNG")
    img_n = pack_np_image(f"T_{asset_prefix}_Hair_N", nrm, non_color=True, file_format="PNG")
    return make_pbr_material(
        f"M_{asset_prefix}_Hair",
        albedo_img=img_d,
        normal_img=img_n,
        roughness=0.74,
        normal_strength=0.65,
        alpha_mode="HASHED",
        specular_ior=0.10,
    )


def _atlas_to_quadrants(arr, cols, rows, size):
    """Nearest-neighbour resize of a procedural cell atlas to size x size (keeps cell edges)."""
    h, w = arr.shape[:2]
    ys = np.linspace(0, h - 1, size).astype(np.int32)
    xs = np.linspace(0, w - 1, size).astype(np.int32)
    return arr[np.ix_(ys, xs)]


def build_brows_and_lashes_material(cache_dir, asset_prefix, eyebrow_png_rel, eyelash_png_rel,
                                    brows_ob, lashes_ob, hair_rgb=(0.036, 0.028, 0.024), scar_notch=True,
                                    lashes_r_ob=None, uv_atlas_ready=False):
    """Pack CC0 MakeHuman eyebrows (bottom half V=[0..0.5]) + delicate eyelashes (top half V=[0.5..1.0])
    into ONE 512x1024 RGBA atlas so eyebrows AND natural eyelashes render cleanly within 10 materials!"""
    brow_fp = os.path.join(cache_dir, eyebrow_png_rel)
    lash_fp = os.path.join(cache_dir, eyelash_png_rel)
    have_cards = os.path.isfile(brow_fp) and os.path.isfile(lash_fp)
    if have_cards:
        brow_arr = load_image_np(brow_fp, (512, 512), non_color=False)
    else:
        # CC0 eyebrow/eyelash cards unavailable. The procedural path does NOT need an atlas:
        # every hair card gets its own cell, so a single strand per cell is what we build.
        seed_base = abs(zlib.crc32(str(asset_prefix).encode())) % 9999
        brow_arr = PROC.strand_atlas(1024, 16, 16, seed_base + 1, hair_rgb=hair_rgb, kind="brow")
        lash_arr_proc = PROC.strand_atlas(512, 8, 8, seed_base + 2, hair_rgb=hair_rgb, kind="lash")
        brow_arr = _atlas_to_quadrants(brow_arr, 16, 16, 512)
        lash_arr_proc = _atlas_to_quadrants(lash_arr_proc, 8, 8, 512)
    base = np.array(hair_rgb, dtype=np.float32)[None, None, :]
    if have_cards:
        lum = 0.299 * brow_arr[:, :, 0:1] + 0.587 * brow_arr[:, :, 1:2] + 0.114 * brow_arr[:, :, 2:3]
        brow_arr[:, :, :3] = np.clip(base * (0.60 + 0.95 * lum), 0.0, 1.0)
        brow_arr[:, :, 3] = np.clip(brow_arr[:, :, 3] * 1.40, 0.0, 1.0)

    if scar_notch:
        u = np.linspace(0.0, 1.0, 512, dtype=np.float32)
        v = np.linspace(0.0, 1.0, 512, dtype=np.float32)
        U, V = np.meshgrid(u, v)
        dx, dy = U - 0.62, V - 0.60
        ang = math.radians(64.0)
        across = -dx * math.sin(ang) + dy * math.cos(ang)
        notch = np.exp(-((across / 0.024) ** 2)) * (V > 0.42).astype(np.float32)
        brow_arr[:, :, 3] *= (1.0 - notch * 0.96)

    if have_cards:
        lash_arr = load_image_np(lash_fp, (512, 512), non_color=False)
        lash_arr[:, :, :3] = np.clip(base * 0.85, 0.0, 1.0)
        # Keep masculine lashes subtle & natural (not heavy mascara!)
        lash_arr[:, :, 3] = np.clip(lash_arr[:, :, 3] * 0.72, 0.0, 1.0)
    else:
        lash_arr = lash_arr_proc.copy()
        lash_arr[:, :, :3] = np.clip(base * 0.85, 0.0, 1.0)
        lash_arr[:, :, 3] = np.clip(lash_arr[:, :, 3], 0.0, 1.0)

    atlas = np.concatenate([brow_arr, lash_arr], axis=0)  # (1024, 512, 4): bottom=brows, top=lashes
    if not uv_atlas_ready:
        # .mhclo cards carry their own 0..1 UVs -> remap them into the two atlas halves
        if brows_ob and brows_ob.data.uv_layers:
            for l in brows_ob.data.uv_layers[0].data:
                l.uv[1] = l.uv[1] * 0.5
        for ob_l in (lashes_ob, lashes_r_ob):
            if ob_l and ob_l.data.uv_layers:
                for l in ob_l.data.uv_layers[0].data:
                    l.uv[1] = 0.5 + l.uv[1] * 0.5

    img = pack_np_image(f"T_{asset_prefix}_BrowsLashes_D", atlas, non_color=False, file_format="PNG")
    return make_pbr_material(f"M_{asset_prefix}_BrowsLashes", albedo_img=img, roughness=0.70,
                             alpha_mode="HASHED", specular_ior=0.20)


def build_eye_material(cache_dir, asset_prefix, iris_rel="makehuman_system_assets/eyes/materials/brown_eye.png", iris_tint=(0.62, 0.44, 0.32)):
    fp = os.path.join(cache_dir, iris_rel)
    if not os.path.isfile(fp):
        fp = os.path.join(cache_dir, "mh_eyes/brown_eye.png")
    arr = load_image_np(fp, (512, 512), non_color=False)
    if iris_tint is not None:
        # Optional hue grade of the iris disc only (sclera untouched).
        lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
        is_iris = np.clip((0.72 - lum) / 0.22, 0.0, 1.0)
        tint = np.array(iris_tint, dtype=np.float32)[None, None, :]
        arr[:, :, :3] = arr[:, :, :3] * (1.0 - is_iris[:, :, None]) + np.clip(arr[:, :, :3] * tint, 0.0, 1.0) * is_iris[:, :, None]
    else:
        print("[PBR] eye material uses the CC0 iris texture un-tinted (natural brown)")
    img = pack_np_image(f"T_{asset_prefix}_Eyes_D", arr[:, :, :3], non_color=False, file_format="JPEG", jpeg_quality=92)
    return make_pbr_material(
        f"M_{asset_prefix}_Eyes",
        albedo_img=img,
        roughness=0.14,
        coat_weight=0.55,
        coat_roughness=0.05,
    )


def build_teeth_material(cache_dir, asset_prefix):
    fp = os.path.join(cache_dir, "makehuman_system_assets/teeth/teeth_base/teeth.png")
    if os.path.isfile(fp):
        arr = load_image_np(fp, (512, 512), non_color=False)[:, :, :3]
        img = pack_np_image(f"T_{asset_prefix}_Teeth_D", arr, non_color=False, file_format="JPEG", jpeg_quality=88)
    else:
        img = None
    return make_pbr_material(
        f"M_{asset_prefix}_Teeth",
        albedo_img=img,
        base_color=(0.86, 0.82, 0.74, 1.0),
        roughness=0.22,
        coat_weight=0.5,
    )
