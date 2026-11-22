# UNDERWORLD - headless gameplay tests for the third-person controller (T-GP-01).
# Run (via Tests/run_gameplay_tests.sh, which imports first so class_names resolve):
#   godot --headless --fixed-fps 60 --path GodotProject --script res://Tests/test_player_controller.gd
# --fixed-fps 60 makes every frame exactly one 1/60 s physics step -> deterministic.
# Input is simulated with Input.action_press()/action_release() on the real InputMap
# actions, and mouse look with Viewport.push_input(InputEventMouseMotion).
# Prints [GPTEST][PASS]/[FAIL] lines; exits 0 on PASS, 1 on any failure.
extends SceneTree

const TEST_RANGE := "res://Scenes/Test/PT_PlayerTestRange.tscn"
const PLAYER := "res://Scenes/Player/Player.tscn"
const MAIN := "res://Scenes/Main.tscn"
const HZ := 60.0
const REQUIRED_ACTIONS := ["move_forward", "move_back", "move_left", "move_right", "look_left",
	"look_right", "look_up", "look_down", "sprint", "walk", "crouch", "jump", "aim", "fire",
	"reload", "interact", "enter_vehicle", "shoulder_swap", "pause"]
const WATCHDOG_FRAMES := 60 * 120

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

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames > WATCHDOG_FRAMES and not _done:
		print("[GPTEST][FAIL] watchdog: tests did not finish in %d frames" % WATCHDOG_FRAMES)
		quit(1)
	return false

func frames(n: int) -> void:
	for i in n:
		await physics_frame

func seconds(s: float) -> void:
	await frames(int(round(s * HZ)))

func release_all() -> void:
	for a in REQUIRED_ACTIONS:
		Input.action_release(a)

## Press for exactly one physics frame (for just_pressed actions).
func tap(action: String) -> void:
	Input.action_press(action)
	await frames(1)
	Input.action_release(action)
	await frames(1)

func spawn(path: String) -> Node:
	var packed: PackedScene = load(path)
	var scene := packed.instantiate()
	root.add_child(scene)
	return scene

func despawn(scene: Node) -> void:
	release_all()
	scene.queue_free()
	await frames(2)

func teleport(p: PlayerController, pos: Vector3) -> void:
	p.global_position = pos
	p.velocity = Vector3.ZERO
	await frames(2)

func _run_all() -> void:
	await frames(1)
	await test_scene_loads()
	await test_gravity_and_landing()
	await test_move_forward_10m()
	await test_camera_relative_movement()
	await test_walk_run_sprint_speeds()
	await test_jump()
	await test_aim_mode()
	await test_mouse_and_stick_look()
	await test_spring_arm_collision()
	await test_crouch_and_low_ceiling()
	await test_slope()
	await test_stairs_up_and_down()
	await test_step_and_ledge()
	await test_no_penetration_main_scene()
	await test_animation_tree_contract()
	_done = true
	if failures.is_empty():
		print("[GPTEST] RESULT: PASS")
		quit(0)
	else:
		print("[GPTEST] RESULT: FAIL (%d)" % failures.size())
		for f in failures:
			print("[GPTEST]   - ", f)
		quit(1)

func _has_joy_button(action: String, button: JoyButton) -> bool:
	for e in InputMap.action_get_events(action):
		if e is InputEventJoypadButton and e.button_index == button:
			return true
	return false

func _has_key(action: String, k: Key) -> bool:
	for e in InputMap.action_get_events(action):
		if e is InputEventKey and e.physical_keycode == k:
			return true
	return false

# --- tests ----------------------------------------------------------------

