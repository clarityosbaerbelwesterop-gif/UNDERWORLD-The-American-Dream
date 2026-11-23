# Bericht Auftrag 02 (Claude Code)

**Branch:** `arena/6ba39491-underworld-the-american-dream`, aufgesetzt auf `main` @ `1c619b2`
**Stand:** 2026-11-22 · **Arbeitsauftrag:** `Docs/Prompts/CLAUDE_CODE_PROMPT_02.md`
**Merge-Regel des Auftrags: `MERGE-FREIGABE: NEIN`** → alle PRs sind offen, nichts wurde selbst gemergt.

---

## 1. Kurzfassung (5 Zeilen)

1. **Alle sechs Tasks sind inhaltlich fertig** (P0-1 … P1-6): Mission M01 komplett, Gegner im Auto,
   Jason-Animationen + Knochen-Hitboxen, HUD, lesbares Level, Linux-Build.
2. `Tests/run_all.sh` → **RUN_ALL: PASS, 738 Checks** (vorher 589), auch auf einem **frischen Worktree**
   von `594c674` nachgestellt.
3. **9 Sabotage-Modi** wurden einzeln gefahren: jeder endet mit **Exit 1** und echten FAILs
   (2 … 22 pro Modus), keiner überspringt Checks.
4. **13 echte Bugs** gefunden und behoben, davon **6 stille**, die weder Absturz noch Warnung erzeugten
   (u. a. das ganze Straßenbild lag übereinander im Ursprung, alle Gebäude fehlten in der Datei).
5. **Nicht behauptet:** nichts davon ist „AAA" oder „production ready". Es gibt **keine** Phase-8-Aufnahme
   (kein X-Server, keine GPU auf dieser Box) und **niemand hat den Build auf einem Rechner gespielt**.

---

## 2. Pro Task

| Task | Status | Was jetzt funktioniert | Beweis |
|---|---|---|---|
| **P0-1 · T-MIS-01b** M01 fertig | **FERTIG** | Marco als unverwundbarer Beifahrer, Wellen 1/2 datengetrieben sequenziert, echte Fahrt durch die echte Eingabe | `test_mission.gd` 105 Checks; Fahrt **26,2 s / 97,2 m / 0,00 m off-road**; Sabotage `UW_MISSION_SABOTAGE=1` → 5 FAIL, `=3` → 2 FAIL |
| **P0-2 · T-AI-03** Gegner vs. Auto | **FERTIG** | Sitzender Spieler wird für Wahrnehmung/Zielen durch sein Fahrzeug ersetzt; Treffer gehen an `Vehicle.health`; Fahrer nur durchs Fahrerfenster (25 %) | `test_ai.gd` 102 Checks; Sabotage `UW_AI_SABOTAGE=incar` → 4 FAIL |
| **P0-3 · T-GP-04** Clips/Aim/Hitboxen | **FERTIG** | 6 Clips an echte Ereignisse gekoppelt, Oberkörper-Aim-Layer, 7 Knochen-Hitboxen | `test_player_controller.gd` 171 Checks; `UW_ANIM_SABOTAGE=1` → 9 FAIL, `UW_JASON_SABOTAGE=1` → 3 FAIL |
| **P0-4 · T-UI-01** HUD | **FERTIG** | HUD hängt an Signalen, Marker projiziert, Passed-Karte, Fail-Grund | `test_hud.gd` 40 Checks; `UW_HUD_SABOTAGE=1` → 3 FAIL |
| **P1-5 · T-LVL-01a** Greybox lesbar | **FERTIG (Blockout!)** | Straße/Bordstein/Gehweg unterscheidbar, 0 `@`-Namen, Navmesh über Straße **und** Gehweg (428 Polygone), Block in 44 Wegpunkten ablaufbar | `test_level.gd` **23 Checks**; `UW_LEVEL_SABOTAGE=1` → 1 FAIL; Planansicht `Docs/Reports/plan_calloway_ave.png` |
| **P1-6 · T-BUILD-01** Linux-Export | **FERTIG (nur Boot-Nachweis)** | Preset + Skript, Export exit 0, 79 MB Binary + 189 MB PCK, `Tests/` und `Scripts/import/` nachweislich nicht im Paket | `Tools/build/build_linux.sh` exit 0, Smoke-Log ohne `ERROR`; `UW_BUILD_SABOTAGE=1` → exit 6 |

