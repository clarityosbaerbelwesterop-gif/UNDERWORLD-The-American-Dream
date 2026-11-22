# UNDERWORLD - NPC body + behaviour (T-AI-01 enemies, T-AI-02 baseline civilians).
# One script for every NPC; the AIProfile .tres decides the archetype (transition table,
# perception, accuracy, cover, flee). Node contract (PT_NPC_*.tscn, later SK_NPC_* scenes):
#   NPCController (CharacterBody3D, layer 3 "Characters", cylinder collider TD-011)
#   ├─ NavigationAgent3D
#   ├─ Pose (Node3D)            crouch drop / death tilt; holds the visual + hitboxes
#   │   ├─ Visual ... [PT_SOCKET_RightHand_Weapon/Weapon]   (Weapon optional: civilians)
#   │   └─ Hitboxes (HumanoidHitboxes -> ../../Health)
#   └─ Health (DamageReceiver)
# Facing: the body yaw is the facing, model front = +Z (TD-004).
class_name NPCController
extends CharacterBody3D

signal state_changed(from: String, to: String, event: String)
signal shot_fired(shot: Dictionary)
signal died

const STATES := ["idle", "alert", "investigate", "engage", "take_cover", "in_cover", "search", "flee", "dead"]
## World | Vehicles: what blocks sight.
const LOS_MASK := 1 | 8

@export var profile: AIProfile
@export var route_path: NodePath
@export var route_start_index := 0
## 0 = random; tests fix it for deterministic aim error / timings.
@export var rng_seed := 0
## Debug: print every state change as [AI] lines.
@export var log_states := false

var fsm: AIStateMachine
var health: DamageReceiver
var weapon: Weapon
var agent: NavigationAgent3D
var pose: Node3D
var hitboxes: HumanoidHitboxes
var route: NPCRoute
## Real SK_NPC model + clip driver (T-GP-01); null while the PT capsule stands in.
var visual: CharacterVisual

var target: Node3D
var awareness := 0.0
var target_visible := false
var visible_time := 0.0
var unseen_time := 0.0
var last_known_pos := Vector3.ZERO
var has_last_known := false
var last_noise_pos := Vector3.ZERO
var is_crouched := false
var is_cowering := false
var cover: CoverPoint
var cover_phase := ""          ## "hide" | "peek" while in_cover
var shots_fired := 0
var last_aim_error := 0.0

var _rng := RandomNumberGenerator.new()
var _self_rids: Array[RID] = []
var _events: Array[String] = []
var _moving := false
var _move_target := Vector3.ZERO
var _move_speed := 0.0
var _face_point = null          # Vector3 or null (= face movement direction)
var _route_idx := 0
var _route_wait := 0.0
var _shot_timer := 0.0
var _burst_left := 0
var _reaction_left := 0.0
var _phase_left := 0.0
var _peek_had_los := false
var _peeks_without_los := 0
var _cover_retry := 0.0
var _bad_covers: Array = []
var _look_timer := 0.0

func _ready() -> void:
	assert(profile != null, "%s: NPCController needs an AIProfile" % name)
	if rng_seed != 0:
		_rng.seed = rng_seed
	else:
		_rng.randomize()
	collision_layer = 1 << 2               # 3 Characters
	collision_mask = 1 | 2 | 4 | 8         # World, Player, Characters, Vehicles
	floor_snap_length = 0.4
	health = get_node("Health") as DamageReceiver
	health.max_health = profile.max_health
	health.reset()
	health.damaged.connect(_on_damaged)
	health.died.connect(_on_died)
	agent = get_node("NavigationAgent3D") as NavigationAgent3D
	pose = get_node("Pose") as Node3D
	hitboxes = pose.get_node_or_null("Hitboxes") as HumanoidHitboxes
	visual = pose.get_node_or_null("Visual/CharacterVisual") as CharacterVisual
	weapon = _find_weapon(pose)
	if weapon != null and profile.weapon != null:
		weapon.data = profile.weapon
		if rng_seed != 0:
			weapon.spread_seed = rng_seed + 1
			weapon._rng.seed = rng_seed + 1
	route = get_node_or_null(route_path) as NPCRoute
	_route_idx = route_start_index
	_self_rids.append(get_rid())
	if hitboxes != null:
		_self_rids.append_array(hitboxes.get_rids())
	add_to_group(AIPerception.HEARING_GROUP)
	add_to_group("npc")
	fsm = AIStateMachine.new(profile.transitions, profile.state_timeouts, profile.initial_state)
	fsm.state_changed.connect(_on_state_changed)
	_enter_state(fsm.state, "", "ready")

