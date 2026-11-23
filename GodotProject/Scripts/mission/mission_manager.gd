# UNDERWORLD - data-driven mission framework (T-MIS-01).
#
# MissionManager walks an ordered ObjectiveData list (MissionData resource) and completes each
# objective from real gameplay events - never from timers unless the objective asks for one:
#   ENTER_AREA / REACH / DELIVER -> the player (or the car with the package) enters an Area3D
#   SURVIVE                      -> every node in `target_group` is dead
#   INTERACT                     -> Interactable.try_interact(player)
#   NONE                         -> debug_complete_current() or auto_seconds
#
# Fail states (M01): player death, package destroyed / left > 60 m behind, mission car destroyed.
# On fail the manager restores the last checkpoint: player transform + health, car transform +
# health, package state, and rewinds to the checkpoint objective.
#
# Contract: Docs/Missions/M01_DeadDrop.md. Areas are Area3D nodes named exactly as in the design.
# Tests: GodotProject/Tests/test_mission.gd. Headless stepping: debug_complete_current().
class_name MissionManager
extends Node

signal mission_started(mission: MissionData)
signal objective_started(index: int, objective: ObjectiveData)
signal objective_completed(index: int, objective: ObjectiveData)
signal mission_completed(mission: MissionData, cash: int)
signal mission_failed(reason: String)
signal checkpoint_saved(index: int)
signal subtitle(speaker: String, text: String)
signal objective_text_changed(text: String)

enum State { IDLE, RUNNING, FAILED, COMPLETED }

const PLAYER_GROUP := &"player"
const VEHICLE_GROUP := &"vehicles"

@export var mission: MissionData
## Root that holds the mission areas / markers (usually the level scene). Defaults to the level.
@export var level_root: NodePath = ^".."
## Fail if the carried/loaded package is farther than this from Jason / the car (M01: 60 m).
@export var package_stray_distance := 60.0
## Seconds the player may stay dead before the fail screen counts as a restart (0 = instant).
@export var fail_delay := 1.2

var state: State = State.IDLE
var current_index := -1
## Index of the objective to rewind to on fail (-1 = mission start).
var checkpoint_index := -1
var fail_reason := ""
var elapsed := 0.0
var level: Node
var player: Node3D
var player_health: DamageReceiver
var mission_car: Vehicle
## True once the crate was picked up; gates the "left behind" failure.
var _package_ever_held := false
var package: CarriedItem
var spawn_groups: Dictionary = {}       # index -> Array[Node]
## M01 wave bookkeeping (T-MIS-01b). wave_groups maps the wave id ("1", "2") to its enemies.
## The ORDER is data: wave 2 is only released once wave 1 is completely dead.
var wave_groups: Dictionary = {}        # String -> Array[Node]
var waves_released: Array[String] = []  # waves that have been activated, in order
## Marco, the ally companion (seated on entry, fights after the ambush trigger).
var ally: AllyCompanion
var ally_seated := false
## Sabotage hooks for the negative controls (UW_MISSION_SABOTAGE=2/3). They corrupt the real
## data/behaviour under test instead of adding a self-referential check.
var sabotage := 0
var _hold := 0.0
var _auto_left := 0.0
var _subtitle_queue: Array[Dictionary] = []
var _subtitle_left := 0.0
var _fail_timer := 0.0
var _saved := {}
var _rng := RandomNumberGenerator.new()

func _ready() -> void:
	add_to_group(&"mission_manager")
	level = get_node_or_null(level_root)
	if level == null:
		level = get_parent()
	_rng.seed = 0

# --- public API ---------------------------------------------------------------

