# Technical Decisions

Owner: Bot 1. Other agents propose changes via `Docs/HANDOFF_PROTOCOL.md` (decision request); Bot 1 decides and records here.

## TD-001 – Engine: Godot 4 instead of Unreal Engine 5 (2026-11-22, Bot 1)
**Decision:** Godot 4.7.2 stable (standard build, GDScript) is the game engine. `GodotProject/` replaces `UnrealProject/` from the brief.
**Reasons (verified on the box):**
- Box: 8 CPU, 15 GB RAM, **no GPU**, ~14 GB free disk. UE5 needs ~100+ GB for engine + DDC, a GPU for the editor and long C++ build times; it cannot run here. Unity's editor needs a licence login and a GPU, and its Linux headless workflow is weaker.
- The owner explicitly allowed "an open engine or Unity".
- Godot is open source (MIT), ~140 MB, fully headless (`--headless`: import, scripts, physics, tests, exports), native glTF 2.0 importer, built-in `CharacterBody3D`, `VehicleBody3D`, `NavigationAgent3D`, `AnimationTree`, `SkeletonProfileHumanoid` retargeting.
**Consequences:** "Blueprints" -> GDScript + scenes; "C++" -> optional GDExtension in `Source/` for hot paths. Rendering quality is validated later on a GPU machine; on this box we only use the dummy renderer.

## TD-002 – Blender headless as the asset pipeline (2026-11-22)
Blender 5.2.4 LTS (`/workspace/tools/blender/blender`) run with `-b --factory-startup --python-exit-code 1`. All asset generation/validation/export is scripted in Python so it is reproducible. No Blender MCP connector exists in this environment – documented in BLOCKERS (B-001); bpy scripts are the supported alternative.

## TD-003 – Interchange format: glTF 2.0 binary (.glb)
- Blender `export_scene.gltf(export_format='GLB', export_yup=True, export_apply=True)`.
- FBX is optional (only if a specific tool needs it); glTF is the source of truth for Godot.
- Animations: one `.glb` per character containing the skinned mesh + all actions (NLA/actions exported as Godot animations) or separate `A_*.glb` animation libraries sharing the same skeleton – Bot 2 picks per asset and documents it in ASSET_REGISTRY.

## TD-004 – Units, axes, origins
- **1 Blender unit = 1 metre = 1 Godot unit.** Scene unit scale 1.0. Character height reference: Jason 1.82 m.
- **Up:** Blender +Z -> Godot +Y (handled by the exporter, never rotate objects by hand to compensate).
- **Front:** model faces **Blender -Y** -> becomes **Godot +Z** (`Vector3.MODEL_FRONT`). Verified by the smoke test's front marker.
- **Origins:** props/buildings at bottom centre; characters at the feet between the soles; vehicles at the ground contact centre; weapons at the grip.
- All transforms applied before export (scale 1, rotation 0) – the exporter validates this.

## TD-005 – Naming conventions
| Prefix | Meaning | Example |
|---|---|---|
| `SK_` | skinned/skeletal mesh | `SK_Jason` |
| `SM_` | static mesh | `SM_LA_Streetlight_A` |
| `A_` | animation (action / Godot Animation) | `A_Jason_Run`, `A_Humanoid_Aim_Pistol` |
| `M_` | material | `M_Car_Paint_Red` |
| `T_` | texture (`_D` albedo, `_N` normal, `_ORM` occlusion/roughness/metal) | `T_Brick_A_D.png` |
| `VH_` | vehicle asset root | `VH_Sedan_01` |
| `WPN_` | weapon asset root | `WPN_Pistol_01` |
| `PT_` | pipeline test placeholder (never ships) | `PT_PipelineTest_Crate` |
| `UCX_` + Godot hint | collision proxy | `UCX_SM_Box-colonly` |
- Names: `PascalCase` parts separated by `_`, ASCII only, no spaces. LODs: suffix `_LOD0/_LOD1/_LOD2`.
- Godot import hints in node names: `-colonly` (collision only), `-convcolonly` (convex collision only), `-col` (mesh + collision), `-noimp` (skip).
- Sockets/attachment points are Blender empties named `SOCKET_<Name>` (e.g. `SOCKET_Muzzle`, `SOCKET_Grip`, `SOCKET_RightHand`).
- Godot scripts/scenes: `snake_case.gd`, scenes `PascalCase.tscn`.
- **Addendum 2026-11-22 (director decision): no action/animation name may end in `_Loop` (case-insensitive; also `-Loop`, `_Cycle`, `-Cycle`).** Godot's scene importer treats these as loop hints, strips them from the name and forces looping (verified 4.7.2: `A_Jason_Jump_Loop` → `A_Jason_Jump`). Loop mode comes **only** from the uwp manifest (`animations[].loop`, applied by `uw_post_import.gd`). Enforced by `Tools/uwp` as error `NAME_ACTION_LOOP`. First rename: `A_Jason_Jump_Loop` → `A_Jason_Jump_Air`.

