# UNDERWORLD – Produktionsplan bis zum fertigen Spiel (P1–P10, Content-first)

**Stand:** 2026-11-23 · **Autor:** Claude Code im Auftrag der Eigentümerin · **Status:** Arbeitsplan, Eigentümerin hat die Richtung vorgegeben („erst alles modellieren und produzieren, dann Mechaniken, dann rendern, polishen, spielen“).

Dieser Plan **ersetzt die Reihenfolge** der Roadmap M1–M10 aus `Docs/Prompts/CLAUDE_CODE_MASTER_PROMPT.md` §7. Die Inhalte bleiben, die Reihenfolge ist Content-first. Was schon existiert, wird nicht neu gebaut:
- Toolchain, CI, Pipeline mit Release-Gate
- M01-Logik und Eingabe-Autopilot
- Look-Dev-Kalibrierung
- 53-Bone-Skelett und Animationsbibliothek

## 0. Grundsätze
1. **Eine Quelle der Wahrheit für alle Daten.** Gegner, Waffen, Figuren, Fahrzeuge und Assets stehen in `Config/Content/` (JSON). Godot-Ressourcen und Bau-Aufträge werden daraus erzeugt, nichts wird doppelt gepflegt.
2. **Ein Befehl baut alles:** `Tools/uwp catalog build [--milestone Pn] [--profile gate]`. Er ruft je Katalog-Eintrag den Generator und den validierenden Exporter auf; `Tools/uwp catalog status` schreibt den Status (eigenes Production-Tracking, kein ShotGrid nötig).
3. **Jedes Asset geht durch das Release-Gate.** Dazu gehören `uwp --profile gate`, Look-Dev-Renders und Review ≥ 4. Nur dann ist es PRODUCTION-READY.
4. **Ehrlichkeit über Qualität:**
   - Generatoren liefern sofort für alles eine saubere, spielbare Basis (Blockout+).
   - Rockstar-Niveau bei Hero-Assets (Gesichter, Kleidung, Hauptfahrzeuge) braucht gestaltete Quellen: Sculpt, Retopo, Bake, Paint (TD-021).
   - Die Pipeline nimmt diese Quellen ohne Umbau auf.
5. **Jede Mechanik:** Headless-Tests, Sabotage-Modus und, wo sie sichtbar ist, eine Forward-Plus-Aufnahme. Am Ende spielt der Eingabe-Autopilot jede Mission durch.

## 1. Werkzeuge und Tricks (aus den Studio-Empfehlungen) – wie wir sie nutzen
| Studio-Werkzeug | Zweck | Unser Weg jetzt (frei, automatisierbar) | Kommerziell (Entscheidung E-4) |
|---|---|---|---|
| Houdini / Geometry Nodes | prozedurale Gebäude, Kabel, Scattering | **Blender-Python-/Geometry-Nodes-Generatoren** im Repo (Gebäude, Zäune, Kabel, Trümmer) | Houdini Engine |
| Substance 3D Painter | PBR-Texturierung, Kantenabnutzung | **bpy-Shader-Bake:** Curvature/AO-gesteuerte Abnutzung, CC0-Materialien (Poly Haven, ambientCG) | Substance (Abo) |
| Marmoset Toolbag | Bake Normal/AO/Curvature, Cage | **Cycles High→Low-Bake** in `uwp` (Cage, Normal, AO, Curvature) | Marmoset |
| RizomUV / Zen UV / UVPackmaster / TexTools | UVs, Texel Density, Trim-Sheets | **Texel-Density-Validator** in `uwp` + Trim-Sheet-Bibliothek (Straße, Fassade, Metall) + Smart-UV + Pack | RizomUV, UVPackmaster |
| DECALmachine | Details ohne Mesh-Schnitte | **Decal-Bibliothek** (Risse, Ölflecken, Graffiti erfundener Gangs, Schilder) → Godot `Decal`-Knoten | DECALmachine |
| RetopoFlow / Quad Remesher | Retopo nach dem Sculpt | Blender-Retopo-Workflow (Shrinkwrap + Remesh) für Hero-Assets | Quad Remesher |
| InstaLOD | LOD-Ketten, HLOD, Impostor | **LOD-Kette in `uwp`** (Gate erzwingt LODs) + HLOD pro Block + Impostor-Bake für Fernsicht | InstaLOD |
| SpeedTree | Vegetation mit Wind und LOD | **Palmen-, Baum- und Busch-Generator** (Blender) + Godot-Wind-Shader | SpeedTree |
| Gaea / World Creator | Terrain, Erosion | **numpy-Erosions-Heightmap** → Godot-Terrain (San-Ardo-Berge, ländlicher Norden) | Gaea |
| RealityCapture / Metashape | Photogrammetrie | CC0-Scans (Poly Haven) nur mit Lizenz-Eintrag | RealityCapture |
| USD / Omniverse | große Szenen | glTF bleibt Austauschformat (TD-003); USD erst bei Bedarf | – |
| ShotGrid / ftrack | Tracking, QC | **Content-Katalog + `uwp catalog status`** (`Docs/Reports/CATALOG_STATUS.md`) | ShotGrid |
| MeshSync / GoB / Better FBX | Live-Brücken, sauberer Export | `uwp` prüft Achsen, Maßstab und Skelett (TD-004/005) für **jede** Quelle | – |
| Custom Python QC | Ein-Klick-Validatoren | **`uwp validate/export --profile gate`** (existiert, wird pro Meilenstein erweitert) | – |

