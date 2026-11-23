# Audit T-PIPE-06 – Asset-Pipeline `Tools/uwp` (mit T-PIPE-05)

**Datum:** 2026-11-23 · **Autor:** Claude Code · **Grundlage:** Master-Prompt §5.2/§5.4, Reviews in `Docs/Reviews/`, Abnahme T-BUILD-02.
Gelesen: `cli.py`, `validate.py`, `generate.py`, `exporter.py`, `scene.py`, `config.py`, `defaults.json`, `Config/asset_budgets.json`, `environment/build_la_kit.py`, Testsuite `tests/run_tests.sh`. Bei den Charakter-, Waffen- und Fahrzeug-Generatoren habe ich die Ergebnisse geprüft, nicht jede Zeile. Ihre Befunde kommen aus dem Gate-Lauf über alle 17 Quellen.

## 1. Kurzfassung
- Der Kern aus Spec → Generator → Validierung → Export → Godot-Import ist reproduzierbar und gut getestet. Er bleibt.
- **Die Validierung war für WIP gebaut und hatte keine Freigabe-Stufe.** Clipping von bis zu 7 Vertices oder unter 3 % galt nur als „info“. Charaktere wurden ganz ohne LODs exportiert, Budgets aus TD-012 fehlten, Kollisionen aus dezimierten LODs schlossen Öffnungen.
- Neu ist das **Release-Gate `uwp export --profile gate`**: strikt, LODs und Kollision Pflicht, TD-012-Budgets, null Kleidungs-Clipping. Ergebnis über alle Quellen: **8 von 17 bestehen technisch**, alle 7 Charaktere und die Limousine fallen durch.
- **TD-021 Hybrid-Pipeline** (PROPOSED): Hero-Assets werden von Hand gestaltet, `uwp` ist die Pflichtstrecke. Die Generatoren bleiben für Blockouts, Kits und Varianten.

## 2. Befunde und Status
| # | Befund | Schwere | Status / Beleg |
|---|---|---|---|
| A-1 | Trimesh-Kollision aus **LOD2** – Dezimierung schloss das M01-Garagentor (B-PT-02) | hoch | **behoben** in PR #21 (LOD0), uwp-Test |
| A-2 | Render-Mesh als Kollision: 4-mm-Markierungen = Wände (B-PT-01) | hoch | **behoben** in PR #21: Regel `COLLISION_MICRO_LIP`, uwp-Test |
| A-3 | `MESH_CLIPPING` gelockert: Fehler erst ab ≥ 8 Vertices **und** > 3 %, sonst nur „info“; nur Ruhepose | hoch | **Dev-Profil bewusst unverändert** (WIP muss exportierbar bleiben). **Release-Gate: 0 Vertices**, belegt: 12 Clipping-Fälle in 5 Charakteren, die das Dev-Profil verschwieg. Prüfung in Animationsposen fehlt noch → T-ANIM-01 |
| A-4 | **Keine Charakter-LODs** (`lods.Characters.ratios = []`), Master-Prompt §5.5 fordert 40k/20k/8k | hoch | Release-Gate verlangt LODs (`LOD_MISSING`); Generator-Umbau mit dem Charakter-Neubau (T-ART-01b), weil ein Re-Export aller Charaktere heute ~70 MB LFS kostet |
| A-5 | TD-012-Budgets (LOD, Kollision) nicht maschinenlesbar | mittel | **behoben**: `asset_budgets.json` → `lod_triangle_fraction_max`, `collision_budget`, Prüfungen `LOD_BUDGET`/`COLLISION_BUDGET` |
| A-6 | Konvexe Hülle überschreitet das eigene 64-Vertex-Limit (65) | niedrig | **behoben**: iterative Dezimierung + Warnung; uwp-Test |
| A-7 | `NAME_MESH_PREFIX` meldet Funktionsteile (`Wheel_FL`, `Door_FL`, `Slide` …) – das ist der Vertrag mit der Godot-Laufzeit | niedrig (falsch positiv) | **behoben**: Allowlist; uwp-Test auf der echten Limousine |
| A-8 | Keine Freigabe-Stufe: „PRODUCTION-READY“ hatte keine maschinelle Voraussetzung | hoch | **behoben**: `--profile gate` (TD-021) |
| A-9 | Limousinen-Kollisionshülle (autorisiert) ist nicht-manifold (56 Kanten mit > 2 Flächen) | mittel | offen → T-ART-04 (Gate weist ab) |
| A-10 | `SK_Jason_Teeth` UV-Selbstüberlappung 32,5 % | niedrig | offen → T-ART-01b (Gate weist ab) |
| A-11 | `SK_NPC_Cop_LA` Ursprung 7,3 cm außermittig | niedrig | offen → T-ART-06 (Gate weist ab) |
| A-12 | Haare als geschlossene Schale, keine Hair Cards; Kleidung geschrumpfte Hüllen; berechnete Animationen | **grundsätzlich** | Ansatzgrenze, nicht per Validator lösbar → TD-021 Hybrid |
| A-13 | Fußrutschen wurde **gemessen** (`anim_report.json`), aber gegen kein Budget geprüft (Jason bis 4,86 cm) | hoch | **behoben**: Regel `ANIM_FOOT_SLIDE` (Budget `animation.foot_slide_max_m` = 1 cm, §6.3) – Warnung im Dev-Profil, Fehler im Release-Gate; uwp-Test. Die Clips selbst zu reparieren (Mocap, Foot-IK) bleibt T-ANIM-01 |
| A-14 | Keine Prüfung auf Normal-/Tangent-Daten, Textur-Kompression, Mipmaps | mittel | offen, Vorschlag für das nächste Pipeline-Paket |
| A-15 | Smoke-Test schrieb bei jedem Lauf getrackte Dateien neu | mittel | **behoben** in PR #22 (Hygiene-Check in `run_all.sh`) |

