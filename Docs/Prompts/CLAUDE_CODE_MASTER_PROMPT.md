# UNDERWORLD – THE AMERICAN DREAM · Master-Prompt für Claude Code

> **Du bist Claude Code** und übernimmst das Spiel **UNDERWORLD – THE AMERICAN DREAM** bis zum Release.
> Dieser Prompt ist in sich vollständig. Lies ihn ganz, bevor du etwas änderst. Danach liest du
> `CLAUDE.md`, `Docs/CLAUDE_CODE_HANDOFF.md`, `Docs/QUALITY_GATE.md`, `Docs/TASK_BOARD.md`,
> `Docs/PROJECT_STATUS.md`, `Docs/BLOCKERS.md`, `Docs/TECHNICAL_DECISIONS.md` und `Docs/SKILLS_AND_TOOLS.md`.
> Wenn das Repo diesem Prompt widerspricht, gilt das Repo. Korrigiere dann diesen Prompt im selben PR.

| | |
|---|---|
| Repo | https://github.com/clarityosbaerbelwesterop-gif/UNDERWORLD-The-American-Dream (privat) |
| Geschrieben von | Bot 1 (Project Director), 2026-11-23 (Europe/Berlin) |
| Stand von `main` | `29ce6e7` = PR #17 (Auftrag 02) + Review-Fix-PR #18 von Bot 1 – siehe §3 |
| Eigentümerin | **Bärbel Westerop**, CEO ClarityCompassAI, Moers. Berichte **auf Deutsch**, ehrlich. |
| Merge-Regel | **MERGE-FREIGABE: NEIN** – du öffnest PRs, Bot 1 reviewt und merged (§9.6). |

---

## Inhaltsverzeichnis

