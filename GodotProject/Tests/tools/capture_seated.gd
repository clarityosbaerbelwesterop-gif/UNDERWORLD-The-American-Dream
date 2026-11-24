extends SceneTree
## B-011 (T-ANIM-02) - Jason (driver) and Marco (passenger) SEATED in the M01 sedan, in engine
## (Forward Plus). Two shots: driver side through the window, three-quarter front through the
## windscreen. Look only.
##   UW_CAPTURE_DIR=/abs/dir Tools/godot_phase8_capture.sh --renderer fwdplus --res 960x540 \
##       --fixed-fps 30 --script res://Tests/tools/capture_seated.gd
const LEVEL := "res://Scenes/Levels/LA_CallowayAve.tscn"

func _initialize() -> void:
	_run()

func secs(s: float) -> void:
	var t := 0.0
	while t < s:
		await process_frame
		t += 1.0 / 30.0

func _run() -> void:
	var out := OS.get_environment("UW_CAPTURE_DIR")
	if out == "":
		out = "/tmp/uw_seated"
	DirAccess.make_dir_recursive_absolute(out)
	var level := (load(LEVEL) as PackedScene).instantiate()
	root.add_child(level)
	await secs(0.3)
	var mm := level.get_node("MissionManager") as MissionManager
	var player := level.get_node("Player") as PlayerController
	var car := level.get_node("VH_Sedan_01") as Vehicle
	mm.start()
	player.global_position = car.get_socket(&"SOCKET_Exit_Left").global_position
	await secs(0.1)
	car.enter(player)
	await secs(car.enter_duration() + 0.5)
	car.control_override = true
	var cam := Camera3D.new()
	level.add_child(cam)
	cam.fov = 45
	cam.make_current()
	var b := car.global_basis
	var c := car.global_position
	var shots := {
		"seated_driver_side": [c + b.x * 3.2 + b.z * 0.2 + Vector3.UP * 1.35, c + b.x * 0.2 + Vector3.UP * 1.0],
		"seated_front_3q": [c + b.z * 4.2 + b.x * 1.6 + Vector3.UP * 1.6, c + b.z * 0.2 + Vector3.UP * 1.0],
	}
	for id in shots:
		cam.global_position = shots[id][0]
		cam.look_at(shots[id][1], Vector3.UP)
		await secs(0.6)
		root.get_viewport().get_texture().get_image().save_png(out.path_join("%s.png" % id))
		print("[SEATED_SHOT] ", id)
	quit(0)
