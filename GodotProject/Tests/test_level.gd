# UNDERWORLD - level readability / hygiene tests (T-LVL-01a).
#   godot --headless --fixed-fps 60 --path GodotProject --script res://Tests/test_level.gd
# The level is generated, so everything here is measured on the SHIPPED scene + its data:
#   * no engine fallback names ("@Node3D@12"), no unused ext_resource
#   * road / kerb / sidewalk have distinguishable materials
#   * the navmesh is baked in the file and covers ROAD and SIDEWALK
#   * the player can walk the whole street with movement input (no teleporting)
# Negative control UW_LEVEL_SABOTAGE=1 makes the contrast audit lie -> FAIL.
extends SceneTree

const LEVEL := "res://Scenes/Levels/LA_CallowayAve.tscn"
const LEVEL_TSCN := "res://Scenes/Levels/LA_CallowayAve.tscn"
const HZ := 60.0
const WATCHDOG := 60 * 400

var failures: Array[String] = []
var _frames := 0
var _done := false

func check(cond: bool, msg: String) -> void:
	if cond:
		print("[GPTEST][PASS] ", msg)
	else:
		print("[GPTEST][FAIL] ", msg)
		failures.append(msg)

func approx(a: float, b: float, tol: float) -> bool:
	return absf(a - b) <= tol

func _initialize() -> void:
	_run_all()

func _process(_d: float) -> bool:
	_frames += 1
	if _frames > WATCHDOG and not _done:
		print("[GPTEST][FAIL] watchdog")
		quit(1)
	return false

func frames(n: int) -> void:
	for i in n:
		await physics_frame

func _run_all() -> void:
	await frames(2)
	test_hygiene()
	await test_materials()
	await test_navmesh()
	await test_walk_the_street()
	await test_npc_climbs_kerb()
	await frames(5)
	_done = true
	if failures.is_empty():
		print("[GPTEST] RESULT: PASS")
		quit(0)
	else:
		print("[GPTEST] RESULT: FAIL (%d)" % failures.size())
		for f in failures:
			print("[GPTEST]   - ", f)
		quit(1)

var level: Node

func load_level() -> void:
	level = (load(LEVEL) as PackedScene).instantiate()
	var map: RID = root.get_world_3d().navigation_map
	var iter0 := NavigationServer3D.map_get_iteration_id(map)
	root.add_child(level)
	await process_frame
	await frames(3)
	# Bot 1 review of PR #17: the navigation map syncs asynchronously (map iterations run on a
	# worker), so after 3 frames the baked region was sometimes not in the map yet and
	# map_get_path() returned 0 points (1 of 3 runs on a fresh worktree). Wait - bounded - until
	# the map has iterated with the region in it. This only waits; every check stays as strict.
	for i in 240:
		if NavigationServer3D.map_get_iteration_id(map) > iter0 and not NavigationServer3D.map_get_regions(map).is_empty():
			break
		await physics_frame
	await frames(2)

func unload() -> void:
	level.queue_free()
	await frames(3)

# --- 1. hygiene: names + resources ------------------------------------------------

func test_hygiene() -> void:
	print("[GPTEST] == level hygiene: speaking names, no dead resources")
	# Its own instance, freed immediately: a leaked level makes the engine shout at exit
	# ("RID allocations ... leaked"), and run_all.sh treats engine errors as a failure.
	var probe := (load(LEVEL) as PackedScene).instantiate()
	var auto_named := LevelAudit.auto_named(probe)
	probe.free()
	check(auto_named.is_empty(), "no engine fallback names in the level (%s)" % [auto_named.slice(0, 5)])
	var unused := LevelAudit.unused_ext(LEVEL_TSCN)
	check(unused.is_empty(), "no unused ext_resource in %s (%s)" % [LEVEL_TSCN.get_file(), unused])
	var text := FileAccess.get_file_as_string(LEVEL_TSCN)
	check(text.contains("Bldg_Shop_01") and text.contains("Garage_Wall_N"),
		"the buildings and the garage are actually IN the shipped scene")
	check(text.contains("NavRegion_Block"), "the navmesh region is in the shipped scene")
	# The painted surface copies are level-owned meshes. Their transform has to come from the kit
	# instance they were copied out of; a copy stored at the origin is invisible in-game while the
	# material check above stays green (that bug shipped once - see TD-018).
	var level2 := (load(LEVEL) as PackedScene).instantiate()
	var origin_copies := 0
	var copies := 0
	for n in level2.find_children("*_SM_*", "MeshInstance3D", true, false):
		copies += 1
		if (n as Node3D).position.length() < 0.5:
			origin_copies += 1
	var road0 := level2.find_child("Road_Straight_01_SM_LA_Road_Straight", true, false) as Node3D
	# Read the position BEFORE free(): a freed node still compares != null, and every read on it
	# returns a zero vector, so the check would silently test the origin.
	var road0_pos := road0.position if road0 != null else Vector3.ZERO
	# ... and compare before free(), too: a freed Object compares equal to null, so the
	# `road0 != null` half of the expression would flip to false after the free.
	var road_ok := road0 != null and road0_pos.distance_to(Vector3(-24, 0, -79)) < 0.6
	level2.free()
	check(copies > 50, "painted surface copies exist (%d)" % copies)
	check(origin_copies == 0, "no painted surface copy sits at the origin (%d of %d)" % [origin_copies, copies])
	check(road_ok, "the first road segment is where the layout says (-24, 0, -79), got %s" % [road0_pos])

