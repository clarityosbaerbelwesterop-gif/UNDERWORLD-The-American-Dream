extends SceneTree
## Phase 8 review shots of M01 through the real entry scene (Bot 1 review of PR #17).
##
##   Tools/godot_phase8_capture.sh --script res://Tests/tools/capture_m01_review.gd
##   (env UW_CAPTURE_DIR=/abs/dir, default /tmp/uw_m01_capture)
##
## Renderer: gl_compatibility on Mesa llvmpipe (no GPU) - NOT the shipping Forward Plus look.
## Use the shots for framing, scale, silhouettes, clipping and readability, not for lighting.
## Needs a display (xvfb-run via the wrapper); under --headless the viewport texture is empty.

var out_dir := "/tmp/uw_m01_capture"
var game: Node
var level: Node
var cam: Camera3D

func _initialize() -> void:
	var d := OS.get_environment("UW_CAPTURE_DIR")
	if d != "":
		out_dir = d
	DirAccess.make_dir_recursive_absolute(out_dir)
	_run()

func frames(n: int) -> void:
	for i in n:
		await process_frame

func shot(name: String) -> void:
	await frames(8)
	var img := root.get_viewport().get_texture().get_image()
	var p := out_dir.path_join(name + ".png")
	img.save_png(p)
	print("[CAP] wrote ", p, " ", img.get_size())

func look(from: Vector3, at: Vector3) -> void:
	cam.global_position = from
	cam.look_at(at, Vector3.UP)
	cam.make_current()

func _run() -> void:
	var main := str(ProjectSettings.get_setting("application/run/main_scene"))
	game = (load(main) as PackedScene).instantiate()
	root.add_child(game)
	await frames(30)
	level = game.get_node("LA_CallowayAve")
	var player := level.get_node("Player") as Node3D
	var car := level.get_node("VH_Sedan_01") as Node3D
	var mm := level.get_node("MissionManager") as MissionManager
	print("[CAP] mission state=%d objective=%d" % [mm.state, mm.current_index])
	await shot("01_gameplay_camera_start")
	cam = Camera3D.new()
	cam.fov = 60.0
	level.add_child(cam)
	var c := car.global_position
	look(c + car.global_basis.x * 6.0 + Vector3(0, 2.2, 0) + car.global_basis.z * 3.0, c + Vector3(0, 0.8, 0))
	await shot("02_car_with_marco_seated")
	look(c - car.global_basis.x * 6.0 + Vector3(0, 1.6, 0) - car.global_basis.z * 2.0, c + Vector3(0, 0.8, 0))
	await shot("03_car_other_side")
	var p := player.global_position
	look(p + Vector3(1.2, 1.7, 2.4), p + Vector3(0, 1.5, 0))
	await shot("04_jason_closeup")
	var garage := level.get_node_or_null("Mission/Area_GarageInside") as Node3D
	if garage != null:
		var g := garage.global_position
		look(g + Vector3(10, 4, 10), g + Vector3(0, 1, 0))
		await shot("05_garage")
	look(Vector3(0, 70, 110), Vector3(0, 0, 0))
	await shot("06_overview")
	look(Vector3(-20, 1.7, 70), Vector3(-20, 1.5, 0))
	await shot("07_street_level")
	quit(0)