func test_scene_loads() -> void:
	print("[GPTEST] == scene loads")
	for a in REQUIRED_ACTIONS:
		check(InputMap.has_action(a) and not InputMap.action_get_events(a).is_empty(), "input action '%s' defined with events" % a)
	# TD-010 gamepad layout: A = jump only, Y = interact + enter_vehicle, keyboard E/F.
	check(_has_joy_button("jump", JOY_BUTTON_A) and _has_key("jump", KEY_SPACE), "jump = Space / gamepad A")
	check(_has_joy_button("interact", JOY_BUTTON_Y) and _has_key("interact", KEY_E), "interact = E / gamepad Y")
	check(_has_joy_button("enter_vehicle", JOY_BUTTON_Y) and _has_key("enter_vehicle", KEY_F), "enter_vehicle = F / gamepad Y")
	var a_users := REQUIRED_ACTIONS.filter(func(a): return _has_joy_button(a, JOY_BUTTON_A))
	check(a_users == ["jump"], "gamepad A bound to jump only (got %s)" % [a_users])
	var packed: PackedScene = load(TEST_RANGE)
	check(packed != null, "PT_PlayerTestRange.tscn loads")
	var scene := spawn(TEST_RANGE)
	await frames(2)
	var p := scene.get_node_or_null("Player") as PlayerController
	check(p != null, "Player is a PlayerController (CharacterBody3D)")
	if p == null:
		await despawn(scene)
		return
	check(p.camera_rig is CameraRig, "CameraRig attached")
	check(p.visual is CharacterVisual, "CharacterVisual attached")
	check(p.camera_rig.spring_arm is SpringArm3D, "SpringArm3D present")
	check(p.camera_rig.camera == root.get_viewport().get_camera_3d(), "player camera is the current camera")
	var shape := p.get_node("CollisionShape3D").shape as CylinderShape3D
	check(shape != null and approx(shape.height, 1.8, 0.001) and approx(shape.radius, 0.35, 0.001), "collision cylinder 1.8 m x r0.35")
	check(p.get_node_or_null("Visual/PT_Capsule") is MeshInstance3D, "PT_ capsule stand-in mesh present")
	await despawn(scene)

func test_gravity_and_landing() -> void:
	print("[GPTEST] == gravity + landing")
	var scene := spawn(TEST_RANGE)
	var p := scene.get_node("Player") as PlayerController
	await frames(1)
	var landed := []
	p.landed.connect(func(v): landed.append(v))
	await teleport(p, Vector3(0, 3, 0))
	check(not p.is_on_floor(), "airborne after spawning at y=3")
	var min_vy := 0.0
	var t := 0
	while not p.is_on_floor() and t < 180:
		min_vy = minf(min_vy, p.velocity.y)
		await frames(1)
		t += 1
	check(p.is_on_floor(), "lands on floor within 3 s (took %.2f s)" % (t / HZ))
	check(min_vy < -5.0, "fell under gravity (min vy %.2f m/s)" % min_vy)
	check(landed.size() == 1, "landed signal emitted once (got %d)" % landed.size())
	await frames(30)
	check(approx(p.global_position.y, 0.0, 0.05), "rests at floor height y=%.3f" % p.global_position.y)
	var before := p.global_position
	await frames(60)
	check(p.global_position.distance_to(before) < 0.01, "stable when idle (drift %.4f m)" % p.global_position.distance_to(before))
	check(p.move_state == PlayerController.MoveState.IDLE, "move state IDLE")
	await despawn(scene)

func test_move_forward_10m() -> void:
	print("[GPTEST] == move 10 m forward")
	var scene := spawn(TEST_RANGE)
	var p := scene.get_node("Player") as PlayerController
	await frames(10)
	var start := p.global_position
	Input.action_press("move_forward")
	var t := 0
	while start.distance_to(p.global_position) < 10.0 and t < 600:
		await frames(1)
		t += 1
	var speed := p.get_planar_speed()
	Input.action_release("move_forward")
	await frames(40)
	var d := p.global_position - start
	check(-d.z >= 10.0, "moved >= 10 m forward (-Z, camera forward): dz=%.2f in %.2f s" % [d.z, t / HZ])
	check(-d.z < 10.8, "stops after release (overshoot %.2f m)" % (-d.z - 10.0))
	check(absf(d.x) < 0.05 and approx(p.global_position.y, 0.0, 0.05), "no sideways/vertical drift (dx=%.3f y=%.3f)" % [d.x, p.global_position.y])
	check(approx(speed, p.run_speed, 0.1), "default keyboard speed = run %.2f m/s (got %.2f)" % [p.run_speed, speed])
	check(p.get_facing_direction().dot(Vector3.FORWARD) > 0.99, "visual faces move direction (-Z)")
	check(p.get_planar_speed() < 0.01, "decelerates to stop")
	await despawn(scene)