func start() -> bool:
	if mission == null or mission.objectives.is_empty():
		push_error("MissionManager: no MissionData")
		return false
	sabotage = int(OS.get_environment("UW_MISSION_SABOTAGE")) if OS.get_environment("UW_MISSION_SABOTAGE") != "" else 0
	_resolve_cast()
	ally = _resolve_ally()
	_prepare_waves()
	_snapshot_initial()
	state = State.RUNNING
	elapsed = 0.0
	current_index = -1
	checkpoint_index = -1
	# Marco is on the passenger seat from the first frame of the mission (design: he is already
	# outside / in the car when Sam calls).
	seat_ally()
	mission_started.emit(mission)
	_advance()
	return true

## Debug/test API (mission design contract): complete the current objective now.
func debug_complete_current() -> void:
	if state != State.RUNNING:
		return
	_complete_current()

## Skip straight to an objective index (tests / debugging).
func debug_set_objective(index: int) -> void:
	if state != State.RUNNING and state != State.IDLE:
		return
	while current_index < index - 1 and state != State.COMPLETED:
		if current_index < 0:
			break
		_complete_current(false)
	_finish_current(false)
	current_index = index - 1
	_advance()

func objective_text() -> String:
	if mission == null or current_index < 0 or current_index >= mission.objectives.size():
		return ""
	return mission.objectives[current_index].text

func current_objective() -> ObjectiveData:
	if mission == null or current_index < 0 or current_index >= mission.objectives.size():
		return null
	return mission.objectives[current_index]

## 0..1 progress for the HUD (objectives done / total).
func progress() -> float:
	if mission == null or mission.objectives.is_empty():
		return 0.0
	return clampf(float(current_index) / float(mission.objectives.size()), 0.0, 1.0)

func fail(reason: String) -> void:
	if state != State.RUNNING:
		return
	state = State.FAILED
	fail_reason = reason
	_fail_timer = fail_delay
	mission_failed.emit(reason)

## Restart from the last checkpoint (or the mission start).
func restart_from_checkpoint() -> void:
	if mission == null:
		return
	var idx := checkpoint_index
	state = State.RUNNING
	fail_reason = ""
	_restore_checkpoint()
	current_index = idx
	_hold = 0.0
	_auto_left = 0.0
	_advance()

# --- per-frame ----------------------------------------------------------------

func _physics_process(delta: float) -> void:
	if state == State.FAILED:
		_fail_timer -= delta
		if _fail_timer <= 0.0:
			restart_from_checkpoint()
		return
	_tick_subtitles(delta)
	if state != State.RUNNING:
		return
	elapsed += delta
	_check_failure_conditions()
	if state != State.RUNNING:
		return
	_tick_wave_release()
	var obj := current_objective()
	if obj == null:
		return
	if obj.auto_seconds > 0.0:
		_auto_left -= delta
		if _auto_left <= 0.0:
			_complete_current()
			return
	if obj.hold_seconds > 0.0:
		if _requirement_met(obj):
			_hold += delta
			if _hold >= obj.hold_seconds:
				_complete_current()
		else:
			_hold = 0.0
		return
	if _requirement_pollable(obj) and _requirement_met(obj):
		_complete_current()

# --- objective machinery ------------------------------------------------------

func _advance() -> void:
	current_index += 1
	_hold = 0.0
	if mission == null or current_index >= mission.objectives.size():
		_finish_mission()
		return
	var obj := mission.objectives[current_index]
	_auto_left = obj.auto_seconds
	_collect_spawn_group(current_index, obj)
	_apply_wave_gate(obj)
	_play_subtitles(obj)
	objective_text_changed.emit(obj.text)
	objective_started.emit(current_index, obj)
	if obj.auto_seconds > 0.0 and obj.auto_seconds <= 0.0:
		_complete_current()

func _complete_current(_announce := true) -> void:
	if state != State.RUNNING or current_index < 0:
		return
	var obj := mission.objectives[current_index]
	objective_completed.emit(current_index, obj)
	_release_on_complete(obj)
	if obj.checkpoint:
		checkpoint_index = current_index
		_save_checkpoint()
		checkpoint_saved.emit(current_index)
	_advance()

func _finish_current(_announce := true) -> void:
	pass

