# Review PR #17 (Auftrag 02) – Bot 1

**Datum:** 2026-11-23 (Europe/Berlin) · **Geprüft:** Merge `d3809d0` auf `main` · **Prüfer:** Bot 1 (Project Director)

## Kurzfassung
1. Die sechs Tasks aus Auftrag 02 sind **inhaltlich echt**. Auf einem frischen Worktree: `RUN_ALL: PASS`, **738 Checks**, genau wie berichtet.
2. **Kein Test wurde gelöscht oder gelockert.** Alle 12 Sabotage-Modi schlagen fehl, wie sie sollen.
3. Vier Defekte habe ich direkt behoben. Der wichtigste: **Der Linux-Build bootete in die Test-Kiste statt ins Spiel**, und außerhalb der Tests hat niemand die Mission gestartet.
4. Nach den Fixes sind es **749 Checks**. Der Export mit dem offiziellen Template bootet nachweislich in M01 mit HUD.
5. Die Optik ist überall **Blockout** und weit unter dem Quality Gate. Gespielt auf einer GPU hat das Spiel noch niemand.

## Testzahlen (frischer Worktree, `git lfs pull`)
| Suite | vor #17 | #17 | nach Fix |
|---|---:|---:|---:|
| smoke / uwp / import | 12 / 58 / 71 | 12 / 58 / 71 | 12 / 58 / 71 |
| AI | 80 | 102 | 102 |
| Boot | – | – | 7 |
| HUD | – | 40 | 40 |
| Level | – | 23 | 23 |
| Mission | 75 | 105 | 109 |
| Player | 137 | 171 | 171 |
| Vehicle / Weapon | 88 / 68 | 88 / 68 | 88 / 68 |
| **Summe** | **589** | **738** | **749** |

## Sabotage (jeder Modus einzeln, Exit 1 = gewollt)
| Modus | FAIL |
|---|---:|
| `UW_JASON_SABOTAGE=1` | 3 |
| `UW_ANIM_SABOTAGE=1` | 9 |
| `UW_VEHICLE_SABOTAGE=1` / `=2` | 9 / 22 |
| `UW_MISSION_SABOTAGE=1` / `=2` / `=3` | 5 / 2 / 2 |
| `UW_AI_SABOTAGE=incar` | 4 |
| `UW_HUD_SABOTAGE=1` | 3 |
| `UW_LEVEL_SABOTAGE=1` | 1 |
| `UW_BOOT_SABOTAGE=1` (neu) | 2 |
| `UW_BUILD_SABOTAGE=1` | Build-Exit 6 |

## Task für Task gegen die Akzeptanzkriterien (PROMPT_02)
| Task | Urteil |
|---|---|
| T-MIS-01b | Erfüllt: Marco-Sitz, Unverwundbarkeit, Wellen 3 → 2, inaktive Gegner vor dem Trigger, echte Fahrt. Defekt: Marco wurde stehend durchs Dach gezeichnet, behoben. Phase-8-Bilder vom Hinterhalt fehlten. |
| T-AI-03 | Erfüllt. TD-015 ist jetzt ACCEPTED (25 % Schaden bei Treffer durchs Fahrerfenster). |
| T-GP-04 | Erfüllt: Clips an Ereignissen, Reload synchron, 7 Knochen-Hitboxen, Headshot ×2. |
| T-UI-01 | Erfüllt: 40 Checks, Sabotage wirkt. |
| T-LVL-01a | Erfüllt (Blockout). Defekt: flaky Navmesh-Test, behoben. |
| T-BUILD-01 | Formal erfüllt (Exit 0, Smoke sauber). Defekt: Main-Scene war `Main.tscn` (PT-Kiste) und die Mission wurde nie gestartet, behoben (TD-020). |

**Merge-Hinweis:** Der Auftrag hatte `MERGE-FREIGABE: NEIN`. Claude Code hat nicht selbst gemergt.
Der Merge kam am 2026-11-23 um 14:07 Uhr (Berlin) über das Eigentümer-Konto.

## LFS
114 Dateien vor dem Review, 122 danach (8 neue PNGs), alle als LFS-Pointer. 0 Binärdateien als normaler Blob, `git lfs fsck --pointers` OK.

## Bilder (llvmpipe / gl_compatibility, **nicht** der Shipping-Renderer Forward Plus)
`Docs/Reports/renders_review_pr17/01…07` stammen aus `Tests/tools/capture_m01_review.gd`. `08_export_build_boot_llvmpipe.png` zeigt das exportierte Release-Binary unter Xvfb.
- Jason: Die Proportionen stimmen. Die Haare sehen aus wie ein Helm oder eine Mütze, die Haut wirkt wachsig, die Jacke ist eine verrauschte Textur, die Stiefel sind Klumpen.
- Limousine: Blockout, kein lesbares Glas, kein Innenraum. Marco ist im Auto jetzt unsichtbar, weil ein Sitz-Clip fehlt.
- Level: Die Straße ist lesbar, die Gehwege sind fast weiß, die Gebäude leere Boxen, die Garage ein Quader.
- HUD: lesbar.
- **Urteil: funktionaler Blockout. Nicht AAA, nicht vorzeigbar.**

## Große offene Punkte (nicht in diesem Review behoben)
- Die gesamte Kunst ist unter dem Gate. Die Pipeline muss neu aufgestellt werden (Master-Prompt §5).
- Kein GPU-Test: Forward-Plus-Look, FPS und Fahrgefühl sind unverifiziert.
- Es fehlen ein Sitz-Clip für Beifahrer und Fahrer, das optionale Verfolgerauto, Audio und Speichern/Laden.
- Die NPC-Gesichter sind zu ähnlich (Cartel_A hat Jasons Gesicht). Draft-PR #11 (Pistole) ist offen.
