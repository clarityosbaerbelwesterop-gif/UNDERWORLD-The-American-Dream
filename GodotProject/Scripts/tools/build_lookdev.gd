extends SceneTree
## T-LOOK-01 - generates Scenes/LookDev/LookDev_Calibration.tscn, the look-dev / calibration scene
## every material and lighting preset is judged in (QUALITY_GATE Phase 8, master prompt §5.4).
##
##   godot --headless --path GodotProject --script res://Scripts/tools/build_lookdev.gd
##
## Contents (film/VFX look-dev convention, adapted to the game):
##   * 18 % grey card, 90 % white card, 4 % black card  - exposure / tonemap reference
##   * chrome ball (metal 1, rough 0) + 18 % grey ball   - reflection / key-fill reference
##   * 24-patch colour chart (published sRGB values of the classic chart) - white balance, saturation
##   * hero line-up: SK_Jason, VH_Sedan_01, WPN_Pistol_01, LA shop facade (real assets, LFS)
##   * WorldEnvironment = the SAME preset resource the level uses (Assets/Environments/ENV_LA_*.tres)
##     so a look approved here is the look in game (no second copy of the numbers).
## Shots: Tests/tools/capture_lookdev.gd (Forward Plus via Tools/godot_phase8_capture.sh).

const OUT := "res://Scenes/LookDev/LookDev_Calibration.tscn"
const ENV_DIR := "res://Assets/Environments/"
const SUN := preload("res://Scripts/game/sun_preset.gd")

## X-Rite/Macbeth ColorChecker Classic, sRGB 8-bit reference values (24 patches, row-major).
const CHART := [
	[115, 82, 68], [194, 150, 130], [98, 122, 157], [87, 108, 67], [133, 128, 177], [103, 189, 170],
	[214, 126, 44], [80, 91, 166], [193, 90, 99], [94, 60, 108], [157, 188, 64], [224, 163, 46],
	[56, 61, 150], [70, 148, 73], [175, 54, 60], [231, 199, 31], [187, 86, 149], [8, 133, 161],
	[243, 243, 242], [200, 200, 200], [160, 160, 160], [122, 122, 121], [85, 85, 85], [52, 52, 52],
]

var root3d: Node3D

func _initialize() -> void:
	root3d = Node3D.new()
	root3d.name = "LookDev_Calibration"
	root.add_child(root3d)
	_build()
	_own(root3d, root3d)
	var ps := PackedScene.new()
	var err := ps.pack(root3d)
	if err == OK:
		err = ResourceSaver.save(ps, OUT)
	print("[LOOKDEV] saved %s err=%d" % [OUT, err])
	quit(0 if err == OK else 1)

func _own(n: Node, owner_node: Node) -> void:
	for c in n.get_children():
		if c.owner == null:
			c.owner = owner_node
		# stop at instanced sub-scenes: they stay instances
		if c.scene_file_path == "":
			_own(c, owner_node)

