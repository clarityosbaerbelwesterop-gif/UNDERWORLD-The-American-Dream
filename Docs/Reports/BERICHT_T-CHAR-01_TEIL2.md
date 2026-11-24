# Bericht T-CHAR-01 Teil 2 – P4: 13 Fraktions-, Boss- und NPC-Figuren

**Datum:** 2026-11-24 · **Autor:** Claude Code · **Status:** READY FOR REVIEW

## 1. Ergebnis
Alle 13 geplanten Figuren sind über die bestehende Charakter-Pipeline (`uwp build-character`) gebaut, exportiert und in-engine geprüft. Die Pipeline nutzt CC0-Quellen von MakeHuman und MPFB2, 53 Knochen, Kleidung als eigene Meshes und gebackene Texturen.

| Fraktion | Leicht | Mittel | Schwer | Boss |
|---|---|---|---|---|
| Los Cuervos | Cartel A/B (vorhanden) | **Cuervos_Soldier** (weinrot) | **Cuervos_Heavy** | **El Jefe** (60er, grau) |
| La Hermandad del Sur | **Hermandad_A** (navy, blaue Jeans) | **Hermandad_Soldier** (Navy-Bomber) | **Hermandad_Heavy** | **El Patrón** (Navy-Anzug) |
| Kings of Flatbush | **Kings_A** (Senf), **Kings_B** (Bordeaux-Bomber) | **Kings_Lieutenant** (schwarzer Anzug) | – | – |
| FBI | – | – | **FBI_Tactical** | **Dana Whitlock** |
| Zivil | **Civ_Kit**-Basis (für das Varianten-Kit) | | | |

- **Kennzahlen:** 21,5k bis 25,5k Dreiecke pro Figur, 7 bis 8 Materialien. Bei den Laufclips liegt das Fußrutschen bei 4,6 bis 5,1 cm (siehe unten).
- **Export:** `uwp export` (dev) besteht **13 von 13**.
  - Zuerst fielen die beiden Bosse durch: Es gab kein Budget für die Kategorie `SK_Boss` (jetzt 30k Dreiecke) und die Anzugjacke clippte bei hoher Muskulatur (4,2 % bzw. 15,7 %). Mit Muskulatur auf Sams Niveau besteht der Export.
- **Godot:** Import mit 0 Fehlern und 0 Warnungen. Der Katalog führt jetzt 79 WIP und 22 geplante Einträge.

## 2. Bosse sehen aus wie Bosse
Bisher hätte der Boss-Archetyp Plattenträger und Helm über dem Anzug getragen; Gesicht und Anzug wären verschwunden. Neu (`combat.json`, `armor_concealed`):
- Bosse tragen eine **verdeckte schwere Weste** und **keinen Helm**.
- Die Körper-TTK bleibt bei 31 Pistolentreffern (Band 30–45). **Kopftreffer werden zum Konter.**
- Test: Der Boss hat 1 Rüstungsteil, und nichts wird über den Anzug gezeichnet.

## 3. Belege (Bilder)
- `Docs/Reports/renders_characters/lineups_factions_fwdplus.jpg`: Aufstellung je Fraktion in-engine, mit echtem `CombatDB.apply()`, Rüstung und neuen Waffen in der Hand. Es werden nur die Stufen gezeigt, die im Kader der Fraktion vorkommen.
- `Docs/Reports/renders_characters/characters_cycles_previews.jpg`: Cycles-Vorschauen des Exporters.

## 4. Ehrlich: was noch nicht gut ist
- **Kleidungsfarben:**
  - Die Tönung wirkt multiplikativ auf die Stoff-Textur.
  - Dunkle Denim-Sätze machten erst alle Hosen schwarz. Für die blauen Jeans ist das kalibriert (heller Denim-Satz wie bei der Zivilistin).
  - Helle Anzüge (El Jefe „creme“) werden weiterhin dunkelgrau.
  - Fix im Garment-Shader: Albedo normalisieren statt multiplizieren (P4-Feinschliff).
- **Frisuren:** Die meisten wirken wie eine Kappe. Hair Cards sind TD-021 bzw. Hero-Arbeit.
- **Dana Whitlock:** Gesicht mit dunklem Schatten unter der Lippe. Das ist ein Pipeline-Thema weiblicher Figuren (schon bei der Zivilistin sichtbar).
- **Fußrutschen:** 4,6 bis 5,1 cm, Release-Gate-Grenze 1 cm. Kommt mit T-ANIM-01 Teil 2 (E-3 Animationsquelle).
- **Status:** **Keine Figur ist PRODUCTION-READY.** Release-Gate (Clipping, Fußrutschen), Review ≥ 4 und GPU-Prüfung fehlen.
- **LFS:** Für die neuen Figuren werden nur Haupt- und Gesichtsvorschau committet statt 8 Bildern (spart rund 29 MB). Insgesamt kommen rund 165 MB dazu (GLB plus `.blend`).
