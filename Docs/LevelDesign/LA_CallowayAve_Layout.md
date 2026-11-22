# LA_CallowayAve – Level Layout Brief (T-DES-02)

Owner: project director · Consumers: art (T-ART-03), level assembly (T-LVL-01), mission (T-MIS-01)
Status: **v1 for M01 "Dead Drop"** · Units: metres, right-handed Godot axes (Y up, level faces +Z)
Related: `Docs/Missions/M01_DeadDrop.md` (behaviour), `Docs/GAME_DESIGN.md` §6 (look), TD-004 (axes/naming),
TD-010 (physics layers), TD-013 (navmesh), TD-014 (vehicles)

This brief is the single source of truth for dimensions and anchor positions. If the greybox
(`Scenes/Levels/LA_CallowayAve_Block.tscn`), the kit manifests and this file ever disagree, this file
wins and the differences get fixed in the same PR.

---

## 1. Design goals

| Goal | Consequence for the block-out |
|---|---|
| 10–15 min mission with one ~300 m drive loop | a simple, readable ring road around one city block |
| The garage ambush must be cover-readable at a glance | 6–8 usable cover anchors inside the garage, ≥ 2 flank routes into the interior |
| Golden-hour LA, "lived-in but poor" | shop row on the west side, low industrial buildings + the garage on the east side |
| No dead ends that trap the player | the drive loop is closed; every alley has a through path |
| Vertical slice, not a city | 1 block, 3 street segments, ~150 m × 150 m footprint |

## 2. Grid, modules and traffic language

The kit snaps to a **2 m grid**. Street furniture sits on sidewalk centres.

| Kit piece | Footprint (m) | Notes |
|---|---|---|
| `SM_LA_Road_Straight` | 10 (X) × 14 (Z) | 2 lanes + double-yellow centreline; road top at y = 0.045 |
| `SM_LA_Sidewalk_Curb` | 4 (X) × 10 (Z) | sidewalk top at y = 0.16, curb edge toward the road |
| `SM_LA_Bldg_ShopStucco` | 10 × 8 × 7.2 | front face toward −Y in Blender = **+Z** in Godot (faces the street) |
| `SM_LA_Bldg_GarageM01` | 12.2 × 10.2 × 4.9 | hollow interior, roll-up door on the street side |
| `SM_LA_Streetlight` | 7.2 tall | gooseneck, light head over the road |
| `SM_LA_PalmTree` | 11.5 tall | sidewalk planter |
| `SM_Prop_PackageCrate` | 0.61 × 0.41 × 0.41 | M01 pickup, sits on the garage bench |

Street cross-section (west → east): sidewalk 4 m · road 10 m (two 5 m lanes) · sidewalk 4 m.
Kerb-to-kerb the street is **10 m**; property line to property line **18 m**.

## 3. Top-down block-out

Coordinates are world metres, origin at the centre of the garage forecourt. `X` = east, `Z` = north.

```
              Z
              ↑
   ┌──────────────────────────────────────────────────────────┐
   │                        NORTH SEGMENT                     │  z = +72 .. +86
   │   [shop 3]      [apartment A]      [warehouse]           │
   │                                            ▲             │
   │                                            │             │
   │  ┌─────────────┐   ┌───────────────────────┴──────────┐  │
   │  │             │   │                                  │  │
   │  │  BLOCK A    │   │            BLOCK B               │  │
   │  │  shops +    │   │   garage  ◄── forecourt          │  │
   │  │  apartments │   │            (Area_GarageArrival)  │  │
   │  │             │   │                                  │  │
   │  └─────────────┘   └──────────────────────────────────┘  │
   │        WEST STREET (N–S)          EAST SERVICE LANE      │
   │                                                        │  │
   │                                                        ▼  │
   │                     SOUTH SEGMENT  z = -72 .. -86        │
   │        [shop 4]        [spawn: Marco's sedan]            │
   └──────────────────────────────────────────────────────────┘
                             X →
```

### 3.1 Streets

