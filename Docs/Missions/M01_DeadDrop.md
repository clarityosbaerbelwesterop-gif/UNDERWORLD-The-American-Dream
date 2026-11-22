# M01 – "Dead Drop" (Chapter 1, vertical-slice mission)

Owner: Bot 1 (design) · Implementation: Bot 3 (T-MIS-01) · Assets: Bot 2. Status: READY FOR REVIEW.
Location: Calloway Avenue, East Hollow (LA), golden hour. Length target: 10–15 min.

## Premise
Sam calls: the Calloway Ave handoff never checked in. Jason and Marco drive over to find out why. Los Cuervos killed the delivery crew and are about to take the package.

## Beats & objectives
| # | Objective (HUD text) | Trigger / completion | Systems | Notes |
|---|---|---|---|---|
| 0 | *(intro)* phone call from Sam | level start, 20 s dialogue (subtitles, audio optional) | dialogue/subtitles | player controllable during call |
| 1 | "Get in the car." | player enters `VH_Sedan_01` (Marco already in passenger seat) | vehicle enter | marker over car |
| 2 | "Drive to the garage on Calloway Ave." | car stops inside `Area_GarageArrival` (radius 8 m) | driving, GPS marker | ~300 m loop around the block; civilians on sidewalks |
| 3 | "Check the garage." | player walks into `Area_GarageInside` | on-foot | scripted reveal: 3 dead crew (ragdoll poses), package crate on the bench |
| 4 | "Survive the ambush." | 2 waves: 3 gunmen from the street, then 2 from a van/rooftop; all `Enemy` nodes dead | gunplay, enemy AI, cover | Marco fights (invulnerable ally, low accuracy) |
| 5 | "Grab the package." | interact with `Pickup_Package` | interaction, carry state | Jason can't sprint while carrying; checkpoint after pickup |
| 6 | "Deliver the package to the warehouse." | car with package enters `Area_Warehouse` at end of street | driving | 2 gunmen in a pursuing car (optional stretch) |
| 7 | *(outro)* "MISSION PASSED" + cash reward $2,500 | end card | UI | |

## Fail states → restart at last checkpoint (start, or after step 5)
- Jason dies.
- Package destroyed (crate has 200 HP once picked up and loaded) or left > 60 m behind.
- Sedan destroyed before step 6 finishes.
- Marco is not killable in M1 (ally death is out of scope).

## Required content (exists as tasks)
- Player Jason + anims (T-ART-01/02, T-GP-01), pistol (T-ART-05, T-GP-02), sedan (T-ART-04, T-GP-03), street + garage (T-ART-03, T-LVL-01), 3+ civilians and ≥ 5 gunmen spawns (T-ART-06, T-AI-01/02), HUD (T-UI-01).
- Extra props for Bot 2 (add to T-ART-03): `SM_Prop_PackageCrate` (0.6×0.4×0.4 m, sealed, generic), garage workbench, roll-up door.
- Marco can reuse `SK_NPC_Civilian_B` rig with a different material until he gets his own model (M2).

## Implementation notes for Bot 3
- Mission defined as data (`Resource` with ordered objectives: type, target node path, text, checkpoint flag).
- Areas = `Area3D` named exactly as above in `LA_CallowayAve.tscn`.
- Debug API: `MissionManager.debug_complete_current()` so headless tests can step through all objectives.