Sicherheitsregel bleibt: Blender-Add-ons oder MCP-Server aus fremden Quellen nur nach Code-Review und TD (§11). Die Blender-**API** nutzen wir direkt.

## 2. Die 10 Meilensteine
Jeder Meilenstein endet mit gemergten PRs, grüner CI, einem deutschen Bericht in `Docs/Reports/` und Forward-Plus-Bildern.

### P1 – Content-Bibel und Datenbank *(Fundament für alles Weitere)*
- **Kampf-Datenbank** `GodotProject/Data/Content/combat.json` (liegt in `res://`, weil das Spiel sie zur Laufzeit liest):
  - Gegner-Stufen **leicht / mittel / schwer / Boss**, dazu Zivilisten, Polizei, FBI und Verbündete.
  - Je Stufe: Gesundheit, Schutz (Weste, Helm), Waffen, Zielgenauigkeit, Angriffsmuster, Verhalten.
  - Waffenkatalog (Schaden, Feuerrate, Reichweite, Magazin, Nachladezeit, Streuung, Rückstoß).
- **Schutzsystem:** Weste und Helm reduzieren Schaden pro Trefferzone und verschleißen.
- **Godot-Generierung:** `AIProfile`, `WeaponData` und Archetyp-Ressourcen entstehen aus dem JSON. Ein Konsistenztest prüft, dass jede Referenz existiert und die Werte in den Bändern liegen.
- **Content-Katalog** `Config/Content/catalog.json`: jedes Asset von Kapitel 1 und 2 mit ID, Typ, Spec, Generator, Status und Priorität.
- **`Tools/uwp catalog check|status|plan|build`:** Querprüfung, Statusbericht, offene Arbeit je Meilenstein, Batch-Bau.
- **Exit:** Datenbank in Godot, Katalog vollständig, `catalog check` ist Teil des Merge-Gates (inkl. Negativtests), Batch-Bau als Befehl (in der CI als Dry-Run geprüft).
- **Stand 2026-11-23: erledigt** (T-DATA-01, `Docs/Reports/BERICHT_T-DATA-01.md`).

### P2 – Werkzeuge auf Studio-Niveau
- **Stand 2026-11-23:** Requisiten-Generator `uwp build-props` mit Materialbibliothek, Texeldichte-Regel, Lightmap-UVs und Schilder-Atlas fertig (T-PROP-01, TD-026). Gebäude-Grammatik `uwp build-buildings` fertig (T-BLDG-01, TD-027, 8 Gebäude). Offen: Decals, Vegetations-Karten, HLOD/Impostor, Terrain.
Trim-Sheet-Bibliothek, Texel-Density-Validator, Decal-Bibliothek, High→Low-Bake-Strecke mit Curvature-Wear, Gebäude-Generator (Fassaden-Grammatik: Erdgeschoss, Etagen, Gesims, Fenster, Türen, Markisen, Schilder), Vegetations-Generator, HLOD/Impostor-Bake, Terrain-Erosion.
- **Exit:** Jedes Werkzeug ist getestet (uwp-Tests) und mit Vorher/Nachher dokumentiert.

### P3 – Umgebung Los Angeles (Kapitel 1) komplett
- **Gebäude:** Shop, Wohnblock, Motel, Tankstelle, Lagerhaus, Hangar, Garage innen, Bürohaus Downtown, Villa Crestmont.
- **Straße:** Ampel, Zebrastreifen, Hydrant, Mülleimer, Bushaltestelle, Zaun, Container, Telefonzelle, Zeitungsbox, Parkuhr, Schilder mit erfundenen Namen, Graffiti, Laternen.
- **Natur:** Palmen, Büsche, Terrain der Hügel.
- **Level:** Calloway Ave final, Lagerhaus, privater Hangar.
- **Exit:** Alle Kit-Teile Gate-PASS, Level-Shots Forward Plus.

### P4 – Figuren und NPCs
- **Jason final:** Hair Cards, Skin-Fade, Bart, Bomberjacke mit Rippbündchen, Stiefel, LOD0–2.
- **Story-Figuren:** Marco, Sam, Dana Whitlock.
- **Gegner nach Stufe:**
  - Los Cuervos: leicht, mittel, schwer, Boss
  - La Hermandad: leicht, mittel, schwer, Boss
  - Kings of Flatbush
