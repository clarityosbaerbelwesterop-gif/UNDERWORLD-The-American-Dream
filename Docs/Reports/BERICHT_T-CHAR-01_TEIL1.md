# Bericht T-CHAR-01 Teil 1 – Gegner sind keine roten Kapseln mehr; Rüstung sichtbar je Stufe

**Datum:** 2026-11-24 · **Autor:** Claude Code · **Status:** READY FOR REVIEW

## 1. Fund (Bug, sichtbar im M01-Video)
**Jeder Gegner und jeder Zivilist in M01 wurde als rote bzw. farbige Kapsel über dem echten Modell gerendert.** Belege: `Docs/Reports/renders_fwdplus_m01/M01_playthrough_contact.jpg`, Bilder 0:50 und 3:27.

- **Ursache:** `CharacterVisual.set_model()` blendet nur die eigenen `PT_`-Kinder aus. In den NPC-Szenen (`build_npc_scenes.gd`) liegen `PT_Capsule` und `PT_FrontMarker` aber als **Geschwister** unter `Pose/Visual`.
- **Spieler:** nicht betroffen, weil seine Kapsel ein Kind von `CharacterVisual` ist.
- **Fix:** `set_model()` blendet jetzt auch Stand-in-**Meshes** unter den Geschwistern aus. Der Waffen-Socket `PT_SOCKET_RightHand_Weapon` bleibt sichtbar, weil er die Waffe trägt.
- **Test** (`test_combat_db.gd`): Kapsel und Marker sind unsichtbar, der Waffen-Socket ist sichtbar.
- **Negativkontrolle:** `UW_ANIM_SABOTAGE=capsule` ergibt FAIL.

## 2. Rüstung sichtbar je Stufe
- `CombatDB.apply(npc, archetype)` hängt die Rüstungs-Props aus `combat.json` an das Skelett:
  - **Weste** am Knochen `Chest`: Unterkante an der Hüfte, Breite auf die Schulterbreite skaliert.
  - **Helm** am Knochen `Head`.
- Die Kollision der Pickup-Props wird entfernt; Treffer nehmen nur die Hitboxen.
- Damit liest man die Stufe vor dem ersten Schuss:

| Stufe | Ausrüstung |
|---|---|
| leicht | ohne |
| mittel | Weste |
| schwer, Boss, FBI | Plattenträger und Helm |

- **Test:** Der schwere Gegner hat 2 Rüstungs-Anhänge mit Meshes und 0 Kollisionskörpern.

## 3. Aufstellung (in-engine)
- **Werkzeug:** `Tests/tools/capture_archetypes.gd`. Es stellt pro Fraktion je einen NPC für Zivilist, leicht, mittel, schwer und Boss auf, mit echtem `CombatDB.apply()`. Vorhandene Fraktionsmodelle aus dem Kader werden automatisch genutzt.
- **Bild:** `Docs/Reports/renders_characters/lineup_tiers_part1_fwdplus.jpg` (Forward Plus): echte Figuren statt Kapseln, Helme und Plattenträger bei schwer und Boss.

## 4. Offen
- **Teil 2:** die 13 Fraktions- und Boss-Figuren aus `Config/Characters/*.json` über `build-character`. Die MakeHuman-CC0-Quellen sind jetzt erreichbar, der Download läuft.
- Die Westen sitzen bei sehr breiten Figuren noch ohne Clipping-Prüfung (P4-Feinschliff).
