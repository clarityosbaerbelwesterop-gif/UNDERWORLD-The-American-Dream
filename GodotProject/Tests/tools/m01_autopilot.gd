extends Node
## M01 "Dead Drop" autopilot - plays the mission like a person at a keyboard (T-BUILD-02).
##
## Contract (this is what makes it a meaningful test, unlike calling mission APIs):
##   * it ONLY presses input actions (Input.action_press/release, same map as KB/gamepad) and
##     turns the camera (CameraRig yaw/pitch = what the mouse does);
##   * it READS the world (positions, HUD objective index, health) the way a player sees it;
##   * it never calls MissionManager / Vehicle / CarriedItem / Health methods that change state.
## If a step can only be finished by calling an API, the game is not playable and the
## autopilot gets stuck - that is the failure it exists to find.
##
## Used by Tests/test_playthrough.gd (headless, --fixed-fps 60) and by
## Tests/tools/record_m01_playthrough.gd (Movie Maker video in Forward Plus).

signal finished(ok: bool, reason: String)

const HZ := 60.0
## Hard cap on mission game time (design: 10-15 min for a human; the bot is faster).
@export var time_limit_s := 900.0

var level: Node
var mm: MissionManager
var player: PlayerController
var car: Vehicle
var rig: Node   # CameraRig

var t := 0.0
var log_lines: PackedStringArray = []
var objective_times: Dictionary = {}     # objective index -> game seconds when it became active
var deaths := 0
var shots := 0
var hits := 0
var done := false
var result_ok := false
var result_reason := ""

var _last_obj := -1
var _pressed: Dictionary = {}            # action -> strength held this frame
var _tap_cooldown := 0.0
var _nav_path: PackedVector3Array = []
var _nav_goal := Vector3.INF
var _nav_idx := 0
var _nav_repath := 0.0
var _route: Array = []
var _route_idx := 0
var _stuck_t := 0.0
var _last_pos := Vector3.ZERO
var _fire_phase := 0
var _last_state := -1
var _debug := false
var _dbg_t := 0.0

func setup(p_level: Node) -> void:
	level = p_level
	mm = level.get_node("MissionManager") as MissionManager
	player = level.get_node("Player") as PlayerController
	car = level.get_node("VH_Sedan_01") as Vehicle
	rig = player.camera_rig
	# Act BEFORE every gameplay node in the same physics frame: Input.is_action_just_pressed()
	# compares against the current physics frame, so a press made after the player already ran
	# would never be seen as "just pressed".
	process_physics_priority = -1000
	_debug = OS.get_environment("UW_AUTOPILOT_DEBUG") == "1"
	var wc := player.get_node_or_null("WeaponController")
	if wc != null and wc.get("weapon") != null:
		(wc.get("weapon") as Weapon).hit_confirmed.connect(func(_i): hits += 1)
		if _debug:
			(wc.get("weapon") as Weapon).impact.connect(func(pos, _n, col):
				note("dbg impact %s at %s" % [(col as Node).name if col is Node else str(col), pos]))
	mm.mission_failed.connect(func(reason: String) -> void:
		deaths += 1
		note("mission FAILED (%s) - the game restarts at the last checkpoint" % reason))

func note(msg: String) -> void:
	var line := "[AUTOPILOT] t=%6.1f s  %s" % [t, msg]
	log_lines.append(line)
	print(line)

# --- input helpers (the ONLY way the autopilot acts) ---------------------------

func _hold(action: StringName, strength := 1.0) -> void:
	_pressed[action] = clampf(strength, 0.0, 1.0)

func _apply_inputs() -> void:
	for a in [&"move_forward", &"move_back", &"move_left", &"move_right", &"sprint", &"aim",
			&"fire", &"vehicle_accelerate", &"vehicle_brake", &"interact", &"enter_vehicle", &"reload", &"crouch"]:
		if _pressed.has(a) and _pressed[a] > 0.0:
			Input.action_press(a, _pressed[a])
		elif Input.is_action_pressed(a):
			Input.action_release(a)
	_pressed.clear()

## One key tap (press this frame, released next frame), rate-limited like a human.
func _tap(action: StringName) -> void:
	if _tap_cooldown <= 0.0:
		_hold(action)
		_tap_cooldown = 0.35

func release_all() -> void:
	_pressed.clear()
	_apply_inputs()

