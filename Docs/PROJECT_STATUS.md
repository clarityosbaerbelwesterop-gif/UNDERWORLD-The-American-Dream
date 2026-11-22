# Project Status

_Last update: 2026-11-22 09:40 (Europe/Berlin) by Bot 1_

## Milestone 1 – LA Vertical Slice: **IN PROGRESS (bootstrap complete)**

| Area | State |
|---|---|
| Tools | ✅ Blender 5.2.4 LTS + Godot 4.7.2 + git-lfs 3.8.1 installed headless in `/workspace/tools/` |
| Repo | ✅ private GitHub repo, LFS, folder structure, ownership rules |
| Pipeline | ✅ Blender → .glb → Godot smoke test passes (`Tests/run_pipeline_smoke.sh`) with a **placeholder** test asset |
| Design | ✅ GDD v0.1, M01 mission design (review), 🔄 street layout brief |
| Art (Bot 2) | ⏳ not started – next: T-PIPE-01, then T-ART-01 Jason |
| Gameplay (Bot 3) | ⏳ not started – next: T-GP-01 controller, T-PIPE-02 |
| Build | ⏳ no export templates yet (T-BUILD-01) |

**What actually exists and is tested:** tool installs; Godot project `GodotProject/` with `Scenes/Main.tscn` (ground, light, sky, camera, imported placeholder crate); headless smoke test (13 assertions PASS; negative test verified to fail).
**What does not exist yet:** any final art, player controller, gunplay, vehicle, AI, mission logic, build.

## Next actions
- **Bot 2:** T-PIPE-01 (production exporter) → T-ART-01 Jason → T-ART-05 pistol / T-ART-04 sedan.
- **Bot 3:** T-GP-01 controller (placeholder capsule) → T-PIPE-02 → T-GP-02 gunplay.
- **Bot 1:** T-DES-02 layout brief, review handoffs, merge to `main`.

See `TASK_BOARD.md` and `BLOCKERS.md`.