**Testzahlen vorher → nachher** (`Tests/run_all.sh`): smoke 12 → 12, uwp-Tools 58 → 58,
Asset-Import 71 → 71, AI 80 → **102**, HUD **neu 40**, Level **neu 23**, Mission 74 → **105**,
Player 137 → **171**, Vehicle 88 → 88, Weapon 68 → 68. **Summe 589 → 738.**

### Sabotage-Matrix (jede Zeile einzeln gefahren, `exit` bezieht sich auf den Godot-Prozess)

| Modus | Test | Exit | FAIL |
|---|---|---|---|
| `UW_AI_SABOTAGE=incar` | test_ai | **1** | 4 |
| `UW_ANIM_SABOTAGE=1` | test_player_controller | **1** | 9 |
| `UW_JASON_SABOTAGE=1` | test_player_controller | **1** | 3 |
| `UW_HUD_SABOTAGE=1` | test_hud | **1** | 3 |
| `UW_LEVEL_SABOTAGE=1` | test_level | **1** | 1 |
| `UW_MISSION_SABOTAGE=1` | test_mission | **1** | 5 |
| `UW_MISSION_SABOTAGE=3` | test_mission | **1** | 2 |
| `UW_VEHICLE_SABOTAGE=1` | test_vehicle | **1** | 9 |
| `UW_VEHICLE_SABOTAGE=2` | test_vehicle | **1** | 22 |
| `UW_BUILD_SABOTAGE=1` | `Tools/build/build_linux.sh` | **6** | – |

---

## 3. Gefundene Bugs (Symptom · Ursache · Fix · Test, der ihn jetzt fängt)

| # | Symptom | Ursache | Fix | Test |
|---|---|---|---|---|
| 1 | **Alle Gebäude fehlten** in der gespeicherten Szene | `_building()` gab das Kit-Teil zurück, das schon Kind des Blocks war → Reparenting scheiterte still | Block zurückgeben | `test_level`: „buildings … actually IN the shipped scene" |
| 2 | Straße/Gehweg/Grund **dasselbe Grau** | Kit-Materialien wurden nie überschrieben, nur der Greybox-Fallback nutzte `fallback_mat` | `paint`-Overrides pro Surface | Luminanz 0,15 / 0,60 / 0,78 |
| 3 | Lackierte Flächen **fehlten** nach dem Speichern | `PackedScene` serialisiert Surface-Overrides in instanziierten Sub-Szenen nicht | gemalte Kopien als level-eigene Meshes, Kit-Instanz unsichtbar | 118 Kopien im `.tscn` |
| 4 | **Alle Straßenstücke übereinander im Ursprung** (unsichtbare Straße) | `_initialize()` eines `--script`-SceneTree läuft **vor** `SceneTree::initialize()` → Level nicht im Baum → `global_transform` = Identity | Transform aus `inst.transform` × Mesh-Kette von Hand | `test_level`: 118 Kopien, 0 im Ursprung, erstes Stück bei (-24, 0, -79) |
| 5 | Navmesh **leer** (0 Polygone), Wegfindung tot | Region nie gebacken; zusätzlich wurde sie gebacken, bevor die Geometrie einen Frame im Baum stand | Bake im Generator **nach** `await process_frame` + `await physics_frame` | 428 Polygone, Probes auf Straße + Gehweg |
| 6 | Gehweg lag **in der Fahrbahn** | flacher `NavFloor`-Kasten deckte alles auf Straßenhöhe ab | `NavFloor` entfernt, Navmesh aus echter Geometrie | Navmesh-Probe auf Gehweg y = 0,16 |
| 7 | **Auto bleibt bei z ≈ 37 m stehen**, keine Rückmeldung | Zivilistenroute querte die Fahrbahn; ein Fußgänger ist ein 0,56-m-Hindernis | Route bleibt auf dem äußeren Gehweg, Spawn 1,4 m abseits der Kante | M01-Fahrt 26,2 s statt Abbruch |
| 8 | **Objektiv „Get in the car"** nie erfüllbar | `_area_occupied` castete auf `Area3D`, das Ziel ist ein `Vehicle` | `Vehicle.driver != null` | `test_mission` |
| 9 | „Package left behind" **feuerte nie** | Distanz wurde zum Träger gemessen (≈ 0) | Distanz zum Spieler/Fahrzeug + `_package_ever_held` | `test_mission` |
| 10 | Keine Gegner in der Mission | `add_to_group` ohne `persistent` wird nicht gepackt | `add_to_group(..., true)` | 5 Gegner in `mission_enemies` |
| 11 | HUD **0 Verbindungen** | HUD-Knoten steht vor dem `MissionManager` in der Szene | `_bind.call_deferred()` | `test_hud` |
| 12 | Gegner sahen **kein geparktes Auto** | Sichtstrahl galt nur bei Treffer auf ein Objekt als „gesehen" | Strahl auf das Ziel selbst zählt | `test_ai` |
| 13 | Level-Test schlug **fälschlich** fehl (Ursprung statt Position) | Node nach `free()` gelesen: vergleicht `!= null`, liefert Nullvektoren | Werte **vor** `free()` lesen und vergleichen | im Test kommentiert |