- **Polizei und Zivilisten:** LAPD-Streife (fiktiv), FBI-Taktik, Zivilisten-Baukasten (Körper × Kopf × Kleidung × Farbe → ≥ 40 Varianten).
- **Exit:** Eigene Gesichter (Vergleichs-Sheet), Gate-PASS, Clipping 0.

### P5 – Waffen, Fahrzeuge, Gegenstände
- **Stand 2026-11-23:** Gegenstände und Schutz fertig (T-PROP-01). Alle 10 Waffen gebaut (T-WPN-01, Waffen-Grammatik, Reload an `combat.json` gekoppelt). Fahrzeuge: 5 von 7 gebaut (T-VEH-01); Motorrad und Flugzeug folgen mit ihrer Mechanik in P7.
- **Waffen:** Pistole, Revolver, Maschinenpistole, Schrotflinte, Sturmgewehr, Scharfschützengewehr, Messer, Schlagstock, Granate, Molotow.
- **Fahrzeuge:** Limousine, Pickup, Lieferwagen, Polizeiwagen, Muscle-Car, NY-Taxi, Motorrad, Kleinflugzeug („Wings“). Jeweils Glas, Chrom, Innenraum und Schadensstufen.
- **Gegenstände:** Paket, Geldbündel, Handy, Goldbarren, Kokainpaket (stilisiert), Taschen, Kisten, Werkzeuge.
- **Exit:** Gate-PASS, Sockets und Fahrdaten aus der Datenbank.

### P6 – Animationen, Effekte, Audio-Bibliothek
- **Animationen:**
  - Mocap-Quelle laut E-3
  - Locomotion-Blendspace (Start, Stop, Pivot), Deckung, Nahkampf
  - Fahrzeug: ein-/aussteigen, Sitz Fahrer und Beifahrer, Motorrad
  - Gesicht und Lipsync
  - Boss-Angriffe
  - Fußrutschen ≤ 1 cm (Gate-Regel existiert)
- **VFX:** Mündungsfeuer je Waffe, Einschläge je Material, Blut (Altersfreigabe E-8), Rauch, Feuer, Explosion, Funken, Glassplitter, Regen, Dampf (NY), Reifenqualm.
- **Audio:** Waffen, Fahrzeuge, Ambience, Foley (nur CC0/CC-BY, jede Quelle in `ASSET_LICENSES.md`).

### P7 – Mechaniken komplett
Deckung und Vault, Waffenrad und Inventar, Nahkampf, Schutz und Gesundheit, Boss-Logik (Phasen, Spezialangriffe), Polizei und Wanted-Level, Verkehr mit Ampeln, Fußgänger-Tagesablauf, Schadensmodell und Ragdoll, Speichern und Laden, Handy und Minimap/GPS, Wirtschaft, Taxi, Wetter, Tageszeit.
- **Exit:** Jede Mechanik mit Tests und Sabotage.

### P8 – Missionen und Welt
- Kapitel 1 (Arrival, The Route, Dead Drop, The Raid, Wings) und Kapitel 2 (Stationen 6–16), gebaut auf fertigem Content. Je Mission zuerst das Design-Dokument (DRAFT, Abnahme durch die Eigentümerin).
- Offene Welt LA und NY mit Chunk-Streaming und HLOD.
- **Exit:** Der Eingabe-Autopilot spielt jede Mission durch.

### P9 – Rendern, Polish, Performance
GPU-Abnahme (E-5), finaler Look, Tag/Nacht, LOD/HLOD-Budgets, 60 fps auf Mittelklasse, Audio-Mix, Menüs, Einstellungen, Barrierefreiheit, Lokalisierung DE/EN.

### P10 – QA, Spielen, Release
Soak-Tests, Bug-Burndown, menschliche Playtests, Side-Quests und Zusatzfiguren, Store-Seite, Altersfreigabe, Lizenzdatei, signierter Build. Jede externe Einreichung erst nach OK der Eigentümerin.

## 3. Reihenfolge und Parallelität
P1 → P2 → (P3 ∥ P4 ∥ P5) → P6 → P7 → P8 → P9 → P10. Die CI läuft durchgehend; jedes neue Asset kommt per Katalog automatisch in den Batch-Bau.

## 4. Entscheidungen, die den Plan beschleunigen (Eigentümerin)
| # | Frage | Wirkung |
|---|---|---|
| E-3 | Animationsquelle (Mocap, CC0/CMU, Mixamo per TD) | blockiert P6 |
| E-4 | Kommerzielle Werkzeuge aus Tabelle 1 (Budget) | beschleunigt P3–P5 deutlich |
| E-5 | GPU-Hardware für die Abnahme | blockiert P9 |
| E-8 | Altersfreigabe-Ziel (Blut, Gewalt) | beeinflusst VFX und Animationen |
| neu | Gegner-Werte in `combat.json` abnehmen (DRAFT) | Balance P7 |
