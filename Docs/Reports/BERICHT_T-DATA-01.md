# Bericht T-DATA-01 – P1: Kampf-Datenbank, Schutzsystem, Content-Katalog

**Datum:** 2026-11-23 · **Autor:** Claude Code · **Status:** READY FOR REVIEW · **TD:** TD-025 (PROPOSED)

## 1. Ergebnis
Alles, was im Kampf zählt, steht jetzt in **einer** Datei. Alles, was gebaut werden muss, steht in **einer** zweiten Datei. Beide werden im Merge-Gate gegeneinander und gegen die Festplatte geprüft.

| Baustein | Datei | Inhalt |
|---|---|---|
| Kampf-Datenbank | `GodotProject/Data/Content/combat.json` | 10 Waffen, 3 Schutzteile, 8 Archetypen, 7 Fraktionen, Balance-Bänder |
| Loader | `GodotProject/Scripts/game/combat_db.gd` (`CombatDB`) | baut `WeaponData`, `AIProfile`, Rüstung; `CombatDB.apply(npc, "enemy_heavy")` |
| Schutzsystem | `Scripts/combat/damage_receiver.gd` (Assets: `SM_Prop_Vest_Light`, `SM_Prop_Vest_Heavy`, `SM_Prop_Helmet_Tactical`) | Weste und Helm je Trefferzone, Durchschlag, Verschleiß, Reset |
| Content-Katalog | `Config/Content/catalog.json` | 101 Assets (17 gebaut/WIP, 84 geplant) mit Meilenstein, Generator, Quelle, Export |
| Werkzeug | `Tools/uwp catalog check\|status\|plan\|build` | Querprüfung, Statusbericht, offene Arbeit, Batch-Bau (reines Python, ohne Blender-Start) |
| Plan | `Docs/PRODUCTION_PLAN.md` | 10 Meilensteine P1–P10 bis zum fertigen Spiel, Content-first |

## 2. Gegner-Logik (festgelegt)
| Archetyp | HP | Schutz | Waffe | Zielfehler | Pistolen-Körpertreffer bis Tod (gemessen) | Band |
|---|---|---|---|---|---|---|
| Zivilist | 60 | – | – | – | 3 | 2–3 |
| Gegner leicht | 80 | – | Pistole | 5,0° | 4 | 3–4 |
| Gegner mittel | 100 | leichte Weste | SMG | 4,0° | 6 | 5–7 |
| Gegner schwer | 150 | schwere Weste + Helm | Gewehr | 3,0° | 11 | 9–14 |
| Boss | 650 | schwere Weste + Helm | Gewehr, Revolver (Phase: Granaten) | 2,5° | 31 | 30–45 |

- **Boss-Phasen:** bei 66 % Granatenhagel, bei 33 % Verstärkung rufen.
- **Weitere Archetypen:** Polizei (100), FBI taktisch (130), Verbündete (150).
- **Fraktionen** mit Kadern je Stufe: Los Cuervos, La Hermandad del Sur, Kings of Flatbush, Polizei, FBI, Zivilisten, Jasons Crew.
- **Gemessen, nicht geschätzt:** Die Trefferzahlen kommen aus einer Simulation mit dem echten `DamageReceiver`, Rüstung eingeschlossen.

**Waffen** (Schaden je Treffer, Durchschlag):
- Pistole 25 (0,10)
- Revolver 45 (0,30)
- SMG 16 (800 Schuss/min)
- Schrotflinte 12 × 8 Schrot
- Gewehr 32 (0,40)
- Scharfschützengewehr 110 (0,70)
- Messer 40
- Baseballschläger 35
- Granate 150 (0,50, Radius 6 m)
- Molotow 60 (Radius 4 m) + Brand 15/s

Die ausgelieferte `WPN_Pistol_01.tres` stimmt mit der Datenbank überein (Test).

## 3. Belege
- `GodotProject/Tests/test_combat_db.gd`: **33 PASS**.
  - Prüft alle Referenzen, die Stufenordnung und die Balance-Bänder.
  - Rüstung: nur abgedeckte Zone, Durchschlag, Verschleiß, Reset.
  - `apply()` an einem echten Gunman: 150 HP, 2 Schutzteile, Gewehr. Ein 25er-Treffer kostet ihn 12,6 HP.
- **Negativkontrolle:** `UW_COMBAT_SABOTAGE=1` schaltet die Rüstung ab. Ergebnis: **8 FAIL**.
- **uwp-Katalogtests:** 13 PASS.
  - Der echte Katalog besteht.
  - Ein sabotierter Katalog fällt durch, mit allen 5 erwarteten Fehlern: fehlende Waffe, fehlendes Fraktionsmodell, doppelte ID, behauptete Datei fehlt, PRODUCTION-READY ohne Review.
  - Eine untergeschobene, nicht katalogisierte `.glb` wird erkannt.
- `Tests/run_all.sh` auf frischem Worktree: siehe PR.

## 4. Ehrlich: was das NICHT ist
- **Keine neuen Modelle.** P1 legt fest, *was* gebaut wird und *wie* es kämpft. Gebaut wird in P2–P6.
- **Katalogwarnungen** (`uwp catalog check`) zeigen die offene Arbeit:
  - 6 Generatoren fehlen noch: `build-props`, `build-buildings`, `build-trims`, `build-decals`, `build-terrain`, `build-fx` (P2/P3/P6).
  - 29 Specs fehlen noch (P4/P5).
- **Gegner-Verhalten:** Archetypen nutzen die vorhandene KI (Deckung, Salven, Reaktionszeit). Das Boss-Phasen-Verhalten (Granaten, Verstärkung) ist als Daten festgelegt, aber noch **nicht als Code umgesetzt**. Das gehört zu P7.
- **Balance:** M01 nutzt die Archetypen noch nicht. Seine Gegner behalten die getesteten M01-Werte (B-008). Die Umstellung kommt mit P8, damit das Playthrough-Gate nicht ungeprüft kippt.

## 5. Nächste Schritte
- **P2 Werkzeuge:** `build-props` (Straßenmöbel und Gegenstände aus dem Katalog), Trim-Sheets, Decals, Gebäude-Generator.
- Danach **P3 bis P5:** Massenproduktion über `uwp catalog build --milestone Pn --profile gate`.
