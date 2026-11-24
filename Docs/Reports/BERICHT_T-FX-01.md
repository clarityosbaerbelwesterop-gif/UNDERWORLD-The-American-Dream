# Bericht T-FX-01 – P6: Effekt-Bibliothek und Einschläge je Oberfläche

**Datum:** 2026-11-24 · **Autor:** Claude Code · **Status:** READY FOR REVIEW · **TD:** TD-030 (PROPOSED)

## 1. Ergebnis
`Tools/uwp build-fx` erzeugt 14 Effekt-Szenen (`GodotProject/Scenes/FX/`) aus einer Tabelle in `Scripts/tools/build_fx.gd`:
- Technik: GPUParticles3D mit ParticleProcessMaterial.
- Texturen sind **prozedural** (Radial-Verlauf, Rauschen). Es kommen keine neuen Binärdateien ins LFS (608 KB Text).

| Effekt | Ebenen | Verwendung |
|---|---|---|
| FX_MuzzleFlash | Blitz (additiv) + Rauchfahne + Lichtblitz (OmniLight, 60 ms) | **jeder Schuss** am `SOCKET_Muzzle` |
| FX_Impact_Concrete / _Metal / _Glass / _Wood | Staub + Splitter / Funken + Licht / Scherben / Holzsplitter | **jeder Treffer**, je nach Oberfläche |
| FX_Blood | Tropfen + Nebel | Treffer auf eine Hitbox (Freigabe E-8 offen) |
| FX_Sparks, FX_GlassShatter | Funkenregen, Glasbruch | Level und Mechaniken |
| FX_Smoke, FX_Fire, FX_Explosion | Rauchsäule; Flammen + Glut + Rauch + Licht; Feuerball + Rauch + Trümmer + Licht | Molotow, Granate, Autos (P7) |
| FX_Rain, FX_Steam_NY, FX_TireSmoke | Regenschlieren um die Kamera; Gullydampf; Reifenqualm | Wetter, New York, Fahrphysik (P7/P8) |

**Waffen-Integration** (`weapon.gd`):
- Jeder Schuss startet das Mündungsfeuer.
- Jeder Treffer startet den passenden Einschlag (`FXEffect.impact_id_for`):

| Getroffen | Effekt |
|---|---|
| Hitbox | Blut |
| Fahrzeug oder Gruppe `surface_metal` | Funken |
| Gruppe `surface_glass` | Glas |
| Gruppe `surface_wood` | Holz |
| alles andere | Beton |

- Die PT-Einschlagsdecals bleiben als Lochspuren erhalten.

## 2. Belege
- **Neuer Test `test_fx.gd`:** PASS. Darin geprüft:
  - Alle 14 Szenen sind FXEffect mit Partikel-Ebenen.
  - Einmal-Effekte räumen sich selbst ab, Dauer-Effekte bleiben.
  - Jeder Katalog-Eintrag hat seine Szenen.
  - **Echte Pistolenschüsse:** Wand ergibt `FX_Impact_Concrete`, Auto `FX_Impact_Metal`, NPC `FX_Blood`.
- **Negativkontrolle:** `UW_FX_SABOTAGE=1` ergibt FAIL (2).
- **Katalog:** Die 11 FX-Einträge stehen auf WIP (mit Mitgliedern); insgesamt 90 WIP und 11 geplant.
- **Bild:** `Docs/Reports/renders_fx/fx_fwdplus.jpg`, alle Effekte in Forward Plus im aussagekräftigen Moment. Leuchtende Effekte sind nachts aufgenommen, Staub und Rauch bei Tag.
- **Zwei Werkzeug-Funde** bei der Aufnahme, beide behoben:
  1. **Uhrzeit:** Skript-Aufnahmen liefen in Echtzeit. Auf der CPU dauert ein Frame bis zu 0,3 s, ein 60-ms-Mündungsfeuer fiel so zwischen zwei Frames. `godot_phase8_capture.sh --fixed-fps` macht die Zeit deterministisch.
  2. **Erster Frame:** Der erste Frame nach dem Szenenaufbau ist auf lavapipe schwarz (Shader-Kompilierung). Die Aufnahme hat jetzt eine Aufwärmphase.
- **Test-Fund:** `PROCESS_MODE_DISABLED` entfernt in Godot auch die Kollisionsobjekte, also die Hitboxen, aus der Physik. Tests stoppen NPC-KI deshalb nur über `set_physics_process(false)`.

## 3. Ehrlich offen
- **Optik:** Die Partikel sind Blockout+; es fehlen Flipbook-Texturen (Feuer und Rauch als Sequenzen) und Soft Particles.
- **Blut:** Die Darstellung hängt an der Freigabe E-8 (Rating).
- **Explosion, Feuer, Rauch:** Sie sind gebaut, aber erst mit Granate, Molotow und Autoschaden in P7 im Spiel.
- **Performance:** Partikel-Kosten sind ohne GPU nicht messbar (B-003/E-5).
