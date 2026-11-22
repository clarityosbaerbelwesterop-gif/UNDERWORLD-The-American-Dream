# UNDERWORLD - mission definition as data (T-MIS-01).
#
# A mission is an ordered list of ObjectiveData. No mission logic lives in the scene:
# MissionManager walks the list and reacts to objective events. Every objective carries
# the exact node path of its trigger so the level designer and the mission author can
# work independently (contract: Docs/Missions/M01_DeadDrop.md "Implementation notes").
#
# Objective types (ObjectiveData.Kind):
#   NONE      - marker-only beat (intro call, outro card); completed via debug_complete_current()
#               or by MissionManager at start (auto_complete).
#   ENTER_AREA- the player (or the car carrying the package) enters `target_path`.
#   SURVIVE   - every node under `target_group` (default "mission_enemies") must be dead.
#   INTERACT  - player interacts with the node at `target_path` (Interactable press action).
#   DELIVER   - like ENTER_AREA but the requirement may be "carrying the package".
#   REACH     - player enters `target_path` on foot (alias kept explicit for readability).
class_name ObjectiveData
extends Resource

enum Kind { NONE, ENTER_AREA, SURVIVE, INTERACT, DELIVER, REACH }

@export var kind: Kind = Kind.NONE
## HUD objective text, e.g. "Get in the car." Empty = no HUD change (intro beats).
@export var text := ""
## Exact node path in the mission scene (Area3D / Interactable / Marker3D).
@export var target_path: NodePath
## Spawn group that must be dead for SURVIVE (nodes in this group are counted at start).
@export var target_group: StringName = &"mission_enemies"
## Completing this objective writes a checkpoint (restart point on fail).
@export var checkpoint := false
## Marker shown on the HUD/GPS (node path). Empty = use target_path.
@export var marker_path: NodePath
## Seconds the objective must stay satisfied (0 = immediate).
@export var hold_seconds := 0.0
## Auto-complete after this many seconds (0 = never); used for timed dialogue beats.
@export var auto_seconds := 0.0
## Requires the package to be carried (DELIVER / ENTER_AREA).
@export var requires_package := false
## Optional subtitle lines played when the objective starts: [seconds, speaker, text].
@export var subtitles: Array[Dictionary] = []
