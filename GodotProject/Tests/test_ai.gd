# UNDERWORLD - headless AI tests (T-AI-01 enemies, T-AI-02 baseline civilians).
# Layers (ForgeSkills gamedev-game-testing): 1 pure perception/accuracy math, 2 state machine +
# T-AI-03 in-car targeting: a seated player is represented by his car (TD-015), so gunmen aim
# at the vehicle and hits go to Vehicle.health. Negative control UW_AI_SABOTAGE=incar restores
# the old behaviour (aim at the player's capsule) -> the ordinary in-car checks FAIL.
# profile tables, 3 integration in res://Scenes/Test/PT_AITestRange.tscn (navmesh, LOS, hearing,
# cover, shooting, damage, death, civilians). Run via Tests/run_gameplay_tests.sh (fixed 60 fps).
# Arena: gunmen at (-3,0,36) (3,0,36) (0,0,37.5) facing -Z; CoverWall_A/B at z 24 (x -5 / 5),
# CoverWall_C at z 30, 1.25 m high; civilians on Route_A (x -30..-18) and Route_B (x 16..28).
extends SceneTree

const AI_RANGE := "res://Scenes/Test/PT_AITestRange.tscn"
const GUNMAN := "res://Data/AI/AI_Gunman_Cartel.tres"
const CIVILIAN := "res://Data/AI/AI_Civilian.tres"
const COWARD := "res://Tests/Data/PT_AI_Coward.tres"
const PISTOL := "res://Data/Weapons/WPN_Pistol_01.tres"
const HZ := 60.0
const FAR_AWAY := Vector3(0, 0, -20)      # > 40 m from every gunman, out of hearing + view range
const OPEN_SPOT := Vector3(0, 0, 12)      # in the open, ~24 m in front of the gunmen

var failures: Array[String] = []
var _frames := 0

func check(cond: bool, msg: String) -> void:
	print("[GPTEST][PASS] " if cond else "[GPTEST][FAIL] ", msg)
	if not cond:
		failures.append(msg)

func approx(a: float, b: float, tol: float) -> bool:
	return absf(a - b) <= tol

func _initialize() -> void:
	_run_all()

func _process(_d: float) -> bool:
	_frames += 1
	if _frames > 60 * 400:
		print("[GPTEST][FAIL] watchdog")
		quit(1)
	return false

func frames(n: int) -> void:
	for i in n:
		await physics_frame

func seconds(s: float) -> void:
	await frames(int(round(s * HZ)))

## Wait until cond() is true (checked every frame) or timeout; returns elapsed seconds or -1.
func wait_until(cond: Callable, timeout: float) -> float:
	var n := int(timeout * HZ)
	for i in n:
		if cond.call():
			return i / HZ
		await physics_frame
	return -1.0


# --- T-AI-03: enemies vs. the player in a car -------------------------------------

## Layer 1: the TD-015 rules as pure functions (no scene needed).
func test_vehicle_targeting_rules() -> void:
	print("[GPTEST] == T-AI-03 targeting rules (TD-015)")
	var fake := Node3D.new()
	check(VehicleTargeting.resolve(fake) == fake, "a target without a vehicle resolves to itself")
	check(VehicleTargeting.vehicle_of(fake) == null, "no vehicle for a target on foot")
	fake.free()


