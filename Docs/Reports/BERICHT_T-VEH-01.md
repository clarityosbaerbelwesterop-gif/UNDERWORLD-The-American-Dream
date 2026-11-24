# Bericht T-VEH-01 – P5: Fahrzeug-Profile und 5 neue Autos

**Datum:** 2026-11-24 · **Autor:** Claude Code · **Status:** READY FOR REVIEW · **TD:** TD-029 (PROPOSED)

## 1. Ergebnis
`Tools/uwp build-vehicles` (`vehicles/profiles.py`) verallgemeinert den Limousinen-Generator zu **Karosserie-Profilen**. Ein Profil besteht aus:
- Maßen und Querschnitten entlang der Länge
- Glashaus
- Türen
- Extras
- Livery

Alle Fahrzeuge folgen dem Vertrag von `vehicle.gd`: Wheel_*, Türen mit Scharnier-Ursprung, UCX-Hülle, Sitz-, Ausstiegs- und Licht-Sockets sowie `uw_wheel_radius_m`.

| Fahrzeug | Merkmale | Dreiecke | Mat. | Maße B × H × L (m) |
|---|---|---|---|---|
| VH_Police_01 | Schwarz-Weiß (Türen weiß), Lichtbalken rot/blau emissiv, Rammschutz, Livery „HOLLOW PD“ (erfunden) | 3.654 | 12 | 2,02 × 1,62 × 5,00 |
| VH_Taxi_NY_01 | Cab-Gelb, Dachschild „TAXI“, Livery „CITY CAB 4K17“ (erfunden) | 3.434 | 10 | 2,02 × 1,72 × 4,86 |
| VH_Muscle_01 | lange Haube, flaches Dach, 2 lange Türen, Lufthutze, Ducktail, Rallyestreifen | 3.302 | 9 | 2,06 × 1,32 × 4,79 |
| VH_Pickup_01 | Crew-Cab, 4 Türen, Ladefläche mit Abdeckung, Bordwand-Leisten, Heckklappe | 3.454 | 8 | 2,12 × 1,91 × 5,61 |
| VH_Van_01 (M01 Welle 2) | Kastenform, Glas nur vorn, Schiebetüren, Dachträger, Livery „HOLLOW FREIGHT“ | 3.542 | 9 | 2,16 × 2,42 × 5,33 |

## 2. Belege
- **Release-Gate:** `uwp export --profile gate` besteht **5 von 5**.
  - Die alte `VH_Sedan_01` fällt durch das Gate, weil ihre Kollisionshülle Restflächen enthält (NON_MANIFOLD). Im Profil-Generator ist das behoben: Es bleibt nur die Hülle.
  - Die Limousine selbst habe ich nicht angefasst, weil ihr Fahrverhalten in `test_vehicle.gd` kalibriert ist.
- **Neuer Test `test_vehicle_fleet.gd`:** Jedes Profil-Fahrzeug wird im **echten** `vehicle.gd` mit dem Tuning der Limousine montiert. Ergebnis für alle 5: **PASS**.
  - montiert ohne Fehler
  - 4 Räder sowie Sitz- und Ausstiegs-Sockets vorhanden
  - Vordertüren mit Scharnier
  - parkt auf dem Boden (±2 mm)
  - fährt geradeaus: 7,7 m/s nach 2 s
- **Negativkontrolle:** `UW_VEH_SABOTAGE=radius` (falscher Radradius) ergibt 10 FAIL.
- **`vehicle.gd`:** Hintere Türen sind jetzt optional, weil Coupés zwei Türen haben.
- **Bild:** `Docs/Reports/renders_vehicles/vehicles_fwdplus_golden_hour.jpg` (Forward Plus).

## 3. Ehrlich offen
- **Motorrad (VH_Motorcycle_01) und Kleinflugzeug (VH_Plane_Small_01)** brauchen eigene Topologie und Fahr- bzw. Flugmechanik (P7). Sie sind **nicht gebaut** und im Katalog weiter PLANNED.
- **Optik:** Die Ladefläche des Pickups liest sich aus der Nähe noch als geschlossene Form. Die Liveries sind einfache Schriftzüge.
- **Fahrwerte:** Alle Profile nutzen das Tuning der Limousine. Eigene `VehicleData` (Masse, Motor, Federung je Typ) kommen mit dem Verkehr in P7/P8.
- **Status:** Blockout+. Kein Fahrzeug ist PRODUCTION-READY.