func _find_weapon(n: Node) -> Weapon:
	if n is Weapon:
		return n
	for c in n.get_children():
		var w := _find_weapon(c)
		if w != null:
			return w
	return null

# --- public helpers -----------------------------------------------------------

## Checkpoint restart (T-MIS-01): bring a dead NPC back exactly as it was spawned.
## Used by MissionManager when it rewinds to a checkpoint - the enemies of the failed attempt
## must be alive again and must not carry over their old awareness/cover state.
func revive() -> void:
	if not is_dead():
		return
	health.reset()
	collision_layer = 1 << 2               # 3 Characters
	if hitboxes != null:
		hitboxes.set_enabled(true)
	pose.rotation_degrees.x = 0.0
	add_to_group(AIPerception.HEARING_GROUP)
	awareness = 0.0
	target_visible = false
	visible_time = 0.0
	unseen_time = 0.0
	has_last_known = false
	last_known_pos = Vector3.ZERO
	shots_fired = 0
	_bad_covers.clear()
	_release_cover()
	fsm.state = profile.initial_state
	fsm.time_in_state = 0.0
	_enter_state(fsm.state, "dead", "revive")

func get_state() -> String:
	return fsm.state

func is_dead() -> bool:
	return fsm.state == "dead"

func get_forward() -> Vector3:
	return global_basis.z.normalized()

func get_eye_pos() -> Vector3:
	return global_position + Vector3(0, profile.eye_height - (profile.crouch_drop if is_crouched else 0.0), 0)

func get_self_rids() -> Array[RID]:
	return _self_rids

func has_los(from: Vector3, to: Vector3) -> bool:
	var q := PhysicsRayQueryParameters3D.create(from, to, LOS_MASK, _self_rids)
	return get_world_3d().direct_space_state.intersect_ray(q).is_empty()

func target_points(t: Node3D) -> Array:
	if t.has_method("get_visibility_points"):
		return t.get_visibility_points()
	return [t.global_position + Vector3(0, 1.65, 0), t.global_position + Vector3(0, 1.15, 0)]

## Cover protects if the threat's eye cannot see our crouched head or crouched body.
func is_cover_protected(cover_pos: Vector3, threat_eye: Vector3) -> bool:
	var top := profile.eye_height - profile.crouch_drop + 0.2
	return not has_los(threat_eye, cover_pos + Vector3(0, top, 0)) and not has_los(threat_eye, cover_pos + Vector3(0, 0.6, 0))

## Best free, protecting, peekable CoverPoint vs the current threat (or null).
func find_cover() -> CoverPoint:
	if target == null:
		return null
	var pts := target_points(target)
	var threat_eye: Vector3 = pts[0]
	var threat_chest: Vector3 = pts[1]
	var threat_pos := target.global_position
	var best: CoverPoint = null
	var best_score := INF
	for n in get_tree().get_nodes_in_group(CoverPoint.GROUP):
		var c := n as CoverPoint
		if c == null or not c.is_free_for(self) or _bad_covers.has(c):
			continue
		var cp := c.global_position
		var d_self := cp.distance_to(global_position)
		var d_threat := cp.distance_to(threat_pos)
		if d_self > profile.cover_search_radius or d_threat < profile.cover_min_threat_distance or d_threat > profile.max_engage_distance:
			continue
		if not is_cover_protected(cp, threat_eye):
			continue
		if not has_los(cp + Vector3(0, profile.eye_height, 0), threat_chest) and not has_los(cp + Vector3(0, profile.eye_height, 0), threat_eye):
			continue  # cannot peek at the threat from here
		var s := AIPerception.cover_score(d_self, d_threat, profile)
		if s < best_score:
			best_score = s
			best = c
	return best

# --- events -------------------------------------------------------------------

func send_event(ev: String) -> void:
	if not _events.has(ev):
		_events.append(ev)

## Listener for AIPerception.emit_noise (group "ai_hearing").
func hear_noise(pos: Vector3, radius: float, source: Node, kind: String) -> void:
	if is_dead() or source == self:
		return
	if not AIPerception.can_hear(global_position, pos, radius, profile):
		return
	last_noise_pos = pos
	if source is Node3D and source.is_in_group("player"):
		target = source
		last_known_pos = (source as Node3D).global_position
		has_last_known = true
	if awareness < 1.0:
		awareness = maxf(awareness, profile.gunshot_awareness)
	send_event("heard_" + kind)