| Segment | Extent (X) | Extent (Z) | Kit modules | Purpose |
|---|---|---|---|---|
| `WEST` (main street) | x = −29 … −19 (road), −33 … −29 and −19 … −15 (sidewalks) | z = −86 … +86 | 12 road modules + 12+12 sidewalk modules | the "hero" street the camera sees on arrival |
| `EAST` (service lane) | x = +19 … +29 road | z = −86 … +86 | 12 road + sidewalks | garage access, delivery vans, the escape route |
| `NORTH` | x = −33 … +33 | z = +72 … +86 | 8 road modules | closes the loop, warehouse frontage |
| `SOUTH` | x = −33 … +33 | z = −72 … −86 | 8 road modules | start position, Marco's car |
| `WEST-ALLEY` (pedestrian) | x = −45 … −33 | z = −10 … +10 | plain concrete + 2 dumpsters | through-path so the block is never a trap |

Loop length (kerb centre line): 2 × (172 m) + 2 × (60 m) ≈ **464 m** of road, of which the M01 route uses
~300 m (south spawn → north segment → east lane → garage forecourt), which satisfies the "~300 m loop"
requirement and leaves room for a pursuit.

### 3.2 Buildings (Block A / Block B)

| ID | Piece | Position (X, Z) | Yaw | Notes |
|---|---|---|---|---|
| `Bldg_Shop_01` | ShopStucco | (−22, −60) | 180° | faces east onto the west street ("Vega Liquor" sign) |
| `Bldg_Shop_02` | ShopStucco | (−22, −38) | 180° | laundromat, awning |
| `Bldg_Shop_03` | ShopStucco | (−22, +20) | 180° | boarded up – environmental storytelling |
| `Bldg_Apartment_A` | ShopStucco (stacked ×2 for height) | (−22, +52) | 180° | placeholder for the 4-storey brick block (T-ART-03 backlog) |
| `Bldg_Shop_04` | ShopStucco | (−4, −80) | 0° | faces north onto the south segment |
| `Bldg_GarageM01` | GarageM01 | (+24, +6) | 270° | roll-up door faces **west** onto the east lane; interior 10 × 8 m |
| `Bldg_Warehouse` | ShopStucco ×3 (assembled) | (+26, +78) | 180° | `Area_Warehouse` delivery target, big roll-up door |
| `Bldg_Industrial_01` | ShopStucco | (+22, −50) | 270° | low industrial frontage along the east lane |

### 3.3 Mission anchors (exact names are binding for T-MIS-01)

| Node | Type | Position | Radius / size | Layer | Used by |
|---|---|---|---|---|---|
| `PlayerSpawn` | `Marker3D` | (−24.5, 0.16, −78) | – | – | M01 objective 0 |
| `VH_Sedan_01` (start) | instance | (−24.5, 0.05, −74), yaw 0° | – | 4 | objectives 1–2 |
| `Marco_Seat` | `Marker3D` | inside sedan, passenger (right/left per LHD) | – | – | Marco ally |
| `Area_GarageArrival` | `Area3D` | (+16, 0, +6) | sphere r = 8 | detect layer 3 (vehicles) | objective 2 complete |
| `Marker_GarageDoor` | `Marker3D` | (+18.8, 0, +6) | – | – | GPS arrow / waypoint |
| `Area_GarageInside` | `Area3D` | (+24, 0, +6) | box 10 × 3 × 8 | detect layer 2 (player) | objective 3 complete |
| `Pickup_Package` | `Area3D` + crate mesh | on the bench, (+26.5, 1.0, +8.5) | box 0.9 × 0.9 × 0.9 | detect layer 2 | objective 5 |
| `Spawn_Wave1_*` (×3) | `Marker3D` | (−14, 0, +22) / (−14, 0, +2) / (+2, 0, +20) | – | – | objective 4 wave 1 |
| `Spawn_Wave2_*` (×2) | `Marker3D` | van at (+30, 0, −8); rooftop (+29.6, 4.9, +6) | – | – | objective 4 wave 2 |
| `Cover_Garage_*` (×6) | `Node3D` + `CoverPoint` | see §5 | – | – | AI cover-lite |
| `Area_Warehouse` | `Area3D` | (+26, 0, +78) | box 12 × 6 × 10 | detect layer 3 | objective 6 complete |
| `NavRegion_Block` | `NavigationRegion3D` | whole block | – | – | baked, cell 0.25 |

