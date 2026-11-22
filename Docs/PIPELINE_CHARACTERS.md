# UNDERWORLD Character Pipeline (`T-PIPE-03`)

Owner: Lead Tech Artist / Pipeline TD.  
Engine target: **Godot 4.7.x** (`SkeletonProfileHumanoid`, glTF 2.0 `.glb`, `StandardMaterial3D` PBR + SSS).  
DCC: **Blender 5.2 LTS** headless via `bpy` (`Tools/underworld_pipeline/characters/` + `Tools/uwp`).

---

## 1. Architecture Overview

Characters are generated reproducibly from declarative JSON/YAML spec files in `Config/Characters/<AssetName>.json` (no primitive-based stickmen, no manual hand-edits to generated `.blend` files).

```
Config/Characters/SK_<Name>.json
        │
        ▼
Tools/underworld_pipeline/fetch_sources.py   (caches verified CC0 sources in .cache/uwp_sources/)
        │
        ▼
Tools/underworld_pipeline/characters/build_character.py
  ├── mh_loader.py      CC0 MakeHuman hm08 base + 1,258 macro/face morphs + 20 ARKit/viseme blendshapes
  │                     + .mhclo barycentric binding (eyes, eyebrows, eyelashes, teeth) + 53-bone humanoid rig
  ├── clothing.py       Body-fitted separate garment meshes in A-pose (t-shirt, jacket, jeans, boots, watch)
  │                     + region-isolated artist weight transfer + occluded-body culling + Cycles hi-to-lo bake
  ├── hair_beard.py     Sculpted textured crop + hairline wisps + blendshape-bound feathered 3D beard shell
  ├── pbr_textures.py   2K hero skin PBR (CC0 photo skin + 3D-baked fade, beard stubble, scar) + 1K garment PBR
  │                     (Cycles baked Normal/AO + CC0 Poly Haven textures via RNM blending) + Godot SSS/ORM
  ├── retarget.py       CC0 BVH mocap parser & retargeter (MakeHuman CC0 walk1.bvh -> humanoid rig)
  └── animations.py     21 in-place 30 fps animations (REQ-GP01-JASON + TD-005, < 5 cm foot sliding,
                        two-handed pistol grip, SOCKET_RightHand_Weapon aligned +Y up / +Z barrel)
        │
        ▼
Blender/Source/Characters/<Name>/<Name>.blend
        │
        ▼
Tools/uwp export Blender/Source/Characters/<Name>/<Name>.blend
  ├── Quality gates: poly/texture/material budgets, non-manifold, degenerate faces, UV overlap,
  │                  texel density, <=4 influences, weight normalization (1.0 ± 0.02), layered
  │                  clothing clipping check, 22 mandatory humanoid bones, TD-004 front/origin/height,
  │                  TD-005 naming (incl. NAME_ACTION_LOOP), weapon socket verification
  ├── glTF 2.0 (.glb) export + Blender round-trip verify
  ├── Cycles CPU denoised multi-view previews (front, 3/4, side, back, face, face_side, aim)
  └── Automated silhouette & proportion comparison vs concept art turnaround (<Name>.silhouette_report.json)
        │
        ▼
Assets/Characters/<Name>/<Name>.glb (+ .manifest.json, .validation.json, .silhouette_report.json, previews)
```

---

## 2. Quick Start: Building & Exporting a Character

### Step 1: Ensure CC0 source cache is populated (once per machine)
```bash
python3 Tools/underworld_pipeline/fetch_sources.py --groups characters,textures,mocap
```
Raw downloads stay in `.cache/uwp_sources/` (gitignored; never committed to Git LFS).

### Step 2: Build the source `.blend` from a character spec
```bash
/workspace/tools/blender/blender -b --factory-startup --python-exit-code 1 \
  --python Tools/underworld_pipeline/characters/build_character.py -- \
  --spec Config/Characters/SK_Jason.json
```

### Step 3: Validate, export `.glb`, render multi-view Cycles previews, and run silhouette check
```bash
Tools/uwp export Blender/Source/Characters/SK_Jason/SK_Jason.blend
```

### Step 4: Verify in Godot 4.7.2 headless + full regression gate
```bash
Blender/Scripts/sk_jason/verify_sk_jason.sh
./Tests/run_all.sh
```

---

## 3. Creating a New Character (Sam, Cartel Gunmen, Cops, Civilians)

Copy `Config/Characters/SK_Jason.json` to `Config/Characters/SK_NPC_<Role>.json` and adjust only the parameters needed:

| Section | Key Fields | Example Variations |
|---|---|---|
| Identity & Budget | `asset_name`, `budget_key` (`Characters/SK_NPC` -> 25k tris), `height_m` | Sam: `1.78`, Heavy Gunman: `1.85`, Female Jogger: `1.68` |
| `macro` | `gender` (`0.0` F – `1.0` M), `age` (`0.50` ~25y, `0.62` ~40y, `0.78` ~60y), `muscle`, `weight`, `proportions`, `ethnicity` (`caucasian`/`asian`/`african`) | Sam: `age: 0.78, weight: 0.76, muscle: 0.42`; Civilian Female: `gender: 0.0, age: 0.52, weight: 0.42` |
| `morphs` | Any MakeHuman `target.json` slider (`chin-bones-decr-incr`, `head-rectangular`, `cheek-bones-decr-incr`, `nose-width1-decr-incr`, `mouth-lowerlip-height-decr-incr`, etc.) | Distinct nose/jaw/cheek silhouettes per NPC |
| `skin` | `texture_size` (`2048` hero, `1024` NPC), `base_diffuse` (from `skins02`/`skins01`/`makehuman_system_assets`), `tint_rgb`, `skin_fade`, `beard_stubble`, `eyebrow_scar` | Disable `eyebrow_scar` & `beard_stubble` for clean-shaven/female NPCs; pick dark/light/older skins |
| `hair` & `beard` | `hair.style` (`skin_fade_crop`, `short_combed`, `buzz_cut`, `medium_crop`, or MakeHuman `.mhclo` hair), `hair.color_rgb`; `beard.style` (`short_boxed_beard`, `stubble`, `full_beard`, `goatee`, `none`) | Sam: `short_combed`, grey-tinted `[0.35, 0.34, 0.33]`; Cartel: `buzz_cut` + `goatee` |
| `outfit` | Toggle & theme `tshirt`, `jacket`, `jeans`, `boots`, `watch` with any CC0 Poly Haven `polyhaven_id`, `tint_rgb`, `desaturate`, `zone_mode`, `texture_size` | Swap jacket/pants colors & fabrics; set `jacket.enabled: false` for t-shirt/shirt-only civilians |
| `animations` | `clip_prefix` (`A_Jason_` or `A_Humanoid_`), `mocap_walk_bvh`, `include_p2` | NPCs share the identical 53-bone `SkeletonProfileHumanoid` skeleton and can play shared `A_Humanoid_*` / `A_Jason_*` clips |

