# Content-Katalog – Status (automatisch erzeugt)

Quelle: `Config/Content/catalog.json` · Werkzeug: `Tools/uwp catalog status`. Nicht von Hand editieren.

| Status | Anzahl |
|---|---|
| PLANNED | 35 |
| WIP | 66 |
| PRODUCTION-READY | 0 |
| **gesamt** | **101** |

| Meilenstein | gesamt | PLANNED | WIP | PRODUCTION-READY | Generator vorhanden |
|---|---|---|---|---|---|
| P2 | 2 | 2 | 0 | 0 | 0/2 |
| P3 | 30 | 1 | 29 | 0 | 29/30 |
| P4 | 20 | 13 | 7 | 0 | 20/20 |
| P5 | 31 | 2 | 29 | 0 | 31/31 |
| P6 | 18 | 17 | 1 | 0 | 1/12 |

## P2

| ID | Typ | Status | Ziel | Generator | Datei |
|---|---|---|---|---|---|
| DC_LA_Decals | decal_set | PLANNED | blockout+ | `build-decals` (fehlt) | – |
| TS_LA_Trims | trim_sheet | PLANNED | blockout+ | `build-trims` (fehlt) | – |

## P3

| ID | Typ | Status | Ziel | Generator | Datei |
|---|---|---|---|---|---|
| SM_LA_Billboard | environment | WIP | blockout+ | `build-props --only SM_LA_Billboard` | ✓ |
| SM_LA_Bldg_Apartment4F | environment | WIP | blockout+ | `build-buildings --only SM_LA_Bldg_Apartment4F` | ✓ |
| SM_LA_Bldg_GarageM01 | environment | WIP | blockout+ | `build-env --only SM_LA_Bldg_GarageM01` | ✓ |
| SM_LA_Bldg_GasStation | environment | WIP | blockout+ | `build-buildings --only SM_LA_Bldg_GasStation` | ✓ |
| SM_LA_Bldg_Hangar | environment | WIP | blockout+ | `build-buildings --only SM_LA_Bldg_Hangar` | ✓ |
| SM_LA_Bldg_LiquorStore | environment | WIP | blockout+ | `build-buildings --only SM_LA_Bldg_LiquorStore` | ✓ |
| SM_LA_Bldg_Motel | environment | WIP | blockout+ | `build-buildings --only SM_LA_Bldg_Motel` | ✓ |
| SM_LA_Bldg_OfficeDowntown | environment | WIP | blockout+ | `build-buildings --only SM_LA_Bldg_OfficeDowntown` | ✓ |
| SM_LA_Bldg_ShopStucco | environment | WIP | blockout+ | `build-env --only SM_LA_Bldg_ShopStucco` | ✓ |
| SM_LA_Bldg_VillaCrestmont | environment | WIP | blockout+ | `build-buildings --only SM_LA_Bldg_VillaCrestmont` | ✓ |
| SM_LA_Bldg_Warehouse | environment | WIP | blockout+ | `build-buildings --only SM_LA_Bldg_Warehouse` | ✓ |
| SM_LA_BusStop | environment | WIP | blockout+ | `build-props --only SM_LA_BusStop` | ✓ |
| SM_LA_Bush | environment | WIP | blockout+ | `build-props --only SM_LA_Bush` | ✓ |
| SM_LA_Dumpster | environment | WIP | blockout+ | `build-props --only SM_LA_Dumpster` | ✓ |
| SM_LA_Fence_Chainlink | environment | WIP | blockout+ | `build-props --only SM_LA_Fence_Chainlink` | ✓ |
| SM_LA_Hydrant | environment | WIP | blockout+ | `build-props --only SM_LA_Hydrant` | ✓ |
| SM_LA_NewspaperBox | environment | WIP | blockout+ | `build-props --only SM_LA_NewspaperBox` | ✓ |
| SM_LA_PalmTree | environment | WIP | blockout+ | `build-env --only SM_LA_PalmTree` | ✓ |
| SM_LA_ParkingMeter | environment | WIP | blockout+ | `build-props --only SM_LA_ParkingMeter` | ✓ |
| SM_LA_PhoneBooth | environment | WIP | blockout+ | `build-props --only SM_LA_PhoneBooth` | ✓ |
| SM_LA_PowerPole | environment | WIP | blockout+ | `build-props --only SM_LA_PowerPole` | ✓ |
| SM_LA_Road_Crosswalk | environment | WIP | blockout+ | `build-props --only SM_LA_Road_Crosswalk` | ✓ |
| SM_LA_Road_Intersection | environment | WIP | blockout+ | `build-props --only SM_LA_Road_Intersection` | ✓ |
| SM_LA_Road_Straight | environment | WIP | blockout+ | `build-env --only SM_LA_Road_Straight` | ✓ |
| SM_LA_Sidewalk_Curb | environment | WIP | blockout+ | `build-env --only SM_LA_Sidewalk_Curb` | ✓ |
| SM_LA_StreetSign | environment | WIP | blockout+ | `build-props --only SM_LA_StreetSign` | ✓ |
| SM_LA_Streetlight | environment | WIP | blockout+ | `build-env --only SM_LA_Streetlight` | ✓ |
| SM_LA_TrafficLight | environment | WIP | blockout+ | `build-props --only SM_LA_TrafficLight` | ✓ |
| SM_LA_TrashCan | environment | WIP | blockout+ | `build-props --only SM_LA_TrashCan` | ✓ |
| TR_LA_SanArdo | terrain | PLANNED | blockout+ | `build-terrain` (fehlt) | – |