## Turn the camera like a mouse would so the screen centre points along `dir` (world).
func _look_dir(dir: Vector3, pitch_override = null) -> void:
	var flat := Vector2(dir.x, dir.z)
	if flat.length() > 0.001:
		rig.yaw = atan2(-dir.x, -dir.z)
	if pitch_override != null:
		rig.pitch = pitch_override
	else:
		rig.pitch = clampf(atan2(dir.y, flat.length()), deg_to_rad(rig.min_pitch_deg), deg_to_rad(rig.max_pitch_deg))
	rig._apply_rotation()

# --- per-frame driver ------------------------------------------------------------

func _physics_process(delta: float) -> void:
	if done or mm == null:
		return
	t += delta
	_tap_cooldown -= delta
	if mm.state == MissionManager.State.COMPLETED:
		_finish(true, "MISSION COMPLETED (reward $%d)" % mm.mission.reward_cash)
		return
	if t > time_limit_s:
		_finish(false, "time limit %.0f s at objective %d '%s'" % [time_limit_s, mm.current_index, mm.objective_text()])
		return
	if mm.state != _last_state:
		note("mission state -> %s" % MissionManager.State.keys()[mm.state])
		_last_state = mm.state
	var obj := mm.current_index
	if obj != _last_obj:
		objective_times[obj] = t
		note("objective %d: '%s'" % [obj, mm.objective_text()])
		_last_obj = obj
		_nav_goal = Vector3.INF
		_route.clear()
		_stuck_t = 0.0
	if player.is_dead():
		_apply_inputs()
		return
	if _debug and t - _dbg_t > 2.0:
		_dbg_t = t
		if mm.current_index == 4:
			var es := []
			for e in _living_enemies():
				es.append("%s@(%.1f,%.1f,%.1f) st=%s" % [e.name, e.global_position.x, e.global_position.y, e.global_position.z, (e.fsm.state if e.fsm else "?")])
			note("dbg fight cover=%s crouch=%s hp=%.0f enemies=%s" % [_cover.name if _cover else "-", player.is_crouching, player.get_node("Health").health, es])
		note("dbg player=%s veh=%s car=%s state=%d speed=%.1f" % [player.global_position, player.vehicle != null,
			car.global_position, car.state, car.forward_speed])
	match obj:
		0, 1:
			_step_board_car()
		2:
			_step_drive(_route_to_garage())
		3:
			_step_leave_car_then_walk(level.get_node("Mission/Area_GarageInside").global_position)
		4:
			_step_fight()
		5:
			_step_pickup()
		6:
			_step_deliver()
		_:
			pass   # outro card: hands off, wait for the mission to complete by itself
	_apply_inputs()

func _finish(ok: bool, reason: String) -> void:
	done = true
	result_ok = ok
	result_reason = reason
	release_all()
	note(("PASS: " if ok else "FAIL: ") + reason)
	finished.emit(ok, reason)

# --- steps -------------------------------------------------------------------------

func _in_car() -> bool:
	return car.driver == player and car.state == Vehicle.State.DRIVING

func _step_board_car() -> void:
	if player.vehicle != null:
		return   # entering animation runs
	# The navmesh is baked without the (movable) car, so walk around it by hand like a person:
	# first to a point beside the driver's side, then to the door, then press F / Y.
	var door := car.get_socket(&"SOCKET_Exit_Left").global_position
	var cpos := car.global_position
	var side := car.global_basis.x * signf((door - cpos).dot(car.global_basis.x))
	side.y = 0.0
	side = side.normalized()
	var fwd := car.global_basis.z
	fwd.y = 0.0
	fwd = fwd.normalized()
	var rel := player.global_position - cpos
	if Vector2(rel.x, rel.z).length() > 6.0:
		_walk_to(cpos + side * 2.4)      # far away: navmesh, around buildings and props
		return
	var lat := rel.dot(side)
	var along_now := rel.dot(fwd)
	var approach := door + side * 0.6
	if lat < 1.4:
		# Wrong side or too close to the body: go round the nearer bumper, like a person would.
		var sgn := signf(along_now) if absf(along_now) > 0.1 else 1.0
		if absf(along_now) < 3.4:
			_walk_direct(cpos + fwd * 3.9 * sgn + side * lat)
		else:
			_walk_direct(cpos + fwd * 3.9 * sgn + side * 2.4)
	elif Vector2(player.global_position.x - approach.x, player.global_position.z - approach.z).length() > 0.5:
		_walk_direct(approach)
	else:
		_tap(&"enter_vehicle")