## 4. Route for M01 (drive leg)

1. Spawn facing north on the west street at z = −78.
2. Drive north 150 m along the west street to the north segment (right turn at z = +78).
3. East along the north segment 60 m, passing the warehouse frontage on the right (the player sees
   the delivery target early — good for orientation).
4. South down the east service lane 72 m to the garage forecourt at z = +6, where `Area_GarageArrival`
   triggers. Total ≈ 300 m at an average 12 m/s ≈ 25 s of driving, plus turns.

## 5. Cover and combat geometry (garage ambush, objective 4)

Interior is 10 × 8 m with the door on the west wall. Objects inside:

| Cover anchor | Position | Type | Blocks |
|---|---|---|---|
| `Cover_Garage_Bench` | (+26.5, 0, +8.5) | workbench, 2.4 × 0.9 × 0.95 m | crouch cover |
| `Cover_Garage_Car_L` | (+23, 0, +2) | wrecked car body (Block A prop), 1.6 m | full cover |
| `Cover_Garage_Crate_A` | (+27.5, 0, +3) | 1.2 m crate stack | full cover |
| `Cover_Garage_Pillar_N` | (+21, 0, +9.5) | concrete pillar 0.4 × 0.4 m | partial |
| `Cover_Garage_Pillar_S` | (+21, 0, +2.5) | concrete pillar 0.4 × 0.4 m | partial |
| `Cover_Forecourt_Dumpster` | (+15.5, 0, −2) | dumpster 2.0 × 1.2 × 1.3 m | full cover, outside |

Flank routes: the open roll-up door (west) and a personnel door on the north wall. Both are 1.0 m wide
so the player can break line of sight; the AI never spawns behind the player's back inside the garage
(wave 1 comes from the street, wave 2 from the van and the roof hatch).

## 6. Lighting and atmosphere

* `ENV_LA_GoldenHour` preset, sun azimuth ~250°, elevation ~12°, long shadows down the west street.
* Streetlights off (dusk not yet); shop windows emit warm practical light (`LA_StoreGlass` emission).
* Garage interior: two 40 W sodium practicals, one flickering (`Flicker3D` on a 0.4–0.9 s band).
* Haze: 0.006 density, golden tint; no fog inside the garage (volume excluded).

## 7. Civilian and traffic dressing (T-AI-02 / M3)

* ≥ 3 civilian walkers on the west sidewalks, routes between z = −70 … +60, 1.4 m/s.
* 2 parked cars on the west street (parking lane), 1 van at the east lane near the garage.
* No moving traffic in M1 (traffic system is M3). Parked vehicles count as cover (layer 4).

## 8. Performance budget for the greybox → level pass

| Metric | Budget | Note |
|---|---|---|
| Kit draw calls (opaque) | ≤ 120 | merge repeated streetlights/palms per street segment if needed |
| Triangles in view (street) | ≤ 400 k | kit is blockout; the real budget comes with the art pass |
| Navmesh bake time (headless) | ≤ 20 s | cell 0.25, agent r 0.5 / h 2.0 / climb 0.25 (TD-013) |
| Physics bodies | ≤ 60 static + 1 vehicle + ≤ 12 characters | |
| Occluders | 4 (shop row, apartment, garage, warehouse) | |

## 9. What the art pass must add (feeds T-ART-03)

Crosswalk + traffic light at the north-west corner, hydrant, trash cans, bus stop, fences,
decal/trim sheets, apartment block, garage interior props (workbench is modelled inside the garage
piece, add a rolling tool chest), invented signage. Everything stays on the 2 m grid.

## 10. Open questions (owner / design)

1. Left-hand or right-hand drive for the sedan? Current asset has `SOCKET_Seat_Driver` on the left (−X);
   the layout above assumes **left-hand drive** (US), so Marco rides on the right.
2. B-004: is "Calloway Avenue" final? The node names above bake the street name in.
3. Warehouse interior: out of scope for M01 (the mission ends at the door) — confirm.
