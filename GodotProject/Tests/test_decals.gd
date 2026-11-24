extends SceneTree
## T-DECAL-01 - decal library + the M01 decal layer.
##   * every Scenes/Decals/DC_*.tscn is a Decal with an albedo map, a real footprint and a shallow
##     projection (ground <= 0.15 m, wall <= 0.35 m: passers-by must not get painted)
##   * the manifest lists exactly the built decals; graffiti / manhole / crack / oil / drain exist
##   * M01 instances the generated layer (>= 100 decals) and EVERY decal touches what it decorates:
##     a ray along its projection axis (-Y) hits a surface within its half depth
## Negative control: UW_DECAL_SABOTAGE=1 lifts every decal 0.5 m before the contact check -> FAIL.

const LEVEL := "res://Scenes/Levels/LA_CallowayAve.tscn"
var failures: PackedStringArray = []

func check(cond: bool, msg: String) -> void:
	print("[GPTEST][PASS] " if cond else "[GPTEST][FAIL] ", msg)
	if not cond:
		failures.append(msg)

func _initialize() -> void:
	_run()

func _run() -> void:
	print("[GPTEST] == decals (T-DECAL-01)")
	var ids: Array = []
	for f in DirAccess.open("res://Scenes/Decals").get_files():
		if f.ends_with(".tscn"):
			ids.append(f.get_basename())
	check(ids.size() >= 12, "%d decal scenes built (>= 12)" % ids.size())
	var bad := []
	for id in ids:
		var d := (load("res://Scenes/Decals/%s.tscn" % id) as PackedScene).instantiate() as Decal
		var kind := String(d.get_meta("uw_kind", "")) if d != null else ""
		var ok := d != null and d.texture_albedo != null and d.size.x > 0.2 and d.size.z > 0.2
		ok = ok and ((kind == "ground" and d.size.y <= 0.15) or (kind == "wall" and d.size.y <= 0.35))
		if not ok:
			bad.append(id)
		if d != null:
			d.free()
	check(bad.is_empty(), "every decal scene: albedo, footprint, shallow projection %s" % str(bad))
	var man = JSON.parse_string(FileAccess.get_file_as_string(ProjectSettings.globalize_path("res://").path_join("../Assets/Decals/decals.manifest.json").simplify_path()))
	var listed := []
	for e in (man as Dictionary).get("decals", []):
		listed.append(String(e["id"]))
	listed.sort()
	ids.sort()
	check(listed == ids, "manifest lists exactly the built decals (%d)" % listed.size())
	for need in ["Graffiti", "Manhole", "Crack", "OilStain", "Drain", "TireMarks"]:
		check(ids.any(func(i): return String(i).contains(need)), "library has a %s decal" % need)
	await _level()
	if failures.is_empty():
		print("[GPTEST] RESULT: PASS")
		quit(0)
	else:
		print("[GPTEST] RESULT: FAIL (%d)" % failures.size())
		quit(1)

func _level() -> void:
	var sabotage := OS.is_debug_build() and OS.get_environment("UW_DECAL_SABOTAGE") == "1"
	var level := (load(LEVEL) as PackedScene).instantiate() as Node3D
	root.add_child(level)
	for i in 3:
		await physics_frame
	var layer := level.get_node_or_null("Decals")
	check(layer != null and layer.scene_file_path.ends_with("LA_CallowayAve_Decals.tscn"), "M01 instances the generated decal layer")
	if layer == null:
		return
	var decals := layer.find_children("*", "Decal", true, false)
	check(decals.size() >= 100, "M01 carries %d decals (>= 100)" % decals.size())
	var space := level.get_world_3d().direct_space_state
	var floating := []
	var walls := 0
	for n in decals:
		var d := n as Decal
		var axis := -d.global_basis.y.normalized()
		var p := d.global_position + (Vector3.UP * 0.5 if sabotage else Vector3.ZERO)
		var q := PhysicsRayQueryParameters3D.create(p - axis * 0.05, p + axis * (d.size.y * 0.5 + 0.05))
		if space.intersect_ray(q).is_empty():
			floating.append(String(d.name))
		if absf(axis.y) < 0.3:
			walls += 1
	check(floating.is_empty(), "every decal touches its surface (%d floating: %s)" % [floating.size(), str(floating.slice(0, 5))])
	check(walls >= 6, "graffiti / grime on the walls (%d)" % walls)
	level.queue_free()
	await physics_frame
