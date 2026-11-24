extends SceneTree
## T-LOOK-02 - the M01 street (Calloway Ave) under every look preset, through the real level: the
## LA chapter grade by day/night and the NY chapter grade (night = wet asphalt via
## MaterialPass.set_wetness). Same camera for all, one PNG per preset. Look only (lavapipe).
##   UW_CAPTURE_DIR=/abs/dir Tools/godot_phase8_capture.sh --renderer fwdplus --res 960x540 \
##       --script res://Tests/tools/capture_look_presets.gd
const LEVEL := "res://Scenes/Levels/LA_CallowayAve.tscn"
const SHOTS := [["golden_hour", 0.0], ["midday", 0.0], ["night", 0.0], ["ny_overcast", 0.35], ["ny_night", 1.0]]
## UW_LOOK_ONLY=ny_night renders one preset

func _initialize() -> void:
	_run()

func frames(n: int) -> void:
	for i in n:
		await process_frame

func _run() -> void:
	var out := OS.get_environment("UW_CAPTURE_DIR")
	if out == "":
		out = "/tmp/uw_look_presets"
	DirAccess.make_dir_recursive_absolute(out)
	var level := (load(LEVEL) as PackedScene).instantiate() as Node3D
	root.add_child(level)
	await frames(5)
	var cam := Camera3D.new()
	level.add_child(cam)
	cam.fov = 55
	cam.make_current()
	cam.global_position = Vector3(-20, 1.7, 70)
	cam.look_at(Vector3(-20, 1.5, 0), Vector3.UP)
	var lighting := level.get_node("Lighting")
	var we := lighting.get_node("WorldEnvironment") as WorldEnvironment
	var only := OS.get_environment("UW_LOOK_ONLY")
	for s in SHOTS:
		var preset: String = s[0]
		if only != "" and only != preset:
			continue
		var old := lighting.get_node_or_null("Sun")
		if old != null:
			old.free()
		var sun := SunPreset.make_sun(preset)
		lighting.add_child(sun)
		we.environment = SunPreset.graded_environment(preset)
		MaterialPass.set_wetness(level, float(s[1]))
		await frames(24)
		root.get_viewport().get_texture().get_image().save_png(out.path_join("%s.png" % preset))
		print("[LOOK_SHOT] ", preset)
	quit(0)
