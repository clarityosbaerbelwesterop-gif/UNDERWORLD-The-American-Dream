# Bericht T-NY-01 – New-York-Set für Kapitel 2 (erste Welle)

**Autor:** Claude Code · **Datum:** 2026-11-24 · **Status:** READY FOR REVIEW (Blockout+, nicht PRODUCTION-READY)

## 1. Was gebaut ist
Fünf neue Assets aus der Gebäude-Grammatik, alle mit Release-Gate PASS:

| Asset | Inhalt | Dreiecke | Mission |
|---|---|---|---|
| `SM_NY_Bldg_Brownstone` | Brooklyn-Reihenhaus mit 4 Ebenen. Stoop aus 9 Stufen mit Eisengeländern und Pfosten, Stürze, Gesims mit Konsolen. Brandwände aus Ziegel. | 1 702 | Ankunft, Brooklyn |
| `SM_NY_Bldg_Tenement` | 6 Geschosse. Zwei Läden (erfunden: „Spin City Laundromat“, „Checks Cashed“), zwei Feuertreppen, Wassertank. | 6 556 | Brooklyn |
| `SM_NY_Bldg_Bodega` | Eckladen mit Glasfront zu beiden Straßen, Markisen, Rollladen, „Hollow Deli & Grocery“ (erfunden). | 1 046 | Brooklyn |
| `SM_NY_Bldg_Bank` | Neoklassische Sparkasse mit Portikus, 4 Säulen, Giebel, Stufensockel und Bronzetür, „Holloway & Stern Savings Bank“ (erfunden). | 1 676 | Bankraub (M9) |
| `SM_NY_SubwayEntrance` | Treppenschacht 3,6 m tief, grüne Geländer, Kugellampen, Haltestelle „Hollow Av“ (erfunden). | 1 108 | Welt |

Dazu:
- **Neue Materialien:** Brownstone (Putz-Scan, auf Sandstein getönt), dunkler NY-Ziegel, Kalkstein, grüne Kugellampe (emissiv).
- **Validator:** Ein Asset darf mit `uw_below_grade_m` **genau so tief** unter Grund reichen, wie es angibt. Der Prop-Kit setzt das automatisch bei `keep_origin` (Treppenschacht). Alles andere bleibt `ORIGIN_GROUND`-Fehler.
- **NY-Licht:** `ny_overcast` hat jetzt eine schwache Sonne (0,55) mit 12° Lichtwinkel, also weiche Schatten. Himmelslicht 3,0, Belichtung 2,5. Gemessen: Graukarte Luminanz ≈ 125, Schattenkarte ≈ 96. Das passt zu Bewölkung: wenig Kontrast.

## 2. Look-Dev-Straße (`Tests/tools/capture_ny_street.gd`)
Zur Laufzeit zusammengesetzt aus:
- Bank, 3 Brownstones, Mietshaus und Bodega
- Kit-Gehweg und Kit-Straße
- 6 Laternen und Schaufensterlicht
- NY-Graffiti, Pfützen und Gulli

Bilder: `Docs/Reports/renders_ny01/`
- `ny_overcast_block.jpg`: Brooklyn-Block bei Bewölkung
- `ny_night_block.jpg`: nass, Laternen spiegeln sich im Asphalt
- `ny_overcast_bank.jpg`: Bank-Portikus
- `ny_set_catalog_sheet.jpg`: Katalog-Aufnahmen. Der Schacht des U-Bahn-Eingangs steht dort über Grund, weil das Werkzeug jedes Asset auf den Boden stellt.

## 3. Ehrlich offen
- **Kein spielbares NY-Level:** Die Straße existiert nur als Look-Dev-Aufnahme. Ein Brooklyn-Level mit Navmesh, Missionsankern und Verkehr ist der nächste NY-Schritt.
- **Noch nicht gebaut:** Innenräume (billiges Zimmer, Bank-Schalterhalle, Tresor), Farm, Lagerhäuser, Brücken, Hochbahn.
- **U-Bahn-Eingang:** Im Gehweg braucht er eine Aussparung. Das Kit-Gehwegteil hat noch keine.
- **Detail:** Fassaden ohne Kantenabnutzung, Fenster ohne Innenleben (Interior Mapping), keine Schaufenster-Auslagen.
- **Kein Asset ist PRODUCTION-READY.**