## 3. Release-Gate über alle Quellen (`uwp export-all --profile gate --no-preview`, Blender 5.2.4)
| Asset | Gate | Gründe |
|---|---|---|
| SM_LA_Bldg_GarageM01, SM_LA_Bldg_ShopStucco, SM_LA_PalmTree, SM_LA_Road_Straight, SM_LA_Sidewalk_Curb, SM_LA_Streetlight, SM_Prop_PackageCrate, WPN_Pistol_01 | **PASS (technisch)** | – |
| SK_Jason | FAIL | Body/TShirt clippen durch die Jacke (je 1 Vertex), Zähne UV-Überlappung 32,5 % |
| SK_NPC_Cartel_A | FAIL | Clipping 1 + 2 Vertices |
| SK_NPC_Cartel_B | FAIL | Clipping 4 + 3 + 2 Vertices |
| SK_NPC_Marco | FAIL | Clipping 1 + 3 Vertices |
| SK_NPC_Sam | FAIL | Clipping 1 + 3 + 2 Vertices |
| SK_NPC_Civilian_Female | FAIL | keine LODs |
| SK_NPC_Cop_LA | FAIL | Ursprung außermittig |
| VH_Sedan_01 | FAIL | Kollisionshülle nicht-manifold |
| PT_PipelineTest_Crate | FAIL | Ursprung (Testobjekt, erwartbar) |

**Wichtig:** Technisch PASS heißt nicht „production-ready“. Alle Assets bleiben im Kunst-Review REJECT/WIP (QUALITY_GATE §4: Review ≥ 4 in allen Kategorien fehlt).

## 4. Tests (neu in `Tools/underworld_pipeline/tests/run_tests.sh`)
- Release-Gate mit LODs → exit 0; ohne LODs → exit 1 + `LOD_MISSING`
- Release-Gate weist 4,86 cm Fußrutschen ab (`ANIM_FOOT_SLIDE`, nennt den Clip)
- Konvexe Hülle ≤ 64 Vertices (alter Code: 65)
- Funktionsteil-Namen der echten Limousine sind kein Namensfehler
- (aus PR #21) `COLLISION_MICRO_LIP` Fail/Pass-Paar, Trimesh aus LOD0

## 5. Empfehlung (Reihenfolge)
1. TD-021 annehmen → Hero-Quellen unter `Art/Source/`. Werkzeugwahl laut §5.3: Blender-Sculpt, Hair Cards per Geometry Nodes, ArmorPaint oder Blender Paint; kommerzielle Tools entscheidet die Eigentümerin (E-4).
2. T-ANIM-01: Fußrutsch-Validierung und Clipping in Posen prüfen.
3. Charakter-LODs im Generator mit T-ART-01b, damit der LFS-Re-Export nur einmal anfällt.
4. Zusätzliche Validatoren: Tangenten/Normalmap-Konvention, Textur-Kompressions-Preset und Mips im Godot-Import.
