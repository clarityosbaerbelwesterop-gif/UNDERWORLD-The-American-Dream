# Project Status

_Last update: 2026-11-22 13:30 (Europe/Berlin) by Bot 1 (handoff)_

**Handoff 2026-11-22:** the three-bot studio stopped; Claude Code takes over. Start at `CLAUDE.md` and `Docs/CLAUDE_CODE_HANDOFF.md`. PRs #1–#10 and #12 are merged; draft PR #11 (pistol quality pass, T-ART-05) is open WIP.

## Milestone 1 – LA Vertical Slice: **IN PROGRESS**

| Area | State |
|---|---|
| Tools | ✅ Blender 5.2.4 LTS + Godot 4.7.2 + git-lfs in `/workspace/tools/` |
| Repo | ✅ private GitHub repo, LFS, ownership rules, merge gate `Tests/run_all.sh` (TD-010) |
| Pipeline | ✅ `Tools/uwp` Blender → glb → Godot; character / weapon / vehicle / LA kit generators |
| Quality gate | ✅ Binding rule in `Docs/QUALITY_GATE.md`. **No asset is PRODUCTION-READY.** First reviews (2026-11-22) all **REJECT**. |
| Design | ✅ GDD v0.1, M01 design (review), concept art for Jason, 🔄 street layout brief |
| Art | 🔄 WIP blockouts / first passes: SK_Jason v2, SK_NPC_Sam, WPN_Pistol_01, VH_Sedan_01, LA kit. Quality passes are next (T-ART-01b and related). |
| Gameplay | 🔄 Controller with SK_Jason v2 visual (PR #12), pistol gunplay + bloom, T-AI-01, vehicle physics on VH_Sedan_01 (PR #9, TD-014) in `main`. Mission logic, HUD, level not started. |
| Build | ⏳ no export templates yet (T-BUILD-01) |

**What actually exists and is tested:** pipeline + Godot project; Jason v2 and recovered kit glbs; gameplay tests for player, weapons and AI (`Tests/run_all.sh`).
**What does not exist yet:** any production-ready art, dressed LA street, mission implementation, playable build.

## Next actions
- **Bot 2:** quality passes in gate order (pistol materials/model, Jason hair/jacket/boots, sedan, street, remaining NPCs). Reference boards first. Creator is never the sole reviewer.
- **Bot 3:** vehicle physics on the stand-in then the sedan, Jason capsule → mesh swap, Dead Drop layout, Phase 8 in-engine captures (`Tools/godot_phase8_capture.sh`).
- **Bot 1:** review every PR against `Docs/QUALITY_GATE.md`, merge when tests pass, keep scores honest.

See `TASK_BOARD.md`, `Docs/Reviews/` and `BLOCKERS.md`.
