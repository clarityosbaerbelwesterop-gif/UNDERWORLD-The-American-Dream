# UNDERWORLD Weapon Pipeline (`T-ART-05`)

Spec-driven headless Blender 5.2 hard-surface weapon generator + Cycles AO/Normal PBR pipeline (`Tools/underworld_pipeline/weapons/build_weapon.py`).

## Usage
```bash
Tools/uwp build-weapon Config/Weapons/WPN_Pistol_01.json
Tools/uwp export Blender/Source/Weapons/WPN_Pistol_01/WPN_Pistol_01.blend
```

## Contract (`Docs/Handoffs/REQ_WPN_Pistol_01.md`)
- **Origin & Axes (TD-004)**: Origin at grip wrap center (mounts directly onto `SK_Jason`'s `SOCKET_RightHand_Weapon` with zero offset/rotation); barrel points Blender `-Y` → Godot `+Z`, up `+Z` → Godot `+Y`.
- **Nodes**: `Frame`, `Slide` (animated), `Magazine` (separate/detachable), `Barrel`, `Trigger`, skinned cleanly to a 4-bone `WeaponRig` (`WpnRoot`, `SlideBone`, `MagBone`, `TrigBone`) so glTF `ACTIONS` mode exports all clips cleanly while preserving exact node names.
- **Sockets**: `SOCKET_Muzzle` (barrel tip, `+Z` out at `z=0.165 m`), `SOCKET_Eject`, `SOCKET_Grip`.
- **Animations (30 fps, frame 0 start)**:
  - `A_WPN_Pistol_01_Fire` (0.10 s, slide blowback + trigger pull)
  - `A_WPN_Pistol_01_Reload` (1.60 s, mag out frame 9 / mag in frame 32 synced to `A_Jason_Reload_Pistol` + slide rack)
  - `A_WPN_Pistol_01_Empty` (static slide locked back)
- **Budget & Output**: ≤ 8,000 tris LOD0 (`WPN_Pistol_01`: 1,920 tris), single 1024² PBR material (`M_WPN_Pistol_01`, Cycles baked AO + CC0 Poly Haven `metal_plate`), auto LOD1/LOD2 + 64-vert convex pickup collision `UCX_WPN_Pistol_01-convcolonly`.