func test_camera_relative_movement() -> void:
	print("[GPTEST] == camera-relative movement")
	var scene := spawn(TEST_RANGE)
	var p := scene.get_node("Player") as PlayerController
	await frames(5)
	p.camera_rig.set_yaw(PI / 2.0)  # camera turned 90° left -> forward is -X
	var start := p.global_position
	Input.action_press("move_forward")
	await seconds(1.0)
	Input.action_release("move_forward")
	var d := p.global_position - start
	check(d.x < -2.0 and absf(d.z) < 0.05, "forward follows camera yaw (d=%s)" % d)
	await frames(40)  # let it decelerate to a stop
	start = p.global_position
	Input.action_press("move_right")
	await seconds(1.0)
	Input.action_release("move_right")
	d = p.global_position - start
	check(d.z < -2.0 and absf(d.x) < 0.05, "right strafes relative to camera (d=%s)" % d)
	await despawn(scene)

func _steady_speed(p: PlayerController, actions: Array) -> float:
	for a in actions:
		Input.action_press(a)
	await seconds(1.5)
	var s := p.get_planar_speed()
	for a in actions:
		Input.action_release(a)
	await seconds(1.0)
	return s

func test_walk_run_sprint_speeds() -> void:
	print("[GPTEST] == walk/run/sprint")
	var scene := spawn(TEST_RANGE)
	var p := scene.get_node("Player") as PlayerController
	await frames(5)
	p.camera_rig.set_yaw(PI)  # run towards +Z (open floor)
	await teleport(p, Vector3(0, 0, -20))
	var states := []
	p.move_state_changed.connect(func(s): states.append(s))
	var walk: float = await _steady_speed(p, ["move_forward", "walk"])
	check(approx(walk, p.walk_speed, 0.05), "walk = %.2f m/s (got %.2f)" % [p.walk_speed, walk])
	await teleport(p, Vector3(0, 0, -20))
	var sprint: float = await _steady_speed(p, ["move_forward", "sprint"])
	check(approx(sprint, p.sprint_speed, 0.1), "sprint = %.2f m/s (got %.2f)" % [p.sprint_speed, sprint])
	check(states.has(PlayerController.MoveState.SPRINT) and states.has(PlayerController.MoveState.WALK), "move states WALK and SPRINT reported")
	await teleport(p, Vector3(0, 0, -20))
	p.can_sprint = false
	var blocked: float = await _steady_speed(p, ["move_forward", "sprint"])
	check(approx(blocked, p.run_speed, 0.1), "can_sprint=false caps at run (got %.2f)" % blocked)
	p.can_sprint = true
	# Analog stick: half deflection -> walk-ish speed.
	await teleport(p, Vector3(0, 0, -20))
	Input.action_press("move_forward", 0.4)
	await seconds(1.5)
	var analog := p.get_planar_speed()
	Input.action_release("move_forward")
	check(analog > 0.3 and analog < p.walk_speed + 0.01, "analog 40%% stick -> slow walk (got %.2f)" % analog)
	await despawn(scene)

func test_jump() -> void:
	print("[GPTEST] == jump")
	var scene := spawn(TEST_RANGE)
	var p := scene.get_node("Player") as PlayerController
	await frames(20)
	var jumped := [0]
	var landed := [0]
	p.jumped.connect(func(): jumped[0] += 1)
	p.landed.connect(func(_v): landed[0] += 1)
	Input.action_press("jump")
	await frames(1)
	Input.action_release("jump")
	var peak := 0.0
	var t := 0
	while t < 120:
		await frames(1)
		t += 1
		peak = maxf(peak, p.global_position.y)
		if t > 5 and p.is_on_floor():
			break
	check(jumped[0] == 1, "jumped signal once")
	check(approx(peak, p.jump_height, 0.12), "jump apex %.2f m (target %.2f)" % [peak, p.jump_height])
	check(p.is_on_floor() and landed[0] == 1, "lands again after %.2f s" % (t / HZ))
	await despawn(scene)

