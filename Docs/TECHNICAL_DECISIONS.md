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


## TD-014 – Vehicle physics: Godot VehicleBody3D, assembled at runtime from the VH_*.glb (proposed Bot 3, ACCEPTED by Bot 1, 2026-11-22, T-GP-03)
**Status: ACCEPTED (Bot 1, 2026-11-22, PR #9 review).** Next free number after TD-013 (TD-012 stays reserved for Bot 2's LOD/collision proposal).
- **Decision:** cars are Godot's built-in raycast vehicle `VehicleBody3D` + `VehicleWheel3D` (not a custom raycast controller). One script `Scripts/vehicle/vehicle.gd` (`class_name Vehicle`), one `VehicleData` .tres per car (`Data/Vehicles/`, all tuning `[DEFAULT]`), scene = body + script + data (`Scenes/Vehicles/VH_Sedan_01.tscn`).
- **Why:** Bot 2's vehicle pipeline (T-ART-04) already exports a VehicleBody3D-shaped hierarchy (wheel-centre origins, UCX hull clearing the wheel rays, wheel radius/wheelbase/track as glTF extras); the built-in vehicle is deterministic headless at a fixed 60 Hz step (2 identical runs) and gives suspension, slip and rolling friction for free. A custom raycast car stays an option if feel testing on a GPU machine (B-003) shows the built-in one can't be tuned.
- **Runtime assembly (no baked scene):** at `_ready` the .glb is instanced and wired by node name, so a re-export by Bot 2 needs no scene edit: `UCX_*` convex shape → the body's `CollisionShape3D` (imported StaticBody3D removed); one `VehicleWheel3D` per `Wheel_FL/FR/RL/RR` at the asset wheel centre (front = steering, `drive` RWD/FWD/AWD = traction); `Door_*` swing around their node origin (vertical hinge, outward sign from the door's side); `SOCKET_*` looked up by name. Mismatches (missing node, data wheel radius ≠ asset radius) go to `Vehicle.assembly_errors` + a warning, and the tests fail on them.
- **Two Godot 4.7.2 quirks, measured and covered by tests:** (1) static suspension compression is `4.0 / suspension_stiffness` m, not the textbook `g / (4 k)` → wheel attach points are raised by that (`Vehicle.STATIC_SAG_K`) so a parked car stands at its design height (test: body origin on the ground ± 1 cm). (2) `VehicleWheel3D`'s own node position is drawn ~1.5/k m too low, so the asset wheel meshes are NOT parented to it: each physics frame they get the wheel's spin/steer basis and a centre one radius above the ground contact (test: parked wheels within 1 cm of the asset positions).
- **Physics layers:** car on layer 4 `Vehicles`, mask World | Player | Characters | Vehicles.
- **Enter/exit:** `enter_vehicle` (F / gamepad Y, TD-010) within `enter_distance` of an exit socket; driver door opens, player is hidden, input/movement off, **collision layer/mask 0** (hitboxes off) and kept on `SOCKET_Seat_Driver`; chase camera becomes current. Exit only ≤ `exit_max_speed`, at `SOCKET_Exit_Left` if a standing player cylinder fits there, else `SOCKET_Exit_Right`, else `exit_blocked`. The player's collision comes back **two physics frames after** it is placed at the exit socket: GodotPhysics applies a kinematic body's new transform at the next step and sweeps it from the old one (the seat, inside the car), which launched the car at ~100 m/s when restored in the same frame.
- **Driving input:** new actions `vehicle_accelerate` (W / RT), `vehicle_brake` (S / LT, reverses below 1 m/s), `vehicle_handbrake` (Space / RB), steering = `move_left/right`; only read while a player drives (RT/LT stay fire/aim on foot). Tests/AI use `Vehicle.set_controls()`.
- **Consequences:** the sedan needs no PT_ stand-in; enter/exit timing (`enter_time` 0.6 s, `exit_time` 0.5 s) is a placeholder until `A_Humanoid_Car_Enter_L/Exit_L` drive it (Jason swap task). NPCs don't see the player as "in a car" yet (AI targets the hidden player at the seat) – **resolved by TD-015** (T-AI-03).

