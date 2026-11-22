# UNDERWORLD – AAA Quality Gate

**Binding production rule.** A successful script or a finished model is not a production-ready game asset. Never accept a mediocre first pass as final. Never call an asset “AAA” merely because it was generated.

This document adapts the owner’s Quality Gate to our stack (TD-001): **Godot 4.7.2**, headless Blender 5.2.4 LTS, **no GPU on the box**. Phase 8 is Godot integration under gameplay lighting and camera, not Unreal.

Owner: Bot 1 (art direction and gate verdict). Creators: Bot 2 / Lead TD. Engine review: Bot 3.

## 1. Reference-first production

Before modelling any important asset:

1. Research visual references (photo, film stills, concept art, turnarounds).
2. Establish how the asset fits the single UNDERWORLD look (grounded, photoreal-leaning crime drama).
3. Define realistic proportions and dimensions in metres.
4. Define the target quality and which details must be reproduced.
5. Create a **reference board** at `Docs/ArtDirection/References/<asset>/`.
6. Record every source and its license in `SOURCES.md` in that folder (CC0 / CC-BY / original concept only; no unlicensed scrapes).

Never model a complex asset from a vague description alone. Jason’s binding concepts already live at `Docs/ArtDirection/Concepts/` and are listed from `References/SK_Jason/SOURCES.md`.

`Tools/uwp review-sheet <asset>` builds a reference-versus-render contact sheet (system Python / Pillow, no Blender). Commit the sheet with the review.

## 2. Mandatory production cycles

Every important asset (hero characters, hero vehicles, hero weapons, hero environment kits) must pass these stages. Blockout kits may stop at Phase 1 only if the registry status stays `WIP` and the review says so.

| Phase | Name | What “done” means |
|---|---|---|
| 1 | Blockout | Proportions, silhouette and scale established. Registry: `WIP`. |
| 2 | High-quality modelling | Topology, geometry, surface detail. |
| 3 | Materials | Realistic PBR (albedo, roughness, metallic, normal, variation). |
| 4 | Lighting and rendering | Professional preview renders from several angles (headless Blender, **Cycles CPU**; Workbench is not evidence for a hero asset). |
| 5 | Independent visual review | Another agent inspects the **actual renders**, compares them to the approved references, and lists defects. The creator is never the sole reviewer. |
| 6 | Refinement | Fix every listed defect. Re-render and re-review. Repeat until the scores pass or the work is honestly parked. |
| 7 | Game-ready validation | Geometry, UVs, topology, materials, LODs, collision, skeletons, naming (TD-005), budgets (`Config/asset_budgets.json`). `Tools/uwp validate` / `export` must PASS. |
| 8 | Godot integration | Import into Godot 4.7 and inspect under **gameplay lighting and camera**. Only then may the asset be marked `PRODUCTION-READY`. |

### Phase 8 capture method (this box)

There is no GPU. Forward Plus (the project default, Vulkan) cannot be captured here: no lavapipe / software-Vulkan ICD is installed.

In-engine screenshots **do work** with software OpenGL. Proven 2026-11-22 on this box with Godot 4.7.2:

```
LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe \
  xvfb-run -a -s "-screen 0 1920x1080x24" \
  /workspace/tools/godot --path GodotProject \
  --display-driver x11 --rendering-driver opengl3 --rendering-method gl_compatibility \
  res://<scene or look-dev>
```

Verified result: Mesa 25 llvmpipe (OpenGL 4.5 Core), a real 3D frame with lit meshes (red box + green ground), not a black dummy framebuffer. `--headless` is for tests and import only; it is not the Phase 8 capture path.

Helper: `Tools/godot_phase8_capture.sh`. Because the renderer is forced to `gl_compatibility`, lighting will not match shipping Forward Plus. Say so on the review. Use the shot for scale, silhouette, materials, clipping and camera framing.

