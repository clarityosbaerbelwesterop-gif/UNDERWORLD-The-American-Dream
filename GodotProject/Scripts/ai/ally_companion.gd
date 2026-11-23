# UNDERWORLD - Marco as the M01 ally companion (T-MIS-01b).
#
# Marco is an NPCController (so he shares locomotion, cover and the weapon) with three
# differences that the mission depends on, and that are all data/regel-driven, not special cases
# sprinkled through the AI:
#
#   * INVULNERABLE in M1. `DamageReceiver.invulnerable = true` + the marker below. Design
#     "Marco is not killable in M1 (ally death is out of scope)". MissionManager re-asserts it
#     every time the mission starts (see `MissionManager._resolve_ally`).
#   * Only ever shoots at `mission_enemies`. NPCController picks the first node in group
#     "player" as its target, which for an ally would be Jason - so a companion must never use
#     that default. `_acquire_target()` below only considers gunmen of the active wave, and
#     `_friendly_fire_guard()` refuses a shot whose ray would cross Jason.
#   * LOW ACCURACY: the profile carries `aim_error_deg` etc.; the ally profile multiplies it.
#     That is the documented "poor precision" of the design, expressed as data.
#
# Seating: Marco rides on the passenger seat (`SOCKET_Seat_Passenger`). The vehicle knows two
# roles now (driver / passenger), see Vehicle.enter_passenger(). A companion that is seated does
# not run its own physics - it is parented to the seat socket and asks the car to move itself.
class_name AllyCompanion
extends NPCController

signal seated(vehicle: Vehicle)
signal unseated(vehicle: Vehicle)

## Extra aim error applied on top of the profile (degrees). "Fights with poor precision."
@export var accuracy_penalty_deg := 6.0
## Never targeted by the enemy AI: an ally in the player's faction is not a mission enemy.
@export var is_ally := true

## The car Marco currently sits in (null while on foot).
var vehicle: Vehicle = null
## Marco's trust in the player's faction: nodes in these groups are never aimed at.
var friendly_groups: PackedStringArray = PackedStringArray(["player", "ally", "civilian", "ai_hearing"])


func _ready() -> void:
	super._ready()
	add_to_group(&"ally")
	add_to_group(&"marco")
	# M1: not killable. Belt and braces: the receiver flag is what actually stops damage.
	if health != null:
		health.invulnerable = true
	# The ally must never be treated as a mission enemy by the SURVIVE objective.
	remove_from_group(&"mission_enemies")


# --- seating ------------------------------------------------------------------

## Board the car's passenger seat. Returns false if the seat is taken or the car is gone.
func board(v: Vehicle) -> bool:
	if v == null or vehicle != null:
		return false
	if not v.enter_passenger(self):
		return false
	vehicle = v
	# A seated passenger is drawn by the car, not by its own CharacterBody: park the body,
	# keep its physics from fighting the vehicle and let the seat socket own the transform.
	set_physics_process(false)
	collision_layer = 0
	collision_mask = 0
	# No sit clip exists yet: drawing the standing pose on the seat put Marco's torso through
	# the roof (Phase 8 capture, Bot 1 review of PR #17). Hide him while seated, exactly like
	# PlayerController hides Jason in the driver's seat; unboard() shows him again.
	if pose != null:
		pose.visible = false
	seated.emit(v)
	return true


## Leave the seat and stand at `at` (the car's exit socket). Called by the vehicle sequence.
func unboard(v: Vehicle, at: Transform3D) -> void:
	if vehicle != v:
		return
	vehicle = null
	global_transform = Transform3D(Basis(Vector3.UP, at.basis.get_euler().y), at.origin)
	velocity = Vector3.ZERO
	collision_layer = 1 << 2
	collision_mask = 1 | 2 | 4 | 8
	set_physics_process(true)
	if pose != null:
		pose.visible = true
	unseated.emit(v)


func is_seated() -> bool:
	return vehicle != null


# --- combat rules -------------------------------------------------------------

## An ally never targets the player or any friendly. NPCController's default
## ("first node in group player") is exactly what we must NOT do here.
func _acquire_target() -> Node3D:
	var best: Node3D = null
	var best_d := INF
	for n in get_tree().get_nodes_in_group(&"mission_enemies"):
		var e := n as MissionEnemy
		if e == null or not e.is_active() or e.is_dead():
			continue
		# Only enemies Marco can plausibly see count; otherwise he would shoot walls.
		var d := global_position.distance_to(e.global_position)
		if d < best_d and d <= profile.view_distance:
			best_d = d
			best = e
	return best


func _is_friendly(node: Node) -> bool:
	if node == null:
		return true
	for g in friendly_groups:
		if node.is_in_group(g):
			return true
	# Jason's body/hitboxes and the mission car are friendly too.
	if node is Vehicle:
		return true
	return false


## Refuse a shot that would hit a friendly: casts the same ray the weapon would and checks what
## it hits first. Returns true when the shot is safe.
func _shot_is_safe(from: Vector3, dir: Vector3, dist: float) -> bool:
	var space := get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(from, from + dir * minf(dist, profile.view_distance), 1 | 8 | 16, _self_rids)
	var hit := space.intersect_ray(q)
	if hit.is_empty():
		return true
	var collider: Object = hit.get("collider")
	if collider == null:
		return true
	var node := collider as Node
	return not _is_friendly(node)


## Aim error used for Marco's shots: profile error plus the documented ally penalty.
func ally_aim_error(distance: float, target_speed: float, focus_time: float) -> float:
	return AIPerception.aim_error_deg(profile, distance, target_speed, focus_time) + accuracy_penalty_deg


## NPCController calls this for every shot; the ally adds its penalty on top.
func aim_error_deg_for(distance: float, target_speed: float) -> float:
	return super.aim_error_deg_for(distance, target_speed) + accuracy_penalty_deg


func _physics_process(delta: float) -> void:
	if is_seated():
		return
	if target == null:
		target = _acquire_target()
	elif _is_friendly(target) or (target.has_method("is_dead") and target.is_dead()):
		target = _acquire_target()
	super._physics_process(delta)
