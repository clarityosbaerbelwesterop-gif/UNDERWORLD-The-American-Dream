# Task Board – Milestone 1 "LA Vertical Slice"

Owner: Bot 1. Each agent updates **Status** of its own tasks (and adds a line to `DEVELOPMENT_LOG.md`). New tasks / re-assignments only via Bot 1.
Statuses: `BACKLOG` · `IN PROGRESS` · `READY FOR REVIEW` · `BLOCKED` · `COMPLETED`.
Highest priority first inside each section. Priority: P0 = blocks others, P1 = slice-critical, P2 = polish.

## Summary

| ID | Pri | Agent | Title | Depends on | Status |
|---|---|---|---|---|---|
| T-BOOT-01 | P0 | Bot 1 | Install Blender + Godot headless | – | COMPLETED |
| T-BOOT-02 | P0 | Bot 1 | Repo, structure, LFS | – | COMPLETED |
| T-BOOT-03 | P0 | Bot 1 | Project docs + task board | T-BOOT-02 | COMPLETED |
| T-PIPE-00 | P0 | Bot 1 | Pipeline smoke test baseline | T-BOOT-01/02 | COMPLETED |
| T-DES-01 | P1 | Bot 1 | Mission M01 design doc | T-BOOT-03 | READY FOR REVIEW |
| T-DES-02 | P1 | Bot 1 | Art direction + LA street layout brief | T-BOOT-03 | IN PROGRESS |
| T-PIPE-01 | P0 | Bot 2 | Production Blender export/validation tool | T-PIPE-00 | READY FOR REVIEW |
| T-PIPE-02 | P0 | Bot 3 | Godot import presets + per-asset import tests | T-PIPE-01 | BACKLOG |
| T-ART-01 | P1 | Bot 2 | Jason model + rig + skin | T-PIPE-01 | BACKLOG |
| T-ART-02 | P1 | Bot 2 | Jason animation set | T-ART-01 | BACKLOG |
| T-ART-03 | P1 | Bot 2 | LA street environment kit | T-PIPE-01, T-DES-02 | BACKLOG |
| T-ART-04 | P1 | Bot 2 | Drivable car model | T-PIPE-01 | BACKLOG |
| T-ART-05 | P1 | Bot 2 | Pistol model | T-PIPE-01 | BACKLOG |
| T-ART-06 | P1 | Bot 2 | 3 NPC models on shared rig | T-ART-01 | BACKLOG |
| T-GP-01 | P0 | Bot 3 | Third-person controller + camera | T-PIPE-00 | BACKLOG |
| T-GP-02 | P1 | Bot 3 | Gunplay (pistol) | T-GP-01 | BACKLOG |
| T-GP-03 | P1 | Bot 3 | Vehicle physics + enter/exit | T-GP-01 | BACKLOG |
| T-AI-01 | P1 | Bot 3 | Enemy AI (cartel gunmen) | T-GP-02 | BACKLOG |
| T-AI-02 | P2 | Bot 3 | Civilian NPC behaviour | T-GP-01 | BACKLOG |
| T-LVL-01 | P1 | Bot 3 | Assemble LA street level | T-ART-03 | BACKLOG |
| T-MIS-01 | P1 | Bot 3 | Mission system + M01 implementation | T-DES-01, T-GP-02, T-GP-03, T-AI-01 | BACKLOG |
| T-UI-01 | P2 | Bot 3 | HUD (health, ammo, objective text) | T-GP-02 | BACKLOG |
| T-BUILD-01 | P1 | Bot 3 | Playable Linux build + export script | T-PIPE-02 | BACKLOG |
| T-QA-01 | P1 | Bot 3 | Headless gameplay regression tests | T-GP-01 | BACKLOG |

Placeholder rule: Bot 3 may start gameplay with Godot primitives (capsule, box car) so code is not blocked by art, but those are marked `PT_` and replaced before the milestone closes. Final slice must use Bot 2's original Blender assets.

---

## Detailed tasks

### T-BOOT-01 – Install Blender + Godot headless
- **Agent:** Bot 1 · **Deps:** – · **Status:** COMPLETED (2026-11-22)
- **Description:** Install portable Blender LTS and Godot 4 stable under `/workspace/tools/`, verify headless.
- **Expected output:** `/workspace/tools/blender/blender`, `/workspace/tools/godot`, `/workspace/tools/README.md`.
- **File ownership:** Bot 1 (`/workspace/tools/`).
- **Acceptance:** both print versions headless (Blender 5.2.4 LTS, Godot 4.7.2.stable) ✅