---

## 4. Rig, Weights, Facial Blendshapes & Animation Contract

- **Skeleton (53 bones, exact `REQ-GP01-JASON` contract)**: `Root` (origin, untranslated) → `Hips` → 22 mandatory `SkeletonProfileHumanoid` bones + 30 finger bones (`ThumbMetacarpal/Proximal/Distal`, `Index/Middle/Ring/Little Proximal/Intermediate/Distal`).
- **Weights**: Loaded from MakeHuman CC0 artist-painted `weights.game_engine.json` (53:53 exact bone match), transferred to clothing with strict anatomical bone-region isolation (`GARMENT_ALLOWED_BONES`), smoothed at joints, capped at ≤ 4 influences per vertex, and normalized to `1.0 ± 0.02` (enforced by `uwp`).
- **Facial Blendshapes (20 Shape Keys exported via glTF morph targets)**:
  - Expressions (ARKit names): `eyeBlinkLeft`, `eyeBlinkRight`, `browDownLeft`, `browDownRight`, `browInnerUp`, `mouthSmileLeft`, `mouthSmileRight`, `mouthFrownLeft`, `mouthFrownRight`, `jawOpen`, `noseSneerLeft`, `noseSneerRight`, `cheekSquintLeft`, `cheekSquintRight`.
  - Lip-sync Visemes: `viseme_aa`, `viseme_E`, `viseme_I`, `viseme_O`, `viseme_U`, `viseme_PP`, `viseme_FF`, `viseme_SS`.
  - Propagated synchronously onto eyebrows, eyelashes, beard, and lower teeth.
- **Socket**: `SOCKET_RightHand_Weapon` parented to bone `RightHand`, oriented Godot `+Y` up / `+Z` barrel forward (`dot = 1.000` in `A_Jason_Aim_Pistol_Idle`).
- **Animations**: 30 fps, frame 0 start, in-place (no root motion), all 21 clips from `REQ-GP01-JASON` (using `A_Jason_Jump_Air` per TD-005 addendum — no `_Loop` suffixes), loop flags stored in `.manifest.json` and applied on Godot import by `uw_post_import.gd`. Foot sliding verified `< 5 cm` per cycle.

---

## 5. Automated Quality Gates (`Tools/uwp`)

Every `Tools/uwp validate` / `export` run enforces:
1. **Poly & Texture Budgets**: `Config/asset_budgets.json` (`Characters/SK_Jason` ≤ 40k tris, `Characters/SK_NPC` ≤ 25k tris, hero textures ≤ 2048², default ≤ 1024²).
2. **Geometry Integrity**: 0 loose vertices/edges, non-manifold check, degenerate zero-area face check, applied transforms, TD-004 ground origin (`z = 0 ± 1 cm`), reference height (`1.82 ± 0.02 m`), `+Z` Godot front.
3. **UV Overlap & Texel Density**: 2D rasterized UV self-overlap check (`UV_OVERLAP`, skipping meshes tagged `uw_allow_uv_overlap` such as hair cards) and median `px/m` texel density report (`TEXEL_DENSITY`).
4. **Skinning & Rig Integrity**: 22 mandatory `SkeletonProfileHumanoid` bones, ≤ 4 influences per vertex, 0 unweighted vertices, exact deform weight normalization (`WEIGHT_UNNORMALIZED`, `1.0 ± 0.02`).
5. **Layered Clothing Clipping Check**: `BVHTree` penetration check (`MESH_CLIPPING`) between `*_Body`, `*_TShirt`, `*_Jeans`, `*_Boots`, and `*_Jacket` in rest pose.
6. **Multi-View Cycles CPU Renders + Concept Silhouette Match**: Renders denoised Cycles CPU `front`, `3q`, `side`, `back`, `face`, `face_side`, `aim` previews next to the `.glb` and compares `front` + `side` silhouettes & anatomical slice proportions against turnaround concept art (`<Name>.silhouette_report.json`).

---

## 6. Git LFS Budget Discipline

- Raw source packs (`.cache/uwp_sources/`) and high-poly bake intermediates are **never committed**.
- Hero skin albedo/ORM packed as high-quality JPEG (2048²), skin normal as 1024² PNG; clothing albedo/ORM as 1024² JPEG, clothing normals as 512²–1024² PNG.
- Resulting hero footprint: `SK_Jason.glb` ≈ 10.7 MB, `SK_Jason.blend` ≈ 9.2 MB, 8 preview PNGs ≈ 2.9 MB total (~23 MB combined, well within GitHub LFS 1 GB free tier).