## Layer 3: real gunmen vs. a real car. The car is placed in the range, Jason is seated, and we
## count what the gunmen actually shoot at and how the damage is booked.
func test_incar_targeting() -> void:
	print("[GPTEST] == T-AI-03 enemies target the car, not the hidden player")
	await setup(["Gunman_1"], false)
	var g := gunmen()[0] as NPCController
	var car_scene := load("res://Scenes/Vehicles/VH_Sedan_01.tscn") as PackedScene
	var car := car_scene.instantiate() as Vehicle
	root.add_child(car)
	# Put the car where the gunmen can actually see it: OPEN_SPOT is the spot the detection
	# test uses, so line of sight is guaranteed by an existing passing test.
	car.global_position = OPEN_SPOT + Vector3(0, 0.1, 0)
	await frames(6)
	# Seat Jason: the real enter path (car.enter) needs him next to an exit socket.
	player.global_position = car.get_socket(&"SOCKET_Exit_Left").global_position
	await frames(2)
	check(car.enter(player), "Jason entered the car for the in-car targeting test")
	await seconds(1.0)
	check(player.vehicle == car and car.driver == player, "Jason is seated and the car knows him")
	# Perception now resolves Jason -> the car.
	check(VehicleTargeting.resolve(player) == car, "a seated player resolves to his vehicle")
	var pts := g.target_points(player)
	check(pts.size() >= 2 and pts[1].distance_to(car.global_position) < 4.0,
		"gunman aim points are on the car (%.2f m from its centre)" % pts[1].distance_to(car.global_position))
	check(pts[1].distance_to(player.global_position) > 0.8,
		"aim points are NOT the player's hidden capsule (%.2f m away)" % pts[1].distance_to(player.global_position))
	# Let him see and shoot.
	g.rng_seed = 4242
	g.awareness = 1.0
	g.send_event("target_spotted")
	var health_before := car.health
	var player_hp_before := player.health.health
	var shots := 0
	var car_shots := 0
	var t := 0.0
	while t < 8.0 and car.health >= health_before:
		await frames(1)
		t += 1.0 / HZ
		shots = g.shots_fired
		if g.target is Vehicle:
			car_shots += 1
	check(g.target is Vehicle, "the gunman's target IS the vehicle (not PlayerController)")
	check(car.health < health_before, "gunfire damaged the VEHICLE (%.0f -> %.0f HP)" % [health_before, car.health])
	check(shots > 0, "the gunman fired at the car (%d shots)" % shots)
	check(is_equal_approx(player.health.health, player_hp_before),
		"the hidden driver took NO damage through the bodywork (%.0f HP)" % player.health.health)
	# TD-015 R3: a hit on the driver's window DOES hurt him, by the configured fraction.
	var split := VehicleTargeting.split_damage(car, VehicleTargeting.car_points(car)[0], 100.0)
	check(is_equal_approx(float(split["driver"]), 100.0 * car.data.driver_window_fraction),
		"a driver-window hit transfers %.0f%% to the driver" % (car.data.driver_window_fraction * 100.0))
	check(split["channel"] == VehicleTargeting.CHANNEL_DRIVER, "window hits are reported as 'driver'")
	var body_split := VehicleTargeting.split_damage(car, car.global_position + Vector3(0, 0.2, -4.0), 100.0)
	check(is_equal_approx(float(body_split["driver"]), 0.0), "a body hit transfers nothing to the driver")
	# A wrecked car no longer shields its driver: the window channel closes with the car.
	car.health = 0.0
	var dead_split := VehicleTargeting.split_damage(car, VehicleTargeting.car_points(car)[0], 100.0)
	check(is_equal_approx(float(dead_split["driver"]), 0.0), "a wrecked car transfers nothing to the driver")
	car.health = health_before
	# R4: getting out makes him a person again.
	check(car.request_exit(), "exit accepted")
	await seconds(1.0)
	check(player.vehicle == null, "Jason left the seat")
	var resolved_after := VehicleTargeting.resolve(player)
	check(resolved_after == player, "on foot the target is the player again (R4)")
	g.awareness = 1.0
	await frames(10)
	await wait_until(func(): return g.target == player, 3.0)
	check(g.target == player, "the gunman re-targets the player after he got out")
	car.queue_free()
	await teardown()


# --- fixture -------------------------------------------------------------------
var scene: Node
var player: PlayerController
var ai: Node

## Fresh PT_AITestRange; NPCs not in `keep` are removed. Player parked far away (unseen, unheard).
func setup(keep: Array = [], invulnerable := true) -> void:
	scene = (load(AI_RANGE) as PackedScene).instantiate()
	ai = scene.get_node("AI")
	for n in ai.get_children():
		if n is NPCController:
			(n as NPCController).rng_seed = 4242 + n.get_index()
			if not keep.has(String(n.name)):
				ai.remove_child(n)
				n.free()
	root.add_child(scene)
	player = scene.get_node("Range/Player")
	await frames(1)
	player.health.invulnerable = invulnerable
	await teleport(FAR_AWAY)
	await frames(10)  # navigation map sync

func teardown() -> void:
	scene.queue_free()
	await frames(2)

func teleport(pos: Vector3) -> void:
	player.global_position = pos
	player.velocity = Vector3.ZERO
	await frames(1)

func npc(n: String) -> NPCController:
	return ai.get_node(n) as NPCController

func gunmen() -> Array:
	return ai.get_children().filter(func(n): return n is NPCController and n.profile.id == "AI_Gunman_Cartel")

## Player weapon fires one shot from its eye at a world point (zero-spread copy of the pistol data).
func player_shoot_at(pt: Vector3) -> Dictionary:
	var w: Weapon = player.get_node("WeaponController").weapon
	if w.data.spread_hip > 0.0:
		var d: WeaponData = w.data.duplicate()
		for k in ["spread_hip", "spread_aim", "spread_moving", "spread_airborne", "bloom_per_shot"]:
			d.set(k, 0.0)
		w.data = d
	w.cooldown = 0.0
	if w.ammo == 0:
		w.ammo = w.data.magazine_size
	w.is_reloading = false
	var eye := player.global_position + Vector3(0, 1.6, 0)
	return w.trigger(true, true, eye, (pt - eye).normalized(), {}, player, player.get_self_rids())