### T-BOOT-02 – Repository, structure, LFS
- **Agent:** Bot 1 · **Status:** COMPLETED
- **Expected output:** private repo `UNDERWORLD-The-American-Dream`, folders per README, `.gitignore`, `.gitattributes` (LFS).
- **Acceptance:** pushed to `main`; `git lfs ls-files` lists the .blend/.glb ✅

### T-BOOT-03 – Docs + task board
- **Agent:** Bot 1 · **Status:** COMPLETED
- **Expected output:** all docs in `Docs/` (this file, status, registry, logs, decisions, blockers, GDD, handoff protocol).
- **Acceptance:** every M1 task has ID/agent/description/deps/output/ownership/acceptance/status ✅

### T-PIPE-00 – Pipeline smoke test baseline
- **Agent:** Bot 1 · **Status:** COMPLETED
- **Description:** headless bpy script builds `PT_PipelineTest_Crate` (placeholder), applies transforms, validates, exports .glb; minimal Godot project imports it; test asserts scale/orientation/collision.
- **Expected output:** `Tools/blender_export.py`, `GodotProject/` (Main.tscn), `GodotProject/Tests/smoke_test.gd`, `Tests/run_pipeline_smoke.sh`.
- **Acceptance:** `./Tests/run_pipeline_smoke.sh` exits 0 and prints `PIPELINE SMOKE TEST: PASS`; a deliberately broken assertion makes it exit 1 ✅ (both verified)

### T-DES-01 – Mission M01 "Dead Drop" design doc
- **Agent:** Bot 1 · **Deps:** T-BOOT-03 · **Status:** READY FOR REVIEW (owner/Bot 3 review)
- **Expected output:** `Docs/Missions/M01_DeadDrop.md` – beats, objectives, triggers, fail states, required assets + nodes.
- **File ownership:** Bot 1.
- **Acceptance:** Bot 3 confirms it is implementable without further questions; every asset it needs exists as a task.

### T-DES-02 – Art direction + LA street layout brief
- **Agent:** Bot 1 · **Status:** IN PROGRESS
- **Expected output:** `Docs/GAME_DESIGN.md` §Art direction (done, v1) + `Docs/LevelDesign/LA_CallowayAve_Layout.md` (top-down block-out with dimensions).
- **Acceptance:** Bot 2 can model the kit with exact dimensions; Bot 3 can block out the level.

### T-PIPE-01 – Production Blender export & validation tool
- **Agent:** Bot 2 · **Deps:** T-PIPE-00 · **Status:** READY FOR REVIEW (2026-11-22, handoff `Docs/Handoffs/2026-11-22_T-PIPE-01.md`)
- **Description:** Turn `Tools/blender_export.py` into a reusable package `Tools/underworld_pipeline/` (CLI: `export <blend>`/`export-all`). Steps: validate (naming TD-005, applied transforms, UVs, materials, tri budget TD-009, non-manifold check), generate LODs (Decimate → `_LOD1/_LOD2`), collision (`UCX_`/Godot hints), export .glb (+ optional FBX), write `.manifest.json`, Cycles-CPU preview render PNG (`Assets/<...>/<Name>_preview.png`).
- **Expected output:** `Tools/underworld_pipeline/*.py`, docs in `Tools/README.md`, smoke test still passing.
- **File ownership:** Bot 2 (`Tools/`, `Blender/Scripts/`).
- **Acceptance:** runs headless on all assets in `Blender/Source/`, fails non-zero on any validation error; preview PNG produced; `Tests/run_pipeline_smoke.sh` PASS.

### T-PIPE-02 – Godot import presets + per-asset import tests
- **Agent:** Bot 3 · **Deps:** T-PIPE-01 · **Status:** BACKLOG
- **Description:** import settings per category (characters: `SkeletonProfileHumanoid` retarget, animation loop flags; vehicles: keep wheel nodes; env: generate LODs/shadow meshes), test that loads every .glb listed in `ASSET_REGISTRY.md` and checks manifest dims vs. Godot AABB.
- **Expected output:** `GodotProject/Tests/test_assets.gd`, wired into `Tests/run_all.sh`.
- **File ownership:** Bot 3 (`.import` changes need a handoff note to Bot 2).
- **Acceptance:** test PASS for all registered assets, zero import errors.

