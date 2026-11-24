"""Decal library generator (P2, T-DECAL-01): the "anti plastic look" layer for streets and walls.

Pure Python (numpy + Pillow), deterministic per decal id (seeded). For every decal it writes
  Assets/Decals/<ID>/<ID>_albedo.png   RGBA (alpha = coverage)
  Assets/Decals/<ID>/<ID>_normal.png   tangent-space normal (from a height field)   [if relief]
  Assets/Decals/<ID>/<ID>_orm.png      R=AO, G=roughness, B=metallic               [if it changes gloss]
and a Godot scene GodotProject/Scenes/Decals/<ID>.tscn (one Decal node, projection -Y, size in m).
Everything is invented: graffiti tags name the game's own fictional crews (Los Cuervos, East Hollow,
Kings of Flatbush), the manhole reads "HOLLOW CITY". No photo sources, no third-party textures.

    Tools/uwp build-decals [--only DC_A,DC_B]
"""
import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation", "/usr/share/fonts/truetype/freefont",
             "/usr/share/fonts/TTF", "/usr/share/fonts"]


# ------------------------------------------------------------------ helpers
def font(size, bold=True):
    names = ("DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "FreeSansBold.ttf") if bold else ("DejaVuSans.ttf",)
    for d in FONT_DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.isfile(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def fbm(rng, h, w, octaves=5, base=4):
    """Fractal value noise in [0,1] (bilinear-upsampled random grids)."""
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        g = base * (2 ** o)
        grid = rng.random((g + 1, g + 1)).astype(np.float32)
        im = Image.fromarray((grid * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
        out += amp * (np.asarray(im, np.float32) / 255.0)
        tot += amp
        amp *= 0.5
    return out / tot


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def normal_from_height(hgt, strength=4.0):
    gy, gx = np.gradient(hgt.astype(np.float32))
    nx, ny, nz = -gx * strength, gy * strength, np.ones_like(hgt)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / ln, ny / ln, nz / ln], -1)
    return ((n * 0.5 + 0.5) * 255).astype(np.uint8)


def rgba(col, alpha):
    """col: (h,w,3) float 0..1 or a tuple; alpha (h,w) 0..1 -> uint8 RGBA."""
    h, w = alpha.shape
    c = np.broadcast_to(np.asarray(col, np.float32), (h, w, 3)) if np.ndim(col) == 1 else col
    out = np.concatenate([np.clip(c, 0, 1), np.clip(alpha, 0, 1)[..., None]], -1)
    return (out * 255).astype(np.uint8)


def blur(a, r):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


def mask_from_draw(w, h, fn):
    im = Image.new("L", (w, h), 0)
    fn(ImageDraw.Draw(im))
    return np.asarray(im, np.float32) / 255.0


# ------------------------------------------------------------------ decal recipes
def crack(rng, w, h, long=False):
    def draw(d):
        n_main = 2 if long else 4
        for _ in range(n_main):
            if long:
                x, y, ang = 0.0, h * (0.35 + 0.3 * rng.random()), 0.0
            else:
                x, y, ang = w * rng.random(), h * rng.random(), rng.random() * math.tau
            width = max(2, int(w / 220))
            for step in range(int((w if long else w * 0.6) / 6)):
                ang += rng.normal(0, 0.35)
                if long:
                    ang = 0.8 * ang
                nx, ny = x + math.cos(ang) * 6, y + math.sin(ang) * 6
                d.line((x, y, nx, ny), fill=255, width=width)
                if rng.random() < 0.05:                 # branch
                    bx, by, ba = nx, ny, ang + rng.choice([-1, 1]) * (0.6 + rng.random())
                    for _ in range(int(20 + 40 * rng.random())):
                        ba += rng.normal(0, 0.4)
                        bnx, bny = bx + math.cos(ba) * 5, by + math.sin(ba) * 5
                        d.line((bx, by, bnx, bny), fill=200, width=max(1, width - 1))
                        bx, by = bnx, bny
                x, y = nx, ny
    m = mask_from_draw(w, h, draw)
    edge = blur(m, 3) * 0.55                            # chipped, dusty border
    a = np.maximum(m, edge * 0.6)
    col = np.stack([0.11 + 0.05 * edge, 0.10 + 0.05 * edge, 0.09 + 0.04 * edge], -1)
    hgt = -blur(m, 1.5)
    return rgba(col, a * 0.92), normal_from_height(hgt, 6.0), None


def oil(rng, w, h):
    n = fbm(rng, h, w, 5, 3)
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    blob = smooth(1.0 - r + (n - 0.5) * 0.9, 0.25, 0.55)
    core = smooth(1.0 - r + (n - 0.5) * 0.6, 0.45, 0.8)
    col = np.stack([0.05 + 0.02 * n, 0.05 + 0.02 * n, 0.055 + 0.03 * n], -1)
    a = blob * (0.45 + 0.4 * core)
    orm = np.stack([np.ones_like(a), 0.25 + 0.35 * (1 - core), np.zeros_like(a)], -1)   # oily = glossier
    return rgba(col, a), None, (orm * 255).astype(np.uint8)


def puddle(rng, w, h):
    n = fbm(rng, h, w, 5, 3)
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    m = smooth(1.0 - r + (n - 0.5) * 1.1, 0.30, 0.42)
    col = np.full((h, w, 3), 0.06, np.float32)
    orm = np.stack([np.ones_like(m), 0.03 + 0.1 * (1 - m), np.zeros_like(m)], -1)          # mirror-wet
    return rgba(col, m * 0.55), None, (orm * 255).astype(np.uint8)


def manhole(rng, w, h, text="HOLLOW CITY  -  SEWER  -  "):
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2, h / 2
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (w / 2)
    ang = np.arctan2(yy - cy, xx - cx)
    disc = (r < 0.97).astype(np.float32)
    rim = ((r > 0.88) & (r < 0.97)).astype(np.float32)
    ring2 = ((r > 0.62) & (r < 0.68)).astype(np.float32)
    grid = ((((xx // (w / 18)) + (yy // (h / 18))) % 2) * (r < 0.6)).astype(np.float32)   # checker lugs
    ribs = ((np.abs(np.sin(ang * 8)) > 0.92) & (r > 0.68) & (r < 0.88)).astype(np.float32)
    hgt = 0.8 * rim + 0.6 * ring2 + 0.5 * grid + 0.6 * ribs
    # text around the ring (characters placed on the circle)
    tm = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(tm)
    f = font(int(w * 0.055))
    rad = w / 2 * 0.775
    for i, ch in enumerate(text):
        a = -math.pi / 2 + i * math.tau / len(text)
        ci = Image.new("L", (int(w * 0.08), int(w * 0.08)), 0)
        ImageDraw.Draw(ci).text((ci.width / 2, ci.height / 2), ch, fill=255, font=f, anchor="mm")
        ci = ci.rotate(-math.degrees(a) - 90, resample=Image.BILINEAR)
        tm.paste(ci, (int(cx + math.cos(a) * rad - ci.width / 2), int(cy + math.sin(a) * rad - ci.height / 2)), ci)
    tmask = np.asarray(tm, np.float32) / 255.0
    hgt = np.maximum(hgt, tmask * 0.7)
    rust = fbm(rng, h, w, 5, 4)
    base = 0.17 + 0.05 * rust
    col = np.stack([base + 0.05 * rust * (1 - hgt), base * 0.95, base * 0.88], -1)
    col = col + 0.06 * hgt[..., None]                      # worn, polished high points
    orm = np.stack([1 - 0.4 * (1 - hgt) * disc, 0.62 - 0.25 * hgt, 0.55 + 0.3 * hgt], -1)
    return rgba(col, disc), normal_from_height(blur(hgt, 1.0), 3.0), (np.clip(orm, 0, 1) * 255).astype(np.uint8)


def drain(rng, w, h):
    yy, xx = np.mgrid[0:h, 0:w]
    frame = ((xx > w * 0.03) & (xx < w * 0.97) & (yy > h * 0.06) & (yy < h * 0.94)).astype(np.float32)
    slot = ((((xx / (w / 14)) % 1.0) > 0.35) & (yy > h * 0.2) & (yy < h * 0.8) & (xx > w * 0.08) & (xx < w * 0.92)).astype(np.float32)
    hgt = frame * (1 - slot)
    rust = fbm(rng, h, w, 4, 4)
    col = np.stack([0.16 + 0.07 * rust, 0.15 + 0.03 * rust, 0.14 + 0.01 * rust], -1) * (1 - 0.85 * slot[..., None])
    orm = np.stack([1 - 0.7 * slot, 0.6 * np.ones_like(slot), 0.6 * (1 - slot)], -1)
    return rgba(col, frame), normal_from_height(blur(hgt, 1.0), 5.0), (orm * 255).astype(np.uint8)


def tire_marks(rng, w, h):
    def draw(d):
        for lane in (0.33, 0.67):
            pts = []
            for i in range(60):
                t = i / 59
                x = w * (0.04 + 0.92 * t)
                y = h * (lane + 0.18 * math.sin(t * 2.2 + 0.4) * t)
                pts.append((x, y))
            d.line(pts, fill=255, width=int(h * 0.09), joint="curve")
    m = mask_from_draw(w, h, draw)
    n = fbm(rng, h, w, 5, 6)
    yy, xx = np.mgrid[0:h, 0:w]
    fade = smooth(xx / w, 0.0, 0.25) * (0.55 + 0.45 * (xx / w))
    a = blur(m, 2) * (0.35 + 0.65 * n) * fade
    col = np.full((h, w, 3), 0.035, np.float32)
    return rgba(col, a * 0.85), None, None


def _warp(m, size, shear, ph):
    """Hand-styled distortion: slant (shear) + slow waves, per-row/column shifts (same params for
    fill and outline, or they drift apart)."""
    h, w = m.shape
    out = np.empty_like(m)
    for y in range(h):
        dx = int(shear * (h / 2 - y) + size * 0.10 * np.sin(y / (size * 0.9) + ph))
        out[y] = np.roll(m[y], dx)
    res = np.empty_like(out)
    for x in range(w):
        dy = int(size * 0.08 * np.sin(x / (size * 1.3) + ph * 0.7))
        res[:, x] = np.roll(out[:, x], dy)
    return res


def graffiti(rng, w, h, words, fill=(0.85, 0.12, 0.16), outline=(0.05, 0.05, 0.06), shine=(0.95, 0.95, 0.9)):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    size = int(h * 0.62 / max(1, len(words)))
    f = font(size)
    while max(d.textlength(t, font=f) for t in words) > w * 0.86 and size > 10:
        size -= 4
        f = font(size)
    lh = size * 1.05
    y0 = h / 2 - lh * (len(words) - 1) / 2
    mask_fill = Image.new("L", (w, h), 0)
    mask_out = Image.new("L", (w, h), 0)
    df, do = ImageDraw.Draw(mask_fill), ImageDraw.Draw(mask_out)
    for i, t in enumerate(words):
        y = y0 + i * lh
        # hand-styled: per-letter jitter + rotation, like a fast spray tag
        x = w / 2 - d.textlength(t, font=f) / 2
        for ch in t:
            cw = d.textlength(ch, font=f)
            dy = rng.normal(0, size * 0.06)
            do.text((x + cw / 2, y + dy), ch, font=f, anchor="mm", fill=255, stroke_width=max(3, size // 9), stroke_fill=255)
            df.text((x + cw / 2, y + dy), ch, font=f, anchor="mm", fill=255)
            x += cw * 0.94
    shear, ph = 0.22 + 0.1 * rng.random(), rng.random() * 6.28
    fm = _warp(np.asarray(mask_fill, np.float32) / 255.0, size, shear, ph)
    om = _warp(np.asarray(mask_out, np.float32) / 255.0, size, shear, ph)
    # throw-up style: a second, lighter outer outline around the dark one
    om2 = np.clip(blur(om, max(2, size // 14)) * 3.0, 0, 1)
    # drips under the outline
    dr = Image.new("L", (w, h), 0)
    ddr = ImageDraw.Draw(dr)
    ys, xs = np.nonzero(om > 0.5)
    if len(xs):
        for _ in range(int(w / 40)):
            k = rng.integers(len(xs))
            x, y = xs[k], ys[k]
            ddr.line((x, y, x, y + rng.integers(int(h * 0.05), int(h * 0.25))), fill=200, width=max(2, size // 18))
    dm = np.asarray(dr, np.float32) / 255.0
    over = blur(om, size * 0.12) * 0.35                                     # overspray halo
    grad = np.linspace(1.0, 0.75, h, dtype=np.float32)[:, None]
    n = fbm(rng, h, w, 4, 8)
    col = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        col[..., c] = outline[c] * (1 - fm) + fill[c] * fm * grad * (0.85 + 0.3 * n)
    hl = blur(fm, 1.0) * (1 - blur(fm, 4.0) * 0.0)
    ring = np.clip(om2 - om, 0, 1)
    for c in range(3):
        col[..., c] = col[..., c] * (1 - ring) + shine[c] * ring
    a = np.clip(np.maximum(np.maximum(np.maximum(om, om2), dm * 0.9), over), 0, 1)
    a = a * (0.80 + 0.2 * n)                                                # spray on rough wall
    _ = hl, shine
    return rgba(col, a), None, None


def grime(rng, w, h):
    n = fbm(rng, h, w, 6, 3)
    streak_x = fbm(rng, 1, w, 5, 12)[0]
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    top = smooth(1.0 - yy, 0.15, 1.0)                                       # dirt runs down from the top
    streaks = smooth(streak_x[None, :] * (1 - yy * 0.6), 0.45, 0.85)
    bottom = smooth(yy, 0.75, 1.0) * 0.7                                    # splash at the foot
    a = np.clip((top * 0.45 + streaks * 0.55 * top + bottom) * (0.55 + 0.45 * n), 0, 1)
    col = np.stack([0.13 + 0.05 * n, 0.12 + 0.04 * n, 0.10 + 0.03 * n], -1)
    orm = np.stack([1 - 0.5 * a, 0.92 * np.ones_like(a), np.zeros_like(a)], -1)
    return rgba(col, a * 0.75), None, (orm * 255).astype(np.uint8)


def trash(rng, w, h):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for _ in range(38):
        cx, cy = rng.random() * w, rng.random() * h
        s = w * (0.015 + 0.05 * rng.random())
        kind = rng.random()
        if kind < 0.45:          # paper scraps
            c = tuple(int(v) for v in rng.integers(170, 235, 3)) + (255,)
            pts = [(cx + s * math.cos(a + rng.normal(0, 0.3)), cy + s * 0.7 * math.sin(a + rng.normal(0, 0.3)))
                   for a in np.linspace(0, math.tau, 5)[:-1] + rng.random() * 3]
            d.polygon(pts, fill=c)
        elif kind < 0.7:         # cups / cans (flattened)
            c = [(196, 32, 38, 255), (40, 70, 160, 255), (230, 230, 225, 255), (60, 140, 70, 255)][rng.integers(4)]
            d.ellipse((cx - s * 0.5, cy - s * 0.3, cx + s * 0.5, cy + s * 0.3), fill=c)
        else:                    # leaves / dirt
            c = (int(80 + 40 * rng.random()), int(60 + 30 * rng.random()), 30, 255)
            d.ellipse((cx - s * 0.3, cy - s * 0.15, cx + s * 0.3, cy + s * 0.15), fill=c)
    a = np.asarray(im, np.float32)[..., 3] / 255.0
    col = np.asarray(im, np.float32)[..., :3] / 255.0
    dirt = blur(a, 6) * 0.35
    shade = np.clip(a + dirt, 0, 1)
    col = col * a[..., None] + np.array([0.09, 0.08, 0.07]) * (1 - a[..., None])
    return rgba(col, shade), None, None


# id: (recipe, size_m (x, z), projection depth m, pixels (w, h), kind, args)
DECALS = {
    "DC_LA_Crack_01":     (crack, (2.0, 2.0), 0.12, (512, 512), "ground", {}),
    "DC_LA_Crack_02":     (crack, (3.0, 1.0), 0.12, (768, 256), "ground", {"long": True}),
    "DC_LA_OilStain_01":  (oil, (1.6, 1.6), 0.12, (512, 512), "ground", {}),
    "DC_LA_OilStain_02":  (oil, (2.6, 1.3), 0.12, (512, 256), "ground", {}),
    "DC_LA_Puddle_01":    (puddle, (2.6, 1.8), 0.12, (512, 384), "ground", {}),
    "DC_LA_Manhole_01":   (manhole, (0.9, 0.9), 0.12, (512, 512), "ground", {}),
    "DC_LA_Drain_01":     (drain, (0.9, 0.36), 0.12, (512, 192), "ground", {}),
    "DC_LA_TireMarks_01": (tire_marks, (6.0, 2.0), 0.12, (1024, 340), "ground", {}),
    "DC_LA_Trash_01":     (trash, (2.0, 2.0), 0.12, (512, 512), "ground", {}),
    "DC_LA_Graffiti_01":  (graffiti, (3.2, 1.3), 0.3, (1024, 416), "wall", {"words": ["EAST", "HOLLOW"], "fill": (0.95, 0.62, 0.10)}),
    "DC_LA_Graffiti_02":  (graffiti, (2.4, 1.0), 0.3, (1024, 426), "wall", {"words": ["CUERVOS"], "fill": (0.08, 0.08, 0.09), "outline": (0.86, 0.86, 0.84)}),
    "DC_NY_Graffiti_01":  (graffiti, (3.0, 1.4), 0.3, (1024, 478), "wall", {"words": ["KINGS", "FLATBUSH"], "fill": (0.20, 0.45, 0.90)}),
    "DC_LA_Grime_01":     (grime, (4.0, 3.0), 0.3, (512, 384), "wall", {}),
}


TSCN = """[gd_scene load_steps={steps} format=3]

{ext}
[node name="{id}" type="Decal"]
size = Vector3({sx}, {sy}, {sz})
{tex}albedo_mix = 1.0
normal_fade = 0.3
upper_fade = 0.15
lower_fade = 0.15
distance_fade_enabled = true
distance_fade_begin = 60.0
distance_fade_length = 15.0
metadata/uw_kind = "{kind}"
"""


def build_one(did, repo):
    fn, (sx, sz), depth, (pw, ph), kind, kw = DECALS[did]
    seed = sum(ord(c) * (i + 1) for i, c in enumerate(did)) % (2 ** 31)
    rng = np.random.default_rng(seed)
    alb, nrm, orm = fn(rng, pw, ph, **kw)
    out = os.path.join(repo, "Assets", "Decals", did)
    os.makedirs(out, exist_ok=True)
    maps = {"albedo": alb}
    if nrm is not None:
        maps["normal"] = nrm
    if orm is not None:
        maps["orm"] = orm
    for k, arr in maps.items():
        Image.fromarray(arr).save(os.path.join(out, f"{did}_{k}.png"), optimize=True)
    ext, tex = "", ""
    slots = {"albedo": "texture_albedo", "normal": "texture_normal", "orm": "texture_orm"}
    for i, k in enumerate(maps):
        ext += f'[ext_resource type="Texture2D" path="res://Assets/Decals/{did}/{did}_{k}.png" id="{i + 1}"]\n'
        tex += f'{slots[k]} = ExtResource("{i + 1}")\n'
    scn = os.path.join(repo, "GodotProject", "Scenes", "Decals", f"{did}.tscn")
    os.makedirs(os.path.dirname(scn), exist_ok=True)
    with open(scn, "w") as fh:
        fh.write(TSCN.format(steps=len(maps) + 1, ext=ext, id=did, sx=sx, sy=depth, sz=sz, tex=tex, kind=kind))
    alpha = alb[..., 3].astype(np.float32) / 255.0
    return {"id": did, "size_m": [sx, sz], "depth_m": depth, "px": [pw, ph], "kind": kind, "maps": list(maps),
            "coverage": round(float((alpha > 0.05).mean()), 3), "px_per_m": round(pw / sx, 1)}


def build_all(repo=REPO, only=None):
    ids = list(DECALS) if not only else [s.strip() for s in only.split(",")]
    bad = [i for i in ids if i not in DECALS]
    if bad:
        raise SystemExit(f"[DECALS] unknown id(s) {bad}; known: {sorted(DECALS)}")
    man = []
    for did in ids:
        info = build_one(did, repo)
        man.append(info)
        print(f"[DECALS] {did}: {info['px']} px, {info['size_m']} m, maps {info['maps']}, coverage {info['coverage']}")
    mp = os.path.join(repo, "Assets", "Decals", "decals.manifest.json")
    old = json.load(open(mp)) if os.path.isfile(mp) else {"decals": []}
    keep = [d for d in old.get("decals", []) if d["id"] not in ids]
    json.dump({"generator": "Tools/uwp build-decals", "decals": sorted(keep + man, key=lambda d: d["id"])},
              open(mp, "w"), indent=2)
    return man


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--only", default=None)
    a = ap.parse_args(sys.argv[1:])
    build_all(a.repo, a.only)
