# Sitzungsbericht 2026-11-23 – Claude Code (Master-Prompt §8, Tasks 1–5 + T-ANIM-01 Teil 1)

## 1. Kurzfassung
- **Toolchain steht in der Cloud:** exakte Studio-Versionen (Blender 5.2.4 LTS, Godot 4.7.2). Erstmals rendert der **Shipping-Renderer Forward Plus** ohne GPU, über Mesa lavapipe auf der CPU, auch in der GitHub-CI.
- **M01 war für Menschen nicht spielbar. Jetzt ist es das, belegt per Eingabe-Autopilot:** 20 Blocker in Pipeline, Level, Mission, KI und HUD sind behoben, dazu ein Video von 3:45 min in Forward Plus.
- **CI ist live:** Jeder PR fährt `run_all` + Linux-Export + Forward-Plus-Shots. Lauf #3 grün; die Negativkontrolle mit Sabotage wird rot.
- **Pipeline hat ein Release-Gate** (`uwp --profile gate`): 8 von 17 Quellen bestehen es technisch, alle Charaktere und die Limousine fallen durch.
- **Look ist kalibriert und messbar:** Graukarte, Licht:Schatten-Verhältnis, ein gemeinsamer Preset-Satz für Level und Look-Dev.

## 2. PRs
| PR | Task | Inhalt | Gate |
|---|---|---|---|
| #20 | T-ENV-01 | Cloud-Toolchain, Forward Plus auf lavapipe, Movie Maker | 749 ✓ |
| #21 | T-BUILD-02 | Eingabe-Autopilot als Merge-Gate, 20 Blocker behoben, M01-Video | 785 ✓ |
| #22 | T-QA-01 | GitHub Actions CI, LFS-Cache, Hygiene-Check | 785 ✓ lokal + CI |
| #23 | T-PIPE-06/05 | Audit, Release-Gate, TD-012-Budgets, `ANIM_FOOT_SLIDE`, TD-021 Hybrid-Pipeline | CI ✓ |
| #24 | T-LOOK-01 | Look-Dev-Kalibrierung, Presets für das Level, TD-024 GI | 792 ✓ lokal + CI |
| folgend | T-ANIM-01 (Teil 1) | echte Animationsbibliothek wiederhergestellt (war 208-Byte-Platzhalter), NPC-Clip-Ausleihe, Platzhalter-Scan | siehe PR |

## 3. Wichtigste Funde (Auswahl)
1. `interact` (E/Y) war nie verdrahtet, das Paket nicht aufhebbar.
2. Das Paket wurde nie ins Auto geladen, die Lieferung war unmöglich.
3. Die Endkarte endete nie; nach dem ersten Tod gab es keine Steuerung mehr.
4. Die Garage war um 180° gedreht und ihr Tor durch eine LOD2-Kollision verschlossen.
5. Fahrbahnmarkierungen und Bordstein-Linien waren Mini-Wände; NPCs kamen keinen Bordstein hoch.
6. Ein doppeltes HUD zeigte „122/60“.
7. Die gemeinsame Animationsbibliothek war in git ein leerer Platzhalter.

## 4. Was NICHT erreicht bzw. NICHT behauptet wird
- Keine GPU-Messung (FPS, Fahrgefühl, Eingabelatenz). Kein Mensch hat M01 gespielt.
- Keine Kunst auf AAA-Niveau. Alle Assets sind weiterhin REJECT/WIP. Die Pipeline prüft jetzt strenger, aber Hero-Assets brauchen gestaltete Quellen (TD-021: Sculpt, Hair Cards, Mocap).
- Offen:
  - Sitz-Clips (B-011)
  - Dach-Schütze (B-007)
  - Balance (B-008)
  - Limousine kippt am Bordstein (B-009)
  - Zielkamera-Clipping (B-010)
  - Nacht-Look
  - Foot-IK

## 5. Entscheidungen der Eigentümerin
| # | Frage |
|---|---|
| E-3 | Animationsquelle: Mocap, CC0/CMU oder Mixamo? Blockiert T-ANIM-01 Teil 2 (Sitz-Clips, Fußrutschen < 1 cm). |
| E-4 | Kommerzielle Werkzeuge (Substance, Marvelous, Character Creator)? Betrifft TD-021. |
| neu | TD-021 Hybrid-Pipeline, TD-022 Difficulty-Wert, TD-023 Playthrough-Gate, TD-024 GI: annehmen? |
| neu | Look-Sign-off: Golden Hour und Mittag (Bilder in `renders_lookdev/`). |
| neu | Branch-Schutz: „CI / gate“ als Pflicht-Check auf `main` setzen (Repo-Einstellung). |
| E-5 | GPU-Hardware für die echte Abnahme (T-BUILD-02, GPU-Teil). |

## 6. Umgebung
- `lfs.github.com` wurde für LFS-Uploads zu den erlaubten Hosts der Umgebung „1 Milliarde“ hinzugefügt.
- Die eingesetzten Agenten und Skills stammen aus „Claude Code Game Studios“ (MIT), das das Setup-Skript dieser Umgebung installiert. Fremde Hooks oder MCP-Server habe ich nicht aktiviert.