func test_aim_mode() -> void:
	print("[GPTEST] == aim mode")
	var scene := spawn(TEST_RANGE)
	var p := scene.get_node("Player") as PlayerController
	var rig := p.camera_rig
	await frames(10)
	rig.pitch = 0.0
	rig.apply_look(Vector2.ZERO)
	await frames(2)
	check(rig.aim_blend == 0.0 and approx(rig.spring_arm.spring_length, rig.arm_length, 0.01) and approx(rig.camera.fov, rig.fov, 0.01), "explore framing (arm %.2f, fov %.1f)" % [rig.spring_arm.spring_length, rig.camera.fov])
	var changes := []
	p.aim_changed.connect(func(a): changes.append(a))
	Input.action_press("aim")
	await seconds(0.6)
	check(p.is_aiming and changes == [true], "aim toggles on with 'aim' action")
	check(rig.aim_blend > 0.99, "aim blend reached (%.3f)" % rig.aim_blend)
	check(approx(rig.spring_arm.spring_length, rig.aim_arm_length, 0.02), "spring arm zoomed in to %.2f m" % rig.spring_arm.spring_length)
	check(approx(rig.camera.fov, rig.aim_fov, 0.2), "fov narrowed to %.1f" % rig.camera.fov)
	check(approx(rig.spring_arm.position.x, rig.aim_shoulder_offset, 0.02), "over-shoulder offset %.2f m (right)" % rig.spring_arm.position.x)
	# Crosshair ray straight ahead hits the AimWall (front face z = -30).
	check(p.aim_collider != null and String(p.aim_collider.name) == "AimWall", "crosshair ray hits AimWall (got %s)" % [p.aim_collider])
	check(approx(p.aim_point.z, -30.0, 0.05), "aim point on wall face z=%.2f" % p.aim_point.z)
	# Character faces the aim direction even when the camera turns.
	rig.apply_look(Vector2(0.6, 0.0))  # yaw right by 0.6 rad
	await seconds(0.5)
	var cam_fwd := -rig.get_planar_basis().z
	check(p.get_facing_direction().dot(cam_fwd) > 0.995, "character faces aim direction (dot %.4f)" % p.get_facing_direction().dot(cam_fwd))
	# Movement while aiming is capped and sprint is blocked.
	Input.action_press("move_right")
	Input.action_press("sprint")
	await seconds(1.0)
	check(approx(p.get_planar_speed(), p.aim_move_speed, 0.1) and not p.is_sprinting, "aim strafe %.2f m/s, no sprint" % p.get_planar_speed())
	check(p.get_facing_direction().dot(cam_fwd) > 0.99, "keeps facing aim while strafing")
	Input.action_release("move_right")
	Input.action_release("sprint")
	# Shoulder swap.
	await tap("shoulder_swap")
	await seconds(0.3)
	check(rig.shoulder_side < 0.0 and rig.spring_arm.position.x < -0.5, "shoulder swap -> left shoulder (x=%.2f)" % rig.spring_arm.position.x)
	Input.action_release("aim")
	await seconds(0.8)
	check(not p.is_aiming and changes == [true, false], "aim toggles off on release")
	check(rig.aim_blend == 0.0 and approx(rig.spring_arm.spring_length, rig.arm_length, 0.01) and approx(rig.camera.fov, rig.fov, 0.01), "explore framing restored")
	await despawn(scene)

func test_mouse_and_stick_look() -> void:
	print("[GPTEST] == mouse + stick look")
	var scene := spawn(TEST_RANGE)
	var p := scene.get_node("Player") as PlayerController
	var rig := p.camera_rig
	await frames(5)
	rig.require_mouse_capture = false  # no real mouse capture in headless
	var yaw0 := rig.yaw
	var pitch0 := rig.pitch
	var ev := InputEventMouseMotion.new()
	ev.relative = Vector2(100, -40)
	root.push_input(ev)
	await frames(2)
	check(approx(rig.yaw, yaw0 - 100 * rig.mouse_sensitivity, 0.001), "mouse right -> yaw right (%.3f -> %.3f)" % [yaw0, rig.yaw])
	check(approx(rig.pitch, pitch0 + 40 * rig.mouse_sensitivity, 0.001), "mouse up -> pitch up (%.3f -> %.3f)" % [pitch0, rig.pitch])
	var yaw1 := rig.yaw
	Input.action_press("look_left", 1.0)
	await seconds(0.5)
	Input.action_release("look_left")
	check(approx(rig.yaw - yaw1, rig.stick_look_speed * 0.5, 0.06), "right stick left -> yaw +%.2f rad (got %.2f)" % [rig.stick_look_speed * 0.5, rig.yaw - yaw1])
	rig.apply_look(Vector2(0, 10))
	check(approx(rig.pitch, deg_to_rad(rig.max_pitch_deg), 0.001), "pitch clamped at max")
	await despawn(scene)

