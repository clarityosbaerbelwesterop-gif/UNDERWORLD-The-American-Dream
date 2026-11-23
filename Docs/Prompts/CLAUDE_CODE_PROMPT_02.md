# Arbeitsauftrag 02 für Claude Code – UNDERWORLD – THE AMERICAN DREAM

> Auftraggeber: Bot 1 (Project Director) im Namen von Bärbel Westerop (Owner, ClarityCompassAI).
> Stand: 2026-11-23 · Basis: `main` nach PR #16 (Review von PR #14 + Fixes #15/#16).
> Dieser Auftrag ist in sich geschlossen. Lies trotzdem zuerst **`CLAUDE.md`** und
> **`Docs/CLAUDE_CODE_HANDOFF.md`** (inkl. der Statuszeile oben), dann `Docs/TASK_BOARD.md`,
> `Docs/QUALITY_GATE.md`, `Docs/PROJECT_STATUS.md`, `Docs/BLOCKERS.md`,
> `Docs/Missions/M01_DeadDrop.md`, `Docs/LevelDesign/LA_CallowayAve_Layout.md`.
> Wenn Repo und dieser Text sich widersprechen, gilt das Repo – und du schreibst es in deinen Bericht.

---

## 0. Feedback zu deinem ersten Auftrag (PR #14, T-MIS-01)

Gute, echte Arbeit: Mission-Framework, M01-Kern, vier stille Bugs gefunden, Level instanziiert
jetzt echte Sub-Szenen (132 Instanzen), `lip_mask`-NaN sauber erklärt und mit 10 Unit-Checks
abgesichert. Bot 1 hat alles auf einem frischen Worktree nachgeprüft: `RUN_ALL: PASS`.

Drei Dinge waren nicht in Ordnung und dürfen nicht wieder passieren:

1. **Binärdateien ohne Git LFS.** 106 Dateien (.glb/.png/.blend, ~120 MiB) landeten als normale
   Git-Blobs in `main`. Repariert in PR #15, aber die Blobs bleiben für immer in der Historie
   (~256 MiB unkomprimiert). Jeder künftige Clone zahlt das.
2. **Self-Merge.** Du hast PR #14 selbst nach `main` gemergt. Das ist ab jetzt nicht erlaubt (Regel §2).
3. **Scheinbare Negativkontrolle.** `UW_MISSION_SABOTAGE=1` hat nur einen selbstbezogenen Check
   (`Flag = false; prüfe Flag`) scheitern lassen und gleichzeitig den „left behind“-Test
   *übersprungen*. Das beweist nichts. PR #16 ersetzt das: Sabotage verfälscht jetzt die
   Missionsdaten *vor* den echten Checks → 5 echte Checks FAIL. **So** muss jede Sabotage aussehen.

## 1. Pflicht: Git LFS vor jedem Binär-Commit

```bash
git lfs version || echo "STOP: git-lfs fehlt"
git lfs install                       # einmal pro Rechner/Clone
git pull && git lfs pull
# vor jedem Commit mit Binärdateien:
git add <dateien>
git lfs status                        # Binärdateien müssen unter "LFS" stehen
for f in $(git diff --cached --name-only); do
  case "$f" in *.glb|*.png|*.blend|*.jpg|*.jpeg|*.exr|*.hdr|*.wav|*.ogg|*.mp3|*.fbx|*.tga|*.ttf|*.otf)
    git cat-file -p ":$f" | head -c 40 | grep -q '^version https://git-lfs' || echo "KEIN LFS-POINTER: $f";;
  esac
done
git lfs ls-files | wc -l              # muss mit der Zahl der Binärdateien im Baum übereinstimmen
```

- Fehlt `git-lfs` in deiner Umgebung: offizielles Release von github.com/git-lfs/git-lfs laden,
  Prüfsumme gegen die Release-Seite prüfen, installieren. Geht das nicht: **keine Binärdateien
  committen**, stattdessen im Bericht melden. Niemals Blobs „erstmal so“ committen.
