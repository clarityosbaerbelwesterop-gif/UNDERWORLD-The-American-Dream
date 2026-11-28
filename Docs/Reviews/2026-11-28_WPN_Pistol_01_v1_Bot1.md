# Asset review — `WPN_Pistol_01` v1 (T-ART-05) — Bot 1 independent ART review

- **Date:** 2026-11-28 12:20 (Europe/Berlin)
- **Phase claimed by creator:** 2 HQ model, 3 Materials, 4 Cycles renders, 7 Validation; 8 Godot = gl_compatibility shots only
- **Creator:** Bot 2 (self-scorecard `Docs/Reviews/2026-11-28_WPN_Pistol_01_v1.md`)
- **Art reviewer (Bot 1):** this file · **Engine reviewer (Bot 3):** pending
- **Reference board:** `Docs/ArtDirection/References/WPN_Pistol_01/` (8 CC-BY/CC-BY-SA/PD photos, `REFERENCES.md`) – present
- **Sheets inspected (actual pixels):** `Docs/Reviews/sheets/WPN_Pistol_01_v1_ref_compare.png`, `Docs/Reviews/sheets/WPN_Pistol_01_before_after.png`
- **Renders inspected:** `Docs/ArtDirection/Reviews/WPN_Pistol_01/after_v1/{left,q3,guard}.jpg` in full, the other 12 views via the sheets
- **Phase 8 shots inspected:** `phase8/pistol_in_hand_close_compat.jpg`, `phase8/pistol_gameplay_ots_compat.jpg` (gl_compatibility/llvmpipe – NOT the shipping Forward+)
- **Technical gates (Bot 1 re-run on the merge with main 131d20b):** see the merge PR – `uwp --profile gate` part of `run_all`, `RUN_ALL` result + check count recorded there. LFS: glb/blend/png/jpg are pointers.
- **Triangles / budget:** 5,814 / 8,000 LOD0, one material, GLB 5.38 MB (2048² maps)

## Reference comparison
v1 is a **large, real improvement** over v0 (before/after sheet: v0 was a bent blob with a mis-attached grip). The side profile now reads as a modern polymer striker pistol: full-size slide on a raked grip, beavertail, front + rear serrations as geometry, 3-dot sights, rail, stippled grip panel, flared mag well. Matches board tiles R1/R3/R4 in proportion. Deviations: the frame/polymer is a flat mid-grey instead of the near-black/charcoal of every board photo; the frame above the trigger guard and the guard itself are slab-sided with hard, unbevelled edges, so close-ups look CAD/blockout rather than injection-moulded; the "9x19" mark is a smudge.

## Scores (Bot 1, art – honest, not adjusted to pass)

| Category | Bot 2 self | Bot 1 (art) | Bot 3 (engine) | Notes |
|---|---:|---:|---:|---|
| Silhouette | 4 | **4** | pending | Reads instantly as a pistol from left/right/top/q3; grip rake + beavertail right. |
| Proportions | 4 | **4** | pending | Slide/grip/guard ratios match R3; mag base plate slightly oversized but plausible. |
| Geometry | 4 | **3** | pending | Guard + dust cover are hard-edged slabs with visible facets and a stepped shelf (`after_v1/guard.jpg`); no soft moulded transitions or edge bevels on the frame; trigger is a thin bent strip. Hero-weapon close-ups need bevels/support loops or a better normal bake there. |
| Materials | 4 | **3** | pending | Slide nitride reads well. Polymer frame is a uniform light-mid grey (left/q3) – clearly off the board; no value separation between frame and grip texture, almost no wear/handling marks. |
| Textures | 4 | **3** | pending | Stipple is convincing; rest of the frame has no micro detail; engraving illegible; 2048² is over the REQ default (see TD-036). |
| Lighting | 4 | **4** | pending | New review rig for dark objects works: forms readable, no crushed blacks. |
| Visual detail | 4 | **4** | pending | Serrations, sights, pins, controls, port hood, rail slots all present and correctly placed. |
| Animation quality | 3 | **3** | pending | Not seen in motion by Bot 1; rigid 4-bone rig, no barrel tilt (barrel bone approved, TD-036). |
| Technical optimization | 4 | **3** | pending | Tris/material fine; 5.38 MB glb from 2048² maps is 4× the REQ texture default → re-export at 1024² (TD-036). |
| Engine integration | 3 | **2** | pending | In-hand compat shot: the right hand does not wrap the grip, the support hand floats on top of the slide, the gun sits too far forward in the palm. Gameplay still uses `PT_Pistol.tscn` (hierarchy issue `WeaponRig/Magazine` vs `test_weapon.gd` → T-WPN-02, Bot 3, P7). No Forward+ capture. |

## Defects (open, for v2)
1. Polymer frame albedo too light/grey vs. the board (left, q3, ref_compare) – target charcoal ~ sRGB 35–45 under the review rig; recheck in Forward+.
2. Trigger guard / dust cover: hard slab edges, facets and the frame-to-guard step (`after_v1/guard.jpg`) – add bevels/rounded moulding, re-bake normals.
3. Trigger blade too thin and flat; add a proper blade with safety lever thickness.
4. Rail teeth read light from below (`after_v1/left.jpg`) – albedo/AO on the rail underside.
5. Export at 1024² (TD-036); keep the 2048² bake in the .blend.
6. Barrel bone + Empty/Fire barrel tilt (TD-036, additive; weapon tests must stay green).
7. Hand fit: grip contact points vs. `SOCKET_RightHand_Weapon` and the support-hand pose (with Bot 3, T-WPN-02).
8. Real glb in gameplay (T-WPN-02, Bot 3, P7): recursive node lookup for `Magazine`/`Slide` under `WeaponRig`.

## Verdict
**REJECT for the art gate (Geometry 3, Materials 3, Textures 3, Technical 3, Animation 3, Engine integration 2) – registry stays `WIP`.**
Merged as **WIP** because it is a clear improvement over v0, nothing in the build is broken and all technical gates are green; the gate decision applies to `PRODUCTION-READY`, not to merging WIP work. Next: v2 against defects 1–7 (Bot 2) + T-WPN-02 (Bot 3).
