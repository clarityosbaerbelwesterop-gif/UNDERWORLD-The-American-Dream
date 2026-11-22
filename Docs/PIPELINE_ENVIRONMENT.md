# UNDERWORLD Modular LA Street Environment Pipeline (`T-ART-03`)

Spec-driven 2 m-grid modular environment kit generator (`Tools/underworld_pipeline/environment/build_la_kit.py`) using verified CC0 Poly Haven PBR textures (`asphalt_02`, `concrete_pavement`, `red_brick`, `plastered_wall`, `corrugated_iron`, `bark_brown_02`, `metal_plate`).

## Usage
```bash
python3 Tools/underworld_pipeline/fetch_sources.py --groups environment
Tools/uwp build-env
Tools/uwp export-all --source-root Blender/Source/Environment/LA
Tools/uwp export Blender/Source/Props/SM_Prop_PackageCrate/SM_Prop_PackageCrate.blend
```

## Modular Kit Pieces (East Hollow / "Calloway Avenue" — M01 Dead Drop)
| Asset | Category | Footprint / Height | Collision | LODs |
|---|---|---|---|---|
| `SM_LA_Road_Straight` | `Environment/LA` | 10 × 14 m (2 lanes + double-yellow centerline) | Trimesh `-colonly` | Auto via `uwp` |
| `SM_LA_Sidewalk_Curb` | `Environment/LA` | 4 × 10 m, 0.16 m curb | Trimesh `-colonly` | Auto via `uwp` |
| `SM_LA_Bldg_ShopStucco` | `Environment/LA` | 10 × 8 × 7.5 m 2-storey storefront w/ awning | Trimesh `-colonly` | LOD0/1/2 |
| `SM_LA_Bldg_GarageM01` | `Environment/LA` | 12 × 10 × 4.9 m hollow M01 Dead Drop garage + workbench + `SOCKET_PackageBench` | Trimesh `-colonly` | LOD0/1/2 |
| `SM_LA_Streetlight` | `Environment/LA` | 7.2 m LA sodium-vapor cobra lamp | Trimesh `-colonly` | LOD0/1/2 |
| `SM_LA_PalmTree` | `Environment/LA` | 11.5 m California fan palm | Trimesh `-colonly` | LOD0/1/2 |
| `SM_Prop_PackageCrate` | `Props` | 0.6 × 0.4 × 0.4 m M01 sealed crate | Convex `-convcolonly` | LOD0/1/2 |

## Vertical-Slice Godot Assembly
`GodotProject/Scenes/Levels/LA_CallowayAve_Block.tscn` assembles a **greybox** East Hollow street block (no player, mission logic or navmesh yet – T-LVL-01 / T-MIS-01, Bot 3) from the exported `.glb` kit with Mission M01 trigger areas (`Area_GarageArrival`, `Area_GarageInside`, `Area_Warehouse`, `Pickup_Package`), `VH_Sedan_01`, and `ENV_LA_GoldenHour.tres`.
