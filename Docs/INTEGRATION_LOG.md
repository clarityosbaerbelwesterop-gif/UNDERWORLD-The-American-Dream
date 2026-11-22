# Integration Log

Every Blender→Godot integration (or engine-side change to an asset) gets an entry. Newest on top. Times Europe/Berlin.

## 2026-11-22 09:44 – Player controller with PT_ capsule stand-in (Bot 3, T-GP-01)
- No Bot 2 asset integrated yet: `Scenes/Player/Player.tscn` uses Godot primitives (`PT_Capsule`, `PT_FrontMarker`) per the placeholder rule.
- Integration point for SK_Jason: set `Visual.model_scene = res://Assets/Characters/SK_Jason/SK_Jason.glb`; `CharacterVisual` hides the PT meshes, finds the AnimationPlayer and builds the locomotion AnimationTree from the clip names in `Docs/Handoffs/REQ_SK_Jason_Controller.md`. Verified headless with a dummy model carrying empty `A_Jason_*` clips (tree active, blend parameters driven, missing clips reported).
- Engine-side check against an existing asset: player stops at `PT_PipelineTest_Crate` in `Main.tscn` (min z 0.850 m = crate half-size 0.5 + capsule radius 0.35), never sinks below Main ground. Result: **PASS**.

## 2026-11-22 09:30 – PT_PipelineTest_Crate (Bot 1)
- Export: Blender 5.2.4 LTS headless, `Tools/blender_export.py`, glTF GLB, `export_yup=True`, `export_apply=True`. Round-trip re-import in Blender: 3 meshes.
- Import: Godot 4.7.2 `--headless --import` via `GodotProject/Assets -> ../Assets` symlink, no errors; `.import` sidecar generated.
- Verified in Godot (smoke_test.gd): 2 MeshInstance3D, `-colonly` hint → 1 StaticBody3D + 1 CollisionShape3D, body AABB 1×1×1 m at y=0, material present, front marker at +Z (Blender −Y → Godot +Z).
- Result: **PASS**. Asset is a placeholder.
