# UNDERWORLD - headless mission framework tests (T-MIS-01, M01 "Dead Drop").
#
#   godot --headless --fixed-fps 60 --path GodotProject --script res://Tests/test_mission.gd
#
# Drives the REAL level (Scenes/Levels/LA_CallowayAve.tscn) through every M01 objective,
# the fail states and the checkpoint restart, using gameplay triggers - not timers - wherever
# the design allows it. MissionManager.debug_complete_current() is used for the intro/outro
# beats only, exactly as the design contract specifies.
#
# Negative controls (each one corrupts the production data/behaviour BEFORE the real checks run,
# so the ordinary assertions fail - there is deliberately no self-referential "sabotage check"):
#   UW_MISSION_SABOTAGE=1  objective 2 loses its checkpoint, package stray distance = 1e9
#                          -> checkpoint index/count and "left behind" checks FAIL
#   UW_MISSION_SABOTAGE=2  wave 2 is live from the start (MissionManager._prepare_waves keeps it)
#                          -> "wave 2 cold before the ambush" and "wave 2 only after wave 1" FAIL
#   UW_MISSION_SABOTAGE=3  Marco becomes killable (AllyCompanion.health.invulnerable = false)
#                          -> "Marco survives damage" FAIL
extends SceneTree

const LEVEL := "res://Scenes/Levels/LA_CallowayAve.tscn"
const HZ := 60.0
const WATCHDOG := 60 * 300

var failures: Array[String] = []
var _frames := 0
var _done := false
var sabotage := int(OS.get_environment("UW_MISSION_SABOTAGE")) if OS.get_environment("UW_MISSION_SABOTAGE") != "" else 0

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
	if sabotage == 1 and mm != null:
		_sabotage_data(mm.mission)
		mm.package_stray_distance = 1.0e9

func unload() -> void:
	level.queue_free()
	await frames(3)

# --- tests --------------------------------------------------------------------

func _run() -> void:
	_done = false
	print("[GPTEST] == M01 mission framework (sabotage=%s)" % str(sabotage))
	await test_level_contents()
	await test_marco_and_waves()
	await test_ambush_waves_in_order()
	await test_real_drive()
	await test_full_mission()
	await test_player_death_fail_and_checkpoint()
	await test_package_failures()
	await test_car_destroyed()
	await test_mission_data_matches_design()
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

## T-MIS-01b: Marco is an ally on the passenger seat, invulnerable in M1, and the two waves
## are bookkept separately. No teleporting, no timers: the mission start does the seating.
func test_marco_and_waves() -> void:
	print("[GPTEST] == Marco as ally + wave bookkeeping (T-MIS-01b)")
	await load_level()
	var marco := level.get_node_or_null("AI/Ally_Marco") as AllyCompanion
	check(marco != null, "Ally_Marco exists in the level (AI/Ally_Marco)")
	if marco == null:
		await unload()
		return
	check(marco.is_in_group("ally") and not marco.is_in_group("mission_enemies"),
		"Marco is in group 'ally' and NOT in 'mission_enemies'")
	check(marco.health != null and marco.health.invulnerable,
		"Marco is invulnerable before the mission starts (M1 design)")
	check(mm.start(), "mission starts with Marco in the cast")
	await frames(2)
	check(marco.is_seated(), "Marco sits on the passenger seat after start()")
	check(car.passenger == marco, "the sedan knows Marco as its passenger")
	var seat := car.get_socket(&"SOCKET_Seat_Passenger")
	check(seat != null and marco.global_position.distance_to(seat.global_position) < 0.25,
		"Marco's body is on SOCKET_Seat_Passenger (%.2f m)" % (
			marco.global_position.distance_to(seat.global_position) if seat != null else 999.0))
	# Enemy AI must never pick an ally as its target.
	var enemy_targets_marco := false
	for n in get_nodes_in_group("mission_enemy"):
		var e := n as MissionEnemy
		if e != null and e.target == marco:
			enemy_targets_marco = true
	check(not enemy_targets_marco, "no gunman targets Marco")
	# M1: Marco is not killable. This is the check UW_MISSION_SABOTAGE=3 turns red, because
	# seat_ally() clears DamageReceiver.invulnerable in that mode.
	var hp_before := marco.health.health
	marco.health.apply_damage(_damage(500.0))
	await frames(2)
	check(not marco.is_dead() and is_equal_approx(marco.health.health, hp_before),
		"Marco survives 500 damage unhurt (%.0f -> %.0f HP)" % [hp_before, marco.health.health])
	check(marco.health.invulnerable, "Marco's DamageReceiver stays invulnerable in M1")
	# Wave bookkeeping: both waves recognised, none of them live before the ambush trigger.
	check(mm.wave_groups.has("1") and mm.wave_groups.has("2"), "mission sees wave 1 and wave 2")
	check((mm.wave_groups.get("1", []) as Array).size() == 3, "wave 1 has 3 gunmen")
	check((mm.wave_groups.get("2", []) as Array).size() == 2, "wave 2 has 2 gunmen")
	var live := 0
	for n in get_nodes_in_group("mission_enemy"):
		var e := n as MissionEnemy
		if e != null and e.is_active():
			live += 1
	check(live == 0, "no ambush gunman is active before the ambush (%d live)" % live)
	await unload()