## TD-006 – Asset folder conventions
`Blender/Source/<Category>/<AssetName>/<AssetName>.blend` -> `Assets/<Category>/<AssetName>/<AssetName>.glb` (+ `.manifest.json`).
Categories: `Characters`, `Vehicles`, `Weapons`, `Environment/LA`, `Environment/NY`, `Props`, `Test`.
Textures live next to the .blend in `textures/` and are embedded in the .glb (or exported alongside – documented per asset).
`GodotProject/Assets` is a **symlink to `../Assets`** so Godot sees the exports at `res://Assets/...` without duplicating binaries (verified: Godot 4.7.2 imports through it). Godot writes `.import` sidecars next to the .glb – these ARE committed.

## TD-007 – File ownership
| Path | Owner | Others may |
|---|---|---|
| `Docs/*`, `README.md`, `Config/` | Bot 1 | append to `DEVELOPMENT_LOG.md`, `INTEGRATION_LOG.md`, `BLOCKERS.md`, `ASSET_REGISTRY.md` (own rows), update status of own tasks in `TASK_BOARD.md` |
| `Blender/`, `Tools/`, `Assets/` (incl. `.import`, manifests) | Bot 2 | read; Bot 3 may tune `.import` settings only after a handoff note |
| `GodotProject/` (except the `Assets` symlink), `Source/`, `Tests/` (except pipeline smoke), `Builds/`, `Tools/build/` | Bot 3 | read |
| `Tests/run_pipeline_smoke.sh`, `GodotProject/Tests/smoke_test.gd` | shared: Bot 3 maintains, Bot 2 must keep it passing | – |
| `Tools/blender_export.py` | bootstrap by Bot 1, **handed to Bot 2** | – |

## TD-008 – Git workflow on the shared box
- `main` = integrated, always passes `Tests/run_pipeline_smoke.sh`. `/workspace/UNDERWORLD` is the integration checkout (Bot 1), stays on `main`.
- Each bot works in its **own git worktree** so nobody switches branches under someone else:
  `/workspace/UNDERWORLD-bot2` (branch `bot2/dev`), `/workspace/UNDERWORLD-bot3` (branch `bot3/dev`).
- Merge to `main` by pull request (or Bot 1 fast-forward merge) only after the smoke test passes. Never force-push `main`.
- Git LFS 3.8.1 is installed; run `git lfs install` once per user.

## TD-009 – Performance budgets (initial, revise after first GPU test)
Jason ≤ 40k tris, NPC ≤ 25k, car ≤ 60k (LOD0), pistol ≤ 8k, street-kit modules ≤ 10k each; textures 2048² max (hero), 1024² default; 60 fps target on mid-range GPU.

