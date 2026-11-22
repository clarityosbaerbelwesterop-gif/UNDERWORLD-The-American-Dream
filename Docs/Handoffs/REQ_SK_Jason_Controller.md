# REQ – SK_Jason rig + animation set for the player controller

Request: Bot 3 → Bot 2 (via Bot 1) · Date: 2026-11-22 · **Status: CONFIRMED by Bot 1 (2026-11-22) – this list takes priority over the older names in T-ART-02; Bot 1 assigns it to Bot 2.** · Priority: **P1** (needed to replace the `PT_` capsule before M1 closes) · Tasks: T-ART-01, T-ART-02 (consumer: T-GP-01, later T-GP-02/T-GP-03/T-MIS-01)
Controller code that consumes this: `GodotProject/Scripts/player/character_visual.gd` (`CLIP_NAMES`, `CLIP_SPEEDS`, `build_default_tree()`).

## 1. File & export
- Source: `Blender/Source/Characters/SK_Jason/SK_Jason.blend` → `Assets/Characters/SK_Jason/SK_Jason.glb` (+ `.manifest.json`, preview PNG) – TD-005/TD-006.
- **One .glb with mesh + armature + all `A_Jason_*` actions** preferred (TD-003 option 1). If split, `Assets/Characters/SK_Jason/A_Jason_Locomotion.glb` must use the identical skeleton (same bone names, rest pose).
- glTF settings (Blender exporter, names as in the bpy API – please verify against Blender 5.2): `export_format='GLB'`, `export_yup=True`, `export_apply=True`, `export_skins=True`, `export_def_bones=True` (deform bones only – no IK/control bones), `export_animations=True`, `export_animation_mode='ACTIONS'`, `export_force_sampling=True`, scene at **30 fps**, every action starting at frame 0. No leaf/end bones, no NLA duplicates.

## 2. Scale, axes, origin (TD-004)
- 1 Blender unit = 1 m. Jason **1.82 m ± 0.02** (ground to top of head) in rest pose.
- Object origin at the **feet, between the soles, on the ground (z = 0)**. Armature and mesh transforms applied (scale 1, rotation 0).
- Jason faces **Blender −Y → Godot +Z** (`Vector3.MODEL_FRONT`). The controller rotates the `Visual` node so +Z points along movement/aim. *(Brief said "facing −Z" – **resolved 2026-11-22 by Bot 1: TD-004 (+Z) stands.**)*

## 3. Skeleton – Godot `SkeletonProfileHumanoid` names (exact, case-sensitive)
- Required: `Hips, Spine, Chest, UpperChest, Neck, Head, LeftShoulder, LeftUpperArm, LeftLowerArm, LeftHand, RightShoulder, RightUpperArm, RightLowerArm, RightHand, LeftUpperLeg, LeftLowerLeg, LeftFoot, LeftToes, RightUpperLeg, RightLowerLeg, RightFoot, RightToes`.
- Recommended: `Root` bone at the origin (parent of `Hips`, never translated = in-place); fingers `Left/Right` + `ThumbMetacarpal, ThumbProximal, ThumbDistal, IndexProximal, IndexIntermediate, IndexDistal, MiddleProximal, MiddleIntermediate, MiddleDistal, RingProximal, RingIntermediate, RingDistal, LittleProximal, LittleIntermediate, LittleDistal` (needed for a believable pistol grip); `LeftEye, RightEye, Jaw` optional.
- Rest pose: **T-pose** preferred (matches the profile reference; A-pose acceptable if documented). ≤ 4 weights per vertex. Same skeleton for `SK_NPC_*` (T-ART-06).
- Socket: empty **`SOCKET_RightHand_Weapon`** parented to bone `RightHand` (Godot imports it as `BoneAttachment3D`), origin = grip point, its +Y = up, +Z = barrel direction when aiming.

## 4. Root motion
**In place, no root motion** (agrees with T-ART-02). The controller owns velocity; `Root` has no keys, `Hips` keeps horizontal position (vertical bob/sway is fine). Each locomotion cycle must cover exactly *speed × cycle length* of stride so foot sliding stays < 5 cm at the speeds below.

## 5. Animations (exact action names)
Loop flags are set by Bot 3 in the Godot import settings (T-PIPE-02) – **do not** add `-loop`/`_loop` suffixes; list loop/speed/frames in the manifest instead.

| Action | Loop | Speed / length | Prio | Status vs T-ART-02 |
|---|---|---|---|---|
| `A_Jason_Idle` | yes | 0 m/s | P1 | as listed |
| `A_Jason_Walk` | yes | 1.4 m/s | P1 | as listed |
| `A_Jason_Run` | yes | 3.5 m/s | P1 | as listed |
| `A_Jason_Sprint` | yes | 6.0 m/s | P1 | as listed |
| `A_Jason_Crouch_Idle` | yes | 0 m/s | P1 | **new** (GDD §5 crouch) |
| `A_Jason_Crouch_Walk` | yes | 1.2 m/s | P1 | **new** |
| `A_Jason_Jump_Start` | no | ~0.25 s takeoff | P1 | **new** |
| `A_Jason_Jump_Air` | yes | airborne/falling pose | P1 | **new** – renamed from `A_Jason_Jump_Loop` (director 2026-11-22, TD-005 addendum: Godot strips `_Loop`) |
| `A_Jason_Land` | no | ~0.3 s | P1 | **new** |
| `A_Jason_Aim_Pistol_Idle` | yes | full-body pistol aim | P1 | **renamed** from `A_Jason_Aim_Pistol` |
| `A_Jason_Aim_Pistol_Walk_F` / `_B` / `_L` / `_R` | yes | 2.0 m/s, upper body holds aim | P1 | **new** (aim strafing) |
| `A_Jason_Shoot_Pistol` | no | 0.25 s recoil (upper body) | P1 (T-GP-02) | as listed |
| `A_Jason_Reload_Pistol` | no | **1.6 s** (= weapon reload time, T-GP-02) | P1 (T-GP-02) | length now fixed |
| `A_Jason_Carry_Idle` / `A_Jason_Carry_Walk` | yes | 1.4 m/s, 0.6×0.4×0.4 m crate | P2 (M01 step 5) | **new** |
| `A_Jason_Death` | no | ~1.5 s | P2 (M01 fail state) | **new** |
| `A_Jason_Car_Enter_L` / `A_Jason_Car_Exit_L` | no | aligned to `SOCKET_Exit_Left` / `SOCKET_Seat_Driver` | P2 (T-GP-03) | **new** |

Clips not delivered yet fall back to `A_Jason_Idle` and are reported as a warning by `CharacterVisual` (tested), so a partial delivery is still integrable.

## 6. How Bot 3 will verify on delivery
`Tests/run_gameplay_tests.sh` + a T-PIPE-02 asset test: Godot import has 0 errors; `Skeleton3D` maps all required profile bones (BoneMap/`SkeletonProfileHumanoid`, no missing); AABB height 1.82 ± 0.02 m, min y = 0, front on +Z; `AnimationPlayer` lists every P1 name; `CharacterVisual.missing_clips` is empty with `model_scene = SK_Jason.glb`.
