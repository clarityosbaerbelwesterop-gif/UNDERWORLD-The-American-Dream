extends SceneTree
## T-BUILD-02 - records the input-only M01 autopilot run through the SHIPPING entry scene with the
## gameplay cameras (player rig / car chase camera). Use Godot Movie Maker for a deterministic video:
##
##   Tools/godot_phase8_capture.sh --renderer fwdplus --script res://Tests/tools/record_m01_playthrough.gd \
##       --movie /abs/out.avi --fps 30 --frames 9000
##
## Same rules as Tests/test_playthrough.gd: seed 2 replay, QA cheat "player invulnerable" stated on
## screen-independent stdout; every gunman is still shot through aim + fire inputs.

const AUTOPILOT := preload("res://Tests/tools/m01_autopilot.gd")

func _initialize() -> void:
	if OS.get_environment("UW_RNG_SEED") == "":
		OS.set_environment("UW_RNG_SEED", "2")
	_run()

func _run() -> void:
	var main := str(ProjectSettings.get_setting("application/run/main_scene"))
	var game: Node = (load(main) as PackedScene).instantiate()
	root.add_child(game)
	for i in 10:
		await physics_frame
	var level := game.get_node("LA_CallowayAve")
	(level.get_node("Player/Health") as DamageReceiver).invulnerable = true
	print("[REC] QA cheat: player invulnerable; seed %s; renderer %s" % [OS.get_environment("UW_RNG_SEED"), OS.get_environment("UW_CAPTURE_RENDERER")])
	var pilot := AUTOPILOT.new()
	pilot.name = "Autopilot"
	pilot.setup(level)
	level.add_child(pilot)
	while not pilot.done:
		await physics_frame
	print("[REC] ", pilot.summary())
	for i in 90:          # hold the MISSION PASSED card for 3 s
		await process_frame
	quit(0 if pilot.result_ok else 1)
