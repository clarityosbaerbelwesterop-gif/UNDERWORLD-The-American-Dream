# UNDERWORLD - generates Scenes/Test/PT_PlayerTestRange.tscn (placeholder test map, PT_ = never ships).
# Run: godot --headless --path GodotProject --script res://Scripts/tools/build_test_range.gd
# Layout (metres, player spawns at the origin facing -Z = camera forward):
#   AimWall    front face at z = -30 (aim ray target straight ahead)
#   Ramp       x = 14, 20° slope rising towards -Z
#   CrouchTunnel x = -12, z = -7..-13, ceiling underside at 1.4 m (stand 1.8 / crouch 1.2)
#   Crates/Pillar  scattered blockers
#   Stairs     x = -22, 8 steps (rise 0.2 m, tread 0.3 m) from z = 0 rising towards -Z,
#              top landing 1.6 m high from z = -2.4 to -5.4 (T-GP-01c)
#   Ledge_050  x = -28, 0.5 m block (must NOT be stepped onto)
#   Step_030   x = -32, single 0.3 m step (must be stepped onto)
#   Shooting lane (T-GP-02): Target_10m (27, 0, -10), Target_35m (24, 0, -35), Backstop wall z=-38.5
extends SceneTree

const OUT := "res://Scenes/Test/PT_PlayerTestRange.tscn"

var _root: Node3D
var _mat_cache := {}

func _initialize() -> void:
	_root = Node3D.new()
	_root.name = "PT_PlayerTestRange"

	var env := WorldEnvironment.new()
	env.name = "WorldEnvironment"
	var e := Environment.new()
	e.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	sky.sky_material = ProceduralSkyMaterial.new()
	e.sky = sky
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.environment = e
	_add(env)

	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	sun.shadow_enabled = true
	sun.rotation_degrees = Vector3(-50, 30, 0)
	_add(sun)

	_box("Floor", Vector3(80, 1, 80), Vector3(0, -0.5, 0), Vector3.ZERO, Color(0.3, 0.3, 0.32))
	_box("AimWall", Vector3(12, 4, 1), Vector3(0, 2, -30.5), Vector3.ZERO, Color(0.6, 0.55, 0.5))
	_box("Crate_A", Vector3(1.5, 1.5, 1.5), Vector3(5, 0.75, -5), Vector3.ZERO, Color(0.55, 0.4, 0.25))
	_box("Crate_B", Vector3(1.5, 1.5, 1.5), Vector3(-5, 0.75, -8), Vector3(0, 30, 0), Color(0.55, 0.4, 0.25))
	_box("Pillar", Vector3(1, 3, 1), Vector3(6, 1.5, 4), Vector3.ZERO, Color(0.5, 0.5, 0.5))
	# Ramp: 10 m long, rotated +20° about X so it rises towards -Z; top surface meets the floor at z = -1.
	var ang := deg_to_rad(20.0)
	var half := 5.0
	var center := Vector3(14, half * sin(ang) - 0.25 * cos(ang), -1.0 - half * cos(ang) - 0.25 * sin(ang))
	_box("Ramp", Vector3(4, 0.5, 10), center, Vector3(20, 0, 0), Color(0.45, 0.45, 0.5))
	# Crouch tunnel: two side walls + a ceiling slab whose underside is at 1.4 m.
	_box("CrouchTunnel_Ceiling", Vector3(3, 0.3, 6), Vector3(-12, 1.55, -10), Vector3.ZERO, Color(0.35, 0.4, 0.45))
	_box("CrouchTunnel_WallL", Vector3(0.3, 1.4, 6), Vector3(-13.65, 0.7, -10), Vector3.ZERO, Color(0.35, 0.4, 0.45))
	_box("CrouchTunnel_WallR", Vector3(0.3, 1.4, 6), Vector3(-10.35, 0.7, -10), Vector3.ZERO, Color(0.35, 0.4, 0.45))

	# Stairs + ledges for step-up tests (T-GP-01c).
	var stair_col := Color(0.5, 0.45, 0.4)
	for i in 8:
		var h := 0.2 * (i + 1)
		_box("Stairs_Step_%d" % (i + 1), Vector3(2, h, 0.3), Vector3(-22, h * 0.5, -0.15 - 0.3 * i), Vector3.ZERO, stair_col)
	_box("Stairs_Landing", Vector3(2, 1.6, 3), Vector3(-22, 0.8, -3.9), Vector3.ZERO, stair_col)
	_box("Ledge_050", Vector3(2, 0.5, 2), Vector3(-28, 0.25, -3), Vector3.ZERO, Color(0.6, 0.3, 0.3))
	_box("Step_030", Vector3(2, 0.3, 2), Vector3(-32, 0.15, -3), Vector3.ZERO, Color(0.3, 0.6, 0.3))

	# Shooting lane (T-GP-02).
	var dummy := load("res://Scenes/Test/PT_TargetDummy.tscn") as PackedScene
	for t in [["Target_10m", Vector3(27, 0, -10)], ["Target_35m", Vector3(24, 0, -35)]]:
		var d: Node3D = dummy.instantiate(PackedScene.GEN_EDIT_STATE_INSTANCE)
		d.name = t[0]
		d.position = t[1]
		_add(d)
	_box("Backstop", Vector3(8, 4, 1), Vector3(25, 2, -38.5), Vector3.ZERO, Color(0.4, 0.42, 0.45))

	var player: Node3D = (load("res://Scenes/Player/Player.tscn") as PackedScene).instantiate(PackedScene.GEN_EDIT_STATE_INSTANCE)
	player.name = "Player"
	_add(player)

	var packed := PackedScene.new()
	var err := packed.pack(_root)
	if err == OK:
		err = ResourceSaver.save(packed, OUT)
	print("[TESTRANGE] saved %s err=%d" % [OUT, err])
	_root.free()
	quit(0 if err == OK else 1)

func _add(n: Node) -> void:
	_root.add_child(n)
	n.owner = _root

func _mat(c: Color) -> StandardMaterial3D:
	if not _mat_cache.has(c):
		var m := StandardMaterial3D.new()
		m.albedo_color = c
		m.roughness = 0.9
		_mat_cache[c] = m
	return _mat_cache[c]

func _box(n: String, size: Vector3, pos: Vector3, rot_deg: Vector3, color: Color) -> void:
	var body := StaticBody3D.new()
	body.name = n
	body.position = pos
	body.rotation_degrees = rot_deg
	_add(body)
	var mi := MeshInstance3D.new()
	mi.name = "Mesh"
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = _mat(color)
	body.add_child(mi)
	mi.owner = _root
	var cs := CollisionShape3D.new()
	cs.name = "Collision"
	var sh := BoxShape3D.new()
	sh.size = size
	cs.shape = sh
	body.add_child(cs)
	cs.owner = _root
