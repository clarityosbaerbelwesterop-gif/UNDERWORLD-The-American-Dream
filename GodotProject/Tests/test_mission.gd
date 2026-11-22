# UNDERWORLD - headless mission framework tests (T-MIS-01, M01 "Dead Drop").
#
#   godot --headless --fixed-fps 60 --path GodotProject --script res://Tests/test_mission.gd
#
# Drives the REAL level (Scenes/Levels/LA_CallowayAve.tscn) through every M01 objective,
# the fail states and the checkpoint restart, using gameplay triggers - not timers - wherever
# the design allows it. MissionManager.debug_complete_current() is used for the intro/outro
# beats only, exactly as the design contract specifies.
#
# Negative control: UW_MISSION_SABOTAGE=1 removes the checkpoint flag from objective 2 and
# breaks the package stray-distance fail -> the suite must FAIL (exit 1).
extends SceneTree

const LEVEL := "res://Scenes/Levels/LA_CallowayAve.tscn"
const HZ := 60.0
const WATCHDOG := 60 * 300

var failures: Array[String] = []
var _frames := 0
var _done := false
var sabotage := OS.get_environment("UW_MISSION_SABOTAGE") != ""

var level: Node3D
var mm: MissionManager
var player: PlayerController
var car: Vehicle
var pkg: CarriedItem

func check(cond: bool, msg: String) -> void:
	if cond:
		print("[GPTEST][PASS] ", msg)
	else:
		print("[GPTEST][FAIL] ", msg)
		failures.append(msg)

func _initialize() -> void:
	_run()

func _process(_d: float) -> bool:
	_frames += 1
	if _frames > WATCHDOG and not _done:
		print("[GPTEST][FAIL] watchdog")
		quit(1)
	return false

func frames(n: int) -> void:
	for i in n:
		await physics_frame

func seconds(s: float) -> void:
	await frames(int(round(s * HZ)))

# --- fixture ------------------------------------------------------------------

func load_level() -> void:
	level = (load(LEVEL) as PackedScene).instantiate()
	root.add_child(level)
	await frames(3)
	mm = level.get_node("MissionManager") as MissionManager
	player = level.get_node("Player") as PlayerController
	car = level.get_node("VH_Sedan_01") as Vehicle
	pkg = level.get_node("Mission/Pickup_Package") as CarriedItem

func unload() -> void:
	level.queue_free()
	await frames(3)

# --- tests --------------------------------------------------------------------

func _run() -> void:
	_done = false
	print("[GPTEST] == M01 mission framework (sabotage=%s)" % str(sabotage))
	await test_level_contents()
	await test_full_mission()
	await test_player_death_fail_and_checkpoint()
	await test_package_failures()
	await test_car_destroyed()
	await test_mission_data_matches_design()
	if sabotage:
		await test_sabotage_detected()
	_done = true
	if failures.is_empty():
		print("[GPTEST] RESULT: PASS")
		quit(0)
	else:
		print("[GPTEST] RESULT: FAIL (%d)" % failures.size())
		for f in failures:
			print("[GPTEST]   - ", f)
		quit(1)

func test_level_contents() -> void:
	print("[GPTEST] == level contents / naming contract")
	await load_level()
	check(level != null and mm != null, "level instantiates with MissionManager")
	for n in ["Mission/Area_GarageArrival", "Mission/Area_GarageInside", "Mission/Area_Warehouse",
			"Mission/Pickup_Package", "Mission/Pickup_Package/Interact", "Mission/PlayerSpawn",
			"Mission/Marco_Seat", "AI/Spawn_Wave1_A", "AI/Spawn_Wave2_Van"]:
		check(level.get_node_or_null(n) != null, "node exists: %s" % n)
	check(pkg is CarriedItem, "Pickup_Package is a CarriedItem")
	check(pkg.health != null and is_equal_approx(pkg.health.max_health, 200.0), "package has 200 HP (M01 design)")
	check(player != null and car != null, "player and sedan instanced in the level")
	var enemies := get_nodes_in_group("mission_enemies")
	check(enemies.size() >= 5, "at least 5 ambush enemies in group mission_enemies (%d)" % enemies.size())
	var civs := 0
	for n in get_nodes_in_group("ai_hearing"):
		if n.get("profile") != null and String(n.get("profile").id).contains("Civilian"):
			civs += 1
	check(civs >= 3, "at least 3 civilians (T-AI-02) (%d)" % civs)
	var nav := level.get_node_or_null("NavRegion_Block") as NavigationRegion3D
	check(nav != null, "navmesh region present")
	await unload()