## P4

| ID | Typ | Status | Ziel | Generator | Datei |
|---|---|---|---|---|---|
| SK_Boss_Cuervos_Jefe | character | PLANNED | authored | `build-character Config/Characters/SK_Boss_Cuervos_Jefe.json` | – |
| SK_Boss_Hermandad_Patron | character | PLANNED | authored | `build-character Config/Characters/SK_Boss_Hermandad_Patron.json` | – |
| SK_Jason | character | WIP | hero-authored | `build-character Config/Characters/SK_Jason.json` | ✓ |
| SK_NPC_Cartel_A | character | WIP | authored | `build-character Config/Characters/SK_NPC_Cartel_A.json` | ✓ |
| SK_NPC_Cartel_B | character | WIP | authored | `build-character Config/Characters/SK_NPC_Cartel_B.json` | ✓ |
| SK_NPC_Civ_Kit | character | PLANNED | authored | `build-character Config/Characters/SK_NPC_Civ_Kit.json` | – |
| SK_NPC_Civilian_Female | character | WIP | authored | `build-character Config/Characters/SK_NPC_Civilian_Female.json` | ✓ |
| SK_NPC_Cop_LA | character | WIP | authored | `build-character Config/Characters/SK_NPC_Cop_LA.json` | ✓ |
| SK_NPC_Cuervos_Heavy | character | PLANNED | authored | `build-character Config/Characters/SK_NPC_Cuervos_Heavy.json` | – |
| SK_NPC_Cuervos_Soldier | character | PLANNED | authored | `build-character Config/Characters/SK_NPC_Cuervos_Soldier.json` | – |
| SK_NPC_Dana_Whitlock | character | PLANNED | authored | `build-character Config/Characters/SK_NPC_Dana_Whitlock.json` | – |
| SK_NPC_FBI_Tactical | character | PLANNED | authored | `build-character Config/Characters/SK_NPC_FBI_Tactical.json` | – |
| SK_NPC_Hermandad_A | character | PLANNED | authored | `build-character Config/Characters/SK_NPC_Hermandad_A.json` | – |
| SK_NPC_Hermandad_Heavy | character | PLANNED | authored | `build-character Config/Characters/SK_NPC_Hermandad_Heavy.json` | – |
| SK_NPC_Hermandad_Soldier | character | PLANNED | authored | `build-character Config/Characters/SK_NPC_Hermandad_Soldier.json` | – |
| SK_NPC_Kings_A | character | PLANNED | authored | `build-character Config/Characters/SK_NPC_Kings_A.json` | – |
| SK_NPC_Kings_B | character | PLANNED | authored | `build-character Config/Characters/SK_NPC_Kings_B.json` | – |
| SK_NPC_Kings_Lieutenant | character | PLANNED | authored | `build-character Config/Characters/SK_NPC_Kings_Lieutenant.json` | – |
| SK_NPC_Marco | character | WIP | hero-authored | `build-character Config/Characters/SK_NPC_Marco.json` | ✓ |
| SK_NPC_Sam | character | WIP | hero-authored | `build-character Config/Characters/SK_NPC_Sam.json` | ✓ |

## P5