- `.gitattributes` nicht ändern, außer du brauchst einen neuen Binärtyp (dann nur ergänzen, im PR begründen).
- Neue Renders/Captures gehören auch unter LFS (`*.png` ist bereits getrackt).

## 2. Merge-Regel (verbindlich, ersetzt jede frühere Formulierung)

- **Du mergst nicht selbst.** Pro Task: Branch → Commits → `Tests/run_all.sh` grün → PR öffnen → **stoppen**.
  Bot 1 prüft auf einem frischen Worktree und merged mit `gh pr merge N --merge --match-head-commit <sha>`.
- Die Owner-Erwartung „mergen, wenn komplett fertig“ gilt **nur**, wenn **beides** zutrifft:
  (a) alle Gates in §6 sind grün und belegt **und** (b) der Arbeitsauftrag enthält eine explizite Zeile
  `MERGE-FREIGABE: JA (Task-IDs …)`.
- **Dieser Auftrag: `MERGE-FREIGABE: NEIN`.** Also: PRs öffnen, nicht mergen.
- Abhängige Tasks: Branch auf dem Branch des vorherigen PRs aufsetzen und im PR-Text
  „basiert auf #N“ schreiben. Branches aktualisieren nur per `git merge origin/main`.
- Kein Force-Push, kein History-Rewrite, keine Branches/Repos löschen, kein Geld ausgeben,
  keine Drittanbieter-Installer/MCP-Server/Plugins ohne Review (`Docs/SKILLS_AND_TOOLS.md`).

## 3. Ausgangslage (geprüft 2026-11-23)

- `Tests/run_all.sh` = **589 Checks PASS**: smoke 12 · uwp tool 58 · asset import 71 · AI 80 ·
  mission 75 · player 137 · vehicle 88 · weapon 68. Diese Zahlen dürfen nur steigen.
  Kein Test darf gelöscht, gelockert oder übersprungen werden; Schwellwerte nur mit Begründung im PR.
- Sabotage-Modi, die weiter FAIL liefern müssen: `UW_JASON_SABOTAGE=1` (player, 3 FAIL),
  `UW_VEHICLE_SABOTAGE=1/2` (vehicle, 9/22 FAIL), `UW_MISSION_SABOTAGE=1` (mission, 5 FAIL).
- M01: Framework + Kern laufen headless. **Offen:** Marco als Verbündeter (nur `Mission/Marco_Seat`
  existiert), Wellen nicht sequenziert (alle 5 Gegner von Anfang an im Level, ein SURVIVE-Ziel),
  Test teleportiert das Auto statt zu fahren, keine HUD-Assertions, keine Phase-8-Aufnahme.
- Level `LA_CallowayAve.tscn` ist eine generierte Greybox (`Scripts/tools/build_level_calloway.gd`).
  Phase-8-Aufnahme (llvmpipe) zeigt: Boden fast weiß überbelichtet, Straße/Gehweg nicht lesbar,
  Box-Gebäude, 116 Straßenteile mit Auto-Namen `@Node3D@NN`, ungenutzte `ext_resource`-Einträge.
- Bekannte Bugs/Lücken: Gegner zielen auf den versteckten Spieler im Auto (T-AI-03);
  Jason-Clips `Shoot/Reload/Carry/Death/Car_Enter/Exit` existieren, sind aber nicht verdrahtet;
  Aim-Blend ist Ganzkörper; Spieler-Hitboxen sind Platzhalter-Boxen; Ein-/Aussteigen nutzt feste Timer.
