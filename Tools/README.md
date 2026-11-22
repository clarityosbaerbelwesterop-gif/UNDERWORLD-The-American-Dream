# Tools (owner: Bot 2; bootstrap by Bot 1)

| Script | Purpose | Run |
|---|---|---|
| `uwp` → `underworld_pipeline/` | **Production asset pipeline (T-PIPE-01).** Validate → LODs → collision → `.glb` → Cycles-CPU preview → manifest → round-trip verify, JSON report + exit codes. | `Tools/uwp export Blender/Source/<Cat>/<Name>/<Name>.blend` |
| `blender_export.py` | **Pipeline smoke test exporter** (T-PIPE-00, kept unchanged). Builds `PT_PipelineTest_Crate`, exports `Assets/Test/*.glb`. Used by `Tests/run_pipeline_smoke.sh`. | `/workspace/tools/blender/blender -b --factory-startup --python-exit-code 1 --python Tools/blender_export.py -- --repo .` |

`Tools/build/` is reserved for Bot 3 build scripts (T-BUILD-01).

## underworld_pipeline – usage

Runs headless inside Blender 5.2.4 (`/workspace/tools/blender/blender`, override with `BLENDER=`). `Tools/uwp` is a thin wrapper for
`blender -b --factory-startup --python Tools/underworld_pipeline/cli.py -- <args>`.

```bash
Tools/uwp validate <file.blend> [--category C] [--budget-key K] [--strict] [--report r.json]
Tools/uwp export   <file.blend> [--out x.glb] [--category C] [--budget-key K] [--strict]
                   [--no-lod] [--lod-ratios 0.5,0.25] [--no-collision] [--collision auto|box|convex|trimesh|none]
                   [--force-collision] [--no-preview] [--no-verify] [--report r.json]
Tools/uwp validate-all [--source-root DIR] [--report summary.json]
Tools/uwp export-all   [--source-root DIR] [--out-root DIR] [...export options] [--report summary.json]
Tools/underworld_pipeline/tests/run_tests.sh [--no-godot]     # end-to-end test (writes only to /tmp/uwp_test)
```

- **Paths (TD-006):** `Blender/Source/<Category>/<Name>/<Name>.blend` → `Assets/<Category>/<Name>/<Name>.glb` (+ `<Name>.manifest.json`, `<Name>.validation.json`, `<Name>_preview.png`). Category comes from the path (`Environment/LA` etc.); outside `Blender/Source` pass `--category` and `--out`.
- **Asset name = .blend file name.** The scene must contain a root object (empty, or armature) with exactly that name at the origin; everything else is parented under it.
- **The source .blend is never saved.** LODs and collision are generated in memory for the export only.
- `export-all` without `--out-root` skips `Blender/Source/Test/PT_PipelineTest_Crate.blend`, whose `.glb` is owned by the smoke test (it expects exactly 2 meshes). `validate-all` still checks it.

### Exit codes
`0` PASS (warnings allowed) · `1` validation failed (nothing exported) · `2` export failed · `3` round-trip verify failed · `4` usage/input error · `5` internal error. `*-all` returns the highest code.

### Checks (codes appear in the JSON report `issues[]` as `{severity, code, object, message}`)
Budgets come from `Config/asset_budgets.json` (Bot 1); tool defaults from `underworld_pipeline/defaults.json` (budgets file wins if it gets the same keys).

| Area | Errors | Warnings / info |
|---|---|---|
| Units / axes (TD-004) | `UNITS` (METRIC, scale 1.0); `FRONT_AXIS`: characters must face Blender −Y = Godot +Z (LeftUpperArm at +X, feet point −Y), meshes named `*Front*` must sit at −Y | `FRONT_AXIS` vehicle long axis not Y |
| Naming (TD-005) | `NAME_ASSET`, `NAME_PREFIX` (Characters `SK_`, Vehicles `VH_`, Weapons `WPN_`, Props/Environment `SM_`, Test `PT_`; `PT_` allowed everywhere), `NAME_OBJECT` (ASCII PascalCase parts + optional Godot hint), `NAME_MATERIAL` (`M_`), `NAME_ACTION` (`A_`), `UCX_NO_HINT` | `NAME_MESH_PREFIX`, `NAME_EMPTY` (non-root empties should be `SOCKET_`), `NAME_TEXTURE` (`T_`), `NAME_BONE`, `COLLISION_PREFIX` |
| Hierarchy / transforms | `ROOT_MISSING`, `ROOT_TRANSFORM`, `ROOT_PARENTED`, `OUTSIDE_ROOT`, `TRANSFORM_SCALE`, `TRANSFORM_ROTATION` (meshes/armatures), `NEGATIVE_SCALE` | `SOCKET_SCALE` (sockets may be rotated) |
| Origin (TD-004) | `ORIGIN_GROUND` (lowest point at z=0 ±1 cm, all but Weapons), `REFERENCE_HEIGHT` (`reference_heights_m`, e.g. Jason 1.82 ±0.02 m) | `ORIGIN_CENTRE` (Props/Characters/Vehicles/Test) |
| Geometry | `EMPTY_MESH`, `LOOSE_GEOMETRY` (loose verts/edges) | `NON_MANIFOLD` (>2 faces per edge, bow-tie verts), `DEGENERATE_FACES`, `OPEN_BOUNDARY` (warn on trimesh collision, info otherwise) |
| Budget (TD-009) | `TRI_BUDGET` (LOD0 visible tris vs `max_triangles`, most specific key: `Characters/SK_Jason` > category), `NO_BUDGET` | – |
| UV / materials / textures | `NO_UVS`, `NO_MATERIAL`, `EMPTY_MATERIAL_SLOT`, `TEXTURE_SIZE` (hero 2048 for Characters/Vehicles/Weapons, else 1024), `TEXTURE_MISSING` | `MATERIAL_COUNT`, `TEXTURE_POT` |
| Skinning | `BONE_INFLUENCES` (> `max_bone_influences` = 4), `UNWEIGHTED_VERTICES`, `SK_NOT_SKINNED`, `ARMATURE_MOD_EMPTY`, `HUMANOID_BONES` (Characters: all 22 required `SkeletonProfileHumanoid` bones of REQ-GP01-JASON) | `SKIN_PARENT`, `HUMANOID_OPTIONAL`, `VGROUP_NO_BONE` |
| Sockets | `SOCKET_MISSING`, `SOCKET_PARENT` (`required_sockets`, e.g. `SOCKET_RightHand_Weapon` on bone `RightHand` for SK_Jason) | – |
| Animation | `NAME_ACTION` | `ACTION_EMPTY`, `ANIM_FPS` (≠ 30), `ANIM_START_FRAME` (Characters), `ANIM_LOOP_SUFFIX` (name ends in `_loop`/`-loop`/`_cycle`/`-cycle`, any case: Godot strips it and forces looping, e.g. `A_Jason_Jump_Loop` → `A_Jason_Jump`) |

