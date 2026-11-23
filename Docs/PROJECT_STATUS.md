# Project Status

_Last update: 2026-11-22 (Europe/Berlin) by Claude Code (Auftrag 02, all six tasks)_

**2026-11-22 – Auftrag 02 (Claude Code), six tasks:** report `Docs/Reports/BERICHT_AUFTRAG-02.md`.
`RUN_ALL: PASS`, **738 checks** (from 589), nine sabotage modes all fail with exit 1, thirteen real
bugs fixed (two of them made the whole street invisible / the buildings absent). Level is a **blockout**;
the Linux build boots headless but was never played, and no Phase-8 capture exists (no X, no GPU).
PRs are open, not merged (`MERGE-FREIGABE: NEIN` in the work order).

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
| Gameplay | ✅ Controller with SK_Jason visual, pistol gunplay + bloom, vehicle physics, **M01 start→finish incl. Marco ally, sequenced waves and a real 97 m drive**, in-car targeting, clip wiring + aim layer + bone hitboxes, HUD (signal-driven, 40 checks), readable greybox level with baked navmesh. **738 headless checks, RUN_ALL: PASS.** Still blockout art, no audio, no capture. |
| Build | ✅ Linux export + boot check (`Docs/BUILD.md`, T-BUILD-01); **not played on a GPU box**, the local template has no renderer |

**What actually exists and is tested:** pipeline + Godot project; Jason v2 and recovered kit glbs; gameplay tests for player, weapons and AI (`Tests/run_all.sh`).
**What does not exist yet:** any production-ready art, a dressed LA street (the level is a greybox), a complete M01 (Marco/waves), a playable build.

## Next actions
- **Bot 2:** quality passes in gate order (pistol materials/model, Jason hair/jacket/boots, sedan, street, remaining NPCs). Reference boards first. Creator is never the sole reviewer.
- **Bot 3:** vehicle physics on the stand-in then the sedan, Jason capsule → mesh swap, Dead Drop layout, Phase 8 in-engine captures (`Tools/godot_phase8_capture.sh`).
- **Bot 1:** review every PR against `Docs/QUALITY_GATE.md`, merge when tests pass, keep scores honest.

See `TASK_BOARD.md`, `Docs/Reviews/` and `BLOCKERS.md`.