## TD-010 – Gameplay conventions from T-GP-01 (proposed Bot 3, ACCEPTED by Bot 1, 2026-11-22)
**Status: ACCEPTED (Bot 1).** Points 1, 2 and 4 accepted as proposed; point 3 decided as option (c); point 5 → task T-GP-01b. Recorded by Bot 3 on Bot 1's instruction.
1. **Physics layers** (named in `project.godot`): 1 `World`, 2 `Player`, 3 `Characters` (NPC/enemy bodies), 4 `Vehicles`, 5 `Hitboxes`. Player collides with 1|3|4; camera spring arm with 1|4; aim ray with 1|3|4|5. Bot 2 collision proxies (`-col`/`-colonly`) land on layer 1 by default – no change needed.
2. **Input map source of truth:** `GodotProject/Scripts/tools/setup_input_map.gd` (rewrites only `[input]` + `[layer_names]` in `project.godot`). Actions: `move_*`, `look_*`, `sprint`, `walk`, `crouch`, `jump`, `aim`, `fire`, `reload`, `interact`, `enter_vehicle`, `shoulder_swap`, `pause`.
3. **Gamepad conflict in GDD §5:** "E/A interact" and "Space/A jump" both use gamepad A. Options: (a) A = jump, interact on D-pad Right; (b) context-sensitive A (interact when a prompt is shown, else jump); (c) interact = Y shared with enter vehicle (both are "use"). **Decision: (c)** – gamepad A = jump only; Y = `interact` **and** `enter_vehicle`; keyboard keeps E (interact) / F (vehicle). Implemented in `setup_input_map.gd`, asserted by `test_player_controller.gd`.
4. **Gameplay tests:** `GodotProject/Tests/test_*.gd` (SceneTree scripts, `[GPTEST]` output) run by `Tests/run_gameplay_tests.sh` with `--fixed-fps 60`; `Tests/run_all.sh` = pipeline smoke + gameplay = **the merge gate for `main`** (must print `RUN_ALL: PASS`).
5. **Vault-lite** (T-GP-01 description) split into T-GP-01b (P2, BACKLOG); stairs/step-up into T-GP-01c (P1).