func _run_all() -> void:
	await frames(1)
	test_l1_perception_math()
	test_l1_accuracy_math()
	test_l2_state_machine()
	test_l2_profiles_validate()
	await test_scene_contract()
	await test_detection_within_2s()
	await test_los_blocked_and_view_cone()
	await test_hearing()
	await test_cover_selection_and_cycle()
	await test_cover_compromised()
	await test_enemies_deal_damage_and_accuracy()
	await test_moving_target_harder()
	await test_enemy_dies_after_hits()
	await test_shared_resources_independent()
	await test_civilians_route_and_flee()
	await test_data_driven_table()
	test_vehicle_targeting_rules()
	await test_incar_targeting()
	if failures.is_empty():
		print("[GPTEST] RESULT: PASS")
		quit(0)
	else:
		print("[GPTEST] RESULT: FAIL (%d)" % failures.size())
		for f in failures:
			print("[GPTEST]   - ", f)
		quit(1)

# --- layer 1: pure math ----------------------------------------------------------

func test_l1_perception_math() -> void:
	print("[GPTEST] == L1 perception math (view cone, awareness, hearing)")
	var eye := Vector3(0, 1.6, 0)
	var fwd := Vector3(0, 0, 1)
	check(AIPerception.in_view_cone(eye, fwd, Vector3(0, 1.2, 10), 120.0, 35.0), "target straight ahead is in the cone")
	check(not AIPerception.in_view_cone(eye, fwd, Vector3(0, 1.2, -10), 120.0, 35.0), "target behind is not")
	check(AIPerception.in_view_cone(eye, fwd, Vector3(10, 1.2, 10).rotated(Vector3.UP, deg_to_rad(-14)), 120.0, 35.0)
		and not AIPerception.in_view_cone(eye, fwd, Vector3(10, 1.2, 10).rotated(Vector3.UP, deg_to_rad(16)), 120.0, 35.0), "cone edge: 59° in, 61° out (fov 120)")
	check(not AIPerception.in_view_cone(eye, fwd, Vector3(0, 1.2, 36), 120.0, 35.0), "beyond view distance is not seen")
	var g := load(GUNMAN) as AIProfile
	var near := AIPerception.awareness_rate(3.0, g)
	var mid := AIPerception.awareness_rate(20.0, g)
	var far := AIPerception.awareness_rate(35.0, g)
	check(approx(near, 1.0 / g.detect_time_near, 1e-4) and approx(far, 1.0 / g.detect_time_far, 1e-4) and near > mid and mid > far, "awareness rate near %.2f > mid %.2f > far %.2f /s" % [near, mid, far])
	check(1.0 / far <= 2.0, "unaware gunman reaches full awareness at view distance in %.2f s (<= 2 s, T-AI-01)" % (1.0 / far))
	var c := load(CIVILIAN) as AIProfile
	check(AIPerception.can_hear(Vector3.ZERO, Vector3(0, 0, 24.9), 40.0, c) and not AIPerception.can_hear(Vector3.ZERO, Vector3(0, 0, 25.1), 40.0, c), "civilian hears gunshots up to 25 m (T-AI-02)")
	check(AIPerception.can_hear(Vector3.ZERO, Vector3(0, 0, 39.9), 40.0, g) and not AIPerception.can_hear(Vector3.ZERO, Vector3(0, 0, 40.1), 40.0, g), "gunman hears up to the pistol's 40 m noise radius")

func test_l1_accuracy_math() -> void:
	print("[GPTEST] == L1 AI accuracy (data-driven, worse than the player)")
	var g := load(GUNMAN) as AIProfile
	var still := AIPerception.aim_error_deg(g, 15.0, 0.0, 0.0)
	var moving := AIPerception.aim_error_deg(g, 15.0, 3.5, 0.0)
	var farther := AIPerception.aim_error_deg(g, 30.0, 0.0, 0.0)
	var focused := AIPerception.aim_error_deg(g, 15.0, 0.0, 10.0)
	check(moving > still and farther > still, "error grows with target speed (%.2f°) and distance (%.2f°) vs %.2f°" % [moving, farther, still])
	check(approx(focused, still * g.focus_min_factor, 1e-4), "focus shrinks error to x%.1f (%.2f°)" % [g.focus_min_factor, focused])
	var pistol := load(PISTOL) as WeaponData
	var best_ai := focused + pistol.spread_hip
	check(best_ai > pistol.spread_aim * 3.0, "best-case AI cone %.2f° (focused + hip spread) is far worse than the player's aimed %.2f°" % [best_ai, pistol.spread_aim])
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	var maxang := 0.0
	for i in 200:
		var d := AIPerception.apply_cone(Vector3.FORWARD, 3.0, rng)
		maxang = maxf(maxang, rad_to_deg(d.angle_to(Vector3.FORWARD)))
	check(maxang <= 3.0001 and maxang > 2.5, "apply_cone stays inside its half-angle (max %.2f° of 3°)" % maxang)

