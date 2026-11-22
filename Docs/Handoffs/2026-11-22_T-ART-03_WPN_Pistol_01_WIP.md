# T-ART-03 (Bot 1 numbering; TASK_BOARD row = T-ART-05 "Pistol") – WPN_Pistol_01 quality pass – WIP HANDOFF

- **From:** Bot 2 · **Date:** 2026-11-22 · **Status:** WIP / DRAFT PR (project handed off mid-task). Shipped asset on main is still v0.
- **Note on IDs:** TASK_BOARD lists T-ART-03 = LA kit and T-ART-05 = pistol; Bot 1's message called the pistol pass T-ART-03. Board not changed here; Bot 1 should reconcile.

## Done
- bot2/dev brought to origin/main 038de21 (fast-forward, no force push). Old unpushed merge 8f658db + uncommitted old pistol work discarded after backup.
- Reference board: `Docs/ArtDirection/References/WPN_Pistol_01/` (8-tile collage PNG 176 KB + REFERENCES.md with Wikimedia Commons sources/licenses).
- "Before" renders of v0 (Cycles CPU, 32 spp): `Docs/ArtDirection/Reviews/WPN_Pistol_01/before/{left,right,q3,port}.jpg` (diamond-plate texture, open guard, blocky forms).
- New generator for `Tools/uwp build-weapon` (replaces Poly Haven metal_plate path):
  - `weapons/hardsurface.py` – profile/prism/boolean/bevel helpers, HP vs LP finishing (LP triangulated, hard edges = seams).
  - `weapons/pistol_hs.py` – parts in contract coordinates: slide (beveled nose, port, rear+front serrations, cover plate, "9x19" mark, 3-dot sights, extractor), barrel (flush crown, hood in port, bore), frame (raked grip with palm swell + beavertail, **closed trigger guard**, rail, guide rod, slide stop/takedown/mag release, pins), trigger with safety blade, magazine.
  - `weapons/hs_materials.py` – HP bake shaders: black-nitride steel, barrel steel, polymer with object-space stipple zone, edge wear from Bevel-node curvature, AO.
  - `weapons/baker.py` – shared UV atlas, Cycles selected-to-active bakes (albedo, roughness, metallic, AO, tangent normal), D/N/ORM packing + dilation.
  - `weapons/render_review.py` – fixed-camera Cycles review renders (left/right/top/3q/3q-back/serrations/stipple/sights/port/muzzle).
  - `build_weapon.py` – new flow; sockets, 4-bone WeaponRig and the 3 clips copied unchanged (contract kept).
  - `Config/Weapons/WPN_Pistol_01.json` – 2048 px, finishes, stipple zone.
- Smoke test: `UWP_WEAPON_FAST=1 Tools/uwp build-weapon Config/Weapons/WPN_Pistol_01.json` runs end to end (7.7 s): LP 2,526 tris (Frame 858, Slide 668, Barrel 328, Trigger 440, Magazine 232), HP 22,647 tris, 96.9 % atlas coverage. That fast .blend was **not** committed (v0 .blend restored).

## Missing (next owner)
1. Look at the new geometry: no "after" renders yet. Known risks: top view framing in render_review (camera roll), light rig too dark for black guns, engraving orientation, grip bevel/union artifacts, mag-release position on the beveled grip edge.
2. Full bake (2048 px, 64 AO spp) + `Tools/uwp export Blender/Source/Weapons/WPN_Pistol_01/WPN_Pistol_01.blend`, then check the GLB size (N map is PNG 2048) for LFS.
3. Render-compare-improve loop against the board until every quality-gate category is >= 4. Then before/after sheet.
4. `Tools/underworld_pipeline/tests/run_tests.sh`, Godot headless import, `Tests/run_all.sh` (with `test_weapon.gd` on the real glb). **None of them were run on this branch state.**
5. Update docs: PIPELINE_WEAPONS.md (still describes the metal_plate path), ASSET_REGISTRY, TASK_BOARD, DEVELOPMENT_LOG; self-scorecard in the PR.

## Old prototype (superseded, kept for ideas)
`Docs/Handoffs/WIP_T-ART-03_old_pistol_prototype/` = Bot 2's earlier standalone pistol scripts (geometry, bake materials, build/bake, render, fit-on-Jason render, verify scripts). Most helpers were already ported into the new pipeline; `render_fit_jason.py` and the verify scripts are still useful for the fit/QA step. The binary outputs (old .blend/.glb/renders) were not kept.

## Self-scorecard (honest, WIP)
Not scored: there are no after renders yet, so no category can be claimed >= 4.
