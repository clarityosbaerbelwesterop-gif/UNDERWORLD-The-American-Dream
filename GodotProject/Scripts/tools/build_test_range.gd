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
#   AI arena (T-AI-01), z = +20..+40: CoverWall_A (-5, z 24), CoverWall_B (5, z 24), CoverWall_C (0, z 30),
#              1.25 m high; CoverPoints on their +Z side (+ decoy CP_A_Front on the wrong side);
#   PT_NavRegion  NavigationRegion3D baked here from every _box (group "navigation_geometry").
# Second output: Scenes/Test/PT_AITestRange.tscn = this range + 3 PT gunmen + 3 PT civilians on routes.
extends SceneTree

const OUT := "res://Scenes/Test/PT_PlayerTestRange.tscn"
const OUT_AI := "res://Scenes/Test/PT_AITestRange.tscn"
const NAV_GROUP := "navigation_geometry"

var _root: Node3D
var _mat_cache := {}

var _done := false

## Built on the first frame (not in _initialize): navmesh parsing needs the SceneTree running.
func _process(_d: float) -> bool:
	if not _done:
		_done = true
		_build()
	return false

func _build() -> void:
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

	# AI arena (T-AI-01): low cover walls + cover points.
	var cover_col := Color(0.45, 0.5, 0.42)
	_box("CoverWall_A", Vector3(3, 1.25, 0.4), Vector3(-5, 0.625, 24), Vector3.ZERO, cover_col)
	_box("CoverWall_B", Vector3(3, 1.25, 0.4), Vector3(5, 0.625, 24), Vector3.ZERO, cover_col)
	_box("CoverWall_C", Vector3(3, 1.25, 0.4), Vector3(0, 0.625, 30), Vector3.ZERO, cover_col)
	var covers := Node3D.new()
	covers.name = "CoverPoints"
	_add(covers)
	for c in [["CP_A1", Vector3(-5.8, 0, 24.75)], ["CP_A2", Vector3(-4.2, 0, 24.75)], ["CP_B1", Vector3(4.2, 0, 24.75)],
			["CP_B2", Vector3(5.8, 0, 24.75)], ["CP_C1", Vector3(-0.8, 0, 30.75)], ["CP_C2", Vector3(0.8, 0, 30.75)],
			["CP_A_Front", Vector3(-5, 0, 23.25)]]:
		var cp := Marker3D.new()
		cp.set_script(load("res://Scripts/ai/cover_point.gd"))
		cp.name = c[0]
		cp.position = c[1]
		covers.add_child(cp)
		cp.owner = _root

	var err := _bake_navmesh()

	var player: Node3D = (load("res://Scenes/Player/Player.tscn") as PackedScene).instantiate(PackedScene.GEN_EDIT_STATE_INSTANCE)
	player.name = "Player"
	_add(player)

	if err == OK:
		var packed := PackedScene.new()
		err = packed.pack(_root)
		if err == OK:
			err = ResourceSaver.save(packed, OUT)
	print("[TESTRANGE] saved %s err=%d" % [OUT, err])
	_root.free()
	if err == OK:
		err = _build_ai_range()
	quit(0 if err == OK else 1)

## Bakes the navmesh from the static boxes (static colliders, works headless) into PT_NavRegion.
func _bake_navmesh() -> int:
	var region := NavigationRegion3D.new()
	region.name = "PT_NavRegion"
	var nm := NavigationMesh.new()
	nm.geometry_parsed_geometry_type = NavigationMesh.PARSED_GEOMETRY_STATIC_COLLIDERS
	nm.geometry_source_geometry_mode = NavigationMesh.SOURCE_GEOMETRY_GROUPS_WITH_CHILDREN
	nm.geometry_source_group_name = NAV_GROUP
	nm.cell_size = 0.25
	nm.cell_height = 0.25
	nm.agent_radius = 0.5  # multiples of cell_size / cell_height (no precision warnings)
	nm.agent_height = 2.0
	nm.agent_max_climb = 0.25
	nm.agent_max_slope = 30.0
	region.navigation_mesh = nm
	_add(region)
	get_root().add_child(_root)  # global transforms for parsing
	var src := NavigationMeshSourceGeometryData3D.new()
	NavigationServer3D.parse_source_geometry_data(nm, src, _root)
	NavigationServer3D.bake_from_source_geometry_data(nm, src)
	get_root().remove_child(_root)
	print("[TESTRANGE] navmesh polygons=%d vertices=%d" % [nm.get_polygon_count(), nm.get_vertices().size()])
	return OK if nm.get_polygon_count() > 0 else FAILED

## PT_AITestRange: instance of the range + AI actors (kept out of PT_PlayerTestRange so player /
## weapon tests are not disturbed by NPCs hearing their shots).
func _build_ai_range() -> int:
	var root := Node3D.new()
	root.name = "PT_AITestRange"
	var range_scene := ResourceLoader.load(OUT, "", ResourceLoader.CACHE_MODE_REPLACE) as PackedScene
	var rng_inst := range_scene.instantiate(PackedScene.GEN_EDIT_STATE_INSTANCE)
	rng_inst.name = "Range"
	root.add_child(rng_inst)
	rng_inst.owner = root
	var ai := Node3D.new()
	ai.name = "AI"
	root.add_child(ai)
	ai.owner = root
	var routes := Node3D.new()
	routes.name = "Routes"
	ai.add_child(routes)
	routes.owner = root
	for r in [["Route_A", [Vector3(-30, 0, 16), Vector3(-30, 0, 30), Vector3(-18, 0, 30), Vector3(-18, 0, 16)]],
			["Route_B", [Vector3(16, 0, 16), Vector3(28, 0, 16), Vector3(28, 0, 30), Vector3(16, 0, 30)]]]:
		var route := Node3D.new()
		route.set_script(load("res://Scripts/ai/npc_route.gd"))
		route.name = r[0]
		routes.add_child(route)
		route.owner = root
		var i := 0
		for p in r[1]:
			var m := Marker3D.new()
			m.name = "P%d" % i
			m.position = p
			route.add_child(m)
			m.owner = root
			i += 1
	var gunman := load("res://Scenes/NPC/PT_NPC_Gunman.tscn") as PackedScene
	for g in [["Gunman_1", Vector3(-3, 0, 36)], ["Gunman_2", Vector3(3, 0, 36)], ["Gunman_3", Vector3(0, 0, 37.5)]]:
		var n := gunman.instantiate(PackedScene.GEN_EDIT_STATE_INSTANCE) as Node3D
		n.name = g[0]
		n.position = g[1]
		n.rotation.y = PI  # face -Z (towards the range)
		ai.add_child(n)
		n.owner = root
	var civ := load("res://Scenes/NPC/PT_NPC_Civilian.tscn") as PackedScene
	for c in [["Civilian_1", Vector3(-30, 0, 16), "../Routes/Route_A", 1], ["Civilian_2", Vector3(-18, 0, 30), "../Routes/Route_A", 3],
			["Civilian_3", Vector3(16, 0, 16), "../Routes/Route_B", 1]]:
		var n := civ.instantiate(PackedScene.GEN_EDIT_STATE_INSTANCE) as Node3D
		n.name = c[0]
		n.position = c[1]
		n.set("route_path", NodePath(c[2]))
		n.set("route_start_index", c[3])
		ai.add_child(n)
		n.owner = root
	var packed := PackedScene.new()
	var err := packed.pack(root)
	if err == OK:
		err = ResourceSaver.save(packed, OUT_AI)
	print("[TESTRANGE] saved %s err=%d" % [OUT_AI, err])
	root.free()
	return err

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
	body.add_to_group(NAV_GROUP, true)
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
