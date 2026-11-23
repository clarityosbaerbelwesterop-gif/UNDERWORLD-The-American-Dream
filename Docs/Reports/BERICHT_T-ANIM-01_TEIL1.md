# Bericht T-ANIM-01 (Teil 1) – geteilte Animationsbibliothek repariert, NPC-Clips, Integritätsprüfung

**Datum:** 2026-11-23 · **Autor:** Claude Code · **Status: TEILWEISE**. Der Rest von T-ANIM-01 hängt an der Entscheidung zur Animationsquelle (E-3: Mocap/CC0/Mixamo).

## 1. Kurzfassung
- **Gefundener Datenfehler (B-ASSET-01):** Die gemeinsame Bibliothek `Assets/Characters/Shared/A_Humanoid_Locomotion.glb` war in git ein **208-Byte-Platzhalter** („UNDERWORLD dev placeholder (LFS unavailable)“) mit 0 Clips.
  - Ursache: Eine Sandbox ohne LFS hatte ihn erzeugt (`build_asset_cache.gd`), und der LFS-Reparatur-Commit `e383080` hat ihn als „echtes“ Objekt übernommen.
  - Das echte Objekt (885 KB, 21 Clips, Blender-Export) lag noch auf dem LFS-Server und ist aus `f79f136` **wiederhergestellt**.
- **NPCs leihen sich fehlende Clips** zur Laufzeit aus dieser Bibliothek (`CharacterVisual._borrow_shared_clip`). Dabei wird der Spurpfad auf das eigene Skelett umadressiert; alle Figuren teilen den 53-Bone-Vertrag.
  - NPC-Modelle hatten nur 16 von 21 Clips eingebacken. Es fehlten Carry_*, Death, Car_Enter/Exit.
  - Die Warnungen „missing clips for carry_idle, carry_walk“ sind weg.
- **Integritätsprüfung im Gate:** `run_all.sh` schlägt fehl, sobald ein committeter `.glb` einen `uw_placeholder` enthält.

## 2. Tests (jeder vorher rot gesehen)
| Test | ohne Fix | mit Fix |
|---|---|---|
| test_mission: Bibliothek hat ≥ 21 Clips (kein Platzhalter) | FAIL (0 Clips, nach Re-Import) | PASS (21) |
| test_mission: NPC hat jeden gemappten Clip | FAIL (carry_idle, carry_walk, death, car_enter, car_exit) | PASS |
| test_mission: geliehener Carry_Walk bewegt das NPC-Skelett | FAIL | PASS (Fuß bewegt sich 0,59 m) |
| `UW_ANIM_SABOTAGE=noshared` (Ausleihen aus) | – | FAIL (2) |
| `run_all.sh` Platzhalter-Scan | meldet den Platzhalter | sauber |

## 3. Ausdrücklich NICHT erreicht (ehrlich)
- **Sitzpose für Marco:** Ich habe die letzte Frame-Pose von `Car_Enter_L` als Sitzpose getestet. Gemessen lag der Kopf 1,79 m über dem Fahrzeugursprung, also **durch das Dach** (Wagenhöhe 1,45 m), die Hüfte 1,13 m statt etwa 0,5 m. Das ist keine Sitzpose. **Zurückgenommen:** Marco bleibt sitzend unsichtbar, wie in PR #18. Nötig ist ein echter Sitz-Clip (`A_Humanoid_Sit_Passenger/Driver`), in Blender erstellt.
- Fußrutschen: Die Clips rutschen weiter bis 4,86 cm. Die Pipeline prüft das jetzt (`ANIM_FOOT_SLIDE`, T-PIPE-06). Repariert werden die Clips mit Mocap und Foot-IK.
- Foot-IK, Hand-IK, Root Motion: noch nicht begonnen.

## 4. Nächste Schritte (brauchen die Entscheidung E-3)
1. Animationsquelle wählen: eigenes Mocap (Kosten), CMU/CC0-BVH (Lizenz prüfen) oder Mixamo nur per TD.
2. Sitz-Clips für Fahrer und Beifahrer erstellen → Marco sichtbar im Auto.
3. Foot-IK (SkeletonModifier3D) für Bordsteine und Treppen, Ziel Fehler < 2 cm.