# --- layer 2: state machine ------------------------------------------------------

func test_l2_state_machine() -> void:
	print("[GPTEST] == L2 AIStateMachine")
	var t := {"a": {"go": "b", "self": "a"}, "b": {"back": "a"}, "*": {"die": "dead"}}
	var m := AIStateMachine.new(t, {"b": 1.0}, "a")
	var log: Array = []
	m.state_changed.connect(func(f, to, e): log.append("%s>%s:%s" % [f, to, e]))
	check(not m.send("unknown") and m.state == "a", "unknown event is ignored")
	check(m.send("go") and m.state == "b", "a --go--> b")
	m.tick(0.5)
	check(m.state == "b", "no timeout before 1 s")
	m.tick(0.6)
	check(m.state == "b" and log.size() == 1, "timeout without a 'timeout' row does nothing")
	m.table["b"]["timeout"] = "a"
	var m2 := AIStateMachine.new(m.table, {"b": 1.0}, "b")
	m2.tick(1.01)
	check(m2.state == "a", "b --timeout(1 s)--> a")
	m2.time_in_state = 5.0
	check(m2.send("self") and m2.state == "a" and m2.time_in_state == 0.0, "self-transition re-enters (timer reset)")
	check(m2.send("die") and m2.state == "dead", "'*' row applies in any state")
	check(m2.history.size() == 3, "history records transitions (%d)" % m2.history.size())

func test_l2_profiles_validate() -> void:
	print("[GPTEST] == L2 shipped profiles validate against NPCController.STATES")
	var known := PackedStringArray(NPCController.STATES)
	for path in [GUNMAN, CIVILIAN, COWARD]:
		var p := load(path) as AIProfile
		var errs := AIStateMachine.validate(p.transitions, p.state_timeouts, p.initial_state, known)
		check(errs.is_empty(), "%s table valid %s" % [p.id, errs])
	var bad := AIStateMachine.validate({"idle": {"heard_gunshot": "alret"}, "hiding": {}}, {"serch": 2.0}, "idle", known)
	check(bad.size() == 3, "validator catches typo'd states (%d errors: %s)" % [bad.size(), bad])
	var g := load(GUNMAN) as AIProfile
	var flow := ["idle", "alert", "engage", "take_cover", "in_cover"]
	var ok: bool = g.transitions["idle"]["heard_gunshot"] == "alert" and g.transitions["alert"]["target_spotted"] == "engage" \
		and g.transitions["engage"]["cover_found"] == "take_cover" and g.transitions["take_cover"]["arrived"] == "in_cover"
	check(ok, "gunman table implements %s" % [flow])

# --- layer 3: integration --------------------------------------------------------

func test_scene_contract() -> void:
	print("[GPTEST] == PT_AITestRange contract")
	await setup(["Gunman_1", "Gunman_2", "Gunman_3", "Civilian_1", "Civilian_2", "Civilian_3"])
	var gs := gunmen()
	var civs := ai.get_children().filter(func(n): return n is NPCController and n.profile.id == "AI_Civilian")
	check(gs.size() == 3 and civs.size() == 3, "3 PT gunmen + 3 PT civilians (%d / %d)" % [gs.size(), civs.size()])
	var region := scene.get_node_or_null("Range/PT_NavRegion") as NavigationRegion3D
	check(region != null and region.navigation_mesh.get_polygon_count() > 50, "NavigationRegion3D with baked navmesh")
	var g1 := npc("Gunman_1")
	var path := NavigationServer3D.map_get_path(g1.get_world_3d().navigation_map, g1.global_position, Vector3(-5, 0, 12), true)
	check(path.size() >= 2 and Vector2(path[-1].x, path[-1].z).distance_to(Vector2(-5, 12)) < 0.6, "nav path around the cover walls (%d points)" % path.size())
	var hb := g1.hitboxes.hitboxes
	var zones := hb.map(func(h): return h.zone)
	check(hb.size() == 5 and zones.count(Hitbox.Zone.HEAD) == 1 and zones.count(Hitbox.Zone.BODY) == 1 and zones.count(Hitbox.Zone.LIMB) == 3
		and hb.all(func(h): return h.collision_layer == 16 and h.get_receiver() == g1.health), "NPC hitboxes head/body/4 limbs... 5 zones on layer 5 -> its DamageReceiver")
	check(g1.collision_layer == 4 and g1.get_node("CollisionShape3D").shape is CylinderShape3D, "NPC body on layer 3 Characters, cylinder (TD-011)")
	check(g1.weapon != null and g1.weapon.data.id == "WPN_Pistol_01" and npc("Civilian_1").weapon == null, "gunman armed with WeaponData pistol, civilian unarmed")
	check(gs.all(func(g): return g.get_state() == "idle"), "gunmen idle while the player is far away")
	check(player.health != null and player.hitboxes != null and player.get_self_rids().size() == 6, "player has Health + 5 hitboxes, excluded from own shots/crosshair")
	await teardown()