## T-MIS-01b: wave 1 comes from the garage trigger, wave 2 only once wave 1 is dead, and
## "Survive the ambush" only completes when both are down. This uses the real objective flow.
func test_ambush_waves_in_order() -> void:
	print("[GPTEST] == ambush waves in order (T-MIS-01b)")
	await load_level()
	mm.start()
	await seconds(8.5)                      # intro phone call
	await board_car()
	check(mm.current_index == 2, "objective 2 (drive) after boarding")
	# Real drive is covered by test_real_drive(); here we step the objective data only.
	car.global_position = level.get_node("Mission/Area_GarageArrival").global_position
	car.linear_velocity = Vector3.ZERO
	await frames(8)
	check(mm.current_index == 3, "objective 3 (check the garage)")
	await leave_car()
	player.global_position = level.get_node("Mission/Area_GarageInside").global_position
	await frames(10)
	check(mm.current_index == 4, "objective 4 (survive the ambush) after entering the garage")
	var wave1_alive := 0
	for n in mm.wave_groups.get("1", []):
		var e := n as MissionEnemy
		if e != null and not e.is_dead():
			wave1_alive += 1
			if e.is_active():
				pass
	check(wave1_alive == 3, "all three wave-1 gunmen alive at the ambush start")
	# WAVE ORDER: wave 1 live, wave 2 still cold.
	var w2_live := 0
	for n in mm.wave_groups.get("2", []):
		var e := n as MissionEnemy
		if e != null and e.is_active():
			w2_live += 1
	check(w2_live == 0, "wave 2 is NOT active while wave 1 fights (%d live)" % w2_live)
	check(not mm.are_wave_dead("2"), "wave 2 is not 'dead' before it ever spawned")
	# Kill wave 1 only: the objective must not complete yet, wave 2 must come.
	for n in mm.wave_groups.get("1", []):
		var e := n as MissionEnemy
		if e != null and e.health != null:
			e.health.apply_damage(_damage(1000.0))
	await frames(10)
	check(mm.current_index == 4, "objective 4 still running after wave 1 died (wave 2 pending)")
	await frames(12)
	check(mm.waves_released.has("2"), "wave 2 was released after wave 1 died")
	var w2_now := 0
	for n in mm.wave_groups.get("2", []):
		var e := n as MissionEnemy
		if e != null and e.is_active() and not e.is_dead():
			w2_now += 1
	check(w2_now == 2, "both wave-2 gunmen are live after wave 1 (%d)" % w2_now)
	# Now kill wave 2 -> the ambush objective completes.
	for n in mm.wave_groups.get("2", []):
		var e := n as MissionEnemy
		if e != null and e.health != null:
			e.health.apply_damage(_damage(1000.0))
	await frames(10)
	check(mm.current_index == 5, "objective 4 completes only when BOTH waves are dead")
	await unload()