func _on_damaged(info: DamageInfo) -> void:
	if is_dead():
		return
	var src := info.source as Node3D
	if src != null and src != self:
		last_noise_pos = src.global_position
		if src.is_in_group("player"):
			target = src
			last_known_pos = src.global_position
			has_last_known = true
			awareness = 1.0
	send_event("damaged")

func _on_died(_info: DamageInfo) -> void:
	_events.clear()
	fsm.force("dead", "died")

# --- main loop ----------------------------------------------------------------

func _physics_process(delta: float) -> void:
	if is_dead():
		_apply_motion(delta, Vector3.ZERO)
		return
	if target == null:
		target = get_tree().get_first_node_in_group("player") as Node3D
	_update_perception(delta)
	fsm.tick(delta)
	_process_events()
	_tick_state(delta)
	_process_events()
	_apply_motion(delta, _desired_velocity())
	_update_visual()

## Drive the locomotion clip of the SK_NPC model from the actual planar speed and the FSM
## state (dead -> freeze, aiming states -> aim clips, otherwise idle/walk/run).
func _update_visual() -> void:
	if visual == null:
		return
	var speed := Vector2(velocity.x, velocity.z).length()
	visual.set_speed(speed)
	visual.set_aiming(fsm.state == "engage" or fsm.state == "take_cover" or fsm.state == "in_cover")
	visual.set_crouching(false)
	visual.set_dead(is_dead())
	visual.update_generic(get_physics_process_delta_time())

func _process_events() -> void:
	var guard := 0
	while not _events.is_empty() and guard < 8 and not is_dead():
		guard += 1
		fsm.send(_events.pop_front())
	_events.clear()

func _target_dead() -> bool:
	return target != null and target.has_method("is_dead") and target.is_dead()

func _update_perception(delta: float) -> void:
	target_visible = false
	var dist := INF
	if target != null and not _target_dead():
		var pts := target_points(target)
		var eye := get_eye_pos()
		dist = eye.distance_to(pts[1])
		var noticeable := AIPerception.in_view_cone(eye, get_forward(), pts[1], profile.fov_deg, profile.view_distance) \
			or dist <= profile.near_awareness_radius
		if noticeable:
			for p in pts:
				if has_los(eye, p):
					target_visible = true
					break
	if target_visible:
		visible_time += delta
		unseen_time = 0.0
		last_known_pos = target.global_position
		has_last_known = true
		var gain := AIPerception.awareness_rate(dist, profile)
		if fsm.state != profile.initial_state:
			gain *= profile.alert_gain_multiplier
		awareness = minf(awareness + gain * delta, 1.0)
		send_event("target_spotted" if awareness >= 1.0 else "suspicious")
	else:
		visible_time = 0.0
		var hiding := fsm.state == "in_cover" and cover_phase == "hide"
		if not hiding:
			unseen_time += delta
		if awareness < 1.0:
			awareness = maxf(awareness - profile.awareness_decay * delta, 0.0)
		elif unseen_time >= profile.lose_target_time:
			send_event("target_lost")
	if _target_dead() and awareness >= 1.0:
		awareness = 0.0
		send_event("target_dead")

func _on_state_changed(from: String, to: String, ev: String) -> void:
	if log_states:
		print("[AI] %s: %s --%s--> %s (t=%d)" % [name, from, ev, to, Engine.get_physics_frames()])
	_exit_state(from)
	_enter_state(to, from, ev)
	state_changed.emit(from, to, ev)

func _exit_state(_s: String) -> void:
	pass  # cover is released by the entered state (engage/search/idle/flee/dead) so engage can blacklist it

func _enter_state(s: String, _from: String, ev: String) -> void:
	_face_point = null
	match s:
		"idle":
			_set_crouch(false)
			is_cowering = false
			awareness = 0.0
			has_last_known = false
			_bad_covers.clear()
			_release_cover()
			_route_wait = 0.0
			_stop()
			if route != null and _from != "":
				_route_idx = _nearest_route_index()
		"alert":
			_stop()
			_face_point = last_known_pos if has_last_known else last_noise_pos
		"investigate":
			_move_to(last_known_pos if has_last_known else last_noise_pos, profile.walk_speed)
		"engage":
			_set_crouch(false)
			_reaction_left = profile.reaction_time
			_burst_left = _rng.randi_range(profile.burst_min, profile.burst_max)
			_shot_timer = 0.0
			_cover_retry = 0.0
			if ev == "cover_compromised" and cover != null:
				_bad_covers.append(cover)
			_release_cover()
			_stop()
		"take_cover":
			_set_crouch(false)
			if cover == null:
				send_event("cover_lost")
			else:
				_move_to(cover.global_position, profile.run_speed)
		"in_cover":
			_stop()
			_peeks_without_los = 0
			_start_phase("hide")
		"search":
			_set_crouch(false)
			_release_cover()
			_move_to(last_known_pos, profile.run_speed)
			_look_timer = 0.0
		"flee":
			_release_cover()
			_start_flee()
		"dead":
			_stop()
			_release_cover()
			collision_layer = 0
			if hitboxes != null:
				hitboxes.set_enabled(false)
			pose.rotation_degrees.x = -80.0   # ragdoll-lite placeholder (T-GP-02b)
			remove_from_group(AIPerception.HEARING_GROUP)
			died.emit()