func _finish_mission() -> void:
	state = State.COMPLETED
	if mission != null:
		mission_completed.emit(mission, mission.reward_cash)

## Requirement checks that can be evaluated every frame (no events).
func _requirement_pollable(obj: ObjectiveData) -> bool:
	match obj.kind:
		ObjectiveData.Kind.SURVIVE:
			return true
		ObjectiveData.Kind.ENTER_AREA, ObjectiveData.Kind.REACH, ObjectiveData.Kind.DELIVER:
			return true
	return false

func _requirement_met(obj: ObjectiveData) -> bool:
	match obj.kind:
		ObjectiveData.Kind.SURVIVE:
			# "Survive the ambush" is only done when BOTH waves are dead: the target group is
			# mission_enemies (all five), and requires_group_cleared pins the ordering to
			# wave 1 -> wave 2 as data (M01_DeadDrop.tres).
			if not obj.requires_group_cleared.is_empty() and not _group_dead(obj.requires_group_cleared):
				return false
			return _group_dead(obj.target_group)
		ObjectiveData.Kind.ENTER_AREA, ObjectiveData.Kind.REACH, ObjectiveData.Kind.DELIVER:
			return _area_occupied(obj)
		ObjectiveData.Kind.INTERACT:
			var it := _node(obj.target_path) as Interactable
			return it == null or (it.used and it.one_shot)
	return false

func _area_occupied(obj: ObjectiveData) -> bool:
	var target := _node(obj.target_path)
	# "Get in the car." targets the sedan itself, not an Area3D. Treat a vehicle target as
	# satisfied once it has a driver (design: M01 objective 1 = enter the car).
	if target is Vehicle:
		var car := target as Vehicle
		return car.driver != null
	var area := target as Area3D
	if area == null:
		return false
	if obj.kind == ObjectiveData.Kind.DELIVER and obj.requires_package:
		if package == null or not package.is_loaded():
			return false
		if mission_car != null and area.overlaps_body(mission_car):
			return true
		return false
	if player != null and area.overlaps_body(player):
		return true
	# Player may be riding: accept the car he is driving.
	if mission_car != null and mission_car.driver != null and area.overlaps_body(mission_car):
		return true
	return false

func _group_dead(group: StringName) -> bool:
	var nodes := get_tree().get_nodes_in_group(group)
	for n in nodes:
		if n == null or not is_instance_valid(n):
			continue
		var h := _find_health(n)
		if h != null and not h.is_dead:
			return false
		if h == null and n is Node3D and (n as Node3D).is_inside_tree():
			return false
	return true

func _collect_spawn_group(index: int, obj: ObjectiveData) -> void:
	if obj.kind != ObjectiveData.Kind.SURVIVE:
		return
	var nodes: Array = []
	for n in get_tree().get_nodes_in_group(String(obj.target_group)):
		if is_instance_valid(n):
			nodes.append(n)
	spawn_groups[index] = nodes

# --- waves (T-MIS-01b) ---------------------------------------------------------

## Collect every MissionEnemy by wave at mission start and make sure none of them is live yet
## unless the mission data says so. The enemies in the level are built inactive; this is what
## keeps a *reloaded* scene honest as well.
func _prepare_waves() -> void:
	wave_groups.clear()
	waves_released.clear()
	for n in get_tree().get_nodes_in_group(&"mission_enemy"):
		var e := n as MissionEnemy
		if e == null or not is_instance_valid(e):
			continue
		var key := str(e.wave)
		if not wave_groups.has(key):
			wave_groups[key] = []
		wave_groups[key].append(e)
	if sabotage == 2:
		# Negative control: "wave 2 starts immediately". The ordering rule that wave 2 only
		# comes after wave 1 is *disabled* in the production gate, so both waves are live from
		# the first frame. The ordinary checks ("wave 2 is NOT active while wave 1 fights" and
		# "objective 4 still running after wave 1 died") must then FAIL.
		release_wave("1")
		release_wave("2")
		return
	# Wave 1 is the one that is armed by the ambush trigger; wave 2 stays cold until released.
	_deactivate_wave("1")
	_deactivate_wave("2")

