# Bericht T-BUILD-02 – Abnahme des Ist-Stands von M01 (Forward Plus, ohne GPU)

**Datum:** 2026-11-23 (Europe/Berlin) · **Autor:** Claude Code · **Vorgänger:** PR #20 (T-ENV-01)

## 1. Kurzfassung
- **M01 „Dead Drop“ war für einen Menschen nicht spielbar.** Die alten Tests haben die Missions-APIs direkt aufgerufen und das deshalb nicht gemerkt. Schon den ersten Gehversuch per Eingabe stoppte eine 4 mm hohe Fahrbahnmarkierung.
- Neu ist ein **Autopilot, der nur Eingaben nutzt** (Tasten/Achsen und Kameradrehung, wie ein Mensch). Er läuft als Merge-Gate in `run_all.sh` (`test_playthrough.gd`). Gefunden hat er **20 echte Fehler** in Pipeline, Level-Generator, Mission und KI. Alle 20 sind behoben, jeder hat einen Test oder Sabotage-Modus.
- **Heute ist M01 per Eingabe von Anfang bis Ende schaffbar:** einsteigen → 300 m fahren → Garage → Hinterhalt mit 5 Schützen per Pistole → Paket per `E` → einladen → Lagerhaus → „MISSION PASSED“, 2.500 $ (Seed 2, 221,9 s Spielzeit).
- **Video in Forward Plus**, dem Shipping-Renderer, aufgenommen mit Godot Movie Maker auf lavapipe (Vulkan auf der CPU). Es zeigt den Look, aber **keine GPU-Leistung**.
- Offen: der Dach-Schütze (B-007) und die Kampf-Balance (B-008, TD-022). Dazu braucht es einen menschlichen Spieltest auf einer GPU.

## 2. Was gemacht wurde
| Teil | Ergebnis |
|---|---|
| Forward Plus ohne GPU | `Tools/godot_phase8_capture.sh --renderer fwdplus` (T-ENV-01). Release-Build und Editor rendern auf Mesa lavapipe. |
| Autopilot | `GodotProject/Tests/tools/m01_autopilot.gd`. Er drückt nur Aktionen und dreht die Kamera. Er nutzt Navmesh, Deckung (peek/hide), taktische Feuerpunkte und läuft um geparkte Autos herum. Staatsändernde Spiel-APIs ruft er nie auf. |
| Merge-Gate | `GodotProject/Tests/test_playthrough.gd`: Shipping-Szene `Game_M01.tscn`, deterministischer Replay mit Seed 2 (TD-021). |
| Video | `Tests/tools/record_m01_playthrough.gd` mit Movie Maker → `Docs/Reports/renders_fwdplus_m01/M01_playthrough_fwdplus.mp4` |

**Offen benannter QA-Cheat:** Im Gate ist Jason unverwundbar. Der Test prüft den **Spielfluss**, nicht die Balance. Alle 5 Schützen müssen trotzdem über Zielen und Schießen getroffen werden: 23 Treffer bei 82 Abzügen.

