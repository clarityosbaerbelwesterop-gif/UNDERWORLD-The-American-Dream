# Task Board – Milestone 1 "LA Vertical Slice"

Owner: Bot 1. Each agent updates **Status** of its own tasks (and adds a line to `DEVELOPMENT_LOG.md`). New tasks / re-assignments only via Bot 1.
Statuses (tasks): `BACKLOG` · `IN PROGRESS` · `READY FOR REVIEW` · `BLOCKED` · `COMPLETED`.
Asset registry status `PRODUCTION-READY` is separate and is allowed only after a passed Quality Gate (`Docs/QUALITY_GATE.md`, template `Docs/Reviews/TEMPLATE_ASSET_REVIEW.md`). A task may be `COMPLETED` when the work item is delivered; that does **not** make the asset production-ready. First Bot 1 reviews (2026-11-22) **REJECT**ed SK_Jason v2, SK_NPC_Sam, WPN_Pistol_01, VH_Sedan_01 and the LA kit — all stay `WIP`.

Highest priority first inside each section. Priority: P0 = blocks others, P1 = slice-critical, P2 = polish.

## Summary

> **Handoff 2026-11-22:** the three-bot studio stopped; Claude Code takes over (`Docs/CLAUDE_CODE_HANDOFF.md`). Agent column = original owner role; new tasks from the handoff roadmap are listed there (§9) and get rows here when started.