## Wave keys are the bare numbers ("1", "2"); the mission data refers to them by their group
## names ("wave1", "wave2") because that is what it also uses for the node groups.
func _wave_key(id: String) -> String:
	return id.trim_prefix("wave") if id.begins_with("wave") else id


func _deactivate_wave(id: String) -> void:
	id = _wave_key(id)
	for n in wave_groups.get(id, []):
		var e := n as MissionEnemy
		if e != null and not e.is_dead():
			e.deactivate()

## Activate a wave once. Returns true if it was cold before (so callers can tell "first time").
func release_wave(id: String) -> bool:
	id = _wave_key(id)
	if waves_released.has(id):
		return false
	for n in wave_groups.get(id, []):
		var e := n as MissionEnemy
		if e != null and is_instance_valid(e) and not e.is_dead():
			e.activate()
	waves_released.append(id)
	return true

func are_wave_dead(id: String) -> bool:
	var nodes: Array = wave_groups.get(_wave_key(id), [])
	if nodes.is_empty():
		return false
	for n in nodes:
		var e := n as MissionEnemy
		if e != null and is_instance_valid(e) and not e.is_dead():
			return false
	return true

## Wave gate driven purely by the objective data:
##   hold_group    -> that wave is NOT live while this objective runs
##   release_group -> this wave is released when this objective *completes*
func _apply_wave_gate(obj: ObjectiveData) -> void:
	if obj == null:
		return
	# Objective 4 ("Survive the ambush") must not start with wave 2 already walking around:
	# re-assert the hold in case something (a checkpoint restore, a test) revived it.
	if not obj.hold_group.is_empty():
		var hold := String(obj.hold_group)
		if not waves_released.has(hold) and sabotage != 2:
			_deactivate_wave(hold)
	elif obj.kind == ObjectiveData.Kind.SURVIVE:
		# The ambush objective arms wave 1 the moment it starts.
		release_wave("1")
	if not obj.release_group.is_empty():
		release_wave(String(obj.release_group))

## The sequencing BETWEEN waves is also data: the SURVIVE objective holds wave 2 and names
## wave 1 as `requires_group_cleared`, so wave 2 goes live the moment wave 1 is wiped out -
## not when the objective completes (which needs both waves dead).
func _tick_wave_release() -> void:
	var obj := current_objective()
	if obj == null or obj.hold_group.is_empty() or obj.requires_group_cleared.is_empty():
		return
	var hold := String(obj.hold_group)
	if waves_released.has(hold):
		return
	if _group_dead(obj.requires_group_cleared):
		release_wave(hold)


func _release_on_complete(obj: ObjectiveData) -> void:
	if obj == null or obj.release_group.is_empty():
		return
	release_wave(String(obj.release_group))

# --- ally (T-MIS-01b) ----------------------------------------------------------

## Marco starts in the passenger seat. He is invulnerable in M1 and never targets Jason.
func _resolve_ally() -> AllyCompanion:
	for n in get_tree().get_nodes_in_group(&"marco"):
		var a := n as AllyCompanion
		if a != null:
			return a
	return null

func seat_ally() -> bool:
	if ally == null:
		ally = _resolve_ally()
	if ally == null or mission_car == null:
		return false
	if sabotage == 3:
		# Negative control: Marco becomes killable. The real checks look at
		# DamageReceiver.invulnerable / take a shot and expect him to survive.
		if ally.health != null:
			ally.health.invulnerable = false
	else:
		if ally.health != null:
			ally.health.invulnerable = true
	ally_seated = ally.board(mission_car)
	return ally_seated

