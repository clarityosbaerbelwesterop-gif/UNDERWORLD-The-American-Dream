# Integration Log

Every Blender→Godot integration (or engine-side change to an asset) gets an entry. Newest on top. Times Europe/Berlin.

## 2026-11-22 10:25 – SK_Jason v2 production character asset → Godot 4.7.2 (Lead TD, T-PIPE-03)
- Asset: `Assets/Characters/SK_Jason/SK_Jason.glb` (10.7 MB, 35,789 tris, 12 meshes, 10 PBR materials, 20 ARKit/viseme blendshapes, 53 `SkeletonProfileHumanoid` bones, `SOCKET_RightHand_Weapon`, 21 `A_Jason_*` animations) replacing procedural primitive v1 at the identical path and contract (`REQ-GP01-JASON`, TD-004, TD-005 addendum `A_Jason_Jump_Air`).
- Import: Godot 4.7.2 headless with `res://Scripts/import/uw_post_import.gd` — 0 errors, 0 warnings; `[UW-IMPORT]` `lod_nodes=0 loops_set=21 manifest=yes missing=[]`.
- Verified: `Blender/Scripts/sk_jason/verify_sk_jason.sh` PASS (53/53 bones mapped to `SkeletonProfileHumanoid`, 12 skinned `MeshInstance3D` nodes, height 1.834 m within 1.82 ± 0.02 m, min y 0.0000, +Z front, `SOCKET_RightHand_Weapon` under `BoneAttachment3D(RightHand)` with aim basis +Y=1.000 / +Z=1.000, all 21 clip lengths & loop modes exact, Root untranslated, Hips max horizontal offset ≤ 1.5 cm); `Tests/run_all.sh` PASS (no Godot gameplay scripts modified).
- Result: **PASS** (visual look verified via 7 denoised Cycles CPU studio previews + concept-art silhouette check: front IoU 0.814, side IoU 0.700; in-engine GPU shader validation pending B-003).

## 2026-11-22 10:10 – PT pistol stand-in on the player hand socket (Bot 3, T-GP-02)
- No Bot 2 asset integrated: `Scenes/Weapons/PT_Pistol.tscn` (Godot primitives, PT_ prefix) mirrors the REQ-GP02-PISTOL node contract (origin at grip, barrel +Z, `Magazine`, `SOCKET_Muzzle`, `SOCKET_Eject`).
- Integration point: `WPN_Pistol_01.tres` → `scene = res://Assets/Weapons/WPN_Pistol_01/WPN_Pistol_01.glb`; the weapon follows `Visual/PT_SOCKET_RightHand_Weapon` now and `SOCKET_RightHand_Weapon` of SK_Jason once `PlayerWeaponController.attach_to_model_socket()` runs (verified headless with a dummy model).
- Result: **PASS** (headless; no GPU visual check).

## 2026-11-22 09:59 – Bot 2 pipeline exports → Godot import preset (Bot 3, T-PIPE-02)
- Assets: Bot 2's procedural test assets `PT_UWP_Barrel` (Props, 2 meshes × LOD0–2, convex collision), `PT_UWP_RigTest` (3-bone rig, 2 actions), `PT_UWP_Humanoid` (22 profile bones), exported with `Tools/uwp export --no-preview` into `GodotProject/Tests/_generated/` (gitignored, test-only).
- Import: Godot 4.7.2 headless, fresh `.import` sidecars pick up `import_script/path=res://Scripts/import/uw_post_import.gd` from `[importer_defaults]`; 0 import errors; `[UW-IMPORT]` log: barrel lod_nodes=6, rig loops_set=2.
- Verified: LOD ranges 0–15 / 15–40 / 40–100 m, one LOD drawn per distance; loop modes = manifest; AABBs = manifest; humanoid bone names ⊂ SkeletonProfileHumanoid. Result: **PASS**.
- Note for Bot 2: no Bot 2 file changed. New exports get the preset automatically; `uw_lod_post_import.gd` is vendored – if you change it, the test fails until `GodotProject/Scripts/import/uw_lod_post_import.gd` is re-copied (tell Bot 3 or copy it in your PR). Handoff: `Docs/Handoffs/2026-11-22_T-PIPE-02.md`.

## 2026-11-22 09:44 – Player controller with PT_ capsule stand-in (Bot 3, T-GP-01)
- No Bot 2 asset integrated yet: `Scenes/Player/Player.tscn` uses Godot primitives (`PT_Capsule`, `PT_FrontMarker`) per the placeholder rule.
- Integration point for SK_Jason: set `Visual.model_scene = res://Assets/Characters/SK_Jason/SK_Jason.glb`; `CharacterVisual` hides the PT meshes, finds the AnimationPlayer and builds the locomotion AnimationTree from the clip names in `Docs/Handoffs/REQ_SK_Jason_Controller.md`. Verified headless with a dummy model carrying empty `A_Jason_*` clips (tree active, blend parameters driven, missing clips reported).
- Engine-side check against an existing asset: player stops at `PT_PipelineTest_Crate` in `Main.tscn` (min z 0.850 m = crate half-size 0.5 + capsule radius 0.35), never sinks below Main ground. Result: **PASS**.

## 2026-11-22 09:30 – PT_PipelineTest_Crate (Bot 1)
- Export: Blender 5.2.4 LTS headless, `Tools/blender_export.py`, glTF GLB, `export_yup=True`, `export_apply=True`. Round-trip re-import in Blender: 3 meshes.
- Import: Godot 4.7.2 `--headless --import` via `GodotProject/Assets -> ../Assets` symlink, no errors; `.import` sidecar generated.
- Verified in Godot (smoke_test.gd): 2 MeshInstance3D, `-colonly` hint → 1 StaticBody3D + 1 CollisionShape3D, body AABB 1×1×1 m at y=0, material present, front marker at +Z (Blender −Y → Godot +Z).
- Result: **PASS**. Asset is a placeholder.