## Straight walk (no navmesh) toward a nearby point.
func _walk_direct(goal: Vector3) -> void:
	var to := goal - player.global_position
	to.y = 0.0
	if to.length() < 0.15:
		return
	_look_dir(to, deg_to_rad(-12.0))
	_hold(&"move_forward", 1.0 if to.length() > 1.0 else 0.6)

func _step_drive(route: Array) -> void:
	if not _in_car():
		if player.vehicle == null:
			_step_board_car()
		return
	if _route.is_empty():
		_route = route
		_route_idx = 0
	if _route_idx >= _route.size():
		_drive_controls(0.0, 1.0, 0.0)
		return
	var target: Vector3 = _route[_route_idx]
	var to := target - car.global_position
	to.y = 0.0
	var last := _route_idx == _route.size() - 1
	if to.length() < (3.0 if last else 6.0):
		_route_idx += 1
		return
	var fwd := car.global_basis.z
	fwd.y = 0.0
	var err := fwd.normalized().signed_angle_to(to.normalized(), Vector3.UP)
	var steer := clampf(err / deg_to_rad(10.0), -1.0, 1.0)
	var speed := car.forward_speed
	var limit := 14.0
	if absf(err) > deg_to_rad(20.0):
		limit = 6.0
	if to.length() < 14.0 and last:
		limit = 3.0
	var throttle := 0.0
	var brake := 0.0
	if speed > limit + 1.0:
		brake = 1.0
	elif speed < limit:
		throttle = 0.9
	_drive_controls(throttle, brake, steer)

func _drive_controls(throttle: float, brake: float, steer: float) -> void:
	if throttle > 0.0:
		_hold(&"vehicle_accelerate", throttle)
	if brake > 0.0:
		_hold(&"vehicle_brake", brake)
	if steer > 0.02:
		_hold(&"move_left", steer)
	elif steer < -0.02:
		_hold(&"move_right", -steer)

func _step_leave_car_then_walk(goal: Vector3) -> void:
	if player.vehicle != null:
		if _in_car():
			if absf(car.forward_speed) > 0.3:
				_drive_controls(0.0, 1.0, 0.0)
			else:
				_tap(&"enter_vehicle")   # F / Y = get out
		return
	_walk_to(goal)

func _living_enemies() -> Array:
	var out: Array = []
	for n in level.get_tree().get_nodes_in_group(&"mission_enemies"):
		var e := n as MissionEnemy
		if e != null and not e.is_dead() and e.is_active() and e.visible:
			out.append(e)
	return out

