#!/usr/bin/env python3
"""Build a reference-vs-render contact sheet for the AAA quality gate.

Runs in system Python (Pillow). Invoked as:

  Tools/uwp review-sheet <asset> [--repo PATH] [--ref IMG ...] [--renders IMG ...]
                         [--out PATH] [--title TEXT]

If --ref / --renders are omitted, files are discovered under
Docs/ArtDirection/References/<asset>/, Docs/ArtDirection/Concepts/,
and Assets/**/<asset>*preview*.png (plus common contact sheets).
"""
from __future__ import annotations

import argparse
import os
import sys
from glob import glob

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.stderr.write("review-sheet requires Pillow (pip install pillow)\n")
    sys.exit(4)

CELL_W, CELL_H = 480, 360
PAD = 12
HEADER_H = 44
LABEL_H = 28
BG = (32, 32, 34, 255)
HEADER_BG = (20, 20, 22, 255)
REF_BAR = (40, 70, 110, 255)
REN_BAR = (70, 50, 20, 255)
TEXT = (240, 240, 240, 255)
MUTED = (180, 180, 180, 255)
BANNER = (120, 30, 30, 255)


def _font(size: int):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ):
        if os.path.isfile(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


FONT = _font(16)
FONT_SM = _font(13)
FONT_LG = _font(22)


def _load(path: str) -> Image.Image:
    im = Image.open(path)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA")
    elif im.mode == "RGB":
        im = im.convert("RGBA")
    return im


def _fit(im: Image.Image, box_w: int, box_h: int) -> Image.Image:
    src = im.convert("RGBA")
    scale = min(box_w / src.width, box_h / src.height, 1.0) if src.width and src.height else 1.0
    # Always fit inside the cell, including upscale of tiny previews so the sheet is readable.
    scale = min(box_w / max(src.width, 1), box_h / max(src.height, 1))
    nw, nh = max(1, int(src.width * scale)), max(1, int(src.height * scale))
    return src.resize((nw, nh), Image.Resampling.LANCZOS)


def _label(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def _discover(repo: str, asset: str):
    refs, renders = [], []
    ref_dir = os.path.join(repo, "Docs", "ArtDirection", "References", asset)
    if os.path.isdir(ref_dir):
        for p in sorted(glob(os.path.join(ref_dir, "*"))):
            if p.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                refs.append(p)
    # Jason concept art lives under Concepts/ until a dedicated board is filled.
    concepts = os.path.join(repo, "Docs", "ArtDirection", "Concepts")
    if os.path.isdir(concepts):
        key = asset.replace("SK_", "").replace("v2", "").replace("_", "").lower()
        for p in sorted(glob(os.path.join(concepts, "*"))):
            base = os.path.basename(p).lower()
            if p.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) and (
                asset.lower() in base or (key and key in base.replace("_", ""))
            ):
                if p not in refs:
                    refs.append(p)
    for pattern in (
        os.path.join(repo, "Assets", "**", f"{asset}*_preview*.png"),
        os.path.join(repo, "Assets", "**", f"{asset}_preview*.png"),
        os.path.join(repo, "Assets", "**", f"{asset}*contact*.png"),
    ):
        for p in sorted(glob(pattern, recursive=True)):
            if p not in renders:
                renders.append(p)
    return refs, renders


def _row(images: list[tuple[str, Image.Image]], bar, title: str, empty_msg: str) -> Image.Image:
    n = max(len(images), 1)
    w = n * CELL_W + (n + 1) * PAD
    h = HEADER_H + LABEL_H + CELL_H + PAD * 2
    sheet = Image.new("RGBA", (w, h), BG)
    draw = ImageDraw.Draw(sheet)
    draw.rectangle([0, 0, w, HEADER_H], fill=bar)
    draw.text((PAD, 12), title, font=FONT_LG, fill=TEXT)
    if not images:
        draw.rectangle([PAD, HEADER_H + PAD, w - PAD, h - PAD], fill=BANNER)
        draw.text((PAD * 2, HEADER_H + CELL_H // 2), empty_msg, font=FONT, fill=TEXT)
        return sheet
    x = PAD
    y = HEADER_H + PAD
    for path, im in images:
        fitted = _fit(im, CELL_W, CELL_H)
        cx = x + (CELL_W - fitted.width) // 2
        cy = y + LABEL_H + (CELL_H - fitted.height) // 2
        cell = Image.new("RGBA", (CELL_W, CELL_H), (16, 16, 16, 255))
        sheet.paste(cell, (x, y + LABEL_H))
        sheet.paste(fitted, (cx, cy), fitted)
        draw.text((x, y), _label(path)[:48], font=FONT_SM, fill=MUTED)
        x += CELL_W + PAD
    return sheet


def compose(title: str, refs: list[str], renders: list[str], out: str) -> None:
    ref_ims = [(p, _load(p)) for p in refs]
    ren_ims = [(p, _load(p)) for p in renders]
    ref_row = _row(ref_ims, REF_BAR, "REFERENCE", "NO REFERENCE BOARD — do not score this asset as production-ready")
    ren_row = _row(ren_ims, REN_BAR, "RENDER (actual pixels)", "NO RENDERS — cannot review")
    w = max(ref_row.width, ren_row.width, 640)
    title_h = 56
    h = title_h + ref_row.height + ren_row.height
    canvas = Image.new("RGBA", (w, h), BG)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, w, title_h], fill=HEADER_BG)
    draw.text((PAD, 16), title, font=FONT_LG, fill=TEXT)
    def _paste(row, y):
        if row.width < w:
            padded = Image.new("RGBA", (w, row.height), BG)
            padded.paste(row, (0, 0))
            row = padded
        canvas.paste(row, (0, y))
    _paste(ref_row, title_h)
    _paste(ren_row, title_h + ref_row.height)
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    canvas.convert("RGB").save(out, "PNG", optimize=True)
    print(f"review-sheet wrote {out} ({canvas.width}x{canvas.height}; {len(refs)} refs, {len(renders)} renders)")


def build_parser():
    p = argparse.ArgumentParser(prog="uwp review-sheet")
    p.add_argument("asset", help="asset id, e.g. SK_Jason or WPN_Pistol_01")
    p.add_argument("--repo", default=None, help="repo root (default: two levels above this script)")
    p.add_argument("--ref", nargs="*", default=None, help="reference image paths")
    p.add_argument("--renders", nargs="*", default=None, help="render / preview image paths")
    p.add_argument("--out", default=None, help="output PNG")
    p.add_argument("--title", default=None)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(args.repo or os.path.join(here, "..", ".."))
    refs = list(args.ref or [])
    renders = list(args.renders or [])
    if not refs or not renders:
        d_refs, d_renders = _discover(repo, args.asset)
        if not refs:
            refs = d_refs
        if not renders:
            renders = d_renders
    missing = [p for p in refs + renders if not os.path.isfile(p)]
    if missing:
        sys.stderr.write("review-sheet: missing files:\n  " + "\n  ".join(missing) + "\n")
        return 4
    if not renders:
        sys.stderr.write("review-sheet: no renders found for %s\n" % args.asset)
        return 4
    out = args.out or os.path.join(repo, "Docs", "Reviews", "sheets", f"{args.asset}_ref_compare.png")
    title = args.title or f"{args.asset} — reference vs render (quality gate)"
    compose(title, refs, renders, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