| ID | Pri | Agent | Title | Depends on | Status |
|---|---|---|---|---|---|
| T-BOOT-01 | P0 | Bot 1 | Install Blender + Godot headless | – | COMPLETED |
| T-BOOT-02 | P0 | Bot 1 | Repo, structure, LFS | – | COMPLETED |
| T-BOOT-03 | P0 | Bot 1 | Project docs + task board | T-BOOT-02 | COMPLETED |
| T-PIPE-00 | P0 | Bot 1 | Pipeline smoke test baseline | T-BOOT-01/02 | COMPLETED |
| T-DES-01 | P1 | Bot 1 | Mission M01 design doc | T-BOOT-03 | READY FOR REVIEW |
| T-DES-02 | P1 | Bot 1 | Art direction + LA street layout brief | T-BOOT-03 | COMPLETED (layout brief v1 `Docs/LevelDesign/LA_CallowayAve_Layout.md`, PR #14) |
| T-PIPE-01 | P0 | Bot 2 | Production Blender export/validation tool | T-PIPE-00 | COMPLETED |
| T-PIPE-02 | P0 | Bot 3 | Godot import presets + per-asset import tests | T-PIPE-01 | COMPLETED |
| T-PIPE-03 | P0 | Lead TD | Production realistic character pipeline + SK_Jason v2 (CC0 human base, fitted clothing, Cycles hi-to-lo PBR, blendshapes, uwp quality gates + silhouette check) | T-PIPE-01, T-PIPE-02 | COMPLETED |
| T-ART-01 | P1 | Bot 2 / Lead TD | Jason model + rig + skin (upgraded to v2 in T-PIPE-03) | T-PIPE-01 | COMPLETED |
| T-ART-02 | P1 | Bot 2 | Jason animation set | T-ART-01 | COMPLETED |
| T-PIPE-04 | P0 | Lead TD → Bot 1 (recovered) | Whole-game asset pipeline v0: NPC/weapon/vehicle/env generators, shared anim library, LA look-dev presets, M01 block greybox | T-PIPE-03 | COMPLETED |
| T-ART-03 | P1 | Bot 2 / Lead TD | LA street environment kit | T-PIPE-01, T-DES-02 | IN PROGRESS |
| T-ART-04 | P1 | Bot 2 / Lead TD | Drivable car model | T-PIPE-01 | IN PROGRESS |
| T-ART-05 | P1 | Bot 2 / Lead TD | Pistol model (quality pass WIP = draft PR #11, titled "T-ART-03" by mistake) | T-PIPE-01 | IN PROGRESS |
| T-ART-06 | P1 | Bot 2 / Lead TD | 3 NPC models on shared rig | T-ART-01 | IN PROGRESS |
| T-GP-01 | P0 | Bot 3 | Third-person controller + camera | T-PIPE-00 | COMPLETED |
| T-GP-01b | P2 | Bot 3 | Vault-lite (low obstacles) | T-GP-01, T-ART-02 | BACKLOG |
| T-GP-01c | P1 | Bot 3 | Stairs / step-up for the player | T-GP-01 | COMPLETED |
| T-GP-01c-J | P1 | Bot 3 | Player visual: capsule → SK_Jason v2 | T-GP-01, T-ART-02 | COMPLETED |
| T-GP-02 | P1 | Bot 3 | Gunplay (pistol) | T-GP-01 | COMPLETED |
| T-GP-02a | P1 | Bot 3 | Rapid-fire bloom (stacking, cap, recovery delay) | T-GP-02 | COMPLETED |
| T-GP-02b | P2 | Bot 3 | Ragdoll-lite hit reaction | T-GP-02, T-ART-01 | BACKLOG |
| T-GP-03 | P1 | Bot 3 | Vehicle physics + enter/exit | T-GP-01 | COMPLETED |
| T-AI-01 | P1 | Bot 3 | Enemy AI (cartel gunmen) | T-GP-02 | COMPLETED |
| T-AI-02 | P2 | Bot 3 | Civilian NPC behaviour | T-GP-01 | IN PROGRESS (3 civilians placed on Calloway Ave, PR #14) |
| T-LVL-01 | P1 | Bot 3 | Assemble LA street level | T-ART-03 | IN PROGRESS (T-LVL-01a readability done; blockout, no art pass) |
| T-MIS-01 | P1 | Claude Code | Mission system + M01 implementation | T-DES-01, T-GP-02, T-GP-03, T-AI-01 | COMPLETED (gameplay, headless; #14–#17 + Bot 1 review fix; art still blockout; chase car = stretch, not built) |
| T-UI-01 | P2 | Bot 3 | HUD (health, ammo, objective text) | T-GP-02 | COMPLETED (40 checks, sabotage-verified) |
| T-BUILD-01 | P1 | Bot 3 / Claude Code | Playable Linux build + export script | T-PIPE-02 | COMPLETED (official 4.7.2 template; boots into M01 via Game_M01.tscn – Bot 1 fix; never played on a GPU) |
| T-QA-01 | P1 | Bot 3 → Claude Code | CI: GitHub Actions merge gate (run_all + Linux export + Forward Plus shots), LFS cache, hygiene check | T-GP-01 | READY FOR REVIEW (branch protection = Bot 1) |
| T-QA-02 | P0 | Bot 1 | Binding AAA Quality Gate + first honest asset reviews | T-PIPE-04 | COMPLETED |
| T-AI-03 | P0 | Claude Code | Enemies vs. player in a car (TD-015) | T-AI-01, T-GP-03 | COMPLETED (PR #17) |
| T-GP-04 | P0 | Claude Code | Jason clips wired, upper-body aim layer, bone hitboxes (TD-016) | T-GP-01c-J | COMPLETED (PR #17) |
| T-LVL-01a | P1 | Claude Code | Greybox readable, speaking names, baked navmesh (TD-018) | T-LVL-01 | COMPLETED (PR #17; nav-sync flake fixed by Bot 1) |
| T-BOOT-04 | P0 | Bot 1 | Shipping entry scene Game_M01 + test_boot (TD-020) | T-MIS-01 | COMPLETED (Bot 1 review fix of PR #17) |
| T-DOC-01 | P2 | Claude Code | GDD §2: Jason early 30s + grey crew T-shirt (art direction wins) | – | BACKLOG |
| T-ENV-01 | P0 | Claude Code | Cloud toolchain: exact Blender 5.2.4 LTS (bpy wheel) + official Godot 4.7.2 + templates + Forward Plus on lavapipe; `bootstrap_cloud.sh` | – | COMPLETED (PR #20, merged) |
| T-BUILD-02 | P0 | Claude Code | M01 acceptance of the current build: input-only autopilot playthrough gate, 18 blockers fixed, Forward Plus video (lavapipe) | T-ENV-01 | COMPLETED (PR #21, merged; run_all 785 PASS; M01 completed by input; GPU human playtest still open: B-007..B-010) |
| T-PIPE-06 | P0 | Claude Code | Pipeline audit + release gate `uwp --profile gate` + TD-021 hybrid pipeline (PROPOSED) | T-ENV-01 | COMPLETED (PR #23, merged; 8/17 sources pass the technical gate; audit `Docs/Reports/AUDIT_T-PIPE-06_Pipeline.md`) |
| T-PIPE-05 | P0 | Claude Code | TD-012 budgets in `Config/asset_budgets.json` (LOD fractions, collision) + checks | T-PIPE-06 | COMPLETED (PR #23, merged) |
| T-LOOK-01 | P0 | Claude Code | Look-dev calibration scene (Forward Plus), measured golden-hour/midday presets, single look source for level + look-dev, GI decision TD-024 | T-ENV-01 | COMPLETED (PR #24, merged; owner look sign-off open) |
| T-ANIM-01 | P0 | Claude Code | Animation pipeline (part 1): real shared humanoid library restored (was a committed 208-byte placeholder), NPCs borrow missing clips at runtime, placeholder scan in run_all | E-3 (anim source) | IN PROGRESS (part 1 COMPLETED: PR #25, merged; part 2 sit clips / foot IK waits for E-3) |
| T-DATA-01 | P0 | Claude Code | P1: combat database (`combat.json`, `CombatDB`, armor system, enemy tiers light/medium/heavy/boss, factions) + content catalogue (`catalog.json`, `uwp catalog`) + production plan P1–P10 | – | READY FOR REVIEW (TD-025 PROPOSED) |
| T-PROP-01 | P0 | Claude Code | P2/P3/P5: `uwp build-props` generator (CC0 material library, world-space texel density, lightmap UVs, label atlases, authored collision) + 27 assets (15 LA street furniture/road tiles, 9 items, 3 armor) through the release gate | T-DATA-01 | READY FOR REVIEW (TD-026 PROPOSED; art review pending, all WIP) |
| T-BLDG-01 | P0 | Claude Code | P3: `uwp build-buildings` facade grammar (openings + reveals, bands, roofs flat/hip/vault, fire escapes, galleries, awnings, signs) + 8 LA buildings (apartment, motel, gas station, warehouse M01, hangar, office tower, Crestmont villa, liquor store) through the release gate | T-PROP-01 | READY FOR REVIEW (TD-027 PROPOSED; all WIP) |
| T-WPN-01 | P0 | Claude Code | P5: `uwp build-weapons` weapon grammar + 9 rigged weapons (revolver, SMG, pump shotgun, carbine, bolt sniper, knife, bat, grenade, molotov) linked from combat.json; Reload clip length == reload_time (tested) | T-DATA-01 | READY FOR REVIEW (TD-028 PROPOSED; all WIP) |
| T-CHAR-01 | P0 | Claude Code | P4: NPC visuals - fix: enemies rendered as PT capsules over their models (M01); visible tier armor (vest/helmet on the skeleton via CombatDB.apply); 13 faction/boss specs; archetype line-up capture | T-WPN-01 | READY FOR REVIEW (part 1 PR #30 merged; part 2: 13 figures built, bosses wear concealed armor) |
| T-VEH-01 | P0 | Claude Code | P5: `uwp build-vehicles` body profiles + 5 cars (police, NY taxi, muscle, pickup, van) on the sedan contract; fleet test in the real vehicle.gd (assemble, park, drive) | T-WPN-01 | READY FOR REVIEW (TD-029 PROPOSED; motorcycle + plane open -> P7) |
| T-FX-01 | P0 | Claude Code | P6: `uwp build-fx` effect library (14 GPU-particle scenes: muzzle flash, impacts concrete/metal/glass/wood, blood, sparks, glass shatter, smoke, fire, explosion, rain, steam, tire smoke) + weapon integration (muzzle + surface impact per shot) | T-WPN-01 | READY FOR REVIEW (TD-030 PROPOSED) |
| T-LVL-02 | P1 | Claude Code | P8: dress M01 (Calloway Ave) with the kit: liquor store, office tower, stucco shop, brick walk-up, traffic light + street sign, hydrants, trash cans, newspaper boxes, payphone, parking meters, real parked cars (visual only on the cover boxes); B-007 fixed | T-BLDG-01 | READY FOR REVIEW (M01 autopilot seeds 1-5 PASS) |
| T-ANIM-02 | P1 | Claude Code | B-011: seated loops `A_Humanoid_Sit_Driver` / `_Sit_Passenger` (root = seat socket / H-point), `CharacterVisual.set_seated()`; Jason drawn in the driver seat while DRIVING, Marco in the passenger seat (rifle stowed); Jason borrows library clips by suffix | T-ANIM-01 | READY FOR REVIEW (test_vehicle + test_mission PASS) |
| T-VEH-02 | P1 | Claude Code | Vehicle interiors (seats, rear bench, dash, instrument hood, steering wheel + column, console, floor) built against the sit contract with a fit check; open cabin, see-through tinted glass; all 6 cars rebuilt (gate 6/6); sit pose: soles -0.22, wrists 0.34 | T-ANIM-02 | READY FOR REVIEW (test_vehicle, test_vehicle_fleet, test_mission PASS) |
| T-LOOK-02 | P1 | Claude Code | Graphics pass: AgX + SSIL on all presets (recalibrated), LA/NY chapter grade LUTs (code-generated), ENV_NY_Night/Overcast, MaterialPass (paint clear coat, skin SSS, eyes, hair, cloth sheen), set_wetness() for rain; M01 graded at runtime (GradedWorld) | T-LOOK-01 | READY FOR REVIEW (test_look PASS, negative control FAIL x4) |
| T-DECAL-01 | P1 | Claude Code | P2 decal set (13 generated decals, `uwp build-decals`) + M01 decal layer (137, ray-placed, own scene) + textured sun-bleached streets instead of flat greys + golden hour 18 deg | T-LOOK-02 | READY FOR REVIEW (test_decals, test_level PASS) |
| T-NY-01 | P1 | Claude Code | Chapter-2 NY set wave 1: brownstone (stoop), tenement (2 fire escapes, stores), corner bodega, neoclassical bank (heist), subway entrance (below grade, validator `uw_below_grade_m`); NY materials; soft ny_overcast; NY look-dev street capture | T-BLDG-01, T-LOOK-02 | READY FOR REVIEW (5/5 gate PASS) |
| T-SAVE-01 | P1 | Bot 3 | Checkpoint save/load (mission state, player, car, package) to `user://`; continue after quit (master prompt §8 #13) | T-MIS-01 | IN PROGRESS (branch `bot3/dev`) |

> **Next work order:** `Docs/Prompts/CLAUDE_CODE_MASTER_PROMPT.md` (§8 = ordered task list to release).

Placeholder rule: Bot 3 may start gameplay with Godot primitives (capsule, box car) so code is not blocked by art, but those are marked `PT_` and replaced before the milestone closes. Final slice must use Bot 2's original Blender assets.

---

## Detailed tasks

### T-BOOT-01 – Install Blender + Godot headless
- **Agent:** Bot 1 · **Deps:** – · **Status:** COMPLETED (2026-11-22)
- **Description:** Install portable Blender LTS and Godot 4 stable under `/workspace/tools/`, verify headless.
- **Expected output:** `/workspace/tools/blender/blender`, `/workspace/tools/godot`, `/workspace/tools/README.md`.
- **File ownership:** Bot 1 (`/workspace/tools/`).
- **Acceptance:** both print versions headless (Blender 5.2.4 LTS, Godot 4.7.2.stable) ✅

### T-BOOT-02 – Repository, structure, LFS
- **Agent:** Bot 1 · **Status:** COMPLETED
- **Expected output:** private repo `UNDERWORLD-The-American-Dream`, folders per README, `.gitignore`, `.gitattributes` (LFS).
- **Acceptance:** pushed to `main`; `git lfs ls-files` lists the .blend/.glb ✅

### T-BOOT-03 – Docs + task board
- **Agent:** Bot 1 · **Status:** COMPLETED
- **Expected output:** all docs in `Docs/` (this file, status, registry, logs, decisions, blockers, GDD, handoff protocol).
- **Acceptance:** every M1 task has ID/agent/description/deps/output/ownership/acceptance/status ✅

### T-PIPE-00 – Pipeline smoke test baseline
- **Agent:** Bot 1 · **Status:** COMPLETED
- **Description:** headless bpy script builds `PT_PipelineTest_Crate` (placeholder), applies transforms, validates, exports .glb; minimal Godot project imports it; test asserts scale/orientation/collision.
- **Expected output:** `Tools/blender_export.py`, `GodotProject/` (Main.tscn), `GodotProject/Tests/smoke_test.gd`, `Tests/run_pipeline_smoke.sh`.
- **Acceptance:** `./Tests/run_pipeline_smoke.sh` exits 0 and prints `PIPELINE SMOKE TEST: PASS`; a deliberately broken assertion makes it exit 1 ✅ (both verified)

### T-DES-01 – Mission M01 "Dead Drop" design doc
- **Agent:** Bot 1 · **Deps:** T-BOOT-03 · **Status:** READY FOR REVIEW (owner/Bot 3 review)
- **Expected output:** `Docs/Missions/M01_DeadDrop.md` – beats, objectives, triggers, fail states, required assets + nodes.
- **File ownership:** Bot 1.
- **Acceptance:** Bot 3 confirms it is implementable without further questions; every asset it needs exists as a task.

### T-DES-02 – Art direction + LA street layout brief
- **Agent:** Bot 1 · **Status:** IN PROGRESS
- **Expected output:** `Docs/GAME_DESIGN.md` §Art direction (done, v1) + `Docs/LevelDesign/LA_CallowayAve_Layout.md` (top-down block-out with dimensions).
- **Acceptance:** Bot 2 can model the kit with exact dimensions; Bot 3 can block out the level.

### T-PIPE-01 – Production Blender export & validation tool
- **Agent:** Bot 2 · **Deps:** T-PIPE-00 · **Status:** COMPLETED (2026-11-22, merged to `main` in 5cad0aa, reviewed by Bot 1; handoff `Docs/Handoffs/2026-11-22_T-PIPE-01.md`)
- **Description:** Turn `Tools/blender_export.py` into a reusable package `Tools/underworld_pipeline/` (CLI: `export <blend>`/`export-all`). Steps: validate (naming TD-005, applied transforms, UVs, materials, tri budget TD-009, non-manifold check), generate LODs (Decimate → `_LOD1/_LOD2`), collision (`UCX_`/Godot hints), export .glb (+ optional FBX), write `.manifest.json`, Cycles-CPU preview render PNG (`Assets/<...>/<Name>_preview.png`).
- **Expected output:** `Tools/underworld_pipeline/*.py`, docs in `Tools/README.md`, smoke test still passing.
- **File ownership:** Bot 2 (`Tools/`, `Blender/Scripts/`).
- **Acceptance:** runs headless on all assets in `Blender/Source/`, fails non-zero on any validation error; preview PNG produced; `Tests/run_pipeline_smoke.sh` PASS.

### T-PIPE-02 – Godot import presets + per-asset import tests
- **Agent:** Bot 3 · **Deps:** T-PIPE-01 · **Status:** COMPLETED (2026-11-22, accepted by Bot 1 at handoff: merged with green `Tests/run_all.sh`) – was READY FOR REVIEW (2026-11-22, Bot 3, branch `bot3/t-pipe-02`, PR #2)
- **Description:** import settings per category (characters: `SkeletonProfileHumanoid` retarget, animation loop flags; vehicles: keep wheel nodes; env: generate LODs/shadow meshes), test that loads every .glb listed in `ASSET_REGISTRY.md` and checks manifest dims vs. Godot AABB.
- **Expected output:** `GodotProject/Tests/test_assets.gd`, wired into `Tests/run_all.sh`.
- **File ownership:** Bot 3 (`.import` changes need a handoff note to Bot 2).
- **Acceptance:** test PASS for all registered assets, zero import errors.
- **Delivered:** project-wide scene import preset `[importer_defaults] scene/import_script/path = res://Scripts/import/uw_post_import.gd` in `project.godot` (applies to every **new** .glb import). `uw_post_import.gd` = (1) Bot 2's `uw_lod_post_import.gd` LOD visibility ranges (vendored byte-identical as `Scripts/import/uw_lod_post_import.gd`, drift-checked), (2) animation loop modes from `<Name>.manifest.json` `animations[].loop`, (3) summary meta `uw_post_import` on the scene root. Tests: `GodotProject/Tests/Import/test_assets.gd` + `Tests/run_asset_import_tests.sh` (exports Bot 2's procedural test assets with `Tools/uwp` into gitignored `GodotProject/Tests/_generated/`, imports, asserts). `Tests/run_all.sh` now = smoke + Bot 2's `Tools/underworld_pipeline/tests/run_tests.sh` (private scratch dir) + asset import + gameplay.
- **Verified:** `./Tests/run_all.sh` (clean `.godot/`) → smoke PASS, UWP TESTS PASS (106), ASSET IMPORT TESTS PASS (38), GAMEPLAY PASS (112), `RUN_ALL: PASS`. Barrel: preset applied to fresh `.import`, 6 LOD nodes ranged (LOD0 0–15 m, LOD1 15–40 m, LOD2 40–100 m), exactly one LOD drawn at every sampled distance 0–400 m, only LOD0 at 0 m; **control** copy imported without the script draws all 3 LODs at 0 m (proves the test catches the bug). RigTest: `A_..._Bend` LOOP_LINEAR / `A_..._Twist` LOOP_NONE = manifest, lengths = `duration_s`. Humanoid: 22 bones, all `SkeletonProfileHumanoid` names. All .glb load; manifest `aabb_godot` = Godot AABB. Negative check: loop step disabled → 2 failures, exit 1.
- **Not done / open:** characters `BoneMap`/retarget sub-resource settings (needs a real SK_Jason .import; bone names already match the profile, verified); vehicle preset (no vehicle test asset yet – Godot keeps named nodes by default); existing `PT_PipelineTest_Crate.glb.import` (Bot 2 file) keeps `import_script/path=""` – harmless (no LODs/anims), re-import or delete the sidecar to adopt the preset; exclude `Scripts/import/` + `Tests/` from game exports (T-BUILD-01).

### T-PIPE-03 – Production realistic character pipeline + SK_Jason v2
- **Agent:** Lead Tech Artist / Pipeline TD · **Deps:** T-PIPE-01, T-PIPE-02 · **Status:** COMPLETED (2026-11-22, PR #7 merged by Bot 1; follow-up quality pass T-ART-01b: jacket hem/clipping, hair shell, LODs, mocap animations)
- **Description:** Replace procedural primitive stickman SK_Jason v1 with a reusable, spec-driven realistic character pipeline (`Tools/underworld_pipeline/characters/` + `Config/Characters/SK_Jason.json`) built on verified CC0 MakeHuman/MPFB2 `hm08` base, 1,258 morph targets, 20 ARKit/viseme facial blendshapes, CC0 eyes/eyebrows/eyelashes/teeth, sculpted crop hair + beard shell, fitted separate clothing meshes (bomber jacket, t-shirt, jeans, boots, watch) with Cycles high-to-low normal/AO baking & CC0 Poly Haven PBR textures, 53-bone `SkeletonProfileHumanoid` rig + artist weights, CC0 BVH mocap-informed walk + fixed two-handed pistol grip, and automated `uwp` quality gates (weight normalization, UV overlap, texel density, layered clothing clipping check, multi-view Cycles CPU renders, turnaround silhouette/proportion comparison vs concept art).
- **Expected output:** `Tools/underworld_pipeline/characters/*.py`, `Tools/underworld_pipeline/fetch_sources.py`, `Tools/underworld_pipeline/silhouette_check.py`, upgraded `Tools/underworld_pipeline/{scene,validate,exporter,cli}.py`, `Config/Characters/SK_Jason.json`, `Blender/Source/Characters/SK_Jason/SK_Jason.blend`, `Assets/Characters/SK_Jason/SK_Jason.glb` (+ manifest, validation, anim_report, silhouette_report, 8 Cycles CPU previews), `Docs/ASSET_LICENSES.md`, `Docs/PIPELINE_CHARACTERS.md`, `Docs/PIPELINE_ROADMAP.md`.
- **Acceptance:** `Tools/uwp export SK_Jason.blend` PASS (0 errors, 0 warnings); `Blender/Scripts/sk_jason/verify_sk_jason.sh` PASS (0 Godot warnings); `Tests/run_all.sh` PASS; silhouette match vs `CA_Jason_Turnaround_v01.jpg` PASS (mean IoU 0.756, front IoU 0.814, mean proportion delta 0.0146); LFS footprint compact (`SK_Jason.glb` 10.7 MB, `SK_Jason.blend` 9.2 MB).

### T-ART-01 – Jason: model, rig, skin
- **Agent:** Bot 2 · **Deps:** T-PIPE-01 · **Status:** COMPLETED (2026-11-22, v1 via PR #5 commits inside PR #7, superseded by v2; handoff `Docs/Handoffs/2026-11-22_T-ART-01-02_SK_Jason.md`)
- **Description:** original male protagonist, 1.82 m, late 30s, see GAME_DESIGN §Characters. Modelled procedurally/with bpy (no purchased or ripped meshes). Armature with **Godot `SkeletonProfileHumanoid` bone names** (Hips, Spine, Chest, UpperChest, Neck, Head, Left/RightShoulder, Left/RightUpperArm, Left/RightLowerArm, Left/RightHand, fingers optional, Left/RightUpperLeg, Left/RightLowerLeg, Left/RightFoot, Left/RightToes) + `SOCKET_RightHand_Weapon`.
- **Expected output:** `Blender/Source/Characters/SK_Jason/SK_Jason.blend`, `Assets/Characters/SK_Jason/SK_Jason.glb`, manifest, preview PNG, ASSET_REGISTRY row.
- **Acceptance:** ≤ 40k tris; T-pose or A-pose rest; clean weights (no >4 influences); PBR materials; Godot import gives `Skeleton3D` + skinned `MeshInstance3D`, height 1.82 ± 0.02 m, faces +Z.

### T-ART-02 – Jason animation set
- **Agent:** Bot 2 · **Deps:** T-ART-01 · **Status:** COMPLETED (2026-11-22, merged via PR #7; all 21 REQ-GP01-JASON actions P1 + P2; `A_Jason_Jump_Loop` renamed to `A_Jason_Jump_Air` per director / TD-005 addendum – Bot 3 to update `CLIP_NAMES`)
- **Description:** keyframed in Blender via bpy: `A_Jason_Idle`, `A_Jason_Walk` (1.4 m/s), `A_Jason_Run` (3.5 m/s), `A_Jason_Sprint` (6 m/s), `A_Jason_Aim_Pistol` (upper-body pose), `A_Jason_Shoot_Pistol` (recoil, 0.25 s), `A_Jason_Reload_Pistol`. 30 fps, in place (no root motion), loop cycles seamless; speeds documented for Bot 3 blend-spaces.
- **Expected output:** actions inside `SK_Jason.glb` (or `Assets/Characters/SK_Jason/A_Jason_Locomotion.glb` on same skeleton).
- **Acceptance:** Godot `AnimationPlayer` lists all names; loops flagged; foot sliding < 5 cm per cycle at stated speed.

### T-PIPE-04 – Whole-game asset pipeline v0 (recovered cloud-agent work)
- **Agent:** Lead TD (Gemini cloud agent, unpushed) → recovered, re-run and verified by Bot 1 · **Deps:** T-PIPE-03 · **Status:** COMPLETED (2026-11-22, PR `pipe/t-pipe-04-recovered`)
- **Output:** `Tools/uwp build-character|build-shared-anims|build-weapon|build-vehicle|build-env|retarget`; generators `Tools/underworld_pipeline/{weapons,vehicles,environment}/`, `characters/build_shared_anims.py`; specs `Config/Characters/SK_NPC_*.json` (6), `Config/Weapons/WPN_Pistol_01.json`, `Config/Vehicles/VH_Sedan_01.json`; assets SK_NPC_Sam, A_Humanoid_Locomotion, WPN_Pistol_01, VH_Sedan_01, 6 LA kit pieces + SM_Prop_PackageCrate; `Assets/Environments/ENV_LA_{GoldenHour,Midday,Night}.tres`; scenes `Scenes/Levels/LA_CallowayAve_Block.tscn` (greybox, no gameplay), `Scenes/LookDev/LA_LookDev_Showcase.tscn`; docs `Docs/PIPELINE_{WEAPONS,VEHICLES,ENVIRONMENT,LOOKDEV}.md`.
- **Quality:** v0 / blockout grade for weapon, vehicle and kit; Sam on Jason v2 level. Not built yet: SK_NPC_Marco, Cartel_A/B, Cop_LA, Civilian_Female (specs only).

### T-ART-03 – LA street environment kit "Calloway Avenue"
- **Agent:** Bot 2 / Lead TD · **Deps:** T-PIPE-01, T-DES-02 · **Status:** IN PROGRESS (v0 kit merged via T-PIPE-04: road, sidewalk+curb, stucco shop, M01 garage, streetlight, palm, package crate; missing: crosswalk, apartment, traffic light, hydrant, trash can, bus stop, fence, LOD1 on road/sidewalk, trim sheets/decals)
- **Description:** modular original kit on a 2 m grid: road segment 10×14 m (2 lanes + parking), sidewalk 10×4 m with curb, crosswalk, 3 building facades (2-storey stucco shop, 4-storey brick apartment, mid-century motel/garage with roll-up door for M01), streetlight, traffic light, palm tree, hydrant, trash can, bus stop, fence, garage interior shell. Each with `-col`/`-colonly` collision and LOD1.
- **Expected output:** `Blender/Source/Environment/LA/<Piece>/...`, `Assets/Environment/LA/<Piece>/<Piece>.glb`.
- **Acceptance:** pieces snap on grid; budgets TD-009; collision present; registry rows.

### T-ART-04 – Drivable car "VH_Sedan_01"
- **Agent:** Bot 2 / Lead TD · **Deps:** T-PIPE-01 · **Status:** IN PROGRESS (v0 blockout merged via T-PIPE-04: 3,382 tris, separate wheels/doors/hood/trunk/bumpers + Cabin, sockets, convex collision; needs a real hi-poly body, interior, glass separation, damage states)
- **Description:** original late-90s American full-size sedan (no real brand), ~5.2×1.9×1.45 m. Separate nodes: `Body`, `Wheel_FL`, `Wheel_FR`, `Wheel_RL`, `Wheel_RR` (origins at wheel centres, radius documented), `Door_FL` (pivot at hinge), `SOCKET_Seat_Driver`, `SOCKET_Exit_Left`, convex collision `UCX_Body-convcolonly`.
- **Acceptance:** Godot import keeps wheel nodes; manifest lists wheel radius, wheelbase, track width; ≤ 60k tris.

### T-ART-05 – Pistol "WPN_Pistol_01"
- **Agent:** Bot 2 / Lead TD · **Deps:** T-PIPE-01 · **Status:** IN PROGRESS (v0 merged via T-PIPE-04: 1,920 tris, Slide/Magazine/Trigger, SOCKET_Muzzle +Z 0.165 m, Eject, Grip, clips Fire/Reload 1.6 s/Empty; weapon tests green with the real glb; needs proper gun-metal material instead of Poly Haven `metal_plate` tread pattern, closed trigger guard, barrel flush with slide)
- **ID note (Bot 1, 2026-11-22 handoff):** the pistol quality pass is **T-ART-05**. Draft PR #11 (`bot2/dev` `cd87981`) and its WIP note `Docs/Handoffs/2026-11-22_T-ART-03_WPN_Pistol_01_WIP.md` (on that branch) say "T-ART-03" by mistake; T-ART-03 stays the LA kit. PR #11 is untested WIP (reference board, HP/LP generator 2,526 / 22,647 tris; no after-renders, bake, export, tests or scorecard) – do not merge as is. See `Docs/CLAUDE_CODE_HANDOFF.md` §8.
- **Description:** original semi-auto pistol, origin at grip. Separate `Slide` and `Magazine` nodes; sockets `SOCKET_Muzzle`, `SOCKET_Eject`, `SOCKET_Grip`.
- **Acceptance:** ≤ 8k tris; sockets present after Godot import; scale fits Jason's hand (registry note).

### T-ART-06 – 3 NPC models (shared rig)
- **Agent:** Bot 2 / Lead TD · **Deps:** T-ART-01 · **Status:** IN PROGRESS (SK_NPC_Sam built + shared `A_Humanoid_Locomotion.glb` (21 clips) via T-PIPE-04; specs ready for Marco, Cartel_A/B, Cop_LA, Civilian_Female – build each with `Tools/uwp build-character`, ~10 MB LFS each)
- **Description:** `SK_NPC_Civilian_A` (female jogger), `SK_NPC_Civilian_B` (older male shop owner), `SK_NPC_Cartel_Gunman` (enemy, 2 colour variants). Same bone names as Jason so his animations play on them.
- **Acceptance:** ≤ 25k tris each; Jason's `A_Jason_Walk` plays on all three in Godot without retarget errors.

### T-GP-01 – Third-person controller + camera
- **Agent:** Bot 3 · **Deps:** T-PIPE-00 · **Status:** COMPLETED (2026-11-22, accepted by Bot 1 at handoff: merged with green `Tests/run_all.sh`) – was READY FOR REVIEW (2026-11-22, Bot 3; branch `bot3/dev`, PR #1)
- **Description:** `CharacterBody3D` player: walk/run/sprint, crouch, jump/vault-lite, acceleration curves, slope handling; `SpringArm3D` orbit camera with collision, over-shoulder aim mode (RMB), shoulder swap; input map for KB/M + gamepad; `AnimationTree` locomotion blend (placeholder capsule until T-ART-02).
- **Expected output:** `GodotProject/Scenes/Player/Player.tscn`, `GodotProject/Scripts/player/*.gd`.
- **Acceptance:** headless test moves the player 10 m forward with simulated input and asserts position; no penetration through Main.tscn ground/crate.
- **Delivered (Bot 3, 2026-11-22):** `Scenes/Player/Player.tscn` (CharacterBody3D + `PT_Capsule`, `Visual`, `CameraRig`→`Pitch`→`SpringArm3D`→`Camera3D`), `Scripts/player/player_controller.gd`, `camera_rig.gd`, `character_visual.gd`, test map `Scenes/Test/PT_PlayerTestRange.tscn` (generator `Scripts/tools/build_test_range.gd`), 19 input actions KB/M + gamepad in `project.godot` (generator `Scripts/tools/setup_input_map.gd`), tests `GodotProject/Tests/test_player_controller.gd`, runners `Tests/run_gameplay_tests.sh`, `Tests/run_all.sh`.
- **Verified:** `./Tests/run_all.sh` → `PIPELINE SMOKE TEST: PASS`, `GAMEPLAY TESTS: PASS` (94 checks, fixed 60 fps headless): scene loads, gravity + landing, 10 m forward (dz −10.31 m in 2.97 s), stops at Main.tscn PT crate (min z 0.850 = 0.5 + capsule r) without sinking, camera-relative move/strafe, walk/run/sprint 1.4/3.5/6.0 m/s, analog walk, jump apex 1.04 m, aim mode (arm 3.2→1.3 m, FOV 70→55, shoulder 0.6 m, faces aim dir, crosshair ray hits wall), shoulder swap, mouse + stick look, spring-arm wall collision, crouch under 1.4 m ceiling, 20° ramp, AnimationTree built from dummy `A_Jason_*` clips. Negative check: halving jump velocity → test exits 1.
- **Bot 1 decisions (2026-11-22):** facing TD-004 (+Z) stands; gamepad A = jump, Y = interact + enter vehicle, keyboard E/F (TD-010 ACCEPTED, input map regenerated + asserted in tests); REQ-GP01-JASON confirmed.
- **Note (T-GP-01c):** player collision is now a cylinder (r 0.35, h 1.8), not a capsule – see T-GP-01c, accepted as TD-011.
- **Not done / open:** vault-lite → **T-GP-01b**; stairs/step-up → **T-GP-01c** (READY FOR REVIEW); real animation blending only verified with empty dummy clips (needs T-ART-02); camera feel/visuals unverified without GPU (B-003).
- **Asset requirement for Bot 2 (T-ART-01/02) – REQ-GP01-JASON:** full spec in `Docs/Handoffs/REQ_SK_Jason_Controller.md`. Summary: `Assets/Characters/SK_Jason/SK_Jason.glb` with all actions; 1.82 m, origin at feet, 1 u = 1 m, Y-up, faces Godot +Z (TD-004); `SkeletonProfileHumanoid` bone names (+ `Root`, fingers recommended), T-pose, `SOCKET_RightHand_Weapon` parented to `RightHand`; **in place, no root motion**; 30 fps; P1 clips `A_Jason_Idle/Walk(1.4)/Run(3.5)/Sprint(6.0)/Crouch_Idle/Crouch_Walk(1.2)/Jump_Start/Jump_Air (was Jump_Loop, TD-005 addendum)/Land/Aim_Pistol_Idle/Aim_Pistol_Walk_F|B|L|R(2.0)/Shoot_Pistol(0.25 s)/Reload_Pistol(1.6 s)`; P2 `Carry_Idle/Carry_Walk, Death, Car_Enter_L/Car_Exit_L`. Extends T-ART-02 (new: crouch, jump, land, aim strafes; renames `A_Jason_Aim_Pistol` → `A_Jason_Aim_Pistol_Idle`). **CONFIRMED by Bot 1 (2026-11-22): takes priority over the older names in T-ART-02; Bot 1 assigns it to Bot 2.**

### T-GP-01b – Vault-lite
- **Agent:** Bot 3 · **Pri:** P2 · **Deps:** T-GP-01, T-ART-02 (vault animation) · **Status:** BACKLOG
- **Description:** vault over low obstacles (~0.5–1.1 m, e.g. fences, car bonnets) with ledge/height probing; context-sensitive on jump; needs `A_Jason_Vault` from Bot 2 (to be added to REQ-GP01-JASON when scheduled).
- **Acceptance:** headless test: 1.0 m fence is crossed with jump input, 2 m wall is not.

### T-GP-01c – Stairs / step-up
- **Agent:** Bot 3 · **Pri:** P1 · **Deps:** T-GP-01 · **Status:** COMPLETED (2026-11-22, accepted by Bot 1 at handoff: merged with green `Tests/run_all.sh`) – was READY FOR REVIEW (2026-11-22, Bot 3; branch `bot3/dev`)
- **Description:** `CharacterBody3D` step-up for steps up to ~0.35 m, stay grounded walking down steps (no hopping), never climb walls/ledges higher than the step height; stairs + ledges in the PT test range.
- **Expected output:** changes in `Scripts/player/player_controller.gd`, `Scenes/Test/PT_PlayerTestRange.tscn` (+ generator), tests in `GodotProject/Tests/test_player_controller.gd`.
- **Acceptance:** headless tests: climbs a stair flight; 0.5 m ledge blocks; walking down stays grounded; `Tests/run_all.sh` PASS.
- **Delivered:** `PlayerController._try_step_up()` (probe this frame's motion → wall-like hit → downward ray finds a walkable top ≤ `step_height` 0.35 m → head-room + clearance checks → lift; `stepped_up(height)` signal), `floor_snap_length = step_height + 0.05` for going down, player collision changed from capsule to **cylinder** (r 0.35, h 1.8; flat base rests on stair nosings – the capsule's round bottom lost floor contact on every riser; the PT visual is still a capsule). Test range: `Stairs_*` (8 × 0.2 m rise / 0.3 m tread → 1.6 m landing), `Ledge_050`, `Step_030`.
- **Verified:** `./Tests/run_all.sh` → `RUN_ALL: PASS` (smoke 12/12, gameplay 112/112). Stairs up: 8 step-ups of ~0.2 m, y 1.60 on landing, 0 airborne frames, 0 landings, max frame-to-frame drop 0.000 m, 1.92 s; stairs down at sprint: 0 airborne frames, 0 landings; walking off the 1.6 m landing side still falls + lands; 0.3 m step climbed (1 step-up); 0.5 m ledge blocks (max y 0.000, stops at the face) but can be jumped onto; pillar wall not climbed; no step-up on flat floor; 20° ramp + crouch tunnel + Main.tscn crate tests still pass. Negative check: `step_height = 0` → 5 failures, exit 1.
- **Known limits:** step-up only while grounded (not mid-air ledge grab = T-GP-01b); stairs steeper than 0.35 m rise need a collision ramp; camera smooths the vertical pivot so steps don't jolt (visual feel unverified without GPU, B-003).

### T-GP-02 – Gunplay (pistol)
- **Agent:** Bot 3 · **Deps:** T-GP-01 · **Status:** COMPLETED (2026-11-22, accepted by Bot 1 at handoff: merged with green `Tests/run_all.sh`) – was READY FOR REVIEW (2026-11-22, Bot 3, branch `bot3/t-gp-02`)
- **Description:** weapon resource (`WeaponData.tres`: damage, RPM, mag 12, reload 1.6 s, spread, recoil pattern), hitscan from camera with muzzle correction, recoil + camera kick, hit markers, damage/health component, ragdoll-lite hit reaction, muzzle flash + impact decals (placeholder FX OK).
- **Acceptance:** headless test: 12 shots then reload; damage applied to a dummy target; no fire during reload.
- **Delivered (Bot 3, 2026-11-22):** `Scripts/combat/` (`WeaponData` resource, `Weapon`, `PlayerWeaponController`, `DamageReceiver`, `Hitbox` (layer 5, zones BODY/HEAD/LIMB), `DamageInfo`, `TargetDummy`); `Data/Weapons/WPN_Pistol_01.tres`; stand-in `Scenes/Weapons/PT_Pistol.tscn` on `Visual/PT_SOCKET_RightHand_Weapon` (moves to the model's `SOCKET_RightHand_Weapon` via `attach_to_model_socket()`); camera recoil kick + exponential recovery in `CameraRig`; hitscan along the crosshair ray (mask World|Vehicles|Hitboxes) + muzzle-line correction; spread cone (aim/hip, crouch, moving, airborne, bloom); hitmarker signal + data, pooled PT impact decals (32), muzzle flash; target dummies + backstop in `PT_PlayerTestRange` (lane at x≈25).
- **Verified:** `GodotProject/Tests/test_weapon.gd` (57 checks): ammo, semi/auto fire rate, empty mag → auto-reload (1.6 s), no fire during empty reload, interruptible reload (fire with rounds left / sprint), dry fire, body 25 / head 50 / leg 18.75 dmg, falloff at 35 m, kill + world hit, spread ordering + bloom, recoil kick + recovery, other `.tres` changes behaviour, socket re-attach. Negative check (falloff disabled + cooldown removed) → 7 failures, exit 1.
- **Tuning defaults (not in GDD/M01) – ACCEPTED by Bot 1 (2026-11-22) as starting values, stay data-driven; reload interruption accepted:** RPM 300 (semi), damage 25, head ×2.0, limb ×0.75, falloff 15→40 m down to ×0.5, reserve 60, spread hip 2.0° / aim 0.6°, crouch ×0.7, moving +2.5° (half when aiming), airborne +5°, bloom +0.8°/shot (max 4°, recovers 6°/s; stacking fixed in T-GP-02a), recoil 2.2° up / ±0.6° yaw, aim ×0.7, recovery 8/s; reload interruptible by firing (rounds left) and by sprint, no fire while sprinting; dummy 100 HP. Values marked `[DEFAULT]` in the `.tres`.
- **Not in this task:** ragdoll-lite hit reaction (only death tilt on the PT dummy) → **T-GP-02b**; hitboxes on SK_Jason/NPCs (with T-AI-01); HUD crosshair/ammo/hitmarker visuals (T-UI-01).
- **Asset requirement for Bot 2 – REQ-GP02-PISTOL:** `Docs/Handoffs/REQ_WPN_Pistol_01.md` (extends T-ART-05 + T-ART-02): `WPN_Pistol_01.glb` + manifest, ~0.19 m, origin at grip, barrel +Z, separate `Slide` + `Magazine` nodes, `SOCKET_Muzzle/Eject/Grip`, ≤ 8k tris, LOD1/2 via uwp, weapon clips Fire/Reload (1.6 s)/Empty, Jason clips Shoot_Pistol (0.25 s), Reload_Pistol (1.6 s, mag-out/in frames in manifest), Hip_Pistol_Idle. **CONFIRMED by Bot 1 (2026-11-22).**

### T-GP-02a – Rapid-fire bloom
- **Agent:** Bot 3 · **Deps:** T-GP-02 · **Status:** COMPLETED (PR #4 merged, 2026-11-22; recovery-delay test made time-based in the T-AI-01 branch)
- **Description:** spread grows with rapid fire: +`bloom_per_shot` per shot up to `bloom_max`, recovery (`bloom_recovery` °/s) only after `bloom_recovery_delay`; aimed bloom scaled by `bloom_aim_multiplier` so aimed spread stays below hip fire. All in `WeaponData`.
- **Tuning defaults ([DEFAULT] in `WPN_Pistol_01.tres`):** `bloom_recovery_delay` 0.35 s (> 0.2 s fire interval at 300 RPM, so max-rate fire stacks), `bloom_aim_multiplier` 0.5. Resulting pistol: hip 2.0° → 6.0° after 5 rapid shots (cap), aimed 0.6° → 2.6°; full recovery 0.35 s + 0.67 s after the last shot.
- **Verified:** `test_weapon.gd` (68 checks): +0.8°/shot stacking to the cap after 5 shots, shots 6–8 stay at the cap, no recovery during the delay, recovery after it, full recovery, aimed < hip at every shot, aimed cap = 4.0 × 0.5. Negative check (delay removed) → 6 FAIL, exit 1.

### T-GP-02b – Ragdoll-lite hit reaction
- **Agent:** Bot 3 · **Deps:** T-GP-02, T-ART-01 · **Status:** BACKLOG (P2, added 2026-11-22 per Bot 1)
- **Description:** short procedural hit reaction (upper-body flinch / partial physical bones on the hit bone) and death collapse for SK_Jason/NPC skeletons, driven by `DamageReceiver.damaged/died` (`DamageInfo.zone`, direction). Currently only the PT dummy tilts on death.
- **Acceptance:** headless test: hit applies an impulse/flinch to the hit zone's bones and settles; death collapses without falling through the floor.

### T-GP-01c-J – Player visual: capsule → SK_Jason v2
- **Agent:** Bot 3 · **Deps:** T-GP-01, T-ART-02 · **Status:** COMPLETED (2026-11-22, accepted by Bot 1 at handoff: merged with green `Tests/run_all.sh`) – was READY FOR REVIEW (Bot 3, 2026-11-22, branch `bot3/t-gp-01c-jason`)
- **Delivered:** `Player.tscn` → `Visual.model_scene = Assets/Characters/SK_Jason/SK_Jason.glb` (PT capsule + front marker hidden, collision unchanged = TD-011 cylinder, controller untouched). `CharacterVisual.CLIP_NAMES`: `jump_loop` → `A_Jason_Jump_Air` (all 14 slots verified against the imported glb); per-instance `clip_names`, `validate_clips()`, `model_changing/model_changed` signals, auto-built AnimationTree rebuilt on model swap. `PlayerWeaponController` moves the pistol onto `SOCKET_RightHand_Weapon` (BoneAttachment3D RightHand) automatically and back to the PT socket before a model swap.
- **Verified:** `test_player_controller.gd` new block (SK_Jason): model + 53-bone skeleton, all mapped clips exist, loop modes from manifest, manifest speeds = CLIP_SPEEDS = controller speeds, height 1.833 m vs 1.8 m collision, feet at y 0 (idle toes 0.03 m, ankles 0.10 m), head bone 1.66 m, weapon on the hand socket (0.055 m from RightHand), AnimationTree idle/walk 1.4/run 3.5/sprint 6.0/jump (OneShot + Jump_Air)/land/aim states, skeleton pose actually changes (LeftUpperLeg 9.3° idle→run), in-place clips. Negative control: `A_Jason_Jump_Loop` reported (missing + _Loop suffix); `UW_JASON_SABOTAGE=1` → 3 FAIL, exit 1. `test_weapon.gd` updated (weapon on SK_Jason socket, muzzle height).
- **Not verified / open:** look of the animations and blends, foot sliding, weapon orientation in the hand (no GPU, B-003); hitboxes are still the PT capsule-shaped boxes under `Visual/Hitboxes` (move to BoneAttachment3D, REQ-AI01-NPC); no aim-offset/upper-body layering (aim blend is full-body); Shoot/Reload/Carry/Death/Car_Enter/Exit clips exist but are not wired yet.

### T-GP-03 – Vehicle physics + enter/exit
- **Agent:** Bot 3 · **Deps:** T-GP-01 · **Status:** COMPLETED (2026-11-22, accepted by Bot 1 at handoff: merged with green `Tests/run_all.sh`) – was READY FOR REVIEW (Bot 3, 2026-11-22, branch `bot3/t-gp-03`)
- **Description:** `VehicleBody3D` with tuned suspension/grip for a heavy sedan, handbrake, chase camera, enter/exit at `SOCKET_Exit_Left`, engine audio pitch by RPM (placeholder sound OK).
- **Acceptance:** headless test: throttle 3 s → speed > 8 m/s; brake to < 0.5 m/s; enter/exit toggles player control.
- **Delivered (Bot 3, 2026-11-22):** `Scripts/vehicle/vehicle.gd` (`Vehicle`, VehicleBody3D, **TD-014 ACCEPTED**) + `vehicle_data.gd` (`VehicleData`), `Data/Vehicles/VH_Sedan_01.tres` (all tuning `[DEFAULT]`: 1450 kg, RWD, 6500 N, 38 m/s top, speed-dependent rate-limited steering 35°→8°, handbrake drift slip, drag + rolling resistance, reverse), `Scenes/Vehicles/VH_Sedan_01.tscn` on the **real VH_Sedan_01.glb** (no PT_ car): wheels/UCX collision/doors/sockets wired by node name at runtime; asset wheel meshes spin + steer from the physics wheels; doors swing on their hinge pivots (`open_door/close_door`, `door_changed`); chase camera (smoothed, look-ahead, FOV widens with speed); crash damage (`crashed`, `wrecked` → engine off); engine pitch from a gear sawtooth (`engine_pitch`, optional `EngineAudio` node, no sound file yet). Enter/exit: F / gamepad Y within 2.5 m of an exit socket → driver door opens, player hidden + out of physics on `SOCKET_Seat_Driver`; exit ≤ 2 m/s at `SOCKET_Exit_Left`, `SOCKET_Exit_Right` if blocked, `exit_blocked` if both are. New input actions `vehicle_accelerate` (W/RT), `vehicle_brake` (S/LT), `vehicle_handbrake` (Space/RB) in `setup_input_map.gd`. `PlayerController`: `try_enter_vehicle()`, `set_in_vehicle()`, `leave_vehicle()`. Test range `Scenes/Test/PT_VehicleTestRange.tscn` (400 m floor, sedan, player, crash wall).
- **Verified:** `GodotProject/Tests/test_vehicle.gd` (88 checks, in `run_gameplay_tests.sh`): asset contract on the imported scene (4 wheels r 0.34, wheelbase 2.86, track 1.58, UCX hull = body collision, StaticBody removed, underside 0.34 m, exit sockets outside hull, 4 doors, 8 sockets, LHD seat); parked on the floor ±1 cm, wheels drawn at asset positions ±1 cm, no creep; doors swing outward around fixed hinges and close back; enter too far = nothing; enter via the real input map (door opens/closes, hidden, collision off, chase cam, seat); **throttle 3 s → 11.1 m/s** (> 8), wheels spin, camera behind; **brake 11.1 → < 0.5 m/s in 2.0 s (10.9 m)**; steer left/right (yaw ±, front wheels steer, rears straight); no exit at speed; **exit places the player at SOCKET_Exit_Left (< 5 cm)**, control/collision/camera back, walks on; left blocked → right exit; both blocked → stays in; wall crash → damage, no tunnelling; never below the floor. Negative controls in the suite: wheel_radius 0.30 is reported, 15 % engine fails the 3 s criterion. Sabotage runs (`UW_VEHICLE_SABOTAGE=1` → 9 FAIL, `=2` → 22 FAIL, exit 1). Deterministic (2 identical runs). `Tests/run_all.sh` → RUN_ALL: PASS.
- **Not in this task / open:** driving feel, camera framing and visuals unverified (no GPU, B-003); enter/exit is timed (0.6 / 0.5 s), clips `A_Humanoid_Car_Enter_L/Exit_L` come with the Jason swap; no passenger / carjacking / NPC drivers; NPCs don't treat a seated player differently; no ram damage to characters yet; no engine sound asset; headlights not lit (sockets found). REQ to the art pipeline: `Docs/Handoffs/REQ_VEH_Sedan_01.md` (**CONFIRMED**, 4 non-blocking CRs).

### T-AI-01 – Enemy AI (cartel gunmen)
- **Agent:** Bot 3 · **Deps:** T-GP-02 · **Status:** COMPLETED (PR #6 merged by Bot 1, 2026-11-22)
- **Description:** state machine Idle → Alert → Engage → Take cover (pre-placed `CoverPoint` nodes) → Flank-lite → Dead; `NavigationAgent3D`; line-of-sight perception + hearing gunshots; accuracy falloff by distance/movement.
- **Acceptance:** headless test: 3 gunmen detect player within 2 s of LOS, deal damage, die after enough hits.
- **Delivered (Bot 3, 2026-11-22):** `Scripts/ai/`: `NPCController` (CharacterBody3D, layer 3, cylinder; NavigationAgent3D movement; states idle/patrol, alert, investigate, engage, take_cover, in_cover (hide ↔ peek + shoot), search, flee, dead), `AIStateMachine` (transition table + timeouts **from the AIProfile .tres**, validator), `AIProfile` (Resource: table, speeds, perception, accuracy, cover, flee), `AIPerception` (pure math: view cone, awareness rate, hearing, aim error, cover score; `emit_noise` → group `ai_hearing`), `CoverPoint` (Marker3D, runtime protection + peek raycasts, claiming), `NPCRoute`. Perception = view cone (120°, 35 m) + LOS raycast (World|Vehicles) to head/chest + 2.5 m near awareness; awareness meter (0.4 s near → 1.6 s at 35 m, ×2 once alerted); hearing gunshots (`WeaponData.noise_radius` 40 m – ACCEPTED [DEFAULT] by Bot 1, capped by `hearing_range`). Shooting via the T-GP-02 `Weapon` + `WPN_Pistol_01.tres` with AI aim error (4° + 3° moving target + 0.5°/10 m, ×0.5 with 2 s focus) on top of hip spread; bursts 2–3, reaction 0.35 s. `HumanoidHitboxes` (head/body/legs/2 arms → DamageReceiver) on NPCs **and the player** (player now has `Health`, dies → input off; own shots/crosshair exclude own hitboxes). Data: `Data/AI/AI_Gunman_Cartel.tres`, `AI_Civilian.tres`; PT scenes `Scenes/NPC/PT_NPC_Gunman.tscn`, `PT_NPC_Civilian.tscn` (`Scripts/tools/build_npc_scenes.gd`); `PT_PlayerTestRange` gets 3 low cover walls, 7 CoverPoints (1 decoy on the wrong side) and `PT_NavRegion` (navmesh baked headless in `build_test_range.gd`); new `Scenes/Test/PT_AITestRange.tscn` = range + 3 gunmen + 3 civilians on 2 routes.
- **Verified:** `GodotProject/Tests/test_ai.gd` (80 checks): L1 view cone/awareness/hearing/aim-error math; L2 state machine + all profile tables validated; L3 in PT_AITestRange: 3 gunmen detect the player in 0.57 s (≤ 2 s), crouched behind cover not seen / seen on standing up, view cone + near radius, hearing → alert → investigate (56 m shot not heard), cover choice rejects the decoy, hide blocks a head shot, peek + shoot, flanked → leaves cover, gunmen damage the player (AI mean error 2.8° vs player 0.6° aimed, misses), moving target → larger AI error (designer-blind strafe run), gunman reacts to damage and dies after 4 body hits (collision/hitboxes off, stops listening), shared .tres / independent runtime state, civilians walk routes + idle at points + flee from a shot ≤ 25 m (not at > 25 m) + calm down and resume, a different profile table (`Tests/Data/PT_AI_Coward.tres`) changes behaviour. Deterministic (fixed seeds, 3 identical runs). Negative check (LOS mask 0 + awareness ×0.2) → 14 FAIL, exit 1.
- **Not in this task / open:** flank-lite (only "leave compromised cover / relocate after 2 empty peeks"); no NPC-vs-NPC targeting (enemies only target the player; Marco ally = T-MIS-01); NPCs don't avoid each other (no RVO avoidance) and use straight cylinder bodies; crouch = PT pose drop (real anims REQ-AI01-NPC); visual check needs a GPU.
- **Asset requirement for Bot 2 – REQ-AI01-NPC:** `Docs/Handoffs/REQ_NPC_Characters.md` (extends T-ART-06): `SK_NPC_Cartel_Gunman` (2+ variants), `SK_NPC_Civilian_A/B` + new `SK_NPC_Civilian_C` (variant OK), ≤ 25k tris, Jason's skeleton, +Z front, origin at feet, `SOCKET_RightHand_Weapon`, hitbox bones, clip list for cover crouch (head ≤ 1.1 m) / peek-aim / shoot / reload 1.6 s / flee / cower / look-around / hit-react / death. **ACCEPTED by Bot 1 (2026-11-22) – delivery: art cloud agent, after Jason v2.**

### T-AI-02 – Civilian NPC behaviour
- **Agent:** Bot 3 · **Status:** BACKLOG
- **Note (Bot 3, 2026-11-22):** baseline behaviour (route walk + idle at points, flee from gunshots ≤ 25 m, calm down after 8 s, cower if cornered) delivered with T-AI-01 (`AI_Civilian.tres`, 3 PT civilians in `PT_AITestRange`, tested). Remaining: placement on Calloway Ave (T-LVL-01), real models (REQ-AI01-NPC).
- **Description:** sidewalk wander along path nodes, idle at points, flee/cower on gunfire.
- **Acceptance:** ≥ 3 civilians on Calloway Ave; flee when a shot is fired within 25 m.

### T-LVL-01a – Greybox lesbar (T-LVL-01, Teil 1)
- **Agent:** Bot 3 · **Status:** COMPLETED (2026-11-22, TD-018) · **Verified:** `Tests/test_level.gd` (20 checks): no `@` auto-names, no unused `ext_resource`, buildings/garage/navmesh really in the file, luminance road 0.15 / sidewalk 0.60 / kerb 0.78, navmesh probes on road + both sidewalks + both ends, 44-waypoint walk across the whole block with real input. Negative check `UW_LEVEL_SABOTAGE=1` → 1 FAIL. Found and fixed five silent bugs (missing buildings, unpainted kit materials, dropped surface overrides, unbaked navmesh, a civilian route crossing the roadway and stalling the M01 drive).
- **Honest limit:** still a blockout – grey boxes, no art pass. No in-engine Phase-8 capture is possible on this box (no X server/Xvfb, no GPU).

### T-LVL-01 – Assemble LA street level
- **Agent:** Bot 3 (with Bot 2 kit) · **Deps:** T-ART-03 · **Status:** IN PROGRESS
- **Note (Bot 1, 2026-11-23):** `LA_CallowayAve.tscn` is generated by `Scripts/tools/build_level_calloway.gd` (PR #14): 132 real sub-scene instances, navmesh region, mission areas. Phase 8 capture (llvmpipe) shows a blockout: overexposed near-white ground, roads/sidewalks not readable, box buildings, 116 street pieces with auto-names `@Node3D@NN`, unused `ext_resource` entries. Walking/driving the whole street is not tested yet.
- **Description:** `GodotProject/Scenes/Levels/LA_CallowayAve.tscn` per layout brief; NavMesh baked; lighting (golden-hour sun, sky), occluders.
- **Acceptance:** player can walk whole street; navmesh covers sidewalks/road; no missing references.

### T-MIS-01 – Mission system + M01 implementation
- **Agent:** Claude Code (external, PR #14, PR #17) · **Deps:** T-DES-01, T-GP-02, T-GP-03, T-AI-01 · **Status:** COMPLETED (gameplay, headless)
- **Review Bot 1 of PR #17 (2026-11-23):** Marco seated + invulnerable, waves sequenced 3 → 2, real input drive (26.2 s / 97.2 m / 0.00 m off-road), `test_mission.gd` 105 → 109 checks; sabotage 1/2/3 → 5/2/2 FAIL. Defect fixed forward: Marco was drawn standing through the car roof (no sit clip) → hidden while seated + test. Defect fixed forward: nothing started the mission outside tests and the export booted the PT crate scene → `Game_M01.tscn` + `test_boot.gd` (TD-020). Not done: optional chase car (step 6 stretch), audio, Marco sit clip.
- **Review Bot 1 (2026-11-23):** framework (`Scripts/mission/*`, `Data/Missions/M01_DeadDrop.tres`, 8 objectives, 2 checkpoints, fail/restart for Jason dead / package destroyed / package left > 60 m / sedan destroyed) is real and tested: `test_mission.gd` 75 checks PASS on a fresh worktree. PR #14 was self-merged by the agent and committed 106 binaries without LFS → fixed forward in PR #15. Its negative control was tautological (it only failed its own self-check) → replaced in PR #16 by real sabotage (checkpoint removed + stray distance disabled → 5 real checks FAIL).
- **Still open (not done, do not claim):** Marco ally (only a `Marco_Seat` marker exists – design wants him in the passenger seat and fighting, invulnerable); ambush waves are not sequenced (all 5 enemies are in the level from the start, one SURVIVE objective; design: 3, then 2 from the van); the test teleports the car into the trigger areas instead of driving the ~300 m loop; no HUD assertions; no Phase 8 capture of the mission.
- **Description:** data-driven mission framework (objectives, triggers/areas, markers, fail/retry, checkpoints) and M01 per `Docs/Missions/M01_DeadDrop.md`.
- **Acceptance:** M01 playable start→finish; fail states (Jason dies, package destroyed, car destroyed) restart from checkpoint; headless test steps through objectives via debug API.

### T-UI-01 – HUD
- **Agent:** Bot 3 → Claude Code (PR #17) · **Status:** COMPLETED · health, ammo, crosshair, objective text, subtitles, GPS marker, mission passed/failed card; `test_hud.gd` 40 checks, `UW_HUD_SABOTAGE=1` → 3 FAIL. Verified by Bot 1 on a fresh worktree 2026-11-23.

### T-BUILD-01 – Playable Linux build
- **Agent:** Bot 3 · **Deps:** T-PIPE-02 · **Status:** COMPLETED (2026-11-22)
- **Description:** install ONLY Linux export templates (disk!), `GodotProject/export_presets.cfg`, `Tools/build/build_linux.sh` (Bot 3 owns `Tools/build/`) → `Builds/linux/Underworld.x86_64`.
- **Acceptance:** build exits 0; binary runs `--headless --quit-after 300` without errors; size documented.
- **Result (`Docs/BUILD.md`):** exit 0; 79 MB binary + 189 MB PCK, 657 files, `Tests/` and `Scripts/import/` excluded (verified by parsing the PCK); smoke run logs only the engine banner. The template was **built from source** here (official `.tpz` host unreachable) with `vulkan=no opengl3=no`, so it proves boot/logic, **not** presentation — a desktop-playable build needs a Vulkan-enabled template.
- **Honest limit:** nobody has *played* this build on a GPU machine yet.

### T-QA-01 – Headless regression suite
- **Agent:** Bot 3 · **Status:** BACKLOG · `Tests/run_all.sh` runs pipeline smoke + all gameplay tests; required to pass before merging to `main`.

### T-QA-02 – Binding AAA Quality Gate
- **Agent:** Bot 1 · **Pri:** P0 · **Deps:** T-PIPE-04, owner prompt 2026-11-22 · **Status:** COMPLETED (2026-11-22)
- **Expected output:** `Docs/QUALITY_GATE.md`, `Docs/Reviews/TEMPLATE_ASSET_REVIEW.md`, first reviews for SK_Jason v2, SK_NPC_Sam, WPN_Pistol_01, VH_Sedan_01, LA kit, `Tools/uwp review-sheet`, Phase 8 capture notes (`Tools/godot_phase8_capture.sh`).
- **Acceptance:** gate adapted to Godot 4.7 (not Unreal); Phase 8 = in-engine capture under xvfb + llvmpipe / opengl3; independent review roles documented; scores 0–5 with pass ≥ 4 all applicable; first reviews are honest (all REJECT / not PRODUCTION-READY); `Tests/run_all.sh` PASS.