## Fights like a competent player: run to a cover spot that the current threats cannot see
## while crouched, then peek (stand, aim, fire) and hide (crouch, reload) in a rhythm.
func _step_fight() -> void:
	if player.vehicle != null:
		_step_leave_car_then_walk(player.global_position)
		return
	var enemies := _living_enemies()
	if enemies.is_empty():
		_set_crouch(false)
		return   # wave 2 not released yet / objective about to complete
	# Close and visible threat: fight it now, wherever we stand (running past it is how you die).
	var close_visible := _nearest_visible(enemies, 9.0)
	_cover_retarget -= 1.0 / HZ
	# Hysteresis: keep the cover until it hides us from nobody, re-check at most every 3 s.
	if close_visible == null and (_cover == null or (_cover_retarget <= 0.0 and not _cover_hides(_cover, enemies))):
		_cover = _pick_cover(enemies)
		_cover_retarget = 3.0
	if _cover != null and close_visible == null:
		var to := _cover.global_position - player.global_position
		to.y = 0.0
		if to.length() > 0.5:
			_set_crouch(false)
			_walk_to(_cover.global_position)
			return
	# In cover (or no cover exists): peek / hide rhythm.
	_peek_t += 1.0 / HZ
	var cycle := fmod(_peek_t, 2.4)
	var weapon := player.get_node_or_null("WeaponController")
	var w = weapon.get("weapon") if weapon != null else null
	if _cover != null and cycle > 1.6:
		_set_crouch(true)
		if w != null and w.ammo < 5 and not w.is_reloading:
			_tap(&"reload")
		return
	_set_crouch(false)
	var cam: Camera3D = rig.camera
	var space := player.get_world_3d().direct_space_state
	var best: MissionEnemy = null
	var best_d := INF
	for e in enemies:
		var aim_at: Vector3 = (e as Node3D).global_position + Vector3(0, 1.25, 0)
		var q := PhysicsRayQueryParameters3D.create(cam.global_position, aim_at, rig.aim_ray_mask, player.get_self_rids())
		var hit := space.intersect_ray(q)
		var sees := hit.is_empty() or _is_part_of(hit.get("collider"), e)
		var d := player.global_position.distance_to((e as Node3D).global_position)
		if sees and d < best_d:
			best = e
			best_d = d
	if best == null:
		# The camera sits ~3 m behind the shoulder; a roof edge can block IT while Jason's own
		# eyes see the target. Aiming pulls the camera in to the shoulder - so raise the gun first.
		var eye_target := _eye_visible(enemies)
		if eye_target != null and _eye_aim_t < 2.0:
			_eye_aim_t += 1.0 / HZ
			_hold(&"aim")
			_look_dir(eye_target.global_position + Vector3(0, 1.25, 0) - cam.global_position)
			return
		_no_los_t += 1.0 / HZ
		if _cover == null or _no_los_t > 3.0:
			# Nobody visible from here (roof gunman, someone flanking round the back): go where
			# a person would - a spot on the ground that can actually see and aim at him.
			if _cover != null:
				_banned_cover[_cover] = true
				_cover = null
			_set_crouch(false)
			_spot_t -= 1.0 / HZ
			# Arrived and still nothing in view for 2 s: this spot is useless, never pick it again.
			if _spot != Vector3.INF and Vector2(_spot.x - player.global_position.x, _spot.z - player.global_position.z).length() < 0.9:
				_at_spot_t += 1.0 / HZ
				if _at_spot_t > 2.0:
					_banned_spots.append(_spot)
					_spot = Vector3.INF
					_at_spot_t = 0.0
			if _spot_t <= 0.0 or _spot == Vector3.INF:
				_spot = _firing_spot(enemies)
				_spot_t = 2.0
				_at_spot_t = 0.0
			if _spot != Vector3.INF:
				_walk_to(_spot)
			else:
				# No known good spot left: back away from the threat to open the angle.
				var ep: Vector3 = (enemies[0] as Node3D).global_position
				var away := player.global_position - ep
				away.y = 0.0
				if away.length() < 0.1:
					away = Vector3.RIGHT
				_walk_to(ep + away.normalized() * 12.0)
				_eye_aim_t = 0.0
		return
	_no_los_t = 0.0
	_eye_aim_t = 0.0
	_spot = Vector3.INF
	_hold(&"aim")
	_look_dir(best.global_position + Vector3(0, 1.25, 0) - cam.global_position)
	if w != null and w.ammo == 0 and not w.is_reloading:
		_tap(&"reload")
		return
	# Semi-auto pistol: one press per shot, released between shots, only once the aim settled.
	# ~2.5 shots/s: a human taps, and spamming only stacks bloom (T-GP-02a).
	if rig.aim_blend > 0.85:
		_fire_phase = (_fire_phase + 1) % 24
		if _fire_phase < 2:
			_hold(&"fire")
			if _fire_phase == 0:
				shots += 1

func _nearest_visible(enemies: Array, max_d: float) -> MissionEnemy:
	var cam: Camera3D = rig.camera
	var space := player.get_world_3d().direct_space_state
	var best: MissionEnemy = null
	var best_d := max_d
	for e in enemies:
		var d := player.global_position.distance_to((e as Node3D).global_position)
		if d > best_d:
			continue
		var q := PhysicsRayQueryParameters3D.create(cam.global_position, (e as Node3D).global_position + Vector3(0, 1.25, 0), rig.aim_ray_mask, player.get_self_rids())
		var hit := space.intersect_ray(q)
		if hit.is_empty() or _is_part_of(hit.get("collider"), e):
			best = e
			best_d = d
	return best

func _cover_hides(c: Node3D, enemies: Array) -> bool:
	var space := player.get_world_3d().direct_space_state
	for e in enemies:
		var q := PhysicsRayQueryParameters3D.create((e as Node3D).global_position + Vector3(0, 1.3, 0), c.global_position + Vector3(0, 0.9, 0), 1)
		if not space.intersect_ray(q).is_empty():
			return true
	return false

var _eye_aim_t := 0.0

func _eye_visible(enemies: Array) -> MissionEnemy:
	var space := player.get_world_3d().direct_space_state
	var eye := player.global_position + Vector3(0, 1.6, 0)
	for e in enemies:
		var q := PhysicsRayQueryParameters3D.create(eye, (e as Node3D).global_position + Vector3(0, 1.25, 0), 1, player.get_self_rids())
		if space.intersect_ray(q).is_empty():
			return e
	return null

