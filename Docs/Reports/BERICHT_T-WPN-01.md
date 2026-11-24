# Bericht T-WPN-01 – P5: Waffen-Grammatik und 9 Waffen

**Datum:** 2026-11-23 · **Autor:** Claude Code · **Status:** READY FOR REVIEW · **TD:** TD-028 (PROPOSED)

## 1. Ergebnis
`Tools/uwp build-weapons` baut alle 9 noch fehlenden Waffen aus `combat.json`. Jede besteht aus mehreren Teilen, ist geriggt und folgt dem Pistolen-Vertrag **REQ-GP02**:

| Waffe | Teile | Rig und Clips | Dreiecke | Materialien |
|---|---|---|---|---|
| Revolver | Frame, Barrel, Magazine (Trommel), Hammer, Trigger | Fire (Hahn), Reload 2,6 s (Trommel schwenkt aus), Empty | 508 | 3 |
| SMG | Frame, Barrel, Magazine, Slide (Verschluss), Trigger | Fire, Reload 2,0 s, Empty | 508 | 2 |
| Shotgun (Pump) | Frame (Holzschaft), Barrel, Magazine (Röhre), Slide (Pumpe), Trigger | Fire mit Repetieren, Reload 3,2 s, Empty | 592 | 4 |
| Rifle (Karabiner) | Frame (Upper/Lower, Rail, Leuchtpunkt, Schaft), Barrel, gebogenes Magazine, Slide (Spannhebel), Trigger | Fire, Reload 2,4 s, Empty | 720 | 3 |
| Sniper (Repetierer) | Frame (Schaft, Wangenauflage, Zielfernrohr, Zweibein), Barrel, Magazine, Slide (Kammerstängel), Trigger | Fire mit Repetieren, Reload 3,0 s, Empty | 932 | 3 |
| Messer, Schläger, Granate, Molotow | Frame (die Granate zusätzlich Trigger = Löffel) | – | 152–376 | 2–3 |

- **Sockets:** `SOCKET_Grip` liegt im Ursprung am Griff. `SOCKET_Muzzle` sitzt vorn auf +Z, bei Wurfwaffen am Zünder bzw. Lappen. Feuerwaffen haben zusätzlich `SOCKET_Eject`.
- **Daten-Kopplung (neu):**
  - Die Länge des Reload-Clips wird beim Bau aus `combat.json` (`reload_time`) gelesen.
  - `test_combat_db.gd` prüft, dass Clip und Gameplay-Wert übereinstimmen (Toleranz 1 Frame). Dass die Prüfung greift, beweist eine eingebaute Gegenprobe: +0,5 s schlägt fehl.
- **Godot:**
  - `combat.json` verweist jetzt mit `scene` auf die Assets.
  - `CombatDB.weapon()` lädt die Szene. Ein schwerer Gegner mit `CombatDB.apply(npc, "enemy_heavy")` trägt damit das echte Gewehr-Modell.
- **Originale Entwürfe:** Kein echtes Herstellermodell wird nachgebaut.

## 2. Belege
- **Release-Gate:** `uwp export --profile gate` besteht 9 von 9 (Sockets, LODs, Kollision, Budgets).
- **Godot:** Import mit 0 Fehlern und 0 Warnungen.
- **`test_combat_db.gd`:** PASS. Darin geprüft:
  - Mündung vorn: 0,205 m bis 0,85 m.
  - Magazine-Knoten vorhanden.
  - Alle 15 Clips vorhanden.
  - Reload-Längen gleich `reload_time`.
- **uwp-Werkzeugtest [9]:** Gewehr und Revolver werden aus einem synthetischen Cache gebaut und bestehen das Gate. Das Manifest enthält Socket und Reload-Clip.
- **Bild:** `Docs/Reports/renders_weapons/weapons_fwdplus_side_midday.jpg` (Seitenprofil, Forward Plus).
  - Die erste Aufnahme hatte die Waffen halb im Boden versenkt, weil ihr Ursprung am Griff liegt. Die Aufnahme setzt Objekte jetzt auf den Boden.
  - Die Silhouetten sind klar lesbar.

## 3. Ehrlich offen
- **Die Pistole bleibt im Spiel beim PT-Stand-in.** Ihr `.glb` hat `Magazine` nicht als direktes Kind, und `test_weapon.gd` erwartet genau das. Die Umstellung kommt mit P7 (Waffenwechsel); dann wird der Knotenvertrag rekursiv.
- **Fehlen noch:**
  - Ego-Detail auf Hero-Niveau: Gravuren, Abnutzung, gebackene Normalen.
  - Mündungsfeuer und Hülsen je Klasse (P6 FX).
  - Jasons Halte- und Nachladeposen je Waffe (P6, E-3).
- **Status:** Blockout+. **Keine Waffe ist PRODUCTION-READY.**
