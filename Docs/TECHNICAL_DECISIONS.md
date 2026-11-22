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