## Marco gets out with Jason once the car stops at the garage and rejoins after the package is
## picked up. Called by the mission flow (NOT on a timer) at the objectives that say so.
func unseat_ally() -> bool:
	if ally == null or not ally_seated or mission_car == null:
		return false
	var at := mission_car.get_socket(&"SOCKET_Exit_Right")
	var xf := mission_car.global_transform
	if at != null:
		xf = at.global_transform
	mission_car.leave_passenger()
	ally.unboard(mission_car, Transform3D(Basis(Vector3.UP, xf.basis.get_euler().y), xf.origin))
	ally_seated = false
	return true

# --- interaction entry point --------------------------------------------------

## Called by the player (or tests) when the interact action is pressed.
func try_interact(by: Node3D) -> bool:
	var obj := current_objective()
	if obj == null or obj.kind != ObjectiveData.Kind.INTERACT:
		return _try_nearest_interactable(by)
	var it := _node(obj.target_path) as Interactable
	if it != null and it.try_interact(by):
		_on_interacted(it, by)
		return true
	return _try_nearest_interactable(by)

func _try_nearest_interactable(by: Node3D) -> bool:
	var best: Interactable = null
	var best_d := INF
	for n in get_tree().get_nodes_in_group(&"interactables"):
		var it := n as Interactable
		if it == null or not it.can_interact(by):
			continue
		var d := it.global_position.distance_to(by.global_position)
		if d < best_d and d <= 3.0:
			best_d = d
			best = it
	if best != null and best.try_interact(by):
		_on_interacted(best, by)
		return true
	return false

func _on_interacted(it: Interactable, by: Node3D) -> void:
	# The M01 package: an Interactable on the same node as a CarriedItem.
	var item := it.get_parent() as CarriedItem
	if item == null:
		item = it.get_node_or_null("..") as CarriedItem
	if item == null:
		for n in get_tree().get_nodes_in_group(&"mission_items"):
			var ci := n as CarriedItem
			if ci != null and ci.global_position.distance_to(it.global_position) <= 2.0:
				item = ci
				break
	if item != null:
		item.pick_up(by)
		if item == package or package == null:
			package = item
			_wire_package()
	_check_interact_objective()

func _check_interact_objective() -> void:
	var obj := current_objective()
	if obj != null and obj.kind == ObjectiveData.Kind.INTERACT:
		var it := _node(obj.target_path) as Interactable
		if it == null or it.used:
			_complete_current()

# --- failures -----------------------------------------------------------------

func _check_failure_conditions() -> void:
	if player_health != null and player_health.is_dead:
		fail("Jason died")
		return
	if package != null:
		if package.health != null and package.health.is_dead:
			fail("Package destroyed")
			return
		# "Left > 60 m behind" (Docs/Missions/M01_DeadDrop.md): once the crate has been picked up
		# it has to stay with the player. While carried it is parented to him; while loaded it
		# rides in the car; if he drops it or drives off without it, the mission fails.
		if package.is_held():
			_package_ever_held = true
		if _package_ever_held:
			var ref: Node3D = package.vehicle if package.is_loaded() else player
			if is_instance_valid(ref) and package.global_position.distance_to(ref.global_position) > package_stray_distance:
				fail("Package left behind")
				return
	if mission_car != null and mission_car.health <= 0.0:
		fail("Sedan destroyed")
		return

# --- checkpoints --------------------------------------------------------------

func _snapshot_initial() -> void:
	_saved.clear()
	_saved["player_pos"] = player.global_position if player != null else Vector3.ZERO
	if player_health != null:
		_saved["player_health"] = player_health.health
	if mission_car != null:
		_saved["car_pos"] = mission_car.global_position
		_saved["car_basis"] = mission_car.global_transform.basis
		_saved["car_health"] = mission_car.health
	if package != null:
		_saved["pkg_state"] = package.state
		_saved["pkg_pos"] = package.global_position
		_saved["pkg_parent"] = package.carrier
		_saved["pkg_vehicle"] = package.vehicle

func _save_checkpoint() -> void:
	_snapshot_initial()

