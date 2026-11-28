# UNDERWORLD Weapon Pipeline (`T-ART-05`)

Two generators:
- **Hero pistol** `Tools/uwp build-weapon <spec.json>` → `Tools/underworld_pipeline/weapons/` (this document): hard-surface high-poly + game low-poly from the same 2D profiles, Cycles CPU high-to-low bake.
- **Weapon grammar** `Tools/uwp build-weapons` → `props/weapons.py` (T-WPN-01, the 9 other weapons, see `Docs/Reports/BERICHT_T-WPN-01.md`).

## Usage (pistol)
```bash
Tools/uwp build-weapon Config/Weapons/WPN_Pistol_01.json          # ~2.5 min on 8 CPU cores (2048 px, 64 AO spp)
Tools/uwp export Blender/Source/Weapons/WPN_Pistol_01/WPN_Pistol_01.blend
UWP_WEAPON_FAST=1 Tools/uwp build-weapon <spec> --repo /tmp/scratch  # 512 px / 8 spp iteration build (~6 s), never commit
# review renders (Cycles CPU, same rig every pass; --clay = grey geometry check):
/workspace/tools/blender/blender -b <Weapon>.blend --python Tools/underworld_pipeline/weapons/render_review.py -- \
    --out-dir <dir> --views left,right,top,front,q3,q3r,q3back,low,serrations,stipple,backstrap,sights,port,muzzle,guard \
    --res 1200 --samples 48 --jpeg 90 [--clay] [--action A_WPN_Pistol_01_Reload --frame 20]
python3 Tools/underworld_pipeline/weapons/before_after_sheet.py     # v0 vs v1 sheet (repo root)
UW_CAPTURE_DIR=<dir> Tools/godot_phase8_capture.sh --res 1280x720 --fixed-fps 30 --script res://Tests/tools/capture_pistol.gd
```

## Modules
- `pistol_hs.py` – parts in contract coordinates; grip = superellipse loft (`GRIP_FRONT/GRIP_BACK/GRIP_HALF_W` tables measured on board tile R3, 20° rake); slide (27 mm, serrations as real geometry in HP and LP), barrel (flush crown, hood), frame (closed guard, rail, mag well, controls, pins), trigger, magazine.
- `hardsurface.py` – prism / loft / superellipse / boolean (optional material transfer) / bevel helpers; LP finishing (triangulated, hard edges > 30° = UV seams).
- `hs_materials.py` – HP bake shaders: black-nitride steel, barrel steel, polymer with object-space stipple zone, curvature edge wear, AO. `UW_GripSheet` tags the LP grip faces.
- `baker.py` – shared atlas (smart project; the tagged grip is re-unwrapped as ONE angle-based sheet, smooth inside, single seam down the front strap), selected-to-active bakes, D/N/ORM packing + dilation.
- `render_review.py` – product rig for dark guns (soft key, strip lights, dark floor), 15 fixed views, `--clay`, action/frame posing.
- `build_weapon.py` – flow + contract (sockets, rig, clips); clip key frames unchanged, easing per segment.

## Contract (`Docs/Handoffs/REQ_WPN_Pistol_01.md`, unchanged)
- **Origin & axes (TD-004)**: origin at the grip wrap point (`SOCKET_RightHand_Weapon`, zero offset); barrel Blender `-Y` → Godot `+Z`, up `+Z` → Godot `+Y`.
- **Nodes**: `Frame`, `Barrel` (static), `Slide`, `Magazine`, `Trigger` rigid-skinned to `WeaponRig` (`WpnRoot`, `SlideBone`, `MagBone`, `TrigBone`).
- **Sockets**: `SOCKET_Muzzle` (0, −0.165, 0.041 Blender = 0.165 m on +Z), `SOCKET_Eject`, `SOCKET_Grip`.
- **Clips (30 fps)**: `A_WPN_Pistol_01_Fire` (0.10 s), `A_WPN_Pistol_01_Reload` (1.60 s; mag out frame 9, seated frame 32), `A_WPN_Pistol_01_Empty` (slide locked back).
- **Output (v1, 2026-11-28)**: LOD0 5,814 tris (≤ 8,000), one material `M_WPN_Pistol_01`, D/N/ORM 2048² (`texture_size` in the spec; 1024 halves the 5.4 MB GLB), Frame/Barrel LOD1/LOD2, skinned parts via Godot import LODs, 64-vert convex `UCX_WPN_Pistol_01-convcolonly`.