# --- 2. materials -----------------------------------------------------------------

func test_materials() -> void:
	print("[GPTEST] == road, kerb and sidewalk are distinguishable")
	await load_level()
	var c := LevelAudit.contrast(level)
	check(c["found"]["road"] and c["found"]["sidewalk"] and c["found"]["kerb"],
		"found road (%.2f), sidewalk (%.2f) and kerb line (%.2f) albedo" % [c["road"], c["sidewalk"], c["kerb"]])
	# Luminance difference: 0 would mean "same grey", which is what the first capture showed.
	check(float(c["diff"]) >= 0.3, "road vs sidewalk luminance differs by %.2f (>= 0.30)" % c["diff"])
	check(float(c["kerb"]) > float(c["sidewalk"]), "the kerb line is brighter than the slab (%.2f > %.2f)" % [c["kerb"], c["sidewalk"]])
	check(float(c["road"]) < float(c["sidewalk"]), "asphalt is darker than concrete (%.2f < %.2f)" % [c["road"], c["sidewalk"]])
	await unload()

# --- 3. navmesh -------------------------------------------------------------------

func test_navmesh() -> void:
	print("[GPTEST] == navmesh baked in the file, covering road AND sidewalk")
	await load_level()
	var nav := level.get_node_or_null("NavRegion_Block") as NavigationRegion3D
	check(nav != null and nav.navigation_mesh != null, "NavRegion_Block with a NavigationMesh")
	if nav == null or nav.navigation_mesh == null:
		await unload()
		return
	check(nav.navigation_mesh.get_polygon_count() > 100,
		"the navmesh ships baked (%d polygons)" % nav.navigation_mesh.get_polygon_count())
	var map: RID = level.get_world_3d().navigation_map
	var probes := {
		"west road": Vector3(-24.0, 0.3, 40.0),
		"east road": Vector3(24.0, 0.3, -40.0),
		"west sidewalk": Vector3(-31.0, 0.3, 10.0),
		"east sidewalk": Vector3(31.0, 0.3, -10.0),
		"south segment": Vector3(0.0, 0.3, -86.0),
		"north segment": Vector3(0.0, 0.3, 86.0),
	}
	for k in probes:
		var p: Vector3 = probes[k]
		var closest := NavigationServer3D.map_get_closest_point(map, p)
		check(Vector2(closest.x - p.x, closest.z - p.z).length() < 1.5,
			"navmesh reaches the %s (%.2f m off)" % [k, Vector2(closest.x - p.x, closest.z - p.z).length()])
	# T-BUILD-02 (B-LVL-02/04): the garage must be walkable from the street through the roll-up
	# door, and every cover anchor of layout §5 must exist and stand ON the navmesh.
	var door_path := NavigationServer3D.map_get_path(map, Vector3(30.0, 0.3, 6.0), Vector3(38.5, 0.3, 6.0), true)
	var end_off := 99.0 if door_path.is_empty() else Vector2(door_path[-1].x - 38.5, door_path[-1].z - 6.0).length()
	var max_leg := 0.0
	for i in range(1, door_path.size()):
		max_leg = maxf(max_leg, door_path[i].distance_to(door_path[i - 1]))
	check(end_off < 1.0 and door_path.size() >= 2,
		"navmesh path from the forecourt INTO the garage through the door (ends %.2f m from the goal)" % end_off)
	var covers := 0
	for n in level.find_children("Cover_*", "", true, false):
		if not (n is CoverPoint):
			continue
		covers += 1
		var c := (n as Node3D).global_position
		var cp := NavigationServer3D.map_get_closest_point(map, c)
		var off := Vector2(cp.x - c.x, cp.z - c.z).length()
		check(off < 0.35, "%s stands on the navmesh (%.2f m off)" % [n.name, off])
	check(covers == 6, "6 cover anchors from layout §5 (found %d)" % covers)
	await unload()