## 3. Gefundene und behobene Fehler
| ID | Symptom | Ursache | Fix | Test, der es jetzt fängt |
|---|---|---|---|---|
| B-PT-01 | Jason bleibt nach 3 m Gehen an einer Straßenkachel hängen | Die Straßen-Kollision ist das Render-Mesh, also sind die 4 mm hohen Markierungen Mini-Wände für die Zylinder-Kollision (TD-011) | Autorisierte flache `UCX_`-Platte; neue Pipeline-Regel **`COLLISION_MICRO_LIP`** (Environment: senkrechte Kollisionsflächen 0,5 mm–2 cm = Fehler) | uwp: `PT_UWP_LipFloor` muss scheitern, `PT_UWP_FlatFloor` muss bestehen (+4 Checks) |
| B-PT-02 | Garage: Tür zu | Trimesh-Kollision kam aus dem dezimierten **LOD2**, die Dezimierung schließt Öffnungen | Trimesh immer aus LOD0. Alle 5 Trimesh-Umgebungs-Assets neu exportiert (Blender 5.2.4) | uwp: Trimesh-Name ohne `_LOD` (alter Code: `..._LOD2-colonly` → FAIL, gesehen) |
| B-LVL-01 | Garagentor blockiert | Die 4 „Kerb_Line“-Streifen waren 2 cm hohe Kollisionsboxen, alle auf der **Gebäudeseite** (Vorzeichenfehler) | Nur noch Optik, 6 mm, auf der Straßenseite; Zebrastreifen ebenso | Playthrough |
| B-LVL-02 | Garage nicht betretbar, Navmesh-Insel | Die Garagenhülle stand im Generator **180° falsch** (+90° statt −90°): Rolltor nach hinten, Westseite massiv | −90° | test_level: Navmesh-Pfad vom Vorplatz **in** die Garage |
| B-M01-01 | Paket nicht aufhebbar | Die Aktion `interact` (E/Y) war belegt, wurde aber **nirgends gelesen** | `PlayerController.try_interact()` + Gruppe `interaction_handlers` | `UW_PLAYTHROUGH_SABOTAGE=1` → hängt bei Ziel 5 |
| B-M01-02 | Lieferung unmöglich | Beim Einsteigen wurde das Paket **nie ins Auto geladen**, DELIVER verlangt LOADED | `CarriedItem` lädt sich ein, wenn der Träger einsteigt | `=2` → hängt bei Ziel 6 |
| B-M01-03 | Mission endet nie, keine 2.500 $ | Endkarte `auto_seconds = 0` = nie | 5 s | test_mission: Outro schließt selbst ab |
| B-M01-04 | Nach dem ersten Tod keine Steuerung mehr | Der Neustart setzte die Gesundheit zurück, aber nicht `input_enabled` | `PlayerController.revive()` | test_mission: Jason **läuft** nach dem Neustart |
| B-M01-05 | Endlosschleife „Sedan destroyed“ | Der Checkpoint setzte Jason auf seine **Sitzposition** im Auto, die Physik schleuderte das Auto weg; wer im Auto starb, wurde nicht herausgeholt | Snapshot an der Ausstiegstür, `Vehicle.eject_driver()` | test_mission: Jason steht neben dem Auto |
| B-M01-06 | Jason „klettert“ auf sein Paket (y = 2,8 m) | Die getragene Kiste behielt ihre statische Kollision und wurde jeden Frame vor ihn teleportiert | Kollision nur am Boden | Playthrough |
| B-M01-07 | Nach dem Neustart startet der Hinterhalt sofort am Auto | `Area3D.overlaps_body()` meldet nach einem Teleport noch einen Frame die alte Überlappung | 3 Physik-Frames Schonfrist | Playthrough (Mortal-Läufe) |
| B-M01-08 | Nach dem Neustart läuft man direkt ins Feuer | Gegner wurden **an Ort und Stelle** wiederbelebt, weiter alarmiert | `MissionEnemy.reset_to_spawn()` | test_mission + `UW_MISSION_SABOTAGE=4` |
| B-LVL-03 | Tod 1,3 s nach Betreten der Garage | Welle 1 stand **in** der Garage, gegen das verbindliche Layout §5 („von der Straße“) | Spawns auf Service-Lane und Gehweg | Playthrough |
| B-LVL-04 | Keine Deckungspunkte | Die 6 `Cover_*`-Anker aus Layout §3.3/§5 fehlten | Ergänzt, mit Agent-Abstand | test_level: 6 Anker, jeder **auf** dem Navmesh |
| B-LVL-05 | Dach-Schütze landet auf Jasons Autodach | Der „Dach“-Spawn lag in der Luft über der Straße | Auf das Garagendach | Playthrough |
| B-AI-05 | Hinterhalt kann ewig hängen | Freigegebene Wellen starteten „idle“ ohne Wissen über Jason | Briefing beim Freigeben (Wissensstand wie nach einem Schuss) | `=3` → hängt bei Ziel 4 |
| B-AI-06 | Alle Gegner kleben an der Bordsteinkante | NPCs hatten **keine Stufenlogik**: 16 cm Bordstein = Wand (betrifft die ganze offene Welt) | NPC-Step-up (≤ 0,3 m, wie beim Spieler) | test_level: Gunman steigt auf den Gehweg + `UW_AI_SABOTAGE=nostep` |
| B-UI-02 | Untertitel „Sam: Go look. Quietly.“ bleibt die ganze Mission über stehen (im Forward-Plus-Video gesehen) | Nach der letzten Zeile eines Anrufs hat niemand die Zeile geleert | `MissionManager` sendet am Ende ein leeres Untertitel-Signal | test_hud (vorher FAIL gesehen) + `UW_MISSION_SABOTAGE=5` |
| B-UI-03 | Munitionsanzeige zeigt „122/60“ (im Video gesehen) | Der Level-Generator speicherte die zur Laufzeit gebauten HUD-Widgets in die `.tscn`, `HUD._ready()` baute ein zweites Set; das gespeicherte blieb bei „12 / 60“ stehen | Generator speichert keine Laufzeit-Kinder (`uw_runtime_children`), HUD verwirft alte Widgets | test_hud: 0 gespeicherte HUD-Kinder, genau 1 AmmoLabel (vorher 15 / 2, FAIL gesehen) |
| B-AI-07 | Gegner geben auf und warten | Hinterhalt-Gegner fielen nach Zielverlust dauerhaft auf „idle“ zurück | Nach 3 s Leerlauf erneutes Briefing, nur für von der Mission freigegebene Gegner | Playthrough |

