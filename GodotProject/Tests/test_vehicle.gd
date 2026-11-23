# UNDERWORLD - headless tests for vehicle physics + enter/exit on VH_Sedan_01 (T-GP-03).
# Run via Tests/run_gameplay_tests.sh (imports first), or directly:
#   godot --headless --fixed-fps 60 --path GodotProject --script res://Tests/test_vehicle.gd
# Uses the real input map (vehicle_accelerate / vehicle_brake / move_left / enter_vehicle ...).
# Negative controls run in the suite (sabotaged copies must be detected); set
# UW_VEHICLE_SABOTAGE=1 (drive: engine x0.3, no steering, no brakes) or =2 (+ exit socket
# moved into the car) to sabotage the real car -> the suite must FAIL (exit 1).
extends SceneTree

const RANGE := "res://Scenes/Test/PT_VehicleTestRange.tscn"
const SEDAN := "res://Scenes/Vehicles/VH_Sedan_01.tscn"
const MANIFEST := "res://Assets/Vehicles/VH_Sedan_01/VH_Sedan_01.manifest.json"
const HZ := 60.0
const ACTIONS := ["vehicle_accelerate", "vehicle_brake", "vehicle_handbrake", "move_left",
	"move_right", "move_forward", "move_back", "enter_vehicle", "interact"]
const WATCHDOG_FRAMES := 60 * 240

var failures: Array[String] = []
var _frames := 0
var _done := false
var range_scene: Node3D
var car: Vehicle
var player: PlayerController
var min_car_y := INF
var sabotage := OS.get_environment("UW_VEHICLE_SABOTAGE") != ""

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

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames > WATCHDOG_FRAMES and not _done:
		print("[GPTEST][FAIL] watchdog: tests did not finish in %d frames" % WATCHDOG_FRAMES)
		quit(1)
	return false

func frames(n: int) -> void:
	for i in n:
		await physics_frame
		if car != null and is_instance_valid(car):
			min_car_y = minf(min_car_y, car.global_position.y)

func seconds(s: float) -> void:
	await frames(int(round(s * HZ)))

func release_all() -> void:
	for a in ACTIONS:
		Input.action_release(a)

func tap(action: String) -> void:
	Input.action_press(action)
	await frames(1)
	Input.action_release(action)
	await frames(1)

## Press until cond() or timeout; returns seconds waited (or -1 on timeout).
func hold_until(action: String, cond: Callable, timeout_s: float) -> float:
	Input.action_press(action)
	var n := 0
	while not cond.call() and n < int(timeout_s * HZ):
		await frames(1)
		n += 1
	Input.action_release(action)
	return n / HZ if cond.call() else -1.0

func _run_all() -> void:
	await frames(1)
	range_scene = (load(RANGE) as PackedScene).instantiate()
	if sabotage:
		print("[GPTEST] SABOTAGE MODE %s: engine x0.3, steering off, brakes off%s" % [OS.get_environment("UW_VEHICLE_SABOTAGE"),
			", exit socket moved into the car" if OS.get_environment("UW_VEHICLE_SABOTAGE") == "2" else ""])
	root.add_child(range_scene)
	car = range_scene.get_node("VH_Sedan_01") as Vehicle
	player = range_scene.get_node("Player") as PlayerController
	if sabotage:
		_sabotage(car)
	await frames(2)
	await test_asset_contract()
	await test_parked_on_floor()
	await test_door_hinges()
	await test_enter_too_far()
	await test_enter()
	await test_accelerate()
	await test_brake()
	await test_steer()
	await test_exit_too_fast_and_exit()
	await test_exit_blocked_sides()
	await test_crash_damage()
	test_steering_math()
	check(min_car_y > -0.05, "car never fell through the floor (min body y %.3f m)" % min_car_y)
	await test_negative_controls()
	_done = true
	release_all()
	if failures.is_empty():
		print("[GPTEST] RESULT: PASS")
		quit(0)
	else:
		print("[GPTEST] RESULT: FAIL (%d)" % failures.size())
		for f in failures:
			print("[GPTEST]   - ", f)
		quit(1)