func test_detection_within_2s() -> void:
	print("[GPTEST] == 3 gunmen detect the player within 2 s of LOS (T-AI-01 acceptance)")
	await setup(["Gunman_1", "Gunman_2", "Gunman_3"])
	await seconds(1.0)
	check(gunmen().all(func(g): return g.awareness == 0.0 and g.get_state() == "idle"), "no detection while out of range")
	var t0 := _frames
	var spotted := {}
	for g in gunmen():
		# Multi-line instead of a one-line "if x: y" lambda body: identical in GDScript, but
		# gdtoolkit's parser rejects the one-line form (false positive), and a test file that
		# trips the formatter hides real parse errors in the output.
		g.state_changed.connect(
			func(f, to, e):
				if e == "target_spotted" and not spotted.has(g.name):
					spotted[g.name] = (_frames - t0) / HZ
		)
	await teleport(OPEN_SPOT)
	await wait_until(func(): return spotted.size() == 3, 3.0)
	var times := spotted.values()
	check(spotted.size() == 3 and times.max() <= 2.0, "all 3 spotted the player at %s s" % [spotted])
	check(gunmen().all(func(g): return g.awareness >= 1.0 and g.has_last_known), "awareness full, last known position set")
	await teardown()

func test_los_blocked_and_view_cone() -> void:
	print("[GPTEST] == LOS blocked by cover, view cone")
	await setup(["Gunman_1"])
	var g := npc("Gunman_1")
	# Crouched behind CoverWall_A (z 24) on the far side from the gunman (z 36): hidden, 13 m away, inside the cone.
	player._set_crouching(true)  # crouch first: teleporting in standing would be seen for a frame
	await teleport(Vector3(-4, 0, 23.0))
	await seconds(3.0)
	check(not g.target_visible and g.awareness == 0.0 and g.get_state() == "idle", "crouched behind 1.25 m cover: not seen in 3 s (aw %.2f, %s)" % [g.awareness, g.get_state()])
	player._set_crouching(false)
	var t: float = await wait_until(func(): return g.awareness >= 1.0, 2.0)
	check(t >= 0.0, "standing up behind the same wall: seen and detected in %.2f s" % t)
	await teardown()
	await setup(["Gunman_1"])
	g = npc("Gunman_1")
	await teleport(g.global_position + Vector3(0, 0, 3.4))  # 3.4 m directly behind (gunman faces -Z)
	await seconds(2.0)
	check(not g.target_visible and g.get_state() == "idle", "player 3.4 m behind the gunman is outside the view cone")
	await teleport(g.global_position + Vector3(0, 0, 2.0))
	await frames(3)
	check(g.target_visible, "inside the 2.5 m near-awareness radius: noticed even from behind")
	await teardown()

func test_hearing() -> void:
	print("[GPTEST] == hearing gunshots -> alert -> investigate")
	await setup(["Gunman_1", "Gunman_2", "Gunman_3"])
	# 56 m away: out of hearing.
	player_shoot_at(player.global_position + Vector3(0, 30, -10))
	await seconds(0.5)
	check(gunmen().all(func(g): return g.get_state() == "idle"), "shot 56 m away is not heard")
	# Hidden behind CoverWall_A (crouched), ~13 m: heard, not seen.
	player._set_crouching(true)  # crouch first: teleporting in standing would be seen for a frame
	await teleport(Vector3(-4, 0, 23.0))
	await frames(5)
	var g := npc("Gunman_1")
	var d0 := g.global_position.distance_to(player.global_position)
	player_shoot_at(player.global_position + Vector3(0, 30, -10))
	await frames(2)
	check(gunmen().all(func(g2): return g2.get_state() == "alert"), "all gunmen alerted by the shot (%s)" % [gunmen().map(func(x): return x.get_state())])
	check(approx(g.awareness, g.profile.gunshot_awareness, 0.05) and g.has_last_known, "awareness %.2f from the gunshot, noise position known" % g.awareness)
	await seconds(1.6)
	check(g.get_state() == "investigate", "after the alert timeout (1.5 s) the gunman investigates (%s)" % g.get_state())
	await seconds(2.5)
	var d1 := g.global_position.distance_to(player.global_position)
	check(d1 < d0 - 2.0, "investigating gunman walks towards the noise: %.1f -> %.1f m" % [d0, d1])
	await teardown()