func _restore_checkpoint() -> void:
	if player != null and _saved.has("player_pos"):
		player.global_position = _saved["player_pos"]
		if "velocity" in player:
			player.set("velocity", Vector3.ZERO)
		if mission_car != null and _saved.has("pkg_vehicle") and _saved["pkg_vehicle"] == mission_car:
			player.global_position = _saved["car_pos"]
	if player_health != null:
		player_health.reset()
	if mission_car != null:
		if _saved.has("car_pos"):
			mission_car.global_transform = Transform3D(_saved["car_basis"], _saved["car_pos"])
			mission_car.linear_velocity = Vector3.ZERO
			mission_car.angular_velocity = Vector3.ZERO
		mission_car.health = _saved.get("car_health", mission_car.health)
	if package != null:
		package.reset_item()
	_revive_enemies()
	# Waves go back to their pre-ambush state; Marco back into the car.
	_prepare_waves()
	if not ally_seated:
		seat_ally()
	package = _find_package()
	_wire_package()

func _revive_enemies() -> void:
	for idx in spawn_groups.keys():
		for n in spawn_groups[idx]:
			if is_instance_valid(n) and n.has_method("revive"):
				n.revive()
	for key in wave_groups.keys():
		for n in wave_groups[key]:
			if is_instance_valid(n) and n.has_method("revive"):
				n.revive()

# --- wiring helpers -----------------------------------------------------------

func _resolve_cast() -> void:
	var players := get_tree().get_nodes_in_group(PLAYER_GROUP)
	if not players.is_empty():
		player = players[0] as Node3D
		if player != null:
			player_health = player.get_node_or_null("Health") as DamageReceiver
	var cars := get_tree().get_nodes_in_group(VEHICLE_GROUP)
	if not cars.is_empty():
		mission_car = cars[0] as Vehicle
	package = _find_package()
	_wire_package()
	if player != null and player_health != null:
		if not player_health.died.is_connected(_on_player_died):
			player_health.died.connect(_on_player_died)

func _find_package() -> CarriedItem:
	for n in get_tree().get_nodes_in_group(&"mission_items"):
		var ci := n as CarriedItem
		if ci != null:
			return ci
	return null

func _wire_package() -> void:
	if package == null:
		return
	if package.health != null and not package.health.died.is_connected(_on_package_died):
		package.health.died.connect(_on_package_died)

func _on_player_died(_info: DamageInfo) -> void:
	if state == State.RUNNING:
		fail("Jason died")

func _on_package_died(_info: DamageInfo) -> void:
	if state == State.RUNNING:
		fail("Package destroyed")

func _find_health(n: Node) -> DamageReceiver:
	if n is DamageReceiver:
		return n as DamageReceiver
	var h := n.get_node_or_null("Health") as DamageReceiver
	if h != null:
		return h
	for c in n.get_children():
		if c is DamageReceiver:
			return c as DamageReceiver
	return null

func _node(path: NodePath) -> Node:
	if path.is_empty() or level == null:
		return null
	return level.get_node_or_null(path)

func _play_subtitles(obj: ObjectiveData) -> void:
	if obj.subtitles.is_empty():
		return
	for line in obj.subtitles:
		_subtitle_queue.append(line)
	if _subtitle_left <= 0.0 and not _subtitle_queue.is_empty():
		_show_next_subtitle()

func _show_next_subtitle() -> void:
	if _subtitle_queue.is_empty():
		return
	var line: Dictionary = _subtitle_queue.pop_front()
	_subtitle_left = float(line.get("seconds", 2.5))
	subtitle.emit(String(line.get("speaker", "")), String(line.get("text", "")))

func _tick_subtitles(delta: float) -> void:
	if _subtitle_left <= 0.0:
		return
	_subtitle_left -= delta
	if _subtitle_left <= 0.0 and not _subtitle_queue.is_empty():
		_show_next_subtitle()