func test_spring_arm_collision() -> void:
	print("[GPTEST] == spring arm camera collision")
	var scene := spawn(TEST_RANGE)
	var p := scene.get_node("Player") as PlayerController
	var rig := p.camera_rig
	await frames(5)
	await teleport(p, Vector3(0, 0, -28.8))  # back to the AimWall (face z=-30)
	rig.set_yaw(PI)  # camera looks +Z, so the arm points into the wall
	await frames(10)
	var hit := rig.spring_arm.get_hit_length()
	check(hit < 1.5, "spring arm shortened by wall behind (hit length %.2f m of %.2f)" % [hit, rig.spring_arm.spring_length])
	check(rig.camera.global_position.z > -30.0, "camera stays in front of the wall (z=%.2f)" % rig.camera.global_position.z)
	rig.set_yaw(0.0)
	await frames(10)
	check(approx(rig.spring_arm.get_hit_length(), rig.arm_length, 0.01), "full arm length in open space (%.2f)" % rig.spring_arm.get_hit_length())
	await despawn(scene)

func test_crouch_and_low_ceiling() -> void:
	print("[GPTEST] == crouch + low ceiling")
	var scene := spawn(TEST_RANGE)
	var p := scene.get_node("Player") as PlayerController
	var shape := p.get_node("CollisionShape3D").shape as CylinderShape3D
	await frames(5)
	# Standing: tunnel (ceiling underside 1.4 m) blocks.
	await teleport(p, Vector3(-12, 0, -4))
	Input.action_press("move_forward")
	await seconds(2.0)
	Input.action_release("move_forward")
	check(p.global_position.z > -7.0 + 0.3, "standing capsule blocked by 1.4 m ceiling (z=%.2f)" % p.global_position.z)
	check(p.global_position.y < 0.05, "did not climb the tunnel (y=%.2f)" % p.global_position.y)
	await tap("crouch")
	check(p.is_crouching and approx(shape.height, p.crouch_height, 0.001), "crouch toggles on, capsule %.2f m" % shape.height)
	Input.action_press("move_forward")
	await seconds(3.0)
	var cspeed := p.get_planar_speed()
	Input.action_release("move_forward")
	await frames(20)
	check(approx(cspeed, p.crouch_speed, 0.05), "crouch speed %.2f (got %.2f)" % [p.crouch_speed, cspeed])
	check(p.global_position.z < -8.0, "crouched capsule fits under ceiling (z=%.2f)" % p.global_position.z)
	check(not p.can_stand_up(), "can_stand_up() false under ceiling")
	await tap("crouch")
	check(p.is_crouching, "cannot stand up under ceiling")
	await tap("jump")
	check(p.is_crouching and p.global_position.y < 0.05, "jump under ceiling does not stand/jump")
	Input.action_press("move_back")
	await seconds(4.0)
	Input.action_release("move_back")
	await frames(10)
	await tap("crouch")
	check(not p.is_crouching and approx(shape.height, p.stand_height, 0.001), "stands up outside tunnel (z=%.2f)" % p.global_position.z)
	await despawn(scene)

func test_slope() -> void:
	print("[GPTEST] == slope 20°")
	var scene := spawn(TEST_RANGE)
	var p := scene.get_node("Player") as PlayerController
	await frames(5)
	await teleport(p, Vector3(14, 0, 1))
	Input.action_press("move_forward")
	await seconds(2.5)
	var on_floor := p.is_on_floor()
	var y := p.global_position.y
	Input.action_release("move_forward")
	check(y > 1.0 and on_floor, "walks up 20° ramp (y=%.2f, on_floor=%s)" % [y, on_floor])
	await frames(60)
	var y2 := p.global_position.y
	await frames(60)
	check(absf(p.global_position.y - y2) < 0.02, "does not slide down when idle on slope (dy=%.3f)" % (p.global_position.y - y2))
	await despawn(scene)