## TD-011 – Player collision shape: cylinder instead of capsule (proposed Bot 3, ACCEPTED by Bot 1, 2026-11-22)
**Status: ACCEPTED (Bot 1, PR #1 review).** Recorded by Bot 3 on Bot 1's instruction.
- **Decision:** the player `CharacterBody3D` uses a `CylinderShape3D` (r 0.35 m, h 1.8 m standing / 1.2 m crouched, origin at the feet). The visual stand-in stays a capsule (`PT_Capsule`), later SK_Jason.
- **Why:** with a capsule the round bottom rests on stair nosings with a ~64° contact normal, which is not a floor contact: re-checked with the final step-up code, a capsule goes airborne 44 frames and "lands" 8 times on the 8-step test flight, 27 airborne frames + 1 landing walking down at sprint, and settles at 0.26 m on a 0.3 m step. The flat cylinder base stays grounded on every tread (0 airborne frames, verified in `test_player_controller.gd`, T-GP-01c).
- **Consequences:** step-up (`step_height` 0.35 m) + floor snap 0.4 m handle stairs and step-downs. Steps > 0.35 m need collision ramps. NPCs (T-AI-01/02) should use the same shape for consistency. If a different physics backend makes cylinders jittery, re-evaluate (tests will catch it).
- **Note:** Bot 2's T-PIPE-01 handoff proposes a "TD-011" for LOD/collision budgets; that proposal needs a new number (suggest TD-012) – Bot 1 to assign.

## TD-013 – NPC AI architecture (proposed Bot 3, ACCEPTED by Bot 1, 2026-11-22, T-AI-01)
- **Decision:** one `NPCController` script for every NPC; the archetype is an `AIProfile` .tres (`Data/AI/`) holding the state-machine transition table (`{state: {event: next}}`, `"*"` = any) + timeouts, speeds, perception, accuracy, cover and flee values. Code implements the fixed state set `NPCController.STATES`; `AIStateMachine.validate()` checks every table in the tests.
- **Perception/noise:** LOS raycasts against World|Vehicles only (character bodies don't block sight); noises are broadcast with `AIPerception.emit_noise` to the group `ai_hearing` (no autoload). Weapons emit a gunshot per shot with `WeaponData.noise_radius`.
- **Navigation:** navmeshes are baked headless from StaticBody colliders in group `navigation_geometry` with cell 0.25 m and agent radius 0.5 / height 2.0 / max climb 0.25 (multiples of the cell size, no precision loss); NPCs need `path_desired_distance` ≥ 0.75 because the baked surface sits ~0.5 m above the floor top.
- **Hitboxes:** `HumanoidHitboxes` (Head/Body/Legs/Arm_L/Arm_R on layer 5) for every humanoid incl. the player; on real skeletons they move to BoneAttachment3D (REQ-AI01-NPC).
- **Number:** TD-012 is left for Bot 2's LOD/collision proposal (see TD-011 note); Bot 1 to renumber if needed.


## TD-014 – Vehicle physics: Godot VehicleBody3D, assembled at runtime from the VH_*.glb (proposed Bot 3, 2026-11-22, T-GP-03)
**Status: PROPOSED** (Bot 1 to accept). Next free number after TD-013 (TD-012 stays reserved for Bot 2's LOD/collision proposal).
- **Decision:** cars are Godot's built-in raycast vehicle `VehicleBody3D` + `VehicleWheel3D` (not a custom raycast controller). One script `Scripts/vehicle/vehicle.gd` (`class_name Vehicle`), one `VehicleData` .tres per car (`Data/Vehicles/`, all tuning `[DEFAULT]`), scene = body + script + data (`Scenes/Vehicles/VH_Sedan_01.tscn`).
- **Why:** Bot 2's vehicle pipeline (T-ART-04) already exports a VehicleBody3D-shaped hierarchy (wheel-centre origins, UCX hull clearing the wheel rays, wheel radius/wheelbase/track as glTF extras); the built-in vehicle is deterministic headless at a fixed 60 Hz step (2 identical runs) and gives suspension, slip and rolling friction for free. A custom raycast car stays an option if feel testing on a GPU machine (B-003) shows the built-in one can't be tuned.
- **Runtime assembly (no baked scene):** at `_ready` the .glb is instanced and wired by node name, so a re-export by Bot 2 needs no scene edit: `UCX_*` convex shape → the body's `CollisionShape3D` (imported StaticBody3D removed); one `VehicleWheel3D` per `Wheel_FL/FR/RL/RR` at the asset wheel centre (front = steering, `drive` RWD/FWD/AWD = traction); `Door_*` swing around their node origin (vertical hinge, outward sign from the door's side); `SOCKET_*` looked up by name. Mismatches (missing node, data wheel radius ≠ asset radius) go to `Vehicle.assembly_errors` + a warning, and the tests fail on them.
- **Two Godot 4.7.2 quirks, measured and covered by tests:** (1) static suspension compression is `4.0 / suspension_stiffness` m, not the textbook `g / (4 k)` → wheel attach points are raised by that (`Vehicle.STATIC_SAG_K`) so a parked car stands at its design height (test: body origin on the ground ± 1 cm). (2) `VehicleWheel3D`'s own node position is drawn ~1.5/k m too low, so the asset wheel meshes are NOT parented to it: each physics frame they get the wheel's spin/steer basis and a centre one radius above the ground contact (test: parked wheels within 1 cm of the asset positions).
- **Physics layers:** car on layer 4 `Vehicles`, mask World | Player | Characters | Vehicles.
- **Enter/exit:** `enter_vehicle` (F / gamepad Y, TD-010) within `enter_distance` of an exit socket; driver door opens, player is hidden, input/movement off, **collision layer/mask 0** (hitboxes off) and kept on `SOCKET_Seat_Driver`; chase camera becomes current. Exit only ≤ `exit_max_speed`, at `SOCKET_Exit_Left` if a standing player cylinder fits there, else `SOCKET_Exit_Right`, else `exit_blocked`. The player's collision comes back **two physics frames after** it is placed at the exit socket: GodotPhysics applies a kinematic body's new transform at the next step and sweeps it from the old one (the seat, inside the car), which launched the car at ~100 m/s when restored in the same frame.
- **Driving input:** new actions `vehicle_accelerate` (W / RT), `vehicle_brake` (S / LT, reverses below 1 m/s), `vehicle_handbrake` (Space / RB), steering = `move_left/right`; only read while a player drives (RT/LT stay fire/aim on foot). Tests/AI use `Vehicle.set_controls()`.
- **Consequences:** the sedan needs no PT_ stand-in; enter/exit timing (`enter_time` 0.6 s, `exit_time` 0.5 s) is a placeholder until `A_Humanoid_Car_Enter_L/Exit_L` drive it (Jason swap task). NPCs don't see the player as "in a car" yet (AI targets the hidden player at the seat) – T-AI-02 / T-MIS-01.