`--strict` turns every warning into an error.

### LODs
Static visible meshes ≥ `lod_min_triangles` (64) get children `<Name>_LOD1`, `<Name>_LOD2` (Decimate collapse, ratios per category in `defaults.json`, e.g. Props 0.5/0.25). **LOD0 keeps its original name** (code and tests address nodes by name; children follow moving parts like wheels). Skinned meshes get no baked LODs (Godot's importer generates mesh LODs). Each LOD node carries glTF extras `uw_lod` and `uw_visibility_range: [begin, end]` (m). Godot imports these as node metadata `extras`; `underworld_pipeline/godot/uw_lod_post_import.gd` (an `EditorScenePostImport`) applies them to `visibility_range_begin/end`. Without that script Godot shows all LOD levels at once, so Bot 3 sets `import_script/path` in the import presets (T-PIPE-02). The last distance is the cull distance. Opt out per object with custom property `uw_no_lod = 1`.

### Collision (Godot import hints)
Collision is generated only if the asset has no authored collision (`-col/-colonly/-convcol/-convcolonly` mesh). If it does, the authored collision is kept (`--force-collision` adds generated collision anyway). Defaults per category: Characters `none` (CharacterBody capsule), Environment `trimesh` (`UCX_<Mesh>-colonly` per mesh from its lowest LOD → `ConcavePolygonShape3D`), everything else `convex` (`UCX_<Asset>-convcolonly`, hull ≤ 64 verts → `ConvexPolygonShape3D`). `box` = 8-vertex bounding box `-convcolonly`.

### glTF export settings
GLB, `export_yup`, `export_apply` (modifiers; the Armature modifier stays a skin), materials + embedded images, tangents, extras, no cameras/lights, skins with ≤ 4 influences, `export_def_bones` (deform bones only), no leaf bones, `export_animation_mode='ACTIONS'` (every action becomes one Godot animation named like the action), forced sampling, `export_anim_slide_to_zero` (every action starts at t=0, so a 31-frame cycle at 30 fps is exactly 1.0 s in Godot). Loop flags are not encoded in names: the manifest lists `loop` per action (Blender action "Manual Frame Range + Cyclic", or custom property `loop`); Bot 3 sets loop mode in the import presets.

### Outputs
- `<Name>.manifest.json` (deterministic, commit it): category, budget key, Godot-space AABB, tris per LOD vs budget, LOD + collision nodes, materials, textures, armature bones, animations (frames, fps, duration, loop), sockets (parent bone, Godot position), glb node names.
- `<Name>.validation.json`: full report (timestamp, every issue, step results, round-trip details, `result`, `exit_code`).
- `<Name>_preview.png`: 320² Cycles CPU, 16 samples, 3/4 front view (front = −Y), LOD>0 and collision hidden.

### Test (`underworld_pipeline/tests/run_tests.sh`)
Builds test assets with bpy (`make_test_assets.py`): a textured prop, a skinned 3-bone tube with 2 actions, a minimal humanoid facing −Y and the same one facing +Y, and a deliberately broken asset. Then it runs the exporter (good assets → 0; broken → 1 with all expected error codes; option and exit-code cases), checks reports and manifests, re-imports the .glb files in Blender (`verify_glb.py`: objects, LOD children with fewer faces, skin, actions that actually move bones), and imports them into a throw-away Godot 4.7.2 project with the LOD post-import script (`godot_verify.gd`: node types, visibility ranges, StaticBody3D + Convex/Concave shapes, Skeleton3D bones, AnimationPlayer lengths, bone rotation during playback, min y = 0, character front on +Z). It also runs `validate-all` and `export-all --out-root` on `Blender/Source`.
