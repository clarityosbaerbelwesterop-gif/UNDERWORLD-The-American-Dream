# Development Log

Append-only, newest on top. `YYYY-MM-DD HH:MM (Europe/Berlin) · Bot N · Task ID · what was done · how it was verified`.

## 2026-11-22 · Bot 3
- **2026-11-22 09:50 · T-GP-01c** Step-up for the player (step height 0.35 m, grounded stair descent via floor snap 0.4 m, no wall/ledge climbing); collision capsule → cylinder for stable stair contact; stairs, 0.5 m ledge and 0.3 m step added to `PT_PlayerTestRange`. Verified: `./Tests/run_all.sh` → RUN_ALL: PASS (gameplay 112 checks); negative check `step_height = 0` → exit 1.
- **2026-11-22 09:50 · T-GP-01** Applied Bot 1 decisions: gamepad A = jump only, Y = interact + enter_vehicle (input map regenerated, asserted in tests); TD-010 recorded as ACCEPTED; REQ-GP01-JASON marked confirmed; facing +Z conflict marked resolved; T-GP-01b/01c added to TASK_BOARD.
- **2026-11-22 09:44 · T-GP-01** Third-person controller on `bot3/dev`: CharacterBody3D capsule player (walk/run/sprint, analog walk, crouch with stand-up check, jump with coyote/buffer, heavier fall gravity, slope snap), SpringArm3D orbit camera (mouse + right stick, pitch clamp, collision), over-shoulder aim mode (arm/FOV/offset blend, shoulder swap, face aim direction, crosshair raycast), `CharacterVisual` that swaps the PT capsule for a model and builds an AnimationTree from `A_Jason_*` clips, 19 input actions, PT test map. Verified: `./Tests/run_all.sh` → pipeline smoke PASS + gameplay tests PASS (94 checks); clean `.godot/` cache run also PASS; negative check (jump velocity halved) → exit 1. Asset request for Jason: `Docs/Handoffs/REQ_SK_Jason_Controller.md`.

## 2026-11-22 · Bot 1
- **T-BOOT-01** Installed Blender 5.2.4 LTS (sha256 verified) and Godot 4.7.2-stable (sha512 verified) to `/workspace/tools/`, archives deleted. Verified: `blender -b` runs bpy (`BPY_OK 5.2.4 LTS`), `godot --headless --version` → `4.7.2.stable.official.ed1daf0bf`. Installed git-lfs 3.8.1.
- **T-BOOT-02** Created private repo `clarityosbaerbelwesterop-gif/UNDERWORLD-The-American-Dream`, structure, `.gitignore`, `.gitattributes` (LFS for blend/glb/images/audio/fonts).
- **T-BOOT-03** Wrote all project docs, task board (24 tasks), GDD v0.1, M01 mission design, handoff protocol.
- **T-PIPE-00** `Tools/blender_export.py` + `GodotProject/` + `GodotProject/Tests/smoke_test.gd` + `Tests/run_pipeline_smoke.sh`. Clean run (deleted `.godot/` cache first) → `PIPELINE SMOKE TEST: PASS`. Negative test (expected mesh count changed to 3) → exit 1, as intended.
