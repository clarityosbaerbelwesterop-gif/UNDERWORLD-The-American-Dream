"""Automated silhouette & anatomical proportion comparison against turnaround concept art (T-PIPE-03).

Compares orthographic/telephoto front & side Cycles renders of a character against the
corresponding panels of a 4-view turnaround sheet (front | 3/4 | side | back), using pure
numpy + bpy.data.images (zero external pip dependencies).

Outputs:
  - Front & side silhouette IoU (after tight vertical height normalization & horizontal centering)
  - Anatomical width/depth-to-height proportion slices at key landmarks:
      head (92%), shoulders (79%), chest (70%), waist (58%), hips (49%), thighs (38%), calves (18%)
  - Pass/warn status against configurable tolerances
"""
import json
import os

import bpy
import numpy as np


def _load_rgb_np(path):
    """Load image into float32 (H, W, 3) array with row 0 = TOP of image (standard image order)."""
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size[0], img.size[1]
    arr = np.array(img.pixels[:], dtype=np.float32).reshape((h, w, 4))[:, :, :3]
    bpy.data.images.remove(img)
    return arr[::-1].copy()  # flip from OpenGL bottom-up -> top-down


def _segment_foreground(rgb, bg_thresh=0.075):
    """Segment character silhouette using per-row studio backdrop subtraction (handles floor gradients cleanly!)."""
    h, w = rgb.shape[:2]
    margin = max(6, w // 12)
    # Per-row background color from left & right border strips (subtracts studio floor horizon cleanly!)
    border_rows = np.concatenate([rgb[:, :margin, :], rgb[:, -margin:, :]], axis=1)
    row_bg = np.median(border_rows, axis=1)  # (H, 3)
    dist = np.linalg.norm(rgb - row_bg[:, None, :], axis=2)
    # Suppress soft floor cast shadow near feet slightly
    thresh = np.full((h, w), bg_thresh, dtype=np.float32)
    thresh[int(h * 0.85):, :] = bg_thresh * 1.50
    mask = dist > thresh

    col_counts = mask.sum(axis=0)
    if col_counts.max() == 0:
        return mask
    valid_cols = col_counts >= max(3, int(h * 0.015))
    if not valid_cols.any():
        return mask
    best_s, best_e = 0, 0
    cur_s = None
    for x, ok in enumerate(valid_cols):
        if ok and cur_s is None:
            cur_s = x
        elif not ok and cur_s is not None:
            if (x - cur_s) > (best_e - best_s):
                best_s, best_e = cur_s, x
            cur_s = None
    if cur_s is not None and (w - cur_s) > (best_e - best_s):
        best_s, best_e = cur_s, w
    out = np.zeros_like(mask)
    out[:, best_s:best_e] = mask[:, best_s:best_e]
    return out


def _normalize_mask(mask, out_h=256, out_w=160):
    """Tight-crop foreground height to out_h (preserving aspect ratio) and center horizontally on (out_h, out_w)."""
    ys, xs = np.where(mask)
    if len(ys) < 20:
        return np.zeros((out_h, out_w), dtype=bool), {}
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    crop = mask[y0:y1, x0:x1]
    ch, cw = crop.shape
    scale = out_h / max(ch, 1)
    nw = max(1, min(out_w, int(round(cw * scale))))

    # Nearest-neighbor resize into (out_h, nw)
    ry = np.linspace(0, ch - 1, out_h).astype(np.int32)
    rx = np.linspace(0, cw - 1, nw).astype(np.int32)
    resized = crop[np.ix_(ry, rx)]

    canvas = np.zeros((out_h, out_w), dtype=bool)
    # Center by horizontal center-of-mass so slight stance asymmetry doesn't penalize IoU unfairly
    cx_res = float(np.where(resized)[1].mean())
    shift_x = int(round(out_w * 0.5 - cx_res))
    dst_x0 = max(0, shift_x)
    dst_x1 = min(out_w, shift_x + nw)
    src_x0 = max(0, -shift_x)
    src_x1 = src_x0 + (dst_x1 - dst_x0)
    if dst_x1 > dst_x0:
        canvas[:, dst_x0:dst_x1] = resized[:, src_x0:src_x1]

    # Compute anatomical slice width/height ratios (y_frac measured from feet=0.0 up to crown=1.0)
    slices = {
        "head_92": 0.92,
        "shoulders_79": 0.79,
        "chest_70": 0.70,
        "waist_58": 0.58,
        "hips_49": 0.49,
        "thighs_38": 0.38,
        "calves_18": 0.18,
    }
    props = {"aspect_w_over_h": round(cw / max(ch, 1), 4)}
    for nm, yf in slices.items():
        row_c = int(round((1.0 - yf) * (out_h - 1)))
        r0, r1 = max(0, row_c - 3), min(out_h, row_c + 4)
        band = canvas[r0:r1, :]
        # Span width (outermost left to outermost right foreground pixels)
        cols = np.where(band.any(axis=0))[0]
        w_ratio = float(cols[-1] - cols[0] + 1) / out_h if len(cols) >= 2 else 0.0
        props[nm] = round(w_ratio, 4)
    return canvas, props


def compare_turnaround(concept_path, front_render_path, side_render_path, out_report_path=None):
    """Compare front & side renders against a 4-panel turnaround concept sheet (front | 3/4 | side | back)."""
    concept = _load_rgb_np(concept_path)
    ch, cw = concept.shape[:2]
    # 4-view horizontal turnaround panels: [0..25%]=front, [25..50%]=3/4, [50..75%]=side, [75..100%]=back
    panel_front = concept[:, :int(cw * 0.25)]
    panel_side = concept[:, int(cw * 0.50):int(cw * 0.75)]

    results = {
        "concept_art": concept_path,
        "front_render": front_render_path,
        "side_render": side_render_path,
        "views": {},
    }

    for vname, c_rgb, r_path in (
        ("front", panel_front, front_render_path),
        ("side", panel_side, side_render_path),
    ):
        if not r_path or not os.path.isfile(r_path):
            continue
        r_rgb = _load_rgb_np(r_path)
        cm = _segment_foreground(c_rgb)
        rm = _segment_foreground(r_rgb)
        cn, c_props = _normalize_mask(cm)
        rn, r_props = _normalize_mask(rm)

        inter = int(np.logical_and(cn, rn).sum())
        union = int(np.logical_or(cn, rn).sum())
        iou = round(inter / max(union, 1), 4)

        deltas = {}
        for k in c_props:
            if k in r_props:
                deltas[k] = round(r_props[k] - c_props[k], 4)
        mean_abs_delta = round(float(np.mean([abs(v) for v in deltas.values()])) if deltas else 0.0, 4)
        results["views"][vname] = {
            "silhouette_iou": iou,
            "concept_proportions": c_props,
            "render_proportions": r_props,
            "proportion_deltas": deltas,
            "mean_abs_proportion_delta": mean_abs_delta,
        }

    ious = [v["silhouette_iou"] for v in results["views"].values()]
    deltas_all = [v["mean_abs_proportion_delta"] for v in results["views"].values()]
    results["mean_iou"] = round(float(np.mean(ious)) if ious else 0.0, 4)
    results["mean_proportion_delta"] = round(float(np.mean(deltas_all)) if deltas_all else 0.0, 4)
    results["pass"] = bool(results["mean_iou"] >= 0.55 and results["mean_proportion_delta"] <= 0.08)

    if out_report_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_report_path)), exist_ok=True)
        with open(out_report_path, "w") as f:
            json.dump(results, f, indent=2)
            f.write("\n")
    return results
