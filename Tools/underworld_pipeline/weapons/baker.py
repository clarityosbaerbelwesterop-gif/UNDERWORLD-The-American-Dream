"""High-to-low Cycles CPU baker for hard-surface weapons (one shared UV atlas / one material).

Passes per part (selected-to-active, HP -> LP, only the pair visible so moving parts don't bake onto each
other): base colour, roughness, metallic, AO (EMIT of labelled HP shader outputs, see hs_materials) and a
tangent-space NORMAL bake. post() packs glTF maps: D (sRGB), N (OpenGL/Blender tangent space), ORM
(R = AO, G = roughness, B = metallic) with edge dilation for mip safety.
"""
import math
import time

import bpy
import numpy as np

from . import hs_materials as HM


def unwrap(lps, angle_deg, margin):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in lps:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = lps[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle_deg), island_margin=0.0, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")


def _img(name, res, color):
    im = bpy.data.images.new(name, res, res, alpha=False, float_buffer=not color)
    im.colorspace_settings.name = "sRGB" if color else "Non-Color"
    return im


def bake_all(pairs, res, samples_ao=48, cage=0.0015, max_ray=0.004):
    """pairs: {node: (hp_ob, lp_ob)}. Returns dict of numpy arrays (H, W, 4) + timings."""
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.use_denoising = False
    sc.render.bake.margin = 6
    sc.render.bake.margin_type = "EXTEND"
    ims = {k: _img(f"UW_bake_{k}", res, k == "albedo") for k in ("albedo", "normal", "rough", "metal", "ao")}
    tmat = bpy.data.materials.new("UW_BakeTarget")
    tmat.use_nodes = True
    tex = tmat.node_tree.nodes.new("ShaderNodeTexImage")
    saved = {}
    for nm, (hp, lp) in pairs.items():
        saved[nm] = [s.material for s in lp.material_slots]
        lp.data.materials.clear()
        lp.data.materials.append(tmat)
    times = {}

    def run(key, typ, samples, emit_key=None, **kw):
        tex.image = ims[key]
        tmat.node_tree.nodes.active = tex
        sc.cycles.samples = samples
        t0 = time.time()
        for i, (nm, (hp, lp)) in enumerate(pairs.items()):
            swaps = []
            if emit_key:
                for mat in {s.material for s in hp.material_slots}:
                    nt = mat.node_tree
                    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
                    prev = out.inputs["Surface"].links[0].from_socket
                    em = nt.nodes.new("ShaderNodeEmission")
                    nt.links.new(HM.bake_socket(mat, emit_key), em.inputs["Color"])
                    nt.links.new(em.outputs[0], out.inputs["Surface"])
                    swaps.append((nt, out, prev, em))
            for o in sc.objects:
                o.select_set(False)
                o.hide_render = o not in (hp, lp)
            hp.select_set(True)
            lp.select_set(True)
            bpy.context.view_layer.objects.active = lp
            for attr in ("visible_camera", "visible_diffuse", "visible_glossy", "visible_shadow", "visible_transmission"):
                setattr(lp, attr, False)
            bpy.ops.object.bake(type=typ, use_selected_to_active=True, cage_extrusion=cage, max_ray_distance=max_ray,
                                margin=6, use_clear=(i == 0), **kw)
            for attr in ("visible_camera", "visible_diffuse", "visible_glossy", "visible_shadow", "visible_transmission"):
                setattr(lp, attr, True)
            for nt, out, prev, em in swaps:
                nt.links.new(prev, out.inputs["Surface"])
                nt.nodes.remove(em)
        times[key] = round(time.time() - t0, 1)
        print(f"[WEAPON] baked {key} in {times[key]} s", flush=True)

    run("albedo", "EMIT", 4, emit_key="albedo")
    run("rough", "EMIT", 4, emit_key="rough")
    run("metal", "EMIT", 4, emit_key="metal")
    run("normal", "NORMAL", 8, normal_space="TANGENT")
    run("ao", "EMIT", samples_ao, emit_key="ao")
    for o in sc.objects:
        o.hide_render = False
    out = {k: px(im) for k, im in ims.items()}
    for nm, (hp, lp) in pairs.items():
        lp.data.materials.clear()
        for m in saved[nm]:
            lp.data.materials.append(m)
    for im in ims.values():
        bpy.data.images.remove(im)
    bpy.data.materials.remove(tmat)
    return out, times


def px(im):
    a = np.empty(im.size[0] * im.size[1] * 4, np.float32)
    im.pixels.foreach_get(a)
    return a.reshape(im.size[1], im.size[0], 4)


def dilate(arr, mask, it=16):
    """Grow island colours into empty texels (mip/bilinear safety)."""
    arr, mask = arr.copy(), mask.copy()
    for _ in range(it):
        acc = np.zeros_like(arr)
        cnt = np.zeros(mask.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            m = np.roll(mask, (dy, dx), (0, 1))
            acc += np.roll(arr, (dy, dx), (0, 1)) * m[..., None]
            cnt += m
        grow = (~mask) & (cnt > 0)
        arr[grow] = acc[grow] / cnt[grow][:, None]
        mask = mask | grow
    return arr


def post(maps, cavity=0.25):
    """-> (D rgb, N rgb, ORM rgb, coverage). Bake images are bottom-up (Blender pixel order) like pack_np_image expects."""
    alb, nrm, rgh, met, ao = (maps[k] for k in ("albedo", "normal", "rough", "metal", "ao"))
    mask = nrm[..., 2] > 0.05
    ao1 = np.clip(ao[..., 0], 0, 1)
    ao_c = np.clip(0.30 + 0.70 * ao1, 0, 1)
    d = alb[..., :3] * (1.0 - cavity + cavity * ao1)[..., None]       # light cavity darkening in base colour
    orm = np.stack([ao_c, rgh[..., 0], met[..., 0]], -1)
    out = []
    for arr, flat in ((d, None), (nrm[..., :3], (0.5, 0.5, 1.0)), (orm, None)):
        a = dilate(arr, mask)
        empty = ~(mask | (a.sum(-1) > 0))
        a[empty] = flat if flat else a[mask].mean(0)
        out.append(np.clip(a, 0, 1))
    return out[0], out[1], out[2], float(mask.mean())