### T-ART-01 – Jason: model, rig, skin
- **Agent:** Bot 2 · **Deps:** T-PIPE-01 · **Status:** BACKLOG
- **Description:** original male protagonist, 1.82 m, late 30s, see GAME_DESIGN §Characters. Modelled procedurally/with bpy (no purchased or ripped meshes). Armature with **Godot `SkeletonProfileHumanoid` bone names** (Hips, Spine, Chest, UpperChest, Neck, Head, Left/RightShoulder, Left/RightUpperArm, Left/RightLowerArm, Left/RightHand, fingers optional, Left/RightUpperLeg, Left/RightLowerLeg, Left/RightFoot, Left/RightToes) + `SOCKET_RightHand_Weapon`.
- **Expected output:** `Blender/Source/Characters/SK_Jason/SK_Jason.blend`, `Assets/Characters/SK_Jason/SK_Jason.glb`, manifest, preview PNG, ASSET_REGISTRY row.
- **Acceptance:** ≤ 40k tris; T-pose or A-pose rest; clean weights (no >4 influences); PBR materials; Godot import gives `Skeleton3D` + skinned `MeshInstance3D`, height 1.82 ± 0.02 m, faces +Z.

### T-ART-02 – Jason animation set
- **Agent:** Bot 2 · **Deps:** T-ART-01 · **Status:** BACKLOG
- **Description:** keyframed in Blender via bpy: `A_Jason_Idle`, `A_Jason_Walk` (1.4 m/s), `A_Jason_Run` (3.5 m/s), `A_Jason_Sprint` (6 m/s), `A_Jason_Aim_Pistol` (upper-body pose), `A_Jason_Shoot_Pistol` (recoil, 0.25 s), `A_Jason_Reload_Pistol`. 30 fps, in place (no root motion), loop cycles seamless; speeds documented for Bot 3 blend-spaces.
- **Expected output:** actions inside `SK_Jason.glb` (or `Assets/Characters/SK_Jason/A_Jason_Locomotion.glb` on same skeleton).
- **Acceptance:** Godot `AnimationPlayer` lists all names; loops flagged; foot sliding < 5 cm per cycle at stated speed.

### T-ART-03 – LA street environment kit "Calloway Avenue"
- **Agent:** Bot 2 · **Deps:** T-PIPE-01, T-DES-02 · **Status:** BACKLOG
- **Description:** modular original kit on a 2 m grid: road segment 10×14 m (2 lanes + parking), sidewalk 10×4 m with curb, crosswalk, 3 building facades (2-storey stucco shop, 4-storey brick apartment, mid-century motel/garage with roll-up door for M01), streetlight, traffic light, palm tree, hydrant, trash can, bus stop, fence, garage interior shell. Each with `-col`/`-colonly` collision and LOD1.
- **Expected output:** `Blender/Source/Environment/LA/<Piece>/...`, `Assets/Environment/LA/<Piece>/<Piece>.glb`.
- **Acceptance:** pieces snap on grid; budgets TD-009; collision present; registry rows.

### T-ART-04 – Drivable car "VH_Sedan_01"
- **Agent:** Bot 2 · **Deps:** T-PIPE-01 · **Status:** BACKLOG
- **Description:** original late-90s American full-size sedan (no real brand), ~5.2×1.9×1.45 m. Separate nodes: `Body`, `Wheel_FL`, `Wheel_FR`, `Wheel_RL`, `Wheel_RR` (origins at wheel centres, radius documented), `Door_FL` (pivot at hinge), `SOCKET_Seat_Driver`, `SOCKET_Exit_Left`, convex collision `UCX_Body-convcolonly`.
- **Acceptance:** Godot import keeps wheel nodes; manifest lists wheel radius, wheelbase, track width; ≤ 60k tris.

### T-ART-05 – Pistol "WPN_Pistol_01"
- **Agent:** Bot 2 · **Deps:** T-PIPE-01 · **Status:** BACKLOG
- **Description:** original semi-auto pistol, origin at grip. Separate `Slide` and `Magazine` nodes; sockets `SOCKET_Muzzle`, `SOCKET_Eject`, `SOCKET_Grip`.
- **Acceptance:** ≤ 8k tris; sockets present after Godot import; scale fits Jason's hand (registry note).

### T-ART-06 – 3 NPC models (shared rig)
- **Agent:** Bot 2 · **Deps:** T-ART-01 · **Status:** BACKLOG
- **Description:** `SK_NPC_Civilian_A` (female jogger), `SK_NPC_Civilian_B` (older male shop owner), `SK_NPC_Cartel_Gunman` (enemy, 2 colour variants). Same bone names as Jason so his animations play on them.
- **Acceptance:** ≤ 25k tris each; Jason's `A_Jason_Walk` plays on all three in Godot without retarget errors.