func _sabotage(v: Vehicle) -> void:
	v.data = v.data.duplicate()
	v.data.engine_force *= 0.3
	v.data.steer_max_deg = 0.0
	v.data.steer_min_deg = 0.0
	v.data.brake_force = 0.0
	v.data.idle_brake = 0.0
	if OS.get_environment("UW_VEHICLE_SABOTAGE") == "2":
		(v.get_socket(&"SOCKET_Exit_Left") as Node3D).position.x = 0.5

# --- 1. asset contract (verified on the imported scene, not the docs) --------

func test_asset_contract() -> void:
	check(car.assembly_errors.is_empty(), "VH_Sedan_01 assembles without errors %s" % car.assembly_errors)
	check(car.wheels.size() == 4, "4 wheel nodes found (Wheel_FL/FR/RL/RR) -> 4 VehicleWheel3D")
	var m = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST))
	check(m is Dictionary and m.get("collision", {}).get("existing", []).size() == 1, "manifest declares the authored UCX hull")
	check(approx(car.asset_wheel_radius, 0.34, 0.005), "asset wheel radius (glTF extras) = %.3f m (0.34)" % car.asset_wheel_radius)
	for wn in car.wheel_meshes:
		var mi := car.wheel_meshes[wn] as MeshInstance3D
		var r := mi.get_aabb().size.y * 0.5
		check(approx(r, 0.34, 0.005) and approx(mi.get_aabb().size.z * 0.5, 0.34, 0.005), "%s mesh radius %.3f m matches 0.34" % [wn, r])
		check(approx((car.wheels[wn] as VehicleWheel3D).wheel_radius, car.asset_wheel_radius, 0.005), "%s physics radius = asset radius" % wn)
	var p: Dictionary = car.wheel_design_pos
	if p.size() == 4:
		var wb: float = (p[&"Wheel_FL"] as Vector3).z - (p[&"Wheel_RL"] as Vector3).z
		var tw: float = (p[&"Wheel_FL"] as Vector3).x - (p[&"Wheel_FR"] as Vector3).x
		check(approx(wb, 2.86, 0.01), "wheelbase from asset nodes %.3f m (2.86)" % wb)
		check(approx(tw, 1.58, 0.01), "track from asset nodes %.3f m (1.58)" % tw)
		check(approx((p[&"Wheel_RR"] as Vector3).z, (p[&"Wheel_RL"] as Vector3).z, 0.001) and (p[&"Wheel_FL"] as Vector3).z > 0.0,
			"front axle at +Z (car faces +Z), axles square")
		check(approx((p[&"Wheel_FL"] as Vector3).y, 0.34, 0.005), "wheel centres at radius height (tyres on y = 0)")
	var front_steer := (car.wheels[&"Wheel_FL"] as VehicleWheel3D).use_as_steering and (car.wheels[&"Wheel_FR"] as VehicleWheel3D).use_as_steering
	var rwd := (car.wheels[&"Wheel_RL"] as VehicleWheel3D).use_as_traction and not (car.wheels[&"Wheel_FL"] as VehicleWheel3D).use_as_traction
	check(front_steer and rwd, "front wheels steer, rear wheels driven (RWD)")
	# Collision: authored convex hull moved onto the VehicleBody3D, StaticBody removed.
	check(car.collision_shape != null and car.collision_shape.shape is ConvexPolygonShape3D, "UCX convex hull is the car's CollisionShape3D")
	var statics: Array[Node] = car.model.find_children("*", "StaticBody3D", true, false)
	check(statics.is_empty(), "imported UCX StaticBody3D removed from the model")
	if car.collision_shape != null:
		var lo := INF
		var hx := 0.0
		for pt in (car.collision_shape.shape as ConvexPolygonShape3D).points:
			lo = minf(lo, pt.y)
			hx = maxf(hx, absf(pt.x))
		check(lo >= 0.30, "hull underside %.2f m clears the wheel rays (>= 0.30)" % lo)
		for sn in [&"SOCKET_Exit_Left", &"SOCKET_Exit_Right"]:
			var s := car.get_socket(sn)
			check(s != null and absf(s.position.x) - car.data.exit_check_radius > hx, "%s outside the hull + player radius" % sn)
	check(car.doors.size() == 4, "4 doors with hinge pivots found")
	for sn in [&"SOCKET_Seat_Driver", &"SOCKET_Seat_Passenger", &"SOCKET_Exit_Left", &"SOCKET_Exit_Right",
			&"SOCKET_Headlight_L", &"SOCKET_Headlight_R", &"SOCKET_Taillight_L", &"SOCKET_Taillight_R"]:
		check(car.get_socket(sn) != null, "socket %s present" % sn)
	var seat := car.get_socket(&"SOCKET_Seat_Driver")
	check(seat != null and seat.position.x > 0.0, "driver seat on the left (+X) = LHD, same side as SOCKET_Exit_Left")
	await frames(1)

