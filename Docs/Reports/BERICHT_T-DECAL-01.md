# Bericht T-DECAL-01 – Decals und Straßenoberflächen: weg vom Plastik-Look

**Autor:** Claude Code · **Datum:** 2026-11-24 · **Status:** READY FOR REVIEW (Blockout+, nicht PRODUCTION-READY)

## 1. Ergebnis in einem Satz
M01 hat jetzt **texturierten, sonnengebleichten Asphalt und Gehweg** statt flacher Graustufen. Darauf liegen **137 Decals**, vom Generator verteilt:

| Art | Anzahl |
|---|---|
| Gullideckel | 12 |
| Abflüsse | 22 |
| Risse | 54 |
| Ölflecken | 18 |
| Bremsspuren | 1 |
| Müll | 19 |
| Graffiti | 6 |
| Wandschmutz | 5 |

## 2. Was gebaut ist
| Baustein | Inhalt |
|---|---|
| `Tools/uwp build-decals` | **13 Decals** aus Python (numpy + Pillow), deterministisch je ID. Je Decal: Albedo mit Alpha, bei Relief eine Normal-Map, bei Glanzänderung eine ORM-Map, dazu eine Godot-Decal-Szene. Alles erfunden: Die Graffiti zeigen die Crews des Spiels (East Hollow, Los Cuervos, Kings of Flatbush), der Gullideckel trägt „HOLLOW CITY“. |
| Graffiti | Handstil: Scherung, Wellenverzerrung, doppelte Kontur, Overspray, Tropfen. Füllung und Kontur werden mit denselben Parametern verzerrt (der erste Versuch lief auseinander). |
| `build_decals_calloway.gd` | Platziert per Raycast. Abwärts-Strahlen erkennen Fahrbahn oder Gehweg am Knotennamen, Seitwärts-Strahlen vom Bordstein finden Hauswände. Ergebnis: `LA_CallowayAve_Decals.tscn`, vom Level instanziert. |
| Straßenoberflächen | Der Level-Builder hatte die Kit-Texturen durch **einfarbige Flächen** ersetzt (T-LVL-01a, damals mit Ersatz-Texturen). Jetzt texturierte PBR-Materialien: Asphalt-Körnung (2,5-fach feiner gekachelt), Gehwegplatten. Kit-Scans auf LA-Werte kalibriert: Asphalt sRGB 108, Gehweg 168. Das Level-Audit misst die **effektive** Albedo (Farbe × Texturmittel). |
| Licht M01 | Golden Hour: Sonne 12° → 18°, Himmelslicht 2,6 → 3,2. Grund: Bei 12° lag die ganze Straßenschlucht im Schatten, die Fahrbahn war fast schwarz (sRGB 13/16/28). Die Graukarte bleibt im Ziel (Luminanz 137, Weiß 238). |

## 3. Tests
- **`test_decals.gd` (neu):**
  - Szenen-Vertrag: Albedo, Fläche, flache Projektion.
  - Manifest gleich Bibliothek.
  - In M01 berührt **jedes** der 137 Decals seine Oberfläche.
  - Mindestens 6 sitzen an Wänden.
  - Negativkontrolle `UW_DECAL_SABOTAGE=1`: 126 schwebende Decals, FAIL.
- **`test_level.gd`:** grün mit texturierten Straßen. Straße 0,35, Gehweg 0,68, Bordstein 0,78, Abstand 0,33.
- **Release-Gate** für die 3 neu gebauten Straßenteile und den Gehweg.

## 4. Bilder
- `Docs/Reports/renders_decals/m01_street_before_after.jpg`
- `Docs/Reports/renders_decals/m01_decal_closeups.jpg`
- `Docs/Reports/renders_decals/decal_library_sheet.jpg`

## 5. Ehrlich offen
- **Nicht Rockstar-Niveau:** Es fehlen Fahrbahnränder mit Rinnstein-Schmutz, Flickstellen, Kaugummi, Ölspuren in Fahrspuren, Pfützen nach Wetter und weitere Graffiti-Stile. Die Decals sind generiert, nicht von Hand gemalt.
- **Decals malen auch auf Figuren**, die sehr nah stehen: Projektionstiefe 0,12 m am Boden, 0,3 m an Wänden. Sauber wäre eine eigene Render-Ebene für Figuren und Fahrzeuge (Cull-Maske).
- **Gebäude** haben noch keine Kantenabnutzung oder Schmutzmasken im Material. Wandschmutz gibt es nur als Decal.
- **Nachtpfützen in NY:** Das Decal ist gebaut, aber noch in keinem Level platziert, weil es kein NY-Level gibt.
