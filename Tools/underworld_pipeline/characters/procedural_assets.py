"""Procedural CC0-free material & micro-detail generators for the UNDERWORLD character pipeline.

Why this module exists
----------------------
The character builder was written against the MakeHuman *system asset* packs
(`makehuman_system_assets_cc0.zip`: skins02/skins01, eyebrows, eyelashes, teeth, Poly Haven
PBR sets). Those archives live on `files2.makehumancommunity.org`, which is **not reachable**
from the build sandbox, and the copies that are mirrored on GitHub are either AGPL-licensed
(`dmaugis/makehuman-py3-assets`) or only contain LFS pointers. The project licence policy
(Docs/ASSET_LICENSES.md) allows only CC0-1.0 / CC-BY-4.0 material, so no third-party copy is
used here.

Everything in this module is generated from scratch with numpy inside Blender: seamless
band-limited noise fields (FFT-filtered white noise -> perfectly tiling textures), analytic
weaves / grain / cellular ridges, and derived normal maps. Output arrays use the same layout
as `pbr_textures.load_image_np` (float32, 0..1, shape (h, w, c)) so they drop straight into
`build_hero_skin_material` / `build_garment_material`.

All generators are deterministic for a given seed.
"""
from __future__ import annotations

import numpy as np

# --------------------------------------------------------------------------------------
# noise primitives
# --------------------------------------------------------------------------------------


def seamless_noise(size: int, rng: np.random.Generator, beta: float = 2.0,
                   low_cut: float = 1.0) -> np.ndarray:
    """Seamless 1/f^beta noise in [0, 1].

    White noise is filtered in the Fourier domain by |k|^(-beta); because the FFT assumes a
    periodic signal the result tiles perfectly, which is exactly what a repeating UV texture
    needs. `low_cut` removes the DC/lowest bands so the field has no global gradient.
    """
    white = rng.standard_normal((size, size))
    f = np.fft.fft2(white)
    ky = np.fft.fftfreq(size)[:, None]
    kx = np.fft.fftfreq(size)[None, :]
    k = np.sqrt(kx * kx + ky * ky)
    k = np.maximum(k, 1.0 / size)
    amp = k ** (-beta)
    amp[k < low_cut / size] = 0.0
    out = np.real(np.fft.ifft2(f * amp))
    out -= out.min()
    span = out.max()
    if span > 1e-9:
        out /= span
    return out.astype(np.float32)


def ridged(noise: np.ndarray) -> np.ndarray:
    """Ridge transform: turns blobby noise into crease/grain lines (leather, bark, brick)."""
    return (1.0 - np.abs(noise * 2.0 - 1.0)).astype(np.float32)


def normal_from_height(height: np.ndarray, strength: float) -> np.ndarray:
    """OpenGL-convention tangent normal map (RGB 0..1) from a height field (0..1)."""
    gx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5 * strength
    gy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 0.5 * strength
    nz = np.ones_like(height)
    length = np.sqrt(gx * gx + gy * gy + nz * nz)
    out = np.empty(height.shape + (3,), dtype=np.float32)
    out[:, :, 0] = (-gx / length) * 0.5 + 0.5
    out[:, :, 1] = (gy / length) * 0.5 + 0.5
    out[:, :, 2] = (nz / length) * 0.5 + 0.5
    return out


# --------------------------------------------------------------------------------------
# human skin
# --------------------------------------------------------------------------------------


