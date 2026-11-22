# Tools (owner: Bot 2; bootstrap by Bot 1)

| Script | Purpose | Run |
|---|---|---|
| `blender_export.py` | **Pipeline smoke test exporter.** Builds the placeholder `PT_PipelineTest_Crate` procedurally, applies transforms, validates (dims, UVs, materials, applied transforms), saves `Blender/Source/Test/*.blend`, exports `Assets/Test/*.glb`, re-imports to verify, writes `.manifest.json`. | `/workspace/tools/blender/blender -b --factory-startup --python-exit-code 1 --python Tools/blender_export.py -- --repo .` (add `--save-blend` to rewrite the .blend; .blend bytes are not deterministic, so the smoke test leaves it alone) |

Planned (T-PIPE-01, Bot 2): `Tools/underworld_pipeline/` – generic validate/LOD/collision/export/preview for every asset in `Blender/Source/`, reading `Config/asset_budgets.json`.
`Tools/build/` is reserved for Bot 3 build scripts (T-BUILD-01).