Sods2/godot-mcp can also screenshot a running game, but only after its editor plugin is installed and a GUI editor is up (see `/workspace/tools/skills-vendor/README.md`). Do **not** install that plugin or start that MCP server unless Bot 1 and Bot 3 agree. Prefer the script above for the gate.

## 3. Independent review

The agent that creates an asset must not be its only reviewer.

| Role | Responsibility |
|---|---|
| Bot 2 / Lead TD | Creates the asset, runs Phases 1–4 and 7, attaches renders and a review sheet. |
| Bot 1 | Art review: references, silhouette, proportions, materials, detail, visual consistency. **Must reject** anything that misses the established direction. |
| Bot 3 | Technical / engine review: scale, import, materials in-engine, LODs, collision, skeletons, performance, Phase 8 capture. **Must reject** broken integration, bad scale, missing materials or budget violations. |

Use `Docs/Reviews/TEMPLATE_ASSET_REVIEW.md`. File reviews at `Docs/Reviews/YYYY-MM-DD_<asset>.md`. If Bot 1 also rebuilt an asset (recovery work), say so; Bot 2 still owes an independent art pass before any `PRODUCTION-READY` mark, and Bot 3 still owes the engine review. A director REJECT of one’s own recovery work is allowed and expected when the pixels fail the bar.

## 4. Scoring

Score every important asset from **0 to 5** in each applicable category:

* Silhouette
* Proportions
* Geometry
* Materials
* Textures
* Lighting
* Visual detail
* Animation quality
* Technical optimization
* Engine integration (Godot, not Unreal)

**Pass = at least 4/5 in every applicable category.** A single 3 fails the gate.

Never manipulate scores to approve an asset. Document remaining limitations honestly. `N/A` is allowed only when the category does not apply (for example animation on a static curb). Do not use `N/A` to dodge a weak area.

Registry and task language:

* Asset registry status `PRODUCTION-READY` is used **only** after this gate passes (Bot 1 art + Bot 3 engine, all applicable scores ≥ 4, Phases 1–8 done, renders + reference comparison + `uwp` validation + in-engine capture attached).
* Task-board `COMPLETED` on an art task means the *work item* was delivered and reviewed, not that the asset is production-ready.
* Do not write “FINAL” or “AAA quality” on an asset that has not passed.

## 5. Character checklist

For Jason, Sam and every important character:

* Realistic human proportions
* Detailed facial structure
* High-quality skin materials
* Natural hair (not a plastic shell)
* Detailed clothing with realistic folds and fabric
* Correct hands and fingers
* Proper topology and high-quality rigging
* Natural animations
* Consistent appearance from every camera angle
* Convincing in close-ups **and** in normal gameplay

## 6. Vehicle checklist

Every major vehicle:

* Convincing body proportions
* Detailed exterior geometry
* Proper windows (real glass, not a dark plane)
* Realistic tires and wheels
* Detailed headlights and taillights
* High-quality paint materials
* Interior geometry
* Working doors and other moving parts
* Correct collisions, suitable LODs
* High-quality Godot integration (sockets, wheel pivots, enter/exit)

## 7. Environment checklist

Every important street must feel like a believable real location:

* Architectural variation and detailed façades
* Sidewalks, street furniture, signs, traffic lights
* Vegetation, road markings, realistic lighting
* Environmental storytelling
* Appropriate NPC and traffic density (when the level is dressed)
* No repetitive boxes and empty streets presented as finished

## 8. Visual consistency

The whole game follows one coherent visual identity. Jason, Sam, NPCs, cars, weapons and environments must belong to the same world. Never combine unrelated art styles.

## 9. Final rule

Never say “AAA quality” merely because the asset has been generated.

Prove quality with actual renders, reference comparisons, technical validation and an in-engine test. Reject, improve and repeat whenever necessary.

The goal is not to generate assets quickly. The goal is to produce assets that genuinely deserve to be part of UNDERWORLD – THE AMERICAN DREAM.
