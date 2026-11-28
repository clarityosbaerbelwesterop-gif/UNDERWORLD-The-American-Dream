"""WPN_Pistol_01 (REQ-GP02-PISTOL, T-ART-05) - procedural hard-surface build with HP -> LP Cycles bake, Bot 2.

  blender -b --factory-startup --python Blender/Scripts/wpn_pistol_01/build_wpn_pistol_01.py -- [--res 2048] [--ao-samples 48] [--no-bake]
-> Blender/Source/Weapons/WPN_Pistol_01/WPN_Pistol_01.blend
   Blender/Source/Weapons/WPN_Pistol_01/textures/T_WPN_Pistol_01_{D,N,ORM}.png  (ORM: R=AO, G=rough, B=metal)

Conventions (TD-004 / REQ): 1 BU = 1 m; barrel along Blender -Y (Godot +Z), up +Z (Godot +Y); gun's left = +X.
Origin = grip point (centre of the grip where index/middle fingers wrap) = SOCKET_Grip; it sits on SK_Jason's
SOCKET_RightHand_Weapon with identity transform. Nodes: Frame, Slide, Magazine (+ uwp LODs/collision),
SOCKET_Muzzle (+Z out = Blender -Y), SOCKET_Eject (local +X out of the right-side port), SOCKET_Grip.
Actions (object level, one slot per animated object): A_WPN_Pistol_01_Fire (3 f = 0.1 s),
A_WPN_Pistol_01_Reload (48 f = 1.6 s), A_WPN_Pistol_01_Empty (1 f, slide locked back).
"""
import argparse
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pistol_geo as G    # noqa: E402
import pistol_mats as PM  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
NAME = "WPN_Pistol_01"
SRC_DIR = os.path.join(REPO, "Blender", "Source", "Weapons", NAME)
TEX_DIR = os.path.join(SRC_DIR, "textures")
GRIP = Vector((0.0, 0.0225, -0.0245))     # grip point in modelling coords -> origin
SLIDE_TRAVEL = 0.028
MAG_AXIS = Vector((0.0, math.sin(G.RAKE), -math.cos(G.RAKE)))
# frames inside the 48-frame reload (30 fps); A_Jason_Reload_Pistol (SK_Jason v1) drops the mag at ~f6 and
# seats the new one at ~f33, racks at f38-42 - final sync belongs to Jason v2 (T-PIPE-03)
RELOAD = {"mag_release": 4, "mag_out": 9, "mag_insert_start": 28, "mag_seated": 33, "slide_back": 38,
          "slide_release": 41, "end": 48}


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, default=2048)
    ap.add_argument("--ao-samples", type=int, default=48)
    ap.add_argument("--no-bake", action="store_true", help="reuse existing textures")
    return ap.parse_args(argv)


def build_set(hp, M):
    parts = {"Frame": G.frame(hp, M), "Slide": G.slide(hp, M), "Magazine": G.magazine(hp, M)}
    out = {}
    for nm, objs in parts.items():
        ob = G.join(objs, nm + ("_HP" if hp else ""))
        ob.data.transform(Matrix.Translation(-GRIP))
        G.finish(ob, hp)
        out[nm] = ob
    return out