func test_cover_selection_and_cycle() -> void:
	print("[GPTEST] == cover-lite: pick protecting cover, hide / peek / shoot")
	await setup(["Gunman_1"])
	var g := npc("Gunman_1")
	await teleport(OPEN_SPOT)
	var eye: Vector3 = player.get_visibility_points()[0]
	var front := scene.get_node("Range/CoverPoints/CP_A_Front") as CoverPoint
	var back := scene.get_node("Range/CoverPoints/CP_A1") as CoverPoint
	check(not g.is_cover_protected(front.global_position, eye) and g.is_cover_protected(back.global_position, eye), "decoy CP_A_Front (player side) rejected, CP_A1 (behind the wall) protects")
	var t: float = await wait_until(func(): return g.get_state() == "in_cover", 8.0)
	var c := g.cover
	check(t > 0.0 and c != null and c != front and c.occupant == g, "gunman reached cover %s in %.2f s and claimed it" % [c.name if c else "-", t])
	check(c != null and c.global_position.z > 24.0, "chosen cover is on the far side of a wall from the player")
	var hid: float = await wait_until(func(): return g.cover_phase == "hide", 3.0)
	await frames(2)
	var head := g.hitboxes.get_node("Hitbox_Head") as Hitbox
	var head_pos := (head.get_node("Shape") as Node3D).global_position
	var q := PhysicsRayQueryParameters3D.create(eye, head_pos, 1 | 16, player.get_self_rids())
	q.collide_with_areas = true
	var hit := g.get_world_3d().direct_space_state.intersect_ray(q)
	check(hid >= 0.0 and g.is_crouched and not hit.is_empty() and not (hit.collider is Hitbox), "while hiding the wall blocks a shot at the gunman's head (hit %s)" % [hit.get("collider")])
	var shots0 := g.shots_fired
	var peeked: float = await wait_until(func(): return g.cover_phase == "peek", 3.0)
	check(peeked >= 0.0 and not g.is_crouched, "peeks (stands up) after %.2f s" % peeked)
	await wait_until(func(): return g.shots_fired > shots0, 3.0)
	check(g.shots_fired > shots0, "shoots while peeking (%d shots)" % g.shots_fired)
	var back_to_hide: float = await wait_until(func(): return g.cover_phase == "hide", 4.0)
	check(back_to_hide >= 0.0, "returns to hiding")
	await teardown()

func test_cover_compromised() -> void:
	print("[GPTEST] == flanked in cover -> leave the compromised cover")
	await setup(["Gunman_1"])
	var g := npc("Gunman_1")
	await teleport(OPEN_SPOT)
	await wait_until(func(): return g.get_state() == "in_cover" and g.cover_phase == "hide", 10.0)
	var c := g.cover
	check(c != null, "in cover at %s" % [c.name if c else "-"])
	# Walk around: stand behind the gunman's side of the wall (same side as the cover point).
	await teleport(c.global_position + Vector3(0, 0, 4.0))
	var left: float = await wait_until(func(): return g.get_state() != "in_cover", 4.0)
	check(left >= 0.0, "cover compromised -> leaves in_cover after %.2f s (now %s)" % [left, g.get_state()])
	await frames(5)
	check(g.cover != c and c.occupant == null, "old cover released and not reused (now %s)" % [g.cover.name if g.cover else "none"])
	await teardown()