func _tick_state(delta: float) -> void:
	match fsm.state:
		"idle":
			_tick_route(delta)
		"alert":
			_face_point = last_known_pos if (has_last_known and target_visible) else _face_point
		"investigate", "search":
			if not _moving:
				_look_timer += delta
				var a := _look_timer * 1.2
				_face_point = global_position + Vector3(sin(a), 0, cos(a)) * 5.0   # look around
		"engage":
			_tick_engage(delta)
		"take_cover":
			if cover == null or not cover.is_free_for(self):
				send_event("cover_lost")
			elif _flat_dist(cover.global_position) <= profile.cover_arrive_distance or (not _moving and _flat_dist(cover.global_position) < 1.2):
				send_event("arrived")
			elif target_visible:
				_face_point = null
		"in_cover":
			_tick_cover(delta)
		"flee":
			if not _moving and not is_cowering:
				is_cowering = true
				_set_crouch(true)

func _tick_route(delta: float) -> void:
	if route == null:
		return
	var pts := route.get_points()
	if pts.is_empty():
		return
	if _route_wait > 0.0:
		_route_wait -= delta
		return
	var p: Vector3 = pts[_route_idx % pts.size()]
	if _flat_dist(p) < 1.0:  # >= NavigationAgent3D target_desired_distance (0.75)
		_route_wait = profile.route_idle_time
		_route_idx = route.next_index(_route_idx)
		_stop()
	elif not _moving or _move_target.distance_to(p) > 0.1:
		_move_to(p, profile.walk_speed)

func _nearest_route_index() -> int:
	var pts := route.get_points()
	var best := 0
	for i in pts.size():
		if _flat_dist(pts[i]) < _flat_dist(pts[best]):
			best = i
	return best

func _tick_engage(delta: float) -> void:
	if target == null:
		return
	_face_point = target.global_position if target_visible else last_known_pos
	if profile.use_cover:
		_cover_retry -= delta
		if _cover_retry <= 0.0:
			_cover_retry = profile.cover_retry_interval
			var c := find_cover()
			if c != null:
				_claim_cover(c)
				send_event("cover_found")
				return
	var d := _flat_dist(target.global_position)
	if target_visible and d <= profile.max_engage_distance:
		_stop()
		_combat_fire(delta)
	else:
		_move_to(last_known_pos, profile.run_speed)

func _tick_cover(delta: float) -> void:
	if target != null:
		_face_point = target.global_position
	_phase_left -= delta
	if cover_phase == "hide":
		if target != null and not _target_dead():
			var eye: Vector3 = target_points(target)[0]
			if not is_cover_protected(cover.global_position, eye):
				send_event("cover_compromised")
				return
		if weapon != null and weapon.data != null and not weapon.is_reloading \
				and weapon.ammo < int(ceil(weapon.data.magazine_size * profile.reload_threshold)):
			weapon.start_reload()
		if _phase_left <= 0.0 and (weapon == null or not weapon.is_reloading):
			_start_phase("peek")
	else:
		if target_visible:
			_peek_had_los = true
			_combat_fire(delta)
		if _phase_left <= 0.0:
			if _peek_had_los:
				_peeks_without_los = 0
			else:
				_peeks_without_los += 1
				if _peeks_without_los >= profile.peeks_without_los_to_relocate:
					send_event("cover_compromised")
					return
			_start_phase("hide")

func _start_phase(ph: String) -> void:
	cover_phase = ph
	if ph == "hide":
		_set_crouch(true)
		_phase_left = _rng.randf_range(profile.cover_hide_min, profile.cover_hide_max)
	else:
		_set_crouch(false)
		_phase_left = _rng.randf_range(profile.cover_peek_min, profile.cover_peek_max)
		_peek_had_los = false
		_reaction_left = profile.reaction_time
		_burst_left = _rng.randi_range(profile.burst_min, profile.burst_max)
		_shot_timer = 0.0

