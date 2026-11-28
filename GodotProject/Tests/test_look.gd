extends SceneTree
## T-LOOK-02 - graphics pass contract.
##   * every look preset (LA golden hour / midday / night, NY night / overcast) tonemaps with AgX,
##     runs SSAO + SSIL and has its chapter grade (3D LUT) once graded
##   * the grades do what they claim: LA warms a mid grey (R > B), NY cools it (B > R) and keeps
##     a saturated neon red saturated
##   * the material pass reaches the game: car paint gets a clear coat (in vehicle.gd), Jason's
##     skin subsurface scattering + rim, his clothes a sheen (in CharacterVisual.set_model)
##   * rain: set_wetness(1) makes asphalt darker and glossier, set_wetness(0) restores it
## Negative control: UW_LOOK_SABOTAGE=1 disables the material pass -> paint / skin / wet checks FAIL.

var failures: PackedStringArray = []

func check(cond: bool, msg: String) -> void:
	print("[GPTEST][PASS] " if cond else "[GPTEST][FAIL] ", msg)
	if not cond:
		failures.append(msg)

func _initialize() -> void:
	_run()

func frames(n: int) -> void:
	for i in n:
		await physics_frame

func _run() -> void:
	print("[GPTEST] == graphics pass (T-LOOK-02)")
	for preset in SunPreset.ENVIRONMENTS:
		var env := SunPreset.graded_environment(preset)
		check(env.tonemap_mode == Environment.TONE_MAPPER_AGX, "%s: AgX tonemapping" % preset)
		check(env.ssao_enabled and env.ssil_enabled, "%s: SSAO + SSIL on" % preset)
		check(env.adjustment_enabled and env.adjustment_color_correction is Texture3D, "%s: chapter grade (%s LUT)" % [preset, SunPreset.CHAPTER.get(preset, "?")])
		check(not (SunPreset.environment(preset).adjustment_color_correction is Texture3D), "%s: the .tres on disk stays LUT-free" % preset)
	var grey := Color(0.46, 0.46, 0.46)
	var la := Grading.grade("LA", grey)
	var ny := Grading.grade("NY", grey)
	check(la.r > la.b + 0.01, "LA grade warms mid grey (%.3f, %.3f, %.3f)" % [la.r, la.g, la.b])
	check(ny.b > ny.r + 0.01, "NY grade cools mid grey (%.3f, %.3f, %.3f)" % [ny.r, ny.g, ny.b])
	var neon := Grading.grade("NY", Color(0.95, 0.10, 0.25))
	check(neon.r - maxf(neon.g, neon.b) > 0.6, "NY keeps neon red saturated (%.2f, %.2f, %.2f)" % [neon.r, neon.g, neon.b])
	check(Grading.grade("??", grey) == grey and Grading.lut("??") == null, "unknown chapter = no grade")
	var lut := Grading.lut("LA")
	check(lut.get_width() == Grading.SIZE and lut.get_depth() == Grading.SIZE, "LA LUT is %d^3" % Grading.SIZE)
	await _materials()
	if failures.is_empty():
		print("[GPTEST] RESULT: PASS")
		quit(0)
	else:
		print("[GPTEST] RESULT: FAIL (%d)" % failures.size())
		quit(1)

func _find_mat(n: Node, suffix: String) -> StandardMaterial3D:
	for c in n.find_children("*", "MeshInstance3D", true, false):
		var mi := c as MeshInstance3D
		if mi.mesh == null:
			continue
		for si in mi.mesh.get_surface_count():
			var m := mi.get_active_material(si) as StandardMaterial3D
			if m != null and m.resource_name.ends_with(suffix):
				return m
	return null

func _materials() -> void:
	var world := Node3D.new()
	root.add_child(world)
	var car := (load("res://Scenes/Vehicles/VH_Sedan_01.tscn") as PackedScene).instantiate() as Vehicle
	car.control_override = true
	world.add_child(car)
	await frames(2)
	var paint := _find_mat(car, "_Paint")
	check(paint != null and paint.clearcoat_enabled and paint.clearcoat >= 0.8, "sedan paint has a clear coat (vehicle.gd -> MaterialPass)")
	var player := (load("res://Scenes/Player/Player.tscn") as PackedScene).instantiate()
	world.add_child(player)
	await frames(2)
	var skin := _find_mat(player, "_Skin")
	check(skin != null and skin.subsurf_scatter_enabled and skin.subsurf_scatter_skin_mode and skin.rim_enabled, "Jason's skin: SSS (skin mode) + rim")
	var jacket := _find_mat(player, "_Jacket")
	check(jacket != null and jacket.rim_enabled, "Jason's jacket: fabric sheen")
	# rain on a street tile
	const ROAD := "res://Assets/Environment/LA/SM_LA_Road_Straight/SM_LA_Road_Straight.glb"
	var tile: Node3D = (load(ROAD) as PackedScene).instantiate() if ResourceLoader.exists(ROAD) else null
	check(tile != null, "a road tile to rain on")
	if tile != null:
		world.add_child(tile)
		var mats := MaterialPass._materials(tile).filter(func(m): return String(m.resource_name).to_lower().contains("asphalt"))
		check(not mats.is_empty(), "road tile has an asphalt material (%d)" % mats.size())
		if not mats.is_empty():
			var a := mats[0] as StandardMaterial3D
			var r0 := a.roughness
			var c0 := a.albedo_color
			var wet := MaterialPass.set_wetness(tile, 1.0)
			check(wet > 0 and a.roughness < r0 - 0.2 and a.albedo_color.v < c0.v - 0.1, "wet asphalt: roughness %.2f -> %.2f, value %.2f -> %.2f" % [r0, a.roughness, c0.v, a.albedo_color.v])
			MaterialPass.set_wetness(tile, 0.0)
			check(is_equal_approx(a.roughness, r0) and a.albedo_color.is_equal_approx(c0), "dry again after set_wetness(0)")
	world.queue_free()
	await frames(2)
