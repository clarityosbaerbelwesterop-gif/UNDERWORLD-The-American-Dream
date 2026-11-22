# UNDERWORLD Asset Pipeline Roadmap

Owner: Lead Tech Artist / Pipeline TD.  
Stack (binding): **Blender 5.2 LTS** (headless `bpy`) → **`Tools/uwp`** (validation, LODs, collision, Cycles CPU previews, manifests) → **glTF 2.0 (`.glb`)** → **Godot 4.7.x** (`uw_post_import.gd`).

All phases execute end-to-end on dedicated branches with individual PRs to `main`, verified by `Tests/run_all.sh`, `Tools/underworld_pipeline/tests/run_tests.sh`, and Cycles CPU proof renders.

---

## Phase 0 — Hero Character Pipeline & `SK_Jason` v2 (`T-PIPE-03`) — DELIVERED
- Spec-driven realistic character pipeline built on CC0 MakeHuman/MPFB2 `hm08` base, 1,258 parametric morphs, 20 ARKit/viseme blendshapes, 53-bone `SkeletonProfileHumanoid` rig + artist weights, layered fitted clothing, Cycles high-to-low normal/AO baking, CC0 Poly Haven PBR textures, CC0 BVH walk retargeting, and automated `uwp` quality gates (UV overlap, texel density, weight normalization, layered clipping check, multi-view Cycles previews, concept art silhouette comparison).
- Proven on `SK_Jason` v2 (35,789 tris, 10 materials, 20 blendshapes, 21 animations, silhouette IoU 0.756, 0 errors / 0 warnings).

---

## Phase 1 — NPC Cast & Shared Animation Library (`T-ART-06`)
- **Goal**: Generate ≥ 6 distinct, realistic NPCs purely from `Config/Characters/SK_NPC_*.json` specs sharing the identical 53-bone `SkeletonProfileHumanoid` rig:
  1. `SK_NPC_Sam` (60s crime boss, heavy-set, formal dark suit & tie, receding grey-brown hair)
  2. `SK_NPC_Marco` (30s loyal driver, athletic casual hoodie/polo + jeans)
  3. `SK_NPC_Cartel_A` & `SK_NPC_Cartel_B` (Los Cuervos cartel gunmen — distinct faces, buzz cut / short crop, dark streetwear/tactical accents, goatee/stubble)
  4. `SK_NPC_Cop_LA` (East Hollow / LAPD-inspired patrol officer — navy uniform shirt, duty belt, dark slacks, tactical boots)
  5. `SK_NPC_Civilian_Female` (athletic jogger / street pedestrian — female `hm08` morphs, `skins01` CC0 skin, casual outfit)
  6. `SK_NPC_Civilian_Shopkeeper` (older neighborhood shop owner — distinct age/weight morphs, casual shirt & slacks)
- **Technical requirements**:
  - Budget ≤ 25,000 tris per NPC (`Config/asset_budgets.json` `Characters/SK_NPC`), 1K textures, compact LFS footprint (~4–6 MB per NPC `.glb`).
  - Shared animation library `Assets/Characters/Shared/A_Humanoid_Locomotion.glb` (or verified retargeting of `A_Jason_*` clips onto every NPC skeleton in Godot headless with zero retarget errors!).
  - Full Cycles CPU previews + `uwp` validation PASS + Godot retarget test PASS.

---