## T-MIS-01b acceptance: at least one route (start -> Area_GarageArrival) is DRIVEN with
## driving input, not teleported, in <= 60 s of game time, and the car stays on the road.
func test_real_drive() -> void:
	print("[GPTEST] == real drive start -> garage arrival with driving input")
	await load_level()
	mm.start()
	await seconds(8.5)
	await board_car()
	check(mm.current_index == 2, "drive objective active")
	var start_pos := car.global_position
	var waypoints: Array = _route_waypoints()
	check(waypoints.size() >= 3, "a drivable route start -> Area_GarageArrival exists (%d waypoints)" % waypoints.size())
	if waypoints.is_empty():
		await unload()
		return
	var t := 0.0
	var arrived := false
	var max_off_road := 0.0
	var idx := 0
	# Drive with the real input map, exactly like a player would.
	while t < 60.0 and not arrived:
		var target: Vector3 = waypoints[min(idx, waypoints.size() - 1)]
		var to_target := target - car.global_position
		to_target.y = 0.0
		var dist := to_target.length()
		if dist < 6.0:
			idx += 1
			if idx >= waypoints.size():
				arrived = true
				break
			target = waypoints[idx]
			to_target = target - car.global_position
			to_target.y = 0.0
		var fwd := car.global_basis.z.normalized()
		var err := (fwd as Vector3).signed_angle_to(to_target.normalized(), Vector3.UP)
		# Positive steer_input = turn left = +yaw (see test_vehicle: "steer left -> yaw > 0"),
		# so a target to the LEFT (positive signed angle) needs positive steer.
		var steer := clampf(err / deg_to_rad(10.0), -1.0, 1.0)
		var speed := car.forward_speed
		# Slow down for corners / the last stretch, brake instead of accelerating when the
		# heading error is large - otherwise the car drives circles around its waypoint.
		var want_slow := absf(err) > deg_to_rad(20.0) or dist < 12.0
		var throttle := 0.0
		var brake := 0.0
		if want_slow and speed > 6.0:
			brake = 1.0
		elif speed < 14.0:
			throttle = 0.9
		car.set_controls(throttle, brake, steer)
		await physics_frame
		t += 1.0 / HZ
		max_off_road = maxf(max_off_road, _off_road_distance(car.global_position))
		if _off_road_distance(car.global_position) > 6.0:
			break   # runaway: stop the loop, the checks below report why
		if mm.current_index >= 3:
			arrived = true
	car.set_controls(0.0, 1.0, 0.0)
	await seconds(0.5)
	print("[GPTEST] drive took %.1f s, %.1f m, max off-road %.2f m" % [
		t, start_pos.distance_to(car.global_position), max_off_road])
	check(t <= 60.0, "the route was driven in <= 60 s (%.1f s)" % t)
	check(mm.current_index >= 3, "driving into Area_GarageArrival completed objective 2")
	check(max_off_road < 2.0, "the car stayed on the road (max %.2f m from the corridor)" % max_off_road)
	check(start_pos.distance_to(car.global_position) > 40.0,
		"the car actually travelled (%.1f m)" % start_pos.distance_to(car.global_position))
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
	# door and only reports `driver`/DRIVING after the enter CLIP has played (T-GP-04:
	# Vehicle.enter_duration() = A_Jason_Car_Enter_L length, VehicleData.enter_time as fallback).
	# Entering from the spawn point requires standing at an exit socket first.
	player.global_position = car.get_socket(&"SOCKET_Exit_Left").global_position
	await frames(2)
	var entered := car.enter(player)
	check(entered, "player entered the sedan (step 1 trigger)")
	await seconds(car.enter_duration() + 0.1)
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
	await seconds(car.exit_duration() + 0.6)  # exit clip + the player's two-frame re-arm
	check(car.driver == null and player.vehicle == null, "player left the seat")
	player.global_position = level.get_node("Mission/Area_GarageInside").global_position
	await frames(8)
	check(mm.current_index == 4, "objective 3 completed inside the garage")
	check(mm.objective_text() == "Survive the ambush.", "objective text for step 4")
	# Step 4: kill the ambush, wave by wave (wave 2 only spawns after wave 1)
	await clear_ambush()
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
	# Pin the expected checkpoint: otherwise "restart at cp + 1" is true for any cp, including -1.
	check(cp == 2, "checkpoint before dying is the garage arrival (2), got %d" % cp)
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
	await clear_ambush()
	await frames(8)
	player.global_position = pkg.global_position + Vector3(0, -1.0, 0.9)
	await frames(3)
	mm.try_interact(player)
	await frames(4)
	check(pkg.is_carried(), "package picked up for the fail tests")
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
	if sabotage == 1 and data != null:
		_sabotage_data(data)
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

## Negative control (UW_MISSION_SABOTAGE): corrupt the mission data the real checks look at.
func _sabotage_data(data: MissionData) -> void:
	if data == null or data.objectives.size() < 3:
		return
	print("[GPTEST] SABOTAGE: objective 2 checkpoint removed, package stray distance disabled")
	data.objectives[2].checkpoint = false

