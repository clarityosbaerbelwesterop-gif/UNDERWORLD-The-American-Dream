"""Prop kit (P2, T-PROP-01): geometry primitives, CC0 material library, UVs, collision, save.

Studio practice this follows (Production plan §1, "tool screenshots"):
  * Material library instead of per-asset textures (Substance/trim-sheet workflow): every prop
    draws from the same CC0 Poly Haven sets, so the city reads as one place.
  * Constant texel density (Zen UV / TexTools "texel density"): UV0 is a world-space box
    projection - 1 UV unit = `tile_m` metres of the material - so a hydrant and a dumpster
    show the same paint grain. UV0 therefore tiles and overlaps on purpose
    (`uw_allow_uv_overlap`), exactly like a trim/tiling workflow.
  * UV1 is a unique, non-overlapping lightmap layout (Godot imports it as UV2 for LightmapGI).
  * Bevelled hard edges (catch the light at game distance, DECALmachine/Hard Ops habit).
  * Authored convex collision boxes (UCX_*-convcolonly) - cheap, never closes openings.
  * Labels/signage are separate quads with 0..1 "fit" UVs and generated text textures
    (original names only - no real brands).
Everything is plain bpy/bmesh; no add-ons.
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

from ..characters import pbr_textures as PBR

TEX_SIZE = 512          # per material; 512 px over 1-2 m = 256-512 px/m (budget min 128)

# name: (poly haven id | None, tint/colour rgb, tile metres, metallic, roughness bias / value, normal strength)
MATERIALS = {
    "asphalt":        ("asphalt_02",        (1.20, 1.18, 1.15), 3.0, 0.0, 0.0, 0.9),   # T-DECAL-01: sun-bleached
    "concrete":       ("concrete_pavement", (0.84, 0.82, 0.78), 2.0, 0.0, 0.0, 0.9),
    "concrete_dirty": ("dirty_concrete",    (0.86, 0.84, 0.80), 2.0, 0.0, 0.0, 0.9),
    "metal_dark":     ("metal_plate",       (0.30, 0.32, 0.34), 1.0, 0.85, 0.0, 0.7),
    "metal_galv":     ("metal_plate",       (0.66, 0.68, 0.70), 1.0, 0.90, -0.05, 0.6),
    "metal_rust":     ("rusty_metal_02",    (1.00, 1.00, 1.00), 1.0, 0.45, 0.0, 1.0),
    "metal_green":    ("green_metal_rust",  (1.00, 1.00, 1.00), 1.5, 0.30, 0.0, 1.0),
    "metal_blue":     ("blue_metal_plate",  (1.00, 1.00, 1.00), 1.0, 0.40, 0.0, 0.8),
    "corrugated":     ("corrugated_iron",   (0.85, 0.85, 0.86), 2.0, 0.60, 0.0, 1.0),
    "wood":           ("wood_planks",       (0.92, 0.86, 0.78), 1.2, 0.0, 0.0, 1.0),
    "wood_worn":      ("worn_planks",       (0.95, 0.90, 0.84), 1.2, 0.0, 0.0, 1.0),
    "wood_creosote":  ("bark_brown_02",     (0.42, 0.33, 0.26), 1.5, 0.0, 0.05, 0.8),
    "plywood":        ("plywood",           (1.00, 1.00, 1.00), 1.2, 0.0, 0.0, 0.8),
    "rubber":         ("rubber_tiles",      (0.22, 0.22, 0.22), 0.6, 0.0, 0.10, 0.6),
    "canvas":         ("fabric_pattern_07", (0.40, 0.42, 0.30), 0.4, 0.0, 0.05, 0.8),
    "ballistic":      ("denim_fabric_04",   (0.16, 0.17, 0.18), 0.25, 0.0, 0.05, 1.0),
    "leather":        ("fabric_leather_02", (0.55, 0.45, 0.38), 0.5, 0.0, 0.0, 0.9),
    "foliage":        ("forest_leaves_02",  (0.78, 0.92, 0.70), 1.0, 0.0, 0.05, 1.0),
    # painted / plastic surfaces: flat colour + borrowed micro-normal + roughness from a set
    "paint_red":      ("metal_plate",       (0.55, 0.06, 0.04), 1.0, 0.10, "flat:0.42", 0.5),
    "paint_yellow":   ("metal_plate",       (0.78, 0.58, 0.08), 1.0, 0.10, "flat:0.45", 0.5),
    "paint_green":    ("metal_plate",       (0.08, 0.24, 0.14), 1.0, 0.10, "flat:0.45", 0.5),
    "paint_black":    ("metal_plate",       (0.035, 0.036, 0.04), 1.0, 0.20, "flat:0.38", 0.5),
    "paint_white":    ("metal_plate",       (0.78, 0.78, 0.76), 1.0, 0.10, "flat:0.40", 0.5),
    "paint_blue":     ("metal_plate",       (0.06, 0.16, 0.42), 1.0, 0.10, "flat:0.40", 0.5),
    "plastic_black":  (None, (0.03, 0.03, 0.032), 1.0, 0.0, 0.45, 0.0),
    "plastic_grey":   (None, (0.22, 0.22, 0.23), 1.0, 0.0, 0.50, 0.0),
    "plastic_olive":  (None, (0.18, 0.20, 0.13), 1.0, 0.0, 0.55, 0.0),
    "gold":           (None, (1.00, 0.77, 0.34), 1.0, 1.0, 0.22, 0.0),
    "chrome":         (None, (0.85, 0.86, 0.88), 1.0, 1.0, 0.12, 0.0),
    "glass":          (None, (0.12, 0.15, 0.16), 1.0, 0.0, 0.05, 0.0),
    "paper_brown":    (None, (0.42, 0.31, 0.20), 1.0, 0.0, 0.85, 0.0),
    "tape_tan":       (None, (0.58, 0.47, 0.30), 1.0, 0.0, 0.40, 0.0),
    "paint_road_white": (None, (0.80, 0.80, 0.78), 1.0, 0.0, 0.75, 0.0),
    "paint_road_yellow": (None, (0.85, 0.64, 0.14), 1.0, 0.0, 0.72, 0.0),
    # building library (T-BLDG-01)
    "stucco_cream":   ("plastered_wall",    (0.92, 0.86, 0.74), 3.0, 0.0, 0.0, 0.8),
    "stucco_peach":   ("plastered_wall",    (0.95, 0.74, 0.60), 3.0, 0.0, 0.0, 0.8),
    "stucco_mint":    ("plastered_wall",    (0.70, 0.86, 0.78), 3.0, 0.0, 0.0, 0.8),
    "stucco_sand":    ("plastered_wall",    (0.86, 0.78, 0.62), 3.0, 0.0, 0.0, 0.8),
    "plaster_white":  ("white_plaster_02",  (0.96, 0.95, 0.92), 3.0, 0.0, 0.0, 0.7),
    "brick":          ("red_brick_03",      (0.95, 0.88, 0.84), 2.0, 0.0, 0.0, 1.0),
    "concrete_wall":  ("concrete_wall_008", (0.90, 0.89, 0.86), 3.0, 0.0, 0.0, 0.8),
    "roof_tiles":     ("clay_roof_tiles_02", (1.00, 0.95, 0.90), 2.0, 0.0, 0.0, 1.0),
    "roof_gravel":    ("gravel_concrete",   (0.80, 0.79, 0.77), 3.0, 0.0, 0.0, 0.8),
    # New York set (T-NY-01): brownstone = plaster scan tinted to Triassic sandstone, darker NY brick, limestone
    "brownstone":     ("plastered_wall",    (0.52, 0.36, 0.28), 2.5, 0.0, 0.05, 0.9),
    "brick_ny":       ("red_brick_03",      (0.70, 0.56, 0.50), 2.0, 0.0, 0.0, 1.0),
    "limestone":      ("white_plaster_02",  (0.86, 0.83, 0.75), 3.0, 0.0, 0.0, 0.7),
    "window_glass":   (None, (0.045, 0.06, 0.07), 1.0, 0.0, 0.06, 0.0),
    "curtain_glass":  ("gen:curtain",       (0.06, 0.09, 0.12), 3.0, 0.0, 0.08, 0.0),
    "rollup_door":    ("gen:rollup",        (0.62, 0.64, 0.66), 2.0, 0.70, 0.35, 1.0),
    # weapon library (T-WPN-01): small tiles -> ~2000 px/m on hand-held objects
    "gunmetal":       ("metal_plate",       (0.17, 0.18, 0.20), 0.25, 0.85, -0.05, 0.6),
    "steel_bright":   ("metal_plate",       (0.62, 0.64, 0.67), 0.20, 1.00, -0.20, 0.4),
    "polymer":        ("rubber_tiles",      (0.055, 0.055, 0.06), 0.12, 0.0, 0.05, 0.4),
    "wood_stock":     ("worn_planks",       (0.62, 0.40, 0.24), 0.35, 0.0, -0.15, 0.6),
    "olive_paint":    ("metal_plate",       (0.20, 0.23, 0.14), 0.20, 0.30, 0.10, 0.5),
    "grip_tape":      ("rubber_tiles",      (0.08, 0.08, 0.085), 0.08, 0.0, 0.10, 0.8),
    "rag":            ("fabric_pattern_07", (0.62, 0.56, 0.46), 0.15, 0.0, 0.05, 0.9),
    "glass_bottle":   (None, (0.08, 0.20, 0.10), 1.0, 0.0, 0.06, 0.0),
    "lens":           (None, (0.04, 0.06, 0.10), 1.0, 0.3, 0.04, 0.0),
}

# Procedural (trim-style) maps: name -> fn(size) -> (diffuse rgb multiplier, roughness, normal rgb)
def _gen_curtain(s):
    """Curtain wall: dark glass with aluminium mullions every 1.5 m and a spandrel band per 3 m."""
    d = np.ones((s, s, 3), np.float32)
    r = np.full((s, s), 0.06, np.float32)
    px = s // 2                                    # 1.5 m at tile 3 m
    w = max(2, s // 96)
    for x in range(0, s, px):
        d[:, x:x + w, :] = (6.0, 6.0, 6.2)         # x tint ~0.06 -> ~0.36 aluminium
        r[:, x:x + w] = 0.35
    d[:s // 10, :, :] = (3.0, 3.0, 3.0)            # spandrel/floor band
    r[:s // 10, :] = 0.5
    d[s // 10:s // 10 + w, :, :] = (6.0, 6.0, 6.2)
    n = np.tile(np.array([0.5, 0.5, 1.0], np.float32), (s, s, 1))
    return d, r, n


def _gen_rollup(s):
    """Roll-up door: horizontal slats every ~8 cm (normal map from a sine profile)."""
    v = np.linspace(0, 2 * np.pi * 24, s, dtype=np.float32)
    slope = np.cos(v)[:, None] * np.ones((1, s), np.float32)
    n = np.stack([np.full((s, s), 0.5, np.float32), 0.5 + 0.35 * slope, np.full((s, s), 0.9, np.float32)], axis=2)
    d = (0.85 + 0.15 * np.sin(v))[:, None, None] * np.ones((1, s, 3), np.float32)
    r = np.full((s, s), 0.4, np.float32)
    return d, r, n


GENERATED = {"curtain": _gen_curtain, "rollup": _gen_rollup}
# name: (rgb, strength)
EMISSIVE = {
    "lamp_sodium": ((1.0, 0.78, 0.42), 4.0),
    "signal_red": ((1.0, 0.08, 0.05), 3.0),
    "signal_amber": ((1.0, 0.55, 0.05), 0.4),
    "signal_green": ((0.10, 1.0, 0.55), 0.4),
    "screen": ((0.20, 0.32, 0.45), 0.6),
    "light_panel": ((0.95, 0.95, 0.90), 1.5),
    "lamp_globe_green": ((0.25, 1.0, 0.45), 2.5),
}
FONT_DIRS = ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation", "/usr/share/fonts/truetype/freefont")


def find_maps(cache_dir, ph_id):
    d = os.path.join(cache_dir, "textures", ph_id or "")
    out = {}
    if not ph_id or not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        low, fp = fn.lower(), os.path.join(d, fn)
        for key, tags in (("diff", ("_diff_", "_diffuse_", "_albedo_")), ("nor", ("_nor_gl_",)),
                          ("rough", ("_rough_",)), ("ao", ("_ao_",)), ("metal", ("_metal_",))):
            if any(t in low for t in tags):
                out[key] = fp
    return out


class Prop:
    """One prop = one root empty + one mesh (+ optional extra parts) + UCX collision."""

    def __init__(self, name, category, cache_dir):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = bpy.context.scene
        sc.unit_settings.system, sc.unit_settings.scale_length = "METRIC", 1.0
        sc.render.fps = 30
        self.name, self.category, self.cache_dir = name, category, cache_dir
        self.root = bpy.data.objects.new(name, None)
        sc.collection.objects.link(self.root)
        self.bm = bmesh.new()
        self.uvmode = self.bm.faces.layers.int.new("uvmode")      # 0 world box, 1 fit
        self.label_id = self.bm.faces.layers.int.new("label_id")  # -1 none, else index into self.labels
        self.labels = []                                           # [(name, text, fg, bg, w, h)]
        self.mats, self.mat_index = [], {}
        self.cols = []
        self.missing_textures = []

    # ---------------------------------------------------------------- parts (weapons, vehicles)
    def part(self, name):
        """Switch the active mesh to part `name` (separate object at finish, e.g. Slide/Magazine)."""
        if not hasattr(self, "_parts"):
            self._parts = {"__main__": (self.bm, self.uvmode, self.label_id)}
        if name not in self._parts:
            bm = bmesh.new()
            self._parts[name] = (bm, bm.faces.layers.int.new("uvmode"), bm.faces.layers.int.new("label_id"))
        self.bm, self.uvmode, self.label_id = self._parts[name]
        return self

    # ---------------------------------------------------------------- materials
    def mat(self, key):
        if key in self.mat_index:
            return self.mat_index[key]
        if key.startswith("label:"):
            # every label of a prop lives in ONE atlas material (trim-sheet style): fewer materials
            # and draw calls, power-of-two texture; UVs are remapped into the atlas in finish().
            _, lname, spec = key.split(":", 2)
            text, fg, bg, wh = (spec.split("|") + ["", "", "", ""])[:4]
            w, h = (int(x) for x in (wh or "512x128").split("x"))
            self.labels.append((lname, text, fg or "ffffff", bg or "0b5d2e", w, h))
            self.mat_index[key] = ("label", len(self.labels) - 1)
            return self.mat_index[key]
        elif key in EMISSIVE:
            rgb, strength = EMISSIVE[key]
            m = bpy.data.materials.new(f"M_Prop_{_pascal(key)}")
            m.use_nodes = True
            b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            b.inputs["Base Color"].default_value = (*rgb, 1.0)
            b.inputs["Roughness"].default_value = 0.2
            b.inputs["Emission Color"].default_value = (*rgb, 1.0)
            b.inputs["Emission Strength"].default_value = strength
        else:
            m = self._pbr_material(key)
        self.mats.append(m)
        self.mat_index[key] = len(self.mats) - 1
        return self.mat_index[key]

    def _pbr_material(self, key):
        ph, rgb, _tile, metallic, rough, nstr = MATERIALS[key]
        name = f"Prop_{_pascal(key)}"
        if ph and ph.startswith("gen:"):
            s_ = TEX_SIZE
            dm, r, nrm = GENERATED[ph[4:]](s_)
            diff = np.clip(dm * np.array(rgb, np.float32), 0, 1)
            r = np.clip(r + (float(rough) if not isinstance(rough, str) else 0.0) * 0.0, 0.05, 0.97)
            orm = np.stack([np.ones((s_, s_), np.float32), r, np.full((s_, s_), metallic, np.float32)], axis=2)
            img_d = PBR.pack_np_image(f"T_{name}_D", diff, False, "JPEG", 88)
            img_n = PBR.pack_np_image(f"T_{name}_N", nrm, True, "JPEG", 92)
            img_o = PBR.pack_np_image(f"T_{name}_ORM", orm, True, "JPEG", 88)
            return PBR.make_pbr_material(f"M_{name}", img_d, img_n, img_o, normal_strength=max(nstr, 0.01))
        maps = find_maps(self.cache_dir, ph)
        if ph and not maps:
            self.missing_textures.append(ph)
        s = TEX_SIZE
        flat_rough = isinstance(rough, str) and rough.startswith("flat:")
        if ph and maps and not flat_rough:
            diff = _load(maps.get("diff"), s, False, (0.5, 0.5, 0.5))[:, :, :3] * np.array(rgb, np.float32)
            r = np.clip(_load(maps.get("rough"), s, True, (0.8,))[:, :, 0] + float(rough), 0.08, 0.97)
        else:
            diff = np.ones((s, s, 3), np.float32) * np.array(rgb, np.float32)
            base_r = float(rough.split(":")[1]) if flat_rough else float(rough)
            if ph and maps:
                # painted surface: keep a little of the set's roughness breakup (wear, grime)
                var = _load(maps.get("rough"), s, True, (0.5,))[:, :, 0]
                r = np.clip(base_r + 0.25 * (var - var.mean()), 0.08, 0.97)
                ao_var = _load(maps.get("ao"), s, True, (1.0,))[:, :, 0]
                diff = diff * (0.82 + 0.18 * ao_var[:, :, None])
            else:
                r = np.full((s, s), base_r, np.float32)
        nrm = _load(maps.get("nor"), s, True, (0.5, 0.5, 1.0))[:, :, :3] if maps else np.tile(np.array([0.5, 0.5, 1.0], np.float32), (s, s, 1))
        ao = _load(maps.get("ao"), s, True, (1.0,))[:, :, 0] if maps else np.ones((s, s), np.float32)
        orm = np.stack([ao, r, np.full_like(r, metallic)], axis=2)
        img_d = PBR.pack_np_image(f"T_{name}_D", np.clip(diff, 0, 1), False, "JPEG", 86)
        img_n = PBR.pack_np_image(f"T_{name}_N", nrm, True, "JPEG", 92)
        img_o = PBR.pack_np_image(f"T_{name}_ORM", orm, True, "JPEG", 86)
        return PBR.make_pbr_material(f"M_{name}", img_d, img_n, img_o, normal_strength=nstr)

    # ---------------------------------------------------------------- primitives
    def _tag(self, faces, mat, uvmode=0, smooth=False):
        mi = self.mat(mat)
        lid = -1
        if isinstance(mi, tuple):              # label -> atlas material (index resolved in finish)
            lid, mi, uvmode = mi[1], self._atlas_slot(), 1
        for f in faces:
            f.material_index = mi
            f[self.uvmode] = uvmode
            f[self.label_id] = lid
            f.smooth = smooth

    def _atlas_slot(self):
        if "__labels__" not in self.mat_index:
            m = bpy.data.materials.new(f"M_Prop_{self.name.split('_', 1)[1]}_Labels")
            self.mats.append(m)
            self.mat_index["__labels__"] = len(self.mats) - 1
        return self.mat_index["__labels__"]

    def _new_faces(self, before):
        return [f for f in self.bm.faces if f not in before]

    def mark(self):
        return set(self.bm.verts)

    def transform_since(self, mark, fn):
        """Apply fn(Vector) -> Vector to every vertex created after `mark`."""
        for v in self.bm.verts:
            if v not in mark:
                v.co = fn(v.co.copy())

    def box(self, center, size, mat, bevel=0.0, rot=(0, 0, 0), uv="world"):
        before = set(self.bm.faces)
        m = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*size, 1.0))
        ret = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        if bevel > 0:
            edges = list({e for v in ret["verts"] for e in v.link_edges})
            bmesh.ops.bevel(self.bm, geom=edges, offset=min(bevel, 0.45 * min(size)), segments=1,
                            affect="EDGES", clamp_overlap=True)
        self._tag(self._new_faces(before), mat, uvmode=1 if uv == "fit" else 0)

    def cyl(self, center, radius, depth, mat, segs=16, rot=(0, 0, 0), radius2=None, caps=True, smooth=True):
        """Cylinder/cone along local Z, centred on `center`."""
        before = set(self.bm.faces)
        m = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4()
        bmesh.ops.create_cone(self.bm, cap_ends=caps, cap_tris=False, segments=segs, radius1=radius,
                              radius2=radius if radius2 is None else radius2, depth=depth, matrix=m)
        new = self._new_faces(before)
        self._tag(new, mat, smooth=smooth)
        for f in new:                      # caps flat, sides smooth
            if len(f.verts) > 4:
                f.smooth = False

    def lathe(self, profile, mat, segs=20, center=(0, 0, 0), smooth=True, cap_top=True, cap_bottom=True):
        """Revolve [(radius, z), ...] (bottom -> top) around Z."""
        before = set(self.bm.faces)
        c = Vector(center)
        rings = []
        for r, z in profile:
            if r < 1e-6:
                pole = self.bm.verts.new(c + Vector((0, 0, z)))
                rings.append([pole] * segs)
            else:
                rings.append([self.bm.verts.new(c + Vector((math.cos(2 * math.pi * i / segs) * r,
                                                            math.sin(2 * math.pi * i / segs) * r, z)))
                              for i in range(segs)])
        for a, b in zip(rings, rings[1:]):
            for i in range(segs):
                j = (i + 1) % segs
                quad = [a[i], a[j], b[j], b[i]]
                uniq = []
                for v in quad:
                    if v not in uniq:
                        uniq.append(v)
                if len(uniq) >= 3:
                    self.bm.faces.new(uniq)
        if cap_bottom and profile[0][0] > 1e-4:
            self.bm.faces.new(rings[0][::-1])
        if cap_top and profile[-1][0] > 1e-4:
            self.bm.faces.new(rings[-1])
        new = self._new_faces(before)
        self._tag(new, mat, smooth=smooth)
        for f in new:
            if len(f.verts) > 4:
                f.smooth = False

    def wall(self, origin, normal, length, height, mat, openings=(), reveal_mat=None, depth=0.25):
        """Outer face of a wall with rectangular openings (no back faces: buildings are closed).
        origin = outer bottom-left corner seen from outside; normal = outward unit vector in XY.
        openings: [(u0, u1, v0, v1), ...] in wall metres. Each opening gets 4 reveal faces of
        `depth` (window/door reveal) - the opening itself stays open for glass/doors behind it."""
        n = Vector(normal).normalized()
        up = Vector((0, 0, 1))
        u = up.cross(n).normalized()                 # u x up = n  -> outward winding
        o = Vector(origin)
        us = sorted({0.0, length, *[c for op in openings for c in op[:2]]})
        vs = sorted({0.0, height, *[c for op in openings for c in op[2:]]})
        P = lambda uu, vv, dd=0.0: o + u * uu + up * vv - n * dd
        before = set(self.bm.faces)
        for a, b in zip(us, us[1:]):
            for c, d in zip(vs, vs[1:]):
                cu, cv = (a + b) / 2, (c + d) / 2
                if any(op[0] < cu < op[1] and op[2] < cv < op[3] for op in openings):
                    continue
                vv_ = [self.bm.verts.new(P(a, c)), self.bm.verts.new(P(b, c)), self.bm.verts.new(P(b, d)), self.bm.verts.new(P(a, d))]
                self.bm.faces.new(vv_)
        self._tag(self._new_faces(before), mat)
        before = set(self.bm.faces)
        for (u0, u1, v0, v1) in openings:
            corners = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            for k in range(4):
                (a1, b1), (a2, b2) = corners[k], corners[(k + 1) % 4]
                # reveal faces point into the opening
                q = [self.bm.verts.new(P(a2, b2)), self.bm.verts.new(P(a1, b1)),
                     self.bm.verts.new(P(a1, b1, depth)), self.bm.verts.new(P(a2, b2, depth))]
                self.bm.faces.new(q)
        self._tag(self._new_faces(before), reveal_mat or mat)

    def quad(self, p0, p1, p2, p3, mat, uvmode=0):
        """Single quad, winding p0->p1->p2->p3 (CCW seen from the visible side)."""
        before = set(self.bm.faces)
        self.bm.faces.new([self.bm.verts.new(Vector(p)) for p in (p0, p1, p2, p3)])
        self._tag(self._new_faces(before), mat, uvmode=uvmode)

    def shell_arc(self, a0, a1, rx, ry, z0, z1, thick, mat, segs=10, top_dip=0.0, ry_front=None):
        """Curved armour/clothing panel: elliptical arc a0..a1 (radians, 0 = +X, -pi/2 = front -Y),
        closed thick slab. top_dip lowers the top edge at the arc centre (neck scoop)."""
        before = set(self.bm.faces)
        outer, inner = [], []
        for i in range(segs + 1):
            t = i / segs
            a = a0 + (a1 - a0) * t
            dip = top_dip * math.sin(math.pi * t) ** 2
            ca, sa = math.cos(a), math.sin(a)
            ry_a = ry_front if (ry_front is not None and sa < 0) else ry
            o_b = self.bm.verts.new((ca * rx, sa * ry_a, z0))
            o_t = self.bm.verts.new((ca * rx, sa * ry_a, z1 - dip))
            i_b = self.bm.verts.new((ca * (rx - thick), sa * (ry_a - thick), z0))
            i_t = self.bm.verts.new((ca * (rx - thick), sa * (ry_a - thick), z1 - dip))
            outer.append((o_b, o_t))
            inner.append((i_b, i_t))
        for k in range(segs):
            (ob0, ot0), (ob1, ot1) = outer[k], outer[k + 1]
            (ib0, it0), (ib1, it1) = inner[k], inner[k + 1]
            self.bm.faces.new((ob0, ob1, ot1, ot0))          # outside
            self.bm.faces.new((ib1, ib0, it0, it1))          # inside
            self.bm.faces.new((ot0, ot1, it1, it0))          # top
            self.bm.faces.new((ob1, ob0, ib0, ib1))          # bottom
        self.bm.faces.new((inner[0][0], outer[0][0], outer[0][1], inner[0][1]))
        self.bm.faces.new((outer[-1][0], inner[-1][0], inner[-1][1], outer[-1][1]))
        self._tag(self._new_faces(before), mat, smooth=True)

    def tube(self, points, radius, mat, segs=8, closed_ends=True):
        """Sweep a circle along a polyline (poles with bends, handles, cables, rails)."""
        before = set(self.bm.faces)
        pts = [Vector(p) for p in points]
        pts = [p for k, p in enumerate(pts) if k == 0 or (p - pts[k - 1]).length > 1e-5]
        if len(pts) < 2:
            return
        rings = []
        u = None
        t_prev = None
        for k, p in enumerate(pts):
            t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
            if u is None:
                ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
                u = t.cross(ref).normalized()
            else:
                # parallel transport (rotation-minimising frame): no twisted / bow-tie quads at bends
                u = t_prev.rotation_difference(t) @ u
                u = (u - t * u.dot(t)).normalized()
            t_prev = t
            v = t.cross(u).normalized()
            # keep the ring in the bisector plane at bends so the tube keeps its radius
            rings.append([self.bm.verts.new(p + (u * math.cos(2 * math.pi * i / segs) + v * math.sin(2 * math.pi * i / segs)) * radius)
                          for i in range(segs)])
        for a, b in zip(rings, rings[1:]):
            for i in range(segs):
                j = (i + 1) % segs
                self.bm.faces.new((a[i], a[j], b[j], b[i]))
        if closed_ends:
            self.bm.faces.new(rings[0][::-1])
            self.bm.faces.new(rings[-1])
        new = self._new_faces(before)
        self._tag(new, mat, smooth=True)
        for f in new:
            if len(f.verts) > 4:
                f.smooth = False

    def sphere(self, center, radius, mat, segs=12, rings=8, scale=(1, 1, 1), hemi=False):
        before = set(self.bm.faces)
        m = Matrix.Translation(center) @ Matrix.Diagonal((*scale, 1.0))
        bmesh.ops.create_uvsphere(self.bm, u_segments=segs, v_segments=rings, radius=radius, matrix=m)
        new = self._new_faces(before)
        if hemi:
            cz = center[2]
            kill = [f for f in new if f.calc_center_median().z < cz - 1e-4]
            bmesh.ops.delete(self.bm, geom=kill, context="FACES")
            new = [f for f in new if f.is_valid]
        self._tag(new, mat, smooth=True)

    def label(self, center, size_xy, mat, rot=(0, 0, 0), double=False):
        """Flat quad facing -Y (TD-004 front) with 0..1 UVs; rot rotates it."""
        before = set(self.bm.faces)
        m = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4()
        w, h = size_xy[0] * 0.5, size_xy[1] * 0.5
        vs = [self.bm.verts.new(m @ Vector(p)) for p in ((-w, 0, -h), (w, 0, -h), (w, 0, h), (-w, 0, h))]
        self.bm.faces.new(vs)
        if double:
            vs2 = [self.bm.verts.new(m @ Vector(p)) for p in ((w, 0.0005, -h), (-w, 0.0005, -h), (-w, 0.0005, h), (w, 0.0005, h))]
            self.bm.faces.new(vs2)
        self._tag(self._new_faces(before), mat, uvmode=1)

    def card(self, center, size_xy, mat, rot=(0, 0, 0)):
        """Double-sided foliage/fabric card (world UV)."""
        before = set(self.bm.faces)
        m = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4()
        w, h = size_xy[0] * 0.5, size_xy[1] * 0.5
        a = [self.bm.verts.new(m @ Vector(p)) for p in ((-w, 0, -h), (w, 0, -h), (w, 0, h), (-w, 0, h))]
        self.bm.faces.new(a)
        b = [self.bm.verts.new(m @ Vector(p)) for p in ((w, 0.002, -h), (-w, 0.002, -h), (-w, 0.002, h), (w, 0.002, h))]
        self.bm.faces.new(b)
        self._tag(self._new_faces(before), mat)

    # ---------------------------------------------------------------- collision
    def col_box(self, center, size, rot=(0, 0, 0)):
        self.cols.append(("box", center, size, rot))

    def col_slab(self, size_xy, top_z):
        """Walkable flat slab, trimesh (-colonly), top exactly at `top_z` (B-PT-01 rule)."""
        self.cols.append(("slab", (0, 0, top_z * 0.5), (size_xy[0], size_xy[1], top_z), (0, 0, 0)))

    # ---------------------------------------------------------------- label atlas
    def _build_label_atlas(self):
        """Shelf-pack all labels into one power-of-two atlas; returns UV rects (u0, v0, u1, v1)."""
        pad = 4
        width = 1024 if max(l[4] for l in self.labels) > 512 or len(self.labels) > 4 else 512
        x = y = shelf_h = 0
        places = []
        for (_n, _t, _fg, _bg, w, h) in self.labels:
            w, h = min(w, width), h
            if x + w > width:
                x, y, shelf_h = 0, y + shelf_h + pad, 0
            places.append((x, y, w, h))
            x += w + pad
            shelf_h = max(shelf_h, h)
        height = 1
        while height < y + shelf_h:
            height *= 2
        atlas = np.zeros((height, width, 4), np.float32)
        atlas[:, :, 3] = 1.0
        rects = []
        for (n, t, fg, bg, w, h), (px, py, pw, ph) in zip(self.labels, places):
            img = text_image(t, fg, bg, pw, ph)                     # bottom-up rows
            # atlas rows are bottom-up too: place label rows from the top of the atlas downwards
            r0 = height - py - ph
            atlas[r0:r0 + ph, px:px + pw, :] = img
            rects.append(((px + 0.5) / width, (r0 + 0.5) / height, (px + pw - 0.5) / width, (r0 + ph - 0.5) / height))
        tag = self.name.split("_", 1)[1]
        img = PBR.pack_np_image(f"T_Prop_{tag}_Labels_D", atlas, False, "JPEG", 90)
        m = self.mats[self.mat_index["__labels__"]]
        new = PBR.make_pbr_material(m.name + "_tmp", img, None, None, roughness=0.45, metallic=0.0)
        name = m.name
        self.mats[self.mat_index["__labels__"]] = new
        bpy.data.materials.remove(m)
        new.name = name
        return rects

    # ---------------------------------------------------------------- finish
    def finish(self, repo_root, ground=True, before_save=None):
        """Build the mesh object(s) + collision and save Blender/Source/<cat>/<name>/<name>.blend.
        Parts (P.part(...)) become separate objects named after the part (Frame, Slide, ...).
        before_save(P, objects) may add sockets/rigs before the file is written."""
        parts = getattr(self, "_parts", {"__main__": (self.bm, self.uvmode, self.label_id)})
        all_verts = [v for (bm, _u, _l) in parts.values() for v in bm.verts]
        # No global recalc_face_normals: primitives are built with outward winding, and a recalc
        # flips isolated label quads / two-sided cards (they would vanish under back-face culling).
        zmin = min(v.co.z for v in all_verts) if ground else 0.0
        if ground and abs(zmin) > 1e-6:
            for v in all_verts:
                v.co.z -= zmin
        # T-NY-01: an asset that deliberately reaches below grade (stairwell) keeps its origin at
        # grade and declares how deep it goes - the validator allows exactly that much.
        below = 0.0 if ground else max(0.0, -min(v.co.z for v in all_verts))
        rects = self._build_label_atlas() if self.labels else []
        objects = {}
        tris = 0
        for pname, (bm, uvl, lid) in parts.items():
            if not bm.faces:
                bm.free()
                continue
            uv0 = bm.loops.layers.uv.new("UVMap")
            for f in bm.faces:
                if f[uvl] == 1:
                    _fit_uv(f, uv0, rects[f[lid]] if f[lid] >= 0 else None)
                else:
                    _world_uv(f, uv0, _tile_for(self.mats[f.material_index]))
            oname = f"{self.name}_Mesh" if pname == "__main__" else pname
            me = bpy.data.meshes.new(oname)
            bm.to_mesh(me)
            bm.free()
            ob = bpy.data.objects.new(oname, me)
            bpy.context.scene.collection.objects.link(ob)
            ob.parent = self.root
            for m in self.mats:
                me.materials.append(m)
            ob["uw_allow_uv_overlap"] = 1        # UV0 tiles on purpose (world-space texel density)
            _lightmap_uv(ob)
            objects[pname] = ob
            if below > 0.0:
                ob["uw_below_grade_m"] = round(below + 0.01, 3)
            tris += sum(len(pg.vertices) - 2 for pg in me.polygons)
        for i, (kind, c, s, r) in enumerate(self.cols):
            cz = c[2] - (zmin if ground and kind != "slab" else 0.0)
            hint = "-colonly" if kind == "slab" else "-convcolonly"
            cname = f"UCX_{self.name}_{i:02d}{hint}"
            cbm = bmesh.new()
            bmesh.ops.create_cube(cbm, size=1.0, matrix=Matrix.Translation((c[0], c[1], cz)) @ Euler(r).to_matrix().to_4x4() @ Matrix.Diagonal((*s, 1.0)))
            cme = bpy.data.meshes.new(cname)
            cbm.to_mesh(cme)
            cbm.free()
            co = bpy.data.objects.new(cname, cme)
            bpy.context.scene.collection.objects.link(co)
            co.parent = self.root
        if self.missing_textures:
            raise RuntimeError(f"{self.name}: CC0 texture sets missing in cache: {sorted(set(self.missing_textures))} "
                               f"(run Tools/underworld_pipeline/fetch_sources.py --groups props)")
        if before_save:
            before_save(self, objects)
        p = os.path.join(repo_root, "Blender", "Source", self.category, self.name, f"{self.name}.blend")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=p, compress=True)
        print(f"[PROPS] saved {os.path.relpath(p, repo_root)} ({tris} tris, {len(self.mats)} materials, "
              f"{len(objects)} part(s), {len(self.cols)} collision)")
        return p


# -------------------------------------------------------------------- helpers
def _pascal(key):
    return "".join(w.capitalize() for w in key.replace("-", "_").split("_"))


def _load(path, size, non_color, fallback):
    if not path:
        a = np.ones((size, size, 4), np.float32)
        a[:, :, :len(fallback)] = np.array(fallback, np.float32)
        return a
    return PBR.load_image_np(path, (size, size), non_color)


def _tile_for(mat):
    key = mat.name[len("M_Prop_"):] if mat.name.startswith("M_Prop_") else ""
    for k, v in MATERIALS.items():
        if _pascal(k) == key:
            return float(v[2])
    return 1.0


def _world_uv(f, layer, tile):
    n = f.normal
    ax = max(range(3), key=lambda i: abs(n[i]))
    for loop in f.loops:
        co = loop.vert.co
        if ax == 0:
            u, v = co.y * (1 if n.x > 0 else -1), co.z
        elif ax == 1:
            u, v = co.x * (-1 if n.y > 0 else 1), co.z
        else:
            u, v = co.x, co.y * (1 if n.z > 0 else -1)
        loop[layer].uv = (u / tile, v / tile)


def _fit_uv(f, layer, rect=None):
    """0..1 UVs over the face, oriented so text reads correctly: u = world-up x normal (side
    faces) or +X (top/bottom faces), v = normal x u. Independent of vertex order."""
    n = f.normal.normalized()
    up = Vector((0, 0, 1))
    if abs(n.z) > 0.9:
        u_ax = Vector((1, 0, 0)) if n.z > 0 else Vector((-1, 0, 0))
    else:
        u_ax = up.cross(n).normalized()
    v_ax = n.cross(u_ax).normalized()
    us = [l.vert.co.dot(u_ax) for l in f.loops]
    vs = [l.vert.co.dot(v_ax) for l in f.loops]
    umin, vmin = min(us), min(vs)
    du, dv = (max(us) - umin) or 1.0, (max(vs) - vmin) or 1.0
    u0, v0, u1, v1 = rect or (0.0, 0.0, 1.0, 1.0)
    for l, uu, vv in zip(f.loops, us, vs):
        l[layer].uv = (u0 + (u1 - u0) * (uu - umin) / du, v0 + (v1 - v0) * (vv - vmin) / dv)


def _lightmap_uv(ob):
    me = ob.data
    lm = me.uv_layers.new(name="UVMap_Lightmap")
    me.uv_layers.active = lm
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    me.uv_layers.active = me.uv_layers["UVMap"]
    me.uv_layers["UVMap"].active_render = True


def text_image(text, fg_hex, bg_hex, w, h):
    """RGBA float image with centred text (DejaVu/Liberation from the system; original wording only)."""
    from PIL import Image, ImageDraw, ImageFont
    fg = tuple(int(fg_hex[i:i + 2], 16) for i in (0, 2, 4))
    bg = tuple(int(bg_hex[i:i + 2], 16) for i in (0, 2, 4))
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    font_path = None
    for fd in FONT_DIRS:
        for fn in ("DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "FreeSansBold.ttf"):
            if os.path.isfile(os.path.join(fd, fn)):
                font_path = os.path.join(fd, fn)
                break
        if font_path:
            break
    lines = text.split("\\n")
    size = int(h * 0.62 / max(1, len(lines)))
    while True:
        font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
        widths = [d.textlength(l, font=font) for l in lines]
        if max(widths) <= w * 0.9 or size <= 8 or not font_path:
            break
        size -= 2
    border = max(2, h // 32)
    d.rectangle([border, border, w - 1 - border, h - 1 - border], outline=fg, width=max(1, border // 2))
    total = size * len(lines) * 1.15
    y = (h - total) / 2
    for l, lw in zip(lines, widths):
        d.text(((w - lw) / 2, y), l, fill=fg, font=font)
        y += size * 1.15
    arr = np.asarray(img, dtype=np.float32) / 255.0
    arr = arr[::-1, :, :]                    # Blender pixel rows start at the bottom
    return np.concatenate([arr, np.ones((h, w, 1), np.float32)], axis=2)
