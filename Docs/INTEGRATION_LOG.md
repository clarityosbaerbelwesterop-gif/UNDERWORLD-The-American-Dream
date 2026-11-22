# Integration Log

Every Blender→Godot integration (or engine-side change to an asset) gets an entry. Newest on top. Times Europe/Berlin.

## 2026-11-22 09:30 – PT_PipelineTest_Crate (Bot 1)
- Export: Blender 5.2.4 LTS headless, `Tools/blender_export.py`, glTF GLB, `export_yup=True`, `export_apply=True`. Round-trip re-import in Blender: 3 meshes.
- Import: Godot 4.7.2 `--headless --import` via `GodotProject/Assets -> ../Assets` symlink, no errors; `.import` sidecar generated.
- Verified in Godot (smoke_test.gd): 2 MeshInstance3D, `-colonly` hint → 1 StaticBody3D + 1 CollisionShape3D, body AABB 1×1×1 m at y=0, material present, front marker at +Z (Blender −Y → Godot +Z).
- Result: **PASS**. Asset is a placeholder.