# --- 4. walk the street with real input -------------------------------------------

func test_walk_the_street() -> void:
	print("[GPTEST] == walk the whole street with movement input (no teleporting)")
	await load_level()
	var p := level.get_node("Player") as PlayerController
	var map: RID = level.get_world_3d().navigation_map
	# Start in the MIDDLE of the block, not at the very end: the sidewalk modules stop at +/-85
	# and the navmesh trims agent radius there, so a walk that starts 5 m in is the honest test.
	var start := Vector3(-31.0, 0.3, 60.0)      # west sidewalk
	var goal := Vector3(-31.0, 0.3, -60.0)      # other end of the same block
	var path := NavigationServer3D.map_get_path(map, start, goal, true)
	check(path.size() >= 2, "navmesh finds a walking route along the block (%d points)" % path.size())
	p.global_position = start
	p.velocity = Vector3.ZERO
	await frames(2)
	var reached := 0
	var stuck := 0
	for wp in path:
		if (wp - p.global_position).length() < 0.6:
			reached += 1
			continue
		stuck = 0
		for t in int(HZ * 8.0):
			var to := wp - p.global_position
			to.y = 0.0
			if to.length() < 0.6:
				reached += 1
				stuck = 0
				break
			# Face the waypoint the way a player would (camera yaw), then push forward.
			# Camera yaw convention (CameraRig): forward = (-sin yaw, 0, -cos yaw), so the yaw that
			# makes the player walk towards `to` is atan2(-to.x, -to.z). (The first drive test in
			# T-MIS-01b got this backwards and sent the car in circles.)
			p.camera_rig.set_yaw(atan2(-to.x, -to.z))
			Input.action_press("move_forward")
			if to.length() > 3.0:
				Input.action_press("sprint")
			else:
				Input.action_release("sprint")
			await frames(1)
			stuck += 1
		if stuck >= int(HZ * 8.0):
			break
	Input.action_release("move_forward")
	Input.action_release("sprint")
	var end_dist := Vector2(p.global_position.x - goal.x, p.global_position.z - goal.z).length()
	check(reached >= path.size() - 2, "walked %d/%d waypoints of the block" % [reached, path.size()])
	check(end_dist < 1.5, "ended at the other end of the block (%.2f m from the goal)" % end_dist)
	check(p.global_position.y > -1.0 and p.global_position.y < 1.0,
		"stayed on the street surface (y = %.2f m, never fell through)" % p.global_position.y)
	await unload()


# --- 5. NPCs climb kerbs (B-AI-06, T-BUILD-02) --------------------------------------

## The 16 cm kerb was a wall for every NPC (no step logic): the M01 ambush wave piled up at the
## east kerb. A gunman ordered from the east road onto the east sidewalk must get up there.
func test_npc_climbs_kerb() -> void:
	print("[GPTEST] == NPC walks from the road onto the sidewalk (16 cm kerb)")
	await load_level()
	var g := (load("res://Scenes/NPC/PT_NPC_Gunman.tscn") as PackedScene).instantiate() as NPCController
	g.name = "KerbTestGunman"
	level.add_child(g)
	g.global_position = Vector3(26.5, 0.1, -30.0)
	for i in 10:
		await physics_frame
	var goal := Vector3(31.0, 0.2, -30.0)
	g._move_to(goal, 2.0)
	var t := 0
	while t < 60 * 6 and g.global_position.x < 30.0:
		g._move_to(goal, 2.0)
		await physics_frame
		t += 1
	check(g.global_position.x > 29.6 and g.global_position.y > 0.12,
		"gunman stepped up the kerb onto the sidewalk (pos %s after %.1f s)" % [g.global_position, t / 60.0])
	g.queue_free()
	await unload()