# --- 2. parked -------------------------------------------------------------------

func test_parked_on_floor() -> void:
	await seconds(2.0)
	check(approx(car.global_position.y, 0.0, 0.01), "parked body origin on the floor (y %.4f m, calibrates STATIC_SAG_K)" % car.global_position.y)
	var all_contact := true
	var worst := 0.0
	for wn in car.wheels:
		all_contact = all_contact and (car.wheels[wn] as VehicleWheel3D).is_in_contact()
		var design: Vector3 = car.global_transform * (car.wheel_design_pos[wn] as Vector3)
		worst = maxf(worst, car.get_wheel_visual_centre(wn).distance_to(design))
	check(all_contact, "all 4 wheels touch the ground")
	check(worst < 0.01, "drawn wheels sit at the asset wheel positions when parked (worst %.4f m)" % worst)
	check(car.linear_velocity.length() < 0.05, "parked car does not creep (%.3f m/s)" % car.linear_velocity.length())

# --- 3. doors --------------------------------------------------------------------

func _door_rear_edge(dn: StringName) -> Vector3:
	return (car.doors[dn] as Node3D).global_transform * Vector3(0, 0, -0.85)

func test_door_hinges() -> void:
	var closed := {}
	var hinge := {}
	for dn in car.doors:
		closed[dn] = _door_rear_edge(dn)
		hinge[dn] = (car.doors[dn] as Node3D).global_position
		car.open_door(dn)
	await seconds(car.data.door_swing_time + 0.1)
	for dn in car.doors:
		var now := _door_rear_edge(dn)
		var left := String(dn).ends_with("L")
		var out: float = (now.x - closed[dn].x) * (1.0 if left else -1.0)
		check(out > 0.5 and approx(car.get_door_open(dn), 1.0, 0.001), "%s swings outward around its hinge (rear edge +%.2f m out)" % [dn, out])
		check((car.doors[dn] as Node3D).global_position.distance_to(hinge[dn]) < 0.001, "%s hinge point stays fixed" % dn)
		car.close_door(dn)
	await seconds(car.data.door_swing_time + 0.1)
	var shut := true
	for dn in car.doors:
		shut = shut and _door_rear_edge(dn).distance_to(closed[dn]) < 0.001
	check(shut, "doors close back to the asset pose")

# --- 4. enter --------------------------------------------------------------------

func test_enter_too_far() -> void:
	var start := player.global_position
	player.global_position = car.global_position + Vector3(6.0, 0.0, 0.0)
	await frames(2)
	await tap("enter_vehicle")
	check(player.vehicle == null and car.driver == null, "enter_vehicle 6 m away does nothing")
	player.global_position = start
	await frames(2)