def skin_maps(size: int, seed: int, tint=(0.94, 0.85, 0.76), gamma: float = 1.08):
    """Photographic-ish bare skin: diffuse, tangent normal, roughness.

    Layers (all seamless):
      * broad melanin/haemoglobin mottling (beta 2.1 + 1.4 octaves)
      * fine capillary flush (beta 1.1, reddish)
      * pores (beta 0.55 ridge, crisp normal)
      * sparse darker beauty marks
    """
    rng = np.random.default_rng(seed)
    tint_arr = np.array(tint, dtype=np.float32)
    # `skin.tint_rgb` in the specs is a *lighting-neutral* colour (0.94, 0.85, 0.76), not an
    # albedo. Photographic skin albedo is ~0.60 and much more saturated, so map the tint's
    # channel ratios onto a real albedo ramp: (1.00, 0.90, 0.81)^2.2 * 0.80 = (0.80, 0.64, 0.50).
    tint_arr = 0.80 * (tint_arr / max(float(tint_arr.max()), 1e-6)) ** 2.2

    broad = seamless_noise(size, rng, beta=2.1)
    mid = seamless_noise(size, rng, beta=1.4)
    flush = seamless_noise(size, rng, beta=1.1)
    pores = ridged(seamless_noise(size, rng, beta=0.55))

    base = 0.94 + 0.10 * (broad - 0.5) + 0.05 * (mid - 0.5)
    diff = np.empty((size, size, 3), dtype=np.float32)
    # Haemoglobin: reds react most to the flush field, blue the least (real subsurface tinting)
    diff[:, :, 0] = base * (1.0 + 0.11 * (flush - 0.5))
    diff[:, :, 1] = base * (1.0 + 0.02 * (flush - 0.5))
    diff[:, :, 2] = base * (1.0 - 0.06 * (flush - 0.5))
    diff *= tint_arr[None, None, :]
    diff = np.clip(diff ** gamma, 0.0, 1.0)

    # Sparse beauty marks / freckles (deterministic, ~1 per 4096 px)
    dots = rng.random((size // 4, size // 4)).astype(np.float32)
    dot_mask = np.zeros((size, size), dtype=np.float32)
    ys, xs = np.nonzero(dots > 0.9992)
    for y, x in zip(ys, xs):
        yy = np.arange(max(0, y * 4 - 3), min(size, y * 4 + 4))
        xx = np.arange(max(0, x * 4 - 3), min(size, x * 4 + 4))
        gy = np.exp(-((yy - y * 4.0) / 1.7) ** 2)
        gx = np.exp(-((xx - x * 4.0) / 1.7) ** 2)
        dot_mask[np.ix_(yy, xx)] = np.maximum(dot_mask[np.ix_(yy, xx)], gy[:, None] * gx[None, :])
    diff = diff * (1.0 - 0.42 * dot_mask[:, :, None])

    height = 0.55 * pores + 0.45 * seamless_noise(size, rng, beta=0.9)
    # Pore relief is ~0.1 mm; keep the tangent normal subtle or the skin turns into crêpe paper.
    nrm = normal_from_height(height, 0.9)
    # Bare skin is matte: a specular highlight that reads as "plastic" comes from a base far
    # below 0.65 under a 88 W key. 0.70 keeps a soft sheen on the nose/temples only.
    rough = np.clip(0.70 + 0.13 * (mid - 0.5) * 2.0 + 0.05 * (pores - 0.5), 0.52, 0.90)
    return diff, nrm, rough.astype(np.float32)


# --------------------------------------------------------------------------------------
# fabrics / hard surfaces (stand-ins for the CC0 Poly Haven sets)
# --------------------------------------------------------------------------------------

# kind -> (base grey, weave family, weave scale, weave strength, roughness, spec)
FABRIC_PRESETS = {
    "cotton_jersey":   dict(base=0.62, family="knit",   scale=320.0, weave=0.10, rough=0.80, grain=1.1, warm=0.02),
    "knitted_fleece":  dict(base=0.55, family="knit",   scale=150.0, weave=0.22, rough=0.86, grain=1.4, warm=0.03),
    "denim_fabric_04": dict(base=0.46, family="twill",  scale=190.0, weave=0.24, rough=0.78, grain=0.9, warm=-0.02),
    "denim_fabric_06": dict(base=0.42, family="twill",  scale=210.0, weave=0.22, rough=0.80, grain=0.9, warm=-0.02),
    "brown_leather":   dict(base=0.46, family="leather", scale=46.0, weave=0.26, rough=0.52, grain=1.3, warm=0.05),
    "fabric_leather_02": dict(base=0.40, family="leather", scale=58.0, weave=0.24, rough=0.58, grain=1.2, warm=0.04),
    "metal_plate":     dict(base=0.58, family="brushed", scale=260.0, weave=0.10, rough=0.34, grain=0.5, warm=0.0),
    "asphalt_02":      dict(base=0.26, family="grit",   scale=130.0, weave=0.45, rough=0.88, grain=1.8, warm=0.0),
    "concrete_pavement": dict(base=0.52, family="grit", scale=90.0,  weave=0.28, rough=0.84, grain=1.2, warm=0.0),
    "plastered_wall":  dict(base=0.66, family="plaster", scale=60.0, weave=0.26, rough=0.82, grain=0.9, warm=0.01),
    "red_brick":       dict(base=0.42, family="brick",  scale=26.0,  weave=0.55, rough=0.86, grain=1.3, warm=0.12),
    "corrugated_iron": dict(base=0.50, family="corrugated", scale=34.0, weave=0.70, rough=0.58, grain=0.8, warm=0.0),
    "bark_brown_02":   dict(base=0.36, family="bark",   scale=45.0,  weave=0.62, rough=0.90, grain=1.7, warm=0.06),
    "_default":        dict(base=0.55, family="knit",   scale=120.0, weave=0.20, rough=0.80, grain=1.0, warm=0.0),
}


def _weave_field(family: str, size: int, rng: np.random.Generator, scale: float) -> np.ndarray:
    """Return a 0..1 micro-surface height field for one material family."""
    u = np.arange(size, dtype=np.float32) / size
    U, V = np.meshgrid(u, u)

    if family == "knit":
        wale = 0.5 + 0.5 * np.cos(U * scale * np.pi * 2.0)
        course = 0.5 + 0.5 * np.cos(V * scale * np.pi * 0.5)
        loops = np.sin((U * scale * 2.0 + np.sin(V * scale * 1.1) * 0.6) * np.pi) * 0.5 + 0.5
        return np.clip(0.45 * wale + 0.25 * course + 0.30 * loops, 0.0, 1.0).astype(np.float32)
    if family == "twill":
        diag = np.sin((U + V) * scale * np.pi * 2.0) * 0.5 + 0.5
        ribs = np.sin(U * scale * np.pi * 0.35) * 0.5 + 0.5
        return np.clip(0.68 * diag + 0.32 * ribs, 0.0, 1.0).astype(np.float32)
    if family == "leather":
        cell = ridged(seamless_noise(size, rng, beta=1.9))
        wrinkle = ridged(seamless_noise(size, rng, beta=1.1))
        return np.clip(0.60 * cell + 0.40 * wrinkle, 0.0, 1.0).astype(np.float32)
    if family == "brushed":
        streak = seamless_noise(size, rng, beta=0.35)
        rows = np.sin(V * scale * np.pi * 0.08) * 0.5 + 0.5
        return np.clip(0.85 * streak + 0.15 * rows, 0.0, 1.0).astype(np.float32)
    if family == "grit":
        grit = seamless_noise(size, rng, beta=0.4)
        patch = seamless_noise(size, rng, beta=1.8)
        return np.clip(0.55 * grit + 0.45 * patch, 0.0, 1.0).astype(np.float32)
    if family == "plaster":
        blob = seamless_noise(size, rng, beta=1.7)
        fine = seamless_noise(size, rng, beta=0.5)
        return np.clip(0.55 * blob + 0.45 * fine, 0.0, 1.0).astype(np.float32)
    if family == "brick":
        rows = np.floor(V * scale)
        offset = (rows % 2) * 0.5
        bx = (U * scale * 2.0 + offset) % 1.0
        by = (V * scale) % 1.0
        mortar_x = np.clip(np.minimum(bx, 1.0 - bx) / 0.04, 0.0, 1.0)
        mortar_y = np.clip(np.minimum(by, 1.0 - by) / 0.08, 0.0, 1.0)
        mortar = np.minimum(mortar_x, mortar_y)
        grain = seamless_noise(size, rng, beta=0.8)
        return np.clip(mortar * (0.55 + 0.45 * grain), 0.0, 1.0).astype(np.float32)
    if family == "corrugated":
        wave = np.sin(U * scale * np.pi * 2.0) * 0.5 + 0.5
        rust = seamless_noise(size, rng, beta=1.3)
        return np.clip(wave * (0.80 + 0.20 * rust), 0.0, 1.0).astype(np.float32)
    if family == "bark":
        streak = seamless_noise(size, rng, beta=0.9)
        ridges = ridged(np.sin(U * scale * np.pi * 2.0 + streak * 3.0) * 0.5 + 0.5)
        return np.clip(0.6 * ridges + 0.4 * streak, 0.0, 1.0).astype(np.float32)
    return seamless_noise(size, rng, beta=1.2)


def fabric_maps(asset_id: str, size: int, seed: int):
    """Diffuse (grey, un-tinted), tangent normal, roughness, AO for one Poly Haven stand-in."""
    preset = FABRIC_PRESETS.get(asset_id, FABRIC_PRESETS["_default"])
    rng = np.random.default_rng(seed)
    height = _weave_field(preset["family"], size, rng, preset["scale"])
    macro = seamless_noise(size, rng, beta=1.6)
    tone = np.clip(preset["base"] * (0.82 + 0.30 * (macro - 0.5) * 2.0 + preset["weave"] * (height - 0.5)),
                   0.02, 1.0)
    diff = np.empty((size, size, 3), dtype=np.float32)
    warm = float(preset["warm"])
    diff[:, :, 0] = np.clip(tone * (1.0 + warm), 0.0, 1.0)
    diff[:, :, 1] = tone
    diff[:, :, 2] = np.clip(tone * (1.0 - warm), 0.0, 1.0)

    nrm = normal_from_height(height, 2.2 * float(preset["grain"]) * 3.0)
    rough = np.clip(preset["rough"] + 0.10 * (height - 0.5) + 0.04 * (macro - 0.5), 0.12, 0.97)
    ao = np.clip(0.78 + 0.22 * height, 0.0, 1.0)
    return diff, nrm, rough.astype(np.float32), ao.astype(np.float32)


# --------------------------------------------------------------------------------------
# eyebrow / eyelash strand atlas (used when the CC0 alpha cards are unavailable)
# --------------------------------------------------------------------------------------


def brow_lash_atlas(size: int, seed: int, hair_rgb=(0.036, 0.028, 0.024),
                    scar_notch: bool = True):
    """512x1024 RGBA strand atlas: bottom half = eyebrow hairs, top half = eyelashes.

    Same layout/UV contract as `pbr_textures.build_brows_and_lashes_material`, so the rest of
    the pipeline (UV remap into the two halves) is unchanged. Strands are drawn analytically
    (tapered capsules) instead of being sampled from a photo card.
    """
    rng = np.random.default_rng(seed)
    h = size * 2
    u = (np.arange(size, dtype=np.float32) + 0.5) / size
    v = (np.arange(size, dtype=np.float32) + 0.5) / size
    U, V = np.meshgrid(u, v)

    # --- eyebrow half (v -> 0..1 of this half): dense, directionally combed short hairs
    alpha_b = np.zeros((size, size), dtype=np.float32)
    shade_b = np.ones((size, size), dtype=np.float32)
    for _ in range(520):
        x0 = rng.uniform(-0.05, 0.75)
        y0 = rng.uniform(0.02, 0.98)
        ang = rng.uniform(0.55, 0.95)          # mostly diagonal, sweeping outward
        ln = rng.uniform(0.30, 0.62)
        wid = rng.uniform(0.008, 0.018)
        bright = rng.uniform(0.55, 1.15)
        dx, dy = np.cos(ang), np.sin(ang)
        px, py = U - x0, V - y0
        along = px * dx + py * dy
        across = -px * dy + py * dx
        taper = np.clip(1.0 - np.maximum(along, 0.0) / ln, 0.0, 1.0) ** 0.75
        profile = np.exp(-((across / (wid * np.maximum(taper, 0.08))) ** 2) * 1.6)
        s = profile * (along > 0.0) * (along < ln) * taper
        better = s > alpha_b
        shade_b = np.where(better, bright, shade_b)
        alpha_b = np.maximum(alpha_b, s)
    # Brow body: soft volume so the arch reads even where strands are sparse
    brow_body = np.clip(1.0 - ((V - 0.42) / 0.40) ** 2 - ((U - 0.34) / 0.52) ** 2, 0.0, 1.0) ** 0.6
    alpha_b = np.clip(np.maximum(alpha_b, brow_body * 0.55) * 1.35, 0.0, 1.0)

    if scar_notch:
        ang = np.radians(64.0)
        dx, dy = U - 0.62, V - 0.60
        across = -dx * np.sin(ang) + dy * np.cos(ang)
        notch = np.exp(-((across / 0.026) ** 2)) * (V > 0.40)
        alpha_b *= (1.0 - notch * 0.94)

    # --- eyelash half: long, sparse, curved lashes growing from the lid edge (V ~ 0.0)
    alpha_l = np.zeros((size, size), dtype=np.float32)
    shade_l = np.ones((size, size), dtype=np.float32)
    for _ in range(150):
        x0 = rng.uniform(0.02, 0.98)
        ln = rng.uniform(0.42, 0.90)
        curve = rng.uniform(-0.20, 0.20)
        wid = rng.uniform(0.006, 0.013)
        bright = rng.uniform(0.50, 1.0)
        t = np.clip(V / ln, 0.0, 1.0)
        centre = x0 + curve * t * t
        taper = (1.0 - t) ** 0.7
        profile = np.exp(-(((U - centre) / (wid * np.maximum(taper, 0.06))) ** 2) * 1.5)
        s = profile * (t <= 1.0) * taper
        better = s > alpha_l
        shade_l = np.where(better, bright, shade_l)
        alpha_l = np.maximum(alpha_l, s)

    base = np.array(hair_rgb, dtype=np.float32)
    rgba = np.zeros((h, size, 4), dtype=np.float32)
    rgba[:size, :, :3] = np.clip(base[None, None, :] * shade_b[:, :, None], 0.0, 1.0)
    rgba[:size, :, 3] = alpha_b
    rgba[size:, :, :3] = np.clip(base[None, None, :] * shade_l[:, :, None], 0.0, 1.0)
    rgba[size:, :, 3] = alpha_l
    return rgba


def strand_atlas(size: int, cols: int, rows: int, seed: int,
                 hair_rgb=(0.036, 0.028, 0.024), kind: str = "brow") -> np.ndarray:
    """RGBA atlas of individual hair strands, one per grid cell (cols x rows).

    Each cell carries ONE strand running from its root (v = 0, bottom) to its tip (v = 1, top),
    tapering to a point, so a single quad card mapped to a cell renders exactly one hair.
    `kind` selects the silhouette: "brow" (short, thick, strong taper, slight curve) or
    "lash" (long, very thin, pronounced outward curl).
    """
    rng = np.random.default_rng(seed)
    out = np.zeros((size, size, 4), dtype=np.float32)
    cw, ch = size // cols, size // rows
    for r in range(rows):
        for c in range(cols):
            col = np.zeros((ch, cw), dtype=np.float32)
            shade = np.ones((ch, cw), dtype=np.float32)
            if kind == "brow":
                n_hairs = 3                      # a brow cell holds a small tuft
                base_w = rng.uniform(0.09, 0.17)
                curl = rng.uniform(-0.22, 0.22)
                tip = rng.uniform(0.80, 1.0)
            else:
                n_hairs = 1
                base_w = rng.uniform(0.035, 0.075)
                curl = rng.uniform(-0.30, 0.30)
                tip = rng.uniform(0.88, 1.0)
            u = (np.arange(cw, dtype=np.float32) + 0.5) / cw
            v = (np.arange(ch, dtype=np.float32) + 0.5) / ch
            U, V = np.meshgrid(u, v)          # V = 0 at bottom row (root)
            for h in range(n_hairs):
                x0 = rng.uniform(0.25, 0.75)
                dw = base_w * rng.uniform(0.7, 1.25)
                bright = rng.uniform(0.55, 1.15)
                t = np.clip(V / tip, 0.0, 1.0)
                centre = x0 + curl * (t ** 1.6)
                taper = np.clip(1.0 - t, 0.0, 1.0) ** (0.45 if kind == "brow" else 0.30)
                width = dw * np.maximum(taper, 0.05)
                alpha = np.exp(-(((U - centre) / width) ** 2) * 1.4) * (t <= 1.0)
                better = alpha > col
                shade = np.where(better, bright, shade)
                col = np.maximum(col, alpha)
            out[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw, :3] = np.clip(
                np.array(hair_rgb, dtype=np.float32)[None, None, :] * shade[:, :, None], 0.0, 1.0)
            out[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw, 3] = np.clip(col * 0.95, 0.0, 1.0)
    return out


def solid_hair_material_rgb(hair_rgb):
    """Constant hair colour tuple for strand geometry (eyebrows, lashes, stubble cards)."""
    return tuple(float(c) for c in hair_rgb)


def lip_mask(X, Z, mouth_z, upper_lip_z, lower_lip_z, half_w=0.0230):
    """Vermilion mask of both lips on a (X, Z) grid, 1 at the centre of a lip, 0 outside.

    Landmarks give lower_lip_z < mouth_z < upper_lip_z. Each lobe is a half-ellipse with a
    sin^p profile, so it reaches exactly 0 at its own border; the width tapers to 0 at the
    commissures and the upper border dips over the philtrum (cupid's bow).

    Every term is a *real* zero outside its span - note that np.clip(t, 0, 1) does NOT do that
    (it saturates at 1, i.e. maximum), which is how an earlier version ended up painting the
    whole face.
    """
    up_h = max((upper_lip_z - mouth_z) * 0.78, 0.004)
    lo_h = max((mouth_z - lower_lip_z) * 0.92, 0.004)
    dip = 1.0 - 0.16 * np.exp(-(X / 0.0055) ** 2)

    # Clamp the *argument* (not the result) and zero out the invalid side: np.cos/np.sin of a
    # value outside their quarter arc would otherwise be fed to a fractional power -> NaN.
    v = np.clip(np.abs(X) / half_w, 0.0, 1.0)
    # np.maximum(..., 0.0) is essential, not cosmetic: in float32 cos(pi/2 * 1.0) evaluates to
    # about -1e-17, and a negative base raised to a fractional power is NaN. At texture resolution
    # (1024^2) enough pixels hit exactly that value to poison ~90 % of the skin maps.
    across = np.maximum(np.cos(np.pi * 0.5 * v), 0.0) ** 0.55

    up_raw = (Z - mouth_z) / (up_h * dip)
    lo_raw = (mouth_z - Z) / lo_h
    # Keep the *raw* parameter for the "inside" test, clamp only for the trigonometry: a clamped
    # parameter alone would turn every point above the lip into sin(pi/2) = 1, i.e. full lip.
    inside_up = ((up_raw >= 0.0) & (up_raw < 1.0)).astype(np.float64)
    inside_lo = ((lo_raw >= 0.0) & (lo_raw < 1.0)).astype(np.float64)
    # A half-ellipse has to start at full width *at the opening* and die at the border, so the
    # profile is sin(pi/2 * (1 - t)), not sin(pi/2 * t) - the latter peaks at the outer border and
    # leaves the lip line itself naked.
    up = (np.maximum(np.sin(np.pi * 0.5 * (1.0 - np.clip(up_raw, 0.0, 1.0))), 0.0) ** 0.85
          * inside_up)
    lo = (np.maximum(np.sin(np.pi * 0.5 * (1.0 - np.clip(lo_raw, 0.0, 1.0))), 0.0) ** 0.65
          * inside_lo)
    return np.clip((up + lo) * across, 0.0, 1.0)