func test_stairs_up_and_down() -> void:
	print("[GPTEST] == stairs up/down (T-GP-01c)")
	var scene := spawn(TEST_RANGE)
	var p := scene.get_node("Player") as PlayerController
	await frames(5)
	var steps := []
	var landed := []
	p.stepped_up.connect(func(h): steps.append(h))
	p.landed.connect(func(v): landed.append(v))
	# Flat ground never triggers a step.
	await teleport(p, Vector3(-22, 0, 6))
	Input.action_press("move_forward")
	await seconds(1.0)
	check(steps.is_empty(), "no step-up on flat floor")
	# Walk up the 8 x 0.2 m flight onto the 1.6 m landing (landing spans z -2.4..-5.4).
	var air_frames := 0
	var t := 0
	var max_dip := 0.0  # largest frame-to-frame drop in y while climbing (pop = bad)
	var prev_y := p.global_position.y
	while p.global_position.z > -3.9 and t < 300:
		await frames(1)
		t += 1
		if not p.is_on_floor():
			air_frames += 1
		max_dip = maxf(max_dip, prev_y - p.global_position.y)
		prev_y = p.global_position.y
	Input.action_release("move_forward")
	await frames(30)
	check(approx(p.global_position.y, 1.6, 0.03) and p.global_position.z < -2.5, "climbed stairs onto landing (y=%.2f z=%.2f)" % [p.global_position.y, p.global_position.z])
	check(steps.size() == 8 and steps.all(func(h): return h > 0.15 and h < 0.25), "stepped up each 0.2 m riser (%d steps: %s)" % [steps.size(), steps])
	check(air_frames == 0 and landed.is_empty(), "grounded the whole way up (air frames %d, landings %d)" % [air_frames, landed.size()])
	check(max_dip < 0.03, "no step pops: max frame drop while climbing %.3f m" % max_dip)
	check(t < 180, "climb took %.2f s (no stalls at risers)" % (t / HZ))
	# Walk back down (camera turned around), at sprint speed: no hopping.
	p.camera_rig.set_yaw(PI)
	await teleport(p, Vector3(-22, 1.6, -4.0))
	await frames(10)
	landed.clear()
	air_frames = 0
	var max_drop_speed := 0.0
	Input.action_press("move_forward")
	Input.action_press("sprint")
	for i in 90:
		await frames(1)
		if not p.is_on_floor():
			air_frames += 1
		max_drop_speed = maxf(max_drop_speed, -p.velocity.y)
	Input.action_release("move_forward")
	Input.action_release("sprint")
	await frames(30)
	check(approx(p.global_position.y, 0.0, 0.03) and p.global_position.z > 0.5, "walked down to the floor (y=%.2f z=%.2f)" % [p.global_position.y, p.global_position.z])
	check(air_frames == 0 and landed.is_empty(), "stays grounded walking down at sprint speed (air frames %d, landings %d)" % [air_frames, landed.size()])
	# A real drop (1.6 m off the landing's side) still falls and lands.
	p.camera_rig.set_yaw(-PI / 2.0)  # forward = +X
	await teleport(p, Vector3(-22, 1.6, -4.0))
	await frames(5)
	landed.clear()
	Input.action_press("move_forward")
	await seconds(1.5)
	Input.action_release("move_forward")
	check(landed.size() == 1 and approx(p.global_position.y, 0.0, 0.03), "walking off a 1.6 m edge falls and lands (landings %d, y=%.2f)" % [landed.size(), p.global_position.y])
	await despawn(scene)

func test_step_and_ledge() -> void:
	print("[GPTEST] == 0.3 m step vs 0.5 m ledge (T-GP-01c)")
	var scene := spawn(TEST_RANGE)
	var p := scene.get_node("Player") as PlayerController
	await frames(5)
	var steps := []
	p.stepped_up.connect(func(h): steps.append(h))
	await teleport(p, Vector3(-32, 0, 1))
	Input.action_press("move_forward")
	await seconds(1.5)
	Input.action_release("move_forward")
	await frames(20)
	check(approx(p.global_position.y, 0.3, 0.03) and steps.size() == 1, "walks onto 0.3 m step (y=%.2f, steps %s)" % [p.global_position.y, steps])
	steps.clear()
	await teleport(p, Vector3(-28, 0, 1))
	Input.action_press("move_forward")
	Input.action_press("sprint")
	var max_y := 0.0
	for i in 120:
		await frames(1)
		max_y = maxf(max_y, p.global_position.y)
	Input.action_release("move_forward")
	Input.action_release("sprint")
	check(max_y < 0.05 and steps.is_empty(), "0.5 m ledge blocks (max y=%.3f, steps %d)" % [max_y, steps.size()])
	check(p.global_position.z > -2.0 + p.capsule_radius - 0.03, "stopped at the ledge face (z=%.2f)" % p.global_position.z)
	# Jumping onto the ledge still works (jump apex 1.0 m > 0.5 m).
	Input.action_press("move_forward")
	await tap("jump")
	await seconds(1.0)
	Input.action_release("move_forward")
	await frames(20)
	check(approx(p.global_position.y, 0.5, 0.03), "can jump onto the 0.5 m ledge (y=%.2f)" % p.global_position.y)
	# Walls are never climbed: run into the 3 m pillar and the 1.5 m crate.
	steps.clear()
	await teleport(p, Vector3(6, 0, 7))
	Input.action_press("move_forward")
	await seconds(1.5)
	Input.action_release("move_forward")
	check(steps.is_empty() and p.global_position.y < 0.05, "no climbing the pillar wall (y=%.2f)" % p.global_position.y)
	await despawn(scene)