## 4. Testzahlen (`Tests/run_all.sh`, frischer Worktree)
| Suite | vorher | nachher |
|---|---:|---:|
| Smoke | 12 | 12 |
| uwp-Tool-Tests | 58 | 63 |
| Asset-Import | 71 | 71 |
| AI | 102 | 102 |
| Boot | 7 | 7 |
| HUD | 40 | 43 |
| Level | 23 | 32 |
| Mission | 109 | 114 |
| **Playthrough (neu)** | – | 14 |
| Player | 171 | 171 |
| Vehicle | 88 | 88 |
| Weapon | 68 | 68 |
| **Summe** | **749** | **785** |

Gemessen auf einem frischen Worktree (`git worktree add` + `git lfs pull` + `./Tests/run_all.sh`) → `RUN_ALL: PASS`.

### Sabotage (neu; alle alten Modi wurden erneut gefahren, siehe PR)
| Modus | Wirkung | Ergebnis |
|---|---|---|
| `UW_PLAYTHROUGH_SABOTAGE=1` | `interact` wird ignoriert | FAIL, hängt bei Ziel 5 |
| `UW_PLAYTHROUGH_SABOTAGE=2` | Paket wird nicht eingeladen | FAIL, hängt bei Ziel 6 |
| `UW_PLAYTHROUGH_SABOTAGE=3` | Wellen nicht gebrieft | FAIL, hängt bei Ziel 4 |
| `UW_MISSION_SABOTAGE=4` | Gegner wiederbelebt an Ort und Stelle | test_mission FAIL (1) |
| `UW_AI_SABOTAGE=nostep` | keine NPC-Stufen | test_level FAIL (1) |
| `UW_MISSION_SABOTAGE=5` | Untertitel wird nicht geleert | test_hud FAIL (1) |

## 5. Balance (gemessen, nicht entschieden) – TD-022
Gemessen mit dem verwundbaren Autopiloten über 3 Seeds, Deckel 15 min, **vor** den letzten Taktik-Verbesserungen des Bots. Das sind also Obergrenzen:
- Rohschaden 1,0: 8–14 Tode, keine Mission geschafft.
- Schadensfaktor 0,5: 5–6 Tode.

Der Bot ist schwächer als ein geübter Mensch: kein Seitwärtslaufen, keine Kopfschüsse. **Der Wert bleibt deshalb unverändert bei 1,0.** Die Schicht `Difficulty` ist eingebaut, die Entscheidung trifft die Eigentümerin nach einem GPU-Spieltest (Vorschlag: zuerst 0,5 testen).

## 6. Bilder und Video (Forward Plus, lavapipe, CPU)
`Docs/Reports/renders_fwdplus_m01/` – Beschreibung in `README.md` dort.

## 7. Was ausdrücklich NICHT behauptet wird
- Keine GPU-Leistung, keine FPS-Zahl, kein Urteil über das Fahr- oder Kamera-Gefühl in Echtzeit. lavapipe rendert mit etwa 15 % Echtzeit.
- Keine Kunstqualität: Alle Assets bleiben REJECT/WIP (Blockout), am Quality Gate hat sich nichts verändert.
- „Spielbar“ heißt hier: **per Eingabe schaffbar**, belegt durch den Bot. Ein Mensch hat M01 noch nicht gespielt.
- Seeds 1, 3 und 4 bleiben am Dach-Schützen hängen (B-007). Das Gate nutzt Seed 2.

## 8. Offene Punkte und Entscheidungen der Eigentümerin
1. **GPU-Spieltest von M01 durch einen Menschen** (Rest von T-BUILD-02): FPS, Fahrgefühl, Kamera, Balance (B-008 / TD-022).
2. Dach-Schütze: Position, Brüstung und Peek-Punkt neu designen (B-007).
2b. **B-VEH-01** (offen): Die Limousine kippt an einem 16-cm-Bordstein bei etwa 14 m/s (Video 0:22) → Schwerpunkt und Wankstabilität beim GPU-Fahrtest. **B-CAM-01** (offen): Die Kamera clippt beim Zielen nah an Wänden in Jason.
3. TD-021 (Playthrough-Gate) und TD-022 (Difficulty-Schicht) annehmen oder ablehnen.
4. Nächster Task laut §8: T-QA-01 (CI). Der Playthrough läuft headless in etwa 60 s und eignet sich als CI-Pflichtcheck.
