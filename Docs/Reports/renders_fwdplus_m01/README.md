# M01 – Forward Plus captures (T-BUILD-02)

| Datei | Inhalt |
|---|---|
| `M01_playthrough_fwdplus.mp4` | 3:45 min, 1280×720 (aufgenommen 1920×1080), 30 fps. Der Eingabe-Autopilot spielt M01 von Anfang bis Ende (Seed 2): Anruf → Fahrt → Garage → Hinterhalt aus der Deckung → Paket per `E` → Lieferung → „MISSION PASSED +$2500“. |
| `M01_playthrough_contact.jpg` | 8 Standbilder aus dem Video mit Zeitmarken. |

**Wie aufgenommen:** `Tools/godot_phase8_capture.sh --renderer fwdplus --script res://Tests/tools/record_m01_playthrough.gd --movie m01.avi --fps 30`. Das ist Godot Movie Maker mit festem Zeitschritt, Forward Plus über Vulkan auf **Mesa lavapipe (CPU)**. Die Aufnahme lief mit 16 % Echtzeit (22:53 min für 3:45 min). Die Zielzeiten im Video (195,5 / 198,7 / 216,9 s) sind identisch mit dem Headless-Test: Der Replay ist deterministisch.

**QA-Cheat:** Jason ist unverwundbar. Alle Gegner werden trotzdem über Zielen und Schießen getroffen (23 Treffer).

## Was man sieht (ehrlich)
- Code-Stand `2346bb8`.
- **Doppelte Munitionsanzeige** („122/60“ ab etwa 0:50): Dieser Fehler wurde *in diesem Video* gefunden (B-UI-03), im nächsten Commit behoben und ist durch `test_hud` abgesichert.
- **0:22 – die Limousine kippt** an der Nordwest-Ecke auf die Seite. Der Bot schneidet bei etwa 14 m/s die Kurve über Bordstein und Palme. Ein Auto, das an einem 16-cm-Bordstein umkippt, ist ein Fahrphysik-Befund (Schwerpunkt, Wankstabilität): **B-VEH-01 OFFEN (BLOCKERS B-009)**, zu prüfen beim GPU-Fahrtest.
- **Beim Zielen nah an der Wand** (3:10) clippt die Kamera in Jasons Schulter: **B-CAM-01 OFFEN (BLOCKERS B-010)**.
- Look: Das Level nutzt noch eine eigene, zu dichte Nebel/Himmel-Einstellung (beige, ausgewaschen). Das wird in T-LOOK-01 auf die kalibrierten Presets umgestellt.
- Alle Assets sind Blockout/WIP (REJECT laut Quality Gate). Das Video belegt **Spielfluss**, nicht Kunstqualität.

**Nicht belegt:** GPU-Bildrate, Echtzeit-Gefühl, Eingabeverzögerung.