## Phase 2 — Hard-Surface Weapon Pipeline & `WPN_Pistol_01` (`T-ART-05`)
- **Goal**: Reusable hard-surface weapon generator + Cycles high-to-low normal/AO/curvature baking pipeline (`Tools/underworld_pipeline/weapons/`), proven on `WPN_Pistol_01` per `Docs/Handoffs/REQ_WPN_Pistol_01.md`.
- **Technical requirements**:
  - Original realistic semi-auto 9mm pistol (~0.19 × 0.13 × 0.03 m, origin at grip, barrel Blender `-Y` → Godot `+Z`).
  - Separate nodes: `Frame`, `Slide` (reciprocating), `Magazine` (detachable/animated), `Trigger`, `Barrel`; sockets `SOCKET_Muzzle`, `SOCKET_Eject`, `SOCKET_Grip`.
  - High-poly bevel/serration/stippling sculpt → Cycles Tangent Normal + AO bake onto ≤ 8,000 tri LOD0 (typically ~3.5–5.5k tris), 1024² PBR metal/polymer maps (CC0 Poly Haven `metal_plate` + polymer grip stipple), single material `M_WPN_Pistol_01`.
  - Auto-generated LOD1/LOD2 + convex pickup collision `UCX_WPN_Pistol_01-convcolonly` via `uwp`.
  - 3 weapon animations (`A_WPN_Pistol_01_Fire` 0.1 s, `A_WPN_Pistol_01_Reload` 1.6 s synced to Jason's reload frames, `A_WPN_Pistol_01_Empty`).
  - Godot headless verification confirming compatibility with Bot 3's `WPN_Pistol_01.tres` & `Tests/test_weapon.gd`.

---

## Phase 3 — Realistic Vehicle Pipeline & `VH_Sedan_01` (`T-ART-04`)
- **Goal**: Reusable automotive hard-surface pipeline (`Tools/underworld_pipeline/vehicles/`) producing an original late-1990s American full-size sedan `VH_Sedan_01` (~5.1 × 1.88 × 1.45 m, zero real brands/badges).
- **Technical requirements**:
  - Clean automotive curvature (subsurf-sculpted fenders, hood, greenhouse, trunk, bumpers, grille, recessed headlights/taillights, mirrors, interior cabin shell, wheel wells).
  - Damage-ready / `VehicleBody3D`-compatible hierarchy:
    - `Body` (chassis) + detachable/damage-ready sub-parts (`Hood`, `Trunk`, `Bumper_F`, `Bumper_R`, `Door_FL`, `Door_FR`, `Door_RL`, `Door_RR` pivoted at hinges!)
    - Separate wheels (`Wheel_FL`, `Wheel_FR`, `Wheel_RL`, `Wheel_RR` with exact origins at wheel centers; manifest documents wheel radius, wheelbase, track width)
    - Sockets: `SOCKET_Seat_Driver`, `SOCKET_Seat_Passenger`, `SOCKET_Exit_Left`, `SOCKET_Exit_Right`, `SOCKET_Headlight_L/R`, `SOCKET_Taillight_L/R`
    - Convex collision `UCX_VH_Sedan_01-convcolonly` (keeping wheel arches clear for `VehicleWheel3D` raycasts!).
  - Budget ≤ 60,000 tris LOD0 (target ~25–42k tris) + LOD1/LOD2 via `uwp`, PBR metallic clearcoat car paint + chrome + glass + rubber tires + interior (CC0 textures + Cycles AO/normal bake).

---

## Phase 4 — Modular LA Street Kit & M01 "Dead Drop" Vertical-Slice Block (`T-ART-03`)
- **Goal**: Reusable modular environment & trim-sheet pipeline (`Tools/underworld_pipeline/environment/`) producing the 2 m-grid East Hollow / "Calloway Avenue" kit + assembled Godot vertical-slice scene `GodotProject/Scenes/Levels/LA_CallowayAve_Block.tscn` supporting Mission M01 ("Dead Drop", `Docs/Missions/M01_DeadDrop.md`).
- **Modular pieces (each ≤ 10k tris, trimesh/convex collision, LOD1/LOD2, CC0 Poly Haven PBR + shared trim sheets)**:
  - **Road & Sidewalk**: `SM_LA_Road_Straight` (10×14 m, 2 lanes + curbs/markings), `SM_LA_Road_Crosswalk`, `SM_LA_Sidewalk_Curb` (10×4 m).
  - **Buildings (original invented signage)**: `SM_LA_Bldg_ShopStucco` (2-storey corner shop "Vega Liquor"), `SM_LA_Bldg_BrickApt` (4-storey East Hollow apartments), `SM_LA_Bldg_GarageM01` (M01 Dead Drop garage with interior shell, workbench, open roll-up door).
  - **Street Furniture & Foliage**: `SM_LA_Streetlight`, `SM_LA_PalmTree` (layered alpha palm fronds + textured trunk), `SM_LA_Hydrant`, `SM_LA_TrashCan`, `SM_LA_Dumpster`, `SM_LA_Fence`, `SM_Prop_PackageCrate` (0.6×0.4×0.4 m M01 package).
  - **Trim Sheets & Decals**: Shared 2K CC0 architectural trim sheet (stucco, brick, concrete curb, metal trim, weathered wood) + asphalt crack/oil/manhole decals.
- **Godot Assembly**: Non-destructive level scene with M01 trigger areas (`Area_GarageArrival`, `Area_GarageInside`, `Area_Warehouse`, `Pickup_Package`), cover positions, streetlights, and parked `VH_Sedan_01` (does NOT modify Bot 3 gameplay scripts).

---

## Phase 5 — Godot Lighting, Look-Dev Presets & Final Pipeline Docs
- **Goal**: Cinematic LA look-dev environment resources in `GodotProject/Assets/Environments/` (zero gameplay-code modifications):
  - `ENV_LA_GoldenHour.tres` (signature M01 warm amber-gold sun, hazy coastal sky, ACES Filmic tonemapping, subtle bloom/SSAO/volumetric fog, warm film color grading)
  - `ENV_LA_Midday.tres` (crisp California coastal daylight, high sun, punchy shadows)
  - `ENV_LA_Night.tres` (deep Pacific twilight/night sky, sodium-vapor street contrast, moody cool shadows)
- **Look-Dev Test Scene**: `GodotProject/Scenes/LookDev/LA_LookDev_Showcase.tscn` loading the presets + `SK_Jason`, `WPN_Pistol_01`, `VH_Sedan_01`, and street block; verified headless in Godot 4.7.2.
- **Final Docs & Budgets**: Complete `Docs/PIPELINE_WEAPONS.md`, `Docs/PIPELINE_VEHICLES.md`, `Docs/PIPELINE_ENVIRONMENT.md`, `Docs/PIPELINE_LOOKDEV.md`, updated `Config/asset_budgets.json`, and complete `Docs/ASSET_LICENSES.md`.
