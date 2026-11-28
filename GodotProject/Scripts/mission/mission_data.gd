# UNDERWORLD - mission definition (T-MIS-01).
#
# One MissionData resource = one playable mission, authored in the Godot inspector or a
# .tres in Data/Missions/. M01 "Dead Drop" lives at Data/Missions/M01_DeadDrop.tres.
class_name MissionData
extends Resource

@export var id := "M01_DeadDrop"
@export var title := "Dead Drop"
@export_multiline var logline := ""
## Ordered objectives (see ObjectiveData).
@export var objectives: Array[ObjectiveData] = []
## Cash paid on MISSION PASSED (M01: 2500).
@export var reward_cash := 0
## Seconds before the fail overlay auto-restarts (0 = wait for input).
@export var fail_restart_seconds := 3.0
## Groups/NPC names that must never be killable (Marco in M01).
@export var invulnerable_tags: PackedStringArray = PackedStringArray()