var _spot := Vector3.INF
var _spot_t := 0.0
var _at_spot_t := 0.0
var _banned_spots: Array = []

## Tactical point query: ground spots 6-13 m around each living enemy, on the navmesh, with a
## clear line from eye height to the enemy's chest and an aim pitch the camera can reach.
## Nearest to the player wins.
func _firing_spot(enemies: Array) -> Vector3:
	var map := player.get_world_3d().navigation_map
	var space := player.get_world_3d().direct_space_state
	var best := Vector3.INF
	var best_d := INF
	for e in enemies:
		var ep: Vector3 = (e as Node3D).global_position + Vector3(0, 1.25, 0)
		for i in 16:
			var ang := TAU * i / 16.0
			for r in [6.0, 9.0, 13.0]:
				var cand := NavigationServer3D.map_get_closest_point(map, (e as Node3D).global_position + Vector3(cos(ang) * r, 0.0, sin(ang) * r))
				var banned := false
				for b in _banned_spots:
					if (b as Vector3).distance_to(cand) < 2.0:
						banned = true
				if banned:
					continue
				var eye := cand + Vector3(0, 1.1, 0)    # navmesh sits ~0.5 m above the floor
				var flat := Vector2(ep.x - eye.x, ep.z - eye.z).length()
				if flat < 3.0 or atan2(ep.y - eye.y, flat) > deg_to_rad(40.0):
					continue
				var hit := space.intersect_ray(PhysicsRayQueryParameters3D.create(eye, ep, 1))
				if not hit.is_empty():
					continue
				var d := player.global_position.distance_to(cand)
				if d < best_d:
					best_d = d
					best = cand
	return best

var _cover: Node3D = null
var _cover_retarget := 0.0
var _peek_t := 0.0
var _no_los_t := 0.0
var _banned_cover: Dictionary = {}

func _set_crouch(on: bool) -> void:
	if player.is_crouching != on:
		_tap(&"crouch")

## Best cover = hides a crouched head (0.9 m) from the most living enemies, then the closest.
func _pick_cover(enemies: Array) -> Node3D:
	var space := player.get_world_3d().direct_space_state
	var best: Node3D = null
	var best_score := -INF
	for n in level.get_tree().get_nodes_in_group(&"cover_points"):
		var c := n as Node3D
		if c == null or _banned_cover.has(c):
			continue
		var hidden := 0
		for e in enemies:
			var from: Vector3 = (e as Node3D).global_position + Vector3(0, 1.3, 0)
			var q := PhysicsRayQueryParameters3D.create(from, c.global_position + Vector3(0, 0.9, 0), 1)
			if not space.intersect_ray(q).is_empty():
				hidden += 1
		var d := player.global_position.distance_to(c.global_position)
		var score := hidden * 100.0 - d
		if hidden > 0 and score > best_score:
			best_score = score
			best = c
	return best

func _is_part_of(collider: Object, e: Node) -> bool:
	var n := collider as Node
	while n != null:
		if n == e:
			return true
		n = n.get_parent()
	return false

func _step_pickup() -> void:
	if player.vehicle != null:
		_step_leave_car_then_walk(player.global_position)
		return
	var pkg := level.get_node("Mission/Pickup_Package") as Node3D
	var stand := pkg.global_position
	stand.y = player.global_position.y
	if Vector2(player.global_position.x - stand.x, player.global_position.z - stand.z).length() > 1.3:
		_walk_to(stand)
	else:
		_look_dir(pkg.global_position - rig.camera.global_position)
		_tap(&"interact")

func _step_deliver() -> void:
	if not _in_car():
		if player.vehicle == null:
			_step_board_car()
		return
	_step_drive(_route_to_warehouse())

# --- navigation on foot (navmesh, like any NPC) -------------------------------------

