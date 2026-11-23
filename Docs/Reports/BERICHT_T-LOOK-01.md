# Bericht T-LOOK-01 – Look-Dev in Forward Plus (Sign-off-Paket für die Eigentümerin)

**Datum:** 2026-11-23 · **Autor:** Claude Code · **Renderer:** Forward Plus (Vulkan) auf Mesa lavapipe, also CPU. Der Look entspricht dem Shipping-Renderer; zur GPU-Leistung sagen die Bilder nichts.

## 1. Kurzfassung
- Neue Kalibrierszene `Scenes/LookDev/LookDev_Calibration.tscn` (Generator `Scripts/tools/build_lookdev.gd`) nach VFX-Look-Dev-Standard:
  - 18-%-Graukarte, 90-%-Weiß- und 4-%-Schwarzkarte sowie eine Füllkarte, die nur Himmelslicht bekommt
  - Chrom- und Graukugel
  - 24-Feld-Farbtafel
  - Hero-Reihe: Jason, Pistole, Limousine, LA-Shop
- **Eine Quelle für den Look:** `Scripts/game/sun_preset.gd` (Sonne/Mond) plus `Assets/Environments/ENV_LA_*.tres`. Das Level M01 nutzt jetzt **dieselben** Presets. Vorher hatte der Level-Generator eine eigene Sonne und eine Inline-Umgebung (FILMIC statt ACES, doppelte Nebeldichte), deshalb waren die M01-Bilder beige und ausgewaschen.
- Die Presets sind **gemessen** abgestimmt, nicht nach Gefühl. Die Messwerte der Karten aus dem fertigen, getonemappten Bild stehen in Tabelle 2.
- **TD-024 (PROPOSED): kein SDFGI als Standard.** Himmelslicht + SSAO + Reflection Probes; LightmapGI für Innenräume. Begründung in Abschnitt 4.

## 2. Messwerte (sRGB 0–255, Mittel über 9×9 Pixel, `lookdev_metrics.json`)
| Preset | 18 % Grau beleuchtet | 18 % Grau Schatten (Himmel) | 90 % Weiß | 4 % Schwarz | Licht:Schatten (linear, G-Kanal) |
|---|---|---|---|---|---|
| golden_hour | 155 / 132 / 127 (warm) | 45 / 54 / 87 (kühl-blau) | 242 / 232 / 230 | 63 / 47 / 42 | ≈ 6 : 1 |
| midday | 143 / 146 / 157 (neutral) | 43 / 61 / 94 (blau) | 235 / 236 / 241 | 57 / 59 / 66 | ≈ 5 : 1 |
| night | 37 / 54 / 105 (Mondlicht) | 0 / 0 / 20 | 30 / 50 / 108 | 0 / 6 / 30 | Nacht: Laternen tragen die Szene |

**Zielbänder, die ich als Vorschlag gesetzt habe** und die die Eigentümerin abnehmen muss:
- Beleuchtete 18-%-Karte am Tag bei sRGB 130–160.
- 90-%-Weiß nicht geclippt (≤ 250).
- Licht:Schatten am Tag zwischen 4:1 und 9:1 (Filmlook mit „langen Schatten“, Art Direction).
- Schatten kühl (B ≥ R), Licht in der Golden Hour warm (R > G > B).

**Golden Hour und Mittag liegen in allen Bändern.** Die Nacht ist noch nicht abgestimmt: Ohne Laternen in der Look-Dev-Szene bleibt nur der Mond übrig.

### Verlauf der Abstimmung (ehrlich)
1. Ausgangslage: Die Graukarte lag im Gegenlicht und die Schatten waren **violett** (33/17/26), weil der Horizont des Himmels zu rot war.
2. Rig zur Sonne gedreht, Belichtung 1,05 → 0,58 (golden hour) bzw. 0,74 (Mittag).
3. Himmelslicht kühler und stärker (`ambient_light_color` blau, `sky_contribution` 0,55, `energy` 2,6). Licht:Schatten ging von ≈ 30 : 1 auf ≈ 6 : 1.

## 3. Bilder (`Docs/Reports/renders_lookdev/`)
| Datei | Was man sieht |
|---|---|
| `lookdev_golden_hour.jpg` | Kalibrierung, Jason ganz und als Nahaufnahme, Pistole, Limousine, Übersicht. Warmes Führungslicht, blaue Schatten. Die Kunst ist weiterhin Blockout (Haare wie Mütze, Pistole schwarzer Block). |
| `lookdev_midday.jpg` | Neutral, wirkt hell bis leicht ausgewaschen; Boden fast weiß. **Prüfpunkt für das Sign-off.** |
| `lookdev_night.jpg` | Nur Mondlicht, sehr dunkel. Nacht-Look braucht Laternen und Neon (später). |
| `gi_comparison_golden_hour.jpg` | Himmelslicht vs. SDFGI. Mit SDFGI fällt die Schattenfüllung auf 9/4/10, also fast schwarz. |
| `m01_before_after.jpg` | M01 vorher (Inline-Umgebung, beige) und nachher (Golden-Hour-Preset). Nachher: Himmelsverlauf und Kontrast. **Ehrlich:** Der Boden jenseits des Blocks wirkt orange-braun und die Straße sehr dunkel. |

## 4. GI-Entscheidung – TD-024 (PROPOSED)
| Option | Befund | Urteil |
|---|---|---|
| SDFGI | Mit den heutigen Presets kippt die Füllung auf fast Schwarz. Jedes Preset müsste neu abgestimmt werden; Konvergenz und GPU-Kosten sind ohne GPU nicht messbar | später auf GPU prüfen (offene Welt, Tageszeit) |
| VoxelGI | begrenzte Volumen, für Straßenzüge ungeeignet | nur für einzelne Innenräume |
| LightmapGI | gebacken, statisch, beste Qualität und Leistung für Innenräume (Garage, Lagerhaus) | **Innenräume** (Bake später, auf GPU deutlich schneller) |
| Himmelslicht + SSAO + Reflection Probes | messbar abgestimmt, billig, stabil | **Standard für Außen (jetzt)** |

## 5. Was NICHT behauptet wird
- Keine GPU-Leistung. Kein Urteil über SDFGI auf echter Hardware.
- Die Assets sind weiterhin Blockout/REJECT. Der Look hilft, die Kunst ersetzt er nicht.
- Die Zielbänder sind ein Vorschlag: **Das Sign-off fehlt.**

## 6. Entscheidungen für die Eigentümerin
1. Golden-Hour-Look abnehmen oder Richtung vorgeben (wärmer, kühler, weniger Kontrast)?
2. Zielbänder aus Abschnitt 2 als verbindlich übernehmen?
3. TD-024 annehmen: kein SDFGI jetzt, LightmapGI für Innenräume, SDFGI-Test auf GPU später?
