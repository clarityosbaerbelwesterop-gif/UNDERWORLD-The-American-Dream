# UNDERWORLD – THE AMERICAN DREAM · Handoff to Claude Code

> **You are Claude Code.** You take over this game from three AI agents ("Bot 1" Project Director,
> "Bot 2" 3D Designer, "Bot 3" Game Developer) who built it on one shared Linux box on 2026-11-22.
> This file is self-contained: read it fully, then `CLAUDE.md`, `Docs/TASK_BOARD.md`,
> `Docs/QUALITY_GATE.md`, `Docs/PROJECT_STATUS.md`. Your job: carry the project to release
> under the standards below. Every fact here was checked against the repo at `main` on
> 2026-11-22 (Europe/Berlin); if the repo disagrees with this file, the repo wins – fix this file.

- Repo: https://github.com/clarityosbaerbelwesterop-gif/UNDERWORLD-The-American-Dream (private)
- Written by: Bot 1 (Project Director), branch `bot1/claude-handoff`
- Snapshot: `main` = `b2acced` (PR #12 merge) before this PR; merge gate `Tests/run_all.sh` = **RUN_ALL: PASS** on fresh worktrees (PR #12 head `a28331c` and this branch).
- **Status update 2026-11-23 (Bot 1):** PR #14 (T-MIS-01, Claude Code) merged as `c63198a`; fixes PR #15 (LFS, `6f149e5`) and PR #16 (real mission sabotage). Gate now **589 checks** (smoke 12, uwp tool 58, import 71, AI 80, mission 75, player 137, vehicle 88, weapon 68). M01 core + greybox level + HUD v0 exist; Marco ally, wave sequencing and a real drive are open (TASK_BOARD T-MIS-01). Next work order: `Docs/Prompts/CLAUDE_CODE_PROMPT_02.md`. Where §0/§4/§8 below say "mission/level/HUD not started", this line wins.

---

## 0. TL;DR

| | |
|---|---|
| Game | Original open-world third-person crime shooter (GTA IV/V/VI quality bar, 100 % original IP). Protagonist **Jason**. Ch.1 Los Angeles (linear, cinematic), Ch.2 New York (open world). |
| Engine | **Godot 4.7.2** (GDScript, Forward Plus project) – not Unreal (TD-001). |
| Art | **Blender 5.2.4 LTS headless `bpy`** → `Tools/uwp` → glTF `.glb` → Godot. Git LFS for binaries. |
| State | Milestone 1 "LA Vertical Slice" **in progress**. Gameplay systems (controller with Jason v2 as the visible player, pistol + bloom, enemy/civilian AI, vehicle physics) are in `main` and tested headless. Art exists as first passes/blockouts. **No asset is PRODUCTION-READY**: all 5 reviewed hero assets were **REJECT**ed by the quality gate. Mission logic (M01) and the HUD exist and are tested headless; a Linux build exports and boots headless (`Docs/BUILD.md`), but it was never played on a GPU box; no audio. |
| Tests | `Tests/run_all.sh` → 12 smoke + 58 uwp tool + 71 asset-import + 102 AI + 40 HUD + 23 level + 105 mission + 171 player + 88 vehicle + 68 weapon checks = **738 checks, all PASS** (2026-11-22). |
| Open at handoff | Draft PR **#11** (Bot 2, pistol quality pass, WIP, untested – do not merge as is). Everything else is merged; both bots stopped. |
| Owner | **Bärbel Westerop** (ClarityCompassAI). Report to her **in German**, honestly. |

---

## 1. Project vision

### 1.1 Pitch & pillars (`Docs/GAME_DESIGN.md` v0.1)
Original open-world third-person crime game; cinematic, realistic; inspired by the *quality bar* of modern
open-world crime games, with **100 % original** characters, story, assets, brands and locations. Real cities
appear only as **fictionalised districts** – no copied maps, logos, brands or assets from any existing game.

Pillars:
1. **Weight** – physical movement and gunplay: momentum, recoil, cover, consequences.
2. **Cinema** – Chapter 1 is a tightly paced crime film; camera, lighting and dialogue sell it.
3. **The American Dream, inverted** – Jason builds an empire from €5,000 and learns what it costs.
4. **Living streets** – NPCs, traffic and police react believably.

### 1.2 Cast (working names; owner decisions open → `Docs/BLOCKERS.md` B-004)
| Name | Role |
|---|---|
| **Jason** (surname open) | Protagonist, smuggler/exporter. Calm, observant, dry humour. |
| **Sam** | Jason's employer, head of a small LA crime family; 60s, heavy-set, expensive suits; secretly sells Jason to the FBI (reveal late Ch.2). |
| **Marco Ruiz** | Jason's talkative, loyal driver/colleague in Ch.1; partner in M01. |
| **Los Cuervos** | Cartel #1 (crow iconography, original); murder the delivery crew in M01. |
| **La Hermandad del Sur** | Cartel #2, works with Sam in Ch.2; kidnaps and tries to recruit Jason. |
| **Kings of Flatbush** (working title) | Brooklyn gang that produces for Jason (80/20 split). |
| FBI Special Agent **Dana Whitlock** | Federal pursuer; leads the warehouse raid. |

### 1.3 Story outline
**Chapter 1 – Los Angeles (linear, cinematic)**
1. Arrival – Jason flies in from Colombia; Sam receives him at a private hangar.
2. The Route – deliveries across LA and up into the Emerald Triangle.
3. **Dead Drop (M01, vertical slice)** – a delivery failed; Jason and Marco find the crew murdered by Los Cuervos at a garage on Calloway Avenue; shootout; Jason secures the package and drives it to the warehouse.
4. The Raid – the FBI storms the warehouse; Jason escapes badly wounded.
5. Wings – Jason steals a small aircraft and flees to New York.

**Chapter 2 – New York (open world)**
6. Arrival with ~€5,000; cheap room; taxi-driver side activity. 7. Brooklyn networks; stealing/selling cocaine.
8. A local gang produces for Jason (80/20). 9. Crew → bank heist; two crew die; Jason wanted.
10. Hiding on a farm; Los Cuervos burn it down. 11. Revenge: rival supplies, cartel operation, huge shipment.
12. Kidnapped by La Hermandad (with Sam); refuses. 13. Gold-depot heist playing both cartels. 14. Reveal: Sam sold Jason to the FBI.
15. Jason destroys both cartels and confronts Sam. 16. Epilogue – family. **FOUR YEARS LATER.**

### 1.4 World (long term)
- **LA (fictionalised):** East Hollow (Hollywood-inspired), Crestmont Hills (Beverly Hills-inspired), Downtown, Seaview beaches, airport, San Ardo mountains, freeways, Harbor industrial, rural north incl. an Emerald-Triangle-inspired region.
- **NY (fictionalised):** Manhattan, Brooklyn, Queens, Bronx, Staten Island, a Central-Park-inspired park, subways, bridges, warehouses.

### 1.5 Mission M01 "Dead Drop" (`Docs/Missions/M01_DeadDrop.md`, status READY FOR REVIEW)
Calloway Avenue, East Hollow, golden hour, 10–15 min.
| # | HUD objective | Completion |
|---|---|---|
| 0 | (intro) phone call from Sam | 20 s dialogue + subtitles, player controllable |
| 1 | "Get in the car." | enter `VH_Sedan_01` (Marco already passenger) |
| 2 | "Drive to the garage on Calloway Ave." | car stops in `Area_GarageArrival` (r 8 m), ~300 m loop, civilians |
| 3 | "Check the garage." | enter `Area_GarageInside`; 3 dead crew, crate on bench |
| 4 | "Survive the ambush." | 2 waves: 3 gunmen street, then 2 van/rooftop; Marco invulnerable ally, low accuracy |
| 5 | "Grab the package." | interact `Pickup_Package`; no sprint while carrying; checkpoint |
| 6 | "Deliver the package to the warehouse." | car + package in `Area_Warehouse`; optional chase car with 2 gunmen |
| 7 | "MISSION PASSED" + $2,500 | end card |
Fail → restart at last checkpoint (start or after step 5): Jason dies; package destroyed (200 HP once loaded) or > 60 m behind; sedan destroyed before step 6 ends. Marco unkillable in M1.
Implementation contract: mission as data (`Resource` with ordered objectives: type, target node path, text, checkpoint flag); `Area3D`s named exactly as above in `LA_CallowayAve.tscn`; debug API `MissionManager.debug_complete_current()` for headless tests.

Vertical-slice scope (GDD §5): one ~120 m street with 2 blocks (shops, apartments, garage, palms, streetlights), Jason playable, sedan, pistol (hitscan, recoil, reload, **12-round mag**), ≥ 2 civilians + ≥ 3 cartel gunmen, M01, Linux x86_64 build.
Controls (KB/M · gamepad): WASD/LS move · Shift/L3 sprint · C/B crouch · RMB/LT aim · LMB/RT fire · R/X reload · F/Y enter/exit vehicle · E/Y interact (TD-010 c) · Space/A jump.

### 1.6 Art direction (`Docs/GAME_DESIGN.md` §6, `Docs/ArtDirection/`)
- Photographic realism, slightly desaturated film look. LA = warm sodium/golden-hour palette, haze, long shadows. NY = cold blues, wet asphalt, steam.
- PBR, worn and lived-in (dirt, decals, cracks), no pristine surfaces. American 1960s–2000s architecture (stucco, brick, neon with **invented** names, e.g. "Vega Liquor", "Sunny Days Motel"). Generic original late-90s American cars, no real badges. Realistic proportions, no stylisation.
- **Jason (binding concept v01, `Docs/ArtDirection/Concepts/`):** Latino-American, **early 30s**, **1.82 m**, athletic-lean, skin-fade haircut, short groomed beard, scar over the **left** eyebrow. Outfit: worn dark-brown leather bomber (ribbed cuffs/hem), grey crew T-shirt, dark indigo jeans, brown leather laced work boots, wristwatch on the left wrist. Files: `CA_Jason_Turnaround_v01.jpg` (binding proportions/outfit), `CA_Jason_Head_v01.jpg` (binding face/hair/beard/scar), `CA_Jason_KeyArt_LA_v01.jpg` (mood only; dual pistols are **not** canon – one pistol, proper grip).
- ⚠ Inconsistency to fix: `GAME_DESIGN.md` §2 still says Jason is "late 30s" with a "grey henley"; the binding art direction (`ArtDirection/README.md`) says **early 30s**, grey crew T-shirt. Art direction wins; update the GDD row (task T-DOC-01 in §9).

---

## 2. Owner & reporting

- Owner: **Bärbel Westerop**, ClarityCompassAI. She writes in German and expects answers **in German**.
- Report honestly and concretely: what was done, how it was verified (command + result), what is still open. Use plain language, show renders/screenshots for art.
- **Never fake completion.** Never say "fertig", "AAA", "production-ready" or "getestet" without the evidence (test log, renders, review sheet, in-engine capture). If something failed or is unverified (e.g. no GPU), say so.
- Times in Europe/Berlin.
- Irreversible/external actions (purchases, paid services, publishing, store submissions, LFS data packs, changing repo visibility) need her explicit OK first.

---

## 3. Tech stack, setup and conventions

### 3.1 Why this stack
- **TD-001 Godot 4.7.2 instead of UE5:** the box has 8 CPU, 15 GB RAM, **no GPU**, limited disk (`/workspace` 125 GB volume, ~11 GB free at handoff). UE5 needs 100+ GB + a GPU editor. Owner allowed an open engine. Godot is MIT, ~140 MB, fully headless (import, scripts, physics, tests, export), native glTF, `CharacterBody3D`, `VehicleBody3D`, `NavigationAgent3D`, `AnimationTree`, `SkeletonProfileHumanoid`.
- **TD-002 Blender headless:** all asset generation/validation/export is reproducible Python (`bpy`). No Blender MCP (B-001).
- **TD-003 glTF 2.0 binary (`.glb`)** is the interchange source of truth (`export_yup=True, export_apply=True`).
- **Git LFS** for `.blend .glb .gltf .fbx .png .jpg .jpeg .exr` (+ audio/fonts per `.gitattributes`).

### 3.2 Exact binaries (current box, `/workspace/tools/README.md`)
| Tool | Version | Path |
|---|---|---|
| Blender | 5.2.4 LTS (hash cd5dc428cce1) | `/workspace/tools/blender/blender` → `/workspace/tools/blender-5.2.4-linux-x64/blender` |
| Godot (standard, GDScript) | 4.7.2.stable.official.ed1daf0bf | `/workspace/tools/godot` → `/workspace/tools/godot-4.7.2/Godot_v4.7.2-stable_linux.x86_64` |
| git-lfs | 3.8.1 | `/usr/local/bin/git-lfs` → `/workspace/tools/git-lfs/git-lfs` |
| Python 3 + Pillow + numpy | system | used by `Tools/uwp review-sheet` and skills |
| xvfb-run + Mesa llvmpipe | system | Phase 8 in-engine captures |
Not installed: Godot export templates (needed for T-BUILD-01), Godot .NET, Unreal.

### 3.3 Fresh-machine setup (Linux x86_64)
```bash
# 1. Tools (verify checksums from the official release pages before extracting)
mkdir -p /workspace/tools && cd /workspace/tools
# Blender 5.2.4 LTS  – https://download.blender.org/release/Blender5.2/blender-5.2.4-linux-x64.tar.xz
tar xf blender-5.2.4-linux-x64.tar.xz && ln -sfn blender-5.2.4-linux-x64 blender
# Godot 4.7.2 stable – https://github.com/godotengine/godot/releases/tag/4.7.2-stable (Godot_v4.7.2-stable_linux.x86_64.zip)
mkdir -p godot-4.7.2 && unzip -d godot-4.7.2 Godot_v4.7.2-stable_linux.x86_64.zip
ln -sfn godot-4.7.2/Godot_v4.7.2-stable_linux.x86_64 godot
# git-lfs 3.8.1 (or distro package), Phase-8 capture deps
sudo apt-get install -y git-lfs xvfb mesa-utils libgl1-mesa-dri python3-pil python3-numpy
# 2. Repo
git clone https://github.com/clarityosbaerbelwesterop-gif/UNDERWORLD-The-American-Dream.git /workspace/UNDERWORLD
cd /workspace/UNDERWORLD && git lfs install && git lfs pull
# 3. CC0 source cache for the character pipeline (gitignored, .cache/uwp_sources/)
python3 Tools/underworld_pipeline/fetch_sources.py --groups characters,textures,mocap
# 4. Verify
/workspace/tools/blender/blender -b --factory-startup --version
/workspace/tools/godot --headless --version
/workspace/tools/godot --headless --path GodotProject --import
./Tests/run_all.sh            # must end with RUN_ALL: PASS
```
Scripts honour `BLENDER=` and `GODOT=` env vars (`Tools/uwp`, `Tools/godot_phase8_capture.sh`); other scripts hard-code `/workspace/tools/...` – keep that path or symlink it.
Godot export templates (T-BUILD-01): the full `.tpz` is ~1 GB; extract **only** `linux_release.x86_64` / `linux_debug.x86_64` into `~/.local/share/godot/export_templates/4.7.2.stable/`.

### 3.4 Repo layout
```
Docs/          design + production docs (task board, status, logs, decisions, blockers, reviews)
Config/        asset_budgets.json, Characters/*.json (7 specs), Weapons/, Vehicles/
Blender/       Source/<Category>/<Asset>/<Asset>.blend, Scripts/ (asset-specific bpy, e.g. sk_jason/verify_sk_jason.sh)
Tools/         uwp (wrapper), underworld_pipeline/ (python package), blender_export.py (smoke), godot_phase8_capture.sh
Assets/        exported .glb + .import sidecars + manifests + previews (GodotProject/Assets -> ../Assets symlink, TD-006)
GodotProject/  project.godot, Scenes/, Scripts/{player,combat,ai,vehicle,import,tools}, Data/{AI,Weapons,Vehicles}, Tests/
Tests/         run_all.sh (merge gate), run_pipeline_smoke.sh, run_asset_import_tests.sh, run_gameplay_tests.sh, logs/
Source/        GDExtension C++ (empty)      Builds/  build output (gitignored)
```

### 3.5 Technical decisions (full text in `Docs/TECHNICAL_DECISIONS.md`)
| TD | Decision |
|---|---|
| TD-001 | Godot 4.7.2 (GDScript; C++ GDExtension in `Source/` only for hot paths). Rendering validated later on a GPU machine. |
| TD-002 | Blender 5.2.4 headless: `-b --factory-startup --python-exit-code 1`. |
| TD-003 | glTF 2.0 `.glb`; FBX optional; animations inside the character glb or shared `A_*.glb` libraries on the same skeleton. |
| TD-004 | 1 BU = 1 m = 1 Godot unit. Blender +Z up → Godot +Y. Model faces **Blender −Y → Godot +Z** (`Vector3.MODEL_FRONT`). Origins: props/buildings bottom-centre, characters at the feet, vehicles at ground-contact centre, weapons at the grip. Transforms applied. |
| TD-005 | Prefixes `SK_ SM_ A_ M_ T_(_D/_N/_ORM) VH_ WPN_ PT_ UCX_`; PascalCase parts with `_`, ASCII; LOD suffix `_LOD0/1/2`; Godot hints `-colonly -convcolonly -col -noimp`; sockets = empties `SOCKET_<Name>`; scripts `snake_case.gd`, scenes `PascalCase.tscn`. **Addendum: no action name may end in `_Loop`/`-Loop`/`_Cycle`/`-Cycle` (any case)** – Godot strips them and forces looping. Loop mode comes only from the uwp manifest. uwp error `NAME_ACTION_LOOP`. (`A_Jason_Jump_Loop` → `A_Jason_Jump_Air`.) |
| TD-006 | `Blender/Source/<Cat>/<Asset>/<Asset>.blend` → `Assets/<Cat>/<Asset>/<Asset>.glb` (+ `.manifest.json`). Categories `Characters, Vehicles, Weapons, Environment/LA, Environment/NY, Props, Test`. `.import` sidecars are committed. |
| TD-007 | File ownership per bot (Docs/Config = director; Blender/Tools/Assets = art; GodotProject/Source/Tests/Builds = gameplay). As the single successor you own everything, but keep the **separation of concerns** and the review roles of the quality gate. |
| TD-008 | `main` always green; one worktree per agent/branch; merge by PR only; never force-push `main`. |
| TD-009 | Budgets: Jason ≤ 40k tris, NPC ≤ 25k, car LOD0 ≤ 60k, pistol ≤ 8k, street module ≤ 10k; textures 2048² hero / 1024² default; 60 fps mid-range GPU target. Machine-readable: `Config/asset_budgets.json` (also `max_bone_influences` 4, `max_materials` default 8 / Characters 10 / Vehicles 12, texel density hero ≥ 256 px/m, default ≥ 128, Props 5k, Test 1k). |
| TD-010 | **Physics layers** 1 `World`, 2 `Player`, 3 `Characters`, 4 `Vehicles`, 5 `Hitboxes`; player collides 1\|3\|4, camera spring arm 1\|4, aim ray 1\|3\|4\|5. **Input map source of truth `GodotProject/Scripts/tools/setup_input_map.gd`** (rewrites `[input]` + `[layer_names]` of `project.godot`; never hand-edit those sections). Gamepad A = jump; Y = interact **and** enter_vehicle; keyboard E / F. Gameplay tests `GodotProject/Tests/test_*.gd` at `--fixed-fps 60`; `Tests/run_all.sh` = merge gate (`RUN_ALL: PASS`). |
| TD-011 | Player body = `CylinderShape3D` r 0.35, h 1.8 (1.2 crouched), origin at feet; step-up 0.35 m + floor snap 0.4 m. Capsules bounce on stair nosings (measured). NPCs use the same shape. |
| TD-012 | **Still PROPOSED** (Bot 2, `Docs/Handoffs/2026-11-22_T-PIPE-01.md`): move `lods`, `collision`, `max_materials`, `hero_categories` from `Tools/underworld_pipeline/defaults.json` into `Config/asset_budgets.json` (tool already reads from there first). Decide and apply (task T-PIPE-05). |
| TD-013 | NPC AI: one `NPCController`; archetype = `AIProfile` .tres in `Data/AI/` with a transition table + tuning; LOS raycasts vs World\|Vehicles; noise via `AIPerception.emit_noise` to group `ai_hearing`; weapons emit gunshots with `WeaponData.noise_radius` (pistol **40 m**); navmesh baked headless (cell 0.25, agent r 0.5 / h 2.0 / climb 0.25); `HumanoidHitboxes` (Head/Body/Legs/Arm_L/Arm_R) on layer 5 for all humanoids. |
| TD-014 | Vehicles = Godot `VehicleBody3D` + `VehicleWheel3D`, assembled **at runtime** from the `VH_*.glb` by node name (`Scripts/vehicle/vehicle.gd`, `VehicleData` .tres in `Data/Vehicles/`, scene `Scenes/Vehicles/VH_Sedan_01.tscn`). Static-sag and wheel-draw quirks of 4.7.2 are compensated and tested. Car on layer 4. Enter/exit via `SOCKET_Seat_Driver` / `SOCKET_Exit_Left/Right`; player collision restored two physics frames after exit. Inputs `vehicle_accelerate` (W/RT), `vehicle_brake` (S/LT), `vehicle_handbrake` (Space/RB). All tuning `[DEFAULT]`. |
Next free TD number: **TD-015** (TD-012 stays reserved for the LOD proposal).

### 3.6 Godot project facts
- `project.godot`: features `4.7`, **Forward Plus**; main scene `res://Scenes/Main.tscn`; `[importer_defaults]` scene import script `res://Scripts/import/uw_post_import.gd` (LOD visibility ranges 0–15 / 15–40 / 40–100 m + loop modes from manifest).
- `Scripts/import/uw_lod_post_import.gd` is a **byte-identical mirror** of `Tools/underworld_pipeline/godot/uw_lod_post_import.gd`; the asset-import test fails on drift. If you change one, copy it to the other in the same PR.
- Scenes: `Player/Player.tscn`, `Weapons/PT_Pistol.tscn`, `NPC/PT_NPC_Gunman.tscn`, `NPC/PT_NPC_Civilian.tscn`, `Vehicles/VH_Sedan_01.tscn`, `Levels/LA_CallowayAve_Block.tscn` (greybox, no gameplay), `LookDev/LA_LookDev_Showcase.tscn`, test ranges `Test/PT_PlayerTestRange.tscn`, `Test/PT_AITestRange.tscn`, `Test/PT_TargetDummy.tscn`.
- Data: `Data/Weapons/WPN_Pistol_01.tres`, `Data/AI/AI_Gunman_Cartel.tres`, `Data/AI/AI_Civilian.tres`, `Data/Vehicles/VH_Sedan_01.tres`. Look-dev environments `Assets/Environments/ENV_LA_{GoldenHour,Midday,Night}.tres`.
- Generators: `Scripts/tools/setup_input_map.gd`, `build_test_range.gd`, `build_npc_scenes.gd`.

### 3.7 Commands you will use
```bash
# Merge gate (run on a fresh worktree before every merge)
./Tests/run_all.sh                                   # → RUN_ALL: PASS
./Tests/run_pipeline_smoke.sh | run_asset_import_tests.sh | run_gameplay_tests.sh
# Asset pipeline (Tools/uwp wraps Blender headless; exit 0 PASS, 1 validation, 2 export, 3 verify, 4 usage, 5 internal)
Tools/uwp validate <file.blend>            Tools/uwp export <file.blend> [--no-lod] [--no-collision]
Tools/uwp validate-all | export-all
Tools/uwp build-character Config/Characters/SK_NPC_Marco.json [--no-bake]
Tools/uwp build-shared-anims               # Assets/Characters/Shared/A_Humanoid_Locomotion.glb
Tools/uwp build-weapon Config/Weapons/WPN_Pistol_01.json
Tools/uwp build-vehicle Config/Vehicles/VH_Sedan_01.json
Tools/uwp build-env [--only <Piece>]       # LA kit sources
Tools/uwp retarget <char.blend> <clip.bvh> --action-name A_... [--cyclic]
Tools/uwp review-sheet <asset> [--ref ..] [--renders ..] [--out ..]   # Pillow, no Blender
Tools/uwp --help ; Tools/uwp <cmd> --help  # check exact flags before use
Blender/Scripts/sk_jason/verify_sk_jason.sh
# Godot
/workspace/tools/godot --headless --path GodotProject --import
/workspace/tools/godot --headless --fixed-fps 60 --path GodotProject --script res://Tests/test_vehicle.gd
/workspace/tools/godot --headless --path GodotProject --script res://Scripts/tools/setup_input_map.gd
# Phase 8 in-engine capture (software GL)
Tools/godot_phase8_capture.sh --scene res://Scenes/LookDev/LA_LookDev_Showcase.tscn --out Docs/Reviews/sheets/<asset>_phase8.png
```

---

## 4. Everything built so far (2026-11-22)

### 4.1 Pull requests
| PR | Branch | Task | Delivered | State |
|---|---|---|---|---|
| #1 | `bot3/dev` | T-GP-01 / T-GP-01c | Third-person `CharacterBody3D` controller (walk 1.4 / run 3.5 / sprint 6.0 m/s, crouch, jump, slopes, step-up 0.35 m), `SpringArm3D` orbit camera with collision, over-shoulder aim (arm 3.2→1.3 m, FOV 70→55), shoulder swap, KB/M + gamepad input map, AnimationTree locomotion, cylinder collision (TD-011). Test range `PT_PlayerTestRange`. | merged `f81144a` |
| #2 | `bot3/t-pipe-02` | T-PIPE-02 | Project-wide Godot scene import preset `uw_post_import.gd` (LOD visibility ranges + loop modes from manifest), asset-import tests, `run_all.sh` wiring. | merged `d9470d8` |
| #3 | `bot3/t-gp-02` | T-GP-02 | Data-driven pistol (`WeaponData` .tres), hitscan, recoil, spread, reload, damage, `TargetDummy`, `PT_Pistol` stand-in, REQ-GP02-PISTOL. | merged `b0c3595` |
| #4 | `bot3/t-gp-02a` | T-GP-02a | Rapid-fire bloom: +0.8°/shot up to 4°, recovery after 0.35 s, aimed = half build-up (all `[DEFAULT]`). | merged `9cf6baf` |
| #5 | `bot2/dev` | T-ART-01/02 | SK_Jason **v1** (procedural, 26,188 tris, 21 actions) + TD-005 `_Loop` addendum. Carried into #7; v1 superseded. | merged `12a628e` |
| #6 | `bot3/t-ai-01` | T-AI-01 | Enemy AI + ambient civilians: data-driven FSM (TD-013), 120° view cone to 35 m, LOS, hearing, cover-lite with peek-and-shoot, AI shooting with aim error, humanoid hitboxes (NPC + player), headless navmesh, 3 fleeing civilians. Deterministic over 3 runs. | merged `ea52f0c` |
| #7 | `cursor/character-pipeline-sk-jason-v2-6fae` | T-PIPE-03 | Realistic spec-driven character pipeline on the CC0 MakeHuman/MPFB2 `hm08` base + **SK_Jason v2**, uwp quality checks (`WEIGHT_UNNORMALIZED`, `UV_OVERLAP`, `TEXEL_DENSITY`, `MESH_CLIPPING`, multi-view Cycles previews, silhouette check). Built by a cloud agent; merge-gate fixes by Bot 1. | merged `d236bef` |
| #8 | `pipe/t-pipe-04-recovered` | T-PIPE-04 | Recovered whole-game pipeline v0 (cloud agent never pushed it; Bot 1 re-ran every generator on the box): `uwp build-character/build-shared-anims/build-weapon/build-vehicle/build-env/retarget`, SK_NPC_Sam, A_Humanoid_Locomotion (21 clips), WPN_Pistol_01, VH_Sedan_01, 6 LA kit pieces + crate, `ENV_LA_*` look-dev presets, `LA_CallowayAve_Block.tscn` greybox, `LA_LookDev_Showcase.tscn`, 6 NPC specs. | merged `038de21` |
| #9 | `bot3/t-gp-03` | T-GP-03 | Vehicle physics on the real `VH_Sedan_01` (TD-014): runtime assembly from the glb, enter/exit via sockets, chase camera, crash damage, driving input, 88 vehicle checks, REQ_VEH_Sedan_01 CONFIRMED with CR-1..4. | merged `bb677b6` |
| #10 | `bot1/quality-gate` | T-QA-02 | Binding `Docs/QUALITY_GATE.md`, review template, first honest reviews of 5 assets (all REJECT) + reference-compare sheets, `Tools/uwp review-sheet`, `Tools/godot_phase8_capture.sh`. | merged `5f53cab` |
| #11 | `bot2/dev` | T-ART-05 (pistol; PR title says T-ART-03, see §8) | WIP pistol quality pass – **draft, untested** (see §8.1). | **OPEN (draft)** |
| #12 | `bot3/t-gp-01c-jason` | T-GP-01c (Jason swap) | Player visual capsule → **SK_Jason v2**: `Visual.model_scene` = SK_Jason.glb, `CLIP_NAMES` uses `A_Jason_Jump_Air`, `validate_clips()` (missing / `_Loop`), AnimationTree rebuilt on model swap, pistol auto-attached to `SOCKET_RightHand_Weapon`; player test +25 checks (137), sabotage `UW_JASON_SABOTAGE=1` → 3 FAIL. | merged `b2acced` (reviewed by Bot 1: no Assets/Blender/Tools changes, fresh-worktree RUN_ALL PASS) |
| (this) | `bot1/claude-handoff` | T-DOC-00 | This handoff, `CLAUDE.md`, `Docs/SKILLS_AND_TOOLS.md`, TASK_BOARD reconciliation. | – |

### 4.2 Gameplay systems in `main` (GodotProject/)
- **Player** `Scripts/player/{player_controller,camera_rig,character_visual}.gd`, `Scenes/Player/Player.tscn`.
- **Combat** `Scripts/combat/{weapon,weapon_data,player_weapon_controller,hitbox,humanoid_hitboxes,damage_receiver,damage_info,target_dummy}.gd`; pistol data `Data/Weapons/WPN_Pistol_01.tres` (12-round mag, noise_radius 40 m) points at the real `WPN_Pistol_01.glb`.
- **AI** `Scripts/ai/{npc_controller,ai_profile,ai_state_machine,ai_perception,cover_point,npc_route}.gd`; profiles `AI_Gunman_Cartel.tres`, `AI_Civilian.tres`; PT NPC scenes.
- **Vehicle** `Scripts/vehicle/{vehicle,vehicle_data}.gd`, `Scenes/Vehicles/VH_Sedan_01.tscn`.
- **Import** `Scripts/import/{uw_post_import,uw_lod_post_import}.gd`.

### 4.3 Asset pipeline (Tools/underworld_pipeline, "uwp")
- `cli.py` subcommands: `validate`, `export`, `validate-all`, `export-all`, `build-character`, `build-shared-anims`, `build-weapon`, `build-vehicle`, `build-env`, `retarget`; `review-sheet` runs in system Python (`review_sheet.py`).
- `validate.py`: naming (TD-005 incl. `NAME_ACTION_LOOP`), applied transforms, UVs/overlap, texel density, materials, tri budgets (`Config/asset_budgets.json`), non-manifold/degenerate, ≤ 4 influences, weight normalisation, 22 mandatory humanoid bones, origin/height/front (TD-004), layered clothing clipping, sockets.
- `exporter.py`: LOD1/LOD2 (Decimate, glTF extras `uw_lod`, `uw_visibility_range`), collision (`UCX_` + Godot hints), `.glb` + round-trip verify, `.manifest.json`, `.validation.json`, Cycles-CPU previews.
- `characters/` (`build_character.py`, `mh_loader.py` clean-room CC0 reader – **no GPLv3 MPFB2 code**, `clothing.py`, `hair_beard.py`, `pbr_textures.py`, `retarget.py`, `animations.py`, `build_shared_anims.py`), `weapons/`, `vehicles/`, `environment/`, `silhouette_check.py`, `fetch_sources.py` (CC0 downloads into gitignored `.cache/uwp_sources/`), `godot/uw_lod_post_import.gd`, `tests/run_tests.sh`.
- Specs: `Config/Characters/SK_Jason.json`, `SK_NPC_{Sam,Marco,Cartel_A,Cartel_B,Cop_LA,Civilian_Female}.json`; `Config/Weapons/WPN_Pistol_01.json`; `Config/Vehicles/VH_Sedan_01.json`.
- Character contract: 53-bone `SkeletonProfileHumanoid` skeleton (`Root` + 22 humanoid + 30 finger bones), `SOCKET_RightHand_Weapon` on `RightHand` (+Y up, +Z barrel), 20 ARKit/viseme blendshapes, 30 fps in-place clips, loop flags in the manifest. Clip list for Jason: `Docs/Handoffs/REQ_SK_Jason_Controller.md` (REQ-GP01-JASON).
- Pipeline docs: `Docs/PIPELINE_{CHARACTERS,WEAPONS,VEHICLES,ENVIRONMENT,LOOKDEV,ROADMAP}.md`.

### 4.4 Assets in `main` (`Docs/ASSET_REGISTRY.md`) – all status **WIP**
| Asset | Tris | Key data |
|---|---|---|
| `SK_Jason` v2 | 35,789 / 40k | 1.83 m incl. soles, 12 meshes, 10 PBR mats (2K skin + SSS), 20 blendshapes, 53 bones, 21 `A_Jason_*` clips (max foot slide 4.86 cm), silhouette IoU front 0.813 / side 0.700 / mean 0.756 vs concept, glb ~10.7 MB |
| `SK_NPC_Sam` | 23,735 / 25k | 1.79 m, Jason skeleton, 16 clips, 8 mats, hair shell |
| `A_Humanoid_Locomotion` | – | shared 53-bone armature + 21 `A_Humanoid_*` clips (incl. car enter/exit, carry, death) |
| `WPN_Pistol_01` | 1,920 / 8k | Frame/Slide/Barrel/Magazine/Trigger, `SOCKET_Muzzle` +Z 0.165 m, Eject, Grip, clips Fire / Reload 1.6 s / Empty |
| `VH_Sedan_01` | 3,382 / 60k | 4.86 × 2.02 × 1.46 m, Body/Cabin/Hood/Trunk/Bumpers, 4 hinged doors, wheels r 0.34 m, wheelbase 2.86, track 1.58, seat/exit/light sockets, convex UCX |
| `SM_LA_Road_Straight` 60, `SM_LA_Sidewalk_Curb` 44, `SM_LA_Bldg_ShopStucco` 240, `SM_LA_Bldg_GarageM01` 168 (`SOCKET_PackageBench`), `SM_LA_Streetlight` 180, `SM_LA_PalmTree` 616 | | 10×14 m road, 4×10 m sidewalk, LOD0–2 + collision via uwp |
| `SM_Prop_PackageCrate` | 176 | 0.61 × 0.41 × 0.41 m, M01 pickup |
| `PT_PipelineTest_Crate` | 170 | placeholder, never ships |
Scenes: `LA_CallowayAve_Block.tscn` (greybox block, no gameplay), `LA_LookDev_Showcase.tscn`; environments `ENV_LA_GoldenHour/Midday/Night.tres` (look never verified on a GPU).

### 4.5 Numbers
- Tests (`Tests/run_all.sh`, fresh worktree of `bb677b6`, before PR #12): smoke 12, uwp tool 48, asset import 61, AI 80, player 112, vehicle 88, weapon 68 → **469 checks PASS**. After PR #12 (`b2acced`): player 137 → **494 checks PASS** (fresh worktree of `a28331c`, which already contained `bb677b6`).
- Git LFS: 58 objects / **~63 MB** at HEAD, **~73 MB** across all history (74 objects) – of GitHub Free's ~1 GB storage + ~1 GB/month bandwidth (B-005). Each realistic NPC adds ~10 MB; budget every hero asset.
- Disk on the box: `/workspace` ~11 GB free.

---

## 5. Standards (binding)

### 5.1 AAA Quality Gate (`Docs/QUALITY_GATE.md` – read it in full)
A successful script or a finished model is **not** a production asset. Never accept a mediocre first pass. Never call anything "AAA" because it was generated.
1. **Reference-first.** Before modelling an important asset: research references, fit the single UNDERWORLD look, define real dimensions in metres, define target quality and must-have details, create a **reference board** at `Docs/ArtDirection/References/<asset>/` with `SOURCES.md` (every image + origin + license; CC0 / CC-BY / original concept only). Only `SK_Jason` has a board in `main`; PR #11 adds one for the pistol. **Sam, sedan and LA kit have none → they cannot pass.**
2. **Eight phases:** 1 Blockout · 2 High-quality modelling · 3 PBR materials · 4 Lighting & multi-angle renders (headless Blender **Cycles CPU**; Workbench is not evidence) · 5 Independent visual review against references · 6 Refinement (fix, re-render, re-review until pass) · 7 Game-ready validation (`Tools/uwp validate/export` PASS: geometry, UVs, topology, materials, LODs, collision, skeleton, naming, budgets) · 8 **Godot integration** under gameplay lighting and camera (replaces Unreal).
3. **Phase 8 capture on a no-GPU box:** Forward Plus (Vulkan) cannot be captured (no lavapipe ICD). Software OpenGL works (proven 2026-11-22, Mesa llvmpipe, OpenGL 4.5):
   ```bash
   LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe xvfb-run -a -s "-screen 0 1920x1080x24" \
     /workspace/tools/godot --path GodotProject --display-driver x11 \
     --rendering-driver opengl3 --rendering-method gl_compatibility res://<scene>
   ```
   Helper `Tools/godot_phase8_capture.sh [--scene res://…] [--script res://…] [--out …png]` (the scene or `--script` must save the viewport PNG). Lighting ≠ shipping Forward Plus – say so on the review; use it for scale, silhouette, materials, clipping, framing. `--headless` is for tests only.
4. **Independent review.** The creator is never the sole reviewer. Roles: *creator* (art, Phases 1–4 + 7, renders + review sheet) · *art reviewer* (references, silhouette, proportions, materials, detail, consistency – must reject off-direction work) · *engine reviewer* (scale, import, in-engine materials, LODs, collision, skeleton, performance, Phase 8 – must reject broken integration). As a single agent, run the reviews as **separate passes with fresh eyes** (e.g. a sub-agent that only sees the renders + references) and document who/what reviewed; never self-approve in the same breath you created.
5. **Scoring 0–5** in: Silhouette, Proportions, Geometry, Materials, Textures, Lighting, Visual detail, Animation quality, Technical optimization, Engine integration (Godot). **Pass = ≥ 4 in every applicable category** (one 3 fails). `N/A` only when truly not applicable. Never massage scores. Template `Docs/Reviews/TEMPLATE_ASSET_REVIEW.md`; file `Docs/Reviews/YYYY-MM-DD_<asset>.md` + sheet `Docs/Reviews/sheets/<asset>_ref_compare.png` (`Tools/uwp review-sheet`).
6. Registry `PRODUCTION-READY` only after the gate passes (art + engine review, all ≥ 4, Phases 1–8, renders + reference comparison + uwp validation + in-engine capture attached). Task `COMPLETED` ≠ production-ready. Never write FINAL/AAA on an asset that has not passed.
7. Checklists in the gate doc: characters (proportions, face, skin, natural hair – not a plastic shell, folds, hands, topology, rigging, animations, all angles, close-up + gameplay), vehicles (proportions, real glass, tyres/rims, lights, paint, interior, working doors, collision, LODs, Godot integration), environments (variation, façades, sidewalks, furniture, signs, traffic lights, vegetation, markings, lighting, storytelling, density – no empty box streets).
8. One coherent visual identity for everything.

### 5.2 Task workflow (`Docs/HANDOFF_PROTOCOL.md`, `Docs/TASK_BOARD.md`)
- IDs `T-<AREA>-NN[x]` (BOOT, PIPE, DES, ART, GP, AI, LVL, MIS, UI, BUILD, QA, …). Statuses `BACKLOG · IN PROGRESS · READY FOR REVIEW · BLOCKED · COMPLETED`. Priority P0 blocks others, P1 slice-critical, P2 polish.
- Each task block lists agent, deps, description, expected output, file ownership, acceptance, status, and after delivery "Delivered / Verified / Not done".
- Asset requests = `Docs/Handoffs/REQ_<name>.md` (exact names, dims, nodes/sockets, clips with speeds, budget). Existing: REQ_SK_Jason_Controller (REQ-GP01-JASON, CONFIRMED), REQ_WPN_Pistol_01 (REQ-GP02-PISTOL, CONFIRMED), REQ_NPC_Characters (REQ-AI01-NPC, ACCEPTED), REQ_VEH_Sedan_01 (CONFIRMED, CR-1..4).
- Decisions = new `TD-0NN` entry (PROPOSED → ACCEPTED) in `Docs/TECHNICAL_DECISIONS.md`.
- On finishing: update TASK_BOARD, `DEVELOPMENT_LOG.md` (what + how verified), `ASSET_REGISTRY.md` (assets), `INTEGRATION_LOG.md` (engine integrations), `BLOCKERS.md`, `PROJECT_STATUS.md`. Handoff note template in HANDOFF_PROTOCOL §4.
- Placeholders are prefixed `PT_` and must be replaced before a milestone closes.

### 5.3 Merge gate, branches, PRs
- **`Tests/run_all.sh` must print `RUN_ALL: PASS` on a fresh worktree** (`git worktree add`, `git lfs pull`) of the exact head you merge. Negative/sabotage checks exist (e.g. `UW_JASON_SABOTAGE=1` in the player test, AI negative test) – a new test must be shown to fail when the feature is broken.
- One task per branch (`<area>/<task-id>-slug`), one PR per task, commit messages `[T-XXX-NN] summary`.
- Never force-push, never rewrite pushed history, never `reset --hard` shared branches. Update a branch by **merging `origin/main` into it** (not rebasing pushed work).
- Merge with `gh pr merge <n> --merge --match-head-commit <sha>` after the gate. Never merge a draft or a red/untested PR.
- Never commit secrets or files > 100 MB; binaries via LFS only.

### 5.4 License policy (`Docs/ASSET_LICENSES.md`)
- Third-party content **only CC0-1.0 or CC-BY-4.0** (commercial use allowed; CC-BY credited). Rejected: NC, Mixamo/Adobe EULA, unlicensed scrapes, ripped game assets, real brands/logos.
- Current sources: MakeHuman/MPFB2 CC0 data (base mesh, 1,258 targets, rig, weights), MakeHuman system assets/skins01/skins02/suits01 (CC0), faceunits01 + visemes01 (CC0), `walk1.bvh` (CC0), Poly Haven textures (CC0). MPFB2 **code** is GPLv3 and is **not** used.
- Raw downloads stay in gitignored `.cache/uwp_sources/` (re-fetch with `fetch_sources.py`); only derived outputs are committed.
- Every new source gets a row before use. Vendored skill repos' licenses: §6.

### 5.5 LFS / disk budget
GitHub Free LFS ≈ 1 GB storage + 1 GB/month bandwidth; ~73 MB used. Rules: 1024² textures by default, 2048² hero only, JPEG albedo/ORM where acceptable, no raw > 4K sources, no hi-poly bake intermediates in git, export templates Linux-only. Watch `git lfs ls-files -s`. If you approach ~700 MB, tell the owner before buying a data pack.

---

## 6. Skills & tools (`Docs/SKILLS_AND_TOOLS.md` = full verdicts)

Eleven repos were shallow-cloned read-only to `/workspace/tools/skills-vendor/<owner>__<repo>` on the old box (**not** in git). Verdicts:
| Repo | Verdict | License | Use for |
|---|---|---|---|
| setcodes/gamedev-skills | USE | MIT | `game-designer`, `godot-gamedev`, `blender-game-assets` headless helpers (`bpy_lib.py`, `bg_verify.py`, `maps_post.py`, `verify_glb.py`); its MCP bridge not usable headless |
| majidmanzarpour/blender-game-skills | USE | MIT | `blender-image-to-3d`: reference-compare gated modelling loop (not auto image-to-3D); `review_render.py --engine cycles`, `compose_review.py`, `world_gate.py` |
| sekaikx/ForgeSkills | USE | Apache-2.0 | orchestrator/verification, blender-headless, reference-reconstruction, modular-kit, texture, animation, lighting; Godot skills unproven by authors |
| proyecto26/blender-ai-plugin | PARTLY | MIT | scripts only (LOD, collision proxy, rig check, Godot export, UV, bake) via `blender -b --python script -- '<json>'`; not the Lab-MCP plugin |
| yi00it/blender-asset-mcp | PARTLY (read only) | MIT | read algorithms in `handlers/assets.py`; do not run |
| Sods2/godot-mcp | PARTLY, not installed | MIT | possible later (file tools, test runners); live editor/screenshots need GUI + plugin; prefer `Tools/godot_phase8_capture.sh` |
| pbzona/godot-skills | USE (docs) | MIT | godot-3d-gameplay, navigation-ai, architecture, patterns; game-mechanics/systems/balance design |
| TheMarco/godot-game-skills | USE (selective) | MIT | godot-game-verification, performance-workflows, 3d-prop-integration, environment-wear |
| gamedev-skills/awesome-gamedev-agent-skills | USE (Godot + workflows) | Apache-2.0 | godot-gdscript-headless-testing, gdscript, 3d-essentials, physics, animation, resources, export; workflows/game-docs |
| maystudios/claude-skills | SKIP | MIT | UE5 + media tools (API keys, yt-dlp, runtime pip) |
| kevinpbuckley/unreal-engine-skills | SKIP | **none** | wrong engine, no license – do not copy |
No other repos were vetted. Anything not in this table is **unvetted**.

**Security rule:** never run `install.sh`, `install.py`, `npx skills add`, `npm install`, `uvx`, plugin installers, MCP servers, Blender add-ons or Godot editor plugins from third-party repos without reading the code first and recording a TD. Blender MCP = arbitrary Python as the user. Project docs override skill advice.

**Recommended Claude Code skills** (copy only the skill folders, by hand, after reading them; keep each repo's LICENSE next to the copy; pin the HEAD from SKILLS_AND_TOOLS.md):
```bash
# project-scoped skills (committed) – one folder per skill with its SKILL.md
mkdir -p .claude/skills
V=/workspace/tools/skills-vendor   # re-clone with git clone --depth 1 if missing
cp -r $V/setcodes__gamedev-skills/skills/godot-gamedev            .claude/skills/
cp -r $V/setcodes__gamedev-skills/skills/game-designer            .claude/skills/
cp -r $V/majidmanzarpour__blender-game-skills/skills/blender-image-to-3d .claude/skills/
cp -r $V/sekaikx__ForgeSkills/skills/gamedev-blender-headless     .claude/skills/
cp -r $V/sekaikx__ForgeSkills/skills/gamedev-verification         .claude/skills/
cp -r $V/gamedev-skills__awesome-gamedev-agent-skills/skills/godot/godot-gdscript-headless-testing .claude/skills/
cp -r $V/TheMarco__godot-game-skills/skills/godot-performance-workflows .claude/skills/
```
Then add a `NOTICE`/license file per copied skill and a line in `Docs/SKILLS_AND_TOOLS.md`. Do **not** copy Unreal skills, maystudios, MCP servers or installers. Skills are guidance; `Tools/uwp`, the TDs and the quality gate stay the source of truth. (Large skill folders count against repo size – copy only what you use.)

---

## 7. Honest quality status per asset

First quality-gate reviews (Bot 1 art scores, 2026-11-22, `Docs/Reviews/`). Engine scores = **pending** for every asset (no independent engine review, no Phase 8 capture yet). `3*` = preliminary, from headless import only.

| Category | SK_Jason v2 | SK_NPC_Sam | WPN_Pistol_01 | VH_Sedan_01 | LA kit |
|---|---:|---:|---:|---:|---:|
| Silhouette | 3 | 2 | 2 | 2 | 2 |
| Proportions | 3 | 2 | 2 | 2 | 3 |
| Geometry | 2 | 2 | 2 | 2 | 2 |
| Materials | 2 | 2 | 1 | 2 | 2 |
| Textures | 2 | 2 | 1 | 1 | 2 |
| Lighting | 3 | 2 | 2 | 2 | 2 |
| Visual detail | 2 | 1 | 1 | 1 | 1 |
| Animation quality | 2 | 2 | 2 | 2 | N/A |
| Technical optimization | 3 | 3 | 3 | 3 | 3 |
| Engine integration | 3* | 3* | 3* | 3* | 3* |
| **Verdict** | **REJECT** | **REJECT** | **REJECT** | **REJECT** | **REJECT** |

Known defects:
- **SK_Jason v2** (T-ART-01b): hair is a ridged/torn plastic shell (needs hair cards/strands + skin fade); beard is a textured card; jacket open with a ragged hem, no ribbed bomber knit or real zipper, crude collar, neck intersection; jeans without folds/seams/wear; boots are slip-on blobs (need laces, eyelets, tongue, tread); T-shirt albedo moiré; waxy close-ups, weak eyelids, hairline gaps; stiff aim pose, hands don't read as a two-handed grip; computed animation (not mocap), foot slide up to 4.86 cm; **no LODs**; 12 meshes / 10 materials is heavy; no Phase 8 shot. Not close-up ready.
- **SK_NPC_Sam:** tube coat, spiky collar, no lapels/buttons/pockets/belt, blob shoes, hollow sleeves, hair shell (helmet look reduced but still poor), trousers show through the coat, shared generic clips. No reference board.
- **WPN_Pistol_01:** blockout (1,920 tris); diamond-plate `metal_plate` texture is wrong for a firearm; open trigger guard, barrel not flush; no sights/serrations/stippling/pins; dark previews. Draft PR #11 attempts the fix (§8.1).
- **VH_Sedan_01:** blockout (3,382 tris): slab body, prism cabin (roof was a crumpled blob, fixed by Bot 1), one paint, no glass/chrome/rubber, no real lights/grille/rims/handles/interior. No reference board.
- **LA kit:** primitives (toy palm, box buildings), tiling greybox shaders, no trim sheets/decals/wear, no street furniture, signs, crosswalk, traffic light, hydrant, apartment block, awning; street not assembled for gameplay; no reference board.
- **Remaining NPCs** `SK_NPC_Marco`, `SK_NPC_Cartel_A`, `SK_NPC_Cartel_B`, `SK_NPC_Cop_LA`, `SK_NPC_Civilian_Female`: **specs only** (`Config/Characters/`), not built (~10 MB LFS each).
- **No GPU:** nothing has been seen in Godot's shipping renderer. Look of materials, `ENV_LA_*` presets, animation blending, camera feel, driving feel and FPS are unverified (B-003). Phase 8 software-GL capture exists but has not yet been run on any hero asset.
- **Clipping gate was loosened** in PR #8: `uwp validate` raises `MESH_CLIPPING` as an *error* only if ≥ 20 verts tested, **≥ 8 clipped** and clipped fraction > `clipping_error_frac` 0.03 (`Tools/underworld_pipeline/defaults.json`, `validate.py`); smaller clipping is info-only. Visible jacket/neck clipping can therefore pass validation – judge renders, and consider tightening once clothing is rebuilt.
- Silhouette IoU 0.7–0.8 is a blockout/forms gate, not a production match.

---

## 8. Open work at handoff

### 8.1 Open PRs / WIP branches
| Item | State | What to do |
|---|---|---|
| **PR #11** `bot2/dev` (`cd87981`), draft, "[T-ART-03 WIP] WPN_Pistol_01 quality pass" | **Task ID is T-ART-05** (board numbering kept; T-ART-03 = LA kit). Contains: reference board `Docs/ArtDirection/References/WPN_Pistol_01/` (collage + REFERENCES.md, Wikimedia Commons sources), v0 before-renders `Docs/ArtDirection/Reviews/WPN_Pistol_01/before/`, new HP/LP hard-surface generator (`weapons/{hardsurface,pistol_hs,hs_materials,baker,render_review}.py`, rewritten `build_weapon.py`; LP 2,526 tris / HP 22,647 tris in a fast smoke build; closed guard, flush barrel, serrations, stippling, black-nitride/polymer; 2048 atlas bake), WIP note `Docs/Handoffs/2026-11-22_T-ART-03_WPN_Pistol_01_WIP.md`, old prototype scripts. **No tests were run; shipped asset is still v0.** | Branch `art/t-art-05-pistol` from it (or continue on it), merge `origin/main`, run: after-renders → full bake + `Tools/uwp export` (check GLB size; normal map PNG 2048) → render-compare loop vs board until all ≥ 4 → uwp tests, Godot import, `Tests/run_all.sh` (`test_weapon.gd` on the real glb) → update PIPELINE_WEAPONS.md (still describes metal_plate), registry, board, dev log, review + scorecard. Verify Commons licenses are CC0/CC-BY (policy §5.4) before merging the board. Close #11 when superseded. |
| Old branches `bot3/*`, `bot1/quality-gate`, `pipe/t-pipe-04-recovered`, `cursor/character-pipeline-sk-jason-v2-6fae` | all merged | may be deleted (ask owner – deleting is visible). |
| Local worktrees on the old box (`/workspace/UNDERWORLD-bot2`, `-bot3`, `wt-*`) | clean / merged | nothing unpushed except what is in PR #11. |

### 8.2 Art backlog (from Bot 2's handoff)
- **Jason T-ART-01b:** hair cards + skin fade, groomed beard, closed/zipped bomber with ribbed hem/cuffs and clean collar, jeans folds/seams/wear, laced work boots, fix T-shirt moiré, eyelids/hairline, natural two-handed aim + hands, better (mocap-quality) clips, LOD1/LOD2, fewer materials/meshes, Phase 8 capture.
- **NPCs (T-ART-06 / REQ-AI01-NPC):** build Marco, Cartel_A/B (≥ 2 gunman variants), Cop_LA, Civilian_Female (+ shopkeeper/Civilian_B/C per REQ) from specs on Jason's skeleton, ≤ 25k tris, `SOCKET_RightHand_Weapon`, hitbox bones, clips for cover crouch (head ≤ 1.1 m), peek-aim, shoot, reload 1.6 s, flee, cower, look-around, hit-react, death. Fix Sam per review. Reference boards first.
- **Sedan (T-ART-04):** real hi-poly body with hood/trunk flush to the body, interior, separate glass, chrome/rubber/lights, damage-ready; REQ_VEH CRs: **CR-1** `SOCKET_Enter_Left/Right` with orientation (+Z = facing the door), **CR-2** `SOCKET_SteeringWheel` or rotatable `SteeringWheel` node, **CR-3** LOD1/2 for Hood/Trunk/Bumpers, **CR-4** verify right-wheel rims face outward (mirror if not); align `A_Humanoid_Car_Enter_L/Exit_L` start/end poses to the sockets.
- **LA kit (T-ART-03):** awning, crosswalk, traffic light, 4-storey brick apartment block, hydrant, trash can, bus stop, fence, dumpster, garage interior/workbench/roll-up door, shared trim sheets + decals (cracks, oil, manholes), wear, invented signage, LOD1 on road/sidewalk.
- **Pipeline rules:** `uw_lod_post_import.gd` must stay byte-identical between `Tools/underworld_pipeline/godot/` and `GodotProject/Scripts/import/` (asset-import test fails on drift). **TD-012** (LOD/collision/material budgets into `Config/asset_budgets.json`) is still PROPOSED – decide and apply (T-PIPE-05).

### 8.3 Gameplay / AI / vehicle / QA backlog (from Bot 3's handoff)
- **Player/gameplay:** player hitboxes are placeholder boxes → attach to bones (`BoneAttachment3D`, REQ-AI01-NPC); no upper-body/aim-offset layering (aim blend is full-body); `Shoot`, `Reload`, `Carry`, `Death`, `Car_Enter/Exit` clips exist but are **not wired**; open tasks T-GP-01b vault-lite (P2), T-GP-02b ragdoll-lite (P2), **T-UI-01 HUD**, **T-BUILD-01 Linux export** (exclude `Scripts/import/` and `Tests/` from the export).
- **AI:** no flank-lite, no NPC-vs-NPC targeting, no RVO avoidance; **BUG: enemies target the hidden player while he sits in the car** (they aim at the seat); NPC scenes still PT capsules → switch to `SK_NPC_*` + `A_Humanoid_*`; **T-AI-02** civilian behaviour on the street not started (baseline flee/calm exists in `AI_Civilian.tres`).
- **Vehicle:** enter/exit uses fixed timers (0.6 / 0.5 s) – drive them from the clips; missing passenger seat, carjacking, NPC drivers, ram damage to characters, engine sound, lit headlights; driving feel untuned (`VH_Sedan_01.tres` all `[DEFAULT]`, B-003); CR-1..4; TD-014 workarounds: **re-check the static-sag constant `4.0 / suspension_stiffness` and the wheel-draw offset on any Godot upgrade**; player collision returns 2 physics frames after exit (keep the test).
- **QA:** `run_all.sh` is the merge gate and sabotage modes must keep failing; no visual/FPS checks without GPU – Phase 8 capture script exists, wire it into T-QA-01 (visual regression shots); keep the `uw_lod_post_import.gd` mirror identical.
- **Missions/level (updated 2026-11-23):** T-MIS-01 framework + M01 core merged (PR #14/#15/#16), open: Marco ally, wave sequencing, real drive loop. T-LVL-01: generated greybox `LA_CallowayAve.tscn` (not dressed). Layout brief `Docs/LevelDesign/LA_CallowayAve_Layout.md` v1 exists.

### 8.4 Blockers (`Docs/BLOCKERS.md`)
- **B-003 OPEN – no GPU.** Workaround: software-GL Phase 8 captures (gl_compatibility). Real fix: a GPU machine or GPU CI runner for Forward Plus look, FPS and feel. EuroHPC/HPC compute is not set up and would be batch, not interactive – do not plan on it; ask the owner for a GPU box/runner when M1 needs perf/look sign-off.
- **B-004 OPEN (owner):** Jason's surname; €5,000 detail; working names Los Cuervos, La Hermandad del Sur, Marco Ruiz, Dana Whitlock, Calloway Avenue/East Hollow.
- **B-005 OPEN (risk):** disk (~11 GB free) and GitHub LFS quota (~1 GB).
- B-001 MITIGATED (no Blender MCP → headless bpy). B-002, B-006 RESOLVED.

---

## 9. Roadmap to release

Priorities: **P0** blocks others / release-critical · **P1** needed for the milestone · **P2** polish/stretch. Order milestones as listed; inside a milestone, P0 first. Every art item passes the quality gate; every code item ships with headless tests (+ a sabotage check) and a Phase 8 capture where visual.

### M1 – Vertical slice "Dead Drop" playable (current milestone)
| ID | Pri | Task | Acceptance |
|---|---|---|---|
| T-DOC-01 | P1 | Align GDD Jason row with art direction (early 30s, crew T-shirt) | GDD = ArtDirection README |
| T-DES-02 | P0 | `Docs/LevelDesign/LA_CallowayAve_Layout.md` – top-down block-out with dimensions, trigger areas, cover, spawn points, ~300 m drive loop | kit pieces + areas dimensioned; level can be built without questions |
| T-LVL-01 | P0 | `Scenes/Levels/LA_CallowayAve.tscn` from the greybox block: kit placement, collisions, baked navmesh, golden-hour `ENV_LA_GoldenHour`, occluders, Area3Ds named per M01 | walk + drive the whole street; navmesh covers sidewalks/road; no missing refs; Phase 8 shots |
| T-MIS-01 | P0 | Data-driven mission framework (objectives, triggers, markers, checkpoints, fail/retry) + M01 per design incl. Marco ally, 2 ambush waves, package carry/HP, delivery, reward | headless test steps all objectives via `MissionManager.debug_complete_current()`; every fail state restarts at the right checkpoint |
| T-GP-04 | P0 | Wire Jason clips: shoot/reload/carry/death/car enter-exit; upper-body aim layer; bone-attached player hitboxes | clips play at the right events; hitboxes follow bones; tests |
| T-AI-03 | P0 | Fix enemies targeting the hidden in-car player; enemies shoot at the car/driver; NPCs on `SK_NPC_*` models | test: seated player not targeted through the roof; real models load |
| T-AI-02 | P1 | Civilians on Calloway Ave (≥ 3): routes, idle, flee ≤ 25 m, calm down | as task board |
| T-UI-01 | P0 | HUD: health, ammo, crosshair, objective text, GPS marker, subtitles, mission-passed card | visible in Phase 8 capture; driven by game state in tests |
| T-AUD-01 | P1 | Audio v0: pistol, impacts, footsteps, car engine/tyres/crash, ambience, UI; CC0/CC-BY only; Sam phone call VO placeholder + subtitles | buses set up; sources in ASSET_LICENSES |
| T-SAVE-01 | P1 | Checkpoint save/load (mission state, player, car, package) | restart from checkpoint after quit; test |
| T-ART-01b / 04 / 05 / 03 / 06 | P0 | Hero art through the gate: Jason, sedan, pistol (finish #11), LA kit + M01 props, Marco + 2 cartel gunmen + civilians | each review ≥ 4 in all categories, Phase 8 shot in the street |
| T-BUILD-01 | P0 | Linux export: export_presets.cfg, `Tools/build/build_linux.sh`, Linux templates only, exclude `Scripts/import/` and `Tests/` | binary runs `--headless --quit-after 300` clean; size documented |
| T-QA-01 | P1 | Visual regression captures via `godot_phase8_capture.sh`; GitHub Actions CI running `Tests/run_all.sh` (Godot + Blender cached, LFS) | CI green on PRs; required check on `main` |
**M1 exit:** M01 playable start → finish in a Linux build in ~10–15 min, all assets PRODUCTION-READY or explicitly waived by the owner, no `PT_` assets, run_all green, owner sign-off on a GPU recording.

### M2 – Art quality to the gate across the slice + style lock
P0: reference boards for every hero asset; LODs for characters; hair/cloth solution (cards + baked normals); car paint/glass shader; trim-sheet library; look-dev sign-off on a GPU (Forward Plus, ACES, fog, GI choice). P1: facial blendshape use in dialogue; mocap-quality locomotion (CC0/CC-BY mocap or keyframed polish). Acceptance: style guide `Docs/ArtDirection/STYLE_GUIDE.md`; all slice assets ≥ 4.

### M3 – Core systems
| Pri | System | Acceptance highlights |
|---|---|---|
| P0 | Cover system (snap, blind fire, corner peek) + vault (T-GP-01b) | AI + player share cover points; tests |
| P0 | Wanted level + police (spawn, pursuit, search, escape) | stars escalate/decay; police AI on foot + cars |
| P0 | Traffic (lanes, intersections, lights, NPC drivers, carjacking) | traffic graph; drivers obey lights; jack + flee |
| P0 | Pedestrians with daily routines + reactions | schedules, density by district/time |
| P0 | Damage model: player/NPC health, armour, vehicle deformation/fire, ragdoll (T-GP-02b) | deterministic tests |
| P1 | Melee (punch, grab, takedown) | anims on shared skeleton |
| P1 | Weapons roster (pistols, SMG, shotgun, rifle, sniper, throwables) + attachments, weapon wheel | data-driven `WeaponData` |
| P1 | Vehicle roster (sedans, pickup, muscle, van, police, taxi, bike; boat/aircraft for Ch.1 finale) | one `VehicleData` each; gate per asset |
| P1 | Phone (calls, contacts, mission start) + minimap/map/GPS | |
| P1 | Economy (cash, shops, rewards, drug trade 80/20), inventory | |
| P2 | Side activities (taxi), dynamic weather, time of day | |

### M4 – LA open world
P0: world partition/streaming (chunked scenes, async `ResourceLoader`), LOD + HLOD, occlusion culling, visibility ranges, navmesh per chunk, traffic/ped spawning by chunk; district blockout of East Hollow, Downtown, Crestmont Hills, Harbor, Seaview, freeway links. P1: interiors, landmarks (original), San Ardo mountains, rural north. Acceptance: free roam across ≥ 2 districts with no load screens, memory and frame budget met on the target GPU.

### M5 – Chapter 1 story (LA)
P0: missions Arrival, The Route (deliveries + Emerald Triangle), Dead Drop (final), The Raid, Wings (aircraft escape); dialogue/cinematic system (AnimationPlayer + camera rigs, subtitles, lip-sync via visemes); characters Sam, Marco, Whitlock, cartel crews. Acceptance: Ch.1 playable start→end with checkpoints and fail states; target play length to be defined in the GDD.

### M6 – Chapter 2 (New York)
P0: NY fictionalised boroughs (Brooklyn first), cold/wet look, taxi activity, missions 6–16 (heists, farm, cartel war, kidnapping, gold depot, Sam reveal, finale, epilogue), Kings of Flatbush, La Hermandad. P1: subways, bridges, Staten Island, park. Acceptance per mission as M5.

### M7 – UI/UX, menus, settings, accessibility
P0: main/pause menus, settings (graphics presets, resolution, FOV, keybinds/gamepad remap, audio sliders), save slots, loading screens. P1: subtitles size/background, colour-blind modes, aim assist, hold/toggle options, camera shake toggle, difficulty. Acceptance: full controller navigation; settings persist.

### M8 – Audio, VO, music
P0: weapon/vehicle/ambience suites, mixing, radio stations (original/licensed CC-BY or commissioned), VO for story (actors or licensed TTS with rights cleared – owner decision), music score. All licenses documented.

### M9 – Performance, platforms, QA, CI, builds, localization
P0: target platforms decided with owner (Windows + Linux PC first; console later needs dev kits), min/rec specs, 60 fps on mid-range GPU (TD-009), profiling passes, memory budgets; GitHub Actions running `Tests/run_all.sh` + export builds; Windows export; crash-free soak tests; bug tracker. P1: **localization DE/EN** (Godot translation CSV/PO, all UI + subtitles), optional other languages. Acceptance: CI green, nightly builds, perf captures on reference GPU.

### M10 – Release checklist
P0: store page (Steam/itch – owner account), age rating (USK/PEGI/ESRB via IARC), EULA/privacy, third-party license file generated from `ASSET_LICENSES.md` + Godot/MIT notices, trademark/IP check of all names (B-004), crash reporting (Godot crash handler + opt-in upload), versioning/changelog, final QA pass, launch build signed. Owner approves every external submission.

**Ordering:** M1 → M2 (overlaps M1 art) → M3 → M4 → M5 → M6, with M7–M9 running continuously from M3 and M10 last.

---

## 10. Working rules for Claude Code

1. **Start of every session:** `git pull`; read `CLAUDE.md`, this handoff, `Docs/PROJECT_STATUS.md`, `Docs/TASK_BOARD.md`, `Docs/BLOCKERS.md`; check `gh pr list`.
2. **Run `./Tests/run_all.sh` before you change anything and after.** Never merge red. Fresh worktree for the merge check.
3. **One task per branch and PR**, ID in branch + commit + PR title; set the board status when you start and finish.
4. **Proof:** art = Cycles renders + `Tools/uwp review-sheet` + review file with scores + Phase 8 capture; gameplay = tests + capture where visual. Attach to the PR.
5. **Keep docs current** in the same PR: TASK_BOARD, DEVELOPMENT_LOG, INTEGRATION_LOG, ASSET_REGISTRY, ASSET_LICENSES, TECHNICAL_DECISIONS (new TD-015+), BLOCKERS, PROJECT_STATUS, and this handoff when facts change.
6. **Honesty:** never claim done/AAA/production-ready without evidence; list what is unverified (GPU!). Report to Bärbel **in German**.
7. Respect TDs (axes, naming, no `_Loop`, layers, input-map script, budgets, LFS), license policy and security rule for third-party code.
8. No force-push, no history rewrites, no deleting branches/repos or spending money without owner OK.
9. Prefer reproducible scripts (spec → generator → export) over hand edits to generated files.
10. When unsure about design, record a decision request (TD PROPOSED) and ask the owner; don't silently change story/names.