func _walk_to(goal: Vector3) -> void:
	var map := player.get_world_3d().navigation_map
	_nav_repath -= 1.0 / HZ
	if _nav_goal.distance_to(goal) > 1.0 or _nav_repath <= 0.0 or _nav_idx >= _nav_path.size():
		_nav_path = NavigationServer3D.map_get_path(map, player.global_position, goal, true)
		_nav_goal = goal
		_nav_idx = 1 if _nav_path.size() > 1 else 0
		_nav_repath = 1.0
		if _debug and int(t) % 4 == 0:
			note("dbg navpath %s -> %s: %s" % [player.global_position, goal, _nav_path])
	var target := goal
	while _nav_idx < _nav_path.size():
		var p := _nav_path[_nav_idx]
		if Vector2(p.x - player.global_position.x, p.z - player.global_position.z).length() < 0.6:
			_nav_idx += 1
			continue
		target = p
		break
	target = _avoid_car(target)
	var to := target - player.global_position
	to.y = 0.0
	if to.length() < 0.15:
		return
	_look_dir(to, deg_to_rad(-12.0))
	# Unstick like a person: less than 15 cm progress in 0.5 s (a prop the navmesh does not
	# know) -> back off, then sidestep, alternating sides on every attempt.
	_prog_t += 1.0 / HZ
	if _prog_t >= 0.5:
		if player.global_position.distance_to(_last_pos) < 0.15:
			_stuck_t += 0.5
		else:
			_stuck_t = 0.0
		_last_pos = player.global_position
		_prog_t = 0.0
	if _stuck_t >= 1.0:
		_stuck_t += 1.0 / HZ
		if _stuck_t < 1.5:
			_hold(&"move_back")
		elif _stuck_t < 2.5:
			_hold(&"move_left" if _unstick_side % 2 == 0 else &"move_right")
			_hold(&"move_forward")
		else:
			_stuck_t = 0.0
			_unstick_side += 1
			_nav_repath = 0.0
		return
	_hold(&"move_forward")
	if to.length() > 6.0:
		_hold(&"sprint")   # the controller itself refuses to sprint while carrying (design)

var _unstick_side := 0
var _prog_t := 0.0

## The parked sedan is not in the navmesh: if the next straight leg crosses its footprint,
## walk round the bumper end that is on the way (what anyone does with a parked car).
func _avoid_car(target: Vector3) -> Vector3:
	if player.vehicle != null:
		return target
	var cpos := car.global_position
	var fx := car.global_basis.z
	fx.y = 0.0
	fx = fx.normalized()
	var sx := car.global_basis.x
	sx.y = 0.0
	sx = sx.normalized()
	var p0 := player.global_position
	var crosses := false
	for i in range(1, 13):
		var q := p0.lerp(target, i / 12.0) - cpos
		if absf(q.dot(sx)) < 1.5 and absf(q.dot(fx)) < 3.1:
			crosses = true
			break
	if not crosses:
		return target
	var rel := p0 - cpos
	var trel := target - cpos
	var sgn := signf(trel.dot(fx) + rel.dot(fx))
	if sgn == 0.0:
		sgn = 1.0
	var lat := rel.dot(sx)
	if absf(rel.dot(fx)) < 3.5:
		return cpos + fx * 3.9 * sgn + sx * (signf(lat) if absf(lat) > 0.05 else 1.0) * 1.6
	return cpos + fx * 3.9 * sgn + sx * signf(trel.dot(sx)) * 1.6

# --- routes (lane centres of the Calloway Ave drive ring, layout §3.1) -------------

func _route_to_garage() -> Array:
	var spawn := level.get_node("Mission/CarSpawn") as Node3D
	var arrival := level.get_node("Mission/Area_GarageArrival") as Node3D
	var x_w := spawn.global_position.x
	return [
		Vector3(x_w, 0, -50.0), Vector3(x_w, 0, 0.0), Vector3(x_w, 0, 62.0), Vector3(x_w, 0, 79.0),
		Vector3(0.0, 0, 79.0), Vector3(24.0, 0, 79.0), Vector3(24.0, 0, 50.0), Vector3(24.0, 0, 20.0),
		Vector3(arrival.global_position.x - 2.0, 0, arrival.global_position.z),
	]

func _route_to_warehouse() -> Array:
	var wh := level.get_node("Mission/Area_Warehouse") as Node3D
	return [
		Vector3(24.0, 0, 30.0), Vector3(24.0, 0, 60.0), Vector3(24.0, 0, 74.0),
		Vector3(wh.global_position.x, 0, wh.global_position.z),
	]

func summary() -> String:
	var s := "autopilot: %s - %s | game time %.1f s | deaths %d | shots %d | hits %d | objectives:" % [
		"PASS" if result_ok else "FAIL", result_reason, t, deaths, shots, hits]
	var keys := objective_times.keys()
	keys.sort()
	for k in keys:
		s += " %d@%.1f" % [k, objective_times[k]]
	return s
