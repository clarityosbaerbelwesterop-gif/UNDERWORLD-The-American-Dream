extends SceneTree
## T-NY-01 - a New York look-dev street assembled at runtime from the chapter-2 building set: bank,
## three brownstones, tenement, corner bodega along one block, kit sidewalk + road, NY graffiti and
## puddle decals, shot under ny_overcast (dry) and ny_night (wet). Look only (lavapipe, no GPU).
##   UW_CAPTURE_DIR=/abs/dir Tools/godot_phase8_capture.sh --renderer fwdplus --res 960x540 \
##       --script res://Tests/tools/capture_ny_street.gd
const NY := "res://Assets/Environment/NY/%s/%s.glb"
const KIT := "res://Assets/Environment/LA/%s/%s.glb"
# id, width along the street (m), depth (m) - fronts face +Z (Blender -Y), centred on the origin
const ROW := [["SM_NY_Bldg_Bank", 20.0, 18.0], ["SM_NY_Bldg_Brownstone", 6.5, 13.0], ["SM_NY_Bldg_Brownstone", 6.5, 13.0],
	["SM_NY_Bldg_Brownstone", 6.5, 13.0], ["SM_NY_Bldg_Tenement", 15.0, 18.0], ["SM_NY_Bldg_Bodega", 9.0, 9.0]]

func _initialize() -> void:
	_run()

func frames(n: int) -> void:
	for i in n:
		await process_frame

func _inst(path: String, parent: Node3D, pos: Vector3, yaw := 0.0) -> Node3D:
	var n := (load(path) as PackedScene).instantiate() as Node3D
	parent.add_child(n)
	n.position = pos
	n.rotation.y = yaw
	MaterialPass.apply(n)
	return n

func _decal(id: String, parent: Node3D, pos: Vector3, basis: Basis) -> void:
	var d := (load("res://Scenes/Decals/%s.tscn" % id) as PackedScene).instantiate() as Decal
	parent.add_child(d)
	d.transform = Transform3D(basis, pos)

func _run() -> void:
	var out := OS.get_environment("UW_CAPTURE_DIR")
	if out == "":
		out = "/tmp/uw_ny_street"
	DirAccess.make_dir_recursive_absolute(out)
	var world := Node3D.new()
	root.add_child(world)
	var x := -38.0
	for b in ROW:
		var w: float = b[1]
		_inst(NY % [b[0], b[0]], world, Vector3(x + w * 0.5, 0, -float(b[2]) * 0.5))
		x += w
	# sidewalk (4 m, z 0..4) and road (10 m, z 4..14) along X, kit pieces turned 90 deg
	for i in 8:
		_inst(KIT % ["SM_LA_Sidewalk_Curb", "SM_LA_Sidewalk_Curb"], world, Vector3(-35.0 + i * 10.0, 0, 2.0), PI / 2.0)
	for i in 6:
		_inst(KIT % ["SM_LA_Road_Straight", "SM_LA_Road_Straight"], world, Vector3(-35.0 + i * 14.0, 0, 9.0), PI / 2.0)
	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(200, 200)
	ground.mesh = pm
	ground.position.y = -0.03
	world.add_child(ground)
	# tags on the tenement + bodega walls, puddles in the gutter
	var wall := Basis(Vector3.RIGHT, Vector3.BACK, Vector3.DOWN)   # Y = +Z (out of the wall)
	_decal("DC_NY_Graffiti_01", world, Vector3(6.0, 1.6, 0.05), Basis(Vector3.RIGHT, Vector3.BACK, Vector3.DOWN))
	_decal("DC_LA_Grime_01", world, Vector3(-8.0, 9.0, 0.05), wall)
	for px in [-30.0, -12.0, 4.0, 18.0]:
		_decal("DC_LA_Puddle_01", world, Vector3(px, 0.05, 5.2), Basis.IDENTITY)
	_decal("DC_LA_Manhole_01", world, Vector3(-5.0, 0.05, 9.5), Basis.IDENTITY)
	# practicals: kit street lamps along the kerb + warm shop-window spill (night carries on these)
	for i in 6:
		var lx := -34.0 + i * 13.0
		_inst(KIT % ["SM_LA_Streetlight", "SM_LA_Streetlight"], world, Vector3(lx, 0, 3.5), PI)
		var lamp := OmniLight3D.new()
		lamp.light_color = Color(1.0, 0.82, 0.58)
		lamp.light_energy = 5.0
		lamp.omni_range = 16.0
		lamp.shadow_enabled = true
		lamp.position = Vector3(lx, 6.4, 4.4)
		world.add_child(lamp)
	for sx in [-0.5, 3.5, 8.6, 14.0, 21.0]:
		var shop := OmniLight3D.new()
		shop.light_color = Color(1.0, 0.86, 0.62)
		shop.light_energy = 2.2
		shop.omni_range = 6.0
		shop.position = Vector3(sx, 1.8, 0.8)
		world.add_child(shop)
	var light_root := Node3D.new()
	world.add_child(light_root)
	var we := WorldEnvironment.new()
	world.add_child(we)
	var cam := Camera3D.new()
	world.add_child(cam)
	cam.fov = 58
	cam.make_current()
	await frames(5)
	for shot in [["ny_overcast", 0.25, Vector3(-14, 1.7, 12.5), Vector3(4, 4.0, 0)], ["ny_night", 1.0, Vector3(-14, 1.7, 12.5), Vector3(4, 4.0, 0)],
			["ny_overcast", 0.25, Vector3(-34, 2.2, 9.0), Vector3(-28, 5.0, -2)]]:
		for c in light_root.get_children():
			c.free()
		light_root.add_child(SunPreset.make_sun(shot[0]))
		we.environment = SunPreset.graded_environment(shot[0])
		MaterialPass.set_wetness(world, float(shot[1]))
		cam.global_position = shot[2]
		cam.look_at(shot[3], Vector3.UP)
		await frames(30)
		var name := "%s_%s" % [shot[0], "bank" if (shot[2] as Vector3).x < -30 else "block"]
		root.get_viewport().get_texture().get_image().save_png(out.path_join(name + ".png"))
		print("[NY_SHOT] ", name)
	quit(0)