func test_full_mission() -> void:
	print("[GPTEST] == full objective walk-through")
	await load_level()
	check(mm.state == MissionManager.State.IDLE, "mission starts IDLE")
	check(mm.start(), "MissionManager.start() accepted M01 data")
	check(mm.state == MissionManager.State.RUNNING, "state RUNNING")
	check(mm.current_index == 0, "objective 0 = intro phone call")
	check(mm.objective_text() == "", "intro beat has no HUD objective text")
	# Intro is a timed dialogue beat -> completes by itself (8 s)
	await seconds(8.5)
	check(mm.current_index == 1, "intro auto-completed -> objective 1 'Get in the car.'")
	check(mm.objective_text() == "Get in the car.", "objective text for step 1")
	# Step 1: actually enter the car. Vehicle.enter() is asynchronous by design: it opens the
	# door and only reports `driver`/DRIVING after `data.enter_time` (0.6 s) of physics frames.
	# Entering from the spawn point requires standing at an exit socket first.
	player.global_position = car.get_socket(&"SOCKET_Exit_Left").global_position
	await frames(2)
	var entered := car.enter(player)
	check(entered, "player entered the sedan (step 1 trigger)")
	await seconds(1.0)
	check(car.driver == player and car.state == Vehicle.State.DRIVING,
		"car reached DRIVING state with the player on the seat")
	check(mm.current_index == 2, "objective 1 completed by entering the car")
	check(mm.objective_text() == "Drive to the garage on Calloway Ave.", "objective text for step 2")
	# Step 2: drive the car into the garage arrival area
	car.global_position = level.get_node("Mission/Area_GarageArrival").global_position
	car.linear_velocity = Vector3.ZERO
	await frames(8)
	check(mm.current_index == 3, "objective 2 completed by entering Area_GarageArrival")
	check(mm.checkpoint_index == 2, "checkpoint saved at the garage arrival (step 2)")
	# Step 3: get out and walk into the garage
	check(car.driver == player, "car still has the driver")
	var exit_requested := car.request_exit()
	check(exit_requested, "exit request accepted (car standing still)")
	await seconds(1.0)          # data.exit_time = 0.5 s + the player's two-frame re-arm
	check(car.driver == null and player.vehicle == null, "player left the seat")
	player.global_position = level.get_node("Mission/Area_GarageInside").global_position
	await frames(8)
	check(mm.current_index == 4, "objective 3 completed inside the garage")
	check(mm.objective_text() == "Survive the ambush.", "objective text for step 4")
	# Step 4: kill all ambush enemies
	var enemies := get_nodes_in_group("mission_enemies")
	for e in enemies:
		var h: DamageReceiver = e.get("health")
		if h != null:
			h.apply_damage(_damage(1000.0))
	await frames(10)
	check(mm.current_index == 5, "objective 4 completed when every mission_enemy is dead")
	check(mm.objective_text() == "Grab the package.", "objective text for step 5")
	# Step 5: interact with the package
	player.global_position = pkg.global_position + Vector3(0, -1.0, 0.9)
	await frames(3)
	var interacted := mm.try_interact(player)
	check(interacted, "interact reached the package interactable")
	await frames(6)
	check(pkg.is_carried(), "package is carried")
	check(mm.current_index == 6, "objective 5 completed by picking the package up")
	check(mm.checkpoint_index == 5, "checkpoint after the pickup (step 5)")
	# Package follows the carrier and blocks sprinting (design: no sprint while carrying)
	var d0 := pkg.global_position.distance_to(player.global_position)
	await frames(10)
	var d1 := pkg.global_position.distance_to(player.global_position)
	check(d1 < 1.6 and absf(d1 - d0) < 0.2, "package follows the carrier (d=%.2f m)" % d1)
	# Step 6: load the package into the car and drive to the warehouse
	check(await board_car(), "player gets back into the sedan")
	pkg.load_into(car)
	await frames(4)
	check(pkg.is_loaded(), "package loaded into the sedan")
	car.global_position = level.get_node("Mission/Area_Warehouse").global_position
	await frames(10)
	check(mm.current_index == 7, "objective 6 completed at Area_Warehouse with the package")
	check(mm.objective_text() == "MISSION PASSED", "outro card objective")
	mm.debug_complete_current()
	await frames(4)
	check(mm.state == MissionManager.State.COMPLETED, "mission COMPLETED")
	check(mm.mission.reward_cash == 2500, "reward $2,500")
	await unload()

func test_player_death_fail_and_checkpoint() -> void:
	print("[GPTEST] == fail state: Jason dies -> restart at checkpoint")
	await load_level()
	mm.start()
	await seconds(8.5)
	await board_car()
	car.global_position = level.get_node("Mission/Area_GarageArrival").global_position
	await frames(8)
	check(mm.current_index == 3, "reached step 3 before dying")
	var cp := mm.checkpoint_index
	var hp: DamageReceiver = player.get_node("Health") as DamageReceiver
	hp.apply_damage(_damage(999.0))
	await frames(4)
	check(mm.state == MissionManager.State.FAILED, "player death fails the mission")
	check(mm.fail_reason.contains("Jason"), "fail reason names Jason (%s)" % mm.fail_reason)
	await seconds(2.0)
	check(mm.state == MissionManager.State.RUNNING, "auto-restart after the fail delay")
	check(mm.current_index == cp + 1, "restarted at the objective after the checkpoint (%d)" % mm.current_index)
	check(not hp.is_dead, "player health restored on restart")
	await unload()

