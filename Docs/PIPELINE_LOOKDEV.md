# UNDERWORLD Godot Look-Dev & Lighting Pipeline

Cinematic Los Angeles lighting, sky, tonemapping, and color-grading presets for Godot 4.7.x (`Forward Plus`, ACES Filmic tonemapping), located in `Assets/Environments/` (referenced in Godot as `res://Assets/Environments/`).

## Environment Presets
| Resource | Mood / Time | Key Settings |
|---|---|---|
| `ENV_LA_GoldenHour.tres` | Chapter 1 / M01 signature warm LA sunset | `ProceduralSkyMaterial` warm amber horizon, ACES Filmic (`tonemap_mode = 3`, exposure `1.05`), SSAO, HDR bloom (`glow_bloom = 0.18`), warm sun-scatter aerial depth fog, film contrast `1.08` / saturation `0.94` |
| `ENV_LA_Midday.tres` | California coastal daylight | High crisp blue sky, lower fog density `0.0014`, balanced neutral exposure `1.0`, SSAO |
| `ENV_LA_Night.tres` | East Hollow night / sodium-vapor street contrast | Deep twilight sky, cool ambient `0.35`, elevated bloom (`glow_bloom = 0.30`) for streetlights/headlights/neon signs, atmospheric night fog `0.0045` |

## Showcase & Verification
- `GodotProject/Scenes/LookDev/LA_LookDev_Showcase.tscn` instances `SK_Jason`, `SK_NPC_Sam`, `WPN_Pistol_01`, and `VH_Sedan_01` under `ENV_LA_GoldenHour.tres` for GPU lighting & shader QA (once GPU hardware is attached, see B-003).
- `GodotProject/Scenes/Levels/LA_CallowayAve_Block.tscn` uses `ENV_LA_GoldenHour.tres` for the vertical-slice street block.
- Note: No Bot 3 gameplay scripts are modified by these presets.