func test_enter() -> void:
	var opened := []
	car.door_changed.connect(func(d, o): opened.append([d, o]))
	var d := car.get_socket(&"SOCKET_Exit_Left").global_position.distance_to(player.global_position)
	await tap("enter_vehicle")
	check(player.vehicle == car and car.driver == player, "F/Y near the driver door (%.2f m) enters the car" % d)
	check(not player.input_enabled and not player.visual.visible and not player.is_physics_processing(), "player hidden, input + movement off while in the car")
	await frames(1)
	check(player.collision_layer == 0 and player.collision_mask == 0, "player collision off while in the car")
	check(car.chase_camera.current, "chase camera active")
	check(opened.size() >= 1 and opened[0] == [&"Door_FL", true], "driver door Door_FL opens on enter")
	await seconds(car.enter_duration() + 0.05)
	check(car.state == Vehicle.State.DRIVING, "enter sequence done -> DRIVING")
	check(opened.size() >= 2 and opened[1] == [&"Door_FL", false], "driver door closes after getting in")
	var seat := car.get_socket(&"SOCKET_Seat_Driver")
	check(player.global_position.distance_to(seat.global_position) < 0.05, "player attached to SOCKET_Seat_Driver")

# --- 5. drive --------------------------------------------------------------------

func test_accelerate() -> void:
	var z0 := car.global_position.z
	var spin0 := (car.wheel_meshes[&"Wheel_RL"] as Node3D).global_basis
	Input.action_press("vehicle_accelerate")
	await seconds(1.0)
	var spin1 := (car.wheel_meshes[&"Wheel_RL"] as Node3D).global_basis
	await seconds(2.0)
	var v := car.forward_speed
	check(v > 8.0, "[ACCEPTANCE] throttle 3 s -> %.1f m/s (> 8)" % v)
	check(car.global_position.z - z0 > 10.0, "car moved forward along +Z (%.1f m)" % (car.global_position.z - z0))
	check(absf(car.global_position.x) < 0.3, "straight line holds (x drift %.2f m)" % car.global_position.x)
	var rpm := (car.wheels[&"Wheel_RL"] as VehicleWheel3D).get_rpm()
	check(rpm > 100.0 and not spin0.is_equal_approx(spin1), "asset wheel meshes spin (rear rpm %.0f)" % rpm)
	var behind := (car.global_position - car.chase_camera.global_position).dot(car.global_basis.z)
	check(behind > 3.0 and car.chase_camera.global_position.y > car.global_position.y + 1.0, "chase camera follows behind and above (%.1f m behind)" % behind)
	check(car.engine_pitch > car.data.pitch_idle, "engine pitch rises with speed (%.2f)" % car.engine_pitch)
	# Driver stays on the seat while moving.
	# Attached in the car's _physics_process, i.e. before this frame's physics step -> lags one step.
	var lag := player.global_position.distance_to(car.get_socket(&"SOCKET_Seat_Driver").global_position)
	check(lag < car.linear_velocity.length() / HZ + 0.05, "driver follows the seat socket (%.3f m, <= one physics step)" % lag)
	Input.action_release("vehicle_accelerate")

func test_brake() -> void:
	var v0 := car.forward_speed
	var z0 := car.global_position.z
	var t := await hold_until("vehicle_brake", func(): return car.forward_speed < 0.5, 5.0)
	check(t > 0.0, "[ACCEPTANCE] brake from %.1f m/s to < 0.5 m/s in %.2f s (%.1f m)" % [v0, t, car.global_position.z - z0])
	await seconds(0.5)
	check(absf(car.forward_speed) < 0.5, "car stays stopped with no input (%.2f m/s)" % car.forward_speed)

func test_steer() -> void:
	var yaw0 := car.global_rotation.y
	Input.action_press("vehicle_accelerate")
	Input.action_press("move_left")
	await seconds(0.5)
	var fl := (car.wheel_meshes[&"Wheel_FL"] as Node3D)
	var steer_local := (car.global_basis.inverse() * fl.global_basis).get_euler(EULER_ORDER_YXZ).y
	var rl := (car.global_basis.inverse() * (car.wheel_meshes[&"Wheel_RL"] as Node3D).global_basis).get_euler(EULER_ORDER_YXZ).y
	check(steer_local > deg_to_rad(10.0) and absf(rl) < 0.001, "front wheel meshes steer left (%.1f deg), rear stay straight" % rad_to_deg(steer_local))
	await seconds(1.5)
	var dyaw := rad_to_deg(wrapf(car.global_rotation.y - yaw0, -PI, PI))
	check(dyaw > 20.0, "steer left -> yaw +%.1f deg in 2 s" % dyaw)
	Input.action_release("move_left")
	Input.action_press("move_right")
	var yaw1 := car.global_rotation.y
	await seconds(2.0)
	var dyaw2 := rad_to_deg(wrapf(car.global_rotation.y - yaw1, -PI, PI))
	check(dyaw2 < -20.0, "steer right -> yaw %.1f deg in 2 s" % dyaw2)
	Input.action_release("move_right")
	Input.action_release("vehicle_accelerate")
	var t := await hold_until("vehicle_brake", func(): return car.forward_speed < 0.3, 6.0)
	check(t > 0.0, "stopped again after the steering run")
	await seconds(0.3)