| ID | Typ | Status | Ziel | Generator | Datei |
|---|---|---|---|---|---|
| SM_Prop_Helmet_Tactical | armor | WIP | blockout+ | `build-props --only SM_Prop_Helmet_Tactical` | ✓ |
| SM_Prop_Vest_Heavy | armor | WIP | blockout+ | `build-props --only SM_Prop_Vest_Heavy` | ✓ |
| SM_Prop_Vest_Light | armor | WIP | blockout+ | `build-props --only SM_Prop_Vest_Light` | ✓ |
| SM_Prop_Barrel | prop | WIP | blockout+ | `build-props --only SM_Prop_Barrel` | ✓ |
| SM_Prop_CashBundle | prop | WIP | blockout+ | `build-props --only SM_Prop_CashBundle` | ✓ |
| SM_Prop_DrugBrick | prop | WIP | blockout+ | `build-props --only SM_Prop_DrugBrick` | ✓ |
| SM_Prop_Duffel | prop | WIP | blockout+ | `build-props --only SM_Prop_Duffel` | ✓ |
| SM_Prop_GoldBar | prop | WIP | blockout+ | `build-props --only SM_Prop_GoldBar` | ✓ |
| SM_Prop_PackageCrate | prop | WIP | blockout+ | `build-env --only SM_Prop_PackageCrate` | ✓ |
| SM_Prop_Pallet | prop | WIP | blockout+ | `build-props --only SM_Prop_Pallet` | ✓ |
| SM_Prop_Phone | prop | WIP | blockout+ | `build-props --only SM_Prop_Phone` | ✓ |
| SM_Prop_Toolbox | prop | WIP | blockout+ | `build-props --only SM_Prop_Toolbox` | ✓ |
| SM_Prop_Workbench | prop | WIP | blockout+ | `build-props --only SM_Prop_Workbench` | ✓ |
| VH_Motorcycle_01 | vehicle | PLANNED | blockout+ | `build-vehicle Config/Vehicles/VH_Motorcycle_01.json` | – |
| VH_Muscle_01 | vehicle | WIP | blockout+ | `build-vehicles --only VH_Muscle_01` | ✓ |
| VH_Pickup_01 | vehicle | WIP | blockout+ | `build-vehicles --only VH_Pickup_01` | ✓ |
| VH_Plane_Small_01 | vehicle | PLANNED | blockout+ | `build-vehicle Config/Vehicles/VH_Plane_Small_01.json` | – |
| VH_Police_01 | vehicle | WIP | blockout+ | `build-vehicles --only VH_Police_01` | ✓ |
| VH_Sedan_01 | vehicle | WIP | hero-authored | `build-vehicle Config/Vehicles/VH_Sedan_01.json` | ✓ |
| VH_Taxi_NY_01 | vehicle | WIP | blockout+ | `build-vehicles --only VH_Taxi_NY_01` | ✓ |
| VH_Van_01 | vehicle | WIP | blockout+ | `build-vehicles --only VH_Van_01` | ✓ |
| WPN_Bat_01 | weapon | WIP | blockout+ | `build-weapons --only WPN_Bat_01` | ✓ |
| WPN_Grenade_01 | weapon | WIP | blockout+ | `build-weapons --only WPN_Grenade_01` | ✓ |
| WPN_Knife_01 | weapon | WIP | blockout+ | `build-weapons --only WPN_Knife_01` | ✓ |
| WPN_Molotov_01 | weapon | WIP | blockout+ | `build-weapons --only WPN_Molotov_01` | ✓ |
| WPN_Pistol_01 | weapon | WIP | hero-authored | `build-weapon Config/Weapons/WPN_Pistol_01.json` | ✓ |
| WPN_Revolver_01 | weapon | WIP | blockout+ | `build-weapons --only WPN_Revolver_01` | ✓ |
| WPN_Rifle_01 | weapon | WIP | blockout+ | `build-weapons --only WPN_Rifle_01` | ✓ |
| WPN_SMG_01 | weapon | WIP | blockout+ | `build-weapons --only WPN_SMG_01` | ✓ |
| WPN_Shotgun_01 | weapon | WIP | blockout+ | `build-weapons --only WPN_Shotgun_01` | ✓ |
| WPN_Sniper_01 | weapon | WIP | blockout+ | `build-weapons --only WPN_Sniper_01` | ✓ |

## P6

| ID | Typ | Status | Ziel | Generator | Datei |
|---|---|---|---|---|---|
| A_Boss_Specials | animation | PLANNED | mocap | `authored (mocap/keyframe)` | – |
| A_Humanoid_Cover_Set | animation | PLANNED | mocap | `authored (mocap/keyframe)` | – |
| A_Humanoid_Locomotion | animation | WIP | mocap | `build-shared-anims` | ✓ |
| A_Humanoid_Locomotion_Mocap | animation | PLANNED | mocap | `authored (mocap/keyframe)` | – |
| A_Humanoid_Melee_Set | animation | PLANNED | mocap | `authored (mocap/keyframe)` | – |
| A_Humanoid_Sit_Driver | animation | PLANNED | mocap | `authored (mocap/keyframe)` | – |
| A_Humanoid_Sit_Passenger | animation | PLANNED | mocap | `authored (mocap/keyframe)` | – |
| FX_Blood_Set | fx | PLANNED | blockout+ | `build-fx --only FX_Blood_Set` (fehlt) | – |
| FX_Explosion | fx | PLANNED | blockout+ | `build-fx --only FX_Explosion` (fehlt) | – |
| FX_Fire | fx | PLANNED | blockout+ | `build-fx --only FX_Fire` (fehlt) | – |
| FX_GlassShatter | fx | PLANNED | blockout+ | `build-fx --only FX_GlassShatter` (fehlt) | – |
| FX_Impact_Set | fx | PLANNED | blockout+ | `build-fx --only FX_Impact_Set` (fehlt) | – |
| FX_MuzzleFlash_Set | fx | PLANNED | blockout+ | `build-fx --only FX_MuzzleFlash_Set` (fehlt) | – |
| FX_Rain | fx | PLANNED | blockout+ | `build-fx --only FX_Rain` (fehlt) | – |
| FX_Smoke | fx | PLANNED | blockout+ | `build-fx --only FX_Smoke` (fehlt) | – |
| FX_Sparks | fx | PLANNED | blockout+ | `build-fx --only FX_Sparks` (fehlt) | – |
| FX_Steam_NY | fx | PLANNED | blockout+ | `build-fx --only FX_Steam_NY` (fehlt) | – |
| FX_TireSmoke | fx | PLANNED | blockout+ | `build-fx --only FX_TireSmoke` (fehlt) | – |