# --- helpers ------------------------------------------------------------------

## Boards the sedan the way the game does (stand at an exit socket, then enter) and waits for
## the asynchronous ENTERING -> DRIVING transition.
func board_car() -> bool:
	player.global_position = car.get_socket(&"SOCKET_Exit_Left").global_position
	await frames(2)
	var ok := car.enter(player)
	# T-GP-04: the enter sequence lasts as long as the enter CLIP, not a constant.
	await seconds(car.enter_duration() + 0.1)
	return ok and car.driver == player

## Leaves the seat through the real exit sequence.
func leave_car() -> void:
	car.request_exit()
	await seconds(car.exit_duration() + 0.6)

func _damage(amount: float) -> DamageInfo:
	var info := DamageInfo.new()
	info.amount = amount
	info.source = null
	return info

# --- ambush helpers (T-MIS-01b) -----------------------------------------------

## Kill every gunman, wave by wave, waiting for the mission to release the next wave in between.
## The earlier M01 tests use this instead of "kill everything at once" so they exercise the real
## wave ordering (wave 2 does not exist as an active enemy until wave 1 is dead).
func clear_ambush() -> void:
	var guard := 0
	while guard < 4:
		guard += 1
		var killed := 0
		for n in get_nodes_in_group("mission_enemies"):
			var e := n as MissionEnemy
			if e != null and not e.is_dead() and e.health != null:
				e.health.apply_damage(_damage(1000.0))
				killed += 1
		await frames(12)
		var still := 0
		for n in get_nodes_in_group("mission_enemies"):
			var e := n as MissionEnemy
			if e != null and not e.is_dead():
				still += 1
		if still == 0:
			return


# --- driving helpers (T-MIS-01b) ----------------------------------------------

## The M01 route from the start spawn to the garage forecourt, as a list of world points on the
## drive ring (layout §3.1): west lane north, north segment east, east lane south, forecourt.
## Derived from the level's own anchors, so a layout change moves the route with it.
func _route_waypoints() -> Array:
	var out: Array = []
	var spawn := level.get_node_or_null("Mission/CarSpawn") as Node3D
	var arrival := level.get_node_or_null("Mission/Area_GarageArrival") as Node3D
	if spawn == null or arrival == null:
		return out
	var x_w := spawn.global_position.x          # west lane centre (-24)
	var x_e := arrival.global_position.x        # in front of the garage
	out.append(spawn.global_position + Vector3(0, 0, 14))   # straight ahead, north
	out.append(Vector3(x_w, 0.1, 40.0))
	out.append(Vector3(x_w, 0.1, 62.0))
	out.append(Vector3(x_w, 0.1, 79.0))         # north segment
	out.append(Vector3(0.0, 0.1, 79.0))
	out.append(Vector3(24.0, 0.1, 79.0))        # corner into the east lane
	out.append(Vector3(24.0, 0.1, 50.0))
	out.append(Vector3(24.0, 0.1, 20.0))
	out.append(Vector3(x_e, 0.1, arrival.global_position.z))
	return out


## How far a point is from the drivable corridor (0 = on the road). Used to prove the car did
## not cut across a sidewalk or a building lot.
func _off_road_distance(p: Vector3) -> float:
	var lanes := [[-29.0, -19.0], [19.0, 29.0]]     # N-S roads (x ranges)
	var best := INF
	for lane in lanes:
		if p.z >= -86.0 and p.z <= 86.0:
			var dx := 0.0
			if p.x < lane[0]:
				dx = lane[0] - p.x
			elif p.x > lane[1]:
				dx = p.x - lane[1]
			best = minf(best, dx)
	# north / south segments (z ranges)
	if p.x >= -33.0 and p.x <= 33.0:
		for band in [[72.0, 86.0], [-86.0, -72.0]]:
			var dz := 0.0
			if p.z < band[0]:
				dz = band[0] - p.z
			elif p.z > band[1]:
				dz = p.z - band[1]
			best = minf(best, dz)
	# the garage forecourt / east lane apron in front of the roll-up door
	if p.x >= 15.0 and p.x <= 19.0 and p.z >= -2.0 and p.z <= 14.0:
		best = minf(best, 0.0)
	return best