# --- 6. exit ---------------------------------------------------------------------

func test_exit_too_fast_and_exit() -> void:
	Input.action_press("vehicle_accelerate")
	await seconds(1.5)
	Input.action_release("vehicle_accelerate")
	check(not car.request_exit(), "no exit above exit_max_speed (%.1f m/s)" % car.forward_speed)
	await hold_until("vehicle_brake", func(): return car.forward_speed < 0.3, 6.0)
	await seconds(0.5)
	var exited := []
	car.exited.connect(func(p): exited.append(p), CONNECT_ONE_SHOT)
	await tap("enter_vehicle")
	check(car.state == Vehicle.State.EXITING and car.get_door_open(&"Door_FL") > 0.0, "F/Y while stopped starts the exit, driver door opens")
	await seconds(car.exit_duration() + 0.05)
	var sock := car.get_socket(&"SOCKET_Exit_Left").global_position
	check(exited.size() == 1 and player.vehicle == null and car.driver == null, "exit finished, car empty")
	check(player.global_position.distance_to(sock) < 0.05, "[ACCEPTANCE] player placed at SOCKET_Exit_Left (%.3f m off)" % player.global_position.distance_to(sock))
	await frames(3)
	check(player.input_enabled and player.visual.visible and player.collision_layer == 2 and player.collision_mask == 13 and player.is_physics_processing(), "player visible, collision + input back on")
	check(player.camera_rig.camera.current and not car.chase_camera.current, "player camera active again")
	var face := player.get_facing_direction().dot(car.global_basis.z)
	check(face > 0.95, "player faces the car's heading after exit")
	# On-foot control works again: walk away from the car.
	var p0 := player.global_position
	Input.action_press("move_forward")
	await seconds(0.6)
	Input.action_release("move_forward")
	await seconds(0.3)
	check(player.global_position.distance_to(p0) > 0.8 and player.is_on_floor(), "player walks on after exit (%.2f m)" % player.global_position.distance_to(p0))
	check(car.handbrake_input == 1.0, "empty car has the parking brake on")

func _block(pos: Vector3) -> StaticBody3D:
	var b := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(0.6, 2.0, 1.2)
	cs.shape = box
	b.add_child(cs)
	range_scene.add_child(b)
	# Aligned with the car so the block covers the exit but never touches the body.
	b.global_transform = Transform3D(Basis(Vector3.UP, car.global_rotation.y), pos + Vector3.UP)
	return b

func test_exit_blocked_sides() -> void:
	# Re-enter (player is next to the left door), block the left exit -> leave on the right.
	player.global_position = car.get_socket(&"SOCKET_Exit_Left").global_position + car.global_basis.x * 0.6
	await frames(2)
	await tap("enter_vehicle")
	await seconds(car.enter_duration() + 0.3)
	check(car.state == Vehicle.State.DRIVING, "re-enter works")
	var wall_l := _block(car.get_socket(&"SOCKET_Exit_Left").global_position)
	await frames(2)
	check(not car.is_exit_free(&"SOCKET_Exit_Left") and car.is_exit_free(&"SOCKET_Exit_Right"), "free-space check sees the blocked left exit")
	await tap("enter_vehicle")
	await seconds(car.exit_duration() + 0.1)
	var r := car.get_socket(&"SOCKET_Exit_Right").global_position
	check(player.vehicle == null and player.global_position.distance_to(r) < 0.05, "left blocked -> player exits at SOCKET_Exit_Right")
	# Both blocked -> stays in.
	await frames(3)
	player.global_position = r + (-car.global_basis.x) * 0.6
	await frames(2)
	await tap("enter_vehicle")
	await seconds(car.enter_duration() + 0.3)
	check(car.state == Vehicle.State.DRIVING, "re-enter from the right side works")
	var wall_r := _block(r)
	var blocked := [false]
	car.exit_blocked.connect(func(): blocked[0] = true, CONNECT_ONE_SHOT)
	await frames(2)
	await tap("enter_vehicle")
	await seconds(car.exit_duration() + 0.1)
	check(blocked[0] and player.vehicle == car and car.state == Vehicle.State.DRIVING, "both exits blocked -> exit_blocked, player stays in")
	wall_l.queue_free()
	wall_r.queue_free()
	await frames(2)

