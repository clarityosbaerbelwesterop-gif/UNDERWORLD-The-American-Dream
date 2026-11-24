# Bericht T-LVL-02 – M01 mit dem neuen Kit ausgestattet; B-007 gelöst

**Datum:** 2026-11-24 · **Autor:** Claude Code · **Status:** READY FOR REVIEW

## 1. Ergebnis
Die Calloway Avenue in M01 besteht nicht mehr aus grauen Platzhalter-Boxen.
- **Westblock:**
  - Liquor Store „Vega Liquor & Deli“
  - 8-stöckiger Büroturm
  - Stuck-Laden
  - Backstein-Wohnhaus mit Feuertreppe und Wassertank
- **Kreuzung:** Ampel mit Mastarm und Straßenschild „CALLOWAY AV / E HOLLOW BLVD“.
- **Straßenmöbel (14):** Hydranten, Mülleimer, Zeitungsboxen, Münztelefon, Parkuhren. Sie stehen außerhalb der Gehlinie (Gehweg-Mitte x = −31); die NPC-Wege bleiben frei.
- **Geparkte Autos:** Muscle-Car, NY-Taxi und Polizeiwagen statt roter Boxen.
  - Die **Deckungsboxen bleiben** unverändert, damit KI-Deckung und Balance gleich bleiben.
  - Die eigene Hülle der Autos entfernt `VisualOnly` beim Laden. Eine Instanz kann man im Level nicht dauerhaft ändern, und Mesh-Kopien hätten die Level-Datei auf 1,7 MB Text aufgebläht.
- Ostblock mit Garage und Lagerhalle (Lieferziel) sowie die Missionsanker bleiben unverändert.

## 2. B-007 (Dach-Schütze) – Ursache und Lösung
1. **Ursache 1:** Ohne Sicht lief der Dachschütze zur letzten bekannten Spielerposition und blieb am Navmesh-Rand 2 m hinter der Dachkante stehen. Dort sieht niemand niemanden.
   - **Lösung:** Er ist jetzt ein **Posten an der Dachkante**: kein Laufen, keine Deckungssuche.
2. **Ursache 2:** Die Kamera des Autopiloten liegt höher als der Lauf. Sie „sah“ den Schützen, aber jede Kugel traf die Dachkante.
   - **Lösung:** Ein Ziel gilt nur als sichtbar, wenn auch die **Schusslinie aus Laufhöhe** frei ist; sonst sucht er eine Schussposition. So verhält sich auch ein Mensch.

**Ergebnis (M01 nur per Eingabe):**

| Seed | vorher | jetzt |
|---|---|---|
| 1 | hängt | PASS 193,0 s |
| 2 | PASS 221,9 s (82 Schüsse) | PASS 200,2 s (47 Schüsse) |
| 3 | hängt | PASS 192,2 s |
| 4 | hängt | PASS 195,4 s |
| 5 | PASS | PASS 190,2 s |

## 3. Belege
- **Tests:**
  - `test_level.gd`: PASS. Navmesh mit 625 Polygonen; der Weg in die Garage ist frei.
  - `test_playthrough.gd`: PASS (Seed 2 im Gate, Seeds 1/3/4/5 manuell).
  - `Tests/run_all.sh`: siehe PR.
- **Bilder:** `Docs/Reports/renders_m01_dressed/` (Forward Plus).

## 4. Offen
- Der Ostblock (Industrie, Lagerhalle) ist noch Graubox. Die Lagerhalle ist das Lieferziel; die Laderampe des Kits würde den Gehweg blockieren und braucht eine eigene Anpassung.
- **Tag/Nacht und Wetter** im Level (Regen-FX ist vorhanden) folgen mit P8.
