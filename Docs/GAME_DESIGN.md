# UNDERWORLD – THE AMERICAN DREAM · Game Design Document (v0.1)

Owner: Bot 1 (Story Director). Status: living document. All names, places and characters are original. Real cities (Los Angeles, New York) are represented by **original, fictionalised districts** – no copied maps, logos, brands or assets from any existing game.

## 1. Pillars
1. **Weight** – movement and gunplay feel physical: momentum, recoil, cover, consequences.
2. **Cinema** – Chapter 1 is a tightly paced crime film; camera, lighting and dialogue sell it.
3. **The American Dream, inverted** – Jason builds an empire from €5,000 and learns what it costs.
4. **Living streets** – NPCs, traffic and police react believably.

## 2. Protagonist & cast (original)
| Name | Role | Notes |
|---|---|---|
| **Jason** (surname: open – owner decision, see BLOCKERS B-004) | Protagonist, smuggler/exporter | late 30s, 1.82 m, lean-athletic, short dark hair, stubble, scar over left eyebrow. Wardrobe Ch.1: worn leather jacket, grey henley, dark jeans, work boots. Calm, observant, dry humour. |
| **Sam** | Jason's employer, head of a small LA crime family | 60s, heavy-set, expensive suits, warm on the surface. Secretly betrays Jason to the FBI (reveal late Ch.2). |
| **Marco Ruiz** | Jason's colleague in Ch.1 | 30s, talkative driver, loyal; partner in M01. |
| **Los Cuervos** | Cartel #1 (antagonists Ch.1/Ch.2) | black/crow iconography (original), murder the delivery team in M01. |
| **La Hermandad del Sur** | Cartel #2 (works with Sam in Ch.2) | kidnaps and tries to recruit Jason. |
| **Kings of Flatbush** (working title) | Brooklyn street gang | produces for Jason, 80/20 split. |
| FBI Special Agent **Dana Whitlock** | Federal pursuer | leads the warehouse raid. |

## 3. Story outline
### Chapter 1 – Los Angeles (linear, cinematic)
1. **Arrival** – Jason flies in from Colombia; Sam receives him at a private hangar.
2. **The Route** – deliveries across LA and up into the Emerald Triangle; meeting contacts; returning home.
3. **Dead Drop (M01, vertical slice)** – Sam calls: a delivery failed. Jason and Marco find the crew murdered by Los Cuervos at a garage on Calloway Avenue. Shootout. Jason secures the package and drives it to the warehouse.
4. **The Raid** – the FBI storms the warehouse. Jason escapes, badly wounded.
5. **Wings** – Jason steals a small aircraft and flees to New York.

### Chapter 2 – New York (open world)
6. Arrival with ~€5,000; a cheap room; work as a taxi driver (taxi side activity).
7. Discovering Brooklyn's networks; stealing and selling cocaine; building contacts.
8. A local gang produces for Jason (80/20).
9. Crew assembly → **bank heist**; two crew members die; Jason escapes, wanted.
10. Hiding on a small farm in the countryside; Los Cuervos find him and burn it down.
11. Revenge: raid a rival gang's supplies, hit the cartel operation, steal a huge cocaine shipment.
12. Kidnapped by La Hermandad (working with Sam); refuses recruitment.
13. **Gold-depot heist** playing both cartels against each other; escape with the gold.
14. Reveal: Sam sold Jason to the FBI to protect his position.
15. Jason destroys both cartels and confronts Sam.
16. Epilogue – Jason starts a family. **FOUR YEARS LATER.**

## 4. World (long-term)
- **Los Angeles (fictionalised):** East Hollow (Hollywood-inspired), Crestmont Hills (Beverly Hills-inspired), Downtown, Seaview beaches, airport, San Ardo mountains, freeways, Harbor industrial, rural north incl. an Emerald-Triangle-inspired region.
- **New York (fictionalised):** Manhattan, Brooklyn, Queens, Bronx, Staten Island, a Central-Park-inspired park, subways, bridges, warehouses.

## 5. Milestone 1 – Vertical slice spec
**Scope:** one street, one mission, ~10–15 min of play, Linux build.
| Feature | Requirement | Tasks |
|---|---|---|
| Jason playable | 3rd-person movement (walk/run/sprint/crouch), aim over shoulder, animations from Blender | T-ART-01/02, T-GP-01 |
| LA street | "Calloway Avenue", East Hollow: ~120 m street, 2 blocks, shops, apartments, a garage, palms, streetlights; golden hour | T-ART-03, T-DES-02, T-LVL-01 |
| Vehicle | VH_Sedan_01, enter/exit, believable heavy-sedan handling | T-ART-04, T-GP-03 |
| Firearm | WPN_Pistol_01: hitscan, recoil, reload, 12-round mag | T-ART-05, T-GP-02 |
| NPCs | ≥ 2 civilians + cartel gunmen (≥ 3 on the street) | T-ART-06, T-AI-01/02 |
| Mission | M01 "Dead Drop" (see `Docs/Missions/M01_DeadDrop.md`) | T-DES-01, T-MIS-01 |
| Pipeline | Blender → .glb → Godot, automated tests | T-PIPE-00/01/02 |
| Build | Linux x86_64 export runs | T-BUILD-01 |

**Controls (KB/M · gamepad):** WASD/LS move · Shift/L3 sprint · C/B crouch · RMB/LT aim · LMB/RT fire · R/X reload · F/Y enter/exit vehicle · E/A interact · Space/A jump.

## 6. Art direction (v1)
- Photographic realism, slightly desaturated film look; LA = warm sodium/golden-hour palette, haze, long shadows; NY = cold blues, wet asphalt, steam.
- Materials: PBR metal/rough, worn and lived-in (dirt, decals, cracks) – no pristine surfaces.
- Shapes: believable American 1960s–2000s architecture (stucco, brick, neon signs with **invented** business names, e.g. "Vega Liquor", "Sunny Days Motel").
- Vehicles: generic original designs evoking late-90s American sedans/pickups; no real badges.
- Characters: realistic proportions, grounded clothing, no stylisation.

## 7. Systems roadmap (post-M1)
Weapons (more types, attachments), vehicles (cars, bikes, aircraft), progression, economy (cash, drug trade 80/20), inventory, police wanted system, gangs/territories, dialogue + cinematics (Godot AnimationPlayer + camera rigs), side activities (taxi), save/load.
