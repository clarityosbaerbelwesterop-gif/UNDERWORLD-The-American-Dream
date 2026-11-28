# Bericht T-AUD-01 – Audio-Bibliothek + AudioDirector

_Claude Code, 2026-11-26. Branch `arena/b376cee3-underworld-the-american-dream`. Status: **READY FOR REVIEW / WIP-Qualität**._

## Ausgangslage
Im Repo gab es **keine einzige Audiodatei** und kein Audiosystem. Der Sedan hatte nur einen leeren
`EngineAudio`-Knoten ohne Stream. PROJECT_STATUS und PRODUCTION_PLAN (P6) führten „Audio“ als offen.

## Was gebaut wurde

### 1. `Tools/uwp build-audio` – prozedurale Bibliothek (Python, numpy/scipy/soundfile)
Jeder Klang wird in Code synthetisiert. Es werden **keine Aufnahmen, Sample-Packs oder fremde
Klänge** gelesen. Deshalb fällt keine Fremdlizenz an (Eintrag in `Docs/ASSET_LICENSES.md`).
Die Ausgabe ist deterministisch: Seed pro Event und Variation.

| Ordner | Dateien | Inhalt |
|---|---|---|
| Weapons (+Handling, Throwables) | 72 | Schuss nah + separater Distanz-Tail für jede Waffe aus `combat.json`; Magazin raus/rein, Schlitten, Pump, Hülsen, Trockenschuss, Granate/Molotow |
| Melee | 17 | Faustschlag, Schwung leicht/schwer, Baseballschläger, Messer |
| Impacts | 35 | Einschläge je Oberfläche (Beton, Metall, Holz, Glas, Erde, Wasser, Fleisch), Querschläger, Flyby |
| Explosions / Destruction / FX | 15 | Explosionen (groß, Granate, Fahrzeug), Glasbruch, Loops für Feuer, Dampf und Funken |
| Foley (+Footsteps) | 104 | Schritte auf 7 Oberflächen × Gehen/Laufen mit Variationen; Sprung, Landung, Körperfall, Aufheben (Gegenstand, Geld), Kleidung |
| Vehicles (+Engines, Sirens) | 43 | 5 Motor-Sets (Sedan, Muscle, Truck, Moto, Prop) × 3 Drehzahl-Loops, Start/Stop, Reifenquietschen, Abrollen, Crash leicht/schwer, Türen, Hupe, 3 Sirenen, Hubschrauber |
| Ambience (+OneShots) | 18 | Straßen-Beds LA/NY Tag/Nacht, Regen, Wind, Innenraum + zufällige One-Shots |
| Music | 5 | M01 Tension (Explore), M01 Combat, Menü, Stinger Mission bestanden/gescheitert |
| UI | 14 | Klick, Hover, Zurück, Hitmarker, Killmarker, Ziel neu/erfüllt, Checkpoint, Geld, Telefon |

Insgesamt **135 Events / 323 Dateien**, Ogg Vorbis 48 kHz, ca. 11 MB. Ein Render dauert ca. 45 s auf 2 CPUs.

- **Pegel:** Spitze ≤ −0,8 dBFS, **nach** dem Dekodieren gemessen. Vorbis schoss beim Feuerknistern um +3,7 dB über; `write_ogg` prüft das jetzt und kodiert neu. Dazu kommen DC-Entfernung und nahtlose Loops.
- **Laufzeittabelle:** `GodotProject/Data/Content/audio.json` (committed). Sie wird nur aus der Registry abgeleitet und nicht aus Render-Ergebnissen. So ändert ein CI-Render keine getrackte Datei (Tree-Diff-Prüfung in `run_all.sh`).

### 2. `AudioDirector` (Autoload `Audio`, `Scripts/audio/audio_director.gd`)
Der Director ist datengetrieben über `audio.json` und hängt sich per `SceneTree.node_added` an
bestehende Signale. **Kein Gameplay-Skript wurde geändert.**

- **Waffen:** Schuss + Tail, Hülse, Pump nach dem Schuss, Nachladeschritte zeitlich passend (bei Abbruch gestoppt), Trockenschuss. Bei NPC-Schüssen nahe am Hörer ein Flyby.
- **FX:** Jede FX-Szene bekommt ihren Klang. Loops (Feuer, Dampf, Funken) hängen am Effekt; dazu Querschläger.
- **Figuren:** Schritte nach Schrittlänge und Oberflächengruppe (`surface_metal`, `surface_grass` …); Sprung und Landung (leicht/schwer). Körperfall nach dem Tod.
- **Fahrzeuge:** 3-Layer-Drehzahl-Crossfade aus `Vehicle.engine_pitch` + Gas, Reifenquietschen aus Querschlupf und Handbremse, Abrollen, Crash, Türen, Start/Stop. API `set_siren()`.
- **Mission:** UI-Sounds, Stinger, Musik Explore ↔ Combat (Combat bei Schüssen oder NPC-Kampfzustand, 9 s Haltezeit, Crossfade), Ambience-Bed mit One-Shots.
- **Mix:** Busse werden zur Laufzeit angelegt (Music, SFX, Weapons, Vehicles, Foley, Ambience, UI, VO). Kompressor auf Weapons, Musik per Sidechain von Weapons geduckt, Hard-Limiter auf Master. Voice-Pools 40 (3D) + 16 (2D) mit Stealing und Distanz-Culling.