## Bursts at the target with AI aim error on top of the weapon's hip spread.
func _combat_fire(delta: float) -> void:
	if weapon == null or weapon.data == null or target == null:
		return
	if _reaction_left > 0.0:
		_reaction_left -= delta
		return
	_shot_timer -= delta
	if _shot_timer > 0.0 or weapon.is_reloading:
		return
	if weapon.ammo <= 0:
		weapon.start_reload()
		return
	var eye := get_eye_pos()
	var pts := target_points(target)
	var aim_pt: Vector3 = pts[1] if has_los(eye, pts[1]) else pts[0]
	var dir := (aim_pt - eye).normalized()
	var tv := Vector3.ZERO
	if target is CharacterBody3D:
		tv = (target as CharacterBody3D).velocity
	var err := AIPerception.aim_error_deg(profile, eye.distance_to(aim_pt), Vector2(tv.x, tv.z).length(), visible_time)
	var shot := weapon.trigger(true, true, eye, AIPerception.apply_cone(dir, err, _rng), {}, self, _self_rids)
	if shot.is_empty():
		return
	shots_fired += 1
	last_aim_error = err
	shot["ai_aim_error_deg"] = err
	shot["ai_aim_point"] = aim_pt
	shot_fired.emit(shot)
	_burst_left -= 1
	if _burst_left <= 0:
		_burst_left = _rng.randi_range(profile.burst_min, profile.burst_max)
		_shot_timer = _rng.randf_range(profile.burst_pause_min, profile.burst_pause_max)
	else:
		_shot_timer = maxf(profile.burst_shot_interval, weapon.data.get_fire_interval())

func _start_flee() -> void:
	_set_crouch(false)
	is_cowering = false
	var away := global_position - last_noise_pos
	away.y = 0.0
	away = away.normalized() if away.length() > 0.1 else -get_forward()
	var map := get_world_3d().navigation_map
	var start_d := global_position.distance_to(last_noise_pos)
	var best_d := -1.0
	var best := global_position
	for ang in [0.0, 30.0, -30.0, 60.0, -60.0, 90.0, -90.0]:
		var cand := global_position + away.rotated(Vector3.UP, deg_to_rad(ang)) * profile.flee_distance
		var p := NavigationServer3D.map_get_closest_point(map, cand)
		var dd := p.distance_to(last_noise_pos)
		if dd > best_d:
			best_d = dd
			best = p
	if best_d - start_d < profile.cower_if_gain_below:
		_stop()
		is_cowering = true
		_set_crouch(true)
	else:
		_move_to(best, profile.flee_speed)

# --- cover / pose / movement ----------------------------------------------------

func _claim_cover(c: CoverPoint) -> void:
	_release_cover()
	cover = c
	c.occupant = self

func _release_cover() -> void:
	if cover != null and cover.occupant == self:
		cover.occupant = null
	cover = null
	cover_phase = ""

func _set_crouch(on: bool) -> void:
	is_crouched = on
	if pose != null and not is_dead():
		pose.position.y = -profile.crouch_drop if on else 0.0

func _move_to(p: Vector3, speed: float) -> void:
	_move_target = p
	_move_speed = speed
	_moving = true
	agent.target_position = p

func _stop() -> void:
	_moving = false
	_move_speed = 0.0

func _flat_dist(p: Vector3) -> float:
	return Vector2(p.x - global_position.x, p.z - global_position.z).length()

func _desired_velocity() -> Vector3:
	if not _moving:
		return Vector3.ZERO
	if agent.is_navigation_finished():
		if _flat_dist(_move_target) < 1.0:
			_moving = false
			return Vector3.ZERO
	var nxt := agent.get_next_path_position()
	var d := nxt - global_position
	d.y = 0.0
	if d.length() < 0.05:
		if agent.is_navigation_finished():
			_moving = false
		return Vector3.ZERO
	return d.normalized() * _move_speed

func _apply_motion(delta: float, want: Vector3) -> void:
	var h := Vector3(velocity.x, 0, velocity.z).move_toward(want, profile.accel * delta)
	var vy := velocity.y
	if is_on_floor():
		vy = 0.0
	else:
		vy -= ProjectSettings.get_setting("physics/3d/default_gravity", 9.8) * delta
	velocity = Vector3(h.x, vy, h.z)
	move_and_slide()
	if is_dead():
		return
	var face := Vector3.ZERO
	if _face_point != null:
		face = (_face_point as Vector3) - global_position
	elif h.length() > 0.2:
		face = h
	face.y = 0.0
	if face.length() > 0.05:
		var want_yaw := atan2(face.x, face.z)
		rotation.y = rotate_toward(rotation.y, want_yaw, profile.turn_rate * delta)
