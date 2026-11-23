# CLAUDE.md – UNDERWORLD – THE AMERICAN DREAM

**Read first:** `Docs/CLAUDE_CODE_HANDOFF.md` (full project handoff), then `Docs/TASK_BOARD.md`,
`Docs/QUALITY_GATE.md`, `Docs/PROJECT_STATUS.md`, `Docs/BLOCKERS.md`, `Docs/SKILLS_AND_TOOLS.md`.

Original open-world third-person crime shooter (Godot 4.7.2 + headless Blender 5.2.4 LTS, glTF, Git LFS).
Owner: Bärbel Westerop (ClarityCompassAI) – report **in German**, honestly, never fake completion.

## Key commands
```bash
git pull && git lfs pull
./Tests/run_all.sh                         # merge gate: must print RUN_ALL: PASS (fresh worktree)
Tools/uwp validate|export <file.blend>     # asset pipeline (Blender headless); Tools/uwp --help
Tools/uwp build-character|build-weapon|build-vehicle <spec.json> ; Tools/uwp build-env ; build-shared-anims
Tools/uwp review-sheet <asset>             # reference vs render sheet (Pillow)
/workspace/tools/godot --headless --path GodotProject --import
Tools/godot_phase8_capture.sh --scene res://... --out Docs/Reviews/sheets/<x>.png   # in-engine shot, xvfb + llvmpipe
```
Binaries: `/workspace/tools/blender/blender`, `/workspace/tools/godot` (override with `BLENDER=` / `GODOT=`).

## Rules
- One task per branch/PR (`[T-XXX-NN]` in commits); update TASK_BOARD + logs in the same PR.
- Run `Tests/run_all.sh` before and after changes; merge only green with `gh pr merge N --merge --match-head-commit SHA`.
- No force-push, no history rewrite; update branches by merging `origin/main`.
- **Git LFS is mandatory:** `git lfs install` before the first commit; never commit .glb/.png/.blend/.jpg/.wav/... as raw blobs; check `git lfs ls-files` and that staged binaries are pointers.
- **Do not self-merge.** Open a PR and stop; Bot 1 reviews and merges. Exception only if the work order contains an explicit merge line *and* every gate is green.
- **Quality gate:** no asset is PRODUCTION-READY/"AAA" without reference board, Cycles renders, independent 0–5 review (≥ 4 in all categories), `uwp` validation and a Godot Phase 8 capture. All current hero assets are REJECT/WIP.
- TD-004 axes (Blender −Y = Godot +Z, 1 u = 1 m), TD-005 naming (no `_Loop` action names), TD-010 physics layers + input map only via `Scripts/tools/setup_input_map.gd`, budgets `Config/asset_budgets.json`.
- Third-party assets: CC0 / CC-BY only, logged in `Docs/ASSET_LICENSES.md`. LFS budget ~1 GB (≈73 MB used).
- Never run third-party installers / MCP servers / plugins without review (`Docs/SKILLS_AND_TOOLS.md`).
- `Tools/underworld_pipeline/godot/uw_lod_post_import.gd` ≡ `GodotProject/Scripts/import/uw_lod_post_import.gd` (byte-identical).
- No GPU on the original box: say what is unverified visually.