# --- 7. crash --------------------------------------------------------------------

func test_crash_damage() -> void:
	# Driver still in. Put the car 25 m in front of the crash wall and floor it.
	car.global_transform = Transform3D(Basis.IDENTITY, Vector3(-40.0, 0.02, 35.0))
	car.linear_velocity = Vector3.ZERO
	car.angular_velocity = Vector3.ZERO
	await frames(10)
	var hits := []
	car.crashed.connect(func(dv, dmg): hits.append([dv, dmg]))
	var h0 := car.health
	Input.action_press("vehicle_accelerate")
	var n := 0
	while hits.is_empty() and n < int(8 * HZ):
		await frames(1)
		n += 1
	Input.action_release("vehicle_accelerate")
	check(not hits.is_empty() and car.health < h0, "wall impact -> crashed (dv %.1f m/s), health %.0f -> %.0f" % [hits[0][0] if hits.size() else 0.0, h0, car.health])
	await seconds(1.0)
	check(car.global_position.z < 60.0, "car did not pass through the wall")

func test_steering_math() -> void:
	var d := car.data
	check(approx(d.get_max_steer_deg(0.0), d.steer_max_deg, 0.001) and approx(d.get_max_steer_deg(40.0), d.steer_min_deg, 0.001),
		"speed-dependent steering %.0f deg -> %.0f deg" % [d.get_max_steer_deg(0.0), d.get_max_steer_deg(40.0)])
	check(d.power_factor(0.0) == 1.0 and d.power_factor(d.top_speed) == 0.0, "drive force fades to 0 at top speed")

# --- 8. negative controls: sabotaged copies MUST be detected -------------------------

func test_negative_controls() -> void:
	# a) wrong wheel radius in the data -> assembly error.
	var bad_data := (load("res://Data/Vehicles/VH_Sedan_01.tres") as VehicleData).duplicate()
	bad_data.wheel_radius = 0.30
	var bad := (load(SEDAN) as PackedScene).instantiate() as Vehicle
	bad.data = bad_data
	range_scene.add_child(bad)
	bad.global_position = Vector3(30, 0.05, 0)
	await frames(2)
	var caught := false
	for e in bad.assembly_errors:
		caught = caught or e.contains("wheel_radius")
	check(caught, "NEGATIVE: wheel_radius 0.30 vs asset 0.34 is reported %s" % bad.assembly_errors)
	bad.queue_free()
	# b) engine force cut to 15 % -> the 3 s acceptance criterion must fail.
	var weak_data := (load("res://Data/Vehicles/VH_Sedan_01.tres") as VehicleData).duplicate()
	weak_data.engine_force *= 0.15
	var weak := (load(SEDAN) as PackedScene).instantiate() as Vehicle
	weak.data = weak_data
	range_scene.add_child(weak)
	weak.global_position = Vector3(-60, 0.05, -100)
	await seconds(1.0)
	weak.set_controls(1.0, 0.0, 0.0)
	await seconds(3.0)
	check(weak.forward_speed < 8.0, "NEGATIVE: 15 %% engine fails the 3 s > 8 m/s criterion (%.1f m/s)" % weak.forward_speed)
	weak.queue_free()
	await frames(2)
