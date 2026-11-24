# Bericht T-LOOK-02 – Grafik-Pass: AgX, SSIL, Kapitel-Grading LA/NY, Material-Pass, Nässe

**Autor:** Claude Code · **Datum:** 2026-11-24 · **Status:** READY FOR REVIEW (nicht PRODUCTION-READY)

## 1. Was umgesetzt ist
| Baustein | Umsetzung |
|---|---|
| **Tonemapping** | Alle Looks laufen auf **AgX** statt ACES. Die Belichtung ist neu auf die TD-024-Ziele kalibriert. |
| **GI-Nahfeld** | Neben SSAO ist jetzt **SSIL** in jedem Preset aktiv. SDFGI bleibt aus (TD-024, nur mit GPU prüfbar). |
| **Kapitel-Grading** | `Grading` erzeugt eine 3D-LUT (17³) im Code, es gibt also keine Binärdatei. **LA:** goldene Lichter, ruhigere Schatten. **NY:** Stahlblau und festere Kurve, Neon bleibt gesättigt. `SunPreset.graded_environment()` und `GradedWorld` (M01) wenden sie zur Laufzeit an. |
| **NY-Presets** | `ENV_NY_Night` (Volumen-Nebel, SSR für nassen Asphalt) und `ENV_NY_Overcast`. |
| **Material-Pass** | `MaterialPass.apply()` läuft auf jedes Fahrzeug- und Figurenmodell, die Zuordnung erfolgt nach Materialnamen: **Klarlack** für Autolack (glTF verliert Blenders Coat), **SSS im Hautmodus** plus Rim für Haut, Klarlack für die Augen, Anisotropie für Haare, Stoffglanz für Kleidung und Sitze. |
| **Nässe** | `MaterialPass.set_wetness(root, 0..1)` macht Asphalt, Beton und Straßenfarbe dunkler und glänzender. Mit 0 sind die Werte wieder trocken. |

## 2. Messung (Look-Dev, Forward Plus, lavapipe)
| Preset | Graukarte 18 % vorher (ACES) | nachher (AgX + Grading) | Weiß 90 % nachher | Ziel |
|---|---|---|---|---|
| Golden Hour | 155/132/127 (Luma ≈ 138) | 153/131/119 (Luma ≈ 135) | 238/220/204 | 130–160, Weiß ≤ 250 ✔ |
| Mittag | 143/146/157 | 134/135/137 | 225/221/213 | ✔ |
| NY bewölkt | – | 122/132/146 (Luma ≈ 131) | 214/220/228 | ✔ |
| NY Nacht | – | 39/59/98 | 45/66/103 | wie LA-Nacht ✔ |

Unterwegs gefunden und behoben:
1. Die erste NY-Kurve drückte dunkle Töne auf null. Die Farbverschiebungen werden jetzt mit der Helligkeit skaliert.
2. Neonrot verlor 19 %. Gesättigte Farben sind jetzt ausgenommen, das prüft ein Test.
3. Der NY-Mond unter 35° lag im Schatten des Messaufbaus.

## 3. Tests
- `test_look.gd` (neu, im Gate):
  - AgX, SSAO und SSIL in jedem Preset.
  - Jedes Preset hat seine LUT. Die `.tres` auf der Platte bleibt LUT-frei.
  - LA wärmt, NY kühlt, Neon bleibt gesättigt.
  - Klarlack am Lack der Limousine.
  - SSS und Rim an Jasons Haut, Glanz an der Jacke.
  - Nasser Asphalt (Rauheit 1,00 → 0,15) und zurück trocken.
- **Negativkontrolle:** `UW_LOOK_SABOTAGE=1` lässt Lack, Haut, Jacke und Nässe korrekt durchfallen (4 FAIL).

## 4. Bilder
- `Docs/Reports/renders_look02/m01_before_after.jpg`: M01 vorher und nachher, gleiche Kameras.
- `Docs/Reports/renders_look02/m01_street_all_presets.jpg`: Calloway Ave in allen 5 Looks.
- `Docs/Reports/renders_look02/ny_night_wet.jpg`

## 5. Ehrlich: was das NICHT ist
- **Der Unterschied im Bild ist dezent.** Der Abstand zu Rockstar kommt vor allem aus Geometrie und Oberflächen, nicht aus der Nachbearbeitung. Es fehlen:
  - Decals (Risse, Reifenspuren, Gullis, Graffiti, Müll)
  - Kantenabnutzung und Schmutzmasken
  - Vegetation und Dichte
  - Hero-Details an Waffen und Autos

  Das ist der nächste Schritt (Restkatalog P2/P3, dann der Hero-Pass).
- **Nasser Asphalt:** Die Spiegelungen per SSR sind in dieser Kamera schwach, die Laternen sind weit weg. Echte Pfützen-Decals fehlen noch.
- **Ohne GPU** gibt es keine Aussage zu Leistung, SSR, Volumen-Nebel oder SSIL-Kosten.
- **Kein Asset ist PRODUCTION-READY.**