---

## 4. Was ausdrücklich NICHT behauptet wird

- **Kein „AAA", kein „production ready", kein „spielbar fertig".** Das Level ist ein **Blockout**
  (graue Boxen, keine Kunst). Die Lesbarkeit ist repariert, das Aussehen nicht.
- **Keine Phase-8-Aufnahme.** `Tools/godot_phase8_capture.sh` braucht Xvfb + Mesa/llvmpipe; auf dieser
  Box gibt es **keinen X-Server und keine GPU** (§9 `Docs/TOOLCHAIN_SANDBOX.md`). Ersatz ist bewusst
  **kein** Screenshot, sondern eine **Planansicht aus den echten Szenendaten**
  (`Tests/tools/capture_level_plan.gd` → `Docs/Reports/plan_calloway_ave.png`, gitignored, regenerierbar).
  Sie zeigt Grundrisse, Positionen und Albedo-Stufen – **keine** Beleuchtung, keine Form, keine Kunst.
  Diese Ansicht hat Bug 4 überhaupt erst sichtbar gemacht.
- **Der Linux-Build ist nicht gespielt.** Er bootet headless. Das Template musste hier **aus dem Quellbaum
  gebaut** werden (der offizielle `.tpz`-Host ist gesperrt) und hat `vulkan=no opengl3=no` – also
  **keinen Renderer**. Auf einem Rechner mit Vulkan-Template ist das der nächste Schritt.
- **FPS, Spielgefühl, Forward-Plus-Look:** unverifiziert.
- Der PCK ist mit **189 MB** groß; das ist die aktuelle Inhaltsgröße (Skelett-/Skin-Ressourcen), keine
  Shipping-Größe.

---

## 5. Offene Punkte / Vorschlag für Auftrag 03

1. **Phase 8 auf einer GPU-Box**: Aufnahmen Übersicht / Straßenniveau / Garage, dann ehrliche Bewertung.
2. **Vulkan-Template** bauen/laden → Build, der wirklich ein Fenster öffnet; erst dann „spielbar" nennen.
3. **Level-Kunst**: Die Greybox ist jetzt lesbar, aber leer. Nächster Schritt ist ein Art-Pass über die
   Pipeline (`Tools/uwp`), nicht Handarbeit an der `.tscn`.
4. **T-LVL-01b**: Beleuchtung (Golden Hour), Okkluder, Straßenmarkierungen als eigene Deckschicht.
5. **Marco/Welle-Feinschliff**: Wellen sind sequenziert, aber es gibt noch kein Audio und keine
   Treffer-Rückmeldung im HUD für Gegner.

---

## 6. Toolchain-Abweichungen dieser Umgebung (mit Beleg)

| Abweichung | Beleg / Umgang |
|---|---|
| **`git-lfs` nicht installierbar** (Release-Hosts gesperrt, kein Go) | `git lfs version` → *„not a git command"*. Binärdateien wurden deshalb **nicht** committet; Assets kommen über `Tools/sandbox/restore_lfs_from_history.py` aus der Historie (114/114 Pointer aufgelöst). Nachweis: alle 114 getrackten Binärdateien sind LFS-Pointer, 0 Klartext-Blobs. `Docs/Reports/plan_calloway_ave.png` ist daher gitignored. |
| **Godot ohne fontconfig/X11/Vulkan** | Selbst gebaut mit `x11=no wayland=no alsa=no ... vulkan=no` (47 min) → keine Phase-8-Aufnahme, keine Systemschrift. |
| **Godot 4.7.2 Export-Templates fehlten** | Aus demselben Quellbaum gebaut, `Docs/BUILD.md` §Templates. |
| **Blender nur über bpy-Stub** | `Docs/TOOLCHAIN_SANDBOX.md` §2; `Tools/uwp`/Tests respektieren `BLENDER=`/`GODOT=`. |
| **Kein Netz zu Download-Hosts** | `github.com`/`codeload` erreichbar, `objects.githubusercontent.com` nicht (302 → exit 35). |