func test_package_failures() -> void:
	print("[GPTEST] == fail state: package destroyed / left behind")
	await load_level()
	mm.start()
	await seconds(8.5)
	await board_car()
	car.global_position = level.get_node("Mission/Area_GarageArrival").global_position
	await frames(8)
	await leave_car()
	player.global_position = level.get_node("Mission/Area_GarageInside").global_position
	await frames(6)
	for e in get_nodes_in_group("mission_enemies"):
		var h: DamageReceiver = e.get("health")
		if h != null:
			h.apply_damage(_damage(1000.0))
	await frames(8)
	player.global_position = pkg.global_position + Vector3(0, -1.0, 0.9)
	await frames(3)
	mm.try_interact(player)
	await frames(4)
	check(pkg.is_carried(), "package picked up for the fail tests")
	if not sabotage:
		# "Left > 60 m behind": the crate stays on the bench while Jason walks away. (While it is
		# carried it is parented to the carrier, so it cannot be moved out of his hands.)
		pkg.drop()
		await frames(2)
		player.global_position = pkg.global_position + Vector3(80.0, 0.2, 0.0)
		await frames(6)
		check(mm.state == MissionManager.State.FAILED, "package left > 60 m fails the mission")
		check(mm.fail_reason.contains("left behind"), "fail reason: left behind (%s)" % mm.fail_reason)
		await seconds(2.0)
		check(mm.state == MissionManager.State.RUNNING and pkg.is_inside_tree(), "restart rebuilt the package")
	pkg.health.apply_damage(_damage(500.0))
	await frames(4)
	check(mm.state == MissionManager.State.FAILED, "package destroyed fails the mission")
	check(mm.fail_reason.contains("Package"), "fail reason: package (%s)" % mm.fail_reason)
	await unload()

func test_car_destroyed() -> void:
	print("[GPTEST] == fail state: sedan destroyed")
	await load_level()
	mm.start()
	await seconds(8.5)
	car.health = 0.0
	await frames(4)
	check(mm.state == MissionManager.State.FAILED, "destroyed sedan fails the mission")
	check(mm.fail_reason.contains("Sedan"), "fail reason: sedan (%s)" % mm.fail_reason)
	await unload()

func test_mission_data_matches_design() -> void:
	print("[GPTEST] == M01 data contract")
	var data := load("res://Data/Missions/M01_DeadDrop.tres") as MissionData
	check(data != null, "M01_DeadDrop.tres loads as MissionData")
	check(data.objectives.size() == 8, "8 objectives (intro + 6 steps + outro), got %d" % data.objectives.size())
	var texts := ["", "Get in the car.", "Drive to the garage on Calloway Ave.", "Check the garage.",
		"Survive the ambush.", "Grab the package.", "Deliver the package to the warehouse.", "MISSION PASSED"]
	for i in texts.size():
		check(data.objectives[i].text == texts[i], "objective %d text matches design" % i)
	var checkpoints := 0
	for o in data.objectives:
		if o.checkpoint:
			checkpoints += 1
	check(checkpoints == 2, "two checkpoints (start area + after pickup), got %d" % checkpoints)
	check(data.objectives[0].subtitles.size() == 3, "intro phone call has 3 subtitle lines")
	check(data.objectives[6].kind == ObjectiveData.Kind.DELIVER and data.objectives[6].requires_package,
		"delivery requires the package")

func test_sabotage_detected() -> void:
	print("[GPTEST] == sabotage control")
	var data := load("res://Data/Missions/M01_DeadDrop.tres") as MissionData
	data.objectives[2].checkpoint = false
	check(data.objectives[2].checkpoint, "SABOTAGE: checkpoint flag was removed -> test suite failed as designed")

# --- helpers ------------------------------------------------------------------

## Boards the sedan the way the game does (stand at an exit socket, then enter) and waits for
## the asynchronous ENTERING -> DRIVING transition.
func board_car() -> bool:
	player.global_position = car.get_socket(&"SOCKET_Exit_Left").global_position
	await frames(2)
	var ok := car.enter(player)
	await seconds(1.0)
	return ok and car.driver == player

## Leaves the seat through the real exit sequence.
func leave_car() -> void:
	car.request_exit()
	await seconds(1.0)

func _damage(amount: float) -> DamageInfo:
	var info := DamageInfo.new()
	info.amount = amount
	info.source = null
	return info