func test_enemies_deal_damage_and_accuracy() -> void:
	print("[GPTEST] == gunmen shoot and damage the player; accuracy worse than the player's")
	await setup(["Gunman_1", "Gunman_2", "Gunman_3"], false)
	var shots: Array = []
	for g in gunmen():
		g.shot_fired.connect(func(s): shots.append(s))
	var dmg: Array = []
	player.health.damaged.connect(func(i): dmg.append(i))
	await teleport(OPEN_SPOT)
	var t: float = await wait_until(func(): return dmg.size() > 0, 12.0)
	check(t > 0.0 and player.health.health < 100.0, "player takes damage after %.2f s (health %.0f)" % [t, player.health.health])
	check(dmg.size() > 0 and dmg[0].source is NPCController and dmg[0].weapon_id == "WPN_Pistol_01", "damage comes from a gunman's WeaponData pistol")
	await wait_until(func(): return shots.size() >= 12 or player.health.is_dead, 15.0)
	var errs: Array = []
	var hits := 0
	for s in shots:
		var exact: Vector3 = (s["ai_aim_point"] - s["origin"]).normalized()
		errs.append(rad_to_deg((s["direction"] as Vector3).angle_to(exact)))
		if s["damage"] != null:
			hits += 1
	var mean := 0.0
	for e in errs:
		mean += e
	mean /= maxf(errs.size(), 1)
	var player_aim := (load(PISTOL) as WeaponData).spread_aim
	print("[GPTEST] AI shots %d, hits %d, mean angular error %.2f°" % [shots.size(), hits, mean])
	check(shots.size() >= 6 and mean > player_aim * 2.0, "AI mean shot error %.2f° > 2x player's max aimed cone %.2f°" % [mean, player_aim])
	check(hits < shots.size(), "AI misses some shots (%d/%d hit)" % [hits, shots.size()])
	if not player.health.is_dead:
		player.health.health = 1.0  # next hit kills
		await wait_until(func(): return player.health.is_dead, 20.0)
	check(player.health.is_dead and not player.input_enabled, "player killed by gunfire loses input")
	await seconds(0.5)
	check(gunmen().all(func(g): return g.get_state() == "idle"), "gunmen stand down when the player is dead (%s)" % [gunmen().map(func(x): return x.get_state())])
	await teardown()

func test_moving_target_harder() -> void:
	print("[GPTEST] == designer-blind run: player strafes in the open (moving target)")
	await setup(["Gunman_2"])
	var g := npc("Gunman_2")
	var errs_still: Array = []
	var errs_moving: Array = []
	g.shot_fired.connect(func(s): (errs_moving if player.velocity.length() > 2.0 else errs_still).append(s["ai_aim_error_deg"]))
	await teleport(Vector3(8, 0, 14))
	await wait_until(func(): return errs_still.size() >= 3, 10.0)
	# strafe left/right across the gunman's view using real input (not a scripted designer route)
	for k in 6:
		Input.action_press("move_left" if k % 2 == 0 else "move_right")
		await seconds(1.2)
		Input.action_release("move_left")
		Input.action_release("move_right")
	var ms := 0.0
	var mm := 0.0
	for e in errs_still:
		ms += e
	for e in errs_moving:
		mm += e
	ms /= maxf(errs_still.size(), 1)
	mm /= maxf(errs_moving.size(), 1)
	check(errs_still.size() >= 1 and errs_moving.size() >= 1 and mm > ms, "AI aim error vs moving target %.2f° > standing %.2f° (%d / %d shots)" % [mm, ms, errs_moving.size(), errs_still.size()])
	await teardown()

func test_enemy_dies_after_hits() -> void:
	print("[GPTEST] == shooting a gunman: reacts, dies after enough hits")
	await setup(["Gunman_1"])
	var g := npc("Gunman_1")
	# From 3.4 m behind (outside the view cone): first hit makes it engage.
	await teleport(g.global_position + Vector3(0, 0, 3.4))
	await frames(5)
	var body := (g.hitboxes.get_node("Hitbox_Body/Shape") as Node3D).global_position
	var s := player_shoot_at(body)
	var info: DamageInfo = s.get("damage")
	check(info != null and info.zone == Hitbox.Zone.BODY and approx(g.health.health, 100.0 - info.amount, 0.01), "body hit on NPC: %.1f dmg via its hitbox -> DamageReceiver" % [info.amount if info else -1.0])
	await frames(2)
	check(g.get_state() in ["engage", "take_cover"] and g.awareness >= 1.0, "damaged gunman engages the shooter (%s)" % g.get_state())
	var per_hit: float = info.amount if info else 25.0
	var needed := int(ceil(100.0 / per_hit))
	var n := 1
	while not g.is_dead() and n < 10:
		await frames(13)
		body = (g.hitboxes.get_node("Hitbox_Body/Shape") as Node3D).global_position
		if g.is_crouched:
			body = (g.hitboxes.get_node("Hitbox_Head/Shape") as Node3D).global_position
		s = player_shoot_at(body)
		if s.get("damage") != null:
			n += 1
	check(g.is_dead() and g.get_state() == "dead" and g.health.is_dead, "gunman dead after %d hits (%d body hits needed at full health)" % [n, needed])
	var shots := g.shots_fired
	await frames(3)
	check(g.collision_layer == 0 and g.hitboxes.hitboxes.all(func(h): return h.get_node("Shape").disabled), "dead: body collision + hitboxes off")
	check(not g.is_in_group(AIPerception.HEARING_GROUP), "dead NPC stops listening")
	player_shoot_at(player.global_position + Vector3(0, 30, -5))
	await seconds(1.0)
	check(g.shots_fired == shots and g.get_state() == "dead", "dead gunman does nothing")
	await teardown()