def unwrap(lps, margin=0.006):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in lps:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = lps[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(G.LP_SHARP_DEG + 1), island_margin=0.0, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")


def new_img(name, res, color):
    im = bpy.data.images.new(name, res, res, alpha=False, float_buffer=not color)
    im.colorspace_settings.name = "sRGB" if color else "Non-Color"
    return im


def bake_all(hps, lps, res, ao_samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.render.bake.margin = 4
    sc.render.bake.margin_type = "EXTEND"
    ims = {k: new_img(f"bake_{k}", res, k == "albedo") for k in ("albedo", "normal", "rough", "metal", "ao")}
    bm = bpy.data.materials.new("BakeTarget")
    bm.use_nodes = True
    tex = bm.node_tree.nodes.new("ShaderNodeTexImage")
    for lp in lps.values():
        lp.data.materials.clear()
        lp.data.materials.append(bm)
    times = {}

    def run(key, typ, samples, emit_key=None, **kw):
        tex.image = ims[key]
        bm.node_tree.nodes.active = tex
        sc.cycles.samples = samples
        t0 = time.time()
        for i, nm in enumerate(("Frame", "Slide", "Magazine")):
            hp, lp = hps[nm], lps[nm]
            swaps = []
            if emit_key:
                for mat in {s.material for s in hp.material_slots}:
                    nt = mat.node_tree
                    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
                    prev = out.inputs["Surface"].links[0].from_socket
                    em = nt.nodes.new("ShaderNodeEmission")
                    nt.links.new(PM.bake_socket(mat, emit_key), em.inputs["Color"])
                    nt.links.new(em.outputs[0], out.inputs["Surface"])
                    swaps.append((nt, out, prev, em))
            for o in bpy.context.scene.objects:
                o.select_set(False)
                o.hide_render = o not in (hp, lp)
            hp.select_set(True)
            lp.select_set(True)
            bpy.context.view_layer.objects.active = lp
            # the LP must not occlude/shadow the HP (coincident surfaces)
            for attr in ("visible_camera", "visible_diffuse", "visible_glossy", "visible_shadow", "visible_transmission"):
                setattr(lp, attr, False)
            bpy.ops.object.bake(type=typ, use_selected_to_active=True, cage_extrusion=0.0015, max_ray_distance=0.004,
                                margin=4, use_clear=(i == 0), **kw)
            for attr in ("visible_camera", "visible_diffuse", "visible_glossy", "visible_shadow", "visible_transmission"):
                setattr(lp, attr, True)
            for nt, out, prev, em in swaps:
                nt.links.new(prev, out.inputs["Surface"])
                nt.nodes.remove(em)
        times[key] = round(time.time() - t0, 1)
        print(f"[PISTOL] baked {key} in {times[key]} s", flush=True)

    run("albedo", "EMIT", 4, emit_key="albedo")
    run("rough", "EMIT", 4, emit_key="rough")
    run("metal", "EMIT", 4, emit_key="metal")
    run("normal", "NORMAL", 8, normal_space="TANGENT")
    run("ao", "EMIT", ao_samples, emit_key="ao")
    for o in bpy.context.scene.objects:
        o.hide_render = False
    return ims, times


def px(im):
    a = np.empty(im.size[0] * im.size[1] * 4, np.float32)
    im.pixels.foreach_get(a)
    return a.reshape(im.size[1], im.size[0], 4)


def dilate(arr, mask, it=24):
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


def write_png(path, arr, color):
    h, w = arr.shape[:2]
    im = bpy.data.images.new(os.path.basename(path)[:-4], w, h, alpha=False)
    im.colorspace_settings.name = "sRGB" if color else "Non-Color"
    rgba = np.concatenate([np.clip(arr[..., :3], 0, 1), np.ones((h, w, 1), np.float32)], axis=2)
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)


def post(ims):
    os.makedirs(TEX_DIR, exist_ok=True)
    alb, nrm, rgh, met, ao = (px(ims[k]) for k in ("albedo", "normal", "rough", "metal", "ao"))
    mask = nrm[..., 2] > 0.05            # baked texels (normal blue channel > 0)
    ao_c = np.clip(0.25 + 0.75 * ao[..., 0], 0, 1)  # keep AO from crushing small recesses to black
    orm = np.stack([ao_c, rgh[..., 0], met[..., 0]], -1)
    for nm, arr, col in (("T_WPN_Pistol_01_D", alb[..., :3], True), ("T_WPN_Pistol_01_N", nrm[..., :3], False),
                         ("T_WPN_Pistol_01_ORM", orm, False)):
        out = dilate(arr, mask)
        out[~(mask | (out.sum(-1) > 0))] = (0.5, 0.5, 1.0) if nm.endswith("_N") else out[mask].mean(0)
        write_png(os.path.join(TEX_DIR, nm + ".png"), out, col)
    return float(mask.mean())


def game_material():
    m = bpy.data.materials.new("M_WPN_Pistol_01")
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes["Principled BSDF"]
    L = nt.links.new

    def tex(nm, color):
        im = bpy.data.images.load(os.path.join(TEX_DIR, nm + ".png"))
        im.colorspace_settings.name = "sRGB" if color else "Non-Color"
        im.filepath = "//textures/" + nm + ".png"
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = im
        return t
    td, tn, to = tex("T_WPN_Pistol_01_D", True), tex("T_WPN_Pistol_01_N", False), tex("T_WPN_Pistol_01_ORM", False)
    L(td.outputs["Color"], bs.inputs["Base Color"])
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    L(tn.outputs["Color"], nmap.inputs["Color"])
    L(nmap.outputs["Normal"], bs.inputs["Normal"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    L(to.outputs["Color"], sep.inputs["Color"])
    L(sep.outputs["Green"], bs.inputs["Roughness"])
    L(sep.outputs["Blue"], bs.inputs["Metallic"])
    g = bpy.data.node_groups.get("glTF Material Output") or bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
    if not g.interface.items_tree:
        g.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    gn = nt.nodes.new("ShaderNodeGroup")
    gn.node_tree = g
    L(sep.outputs["Red"], gn.inputs["Occlusion"])
    m.use_backface_culling = True
    return m


# ------------------------------------------------------------------ animation (object-level, slotted actions)
def _fcurves(act):
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                yield from cb.fcurves


def make_action(name, frame_end, keys_by_obj, objs):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    for ob in objs:
        ad = ob.animation_data or ob.animation_data_create()
        ad.action = act
        ad.action_slot = act.slots.new(id_type="OBJECT", name=ob.name)
        for f, loc, sc in keys_by_obj[ob.name]:
            ob.location = loc
            ob.scale = (sc, sc, sc)
            ob.keyframe_insert("location", frame=f)
            ob.keyframe_insert("scale", frame=f)
    for fc in _fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT" if fc.data_path == "scale" else "BEZIER"
    act.use_frame_range = True
    act.frame_start, act.frame_end = 0, frame_end
    act.use_cyclic = False
    act["loop"] = False
    return act


def build_actions(slide, mag):
    Z = Vector((0, 0, 0))
    back = Vector((0, SLIDE_TRAVEL, 0))
    drop = MAG_AXIS * 0.12
    R = RELOAD
    spec = {
        "A_WPN_Pistol_01_Fire": (3, {"Slide": [(0, Z, 1), (1, back, 1), (3, Z, 1)], "Magazine": [(0, Z, 1), (3, Z, 1)]}),
        "A_WPN_Pistol_01_Reload": (48, {
            "Slide": [(0, Z, 1), (R["slide_back"], Z, 1), (R["slide_back"] + 2, back, 1), (R["slide_release"], back, 1),
                      (R["slide_release"] + 1, Z, 1), (48, Z, 1)],
            "Magazine": [(0, Z, 1), (R["mag_release"], Z, 1), (R["mag_out"], drop, 1), (R["mag_out"] + 1, drop, 0),
                         (R["mag_insert_start"] - 1, drop, 0), (R["mag_insert_start"], drop, 1), (R["mag_seated"], Z, 1),
                         (48, Z, 1)]}),
        "A_WPN_Pistol_01_Empty": (1, {"Slide": [(0, back, 1), (1, back, 1)], "Magazine": [(0, Z, 1), (1, Z, 1)]}),
    }
    out = {}
    for nm, (fe, keys) in spec.items():
        make_action(nm, fe, keys, [slide, mag])
        out[nm] = {"frames": fe, "length_s": round(fe / 30.0, 4)}
    # glTF ACTIONS mode only exports object actions reachable from the object (active action / NLA):
    # one muted NLA track per action and object, strip bound to that object's slot -> one glTF animation per action
    for ob in (slide, mag):
        ad = ob.animation_data
        ad.action = None
        for nm in spec:
            act = bpy.data.actions[nm]
            tr = ad.nla_tracks.new()
            tr.name = nm
            st = tr.strips.new(nm, 0, act)
            st.action_slot = next(s for s in act.slots if s.identifier == "OB" + ob.name)
            tr.mute = True
    a = bpy.data.actions["A_WPN_Pistol_01_Reload"]
    for k, f in RELOAD.items():
        a["event_" + k] = f
    for ob in (slide, mag):
        ob.location, ob.scale = (0, 0, 0), (1, 1, 1)
    return out


def main():
    a = args()
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps, sc.render.fps_base = 30, 1.0
    sc.unit_settings.system, sc.unit_settings.scale_length = "METRIC", 1.0
    M = PM.library()
    lps = build_set(False, M)
    unwrap(list(lps.values()))
    times = {}
    if not a.no_bake:
        hps = build_set(True, M)
        ims, times = bake_all(hps, lps, a.res, a.ao_samples)
        cover = post(ims)
        print(f"[PISTOL] texel coverage {cover:.2%}")
        for ob in hps.values():
            bpy.data.objects.remove(ob)
        for im in ims.values():
            bpy.data.images.remove(im)
    for mt in list(bpy.data.materials):
        bpy.data.materials.remove(mt)
    for nm in ("txt",):
        for c in [c for c in bpy.data.curves if c.name.startswith(nm)]:
            bpy.data.curves.remove(c)
    mat = game_material()
    for ob in lps.values():
        ob.data.materials.clear()
        ob.data.materials.append(mat)
    root = bpy.data.objects.new(NAME, None)
    root.empty_display_type, root.empty_display_size = "ARROWS", 0.05
    sc.collection.objects.link(root)
    for ob in lps.values():
        ob.parent = root
    # sockets
    muzzle = Vector((0, -0.1492, 0.0365)) - GRIP
    eject = Vector((-0.0130, -0.0305, 0.0470)) - GRIP
    socks = {"SOCKET_Muzzle": (muzzle, Matrix.Identity(4), lps["Slide"]),
             # rotated 180 deg about up: local +X points out of the right-side port (world -X), local up stays +Z
             "SOCKET_Eject": (eject, Matrix.Rotation(math.pi, 4, "Z"), lps["Slide"]),
             "SOCKET_Grip": (Vector((0, 0, 0)), Matrix.Identity(4), root)}
    for nm, (p, rot, parent) in socks.items():
        e = bpy.data.objects.new(nm, None)
        e.empty_display_type, e.empty_display_size = "ARROWS", 0.015
        sc.collection.objects.link(e)
        e.parent = parent
        e.matrix_world = Matrix.Translation(p) @ rot
    acts = build_actions(lps["Slide"], lps["Magazine"])
    tris = {}
    for nm, ob in lps.items():
        ob.data.calc_loop_triangles()
        tris[nm] = len(ob.data.loop_triangles)
    os.makedirs(SRC_DIR, exist_ok=True)
    path = os.path.join(SRC_DIR, NAME + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True, relative_remap=True)
    pts = [ob.matrix_world @ v.co for ob in lps.values() for v in ob.data.vertices]
    dims = [round(max(p[i] for p in pts) - min(p[i] for p in pts), 4) for i in range(3)]
    print(f"[PISTOL] saved {path}")
    print(f"[PISTOL] tris {tris} total {sum(tris.values())} dims x/y/z {dims} muzzle {tuple(round(c, 4) for c in muzzle)}")
    print(f"[PISTOL] actions {acts} bake {times} total {time.time() - t0:.1f} s")


main()
sys.stdout.flush()
os._exit(0)
