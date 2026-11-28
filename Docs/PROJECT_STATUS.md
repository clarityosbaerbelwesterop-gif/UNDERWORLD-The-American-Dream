# Project Status

_Last update: 2026-11-28 (Europe/Berlin) by Bot 1 (review of PRs #42–#44)_

**2026-11-28 – Bot 1 review of #42, #43, #44 (main `69d3197` → this PR):** every merge gated on a fresh worktree with `git lfs pull`.
- Baseline main `69d3197`: `RUN_ALL: PASS` **1228 checks** (counted = smoke + all "checks passed" lines).
- **#43 T-AUD-01** audio (Claude Code) merged `b8d2f35`: **1269** (+41 `test_audio`); `UW_AUDIO_SABOTAGE=1` → 15 FAIL, a deleted Ogg on a fresh import → 2 FAIL. Procedural: the generator reads no external sound (licence clean). Ogg were gitignored → committed to LFS in **#47** `74583a8` (323 files, ~10 MB). TD-034 ACCEPTED with change. Nobody has listened yet.
- **#42 T-VEH-03** plane + motorcycle (Claude Code): 3 new commits, docs conflicts with #43 resolved in **#45** `87135f8`: **1273** (+4 import checks). Blockout art, no flight/bike physics (P7).
- **#44 T-SAVE-01** checkpoint save/load + B-M01-09 soft-lock fix (Bot 3): docs conflicts resolved in **#46** `a1e56fa`: **1332** (+59 `test_save`); `UW_SAVE_SABOTAGE=1/2/3` → 25/9/2 FAIL confirmed. TD-035 ACCEPTED.
- **Gate defect fixed (T-QA-03):** the "flaky" `uwp build-props` exit 5 was deterministic – Blender's Python on the box had no Pillow. `Tests/check_toolchain.sh` now fails the gate in seconds with the fix.
- **#11 T-ART-05** pistol v1 (Bot 2): Bot 1 art review **REJECT** (`Docs/Reviews/2026-11-28_WPN_Pistol_01_v1_Bot1.md`: Silhouette/Proportions/Lighting/Detail 4, Geometry/Materials/Textures/Tech/Animation 3, Engine 2), merged as **WIP** (registry WIP) via a Bot 1 conflict PR. Owner decisions in TD-036 (optional barrel bone, 1024² export). Real glb in gameplay = T-WPN-02 (Bot 3).
- LFS: ~0.49 GB of the ~1 GB quota across all refs (B-005).

**2026-11-23 – Bot 1 review of PR #17 (Auftrag 02, merge `d3809d0`):** verified on a fresh worktree with `git lfs pull`: `RUN_ALL: PASS`, **738 checks** as claimed; after the review fixes **749** (+7 `test_boot`, +4 mission). All 12 sabotage modes fail as they must (player 3/9, vehicle 9/22, mission 5/2/2, AI 4, HUD 3, level 1, boot 2; build exit 6). LFS clean (0 raw binaries). Defects fixed forward in the review PR: (1) the export booted the PT crate scene and nothing outside tests started M01 → `Scenes/Game_M01.tscn` + `test_boot.gd` (TD-020), build smoke now requires the GameBoot banner; (2) Marco drawn standing through the car roof → hidden while seated + test; (3) `test_level` navmesh flake (1 of 3 runs red) → bounded wait for the async nav-map sync; (4) sabotage env switches now debug-build only. Linux export with the **official** 4.7.2 template: 71 MB + 95 MB PCK, boots into M01 with HUD under Xvfb/llvmpipe (`Docs/Reports/renders_review_pr17/08_export_build_boot_llvmpipe.png`) – still never played on a GPU. Art: blockout everywhere (helmet-like hair, empty box buildings, overexposed sidewalks in gl_compatibility). Report: `Docs/Reports/REVIEW_PR17_BOT1.md`. Next work order: `Docs/Prompts/CLAUDE_CODE_MASTER_PROMPT.md`.

**2026-11-22 – Auftrag 02 (Claude Code), six tasks:** report `Docs/Reports/BERICHT_AUFTRAG-02.md`.
`RUN_ALL: PASS`, **738 checks** (from 589), nine sabotage modes all fail with exit 1, thirteen real
bugs fixed (two of them made the whole street invisible / the buildings absent). Level is a **blockout**;
the Linux build boots headless but was never played, and no Phase-8 capture exists (no X, no GPU).
PR #17 was not self-merged by Claude Code; it was merged on 2026-11-23 14:07 (Berlin) from the owner account.

**2026-11-23 – review of Claude Code's first PR:** PR #14 (T-MIS-01, merge `c63198a`, self-merged by the agent) verified on a fresh worktree: `RUN_ALL: PASS`, **588 checks** (smoke 12, uwp tool 58, import 71, AI 80, mission 74, player 137, vehicle 88, weapon 68). Defects fixed forward: 106 binaries committed without LFS → PR #15 (`6f149e5`); tautological mission sabotage → PR #16. M01 core runs headless; Marco ally, wave sequencing, a real drive and a Phase 8 capture are still open. Next prompt for Claude Code: `Docs/Prompts/CLAUDE_CODE_PROMPT_02.md`.

**Handoff 2026-11-22:** the three-bot studio stopped; Claude Code takes over. Start at `CLAUDE.md` and `Docs/CLAUDE_CODE_HANDOFF.md`. PRs #1–#10 and #12 are merged; draft PR #11 (pistol quality pass, T-ART-05) is open WIP.

## Milestone 1 – LA Vertical Slice: **IN PROGRESS**

| Area | State |
|---|---|
| Tools | ✅ Blender 5.2.4 LTS + Godot 4.7.2 + git-lfs in `/workspace/tools/` |
| Repo | ✅ private GitHub repo, LFS, ownership rules, merge gate `Tests/run_all.sh` (TD-010) |
| Pipeline | ✅ `Tools/uwp` Blender → glb → Godot; character / weapon / vehicle / LA kit generators |
| Quality gate | ✅ Binding rule in `Docs/QUALITY_GATE.md`. **No asset is PRODUCTION-READY.** First reviews (2026-11-22) all **REJECT**. |
| Design | ✅ GDD v0.1, M01 design (review), concept art for Jason, ✅ street layout brief v1 (`Docs/LevelDesign/LA_CallowayAve_Layout.md`) |
| Art | 🔄 WIP blockouts / first passes: SK_Jason (rebuilt in #14, faces fixed), SK_NPC_Sam, **new** SK_NPC_Marco / Cartel_A / Cartel_B / Civilian_Female / Cop_LA (first builds, not gate-reviewed), WPN_Pistol_01, VH_Sedan_01, LA kit. Bot 1 look at the #14 renders: procedural blockout quality (helmet-like hair, painted brows/mouth, noisy jacket, shirt texture artifacts, Cartel_A = Jason's face) – far from the gate. |
| Gameplay | ✅ Controller with SK_Jason visual, pistol gunplay + bloom, vehicle physics, **M01 start→finish incl. Marco ally, sequenced waves and a real 97 m drive**, in-car targeting, clip wiring + aim layer + bone hitboxes, HUD (signal-driven, 40 checks), readable greybox level with baked navmesh. **738 headless checks, RUN_ALL: PASS.** Still blockout art. **Since 2026-11-28:** procedural audio library + AudioDirector (T-AUD-01, WIP sound), checkpoint save/load (T-SAVE-01), all P5 vehicles built (T-VEH-03). **1332 checks, RUN_ALL: PASS.** |
| Build | ✅ Linux export + boot check (`Docs/BUILD.md`, T-BUILD-01); **not played on a GPU box**, the local template has no renderer |

**What actually exists and is tested:** pipeline + Godot project; Jason v2 and recovered kit glbs; gameplay tests for player, weapons and AI (`Tests/run_all.sh`).
**What does not exist yet:** any production-ready art, menus, any mission besides M01, a GPU look/FPS check, a build played by a human.

## Next actions
- **Bot 2:** quality passes in gate order (pistol materials/model, Jason hair/jacket/boots, sedan, street, remaining NPCs). Reference boards first. Creator is never the sole reviewer.
- **Bot 3:** vehicle physics on the stand-in then the sedan, Jason capsule → mesh swap, Dead Drop layout, Phase 8 in-engine captures (`Tools/godot_phase8_capture.sh`).
- **Bot 1:** review every PR against `Docs/QUALITY_GATE.md`, merge when tests pass, keep scores honest.

See `TASK_BOARD.md`, `Docs/Reviews/` and `BLOCKERS.md`.