### T-GP-01 – Third-person controller + camera
- **Agent:** Bot 3 · **Deps:** T-PIPE-00 · **Status:** BACKLOG
- **Description:** `CharacterBody3D` player: walk/run/sprint, crouch, jump/vault-lite, acceleration curves, slope handling; `SpringArm3D` orbit camera with collision, over-shoulder aim mode (RMB), shoulder swap; input map for KB/M + gamepad; `AnimationTree` locomotion blend (placeholder capsule until T-ART-02).
- **Expected output:** `GodotProject/Scenes/Player/Player.tscn`, `GodotProject/Scripts/player/*.gd`.
- **Acceptance:** headless test moves the player 10 m forward with simulated input and asserts position; no penetration through Main.tscn ground/crate.

### T-GP-02 – Gunplay (pistol)
- **Agent:** Bot 3 · **Deps:** T-GP-01 · **Status:** BACKLOG
- **Description:** weapon resource (`WeaponData.tres`: damage, RPM, mag 12, reload 1.6 s, spread, recoil pattern), hitscan from camera with muzzle correction, recoil + camera kick, hit markers, damage/health component, ragdoll-lite hit reaction, muzzle flash + impact decals (placeholder FX OK).
- **Acceptance:** headless test: 12 shots then reload; damage applied to a dummy target; no fire during reload.

### T-GP-03 – Vehicle physics + enter/exit
- **Agent:** Bot 3 · **Deps:** T-GP-01 · **Status:** BACKLOG
- **Description:** `VehicleBody3D` with tuned suspension/grip for a heavy sedan, handbrake, chase camera, enter/exit at `SOCKET_Exit_Left`, engine audio pitch by RPM (placeholder sound OK).
- **Acceptance:** headless test: throttle 3 s → speed > 8 m/s; brake to < 0.5 m/s; enter/exit toggles player control.

### T-AI-01 – Enemy AI (cartel gunmen)
- **Agent:** Bot 3 · **Deps:** T-GP-02 · **Status:** BACKLOG
- **Description:** state machine Idle → Alert → Engage → Take cover (pre-placed `CoverPoint` nodes) → Flank-lite → Dead; `NavigationAgent3D`; line-of-sight perception + hearing gunshots; accuracy falloff by distance/movement.
- **Acceptance:** headless test: 3 gunmen detect player within 2 s of LOS, deal damage, die after enough hits.

### T-AI-02 – Civilian NPC behaviour
- **Agent:** Bot 3 · **Status:** BACKLOG
- **Description:** sidewalk wander along path nodes, idle at points, flee/cower on gunfire.
- **Acceptance:** ≥ 3 civilians on Calloway Ave; flee when a shot is fired within 25 m.

### T-LVL-01 – Assemble LA street level
- **Agent:** Bot 3 (with Bot 2 kit) · **Deps:** T-ART-03 · **Status:** BACKLOG
- **Description:** `GodotProject/Scenes/Levels/LA_CallowayAve.tscn` per layout brief; NavMesh baked; lighting (golden-hour sun, sky), occluders.
- **Acceptance:** player can walk whole street; navmesh covers sidewalks/road; no missing references.

### T-MIS-01 – Mission system + M01 implementation
- **Agent:** Bot 3 · **Deps:** T-DES-01, T-GP-02, T-GP-03, T-AI-01 · **Status:** BACKLOG
- **Description:** data-driven mission framework (objectives, triggers/areas, markers, fail/retry, checkpoints) and M01 per `Docs/Missions/M01_DeadDrop.md`.
- **Acceptance:** M01 playable start→finish; fail states (Jason dies, package destroyed, car destroyed) restart from checkpoint; headless test steps through objectives via debug API.

### T-UI-01 – HUD
- **Agent:** Bot 3 · **Status:** BACKLOG · health, ammo, crosshair, objective text, mission-passed screen.

### T-BUILD-01 – Playable Linux build
- **Agent:** Bot 3 · **Deps:** T-PIPE-02 · **Status:** BACKLOG
- **Description:** install ONLY Linux export templates (disk!), `GodotProject/export_presets.cfg`, `Tools/build/build_linux.sh` (Bot 3 owns `Tools/build/`) → `Builds/linux/Underworld.x86_64`.
- **Acceptance:** build exits 0; binary runs `--headless --quit-after 300` without errors; size documented.

### T-QA-01 – Headless regression suite
- **Agent:** Bot 3 · **Status:** BACKLOG · `Tests/run_all.sh` runs pipeline smoke + all gameplay tests; required to pass before merging to `main`.