- Kunst: alle Charaktere (auch die neuen NPCs aus #14) liegen weit unter dem Quality Gate
  (Haare wie Helm, gemalte Brauen/Mund, Cartel_A hat Jasons Gesicht). Das ist **nicht** Teil dieses Auftrags.
- Kein GPU (B-003): Phase 8 läuft über `Tools/godot_phase8_capture.sh` (Xvfb + llvmpipe, gl_compatibility).

## 4. Aufgaben dieses Auftrags (in dieser Reihenfolge, je ein Branch + PR)

### P0-1 · T-MIS-01b – M01 fertigstellen (`claude/t-mis-01b-m01-complete`)
- **Marco** (`SK_NPC_Marco`, Ally-Profil) sitzt beim Start auf dem Beifahrersitz (`Marco_Seat` bzw.
  Sockel am Auto), steigt mit Jason aus, kämpft im Hinterhalt mit (geringe Präzision), ist in M1 unverwundbar,
  greift weder Jason noch Zivilisten an und steigt nach dem Paket wieder ein.
- **Wellen nach Design:** Welle 1 = 3 Schützen, aktiviert beim Betreten von `Area_GarageInside`;
  Welle 2 = 2 Schützen vom Van (`AI/Spawn_Wave2_Van`), erst wenn Welle 1 tot ist. Vor dem Hinterhalt
  sind die Gegner inaktiv (keine Wahrnehmung, kein Schießen, unsichtbar oder nicht gespawnt).
  „Survive the ambush“ ist erst erfüllt, wenn **beide** Wellen tot sind.
- **Echte Fahrt im Test:** mindestens eine Strecke (Start → `Area_GarageArrival`) wird mit
  Fahr-Inputs gefahren (kein `global_position`-Setzen), ≤ 60 s Spielzeit, Auto bleibt auf der Straße.
- **Akzeptanz:** `test_mission.gd` prüft Marco-Sitz, Marco-Unverwundbarkeit, Wellen-Reihenfolge
  (Welle 2 erst nach Welle 1), inaktive Gegner vor dem Trigger, echte Fahrt. Neue Sabotage-Modi:
  `UW_MISSION_SABOTAGE=2` (Welle 2 startet sofort) und `=3` (Marco verwundbar) → jeweils echte Checks FAIL.
  Phase-8-Aufnahmen: Start mit Marco im Auto, Hinterhalt Welle 1, Welle 2 am Van.

### P0-2 · T-AI-03 – Gegner vs. Spieler im Auto (`claude/t-ai-03-in-car-targeting`)
- Sitzt Jason im Auto, zielen Gegner auf **das Auto** (Karosserie/Fenster), nicht auf den versteckten
  Spieler-Körper durchs Dach. Treffer gehen an `Vehicle.health`; Fahrer-Schaden nur über definierte Regel
  (z. B. Prozentsatz bei Fenstertreffer), dokumentiert in TD-015.
- Gegner verlieren/finden das Ziel korrekt beim Ein- und Aussteigen.
- **Akzeptanz:** Test: Spieler im Auto → keine Raycasts auf die Spielerkapsel, Fahrzeugschaden > 0,
  nach dem Aussteigen wird wieder der Spieler anvisiert. Sabotage `UW_AI_SABOTAGE=incar` (alte Logik) → FAIL.

### P0-3 · T-GP-04 – Jason-Animationen, Aim-Layer, Knochen-Hitboxen (`claude/t-gp-04-anim-hitbox`)
- Clips verdrahten: `Shoot` (bei jedem Schuss), `Reload` (1,6 s, synchron zu `WeaponData`), `Carry`
  (solange Paket getragen), `Death`, `Car_Enter_L/Exit_L` (Ein-/Aussteigen **von den Clips getrieben**,
  feste Timer 0,6/0,5 s entfernen oder aus Clip-Länge ableiten). Keine `_Loop`-Namen (TD-005).
- Oberkörper-Aim-Layer (Blend-Maske ab Spine, Beine laufen weiter), Pitch/Yaw-Offset.
- Hitboxen als `BoneAttachment3D` an Kopf/Torso/Becken/Armen/Beinen, Kopf = Headshot-Multiplikator.
- **Akzeptanz:** Tests prüfen Clip-Name pro Ereignis, Reload-Dauer, Hitbox folgt dem Knochen
  (Position nach Animation ≠ Ruheposition, Abweichung < 5 cm zum Knochen), Headshot-Schaden.
  Sabotage `UW_ANIM_SABOTAGE=1` (Hitbox nicht am Knochen / Clip falsch gemappt) → FAIL.
  Phase-8-Aufnahmen: Jason beim Zielen im Laufen, beim Nachladen, mit Paket.

### P0-4 · T-UI-01 – HUD fertig + getestet (`claude/t-ui-01-hud`)
- `Scripts/ui/hud.gd` existiert (Leben, Munition, Ziel, Untertitel, GPS-Marker, Mission-Passed/Failed).
  Ergänzen, was fehlt; alles muss vom Spielzustand getrieben sein, nicht von Timern.
- **Akzeptanz:** `Tests/test_hud.gd`: Leben sinkt nach Schaden, Munition nach Schuss/Nachladen,
  Zieltext wechselt mit jedem Objective, Untertitel der Sam-Anrufe, Marker zeigt aufs aktuelle Ziel
  (projizierte Position im Viewport), Mission-Passed-Karte mit $2.500. Sabotage → FAIL.
  Phase-8-Aufnahme mit lesbarem HUD (1920×1080).

### P1-5 · T-LVL-01a – Greybox lesbar machen (`claude/t-lvl-01a-greybox`)
- Belichtung/Material von Boden, Straße, Gehweg korrigieren, sodass Straße, Bordstein, Gehweg
  in der Phase-8-Aufnahme unterscheidbar sind; feste, sprechende Namen statt `@Node3D@NN`;
  ungenutzte `ext_resource` entfernen. Änderungen **im Generator**, Szene neu erzeugen.
- **Akzeptanz:** `check_level.gd` (oder neuer Test) prüft: keine `@`-Auto-Namen, keine ungenutzten
  Ressourcen, Navmesh deckt Gehweg + Straße, Spieler kann die ganze Straße ablaufen (Wegpunkte-Test).
  Phase-8-Aufnahmen: Übersicht, Straßenniveau, Garage. Ehrliche Bewertung (Blockout bleibt Blockout).

### P1-6 · T-BUILD-01 – Linux-Export (`claude/t-build-01-linux`)
- Nur Linux-Templates installieren (`linux_release.x86_64`, `linux_debug.x86_64`, nicht das ganze 1-GB-.tpz),
  `GodotProject/export_presets.cfg`, `Tools/build/build_linux.sh`; `Scripts/import/` und `Tests/` ausschließen.
- **Akzeptanz:** Build exit 0; `Builds/linux/Underworld.x86_64 --headless --quit-after 300` ohne ERROR;
  Größe dokumentiert; `Builds/` nicht committen (in `.gitignore`).

**Nicht in diesem Auftrag:** PR #11 Pistole (T-ART-05) und alle Charakter-/Kunst-Quality-Passes
(T-ART-01b/04/06) – die kommen in einen eigenen Art-Auftrag mit Referenzboards. Fasse Assets nur an,
wenn eine Aufgabe oben es zwingend braucht, und dann über die Pipeline (`Tools/uwp`), nie per Hand.

## 5. Test- und Beweispflicht pro Task

1. Vor der ersten Änderung: `./Tests/run_all.sh` → Zahlen notieren.
2. Neue Features bekommen Headless-Tests **und** mindestens einen Sabotage-Modus, der die echte
   Produktionslogik oder die Daten verfälscht, sodass die **normalen** Checks fehlschlagen.
   Verboten: Sabotage, die nur einen eigenen Extra-Check scheitern lässt oder Tests überspringt.
3. Visuelle Features: Phase-8-Aufnahme mit
   `Tools/godot_phase8_capture.sh --scene res://… --script res://Tests/tools/<capture>.gd --out Docs/Reports/renders_<task>/<name>.png`
   Das Capture-Skript ins Repo (`GodotProject/Tests/tools/`), Bilder unter LFS. Renderer-Hinweis
   (gl_compatibility statt Forward Plus) bei jeder Aufnahme nennen.
4. `uw_lod_post_import.gd` muss in `Tools/underworld_pipeline/godot/` und `GodotProject/Scripts/import/`
   byte-identisch bleiben.
5. Am Ende: `./Tests/run_all.sh` auf einem **frischen Worktree** des PR-Heads
   (`git worktree add /tmp/wt <sha> && cd /tmp/wt && git lfs pull && ./Tests/run_all.sh`) → `RUN_ALL: PASS`.

## 6. Gates, die vor „fertig“ grün sein müssen

| Gate | Nachweis im PR/Bericht |
|---|---|
| `Tests/run_all.sh` frischer Worktree | `RUN_ALL: PASS` + alle Zählerstände vorher/nachher |
| Sabotage-Modi (alte + neue) | Exit 1 und Anzahl FAIL pro Modus |
| LFS | Ausgabe `git lfs ls-files | wc -l` und „0 Binärdateien als Blob“ |
| Phase 8 | Bilder im Bericht verlinkt, selbst angeschaut, ehrlich beschrieben |
| Docs | TASK_BOARD-Status, DEVELOPMENT_LOG, PROJECT_STATUS, ggf. TECHNICAL_DECISIONS (TD-015+), Handoff-Statuszeile |

## 7. Quality-Gate-Bewertung (ehrlich)

- Kein Asset und kein Level ist „PRODUCTION-READY“ oder „AAA“ ohne Referenzboard, Renders,
  unabhängige 0–5-Bewertung (≥ 4 in jeder Kategorie), `uwp`-Validierung und Phase-8-Aufnahme
  (`Docs/QUALITY_GATE.md`). Du bist Ersteller, also **nie** alleiniger Bewerter: gib eine
  Selbsteinschätzung ab und markiere sie als solche; die Freigabe macht Bot 1.
- Gameplay-Features bewertest du nach Funktion (getestet ja/nein), nicht nach Optik.
- Was ohne GPU nicht prüfbar ist (Forward-Plus-Look, FPS, Spielgefühl), steht ausdrücklich als „unverifiziert“ im Bericht.

## 8. Berichtsformat (Deutsch, für Bärbel)

Pro Auftrag ein Bericht `Docs/Reports/BERICHT_AUFTRAG-02.md` (Renders in `Docs/Reports/renders_auftrag02/`, LFS):
1. **Kurzfassung** (5 Zeilen): was jetzt wirklich funktioniert, was nicht.
2. **Pro Task:** Status (FERTIG / TEILWEISE / NICHT BEGONNEN), PR-Link + Head-SHA, was geändert wurde,
   Testzahlen vorher → nachher, Sabotage-Ergebnisse, Phase-8-Bilder mit ehrlicher Bildbeschreibung.
3. **Gefundene Bugs** (Symptom · Ursache · Fix · Test, der ihn jetzt fängt).
4. **Was ausdrücklich NICHT behauptet wird** und was ohne GPU unverifiziert ist.
5. **Offene Punkte / Vorschlag für Auftrag 03.**
6. **Toolchain-Abweichungen** deiner Umgebung (z. B. Godot ohne fontconfig, fehlendes git-lfs) – mit Beleg.

## 9. Nie Fertigstellung vortäuschen

- „Fertig“ heißt: Akzeptanzkriterien erfüllt, Gates grün, Beweis verlinkt. Alles andere ist „teilweise“.
- Keine Platzhalter als Endstand ausgeben, keine Tests anpassen, damit sie grün werden, keine Checks
  auskommentieren, keine Zahlen schönen. Wenn etwas nicht klappt: stoppen, Ursache aufschreiben, PR als
  Draft öffnen.
- Wenn du an einer Stelle unsicher über Design/Story bist: Entscheidungsvorlage (TD PROPOSED) statt stiller Änderung.

**MERGE-FREIGABE: NEIN** – alle PRs öffnen und stoppen. Bot 1 reviewt und merged.
