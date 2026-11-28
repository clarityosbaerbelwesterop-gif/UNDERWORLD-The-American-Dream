# UNDERWORLD - T-SAVE-01 helper: a SEPARATE Godot process that boots the shipping entry scene
# (Game_M01.tscn) exactly like the exported game and reports what GameBoot did with the save in
# UW_SAVE_DIR. Started by Tests/test_save.gd with OS.execute() = "quit the game, start it again".
# Output: one line  [SAVECHILD] resumed=<bool> index=<int> checkpoint=<int> carried=<bool> dead=<int>
extends SceneTree

func _initialize() -> void:
	_run()

func _run() -> void:
	var game: Node = (load(str(ProjectSettings.get_setting("application/run/main_scene"))) as PackedScene).instantiate()
	root.add_child(game)
	for i in 12:
		await physics_frame
	var boot := game as GameBoot
	var level := game.get_node("LA_CallowayAve")
	var mm := level.get_node("MissionManager") as MissionManager
	var pkg := level.get_node("Mission/Pickup_Package") as CarriedItem
	var dead := 0
	for n in get_nodes_in_group("mission_enemy"):
		if (n as MissionEnemy).is_dead():
			dead += 1
	print("[SAVECHILD] resumed=%s index=%d checkpoint=%d carried=%s dead=%d" % [
		str(boot.resumed), mm.current_index, mm.checkpoint_index, str(pkg.is_carried()), dead])
	game.queue_free()
	for i in 3:
		await physics_frame
	quit(0)
