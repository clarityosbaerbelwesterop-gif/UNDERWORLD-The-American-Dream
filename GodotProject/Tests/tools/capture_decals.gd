extends SceneTree
## T-DECAL-01 - in-engine shots of the M01 decal layer (Forward Plus, golden hour, graded):
## a lane with manhole/drain/oil, a sidewalk with cracks/litter, and the nearest graffiti wall.
##   UW_CAPTURE_DIR=/abs/dir Tools/godot_phase8_capture.sh --renderer fwdplus --res 960x540 \
##       --script res://Tests/tools/capture_decals.gd
const LEVEL := "res://Scenes/Levels/LA_CallowayAve.tscn"

func _initialize() -> void:
	_run()

func frames(n: int) -> void:
	for i in n:
		await process_frame

func _first(layer: Node, prefix: String) -> Decal:
	for c in layer.get_children():
		if String(c.name).begins_with(prefix):
			return c as Decal
	return null

func _run() -> void:
	var out := OS.get_environment("UW_CAPTURE_DIR")
	if out == "":
		out = "/tmp/uw_decals"
	DirAccess.make_dir_recursive_absolute(out)
	var level := (load(LEVEL) as PackedScene).instantiate() as Node3D
	root.add_child(level)
	await frames(5)
	var hud := level.get_node_or_null("HUD")
	if hud != null:
		hud.queue_free()
	var cam := Camera3D.new()
	level.add_child(cam)
	cam.fov = 50
	cam.make_current()
	var layer := level.get_node("Decals")
	for spec in [["DC_LA_Manhole_01", Vector3(3.0, 2.2, 4.0)], ["DC_LA_Drain_01", Vector3(2.0, 1.6, 3.0)],
			["DC_LA_Trash_01", Vector3(3.0, 2.4, 3.5)], ["DC_LA_Graffiti_01", Vector3(0, 0.3, 0)], ["DC_LA_Graffiti_02", Vector3(0, 0.3, 0)],
			["DC_LA_TireMarks_01", Vector3(6.0, 3.0, 6.0)], ["DC_LA_OilStain_02", Vector3(2.5, 2.0, 3.0)]]:
		var d := _first(layer, spec[0])
		if d == null:
			continue
		var p := d.global_position
		if String(spec[0]).contains("Graffiti"):
			var n := d.global_basis.y
			cam.global_position = p + n * 4.5 + Vector3(0, 0.2, 0)
		else:
			cam.global_position = p + spec[1]
		cam.look_at(p, Vector3.UP)
		await frames(20)
		root.get_viewport().get_texture().get_image().save_png(out.path_join("%s.png" % spec[0]))
		print("[DECAL_SHOT] ", spec[0])
	quit(0)
