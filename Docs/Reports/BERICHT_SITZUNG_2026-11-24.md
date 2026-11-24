# Sitzungsbericht 2026-11-23/24 – Content-first: P1 bis P6 umgesetzt

**Autor:** Claude Code · **Auftrag:** Eigentümerin, 2026-11-23: „10 Milestones bis zum fertigen Spiel … alles modellieren … durch die Pipeline … polishen … testen“.

## 1. Kurzfassung
- **Produktionsplan P1–P10** (`Docs/PRODUCTION_PLAN.md`) erstellt und von P1 bis P6 inhaltlich abgearbeitet.
- **Katalog:** von **17 auf 90 gebaute Assets** (WIP) von 101 geplanten. 11 stehen noch aus.
  - Die Inhalte kommen aus **eigenen Generatoren**, die Rezepte und Profile in Blender bzw. Godot umsetzen: Requisiten, Gebäude, Waffen, Fahrzeuge, Effekte.
  - Die Figuren kommen aus der bestehenden Charakter-Pipeline.
- **Jedes neue Asset ist geprüft:**
  - Release-Gate bzw. Export
  - Godot-Import
  - automatischer Test
  - Aufnahme in Forward Plus
  - jeder PR: frisches lokales Gate **und** grüne CI vor dem Merge
- **Zwei sichtbare Bugs behoben:**
  1. **Alle Gegner in M01 waren rote Kapseln** über ihrem Modell.
  2. Die Kollisionshülle der Limousinen-Familie war unsauber. Der neue Generator baut sie sauber; die Limousine selbst ist bewusst unverändert.

## 2. PRs
| PR | Task | Inhalt |
|---|---|---|
| #24 | T-LOOK-01 | Look-Dev-Kalibrierung, Presets, TD-024 |
| #25 | T-ANIM-01 Teil 1 | echte Animationsbibliothek (war ein Platzhalter) |
| #26 | T-DATA-01 (P1) | Kampf-Datenbank (Waffen, Rüstung, Stufen leicht/mittel/schwer/Boss, Fraktionen), Content-Katalog, `uwp catalog`, Produktionsplan |
| #27 | T-PROP-01 (P2/P3/P5) | `uwp build-props`: Materialbibliothek, Texeldichte, Lightmap-UVs, Schilder-Atlas; 27 Assets |
| #28 | T-BLDG-01 (P3) | `uwp build-buildings`: Fassaden-Grammatik, 8 LA-Gebäude |
| #29 | T-WPN-01 (P5) | `uwp build-weapons`: 9 geriggte Waffen, Nachladen an `combat.json` gekoppelt |
| #30 | T-CHAR-01 Teil 1 | **Kapsel-Bug behoben**, Rüstung je Stufe sichtbar |
| #31 | T-VEH-01 (P5) | `uwp build-vehicles`: 5 Autos, Flotten-Test im echten `vehicle.gd` |
| #32 | T-CHAR-01 Teil 2 (P4) | 13 Fraktions-, Boss- und NPC-Figuren, Bosse mit verdeckter Weste |
| folgend | T-FX-01 (P6) | `uwp build-fx`: 14 Effekte; Mündungsfeuer und Einschlag je Oberfläche bei jedem Schuss |

## 3. Was im Spiel jetzt anders ist
- **Gegner:** echte Figuren mit Fraktionsfarben statt Kapseln.
  - Mittlere Stufe mit Weste.
  - Schwere Stufe mit Plattenträger und Helm.
  - Bosse im Anzug mit verdeckter Weste, Kopftreffer sind der Konter.
  - Die neuen Waffen-Modelle liegen in der Hand.
- **Jeder Schuss:** Mündungsfeuer mit Lichtblitz. Jeder Treffer zeigt den passenden Einschlag: Blut, Funken am Auto, Betonstaub an der Wand.
- **Kampfwerte aus einer Datei:** `combat.json`. Gemessene Pistolen-Treffer bis zum Tod: Zivilist 3, leicht 4, mittel 6, schwer 11, Boss 31.

## 4. Ehrlich: was NICHT erreicht ist
- **Kein einziges Asset ist PRODUCTION-READY.** Alles ist Blockout+ bzw. WIP. Es fehlen Review ≥ 4, eine GPU-Prüfung und Hero-Details (Sculpt, Bake, Decals, Hair Cards).
- **M01 nutzt die neuen Gebäude noch nicht** (T-LVL-02):
  - Die Ausstattung war fertig, Bild: `Docs/Reports/renders_buildings/m01_dressed_preview_NOT_SHIPPED.jpg`.
  - Sie brachte aber den deterministischen Autopiloten beim Dach-Schützen (B-007) in einen Patt. Ich habe sie **zurückgenommen**, statt ein rotes Gate zu mergen.
  - Diagnose und Patch: `Docs/BLOCKERS.md` B-007, `Docs/Handoffs/T-LVL-02_level_dressing.patch`.
- **Offen im Katalog (11):**
  - Motorrad und Flugzeug (Mechanik in P7)
  - Trim-Sheets, Decals, Terrain (P2/P3)
  - 6 Animationssets: Sitzen, Deckung, Nahkampf, Mocap-Fortbewegung, Boss-Angriffe. **Dafür ist E-3 nötig (Animationsquelle).**
- **Figuren:**
  - Helle Stoffe werden zu dunkel.
  - Frisuren wirken wie eine Kappe.
  - Fußrutschen 4,6–5,1 cm (Grenze 1 cm).
- **Audio:** keine Audio-Bibliothek in dieser Sitzung.
- **Ohne GPU:** keine FPS-, Partikel- oder Fahrgefühl-Messung.

## 5. Umgebung
- `files2.makehumancommunity.org` und `github.com` wurden für die CC0-Charakterquellen zur Umgebung „1 Milliarde“ hinzugefügt, mit Freigabe über den Dialog.
- Der MakeHuman-Server liefert etwa 25 KB/s pro Verbindung. Ich habe parallel per Range-Requests geladen und jedes ZIP geprüft.
- **LFS** liegt nach dieser Sitzung grob bei 390 MB von etwa 1 GB. Die CI zieht nur neue Objekte (Cache).

## 6. Entscheidungen der Eigentümerin
| # | Frage |
|---|---|
| E-3 | Animationsquelle (Mocap, CMU/CC0 oder Mixamo). Blockiert die 6 Animationssets, Sitz-Clips und Fußrutschen < 1 cm. |
| E-8 | Gewaltdarstellung (Blut-Effekt ist gebaut, Freigabe offen). |
| neu | TD-025 bis TD-030 annehmen (Datenbank, Requisiten-Kit, Gebäude-Grammatik, Waffen, Fahrzeuge, Effekte). |
| neu | B-007: Soll der Dach-Schütze in M01 bleiben (dann mit Peek-Punkt an der Kante) oder auf den Boden? |
| E-5 | GPU-Hardware für die echte Abnahme. |
