# UNDERWORLD - game entry point (Bot 1 review of PR #17).
#
# The project's main scene used to be the pipeline smoke scene (PT crate), and nothing ever
# called MissionManager.start() outside the tests - so the exported Linux build booted into a
# test crate and M01 could not be played. This node is the shipping entry: it instances the
# level, waits for the scene tree to settle and starts the mission through the same public API
# the tests use. Tests keep loading the level directly and start the mission themselves.
class_name GameBoot
extends Node

@export var level_scene: PackedScene = preload("res://Scenes/Levels/LA_CallowayAve.tscn")
## Frames to wait before starting, so physics bodies, the HUD binding and the AI are ready.
@export var start_delay_frames := 3

var level: Node
var mission: MissionManager

static func sabotage() -> bool:
	# Negative control for Tests/test_boot.gd, never active in a release export.
	return OS.is_debug_build() and OS.get_environment("UW_BOOT_SABOTAGE").strip_edges() == "1"

func _ready() -> void:
	print("UNDERWORLD: GameBoot -> M01 Dead Drop")
	if level_scene == null:
		push_error("GameBoot: no level_scene")
		return
	level = level_scene.instantiate()
	add_child(level)
	mission = level.get_node_or_null("MissionManager") as MissionManager
	if mission == null:
		push_error("GameBoot: level has no MissionManager")
		return
	for i in start_delay_frames:
		await get_tree().physics_frame
	if sabotage():
		return
	if not mission.start():
		push_error("GameBoot: MissionManager.start() failed")