func test_no_penetration_main_scene() -> void:
	print("[GPTEST] == Main.tscn ground + PT crate collision")
	var main := spawn(MAIN)
	var p := (load(PLAYER) as PackedScene).instantiate() as PlayerController
	main.add_child(p)
	await frames(2)
	await teleport(p, Vector3(0, 0.5, 4))  # crate is 1x1x1 m at the origin
	Input.action_press("move_forward")
	Input.action_press("sprint")
	var min_y := 99.0
	var min_z := 99.0
	for i in 240:
		await frames(1)
		min_y = minf(min_y, p.global_position.y)
		min_z = minf(min_z, p.global_position.z)
	Input.action_release("move_forward")
	Input.action_release("sprint")
	check(min_y > -0.05, "never sinks into Main ground (min y=%.3f)" % min_y)
	check(min_z >= 0.5 + p.capsule_radius - 0.03, "stopped by PT crate, no penetration (min z=%.3f, limit %.2f)" % [min_z, 0.5 + p.capsule_radius])
	check(p.global_position.y < 0.05, "did not climb the 1 m crate")
	main.queue_free()
	await frames(2)

func _dummy_model(clips: Array) -> PackedScene:
	var m := Node3D.new()
	m.name = "PT_DummyModel"
	var ap := AnimationPlayer.new()
	ap.name = "AnimationPlayer"
	m.add_child(ap)
	ap.owner = m
	var lib := AnimationLibrary.new()
	for c in clips:
		var a := Animation.new()
		a.length = 1.0
		a.loop_mode = Animation.LOOP_LINEAR
		lib.add_animation(c, a)
	ap.add_animation_library("", lib)
	var ps := PackedScene.new()
	ps.pack(m)
	m.free()
	return ps

func test_animation_tree_contract() -> void:
	print("[GPTEST] == model swap + AnimationTree contract (dummy clips)")
	var scene := spawn(TEST_RANGE)
	var p := scene.get_node("Player") as PlayerController
	await frames(5)
	p.visual.set_model(_dummy_model(CharacterVisual.CLIP_NAMES.values()))
	await frames(2)
	var tree := p.visual.animation_tree
	check(tree != null and tree.active, "AnimationTree built from model's AnimationPlayer")
	check(p.visual.missing_clips.is_empty(), "all required clip names resolved")
	check(not (p.get_node("Visual/PT_Capsule") as Node3D).visible, "PT capsule hidden when a model is set")
	Input.action_press("move_forward")
	await seconds(1.0)
	var bp: float = tree.get("parameters/loco/blend_position")
	check(approx(bp, p.get_planar_speed(), 0.01) and bp > 3.0, "loco blend_position follows speed (%.2f)" % bp)
	Input.action_press("aim")
	await seconds(0.8)
	check(float(tree.get("parameters/aim/blend_amount")) > 0.95, "aim blend amount driven")
	var strafe: Vector2 = tree.get("parameters/aim_loco/blend_position")
	check(strafe.y > 0.9, "aim_loco blend = forward while walking forward (%s)" % strafe)
	Input.action_release("aim")
	Input.action_release("move_forward")
	await frames(30)
	await tap("jump")
	check(bool(tree.get("parameters/jump/active")), "jump_start OneShot fired on jump")
	await seconds(1.2)
	check(p.is_on_floor() and float(tree.get("parameters/air/blend_amount")) < 0.05, "air blend back to 0 after landing")
	# A model with only idle reports the missing slots instead of failing
	# (the WARNING "model is missing clips" printed here is expected).
	p.visual.animation_tree.queue_free()
	p.visual.animation_tree = null
	p.visual.missing_clips.clear()
	p.visual.set_model(_dummy_model(["A_Jason_Idle"]))
	await frames(2)
	check(p.visual.missing_clips.size() == CharacterVisual.CLIP_NAMES.size() - 1, "missing clips reported (%d)" % p.visual.missing_clips.size())
	await despawn(scene)