func _mat(albedo: Color, rough := 0.9, metal := 0.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = albedo
	m.roughness = rough
	m.metallic = metal
	return m

## Linear reflectance -> sRGB-encoded albedo (StandardMaterial3D albedo is sRGB).
static func refl(v: float) -> Color:
	return Color(v, v, v).linear_to_srgb()

func _box(name: String, size: Vector3, pos: Vector3, m: Material, parent: Node) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.name = name
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = m
	parent.add_child(mi)
	mi.position = pos
	return mi

func _sphere(name: String, r: float, pos: Vector3, m: Material, parent: Node) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.name = name
	var sm := SphereMesh.new()
	sm.radius = r
	sm.height = r * 2.0
	sm.radial_segments = 64
	sm.rings = 32
	mi.mesh = sm
	mi.material_override = m
	parent.add_child(mi)
	mi.position = pos
	return mi

func _build() -> void:
	# Floor: 18 % grey, large enough to receive the sun shadow of every object.
	_box("Floor_Grey18", Vector3(40, 0.1, 40), Vector3(0, -0.05, 0), _mat(refl(0.18)), root3d)

	# Calibration rig. Its local +Z is turned toward the sun by the capture script (per preset),
	# so the cards are always front-lit and the camera has the sun at its back - the classic
	# look-dev read. Card_Grey18_Shade sits under an opaque slab: it reads the sky/fill only.
	var refs := Node3D.new()
	refs.name = "References"
	root3d.add_child(refs)
	refs.position = Vector3(-3.0, 0.0, 0.0)
	_box("Card_Grey18", Vector3(0.6, 0.8, 0.02), Vector3(0.0, 0.9, 0), _mat(refl(0.18)), refs)
	_box("Card_White90", Vector3(0.3, 0.8, 0.02), Vector3(0.55, 0.9, 0), _mat(refl(0.90)), refs)
	_box("Card_Black04", Vector3(0.3, 0.8, 0.02), Vector3(-0.55, 0.9, 0), _mat(refl(0.04)), refs)
	# Fill card: turned 90 deg, so the sun only grazes it (N.L = 0) and it reads sky + bounce.
	var shade := _box("Card_Grey18_Shade", Vector3(0.6, 0.8, 0.02), Vector3(1.6, 0.9, 0.3), _mat(refl(0.18)), refs)
	shade.rotation.y = -PI * 0.5
	_sphere("Ball_Chrome", 0.22, Vector3(-0.3, 0.22, 0.8), _mat(Color(0.95, 0.95, 0.95), 0.02, 1.0), refs)
	_sphere("Ball_Grey18", 0.22, Vector3(0.3, 0.22, 0.8), _mat(refl(0.18), 0.95), refs)
	_cam("Cam_Calibration", Vector3(0.4, 1.3, 4.2), Vector3(0.4, 0.75, 0.0), 40.0, refs)

	var chart := Node3D.new()
	chart.name = "ColorChart"
	refs.add_child(chart)
	chart.position = Vector3(-1.6, 0.6, 0.0)
	for i in CHART.size():
		var c: Array = CHART[i]
		var col := Color8(int(c[0]), int(c[1]), int(c[2]))
		var x := float(i % 6) * 0.13 - 0.33
		var y := 0.5 - float(i / 6) * 0.13
		_box("Patch_%02d" % (i + 1), Vector3(0.12, 0.12, 0.01), Vector3(x, y, 0), _mat(col, 0.95), chart)
	_box("ChartBacking", Vector3(0.84, 0.58, 0.008), Vector3(0, 0.305, -0.01), _mat(refl(0.03)), chart)

	# Hero line-up (real LFS assets; missing ones are reported, never faked).
	var heroes := Node3D.new()
	heroes.name = "Heroes"
	root3d.add_child(heroes)
	var lineup := [
		["SK_Jason", "res://Assets/Characters/SK_Jason/SK_Jason.glb", Vector3(0.0, 0, 0), 0.0],
		["WPN_Pistol_01", "res://Assets/Weapons/WPN_Pistol_01/WPN_Pistol_01.glb", Vector3(1.0, 1.0, 0.3), -PI * 0.5],
		["VH_Sedan_01", "res://Assets/Vehicles/VH_Sedan_01/VH_Sedan_01.glb", Vector3(4.2, 0, -0.5), PI * 0.25],
		["SM_LA_Bldg_ShopStucco", "res://Assets/Environment/LA/SM_LA_Bldg_ShopStucco/SM_LA_Bldg_ShopStucco.glb", Vector3(1.5, 0, -9.0), 0.0],
	]
	for h in lineup:
		var ps = load(h[1]) if ResourceLoader.exists(h[1]) else null
		if ps is PackedScene:
			var inst := (ps as PackedScene).instantiate() as Node3D
			inst.name = h[0]
			heroes.add_child(inst)
			inst.position = h[2]
			inst.rotation.y = h[3]
		else:
			push_warning("LookDev: hero asset missing: %s" % h[1])
	# The pistol is tiny: put it on a 1 m plinth next to Jason.
	_box("Plinth", Vector3(0.4, 0.95, 0.4), Vector3(1.0, 0.475, 0.3), _mat(refl(0.18)), heroes)

	# Light + environment: the shipping presets (TD-023). Golden hour is the default look.
	var light := Node3D.new()
	light.name = "Lighting"
	root3d.add_child(light)
	var sun := SUN.make_sun("golden_hour")
	light.add_child(sun)
	var we := WorldEnvironment.new()
	we.name = "WorldEnvironment"
	we.environment = load(ENV_DIR + "ENV_LA_GoldenHour.tres")
	light.add_child(we)

	# Cameras the capture script cycles through (names are the shot list).
	var cams := Node3D.new()
	cams.name = "Cameras"
	root3d.add_child(cams)
	_cam("Cam_Jason_Full", Vector3(0.4, 1.1, 3.4), Vector3(0.0, 0.95, 0.0), 35.0, cams)
	_cam("Cam_Jason_Face", Vector3(0.15, 1.68, 0.85), Vector3(0.0, 1.62, 0.0), 30.0, cams)
	_cam("Cam_Pistol", Vector3(1.0, 1.25, 0.95), Vector3(1.0, 1.0, 0.3), 30.0, cams)
	_cam("Cam_Sedan", Vector3(8.5, 1.6, 4.5), Vector3(4.2, 0.7, -0.5), 40.0, cams)
	_cam("Cam_Overview", Vector3(-2.0, 4.5, 11.0), Vector3(1.0, 1.0, -2.0), 50.0, cams)

func _cam(name: String, pos: Vector3, at: Vector3, fov: float, parent: Node) -> void:
	var c := Camera3D.new()
	c.name = name
	c.fov = fov
	parent.add_child(c)
	c.position = pos
	# local look-at (works for cameras parented to a rotated rig too)
	c.basis = Basis.looking_at(at - pos, Vector3.UP)
