# Bericht T-PROP-01 – P2/P3/P5: Requisiten-Generator und 27 neue Assets

**Datum:** 2026-11-23 · **Autor:** Claude Code · **Status:** READY FOR REVIEW · **TD:** TD-026 (PROPOSED)

## 1. Ergebnis
- `Tools/uwp build-props` baut Straßenmöbel, Gegenstände und Schutzausrüstung aus Rezepten in Blender, headless und reproduzierbar.
- Alle **27 neuen Assets** bestehen das **Release-Gate** `uwp export --profile gate`. Das Gate verlangt LODs, Kollision, Budgets, Texturen in Zweierpotenz und null degenerierte Flächen.
- Alle 27 importieren in Godot ohne Fehler oder Warnungen.
- Alle 27 sind in-engine in **Forward Plus** gerendert, im kalibrierten Golden-Hour-Look aus T-LOOK-01.

| Gruppe | Assets |
|---|---|
| Straße LA (P3, 15) | Kreuzung 14 × 14 m, Fußgängerüberweg, Ampel mit Mastarm, Hydrant, Mülleimer, Bushaltestelle, Maschendrahtzaun, Müllcontainer, Münztelefon, Zeitungsbox, Parkuhr, Straßenschild, Plakatwand, Busch, Strommast |
| Gegenstände (P5, 9) | Geldbündel, Handy, Goldbarren, Päckchen, Duffelbag, Ölfass, Europalette, Werkzeugkiste, Werkbank |
| Schutz (P5, 3) | leichte Weste, Plattenträger, taktischer Helm. Sie sind mit `combat.json` verknüpft (`armor.*.asset`). |

**Katalog:** 44 Assets sind gebaut (WIP), 57 geplant, 0 PRODUCTION-READY. Details stehen in `Docs/Reports/CATALOG_STATUS.md`.

## 2. Studio-Techniken (aus der Werkzeugliste), umgesetzt mit freien Mitteln
| Studio-Werkzeug | Unser Ersatz im Generator |
|---|---|
| Substance / Materialbibliothek | **Eine gemeinsame CC0-Bibliothek** aus 17 Poly-Haven-Sätzen, getönt, mit Metall- und Rauheitsanteil. Lackflächen übernehmen Normal- und Rauheitsstruktur eines echten Satzes. |
| Zen UV / TexTools (Texeldichte) | **UV0 als Box-Projektion in Weltmaßen.** Gemessene Texeldichte: **430–510 px/m** bei fast allen Assets, Budget ≥ 128. Hydrant und Container zeigen dieselbe Körnung. |
| Lightmap-UVs (Bakery / UVPackmaster) | **UV1 als eigenes, überlappungsfreies Lightmap-Layout**, bereit für LightmapGI (TD-024). |
| Trim-Sheet / DECALmachine | **Ein Schilder-Atlas pro Asset:** alle Beschriftungen in einer Textur (Zweierpotenz) und einem Material. Die Schrift ist auf jeder Fläche korrekt orientiert. Alle Namen sind erfunden: „Calloway Av“, „Sundown Cola“, „The Hollow Herald“. |
| Houdini-Sweeps | **Rohr-Sweep mit Parallel-Transport-Frame:** keine verdrehten Flächen an Knicken. Gefunden hat das das Gate (DEGENERATE_FACES). |
| Hard-Ops-Kanten | gefaste Kanten an allen harten Teilen |
| UCX-Kollision | **Handgesetzte konvexe Boxen.** Begehbare Kacheln bekommen eine flache Platte genau auf Asphalthöhe (Regel B-PT-01). |
| InstaLOD | LOD1 und LOD2 vom Exporter, Sichtweiten in Godot geprüft |

## 3. Belege
- **Release-Gate:** 27 von 27 PASS, 0 Fehler, 0 Warnungen. Die Dreiecke liegen bei 88 bis 1.172 pro Asset (Budget 5.000 bzw. 10.000), mit 1 bis 8 Materialien.
- **Godot:**
  - Import mit 0 Fehlern und 0 Warnungen.
  - Neuer Test `test_catalog_assets` in `Tests/Import/test_assets.gd` prüft jeden gebauten Katalog-Eintrag: Kollision vorhanden, LOD-Sichtweiten gesetzt, alle Flächen texturiert oder emissiv. Ergebnis: **PASS**.
  - **Negativkontrolle** `UW_ASSET_SABOTAGE=nocollision`: Ergebnis **FAIL**, wie erwartet.
- **uwp-Werkzeugtest [9]** (läuft in CI ohne Netz):
  - Ein synthetischer Textur-Cache, dann Bau von Hydrant, Straßenschild und Plattenträger, dann Release-Gate: PASS.
  - Der Schilder-Atlas ist nachgewiesen.
  - **Ohne Cache scheitert der Bau laut**, statt still graue Materialien zu erzeugen.
- **Bilder** in `Docs/Reports/renders_props/`:
  - `catalog_fwdplus_golden_hour.jpg`: alle 34 gebauten Umgebungs- und Requisiten-Assets in-engine (Forward Plus, lavapipe)
  - `street_corner_fwdplus_golden_hour.jpg`: eine dekorierte LA-Straßenecke nur aus Katalog-Assets
  - `props_cycles_previews.jpg`: Cycles-Vorschauen des Exporters
- **Speicher:** 15,2 MB GLB plus 13,3 MB `.blend`, alles in LFS.

## 4. Eigene Sichtprüfung (ehrlich)
- **Gut lesbar auf Spieldistanz:** Hydrant, Ölfass, Mülleimer, Container, Ampel, Plakatwand, Palette, Werkzeugkiste, Geldbündel, Goldbarren, Kreuzung und Überweg.
- **Schwach, bleibt Blockout+:**
  - **Busch:** Kugelhaufen statt Blattkarten. Kommt mit dem Vegetations-Generator in P2/P6.
  - **Westen:** grobe Form ohne Nähte oder Stoffsimulation. Für Pickups taugen sie, getragen auf der Figur brauchen sie Anpassung in P4.
  - **Maschendraht:** einzelne Drähte statt Alpha-Karte.
  - **Münztelefon:** einfache Form.
- **Kein Asset ist PRODUCTION-READY.** Dafür fehlen das unabhängige Review ≥ 4 und, bei Hero-Props, Sculpt- und Bake-Details (TD-021).
- Alle Bilder stammen aus lavapipe auf der CPU. Eine GPU-Prüfung fehlt (B-003/E-5).

**Fehler, die während der Arbeit gefunden und behoben wurden:**
1. Zebrastreifen der Kreuzung lagen um 90° gedreht.
2. Klebeband-Flackern durch koplanare Flächen.
3. Gespiegelte Schrift.
4. Verdrehte Rohrringe.
5. Texturen ohne Zweierpotenz.

## 5. Nächste Schritte (P2/P3)
1. `build-buildings`: Fassaden-Grammatik für die 8 geplanten Gebäude (Motel, Tankstelle, Lagerhalle M01, Hangar, Wohnhaus, Büroturm, Villa, Liquor Store), mit derselben Materialbibliothek.
2. Decals: Risse, Ölflecken, Graffiti erfundener Gangs.
3. Vegetations-Karten.
4. Danach P4 (Figuren) und P5 (Waffen, Fahrzeuge).
