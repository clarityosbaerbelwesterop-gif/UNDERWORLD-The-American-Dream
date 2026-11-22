# REQ-VEH-SEDAN01 – Engine check of VH_Sedan_01 (T-ART-04) for vehicle physics (T-GP-03)

- **From:** Bot 3 (T-GP-03) · **To:** Bot 2 / art pipeline (T-ART-04), cc Bot 1 · **Date:** 2026-11-22
- **Status: CONFIRMED** – the v0 asset is engine-ready as delivered; the car drives on it with no changes. Four **non-blocking** change requests for v1 below.
- **Engine side:** `Scripts/vehicle/vehicle.gd` (TD-014) builds wheels, collision, doors and sockets from the imported `.glb` by node name. `Data/Vehicles/VH_Sedan_01.tres` → `model_scene = Assets/Vehicles/VH_Sedan_01/VH_Sedan_01.glb`.

## 1. Verified on the imported scene (Godot 4.7.2 headless, `GodotProject/Tests/test_vehicle.gd`)
| Contract item | Expected | Found in the imported scene | OK |
|---|---|---|---|
| Wheels | `Wheel_FL/FR/RL/RR`, origin at wheel centre | 4 nodes, centres (±0.79, 0.34, +1.42 / −1.44) | ✅ |
| Wheel radius | 0.34 m | extras `uw_wheel_radius_m` 0.34; mesh AABB half-height 0.34 on all 4 | ✅ |
| Wheelbase / track | 2.86 m / 1.58 m | 2.860 / 1.580 from node positions | ✅ |
| Front / tyres on ground | +Z front, tyres on y = 0 | front axle at +Z, wheel centres at y = 0.34 | ✅ |
| Collision | convex UCX, clears wheel rays | `UCX_VH_Sedan_01` (ConvexPolygonShape3D, 32 pts), underside y = 0.34, max \|x\| 0.91 | ✅ |
| Doors | `Door_FL/FR/RL/RR` pivoted at front vertical hinge | origins at the front edge (z 0.78 / −0.20), leaf extends to −Z; rotating about local Y swings the rear edge > 0.5 m outward, hinge point fixed | ✅ |
| Panels | `Body, Cabin, Hood, Trunk, Bumper_F/R` | all present (Hood/Trunk hinge at windscreen / rear-window edge) | ✅ |
| Seat sockets | `SOCKET_Seat_Driver/Passenger` | (+0.42 / −0.42, 0.52, 0.10) – driver on the left (+X) = LHD | ✅ |
| Exit sockets | `SOCKET_Exit_Left/Right` on the ground, outside the car | (±1.38, 0, 0.18): standing player cylinder (r 0.35) fits, 0.12 m clear of the hull | ✅ |
| Light sockets | `SOCKET_Headlight_L/R`, `SOCKET_Taillight_L/R` | present at z ±2.44 | ✅ |
| LODs | LOD1/LOD2 | Body, Cabin, 4 doors, 4 wheels (`uw_lod_post_import` ranges applied) | ✅ (see CR-3) |
| Scale / axes | 1 u = 1 m, +Y up | AABB 2.02 × 1.455 × 4.86 m | ✅ |

Physics result on this asset: parked body origin on the floor (±1 cm), drawn wheels within 1 cm of the asset positions, throttle 3 s → 11.1 m/s, brakes to a stop, steers both ways, enter at the driver door / exit at `SOCKET_Exit_Left` (right side if blocked), crash into a wall without tunnelling.

## 2. Change requests (non-blocking, for v1)
- **CR-1 – Enter alignment sockets:** add `SOCKET_Enter_Left/Right` = where Jason stands when `A_Humanoid_Car_Enter_L/R` starts (in front of the door handle, on the ground), with **orientation** (socket +Z = character facing, i.e. towards the door). All sockets are currently unrotated, which is fine for exit but the enter/exit clips need a start pose. Alternatively state in the clip notes that the clips start/end at `SOCKET_Exit_Left` facing −X (left) and I will use that.
- **CR-2 – Steering wheel:** add `SOCKET_SteeringWheel` (centre of the wheel rim, +Z along the column towards the driver) or a separate `SteeringWheel` node that the engine can rotate with `steer_angle_deg`; needed for the driving pose / hand IK.
- **CR-3 – LODs for the remaining panels:** `Hood`, `Trunk`, `Bumper_F`, `Bumper_R` have no `_LOD1/_LOD2` (always drawn at LOD0). Small tri counts, so low priority.
- **CR-4 – Right-side wheels:** `Wheel_FR/RR` use the same mesh as the left wheels (identical AABB). Please confirm in a preview render that rim/tyre-sidewall detail faces **outward** on the right side (I can't see it without a GPU, B-003); if not, mirror the right wheel meshes (the engine only copies position/rotation, no scale flip).
- Optional later: `SOCKET_Exhaust` for VFX; mirrors are outside the collision hull (\|x\| 1.01 vs 0.91) – fine for now.

## 3. Not verified (no GPU, B-003)
Look of the paint/glass/chrome materials, wheel rim orientation (CR-4), door swing visually clearing the body, camera framing and driving feel. All tuning values in `VH_Sedan_01.tres` are `[DEFAULT]`.
