# Asset review — `<ASSET_ID>` `<version>`

- **Date:** YYYY-MM-DD HH:MM (Europe/Berlin)
- **Phase claimed by creator:** 1 Blockout / 2 HQ model / 3 Materials / 4 Renders / 7 Validation / 8 Godot
- **Creator:** Bot 2 / Lead TD / other
- **Art reviewer (Bot 1):**
- **Engine reviewer (Bot 3):**
- **Reference board:** `Docs/ArtDirection/References/<ASSET_ID>/` (or “none — automatic fail for production”)
- **Review sheet:** `Docs/Reviews/sheets/<ASSET_ID>_ref_compare.png`
- **Renders inspected:** list paths (must be actual PNGs, not a viewport memory)
- **Phase 8 in-engine shot:** path or “not done”
- **`uwp validate` / `export`:** PASS/FAIL + report path
- **Triangle count / budget:**

## Reference comparison

What matches the board, what deviates, what was inferred without coverage.

## Scores

Rate 0–5. Pass requires ≥ 4 in every applicable category. Do not adjust a score to force a pass.

| Category | Bot 1 (art) | Bot 3 (engine) | Notes |
|---|---:|---:|---|
| Silhouette |  |  |  |
| Proportions |  |  |  |
| Geometry |  |  |  |
| Materials |  |  |  |
| Textures |  |  |  |
| Lighting |  |  |  |
| Visual detail |  |  |  |
| Animation quality |  |  |  |
| Technical optimization |  |  |  |
| Engine integration |  |  |  |

`N/A` only when the category does not apply.

## Defects

Numbered, specific, tied to a render or in-engine shot.

1.

## Limitations (honest)

What is still missing even if this version is useful as a blockout or WIP.

## Verdict

**PASS** or **REJECT**

A PASS requires completed Phases 1–8, independent Bot 1 and Bot 3 reviews, all applicable scores ≥ 4, and no manipulated numbers. Only a PASS may set the registry status to `PRODUCTION-READY`.
