# Bericht T-BLDG-01 – P3: Gebäude-Grammatik und 8 LA-Gebäude

**Datum:** 2026-11-23 · **Autor:** Claude Code · **Status:** READY FOR REVIEW · **TD:** TD-027 (PROPOSED)

## 1. Ergebnis
`Tools/uwp build-buildings` erzeugt Gebäude aus Regeln, so wie Studios es mit Houdini oder Geometry Nodes machen. Dafür gibt es eine Wand-Primitive mit **echten Öffnungen**: Laibung, zurückgesetztes Glas, Türen und Rolltore, Sohlbänke, Sprossen.

**Alle 8 geplanten Gebäude** bestehen das Release-Gate:

| Gebäude | Merkmale | Dreiecke | Materialien |
|---|---|---|---|
| Apartment4F | Backstein, 4 Etagen, Feuertreppe mit Leiter, Lobby, Vordach, Wassertank | 3.864 | 8 |
| Motel | 16 Zimmer mit Nummern, offene Galerie mit Geländer, Treppe, Mastschild „SUNNY DAYS MOTEL / VACANCY“ | 2.158 | 8 |
| GasStation | Kiosk, Tankdach mit Lichtfläche, 2 Zapfinseln, Preisschild „COASTLINE FUEL“ | 956 | 8 |
| Warehouse (M01) | Wellblech, Laderampe, 3 Rolltore mit Bay-Schildern, Oberlichter, Sockel | 1.442 | 7 |
| Hangar | Tonnendach, großes Tor, Seitenfenster, „SAN ARDO AIRFIELD“ | 492 | 6 |
| OfficeDowntown | 8 Etagen, Bandfassade mit Glas-Trim (Pfosten-Raster prozedural), Glaslobby, Penthouse, Antenne | 2.370 | 7 |
| VillaCrestmont (Sam) | Walmdach mit Tonziegeln, Balkon mit Glasbrüstung, Säulen, Garage, Kamin | 1.574 | 8 |
| LiquorStore | Schaufenster mit Gittern, Markise, Schild „VEGA LIQUOR & DELI“, Wandbild, Stufen-Attika | 1.028 | 8 |

Alle Namen sind erfunden. Es gibt keine echten Marken.

**Katalog:** 52 WIP, 49 geplant.

## 2. Belege
- **Release-Gate:** `uwp export --profile gate` besteht 8 von 8.
  - Zuerst fielen 3 Gebäude mit 9 Materialien durch. Das Gate verlangt höchstens 8 (Draw-Calls). Behoben durch Material-Disziplin.
- **Godot:** Import mit 0 Fehlern und 0 Warnungen. Der Katalog-Importtest (Kollision, LOD-Sichtweiten, texturierte Flächen) deckt die Gebäude automatisch ab.
- **uwp-Werkzeugtest [9]** (läuft in CI ohne Netz): Liquor Store und Hangar werden aus einem synthetischen Textur-Cache gebaut und bestehen das Release-Gate.
- **Bilder** in `Docs/Reports/renders_buildings/` (Forward Plus, lavapipe, Golden Hour):
  - `buildings_fwdplus_golden_hour.jpg`: alle 8 Gebäude
  - `street_corner_with_buildings_fwdplus.jpg`: dekorierte Straßenecke aus Gebäuden, Straßenkacheln und Requisiten, ausschließlich aus dem Katalog

## 3. Ehrliche Einordnung
- **Bewusste Grenzen:**
  - Die Gebäude sind **geschlossene Hüllen ohne Innenräume**. Betretbare Innenräume (Garage, Lager M01, Safehouses) kommen als eigene Innenraum-Kits mit LightmapGI.
  - **Noch fehlen:**
    - Decals (Schmutz, Risse, Graffiti)
    - Kantenabnutzung
    - Variation pro Instanz (Farbvarianten, Werbung)
    - HLOD bzw. Impostor für Fernsicht
- **Optik:** Auf Spieldistanz lesen sie sich klar als LA-Straße (siehe Straßenecke). Aus der Nähe zeigen Fassaden ohne Decals noch „saubere“ Flächen.
- **Status:** Blockout+, nicht Rockstar-Hero. **Kein Gebäude ist PRODUCTION-READY.** Dafür fehlen das Review ≥ 4, eine GPU-Prüfung und Hero-Details nach TD-021.

## 4. Nächste Schritte
1. **P2 Decals** (`build-decals`) und **Vegetations-Karten**: Sie heben Straße und Fassaden sichtbar am stärksten.
2. **P4 Figuren:** 13 Gegner-, Boss- und NPC-Specs für `build-character`. Gegner nach Stufe leicht, mittel, schwer und Boss je Fraktion.
3. **P5 Waffen und Fahrzeuge:**
   - 9 Waffen über eine parametrische Waffen-Grammatik (Gehäuse, Lauf, Schaft, Magazin, Visier)
   - 7 Fahrzeuge über Karosserie-Profile auf Basis der Limousine