### 3. Tests
- **`Tools/underworld_pipeline/tests/test_audio_pipeline.py`** (`run_tests.sh` Abschnitt [10]). Er prüft:
  - Registry, Benennung und Busse;
  - jede Binding-Auflösung und jede Waffe aus `combat.json`;
  - dass `audio.json` byteidentisch zu einem frischen Build ist;
  - 12 Probe-Renders auf Format, Pegel, DC, Loop-Naht, Determinismus und Variation;
  - eine Negativkontrolle mit kaputter Naht.

  **Hier gelaufen: PASS.**
- **Voll-Render** aller 323 Dateien hier: 0 fehlend, keine Datei mit Spitze > −0,3 dBFS, RMS < −50 dBFS, DC > 0,01 oder ≠ 48 kHz.
- **`GodotProject/Tests/test_audio.gd`** (CI: PASS) prüft Tabelle, Bindings, Dateien und Laufzeit: Pistole, Nachladen, FX, Schritte, Sedan-Motor-Mix, Crash/Tür/Sirene, Mission/Musik, Voice-Stealing. Negativkontrolle: `UW_AUDIO_SABOTAGE=1`.
- **Catalog:** `AUD_Library_Core` (WIP, 107 Einträge), `catalog.py check` PASS.

## Ehrlich: was NICHT erledigt bzw. nicht verifiziert ist
1. **Godot lief nur in der CI, nicht lokal.** Auf der Sandbox gibt es kein Godot-Binary, und GitHub-Release-Downloads sind blockiert. Die CI hat drei echte Fehler gefunden, die hier behoben sind:
   - `test_ai`: „50 resources still in use at exit“. Playbacks im AudioServer hielten Streams beim Beenden fest. **Fix:** unter `--headless` startet der Director keine Playbacks mehr; Voices werden über die Stream-Dauer belegt.
   - `test_audio`: Das Autoload kommt im `--script`-Modus erst nach `_initialize()` in den Baum. **Fix:** der Test wartet darauf.
   - `test_mission`: „Lambda capture was freed“. Verzögerte Callbacks hatten Nodes eingefangen. **Fix:** sie fangen jetzt nur noch Instanz-IDs ein.

   **Ergebnis:**
   - **CI-Gate PASS** (Run 45877227725): `RUN_ALL: PASS` plus Linux-Export und Boot-Check.
   - **Negativkontrolle** `UW_AUDIO_SABOTAGE=1` (Run 45878953010): `test_audio` FAIL mit 15 Fehlschlägen, wie verlangt.
   - Logs und Artefakte sind von der Sandbox aus nicht abrufbar. Neu ist deshalb der CI-Schritt „Failure digest“: Bei Fehlschlag schreibt er die relevanten Logzeilen als Check-Annotations, die über die API lesbar sind.
   - Weil headless nie wirklich abgespielt wird, prüfen die Tests Auflösung, Laden, Timing und Voice-Vergabe, **nicht aber das hörbare Ergebnis**.
2. **Die Ogg-Dateien sind nicht im Git.** `*.ogg` ist LFS-pflichtig, git-lfs ist hier nicht installierbar, und der S3-Upload ist blockiert. Deshalb gilt:
   - Die Dateien sind gitignored.
   - CI rendert sie vor dem Gate.
   - Lokal reicht `Tools/uwp build-audio`.

   Committen kann man sie später von einer LFS-fähigen Maschine (Anleitung in `.gitignore`, TD-034).
3. **Kein Mensch hat die Klänge gehört.** Es wurde nur messtechnisch geprüft (Pegel, Spektrum, Naht). Synthese klingt nicht wie Feldaufnahmen. **Das ist WIP-Qualität, nicht AAA**, und kein Asset wurde als PRODUCTION-READY markiert. Bekannte Schwächen:
   - Explosionen sind eher leise (RMS ca. −27 dBFS).
   - Kies-Schritte sind sehr leise (ca. −38 dBFS).
   - Die Hüllkurve beim Motorstart und der Musik-Loop sind ungeprüft.
4. **Bindings auf FX, die es noch nicht gibt** (`FX_Molotov`, `FX_Explosion_Grenade`, `FX_Impact_Dirt` …) sind Vorratseinträge und greifen erst, wenn diese Szenen existieren.
5. **Motorrad und Flugzeug** haben Motor-Sets (Moto, Prop). Die Fahrzeuge selbst kommen aus dem offenen PR #42 (T-VEH-03) und wurden hier nicht angefasst.
6. Für Hupe, Telefon, Stimmen (VO) und das Menü gibt es Klänge oder einen Bus, aber noch **keinen Gameplay-Auslöser**: Es gibt noch kein Hupen-Input und kein Menü.

## Reproduktion
```
python3 -m venv venv && venv/bin/pip install numpy scipy soundfile
UWP_PYTHON=venv/bin/python Tools/uwp build-audio          # rendert Assets/Audio/**
venv/bin/python Tools/underworld_pipeline/tests/test_audio_pipeline.py --scratch /tmp/aud
Tests/run_all.sh                                          # mit Godot 4.7.2 (CI)
```
