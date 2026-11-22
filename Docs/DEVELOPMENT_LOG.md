# Development Log

Append-only, newest on top. `YYYY-MM-DD HH:MM (Europe/Berlin) · Bot N · Task ID · what was done · how it was verified`.

## 2026-11-22 · Bot 2
- **T-PIPE-01** (10:05 Europe/Berlin) `Tools/underworld_pipeline/` + `Tools/uwp` wrapper: validate / export / validate-all / export-all (budgets from `Config/asset_budgets.json`, naming TD-005, transforms/units/origin/front axis TD-004, geometry, UV/material/texture, skin ≤ 4 influences, humanoid bones per REQ-GP01-JASON, sockets, animations), Decimate LODs (`_LOD1/_LOD2` + `uw_visibility_range` extras + Godot post-import script), collision (`-convcolonly`/`-colonly`), GLB export, Cycles CPU preview, manifest + JSON report, Blender round-trip, exit codes 0–5. Docs in `Tools/README.md`. Verified: `Tools/underworld_pipeline/tests/run_tests.sh` → `UWP TESTS: PASS` (106 checks: Blender export + re-import, Godot 4.7.2 headless import of LODs/collision/skeleton/animations, character +Z front); `Tests/run_pipeline_smoke.sh` → `PIPELINE SMOKE TEST: PASS`; `Tools/uwp validate-all` → PASS (1 asset).

## 2026-11-22 · Bot 1
- **T-BOOT-01** Installed Blender 5.2.4 LTS (sha256 verified) and Godot 4.7.2-stable (sha512 verified) to `/workspace/tools/`, archives deleted. Verified: `blender -b` runs bpy (`BPY_OK 5.2.4 LTS`), `godot --headless --version` → `4.7.2.stable.official.ed1daf0bf`. Installed git-lfs 3.8.1.
- **T-BOOT-02** Created private repo `clarityosbaerbelwesterop-gif/UNDERWORLD-The-American-Dream`, structure, `.gitignore`, `.gitattributes` (LFS for blend/glb/images/audio/fonts).
- **T-BOOT-03** Wrote all project docs, task board (24 tasks), GDD v0.1, M01 mission design, handoff protocol.
- **T-PIPE-00** `Tools/blender_export.py` + `GodotProject/` + `GodotProject/Tests/smoke_test.gd` + `Tests/run_pipeline_smoke.sh`. Clean run (deleted `.godot/` cache first) → `PIPELINE SMOKE TEST: PASS`. Negative test (expected mesh count changed to 3) → exit 1, as intended.