func test_shared_resources_independent() -> void:
	print("[GPTEST] == shared .tres, independent runtime state (godot-gamedev verification)")
	await setup(["Gunman_1", "Gunman_2"])
	var a := npc("Gunman_1")
	var b := npc("Gunman_2")
	check(a.profile == b.profile and a.weapon.data == b.weapon.data, "both gunmen share the same AIProfile + WeaponData resources")
	a.weapon.ammo = 3
	a.health.apply_damage(_dmg(40.0))
	check(b.weapon.ammo == 12 and b.health.health == 100.0 and a.profile.max_health == 100.0, "damage/ammo on one gunman leave the other + the resource untouched")
	await teardown()

func _dmg(amount: float) -> DamageInfo:
	var i := DamageInfo.new()
	i.amount = amount
	return i

func test_civilians_route_and_flee() -> void:
	print("[GPTEST] == civilians: walk routes, idle at points, flee from gunshots within 25 m")
	await setup(["Civilian_1", "Civilian_2", "Civilian_3"])
	var c1 := npc("Civilian_1")
	var c3 := npc("Civilian_3")
	var start1 := c1.global_position
	var start3 := c3.global_position
	await seconds(5.0)
	check(c1.global_position.distance_to(start1) > 4.0 and c3.global_position.distance_to(start3) > 4.0, "walking their routes (moved %.1f / %.1f m)" % [c1.global_position.distance_to(start1), c3.global_position.distance_to(start3)])
	var waited: float = await wait_until(func(): return c3._route_wait > 0.0, 10.0)
	await frames(20)
	check(waited >= 0.0 and c3._route_wait > 0.0 and c3.velocity.length() < 0.1, "civilian idles at a route point (speed %.2f)" % c3.velocity.length())
	# Shot fired 20 m from Civilian_1, 40+ m from Civilian_3.
	var p1 := c1.global_position
	await teleport(p1 + Vector3(20, 0, 0))
	await frames(3)
	var d0 := c1.global_position.distance_to(player.global_position)
	player_shoot_at(player.global_position + Vector3(0, 30, -5))
	await frames(2)
	check(c1.get_state() == "flee", "civilian 20 m from the shot flees")
	check(c3.get_state() == "idle" and c3.global_position.distance_to(player.global_position) > 25.0, "civilian > 25 m away keeps walking")
	await seconds(4.0)
	var d1 := c1.global_position.distance_to(player.global_position)
	check(d1 > d0 + 6.0, "flees away from the shooter: %.1f -> %.1f m" % [d0, d1])
	var back: float = await wait_until(func(): return c1.get_state() == "idle", 8.0)
	check(back >= 0.0, "calms down after the flee timeout (8 s) and returns to the route")
	var pos := c1.global_position
	await seconds(3.0)
	check(c1.global_position.distance_to(pos) > 1.0, "walking again after calming down")
	await teardown()

func test_data_driven_table() -> void:
	print("[GPTEST] == data-driven: a different AIProfile table changes behaviour")
	scene = (load(AI_RANGE) as PackedScene).instantiate()
	ai = scene.get_node("AI")
	for n in ai.get_children():
		if n is NPCController and n.name != "Gunman_1":
			ai.remove_child(n)
			n.free()
	(ai.get_node("Gunman_1") as NPCController).profile = load(COWARD)
	root.add_child(scene)
	player = scene.get_node("Range/Player")
	await frames(1)
	player.health.invulnerable = true
	player._set_crouching(true)  # crouch first: teleporting in standing would be seen for a frame
	await teleport(Vector3(-4, 0, 23.0))
	await frames(10)
	var g := npc("Gunman_1")
	var d0 := g.global_position.distance_to(player.global_position)
	player_shoot_at(player.global_position + Vector3(0, 30, -10))
	await frames(2)
	check(g.get_state() == "flee", "PT_AI_Coward.tres: same armed NPC flees on a gunshot instead of alerting (%s)" % g.get_state())
	await seconds(2.5)
	check(g.global_position.distance_to(player.global_position) > d0 + 4.0 and g.shots_fired == 0, "runs away and does not shoot")
	await seconds(1.0)
	check(g.get_state() == "idle", "table timeout (3 s) -> idle")
	await teardown()