1. [Auftrag in einem Satz und deine fünf Ziele](#1-auftrag-in-einem-satz-und-deine-fünf-ziele)
2. [Das Spiel: Vision, Säulen, Look](#2-das-spiel-vision-säulen-look)
3. [Ist-Stand nach PR #17 (geprüft)](#3-ist-stand-nach-pr-17-geprüft)
4. [Story und Missionsreihenfolge (Kanon aus dem Repo)](#4-story-und-missionsreihenfolge-kanon-aus-dem-repo)
5. [Asset-Pipeline: ehrliche Bewertung und Neuaufbau auf AAA-Niveau](#5-asset-pipeline-ehrliche-bewertung-und-neuaufbau-auf-aaa-niveau)
6. [Animationen Ende-zu-Ende: Blender → Godot](#6-animationen-ende-zu-ende-blender--godot)
7. [Roadmap M1–M10 bis zum Release](#7-roadmap-m1m10-bis-zum-release)
8. [Wo du weitermachst: die nächsten Tasks in Reihenfolge](#8-wo-du-weitermachst-die-nächsten-tasks-in-reihenfolge)
9. [Standards (verbindlich)](#9-standards-verbindlich)
10. [Skills, Tools und der Game-Studio-Skill](#10-skills-tools-und-der-game-studio-skill)
11. [Sicherheitsregeln](#11-sicherheitsregeln)
12. [Berichte an die Eigentümerin](#12-berichte-an-die-eigentümerin)
13. [Offene Entscheidungen der Eigentümerin (OFFEN)](#13-offene-entscheidungen-der-eigentümerin-offen)
14. [Start-Checkliste für deine erste Sitzung](#14-start-checkliste-für-deine-erste-sitzung)

---

## 1. Auftrag in einem Satz und deine fünf Ziele

**Bringe UNDERWORLD von einem headless getesteten Blockout-Vertical-Slice zu einem veröffentlichten,
vollständigen Spiel (Kapitel 1 Los Angeles + Kapitel 2 New York) in Rockstar-Games-Qualität –
ohne jemals Fertigstellung vorzutäuschen.**

1. **Pipeline prüfen, reparieren, auf AAA-Niveau heben.** Die heutige prozedurale Pipeline
   (`Tools/uwp`, MakeHuman-hm08-Basis) erreicht das Ziel nicht (§5). Baue die Toolchain neu auf,
   wo nötig, und behalte, was trägt (Validierung, Export, Tests).
2. **Animationen Ende-zu-Ende** über Blender und Godot: Quelle, Retargeting, Clips, AnimationTree,
   Blend-Spaces, Oberkörper-Layer, IK, Root Motion (§6).
3. **Das ganze Spiel bauen**, von der ersten bis zur letzten Mission, in der Reihenfolge aus §4
   und nach der Roadmap in §7.
4. **Qualität beweisen**: jedes Asset durch das Quality Gate (§9.1), jeder Code durch `Tests/run_all.sh`
   mit echten Sabotage-Modi (§9.2), jede visuelle Aussage mit GPU-Aufnahmen (§9.3).
5. **Ehrlich berichten**, auf Deutsch, mit Renders in `Docs/Reports/` (§12).

Du arbeitest vermutlich lokal **mit GPU**. Das ist der größte Unterschied zu allen bisherigen Agenten:
Alles, was bisher „ohne GPU unverifiziert“ war (Forward-Plus-Look, FPS, Fahrgefühl, Animations-Blending),
kannst und sollst du jetzt prüfen.

---

## 2. Das Spiel: Vision, Säulen, Look

**Genre:** originaler Open-World-Third-Person-Crime-Shooter. Qualitätsmaßstab: GTA IV/V/VI.
**100 % eigene IP:** keine echten Marken, Logos, Karten oder Assets aus anderen Spielen. Echte Städte
erscheinen nur als **fiktionalisierte Bezirke**.

**Säulen** (`Docs/GAME_DESIGN.md` §1):
1. **Gewicht:** Bewegung und Gunplay fühlen sich physisch an, mit Schwung, Rückstoß, Deckung und Konsequenzen.
2. **Kino:** Kapitel 1 ist ein straff erzählter Crime-Film, getragen von Kamera, Licht und Dialog.
3. **Der amerikanische Traum, umgedreht:** Jason baut aus 5.000 € ein Imperium auf und lernt, was es kostet.
4. **Lebendige Straßen:** NPCs, Verkehr und Polizei reagieren glaubwürdig.

**Look** (`Docs/GAME_DESIGN.md` §6, `Docs/ArtDirection/README.md`):
- Fotografischer Realismus, leicht entsättigter Film-Look.
  - LA: warme Natriumdampf- und Golden-Hour-Palette, Dunst, lange Schatten.
  - NY: kalte Blautöne, nasser Asphalt, Dampf.
- PBR-Materialien, abgenutzt und bewohnt (Schmutz, Decals, Risse), keine sterilen Flächen.
- Amerikanische Architektur 1960–2000: Stuck, Backstein, Neon mit **erfundenen** Namen
  (z. B. „Vega Liquor“, „Sunny Days Motel“).
- Fahrzeuge: eigene Designs im Stil später 90er-US-Limousinen und Pickups, keine echten Embleme.
- Charaktere: realistische Proportionen, keine Stilisierung.

**Jason, verbindliches Konzept v01** (`Docs/ArtDirection/Concepts/`):
- Latino-Amerikaner, **Anfang 30**, 1,82 m, athletisch-schlank.
- Skin-Fade-Haarschnitt, kurzer gepflegter Bart, Narbe über der **linken** Augenbraue.
- Kleidung: abgetragene dunkelbraune Leder-Bomberjacke mit Rippbündchen, graues Rundhals-T-Shirt,
  dunkle Indigo-Jeans, braune geschnürte Lederarbeitsstiefel, Armbanduhr links.
- Er führt eine Pistole mit sauberem Griff. Die zwei Pistolen auf dem Key-Art sind **nicht** Kanon.
- ⚠ **T-DOC-01:** `GAME_DESIGN.md` §2 sagt noch „late 30s“ und „grey henley“. Die Art Direction
  (Anfang 30, Rundhals-T-Shirt) gilt. Korrigiere die GDD-Zeile, sobald du sie anfasst.

**Steuerung (KB/M · Gamepad):**
- Bewegen: WASD / linker Stick. Sprinten: Shift / L3. Ducken: C / B.
- Zielen: rechte Maustaste / LT. Schießen: linke Maustaste / RT. Nachladen: R / X.
- Fahrzeug ein/aus: F / Y. Interagieren: E / A. Springen: Leertaste / A.

---

## 3. Ist-Stand nach PR #17 (geprüft)

### 3.1 Was PR #17 (Auftrag 02) geliefert hat
Bot 1 hat PR #17 auf einem frischen Worktree mit `git lfs pull` nachgeprüft. Alle Zahlen sind selbst gemessen.

| Task | Ergebnis der Prüfung |
|---|---|
| T-MIS-01b M01 fertig | ✅ Marco sitzt beim Start auf dem Beifahrersitz und ist in M1 unverwundbar. Die Wellen laufen in der richtigen Reihenfolge (erst 3, dann 2 Gegner). Der Test fährt eine echte Strecke mit Eingaben (26,2 s, 97,2 m, 0,00 m neben der Straße). Defekt: Marco wurde stehend durchs Autodach gezeichnet, behoben in PR #18. |
| T-AI-03 Gegner vs. Auto | ✅ Gegner zielen aufs Fahrzeug. Der Fahrer bekommt nur bei Treffern durchs Fahrerfenster Schaden (25 %). Nach dem Aussteigen wird wieder der Spieler anvisiert. TD-015 ist jetzt ACCEPTED. |
| T-GP-04 Clips/Aim/Hitboxen | ✅ Shoot, Reload, Carry, Death und Car_Enter/Exit hängen an echten Ereignissen. Ein- und Aussteigen richtet sich nach der Clip-Länge. Es gibt einen Oberkörper-Aim-Layer und 7 Knochen-Hitboxen. |
| T-UI-01 HUD | ✅ Das HUD reagiert auf Signale und hat 40 Checks. Die Phase-8-Aufnahme zeigt Leben, Munition, Ziel und Untertitel. |
| T-LVL-01a Greybox lesbar | ✅ Straße, Bordstein und Gehweg sind unterscheidbar, das Navmesh ist gebacken. **Blockout**: Box-Gebäude, überbelichtete Gehwege in gl_compatibility. Defekt: der Navmesh-Test war flaky (1 von 3 Läufen rot), behoben. |
| T-BUILD-01 Linux-Export | ⚠ Der Export lief. **Aber** die Main-Scene war die Pipeline-Testszene mit Kiste, und außerhalb der Tests hat niemand die Mission gestartet. Das Binary bootete also nicht ins Spiel. Behoben im Review-PR: neue Einstiegsszene `Scenes/Game_M01.tscn` plus `Tests/test_boot.gd`. |

**Merge-Hinweis, neutral:** PR #17 hatte `MERGE-FREIGABE: NEIN`. Claude Code hat nicht selbst gemergt
(der PR-Text sagt das ausdrücklich). Der Merge kam am 2026-11-23 um 14:07 Uhr (Berlin) über das
Eigentümer-Konto, nach Aussage der Eigentümerin von ihr selbst.

### 3.2 Testzahlen (`Tests/run_all.sh`, frischer Worktree)
| Suite | vor #17 | nach #17 | nach Review-Fix |
|---|---:|---:|---:|
| Smoke | 12 | 12 | 12 |
| uwp-Tool-Tests | 58 | 58 | 58 |
| Asset-Import | 71 | 71 | 71 |
| AI | 80 | 102 | 102 |
| Boot (neu) | – | – | 7 |
| HUD (neu) | – | 40 | 40 |
| Level (neu) | – | 23 | 23 |
| Mission | 75 | 105 | 109 |
| Player | 137 | 171 | 171 |
| Vehicle | 88 | 88 | 88 |
| Weapon | 68 | 68 | 68 |
| **Summe** | **589** | **738** | **749** |

**Sabotage-Modi:** Alle müssen FAIL liefern, und alle tun es (§9.2). Es sind `UW_JASON_SABOTAGE=1`,
`UW_ANIM_SABOTAGE=1`, `UW_VEHICLE_SABOTAGE=1/2`, `UW_MISSION_SABOTAGE=1/2/3`, `UW_AI_SABOTAGE=incar`,
`UW_HUD_SABOTAGE=1`, `UW_LEVEL_SABOTAGE=1`, `UW_BOOT_SABOTAGE=1` und `UW_BUILD_SABOTAGE=1` (Build-Skript, Exit 6).
Seit dem Review-Fix wirken die Schalter nur in Debug-Builds (`OS.is_debug_build()`), nie im Release-Export.

**LFS:** 114 → 122 Dateien unter LFS (8 neue Review-PNGs), 0 Binärdateien als normaler Blob, `git lfs fsck --pointers` OK.

### 3.3 Was es gibt
- **Godot-Projekt** (`GodotProject/`, Godot 4.7.2, GDScript, Forward Plus):
  - Third-Person-Controller mit Jason v2 als Spielfigur und SpringArm-Kamera.
  - Pistolen-Gunplay mit Bloom, Rückstoß und Hitscan.
  - Gegner- und Zivilisten-KI (TD-013), Fahrzeugphysik (TD-014, VehicleBody3D, Laufzeit-Montage aus `VH_*.glb`).
  - Mission-Framework mit M01 „Dead Drop“, HUD, generiertes Greybox-Level `LA_CallowayAve.tscn`,
    Einstiegsszene `Game_M01.tscn`.
- **Pipeline** `Tools/uwp` (Blender 5.2.4 LTS headless, `bpy`): build-character, build-shared-anims,
  retarget, build-weapon, build-vehicle, build-kit/build-env, validate, export, review-sheet.
- **Assets, alle Status WIP**:
  - Charaktere: SK_Jason v2, SK_NPC_Sam, SK_NPC_Marco, SK_NPC_Cartel_A/B, SK_NPC_Civilian_Female, SK_NPC_Cop_LA.
  - Gemeinsame Animationsbibliothek A_Humanoid_* (53-Bone-Skelett).
  - WPN_Pistol_01, VH_Sedan_01, LA-Kit (Straße, Gehweg, Shop, Garage, Laterne, Palme), SM_Prop_PackageCrate.
- **Linux-Export** `Tools/build/build_linux.sh` (TD-019). Offizielle Templates 4.7.2 gehören nach
  `~/.local/share/godot/export_templates/4.7.2.stable/`.

### 3.4 Was es NICHT gibt (ehrlich)
- **Kein einziges Asset ist PRODUCTION-READY.** Alle 5 geprüften Hero-Assets (Jason, Sam, Pistole,
  Limousine, LA-Kit) sind beim Quality Gate durchgefallen, und die neuen NPCs sind nicht reviewt (§5.1).
- Kein Audio, kein Speichern/Laden, keine Menüs, keine Polizei, kein Verkehr, keine offene Welt.
- **Niemand hat das Spiel je auf einer GPU gesehen oder gespielt.** Alle Bilder bisher kommen aus
  Software-OpenGL (llvmpipe, gl_compatibility) und nicht aus dem Shipping-Renderer Forward Plus.
- Nur eine der 16 Story-Stationen ist gebaut (M01, als Blockout).
- Offene Draft-PR **#11** (Pistolen-Qualitätspass, T-ART-05, ungetestet, „T-ART-03“ fälschlich im Titel).

### 3.5 Phase-8-Befund von Bot 1 (llvmpipe, nicht Forward Plus)
Bilder: `Docs/Reports/renders_review_pr17/` (Capture-Skript `GodotProject/Tests/tools/capture_m01_review.gd`).
- Jason: Die Proportionen stimmen. Die Haare sehen aus wie eine Mütze oder ein Helm, die Haut wirkt wachsig,
  die Jacke ist eine verrauschte Textur ohne Rippbündchen, die Stiefel sind Klumpen. Weit unter dem Gate.
- Limousine: Blockout-Karosserie, Fenster nicht als Glas lesbar, kein Innenraum.
- Level: Die Straße ist lesbar, die Gehwege sind fast weiß überbelichtet. Die Gebäude sind leere Boxen,
  die Garage ein brauner Quader. Keine Straßenmöbel, Schilder, Decals oder Abnutzung.
- HUD: lesbar (Leben, Munition, Zieltext, Untertitel).
- **Bewertung: funktionaler Blockout, kein AAA, nicht vorzeigbar.**

---

## 4. Story und Missionsreihenfolge (Kanon aus dem Repo)

Quellen: `Docs/GAME_DESIGN.md` §2–§4 (v0.1), `Docs/Missions/M01_DeadDrop.md`,
`Docs/LevelDesign/LA_CallowayAve_Layout.md`.
**Regel:** Erfinde keinen Kanon. Was hier als **OFFEN** markiert ist, entscheidet die Eigentümerin.
Du darfst Vorschläge machen, als Entscheidungsvorlage (TD PROPOSED oder ein Eintrag in `Docs/BLOCKERS.md`),
aber nie still einbauen. Alle Namen sind **Arbeitsnamen** (B-004).

### 4.1 Figuren
| Figur | Rolle | Kanon-Details |
|---|---|---|
| **Jason** (Nachname OFFEN, B-004) | Protagonist, Schmuggler/Exporteur | ruhig, beobachtend, trockener Humor; Aussehen §2 |
| **Sam** | Jasons Auftraggeber, Kopf einer kleinen LA-Crime-Familie | 60er, schwer gebaut, teure Anzüge, an der Oberfläche warm. Verrät Jason heimlich an das FBI (Enthüllung spät in Kap. 2). |
| **Marco Ruiz** | Jasons Kollege in Kap. 1 | 30er, gesprächiger Fahrer, loyal, Partner in M01 |
| **Los Cuervos** | Kartell #1, Antagonisten Kap. 1/2 | schwarze Krähen-Ikonografie (eigen); ermorden in M01 die Lieferanten-Crew |
| **La Hermandad del Sur** | Kartell #2, arbeitet in Kap. 2 mit Sam | entführt Jason und versucht ihn anzuwerben |
| **Kings of Flatbush** (Arbeitstitel) | Brooklyn-Straßengang | produziert für Jason, Aufteilung 80/20 |
| FBI Special Agent **Dana Whitlock** | Verfolgerin | leitet die Lagerhaus-Razzia |

### 4.2 Kapitel 1 – Los Angeles (linear, filmisch)
| # | Station | Inhalt (Kanon) | Status |
|---|---|---|---|
| 1 | **Arrival** | Jason fliegt aus Kolumbien ein; Sam empfängt ihn in einem privaten Hangar. | nicht begonnen |
| 2 | **The Route** | Lieferungen quer durch LA und hinauf ins Emerald Triangle; Kontakte treffen; Heimkehr. | nicht begonnen |
| 3 | **Dead Drop (M01, Vertical Slice)** | Sam ruft an: eine Lieferung ist schiefgegangen. Jason und Marco finden die Crew in einer Garage an der Calloway Avenue, ermordet von Los Cuervos. Schießerei; Jason sichert das Paket und fährt es zum Lagerhaus. | Gameplay headless fertig, Kunst Blockout |
| 4 | **The Raid** | Das FBI stürmt das Lagerhaus. Jason entkommt schwer verletzt. | nicht begonnen |
| 5 | **Wings** | Jason stiehlt ein Kleinflugzeug und flieht nach New York. | nicht begonnen |

**M01 „Dead Drop“ im Detail** (Calloway Avenue, East Hollow, Golden Hour, 10–15 min):
| # | HUD-Ziel | Abschluss |
|---|---|---|
| 0 | (Intro) Anruf von Sam | 20 s Dialog mit Untertiteln, Spieler steuerbar |
| 1 | „Get in the car.“ | in `VH_Sedan_01` einsteigen, Marco sitzt schon auf dem Beifahrersitz |
| 2 | „Drive to the garage on Calloway Ave.“ | Auto hält in `Area_GarageArrival` (r 8 m), Runde von ca. 300 m, Zivilisten |
| 3 | „Check the garage.“ | `Area_GarageInside` betreten; 3 tote Crew-Mitglieder, Kiste auf der Werkbank |
| 4 | „Survive the ambush.“ | Welle 1: 3 Schützen von der Straße; Welle 2: 2 vom Van/Dach; Marco kämpft mit (unverwundbar, geringe Präzision) |
| 5 | „Grab the package.“ | `Pickup_Package` aufnehmen; kein Sprint beim Tragen; Checkpoint |
| 6 | „Deliver the package to the warehouse.“ | Auto mit Paket in `Area_Warehouse`; optional ein Verfolgerauto mit 2 Schützen (Stretch, **noch nicht gebaut**) |
| 7 | (Outro) „MISSION PASSED“ + 2.500 $ | Endkarte |

Fail-States: Jason stirbt, Paket zerstört (200 HP) oder mehr als 60 m zurückgelassen, Limousine vor
Schritt 6 zerstört. Neustart am letzten Checkpoint. Marco ist in M1 nicht tötbar.

### 4.3 Kapitel 2 – New York (offene Welt)
| # | Station | Inhalt (Kanon) |
|---|---|---|
| 6 | Ankunft | ca. 5.000 €, billiges Zimmer, Job als Taxifahrer (Taxi-Nebenaktivität) |
| 7 | Brooklyn | Netzwerke entdecken, Kokain stehlen und verkaufen, Kontakte aufbauen |
| 8 | Produktion | eine lokale Gang (Kings of Flatbush) produziert für Jason (80/20) |
| 9 | Bankraub | Crew zusammenstellen → Bankraub; zwei Crew-Mitglieder sterben; Jason entkommt, wird gesucht |
| 10 | Die Farm | Versteck auf einer kleinen Farm auf dem Land; Los Cuervos finden ihn und brennen sie nieder |
| 11 | Rache | Vorräte einer rivalisierenden Gang überfallen, Kartell-Operation angreifen, riesige Kokain-Lieferung stehlen |
| 12 | Entführung | von La Hermandad entführt (die mit Sam arbeitet); Jason lehnt die Anwerbung ab |
| 13 | Gold-Depot | Überfall auf ein Golddepot, beide Kartelle gegeneinander ausgespielt; Flucht mit dem Gold |
| 14 | Enthüllung | Sam hat Jason an das FBI verkauft, um seine Position zu schützen |
| 15 | Finale | Jason zerstört beide Kartelle und stellt Sam |
| 16 | Epilog | Jason gründet eine Familie. **VIER JAHRE SPÄTER.** |

### 4.4 Welt (langfristig)
- **LA (fiktionalisiert):**
  - East Hollow (Hollywood-inspiriert), Crestmont Hills (Beverly-Hills-inspiriert), Downtown.
  - Seaview-Strände, Flughafen, San-Ardo-Berge, Freeways, Harbor-Industriegebiet.
  - Ländlicher Norden mit einer Emerald-Triangle-inspirierten Region.
- **NY (fiktionalisiert):** Manhattan, Brooklyn, Queens, Bronx, Staten Island, ein Central-Park-inspirierter
  Park, U-Bahn, Brücken, Lagerhäuser.

### 4.5 Lücken im Kanon – OFFEN (Eigentümerin entscheidet)
- **Missions-IDs und Reihenfolge der Missionsnummern:** Nur „M01 = Dead Drop“ existiert, obwohl Dead Drop
  Station 3 ist. Ob Arrival/The Route eigene Missionen bekommen (z. B. M00/Prolog) oder umnummeriert wird, ist OFFEN.
- **Missionsdesigns für Stationen 1, 2, 4–16:** Es gibt keine Design-Dokumente. Schreibe pro Mission ein
  `Docs/Missions/Mxx_<Name>.md` nach dem Muster von M01 und markiere es `DRAFT – owner review`.
- Jasons Nachname; die 5.000-€-Herkunft (bisher: Euros aus seiner Kolumbien-Arbeit); alle Arbeitsnamen (B-004).
- Was mit **Marco** nach Kapitel 1 passiert (stirbt er bei der Razzia, bleibt er in LA?) – nicht im Kanon.
- Wer die zwei toten Crew-Mitglieder beim Bankraub sind; die Crew-Zusammensetzung.
- Ziel-Spielzeit pro Kapitel; Anzahl Nebenaktivitäten; Wanted-System-Details.
- Ob **Dana Whitlock** in Kapitel 2 wiederkehrt (naheliegend durch Station 14, aber nicht festgelegt).
- Ton und Rating-Ziel (USK 18 / PEGI 18 wahrscheinlich, nicht entschieden).

---

## 5. Asset-Pipeline: ehrliche Bewertung und Neuaufbau auf AAA-Niveau

### 5.1 Was die heutige Pipeline ist
`Tools/uwp` (Python + Blender 5.2.4 LTS headless) baut alles **prozedural aus JSON-Specs**:
- Charaktere auf der CC0-Basis **MakeHuman hm08 / MPFB2-Daten**: Targets, Rig, Gewichte, Kleidung als
  angepasste Hüllen, Cycles-Bake, 20 ARKit/Visem-Blendshapes, 53-Bone-`SkeletonProfileHumanoid`.
- Animationen werden **berechnet** (`build-shared-anims`) oder per `retarget` aus einer CC0-BVH übernommen.
- Waffen, Fahrzeug und LA-Kit entstehen aus Primitiven bzw. dem Hard-Surface-Generator in Draft-PR #11.
- `validate`/`export`: Geometrie, UVs, Topologie, Materialien, LODs, Kollision, Skelett, Benennung, Budgets.
  Dazu kommen `review-sheet` (Referenz neben Render) und die Godot-Import-Tests.

### 5.2 Ehrliche Bewertung
**Was trägt und bleiben soll:**
- Reproduzierbarkeit: Spec → Generator → Export, CI-fähig.
- Das Gerüst aus Validierung, Export und Tests: Achsen (TD-004), Benennung (TD-005), Sockets, Manifest
  mit Loop-Flags, LOD-Post-Import, Budgets.
- Das 53-Bone-Humanoid-Skelett als gemeinsamer Vertrag für alle Charaktere und Clips.
- Der Godot-Import-Pfad (glTF, `uw_post_import.gd`, Asset-Import-Tests).

**Wo der Ansatz an seine Grenze kommt (belegt durch die Reviews in `Docs/Reviews/`):**
| Problem | Ursache im Ansatz |
|---|---|
| Haare wirken wie ein Helm oder eine Plastikhülle | Haare als geschlossene Mesh-Schale statt Hair Cards/Strands mit Alpha und Anisotropie |
| Augenbrauen und Mund sind aufgemalt, die Haut wirkt wachsig | kein gesculptetes Detail, keine Poren- oder Mikro-Normalmaps, generische Skin-Texturen |
| Kleidung sind Schlauch-Hüllen ohne Nähte, Falten, Rippbündchen oder Reißverschluss; die Stiefel sind Klumpen | Kleidung wird geschrumpft und angepasst, nicht simuliert oder gesculptet |
| **Cartel_A hat Jasons Gesicht**, die NPCs sehen sich zu ähnlich | dieselbe hm08-Basis mit kleinen Target-Variationen; keine eigenständigen Kopf-Sculpts |
| Pistole, Limousine und Kit sind Blockouts | Primitive ohne High-Poly-Detail, ohne Bake, ohne Trim-Sheets oder Decals |
| Die Animationen wirken steif, die Füße rutschen bis 4,86 cm | berechnete Keyframes statt Mocap, kein Foot-IK |
| **Alle 5 geprüften Assets: REJECT** | Scores 1–3, nie 4 (Handoff §7) |

**Fazit:** Der rein prozedurale Weg liefert brauchbare **Blockouts und Proportionen**, aber nicht mehr.
Rockstar-Niveau braucht **von Menschen oder Werkzeugen gestaltete Quellassets** (Sculpt, Retopo, Bake,
gemaltes PBR, echte Hair Cards, Mocap). Generatoren bleiben für Blockouts, Kits, Varianten und die
gesamte Validierung und Integration.

### 5.3 Optionen
| Bereich | Option | Bewertung |
|---|---|---|
| **Charakter-Köpfe/Körper** | Sculpt in Blender (Multires/Dyntopo) → Retopo (Quad Remesher oder von Hand) → Bake High→Low (Normal, AO, Curvature) | Empfohlen, volle Kontrolle, keine Lizenzfrage |
| | Character Creator 4 / Headshot (Reallusion), kommerziell | schneller zu realistischen Menschen; **Lizenz für Spiel-Export prüfen, kostet Geld → Eigentümerin entscheidet** |
| | MetaHuman | **nicht verwendbar**: Lizenz an Unreal Engine gebunden |
| | 3D-Scans (CC0/CC-BY, z. B. Scan-Bibliotheken) als Basis | gut für Haut und Kleidung; jede Quelle in `ASSET_LICENSES.md` |
| **Haare** | Blender Hair Curves → Hair Cards (Geometry Nodes) → Bake von Alpha, Tiefe, ID und Root-Tip auf ein Atlas; in Godot ein Shader mit Alpha-Scissor/Hash und Anisotropie | Empfohlen, Industriestandard für Echtzeit |
| **Kleidung** | Marvelous Designer (kommerziell) oder Blender Cloth-Sim → Sculpt-Falten → Retopo → Bake | MD nur mit OK der Eigentümerin; Blender-Cloth geht ohne Kosten |
| **PBR-Texturierung** | Substance 3D Painter (Abo) / ArmorPaint / Blender Texture Paint + Poly-Haven-CC0-Materialien; Trim-Sheets und Decals für die Umgebung | Painter ist Standard (Kosten → Eigentümerin); ArmorPaint und Blender sind kostenlos |
| **Hard Surface (Waffen, Autos)** | Subdivision/Bevel-High-Poly → Low-Poly → Bake (Ansatz aus Draft-PR #11 weiterführen); Autos mit eigenem Lack-Shader (Clearcoat, Flakes), echtem Glas, Chrom, Gummi und Innenraum | Empfohlen |
| **Umgebung** | modulares Kit + Trim-Sheets + Decals + Vertex-Paint-Wear; Kit-Bashing für Varianten; HLOD pro Block | Empfohlen |
| **Quellen fremder Assets** | nur **CC0 oder CC-BY-4.0** (`ASSET_LICENSES.md`). Gekaufte Pakete nur mit Lizenzprüfung, Eintrag und OK der Eigentümerin. NC, Ripps, echte Marken: verboten | verbindlich |

### 5.4 Empfehlung (so baust du die Toolchain neu)
1. **TD-021 „Hybrid-Pipeline“** (PROPOSED → von Bot 1 akzeptieren lassen): Quellassets sind von Hand
   gestaltete `.blend`-Dateien unter `Art/Source/<Asset>/` (LFS, Budget beachten). `Tools/uwp` wird
   zur Pflichtstrecke **Validierung → Export → Import-Test → Review-Sheet**, nicht mehr zum Bildhauer.
   Die Generatoren bleiben für Blockouts, Kits und Varianten.
2. **Pipeline-Audit (T-PIPE-06):** Lies jeden Generator und Validator. Liste Fehler und Lockerungen
   (z. B. das gelockerte `MESH_CLIPPING`-Gate aus PR #8) und repariere sie mit Tests.
   Ziehe TD-012 (LOD-, Kollisions- und Material-Budgets) in `Config/asset_budgets.json` nach (T-PIPE-05).
3. **Look-Dev auf der GPU (T-LOOK-01):** eine Look-Dev-Szene in Forward Plus mit ACES-Tonemapping, Belichtung,
   Volumetric Fog, Wahl der GI (SDFGI/VoxelGI/Lightmaps – entscheiden und als TD festhalten), SSAO/SSIL und
   Referenz-Graukarte. Ohne diese Szene und ein Sign-off durch die Eigentümerin gilt kein Material als bewertet.
4. **Reihenfolge der Assets** (eines nach dem anderen durchs volle Gate, nicht alle halb):
   Pistole (PR #11 fertig machen) → Jason → Limousine → LA-Kit inklusive M01-Props → Marco → Cartel_A/B
   (eigene Gesichter!) → Zivilisten → Cop_LA → Sam.
5. **LOD/HLOD:** LOD0–2 pro Asset (Charaktere 40k/20k/8k als Startwert, Budgets in `asset_budgets.json`),
   HLOD pro Straßenblock für die offene Welt (M4), Visibility Ranges in Godot, Occluder.
6. **Lizenz-Tracking:** jede Quelle sofort in `Docs/ASSET_LICENSES.md` (Quelle, URL, Lizenz, Datum,
   was abgeleitet wurde). Rohdaten bleiben gitignored in `.cache/uwp_sources/`.

---

## 6. Animationen Ende-zu-Ende: Blender → Godot

### 6.1 Heute
- 53-Bone-Skelett, 21 `A_Jason_*`-Clips und eine gemeinsame `A_Humanoid_*`-Bibliothek, berechnet, 30 fps, in-place.
- In Godot: AnimationTree mit Locomotion-Blend, Oberkörper-Aim-Layer (`AimSpineModifier`, SkeletonModifier3D),
  Clips für Shoot, Reload, Carry, Death und Car-Enter/Exit an Ereignissen, Hitboxen an `BoneAttachment3D` (TD-016).
- Es fehlen: Mocap-Qualität, Foot-IK, Root Motion, Sitz-Clips für Fahrer und Beifahrer, Deckung, Nahkampf,
  Gesichtsanimation im Dialog, NPC-spezifische Sets.
- Carry-Clips fehlen bei den NPC-Modellen (Warnung „missing clips for carry_idle, carry_walk“).

### 6.2 Quellen (Lizenzpolitik beachten)
| Quelle | Status |
|---|---|
| Eigenes Mocap (z. B. Rokoko-Anzug, Move.ai, Kamera-Mocap) | beste Qualität und IP-sicher; **Kosten → Eigentümerin entscheidet** |
| CMU Graphics Lab Motion Capture Database | laut Projektseite frei nutzbar; Lizenztext vor Nutzung prüfen und eintragen; Qualität gemischt, braucht Cleanup |
| CC0/CC-BY-BVH-Sammlungen | erlaubt, jede Datei in `ASSET_LICENSES.md` |
| **Mixamo (Adobe)** | **heute durch die Lizenzpolitik ausgeschlossen** (`Docs/ASSET_LICENSES.md`: „Mixamo/Adobe EULA rejected“). Nur wenn die Eigentümerin per TD freigibt; dann keine Roh-FBX ins Repo. |
| Gekaufte Animationspakete | nur mit Spiel-Lizenz, Eintrag und OK der Eigentümerin |
| Keyframe-Polish von Hand in Blender | immer für Hero-Momente (Zielen, Nachladen, Ein- und Aussteigen) |

### 6.3 Ziel-Pipeline
1. **Ingest** in Blender: BVH oder FBX → Cleanup (Rauschen, Fußkontakte), Skalierung auf 1 u = 1 m.
2. **Retarget** auf das 53-Bone-Humanoid-Skelett (vorhandenes `Tools/uwp retarget` reparieren oder ersetzen;
   Bone-Mapping als Datei unter Versionskontrolle).
3. **Clips schneiden** nach TD-005: `A_<Char|Humanoid>_<Action>`, **kein** `_Loop`-Suffix; Loop-Flag nur im Manifest.
   Pro Clip Länge, Loop-Flag, Root-Motion ja/nein und Events (Fußkontakt, Schuss, Magazin raus/rein, Tür).
4. **Validierung** (`uwp validate`): Fußrutschen ≤ 1 cm bei Locomotion, kein Knochen-Flip, Loop-Naht ≤ Toleranz,
   Root-Motion-Kurve plausibel. Werte in `asset_budgets.json`, Tests mit Sabotage.
5. **Godot:**
   - AnimationTree mit BlendSpace2D für Locomotion (Richtung × Geschwindigkeit) und Start/Stop/Pivot-Übergängen.
   - Oberkörper-Layer über eine Bone-Maske ab der Wirbelsäule, Aim-Offsets (Pitch/Yaw) als additive Posen.
   - **Foot-IK** (SkeletonModifier3D / `SkeletonIK3D`-Ersatz in 4.7) auf Treppen und Hängen; Hand-IK für den
     beidhändigen Pistolengriff und das Lenkrad.
   - **Root Motion** für Ein- und Aussteigen, Deckung und Nahkampf (`AnimationTree.root_motion_track`);
     Locomotion bleibt kapselgetrieben.
   - Gesicht: ARKit/Visem-Blendshapes für Lip-Sync im Dialog (M5).
6. **Beweis:** Tests (Clip pro Ereignis, Dauer, Fußrutschen, IK-Fehler < 2 cm) **und** GPU-Videos
   (Gehen, Laufen, Sprint-Stop, Zielen im Laufen, Nachladen, Ein- und Aussteigen) in `Docs/Reports/`.

---

## 7. Roadmap M1–M10 bis zum Release

Prioritäten: **P0** blockiert anderes oder ist release-kritisch · **P1** nötig für den Meilenstein · **P2** Feinschliff.
Jedes Kunst-Item geht durchs Quality Gate. Jedes Code-Item bekommt Headless-Tests mit Sabotage und,
wo es visuell ist, eine GPU-Aufnahme.

### M1 – Vertical Slice „Dead Drop“ spielbar · **Stand: Gameplay headless fertig, Kunst Blockout**
| Pri | Item | Stand |
|---|---|---|
| ✅ | M01-Logik, KI im Auto, Clips/Aim/Hitboxen, HUD, lesbare Greybox, Linux-Export, Einstieg Game_M01 | erledigt (PR #14–#18) |
| P0 | GPU-Abnahme: Build auf der GPU spielen, Video von M01 von Anfang bis Ende, FPS messen (T-BUILD-02) | offen |
| P0 | Pipeline-Audit und Hybrid-Pipeline (T-PIPE-06, TD-021), Look-Dev (T-LOOK-01) | offen |
| P0 | Hero-Kunst durchs Gate: Pistole (T-ART-05), Jason (T-ART-01b), Limousine (T-ART-04), LA-Kit + Props (T-ART-03), Marco und 2 Gangster-Varianten (T-ART-06) | offen, alle REJECT/WIP |
| P0 | Animationen Mocap-Qualität + Foot-IK + Sitz-Clips (T-ANIM-01) | offen |
| P1 | Level-Art-Pass und Golden-Hour-Licht (T-LVL-01b) | offen |
| P1 | Audio v0 (T-AUD-01), Checkpoint-Speichern (T-SAVE-01), Zivilisten (T-AI-02), Verfolgerauto Schritt 6 (T-MIS-01c) | offen |
| P1 | CI: GitHub Actions mit `run_all.sh` + Export (T-QA-01) | offen |

**Exit M1:** M01 von Anfang bis Ende in einem Linux-Build in 10–15 min spielbar, auf einer GPU aufgenommen.
Alle Assets sind PRODUCTION-READY oder ausdrücklich von der Eigentümerin freigestellt, es gibt keine `PT_`-Assets mehr,
`run_all` ist grün und die Eigentümerin hat abgenommen.

### M2 – Kunstqualität über den ganzen Slice + Style-Lock
P0: Referenzboards für jedes Hero-Asset, Charakter-LODs, Haar- und Kleidungslösung, Lack- und Glas-Shader,
Trim-Sheet-Bibliothek, Look-Dev-Sign-off auf der GPU, `Docs/ArtDirection/STYLE_GUIDE.md`.
P1: Gesichts-Blendshapes im Dialog.
**Exit:** alle Slice-Assets ≥ 4 in jeder Kategorie, Style-Guide abgenommen.

### M3 – Kernsysteme
P0: Deckungssystem plus Vault (T-GP-01b), Wanted-Level und Polizei, Verkehr (Spuren, Ampeln, NPC-Fahrer,
Carjacking), Fußgänger mit Tagesablauf, Schadensmodell (Rüstung, Fahrzeugdeformation, Ragdoll T-GP-02b),
Speichern/Laden.
P1: Nahkampf, Waffen-Roster mit Waffenrad, Fahrzeug-Roster (inklusive Kleinflugzeug für „Wings“), Handy und Minimap/GPS,
Wirtschaft und Inventar.
P2: Taxi, Wetter, Tageszeit.
**Exit:** jedes System mit Tests und Sabotage; Polizeijagd und Verkehr auf der GPU aufgenommen.

### M4 – Offene Welt LA
P0: World-Streaming in Chunks (async `ResourceLoader`), LOD/HLOD, Occlusion, Navmesh pro Chunk, Spawning pro Chunk.
Blockout von East Hollow, Downtown, Crestmont Hills, Harbor, Seaview und Freeway-Verbindungen.
P1: Innenräume, eigene Landmarken, San-Ardo-Berge, ländlicher Norden.
**Exit:** freies Fahren durch ≥ 2 Bezirke ohne Ladebildschirm, Speicher- und Frame-Budget auf der Ziel-GPU eingehalten.

### M5 – Kapitel 1 Story (LA)
P0: Missionen Arrival, The Route, Dead Drop (final), The Raid, Wings. Dialog- und Kino-System (AnimationPlayer,
Kamera-Rigs, Untertitel, Lip-Sync). Figuren Sam, Marco, Whitlock und Kartell-Crews.
**Exit:** Kapitel 1 von Anfang bis Ende spielbar, mit Checkpoints und Fail-States; Missionsdesigns von der Eigentümerin abgenommen.

### M6 – Kapitel 2 (New York)
P0: fiktionalisierte Bezirke (Brooklyn zuerst), kalter und nasser Look, Taxi, Stationen 6–16, Kings of Flatbush, La Hermandad.
P1: U-Bahn, Brücken, Staten Island, Park.
**Exit:** Kapitel 2 von Anfang bis Ende spielbar, Abnahme wie in M5.

### M7 – UI/UX, Menüs, Einstellungen, Barrierefreiheit
P0: Haupt- und Pausemenü (ersetzt `Game_M01.tscn` als Main-Scene, TD-020), Einstellungen (Grafik-Presets,
Auflösung, FOV, Tastenbelegung und Gamepad, Audio), Speicherslots, Ladebildschirme.
P1: Untertitel-Optionen, Farbenblind-Modi, Zielhilfe, Halten/Umschalten, Kamerawackeln aus, Schwierigkeit.

### M8 – Audio, Sprachausgabe, Musik
P0: Waffen-, Fahrzeug- und Ambience-Sets, Mix, Radiosender (eigen, CC-BY oder beauftragt), Sprachausgabe
(Sprecher oder lizenziertes TTS mit geklärten Rechten → Eigentümerin entscheidet), Score. Alle Lizenzen dokumentiert.

### M9 – Performance, Plattformen, QA, CI, Builds, Lokalisierung
P0: Zielplattformen mit der Eigentümerin festlegen (zuerst Windows- und Linux-PC), Mindest- und empfohlene Specs,
60 fps auf Mittelklasse-GPU (TD-009), Profiling, Speicherbudgets, CI mit nächtlichen Builds, Windows-Export,
Soak-Tests, Bugtracker.
P1: Lokalisierung DE/EN.

### M10 – Release
P0: Store-Seite (Steam/itch, Konto der Eigentümerin), Altersfreigabe (USK/PEGI/ESRB über IARC), EULA und
Datenschutz, Drittanbieter-Lizenzdatei aus `ASSET_LICENSES.md` plus Godot/MIT-Hinweise, Marken- und IP-Prüfung
aller Namen (B-004), Crash-Reporting, Versionierung und Changelog, finaler QA-Pass, signierter Launch-Build.
**Jede externe Einreichung braucht das OK der Eigentümerin.**

**Reihenfolge:** M1 → M2 (überlappt mit M1-Kunst) → M3 → M4 → M5 → M6, dazu M7–M9 laufend ab M3, M10 zuletzt.

---

## 8. Wo du weitermachst: die nächsten Tasks in Reihenfolge

Jeder Task bekommt einen eigenen Branch (`claude/<task-id>-<slug>`) und einen eigenen PR. Trage den Task beim
Start in `Docs/TASK_BOARD.md` ein (IN PROGRESS) und beim Abschluss mit Beweis (READY FOR REVIEW). Bot 1 setzt COMPLETED.
Arbeite die Liste **in dieser Reihenfolge** ab. Wenn du einen Task nicht beenden kannst, öffne einen Draft-PR,
schreib die Ursache auf und mach mit dem nächsten unabhängigen Task weiter.

| # | ID | Pri | Was | Akzeptanz (Kurzform) |
|---|---|---|---|---|
| 1 | **T-ENV-01** | P0 | Deine Umgebung aufsetzen: Blender 5.2.4 LTS, Godot 4.7.2 (gleiche Version!), git-lfs, offizielle Linux- und Windows-Export-Templates 4.7.2, GPU-Treiber (Vulkan). `Tests/run_all.sh` grün. | `RUN_ALL: PASS`, 749 Checks; Versionen in `Docs/TOOLCHAIN_SANDBOX.md` |
| 2 | **T-BUILD-02** | P0 | **GPU-Abnahme des Ist-Stands:** Build exportieren, M01 von Hand von Anfang bis Ende spielen, Video aufnehmen, FPS (Durchschnitt und 1 % Low) messen, Forward-Plus-Screenshots machen. Fehler als Bugs eintragen. | Video und Screenshots in `Docs/Reports/renders_gpu_m01/`, ehrlicher Bericht (was hakt: Kamera, Fahrgefühl, KI, Licht) |
| 3 | **T-QA-01** | P1 | GitHub Actions: `Tests/run_all.sh` (Godot und Blender gecacht, LFS) + Linux-Export bei jedem PR; Pflicht-Check auf `main` (Branch-Schutz setzt Bot 1). Phase-8-Capture als Artefakt. | grüner CI-Lauf auf einem Test-PR, Sabotage-Lauf zeigt rot |
| 4 | **T-PIPE-06** | P0 | Pipeline-Audit (§5.2): jeden Generator und Validator lesen, Fehler und Lockerungen auflisten, `MESH_CLIPPING` neu bewerten, TD-021 Hybrid-Pipeline vorschlagen; **T-PIPE-05**: TD-012-Budgets in `Config/asset_budgets.json`. | Audit-Bericht + TD-021 PROPOSED + Tests für jede reparierte Regel |
| 5 | **T-LOOK-01** | P0 | GPU-Look-Dev-Szene (Forward Plus, ACES, Fog, GI-Entscheidung als TD, Graukarte, Golden-Hour-Preset `ENV_LA_*`), Referenzrenders | Sign-off-Paket für die Eigentümerin (Bilder + Werte) |
| 6 | **T-ART-05** | P0 | Pistole fertig: Draft-PR #11 übernehmen (Branch `art/t-art-05-pistol`, `origin/main` hineinmergen), High/Low + Bake, Referenzboard-Lizenzen prüfen, volles Gate. | Review ≥ 4 in allen Kategorien, GPU-Aufnahme in der Hand, `test_weapon.gd` auf dem echten glb grün; #11 schließen |
| 7 | **T-ANIM-01** | P0 | Animations-Pipeline neu (§6.3): Quelle (Eigentümerin entscheidet: Mocap oder CC0), Retarget, Foot-IK, Hand-IK, Root Motion fürs Ein- und Aussteigen, **Sitz-Clips Fahrer/Beifahrer** (dann Marco wieder sichtbar im Auto), Carry-Clips für NPCs. | Fußrutschen ≤ 1 cm, Tests + Sabotage, GPU-Videos |
| 8 | **T-ART-01b** | P0 | Jason neu nach Hybrid-Pipeline: Sculpt, Hair Cards mit Skin Fade, gepflegter Bart, Bomberjacke mit Rippbündchen und Reißverschluss, Jeans mit Nähten, geschnürte Stiefel, LOD0–2, weniger Materialien. | Gate ≥ 4 überall, Nahaufnahme und Gameplay-Shot auf der GPU |
| 9 | **T-ART-06** | P0 | Marco, Cartel_A, Cartel_B mit **eigenen Gesichtern** (Cartel_A darf nicht Jason sein), danach Zivilisten, Cop_LA, Sam neu. Referenzboards zuerst. | je Asset Gate ≥ 4; Gesichtsvergleich als Sheet im Review |
| 10 | **T-ART-04** | P0 | Limousine: echte Karosserie, Glas, Chrom, Gummi, Lichter, Innenraum, Lenkrad; CR-1 bis CR-4 aus `REQ_VEH_Sedan_01.md`; Ein- und Aussteige-Clips an die Sockets anpassen. | Gate ≥ 4; `test_vehicle.gd` grün; Fahrvideo auf der GPU |
| 11 | **T-ART-03 + T-LVL-01b** | P0 | LA-Kit fertig (Markise, Zebrastreifen, Ampel, Wohnblock, Hydrant, Müll, Bushaltestelle, Zaun, Container, Garagen-Innenraum mit Rolltor), Trim-Sheets, Decals, Abnutzung, erfundene Schilder; Level über den Generator neu, Golden-Hour-Licht. | Umgebungs-Checkliste im Gate erfüllt; `test_level.gd` grün; Übersicht, Straßenniveau und Garage auf der GPU |
| 12 | **T-AUD-01** | P1 | Audio v0: Pistole, Einschläge, Schritte, Motor/Reifen/Crash, Ambience, UI, Platzhalter-Telefonstimme von Sam mit Untertiteln; nur CC0/CC-BY. | Busse eingerichtet; Quellen in `ASSET_LICENSES.md`; Test, dass Ereignisse Sounds auslösen |
| 13 | **T-SAVE-01** | P1 | Checkpoint speichern und laden (Missionsstand, Spieler, Auto, Paket); Neustart nach Beenden. | Test inklusive Sabotage |
| 14 | **T-AI-02 + T-MIS-01c** | P1 | Zivilisten auf der Calloway Ave (Routen, Idle, Flucht ≤ 25 m, Beruhigen); optionales Verfolgerauto in Schritt 6 (2 Schützen). | Tests + Sabotage + GPU-Aufnahme |
| 15 | **T-DOC-01** | P2 | GDD §2 korrigieren: Jason Anfang 30, graues Rundhals-T-Shirt (Art Direction gilt). | Doc-Diff |
| 16 | **M1-Abnahme** | P0 | M01 in 10–15 min im Linux-Build auf der GPU, Video, keine `PT_`-Assets, alle Gates grün | Abnahme durch die Eigentümerin |
| 17 | danach | | M2 → M3 → M4 → M5 → M6 laut §7; pro Mission zuerst ein Design-Dokument (DRAFT, Abnahme durch die Eigentümerin), dann bauen | – |

**Kein neuer Content vor Task 2 (GPU-Abnahme).** Erst muss klar sein, wie der Ist-Stand auf echter Hardware aussieht.

---

## 9. Standards (verbindlich)

### 9.1 AAA-Quality-Gate (`Docs/QUALITY_GATE.md` ganz lesen)
1. **Referenz zuerst:**
   - Referenzen recherchieren, an den einen UNDERWORLD-Look anpassen.
   - Maße in Metern festlegen, Zielqualität und Pflichtdetails festlegen.
   - Referenzboard `Docs/ArtDirection/References/<Asset>/` anlegen, mit `SOURCES.md` (jede Quelle mit Lizenz, nur CC0, CC-BY oder eigenes Konzept).
2. **Acht Phasen:**
   1. Blockout
   2. High-Quality-Modellierung
   3. PBR-Materialien
   4. Licht- und Multi-Angle-Renders (Cycles, nicht Workbench)
   5. Unabhängiges Review gegen die Referenzen
   6. Verfeinerung, bis das Review besteht
   7. Game-Ready-Validierung (`Tools/uwp validate/export` PASS)
   8. **Godot-Integration** unter Gameplay-Licht und -Kamera, mit dir **auf der GPU in Forward Plus**
      (llvmpipe/gl_compatibility nur noch als CI-Ersatz, immer so gekennzeichnet)
3. **Unabhängiges Review:** Der Ersteller ist nie der einzige Prüfer.
   - Rollen: Ersteller, Art-Reviewer, Engine-Reviewer.
   - Als einzelner Agent machst du getrennte Durchgänge mit frischem Blick, z. B. einen Subagenten, der nur
     Renders und Referenzen sieht. Dokumentiere, wer geprüft hat.
   - Die Freigabe macht Bot 1.
4. **Bewertung 0–5** in: Silhouette, Proportionen, Geometrie, Materialien, Texturen, Licht, visuelles Detail,
   Animationsqualität, technische Optimierung, Engine-Integration.
   - **Bestanden heißt ≥ 4 in jeder zutreffenden Kategorie.** Eine 3 lässt das Asset durchfallen.
   - Nie Scores schönen.
   - Vorlage `Docs/Reviews/TEMPLATE_ASSET_REVIEW.md`, Datei `Docs/Reviews/YYYY-MM-DD_<asset>.md`
     plus Sheet von `Tools/uwp review-sheet`.
5. Checklisten für Charaktere, Fahrzeuge und Umgebung stehen in `QUALITY_GATE.md` §5–§7, dazu eine einheitliche visuelle Identität.
6. `PRODUCTION-READY` steht im `ASSET_REGISTRY.md` **nur** nach bestandenem Gate.

### 9.2 Merge-Gate und Tests
- **`Tests/run_all.sh` muss `RUN_ALL: PASS` auf einem frischen Worktree des exakten PR-Heads drucken**:
  `git worktree add /tmp/wt <sha> && cd /tmp/wt && git lfs pull && ./Tests/run_all.sh`.
- Die Zahlen dürfen nur steigen. Kein Test wird gelöscht, gelockert oder übersprungen. Schwellwerte ändern
  nur mit Begründung im PR.
- **Jedes neue Feature bekommt einen Sabotage-Modus**, der die echte Produktionslogik oder Daten verfälscht,
  sodass die **normalen** Checks fehlschlagen.
  - Verboten: Sabotage, die nur einen eigenen Extra-Check scheitern lässt.
  - Schalter `UW_<BEREICH>_SABOTAGE`, nur in Debug-Builds (`OS.is_debug_build()`, TD-020).
  - Im PR die Tabelle „Modus → Exit → Anzahl FAIL“ aufführen und **alle** alten Modi erneut fahren.
- Flaky Tests sind Bugs: Ursache finden (z. B. asynchrone Navigation), nie mit „nochmal laufen lassen“ oder
  gelockerten Checks verdecken.
- `uw_lod_post_import.gd` bleibt byte-identisch in `Tools/underworld_pipeline/godot/` und `GodotProject/Scripts/import/`.

### 9.3 Visuelle Beweise
- Jede visuelle Aussage braucht ein Bild oder Video von der GPU (Forward Plus). Die Capture-Skripte kommen ins Repo
  (`GodotProject/Tests/tools/`), die Bilder unter LFS nach `Docs/Reports/renders_<task>/`.
- Schau dir jedes Bild selbst an und beschreib es ehrlich. „Sieht gut aus“ ohne Bild gilt nicht.

### 9.4 Git und LFS
- **Git LFS ist Pflicht:** `git lfs install` vor dem ersten Commit. `.blend .glb .gltf .fbx .png .jpg .jpeg .exr
  .hdr .tga .wav .ogg .mp3 .mp4 .ttf .otf` nur über LFS (`.gitattributes`).
  - Vor jedem Push prüfen: `git lfs ls-files` und dass gestagte Binärdateien Pointer sind.
  - PR #14 hat 106 Binärdateien als Blob committet, das darf nie wieder passieren.
- **LFS-Budget:** GitHub Free ≈ 1 GB Speicher + 1 GB/Monat Traffic. Texturen standardmäßig 1024², Hero 2048².
  Keine Bake-Zwischenstände, keine Rohquellen > 4K. Ab ca. 700 MB vorher die Eigentümerin fragen (Datenpaket kostet Geld).
- Kein Force-Push, kein History-Rewrite, kein `reset --hard` auf geteilten Branches.
  - Branches aktualisierst du per `git merge origin/main`, nicht per Rebase.
  - Keine Branches oder Repos löschen.
- Ein Task pro Branch und PR. Commit-Nachrichten im Format `[T-XXX-NN] Zusammenfassung`.
- Keine Secrets und keine Dateien > 100 MB committen.

### 9.5 Technische Entscheidungen und Konventionen (`Docs/TECHNICAL_DECISIONS.md`)
| TD | Inhalt |
|---|---|
| TD-001 | Godot 4.7.2 statt Unreal (MIT, headless-fähig, glTF nativ) |
| TD-002 | Blender headless (`bpy`) als Asset-Pipeline, reproduzierbar |
| TD-003 | glTF 2.0 binär (`.glb`) als Austauschformat |
| TD-004 | 1 u = 1 m; Blender −Y = Godot +Z (Vorderseite); Ursprung am Boden; der Charakter schaut nach +Z |
| TD-005 | Präfixe `SK_ SM_ A_ M_ T_ VH_ WPN_ PT_ UCX_`, `SOCKET_<Name>`, LOD-Suffixe `_LOD0..2`, Skripte `snake_case.gd`, Szenen `PascalCase.tscn`; **kein Aktionsname endet auf `_Loop`/`_Cycle`** (Godot erzwingt sonst Looping) |
| TD-006/007/008 | Ordnerkonventionen, Datei-Eigentum, Git-Workflow |
| TD-009 | Performance-Budgets (nach dem ersten GPU-Test überarbeiten) |
| TD-010 | Physik-Layer, Input-Map nur über `Scripts/tools/setup_input_map.gd`, `run_all.sh` als Merge-Gate |
| TD-011 | Spieler-Kollision als Zylinder |
| TD-012 | LOD-, Kollisions- und Material-Budgets (**PROPOSED**, mit T-PIPE-05 anwenden) |
| TD-013 | NPC-KI-Architektur |
| TD-014 | VehicleBody3D, zur Laufzeit aus `VH_*.glb` montiert (Static-Sag-Konstante bei Godot-Upgrades prüfen) |
| TD-015 | Gegner vs. Spieler im Auto (Fahrerfenster 25 %) – ACCEPTED |
| TD-016 | Animations-Verdrahtung, Oberkörper-Layer, Knochen-Hitboxen |
| TD-017 | HUD als reiner Listener |
| TD-018 | Greybox-Lesbarkeit im Generator |
| TD-019 | Linux-Export |
| TD-020 | Einstiegsszene `Game_M01.tscn`; Sabotage-Schalter nur in Debug-Builds |
| ab TD-021 | deine neuen Entscheidungen: erst PROPOSED, dann ACCEPTED durch Bot 1 oder die Eigentümerin |

Weitere Regeln: Platzhalter tragen das Präfix `PT_` und verschwinden vor dem Meilenstein-Abschluss.
Generierte Dateien änderst du über den Generator, nicht von Hand. Asset-Requests liegen als `Docs/Handoffs/REQ_<name>.md` vor.

### 9.6 Merge-Politik
- **Du öffnest PRs. Bot 1 reviewt und merged.** Selbst mergen darfst du nur, wenn die Eigentümerin es in einem
  Arbeitsauftrag ausdrücklich mit der Zeile `MERGE-FREIGABE: JA (Task-IDs …)` erlaubt **und** alle Gates grün sind.
- **Für diesen Master-Prompt gilt: MERGE-FREIGABE: NEIN.**
- Bot 1 merged mit `gh pr merge <n> --merge --match-head-commit <sha>` nach eigenem Gate-Lauf auf einem frischen Worktree.
- Keine Drafts und nichts Rotes zum Mergen anbieten. Abhängige PRs: „basiert auf #N“ in den Text.

### 9.7 Ehrlichkeit
- „Fertig“ heißt: Akzeptanzkriterien erfüllt, Gates grün, Beweis verlinkt. Alles andere heißt „teilweise“.
- Nie „AAA“, „production-ready“, „getestet“ oder „spielbar“ ohne Beweis sagen.
- Keine Platzhalter als Endstand, keine Tests anpassen, damit sie grün werden, keine Zahlen schönen.
- Unklare Design- oder Story-Fragen gehen als Entscheidungsvorlage an die Eigentümerin, nie als stille Änderung.

---

## 10. Skills, Tools und der Game-Studio-Skill

### 10.1 Geprüfte Skill-Repos (`Docs/SKILLS_AND_TOOLS.md` = volle Begründung)
Die Repos liegen auf der alten Box schreibgeschützt unter `/workspace/tools/skills-vendor/` und **nicht** im Git-Repo.
Auf deiner Maschine klonst du sie mit `git clone --depth 1` neu und pinnst sie auf den Commit aus `SKILLS_AND_TOOLS.md`.

| Repo | Urteil | Lizenz | Wofür |
|---|---|---|---|
| setcodes/gamedev-skills | USE | MIT | `godot-gamedev`, `game-designer`, `blender-game-assets` (Headless-Helfer); MCP-Bridge nicht nutzen |
| majidmanzarpour/blender-game-skills | USE | MIT | `blender-image-to-3d`: Modellier-Schleife mit Referenzvergleich, `review_render.py --engine cycles` |
| sekaikx/ForgeSkills | USE | Apache-2.0 | Orchestrierung/Verifikation, blender-headless, modular-kit, texture, animation, lighting |
| proyecto26/blender-ai-plugin | PARTLY | MIT | nur Skripte (LOD, Kollision, Rig-Check, UV, Bake) per `blender -b --python`; nie importieren |
| yi00it/blender-asset-mcp | PARTLY (nur lesen) | MIT | Algorithmen lesen, nicht ausführen |
| Sods2/godot-mcp | PARTLY, nicht installiert | MIT | eventuell später; lieber eigene Capture-Skripte |
| pbzona/godot-skills | USE (Doku) | MIT | 3D-Gameplay, Navigation/KI, Architektur |
| TheMarco/godot-game-skills | USE (selektiv) | MIT | Verifikation, Performance, Prop-Integration, Abnutzung |
| gamedev-skills/awesome-gamedev-agent-skills | USE (Godot + Workflows) | Apache-2.0 | Headless-Testing, GDScript, 3D, Physik, Animation, Export |
| maystudios/claude-skills | SKIP | MIT | UE5, Medien-Tools mit API-Keys und Laufzeit-pip |
| kevinpbuckley/unreal-engine-skills | SKIP | keine | falsche Engine, keine Lizenz |

Empfohlene Projekt-Skills (nur die Ordner kopieren, nachdem du sie gelesen hast, mit LICENSE/NOTICE daneben,
Eintrag in `SKILLS_AND_TOOLS.md`): `godot-gamedev`, `game-designer`, `blender-image-to-3d`,
`gamedev-blender-headless`, `gamedev-verification`, `godot-gdscript-headless-testing`, `godot-performance-workflows`
→ nach `.claude/skills/`. Skills sind Hilfen; `Tools/uwp`, die TDs und das Quality Gate gehen vor.

### 10.2 Der Game-Studio-Skill von GitHub (geprüft 2026-11-23)
**Bester Kandidat: [Donchitos/Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios)**
- MIT-Lizenz, rund **40.700 Sterne**, 5.300 Forks, aktiv: Release **v1.3.0 vom 2026-11-09**, Commit `abc0de7`.
- Inhalt: **49 Agenten** in drei Ebenen:
  - Directors: creative-director, technical-director, producer.
  - Leads: game-designer, lead-programmer, art-director, qa-lead, release-manager und weitere.
  - Specialists, darunter **godot-specialist, godot-gdscript-specialist, godot-shader-specialist**,
    technical-artist, level-designer, ai-programmer und performance-analyst.
- Dazu 75 Workflow-Skills (`/design-system`, `/create-stories`, `/dev-story`, `/gate-check`,
  `/vertical-slice`, `/regression-suite`, `/perf-profile`, `/release-checklist`, `/launch-checklist` …),
  15 Hooks, 14 Regeln und 62 Vorlagen (GDD, ADR, HUD, Barrierefreiheit).
- Die Agenten sind auf Zusammenarbeit ausgelegt („fragen → Optionen → du entscheidest → Entwurf → Freigabe“).

**Prüfbefund (Bot 1 hat den Code gelesen, nichts ausgeführt):**
- Es ist ein **Projekt-Template**: Es bringt eigene `CLAUDE.md`, `.claude/settings.json`, `project.yaml` und
  `src/`-Struktur mit. Über unser Repo kopiert, würde es unsere Regeln und Pfade überschreiben.
- `.claude/settings.json` registriert **Hooks auf fast jedem Tool-Aufruf** (SessionStart, PreToolUse Bash/Write/Edit/Read,
  PostToolUse, Stop, PreCompact, Notification), alle als Bash-Skripte unter `.claude/hooks/`.
  - `session-start.sh` ruft `update-check.sh` auf, das per `curl`/`wget` die GitHub-API abfragt
    (Netzwerkzugriff bei jedem Sitzungsstart, abschaltbar mit `updates.check=false`).
  - `validate-commit.sh` und `validate-push.sh` sind nützlich (blockieren Force-Push, prüfen LFS-Pointer),
    `deny`-Regeln für `rm -rf`, `git push --force`, `git reset --hard` und `sudo` passen zu unseren Regeln.
- `.claude/scripts/vendor-three.sh` und `test-scaffold.sh` nutzen `npm`/`npx`/`curl`. Sie sind nur für den
  Web-Pfad gedacht und für uns irrelevant: **nie ausführen**.
- Die Agenten-Frontmatter fordern bestimmte Modelle an (Opus/Sonnet). Das kostet Nutzung, also bewusst wählen.

**Urteil: PARTLY / selektiv nutzen, nicht als Template über das Repo legen, nicht ins Repo vendoren.**
Sichere Nutzung:
```bash
# 1. Außerhalb des Repos klonen und pinnen
git clone --depth 1 https://github.com/Donchitos/Claude-Code-Game-Studios ~/vendor/ccgs
git -C ~/vendor/ccgs log --oneline -1          # erwartet abc0de7 (v1.3.0) oder neuer: dann neu prüfen
# 2. Lesen, bevor irgendetwas aktiv wird
less ~/vendor/ccgs/.claude/settings.json ~/vendor/ccgs/.claude/hooks/*.sh
# 3. Nur ausgewählte Agenten in den USER-Bereich kopieren (nicht ins Projekt):
mkdir -p ~/.claude/agents
cp ~/vendor/ccgs/.claude/agents/{godot-specialist,godot-gdscript-specialist,godot-shader-specialist,technical-artist,level-designer,qa-lead,performance-analyst,release-manager}.md ~/.claude/agents/
# 4. Agenten-Texte anpassen: Pfade (src/ → GodotProject/), Verweise auf ihre Docs durch unsere ersetzen
#    (QUALITY_GATE.md, TECHNICAL_DECISIONS.md, TASK_BOARD.md); Modell-Zeile bewusst setzen.
# 5. Hooks: zunächst KEINE. Wenn gewünscht, nur validate-push.sh/validate-commit.sh nach Review,
#    als TD-Eintrag, ohne update-check.sh. Keine npm/npx-Skripte.
```
Vorlagen (GDD, ADR, Sprint, Release-Checkliste) darfst du als **Inspiration** lesen. Eigene Dokumente bleiben in
`Docs/` in unserem Format.

**Alternativen (geprüft per GitHub-API, 2026-11-23):**
| Repo | Sterne | Lizenz | Bewertung |
|---|---:|---|---|
| bgrenat/godot-game-dev-studio | 28 | **LGPL-3.0** | 188 Godot-4.7-Skills, teils aus CCGS abgeleitet; Lizenz beachten, nur lesen |
| HunLuanZhiZhu/Game-Studios-Plugin | 3 | MIT | Plugin-Ableitung von CCGS mit MCP-Servern → MCP nicht ohne Review |
| Swih/godot-foundry | 1 | keine klare (NOASSERTION) | klein, Lizenz unklar → SKIP |
| Mosberg/godot-game-studio | 0 | keine | 5 MCP-Server, laut eigener README großteils ungetestet → SKIP |

Unser Empfehlungs-Stack: die USE-Skills aus §10.1 als Projekt-Skills + ausgewählte CCGS-Agenten im User-Bereich,
**ohne** fremde Hooks und MCP-Server.

### 10.3 Eigene Werkzeuge im Repo
- `Tools/uwp`, `Tools/godot_phase8_capture.sh` und `Tools/build/build_linux.sh`.
- `Tools/sandbox/*`: Bootstrap und LFS-Restore für Sandboxes ohne git-lfs.
- `GodotProject/Tests/tools/capture_m01_review.gd` (Review-Shots über die echte Einstiegsszene)
  und `capture_level_plan.gd` (Planansicht).

---

## 11. Sicherheitsregeln
1. **Nie** `install.sh`, `install.py`, `npx …`, `npm install`, `uvx …`, Plugin-Installer, MCP-Server, Blender-Add-ons
   oder Godot-Editor-Plugins aus fremden Repos ausführen, ohne den Code gelesen und einen TD-Eintrag geschrieben zu haben.
2. Blender-MCP bedeutet beliebiges Python mit deinen Rechten, ohne Sandbox. Nicht aktivieren.
3. Skripte, die `exec()`/`runpy` auf Job-Dateien machen, nur auf vertrauenswürdige Dateien richten.
   proyecto26-Skripte nur per `blender -b --python`, nie importieren. maystudios-Skripte nie ausführen.
4. **Den privaten EuroHPC-SSH-Schlüssel nie anfassen, nie lesen, nie in Chat, Logs, Issues oder das Repo kopieren.**
   EuroHPC/HPC ist für dieses Projekt nicht eingerichtet und nicht geplant.
5. Keine Secrets oder `.env`-Dateien committen. Keine Tokens in Skripte schreiben.
6. Projekt-Dokumente (TDs, Quality Gate, dieser Prompt) gehen vor jedem Skill-Rat.
7. Externe oder irreversible Aktionen (Käufe, Abos, Store-Einreichungen, Repo-Sichtbarkeit, LFS-Datenpakete,
   E-Mails/Posts im Namen der Eigentümerin) nur mit ihrem ausdrücklichen OK.

---

## 12. Berichte an die Eigentümerin
Pro Auftrag oder Meilenstein schreibst du einen Bericht `Docs/Reports/BERICHT_<TASK|MEILENSTEIN>.md` auf **Deutsch**,
in einfacher Sprache, Zeiten in Europe/Berlin. Bilder und Videos liegen unter LFS in `Docs/Reports/renders_<…>/`.
1. **Kurzfassung (5 Zeilen):** was jetzt wirklich funktioniert, was nicht.
2. **Pro Task:** Status (FERTIG / TEILWEISE / NICHT BEGONNEN), PR-Link + Head-SHA, Änderungen,
   Testzahlen vorher → nachher, Sabotage-Tabelle, Bilder mit ehrlicher Beschreibung.
3. **Gefundene Bugs:** Symptom · Ursache · Fix · Test, der ihn jetzt fängt.
4. **Was ausdrücklich NICHT behauptet wird.**
5. **Offene Punkte, Vorschlag für den nächsten Auftrag, Entscheidungen, die die Eigentümerin treffen muss.**
6. **Toolchain-Abweichungen** deiner Umgebung, mit Beleg.

---

## 13. Offene Entscheidungen der Eigentümerin (OFFEN)
| # | Frage | Wo |
|---|---|---|
| E-1 | Jasons Nachname; Arbeitsnamen (Los Cuervos, La Hermandad del Sur, Marco Ruiz, Dana Whitlock, Calloway Avenue, East Hollow) | B-004 |
| E-2 | Missionsnummern: bekommen Arrival/The Route eigene IDs vor M01? | §4.5 |
| E-3 | Animationsquelle: eigenes Mocap (Kosten), CC0/CMU, oder Mixamo per TD freigeben? | §6.2 |
| E-4 | Kommerzielle Tools (Substance Painter, Marvelous Designer, Character Creator) ja/nein, Budget | §5.3 |
| E-5 | GPU-Hardware und Zielplattformen (Windows + Linux zuerst?), Mindestspezifikation | M9 |
| E-6 | Sprachausgabe: Sprecher oder TTS, Sprachen (DE/EN) | M8 |
| E-7 | LFS-Datenpaket, sobald ~700 MB erreicht sind | §9.4 |
| E-8 | Altersfreigabe-Ziel, Store (Steam/itch), Release-Termin | M10 |
| E-9 | Story-Lücken aus §4.5 (Marcos Schicksal, Bankraub-Crew, Spielzeit, Whitlock in Kap. 2) | §4.5 |

---

## 14. Start-Checkliste für deine erste Sitzung
```bash
git clone https://github.com/clarityosbaerbelwesterop-gif/UNDERWORLD-The-American-Dream.git underworld
cd underworld && git lfs install && git lfs pull
git log --oneline -5                     # main enthält den Merge von PR #17 + Review-PR #18
# Werkzeuge: Blender 5.2.4 LTS, Godot 4.7.2 stable (exakt), git-lfs; Pfade per BLENDER=/GODOT= setzen
export GODOT=/pfad/zu/Godot_v4.7.2-stable_linux.x86_64 BLENDER=/pfad/zu/blender
./Tests/run_all.sh                       # erwartet RUN_ALL: PASS, 749 Checks
Tools/build/build_linux.sh               # Templates 4.7.2 nach ~/.local/share/godot/export_templates/4.7.2.stable/
./Builds/linux/Underworld.x86_64         # auf der GPU: bootet in M01 („Get in the car.“)
gh pr list                                # offen: Draft #11 (Pistole)
```
Dann: `Docs/TASK_BOARD.md` öffnen und mit **§8 Task 1 (T-ENV-01)** beginnen. Den ersten Bericht schickst du nach
**Task 2 (GPU-Abnahme)**, mit Video.

**MERGE-FREIGABE: NEIN** – PRs öffnen, Bot 1 reviewt und merged.