## TD-015 – Enemies vs. a player who is inside a car (proposed Bot 3, 2026-11-22, T-AI-03)
**Status: ACCEPTED (Bot 1, 2026-11-23, review of PR #17)** – the 25 % driver-window rule stays the M1 default; tune per weapon later.
- **The bug:** `NPCController` aimed at the player's capsule unconditionally. While Jason sat in the sedan the two visibility points were still head/chest height *inside* the bodywork, so gunmen shot through the roof at a body they could not see and the damage landed on the player's `DamageReceiver` instead of the car. Fixed by one module, `Scripts/ai/vehicle_targeting.gd` (`class_name VehicleTargeting`), that every AI rule goes through.
- **R1 – substitution:** a seated target is replaced by its `Vehicle` for perception, aim and cover (`VehicleTargeting.resolve()`), re-evaluated every physics frame, so entering/leaving changes the target class on the next frame. The player node itself is remembered (`NPCController._person`); a gunman who loses the car falls back to the human instead of staring at an empty seat.
- **R2 – car damage:** a hit on the car goes to `Vehicle.health` through `Vehicle.apply_hit_damage(amount, hit_position, source)`; `crashed`/`wrecked` fire exactly as in the existing crash path, so there is one health pool, not two.
- **R3 – the driver channel:** the driver only takes damage through the **driver-side window** (hit within 0.75 m of the seat point at window height) and takes `VehicleData.driver_window_fraction` (default **0.25**) of the hit; the car takes the full amount in every case. Once `Vehicle.health` is 0 the window channel closes (a wreck shields nobody). Every other hit on the car is car-only: **the driver cannot be shot through the bodywork.**
- **R4 – getting out:** leaving the seat restores the person target on the next physics frame; no script re-registration needed.
- **LOS to a car:** the AI's sight ray stops on the target's own bodywork, which made parked cars invisible to every gunman. `NPCController.has_los_to(from, to, target)` treats a ray that ends on the target (or its child) as "seen"; walls and other cars still block.
- **Test coverage:** `Tests/test_ai.gd` "T-AI-03" – real gunman + real sedan, Jason seated through the real `Vehicle.enter()` path: aim points on the car (not the capsule), car loses HP, hidden driver takes nothing, window hit transfers exactly the configured fraction, body hit transfers nothing, wrecked car transfers nothing, getting out re-targets the person. Negative control `UW_AI_SABOTAGE=incar` disables R1 (the pre-fix behaviour) and makes 3 of those checks FAIL.
- **Consequences:** the "NPCs don't see the player as in a car yet" line in TD-014 is now obsolete. `Weapon.trigger()` additionally reports `hit_body`/`hit_position`/`hit_normal` in its shot dictionary; `WeaponData.damage_at(distance)` is the public damage-at-range helper the AI uses for non-hitbox targets.

## TD-016 – Character animation wiring (clips, upper-body layer, bone hitboxes) – T-GP-04
**Status: IMPLEMENTED (recorded by Bot 3, 2026-11-22) · ACCEPTED by Bot 1 2026-11-23.**
- **One clip per event:** `Shoot` on every shot the weapon actually fires (`Weapon.fired`, so the weapon's own fire rate is the limiter), `Reload` on `Weapon.reload_started`, `Death` as the last pose, `Carry_Idle/Carry_Walk` blended in while `CarriedItem` is carried, `Car_Enter_L/Car_Exit_L` on the vehicle sequences. All of them are one-shots on a dedicated `oneshot` node chain (`AnimationNodeOneShot`), never a name-suffixed loop clip (TD-005).
- **The vehicle timing comes from the clip:** `Vehicle.enter_duration()` / `exit_duration()` return the driver's `A_Jason_Car_Enter_L` / `A_Jason_Car_Exit_L` length (both 1.5 s) and fall back to `VehicleData.enter_time`/`exit_time` only when the driver has no character model. `VehicleData` values stay as the documented fallbacks; the 0.6/0.5 s constants no longer drive gameplay. Tests must wait for these functions, not for a literal second.
- **Upper-body aim layer = `SkeletonModifier3D`, not an `AnimationTree` filter.** `AimSpineModifier` sits on the Skeleton3D (the only parent type Godot accepts for a modifier) and adds pitch/yaw to `Spine`/`Chest`/`UpperChest` *after* the tree has posed the skeleton; the legs (and the hips) are simply not in its chain, which is the blend mask from the spine up. Weight ramps with the aim state, pitch comes from the camera, softened to 75 %.
  - **Why not a tree filter:** filters are `NodePath` lists; on every re-export the path list would have to be maintained by hand and would silently target nothing. The modifier also carries the semantic ("bend the spine chain, share the rotation") that a filter cannot express.
  - **Godot quirk, measured:** after the modifiers have run, `Skeleton3D` *restores* the animated bone poses (it only keeps the modified pose for the skin). `get_bone_pose_rotation()` therefore shows the unmodified pose - the layer's effect is visible on the skin and on `BoneAttachment3D` children. The tests measure there.
- **Hitboxes are bone-bound:** `HumanoidHitboxes` builds 7 zones (head, chest, hips, 2 upper arms, 2 upper legs) as `BoneAttachment3D` + `Hitbox` on the standard humanoid skeleton, and falls back to the old rest offsets for models without one (`mode == "bone" | "rest"`). Head keeps the headshot multiplier (`WeaponData.zone_multiplier(HEAD)`), limbs ×0.75.
- **Negative control `UW_ANIM_SABOTAGE=1`:** no aim modifier, hitboxes pinned to the Hips bone, one-shot slots mapped to idle → 9 checks FAIL.

## TD-017 – HUD is a pure listener, bound deferred – T-UI-01
**Status: IMPLEMENTED (2026-11-22) · ACCEPTED by Bot 1 2026-11-23.**
- **No polling, no timers:** every HUD element is a signal sink (`health_changed`, `ammo_changed`, `reload_started/finished`, `objective_text_changed`, `subtitle`, `mission_completed`, `mission_failed`). The only per-frame work is projecting the GPS marker and sizing the crosshair from the weapon's bloom.
- **Binding must be deferred.** `HUD` is the first node of `LA_CallowayAve.tscn`, so during its `_ready()` the `MissionManager` has not joined the `mission_manager` group yet and every later connection would silently go to nothing (that is what the first test run showed: 0 connections, empty objective label). `_bind.call_deferred()` after `_build()` fixes the order; the tests wait one **idle** frame (`process_frame`) because a headless `SceneTree` does not flush the message queue on physics frames alone.
- **Camera path:** the chase camera hangs at `CameraRig/Pitch/SpringArm3D/Camera3D`; the HUD resolves it from there (and still honours an explicit `camera_path`).
- **Objective text** is mirrored into `objective_name` so the UI state can be asserted without parsing the label. The PASSED card (`MISSION PASSED` + `+$2500` from `MissionData.reward_cash`) never overwrites the objective text.
- **Marker:** projects the current objective's `marker_path`/`target_path`; hidden when the target is behind the camera (no edge clamping - M01 has no off-screen arrow).
- **Tests:** `Tests/test_hud.gd` against the real level (40 checks): health from real damage, ammo from a real shot + reload, every objective text, the intro subtitle lines, projected marker position (±2 px), PASSED card with $2.500, fail reason. **Negative control `UW_HUD_SABOTAGE=1`** freezes the ammo counter and the objective label → 3 checks FAIL.

## TD-018 – Greybox readability in the generator (T-LVL-01a)
**Status: IMPLEMENTED (2026-11-22) · ACCEPTED by Bot 1 2026-11-23.**
- **Everything happens in `Scripts/tools/build_level_calloway.gd`**, the scene is regenerated. Nothing is hand-edited in the `.tscn`.
- **Found bugs while doing it** (all were silently shipping):
  1. `_building()` returned the kit piece, not the block → the piece was re-parented and **every building was missing from the saved scene** (Godot: "Can't add child ... already has a parent"). The level has been a street without houses.
  2. The kit materials were never touched: `fallback_mat` was only used for the greybox, so road (near-black asphalt texture), sidewalk (light concrete texture) and background were the same grey in the capture — and the asphalt/concrete TEXTURES are `baseColorTexture` only, so the albedo said nothing. `_kit_piece()` now takes `paint = [[material-name-substring, material], ...]`.
  3. Per-surface overrides inside an instanced sub-scene are **not serialised** by `PackedScene` (only the instance root is). The painted surfaces are therefore copied out as level-owned `MeshInstance3D` nodes (`Road_Straight_01_SM_LA_Road_Straight`, …) and the kit instance is hidden — it keeps its exported UCX hull, which is what physics and the navmesh parse.
  4. Engine fallback names (`@Node3D@12`, `@StaticBody3D@3`): fixed at the source (speaking `piece_NN` names, `_name_children()` safety net, named Ground collision shape). The shipped scene contains **0** `@` names.
  5. The navmesh was never baked: the empty `NavigationRegion3D` shipped, `map_get_path()` returned nothing. The generator now bakes it (`NavigationServer3D.parse_source_geometry_data` + `bake_from_source_geometry_data`) **after one idle/physics frame** — the parser reads global transforms, so baking right after `add_child()` yields 0 polygons. Result: 428 polygons covering road **and** sidewalk; the old flat `NavFloor` box (which buried the 0.16 m sidewalk in the road) is gone.
  6. The civilian route crossed the roadway at z = 40, and a pedestrian is a solid 0.56 m obstacle: it stopped the player's sedan dead at z ≈ 37 with no feedback (the M01 drive test went from 26 s to a stall). The route stays on the outer west sidewalk now; civilians also spawn 1.4 m off the kerb line.
- **Materials:** asphalt `0.15` luminance, sidewalk `0.60`, kerb line `0.78` (bright edge strips along every sidewalk) — a 0.45 luminance step where the first capture had 0.00.
- **Tests:** `Tests/test_level.gd` (23 checks): no `@` names, no unused `ext_resource`, building/garage/navmesh really in the file, luminance differences, navmesh reachability probes on road + sidewalk + both closing segments, and a walk from one end of the block to the other with real movement input (44 waypoints). **`UW_LEVEL_SABOTAGE=1`** makes the contrast audit lie (0.02) → FAIL.
- **Honest limit:** this is still a blockout. The fix makes road/kerb/sidewalk distinguishable and the block walkable/drivable; it does not add art. In-engine Phase-8 captures are **not possible on this box** (no X server/Xvfb, no GPU); the report states that instead of faking a screenshot.

## TD-019 – Linux export (T-BUILD-01)
**Status: IMPLEMENTED (2026-11-22) · ACCEPTED by Bot 1 2026-11-23.**
- **Preset** `GodotProject/export_presets.cfg` (platform `Linux`, x86_64, PCK beside the binary, text→binary), **script** `Tools/build/build_linux.sh` → `Builds/linux/Underworld.x86_64`; `Builds/` stays gitignored, no binary is ever committed.
- **Excluded from the export:** `Tests/*` and `Scripts/import/*` (the import post-processors are editor-only). Verified by parsing the PCK directory instead of trusting the log: 657 files, 0 hits for either prefix.
- **Export templates are version-locked** to the engine build. The official `.tpz` (~1 GB) is unreachable from this sandbox, so the template was **compiled from the same `4.7.2-stable` source tree** and installed as `~/.local/share/godot/export_templates/4.7.2.stable/linux_release.x86_64` (47 min, 2 vCPU). `Docs/BUILD.md` has the exact scons line.
- **The template has no renderer** (`vulkan=no opengl3=no`, like the sandboxed editor). It boots `Main.tscn` from the PCK, runs the scene tree and exits cleanly — that is the acceptance criterion — but it cannot present a frame. **A desktop-playable build therefore still requires a Forward+/Vulkan template**, built or downloaded on a machine that has the Vulkan loader.
- **Negative control:** `UW_BUILD_SABOTAGE=1` plants an `ERROR:` line in the smoke log; the script must fail with exit 6 (checked).

### TD-018 addendum (2026-11-22, second pass) – a bug the luminance test could not see
The painted surface copies from the first pass were saved **at the origin**, so all 26 road pieces
and every kerb sat stacked in one place while `test_level.gd` stayed green (it only looked at the
material, never at the transform). Found by `Tests/tools/capture_level_plan.gd`, a headless plan
view drawn from the scene's real AABBs.
- Why: a `--script` `SceneTree` runs `_initialize()` **before** `SceneTree::initialize()` sets the
  tree, so `root.add_child(level)` does not make the level "inside tree"; every `global_transform`
  still reads identity, and setting one on a node outside the tree silently writes the identity.
- Fix: `_own_painted_meshes()` composes `inst.transform * (chain of `.transform` from the instance
  down to the mesh)`. **Never use `global_transform` in this generator** – the same trap applies to
  every other piece of geometry it places.
- Regression guard: `test_level.gd` now asserts 118 painted copies, **0 of them at the origin**, and
  the first road segment at (-24, 0, -79) – read before `free()`, because a freed Object compares
  equal to `null` and returns zero vectors (a second silent trap that made two draft assertions
  always pass/fail for the wrong reason).

## TD-020 – Shipping entry scene and debug-only sabotage switches (Bot 1, 2026-11-23, review of PR #17)
**Status: ACCEPTED.**
- `application/run/main_scene` = `res://Scenes/Game_M01.tscn` (`Scripts/game/game_boot.gd`, `class_name GameBoot`). It instances `LA_CallowayAve.tscn`, waits 3 physics frames and calls `MissionManager.start()`; it prints `UNDERWORLD: GameBoot -> M01 Dead Drop`, which `Tools/build/build_linux.sh` now requires in the smoke log (exit 8 otherwise). Before, the export booted the pipeline smoke scene (PT crate) and nothing outside the tests started the mission.
- `Scenes/Main.tscn` stays the pipeline smoke scene (loaded by path in `smoke_test.gd` and `test_player_controller.gd`).
- Every `UW_*_SABOTAGE` switch is only honoured when `OS.is_debug_build()` – a release export can never be sabotaged through the environment. Tests run the editor binary (debug), so all negative controls still bite.
- Test: `Tests/test_boot.gd` (7 checks) instances whatever `main_scene` points at; `UW_BOOT_SABOTAGE=1` skips `start()` → 2 FAIL.
- When a front-end/main menu exists (M7), it replaces `Game_M01.tscn` as `main_scene`; keep `test_boot.gd` pointing at the real entry.

## TD-023 – Input-only playthrough as a merge gate; deterministic replays (Claude Code, 2026-11-23, T-BUILD-02)
*(Numbered TD-021 in PR #21; renumbered in T-PIPE-06 because the master prompt §5.4 reserves TD-021 for the hybrid pipeline.)*
**Status: PROPOSED** (Bot 1 / owner to accept).
- Every earlier M01 test drove the mission through APIs (`try_interact`, `load_into`, `debug_complete_current`, teleports). They proved the logic, not that a person can play it. `GodotProject/Tests/test_playthrough.gd` boots the shipping entry scene and `Tests/tools/m01_autopilot.gd` plays M01 using **only input actions and camera turns** (it reads the world, it never calls a state-changing game API). Its runs found 20 blockers (bug list in `Docs/Reports/BERICHT_T-BUILD-02.md`).
- **Deterministic replay:** `UW_RNG_SEED=<n>` seeds every NPC/weapon RNG without an explicit seed from `seed + hash(node path)` (`Weapon.replay_seed()`, debug builds only). The test pins seed 2.
- **QA cheat, stated openly:** the gate runs with the player invulnerable – it is a FLOW gate. Every gunman is still killed through aim + fire inputs (≥ 20 hits asserted). Balance is measured separately (`UW_PLAYTHROUGH_MORTAL=1`, several seeds) and reported, never gated by this test.
- Negative controls: `UW_PLAYTHROUGH_SABOTAGE=1` (interact input ignored) → stalls at objective 5; `=2` (package not loaded on boarding) → objective 6; `=3` (released waves not briefed) → objective 4. `UW_MISSION_SABOTAGE=4` (enemies revived in place) → `test_mission` FAIL. `UW_AI_SABOTAGE=nostep` (no NPC step-up) → `test_level` FAIL.
- Movie Maker recording of the same replay in Forward Plus: `Tests/tools/record_m01_playthrough.gd` via `Tools/godot_phase8_capture.sh --renderer fwdplus --movie ...`.

## TD-022 – Difficulty layer: AI damage to the player (Claude Code, 2026-11-23, T-BUILD-02)
**Status: PROPOSED – value unchanged (1.0), owner decides.**
- `Scripts/game/difficulty.gd` (`Difficulty`) + `Data/Game/Difficulty_Normal.tres`: `ai_damage_to_player` multiplies damage an `NPCController` deals to the player (`DamageReceiver.scale_npc_damage`, set on `Player/Health`). Weapon data stays physical (a pistol does 25 to anyone). `UW_AI_DAMAGE_SCALE` overrides it in debug builds for balancing runs.
- Measured with the mortal autopilot over seeds 1–3 (15 min cap each, before the later bot-tactics fixes, so these are upper bounds of difficulty): scale 1.0 → 8–14 deaths and no completion; scale 0.5 → 5–6 deaths. The bot is weaker than a skilled human (no strafing, no headshot preference), so these numbers do **not** settle the value.
- Recommendation: decide after a human GPU playtest of M01 (T-BUILD-02 GPU part). Industry reference for a first combat mission is clearly below raw weapon damage; 0.5 is the candidate to test first.

## TD-021 – Hybrid asset pipeline: hand-authored sources, uwp as the mandatory gate (Claude Code, 2026-11-23, T-PIPE-06)
**Status: PROPOSED** (Bot 1 / owner to accept). Master prompt §5.2–§5.4, audit `Docs/Reports/AUDIT_T-PIPE-06_Pipeline.md`.
- **Hero assets are authored**, not generated: sculpt → retopo → bake → painted PBR, real hair cards, simulated or sculpted cloth, mocap-based animation. Sources live as `.blend` under `Art/Source/<Asset>/` (LFS, budget §9.4). Generators (`Tools/uwp build-*`) stay for blockouts, modular kits, variants and test fixtures.
- **`Tools/uwp` is the mandatory route for every asset**: `validate → export → Godot import test → review-sheet`. An asset may only be marked PRODUCTION-READY in `ASSET_REGISTRY.md` after `uwp export --profile gate` PASS (new release gate, T-PIPE-06) **and** the art review ≥ 4 (QUALITY_GATE). The dev profile stays permissive so WIP can be exported and played.
- Release gate = strict (warnings are errors) + LODs required (≥ `lod_min_triangles`) + collision required (non-characters) + TD-012 LOD/collision budgets + zero layered-clothing clipping. Values in `Config/asset_budgets.json` (`gate_profile`, `lod_triangle_fraction_max`, `collision_budget`).
- Consequence today: 8/17 sources pass the technical gate (all kit pieces, crate, pistol); all 7 characters and the sedan fail it (audit table). Technical PASS is **not** production-ready - every asset is still REJECT in art review.

## TD-012 – LOD, collision and material budgets → applied (Claude Code, 2026-11-23, T-PIPE-05)
**Status: APPLIED, acceptance by Bot 1.** Values now live in `Config/asset_budgets.json`: `lod_triangle_fraction_max` (LOD1 50 %, LOD2 20 %, LOD3 8 % of the category LOD0 budget → characters 40k/20k/8k as in master prompt §5.5), `collision_budget` (convex ≤ 64 vertices - the generator now really meets it, it produced 65 before -, trimesh ≤ 5,000 tris for Environment, 1,500 for Props), `max_materials` unchanged. Checked after generation as `LOD_BUDGET` / `COLLISION_BUDGET` (warning in dev, error in the gate).
## TD-024 – Global illumination and the single look source (Claude Code, 2026-11-23, T-LOOK-01)
**Status: PROPOSED** (owner sign-off). Evidence: `Docs/Reports/BERICHT_T-LOOK-01.md`.
- **One look source:** `Scripts/game/sun_preset.gd` (key light per preset) + `Assets/Environments/ENV_LA_<Preset>.tres` are used by BOTH the look-dev scene and the level generator. No inline environments in generators.
- **GI now:** sky ambient (colour + sky contribution) + SSAO + reflection probes for exteriors; **LightmapGI** for interiors (garage, warehouse) when they get art. **No SDFGI by default:** with the current presets it collapsed the measured fill to near black (9/4/10) and its cost/convergence cannot be measured without a GPU (B-003). Re-evaluate SDFGI on a GPU for the open world with time of day (M4).
- **Calibration targets (proposed):** lit 18 % card sRGB 130–160 by day, 90 % white ≤ 250, day key:fill 4:1–9:1 (linear), cool fill (B ≥ R). Measured by `Tests/tools/capture_lookdev.gd` → `lookdev_metrics.json`.

## TD-025 – Combat database and content catalogue as the single data source (Claude Code, 2026-11-23, T-DATA-01)
**Status: PROPOSED.** Evidence: `Docs/Reports/BERICHT_T-DATA-01.md`.
- **Combat numbers live in one file:** `GodotProject/Data/Content/combat.json` (in `res://` because the game reads it at runtime). It holds weapons, armor, NPC archetypes (civilian, enemy_light/medium/heavy, boss, police_patrol, fbi_tactical, ally) and faction rosters. `Scripts/game/combat_db.gd` (`CombatDB`) builds `WeaponData`, `AIProfile` and armor from it; `CombatDB.apply(npc, archetype)` turns any `NPCController` into an archetype. Hand-made `.tres` files may only mirror the JSON; `test_combat_db.gd` fails if the shipped pistol disagrees.
- **Armor model:** a hit in a covered zone (0 BODY vest, 1 HEAD helmet; limbs never) is reduced by `absorb × (1 − armor_penetration)` until the piece's points are used up; `reset()` restores armor. Balance is expressed as pistol body hits to kill per tier (`design_targets`), simulated with the real `DamageReceiver` and asserted in the gate.
- **Asset list lives in one file:** `Config/Content/catalog.json` lists every chapter 1+2 asset (built and planned) with milestone, generator, source and export path. `Tools/uwp catalog check` (merge gate, via the uwp tool tests) cross-checks catalogue ↔ combat database ↔ `Assets/`: nothing ships uncatalogued, nothing claims a file that is missing, nothing is PRODUCTION-READY without a review record. `catalog build` runs generator + exporter per entry; `catalog status` writes `Docs/Reports/CATALOG_STATUS.md` (our production tracking instead of ShotGrid).

## TD-026 – Generated prop kit: shared CC0 material library, world-space texel density, lightmap UVs, label atlases (Claude Code, 2026-11-23, T-PROP-01)
**Status: PROPOSED.** Evidence: `Docs/Reports/BERICHT_T-PROP-01.md`.
- **Generator, not hand edits:** street furniture, items and armor come from `Tools/uwp build-props` (`Tools/underworld_pipeline/props/`: `kit.py` primitives + `recipes.py`, one function per asset, real-world sizes, front −Y per TD-004). A changed recipe re-builds the `.blend` source; `uwp export --profile gate` is mandatory.
- **One material library** (`kit.MATERIALS`): CC0 Poly Haven sets at 512 px with tint, metallic and roughness bias, plus flat "painted" variants that borrow a set's normal and roughness breakup. All props share it, so the street reads as one place. A missing texture set is a **build error**, never a silent grey material.
- **UV policy:** UV0 = world-space box projection (1 UV unit = the material's `tile_m`), so texel density is constant across assets (256–512 px/m, budget ≥ 128). UV0 tiles on purpose (`uw_allow_uv_overlap`). **UV1 = unique lightmap layout** (Godot UV2 for LightmapGI, TD-024).
- **Signage** (invented names only) is rasterised into **one label atlas per asset** (power-of-two, a single material), with text-correct orientation on every face.
- **Collision:** authored convex boxes (`UCX_*-convcolonly`) per asset; walkable tiles use one flat `-colonly` slab with its top at the asphalt height (B-PT-01 rule). LOD1/LOD2 come from the exporter.
- **Hero quality is not claimed:** this is a production-quality blockout+ kit (gate-clean, textured, lit). Hero props (sculpt/bake detail, decals, wear masks) follow TD-021.

## TD-027 – Building grammar for city blocks (Claude Code, 2026-11-23, T-BLDG-01)
**Status: PROPOSED.** Evidence: `Docs/Reports/BERICHT_T-BLDG-01.md`.
- **`Tools/uwp build-buildings`** (`props/buildings.py`) builds buildings from rules instead of hand-placed boxes:
  - footprint × floors × bays
  - walls with real openings and reveals, plus set-back glass, door and roll-up fills, sills and mullions
  - string courses and cornices
  - roofs: flat with parapet, hip with clay tiles, or barrel vault
  - extras: awnings, fire escapes, galleries, railings, signs from the label atlas, rooftop units
- Same material library and UV policy as TD-026.
- **≤ 8 materials per building:** the gate's `MATERIAL_COUNT` is an error in `--profile gate`, so draw calls are bounded.
- **Closed shells, no interiors:** glass is dark, and walls have no back faces, which roughly halves the triangles. Enterable interiors (garage, warehouse M01, safehouses) are separate interior kits with LightmapGI (TD-024).
- **Collision:** one convex box per volume, plus canopies, docks and posts.
- A new building type is a new rule set of ~30–60 lines, not a modelling session. Bespoke hero facades (landmarks) stay hand-authored (TD-021).

## TD-028 – Weapon grammar and gameplay-coupled weapon animation (Claude Code, 2026-11-23, T-WPN-01)
**Status: PROPOSED.** Evidence: `Docs/Reports/BERICHT_T-WPN-01.md`.
- **`Tools/uwp build-weapons`** (`props/weapons.py`) builds every `combat.json` weapon as a multi-part asset with the REQ-GP02 contract:
  - grip origin, barrel along +Z
  - parts Frame, Slide, Magazine, Barrel, Trigger, Hammer
  - SOCKET_Grip, SOCKET_Muzzle and SOCKET_Eject
  - a rigid rig with A_<id>_Fire, A_<id>_Reload and A_<id>_Empty
- **Coupling:** the generator reads the Reload clip length from `combat.json` `reload_time`. `test_combat_db.gd` fails if clip and data drift apart (tolerance 1 frame).
- **Linking:** `combat.json` `weapons.<id>.scene` points at the asset, and `CombatDB.weapon()` loads it.
