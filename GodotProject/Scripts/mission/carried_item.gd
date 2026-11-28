# UNDERWORLD - carried mission item (T-MIS-01, M01 package).
#
# The package crate is a real object with 200 HP once it is picked up. It can be:
#   * CARRIED  - attached in front of Jason; he cannot sprint
#   * ON_GROUND- dropped (or spawned on the garage bench before pickup)
#   * LOADED   - placed in the car boot; the car carries it
# It follows the carrier by snapping to a hand offset every physics frame (no soft body);
# that keeps it deterministic and testable headless.
class_name CarriedItem
extends Node3D

signal picked_up(by: Node3D)
signal dropped(position: Vector3)
signal loaded_into(vehicle: Node3D)
signal unloaded(position: Vector3)
signal destroyed

enum State { ON_GROUND, CARRIED, LOADED }

## DamageReceiver child (200 HP per M01 design). Optional.
@export var health_path: NodePath = ^"DamageReceiver"
## Where the item sits relative to the carrier (2-handed carry pose, chest height).
@export var carry_offset := Vector3(0.0, 1.05, 0.42)
## Where the item sits inside a vehicle (boot, relative to the vehicle origin).
@export var vehicle_offset := Vector3(0.0, 0.75, -1.55)
## Distance beyond which a carried/loaded item counts as "left behind" (M01: 60 m).
@export var stray_distance := 60.0
## Tag used by MissionManager to find this item in the level.
@export var tag := &"package"

var state: State = State.ON_GROUND
var carrier: Node3D = null
var vehicle: Node3D = null
var health: DamageReceiver
var _destroyed := false
var _home_transform := Transform3D.IDENTITY

func _ready() -> void:
	add_to_group(&"mission_items")
	health = get_node_or_null(health_path) as DamageReceiver
	if health != null:
		health.died.connect(_on_health_died)
	_home_transform = global_transform

func is_carried() -> bool:
	return state == State.CARRIED

func is_loaded() -> bool:
	return state == State.LOADED

func is_held() -> bool:
	return state == State.CARRIED or state == State.LOADED

func pick_up(by: Node3D) -> bool:
	if _destroyed or state == State.CARRIED:
		return false
	if state == State.LOADED:
		return false
	state = State.CARRIED
	_sync_world_collision()
	carrier = by
	vehicle = null
	top_level = true
	# Dropping the parent keeps the world transform stable across the reparent.
	picked_up.emit(by)
	_set_carrier_carrying(by, true)
	_snap_to_carrier()
	return true

func drop() -> bool:
	if state != State.CARRIED:
		return false
	var pos := global_position
	_set_carrier_carrying(carrier, false)
	state = State.ON_GROUND
	_sync_world_collision()
	carrier = null
	top_level = false
	dropped.emit(pos)
	return true

func load_into(car: Node3D) -> bool:
	if _destroyed:
		return false
	if state == State.LOADED:
		return false
	_set_carrier_carrying(carrier, false)
	state = State.LOADED
	_sync_world_collision()
	vehicle = car
	carrier = null
	top_level = true
	loaded_into.emit(car)
	_snap_to_vehicle(car)
	return true

func unload(pos: Vector3) -> void:
	if state != State.LOADED:
		return
	state = State.ON_GROUND
	_sync_world_collision()
	vehicle = null
	top_level = false
	global_position = pos
	unloaded.emit(pos)

## Distance from the package to the player who has to bring it along.
##
## While the package is *carried* it is parented to the carrier (it snaps to his hands every
## physics frame), so measuring against the carrier would always be 0 - the "left > 60 m behind"
## fail (Docs/Missions/M01_DeadDrop.md) could never trigger. The meaningful reference is the
## player: he may walk away and leave the crate standing on the bench. Once loaded into the car
## the reference is the car itself (a stopped car does not "leave the package behind").
func distance_from_holder(player: Node3D = null) -> float:
	if state == State.CARRIED and player != null:
		return global_position.distance_to(player.global_position)
	var holder: Node3D = carrier if carrier != null else vehicle
	if holder == null:
		return 0.0
	var p := (holder as Node3D).global_position
	return Vector2(p.x - global_position.x, p.z - global_position.z).length()

## T-GP-04: the two-handed Carry clips replace locomotion while the carrier holds the item.
## Set on pickup/drop, so the visual never has to poll the mission state.
func _set_carrier_carrying(by: Node3D, on: bool) -> void:
	if by == null or not is_instance_valid(by):
		return
	var vis = by.get("visual")
	if vis is CharacterVisual:
		(vis as CharacterVisual).carrying = on


func _physics_process(_delta: float) -> void:
	if state == State.CARRIED and is_instance_valid(carrier):
		# B-M01-02 (T-BUILD-02): nothing loaded the package when Jason got into the car, so the
		# DELIVER objective (requires a LOADED package) could never complete in real play.
		var ride = carrier.get("vehicle")
		if ride is Node3D and is_instance_valid(ride) and not _sabotage_autoload():
			load_into(ride)
			return
		_snap_to_carrier()
	elif state == State.LOADED and is_instance_valid(vehicle):
		_snap_to_vehicle(vehicle)

## B-M01-06 (T-BUILD-02): the crate's imported static collision (UCX_ hull) stayed solid while
## the item was snapped in front of Jason every frame - he climbed onto his own package (seen at
## y = 2.8 m in the playthrough), and in the boot it would fight the car body. Solid only on
## the ground; the Interact area and the DamageReceiver (hit by hitscan) are unaffected.
var _world_layers: Dictionary = {}

func _sync_world_collision() -> void:
	var solid := state == State.ON_GROUND
	for n in find_children("*", "CollisionObject3D", true, false):
		var co := n as CollisionObject3D
		if co is Area3D:
			continue
		if not _world_layers.has(co):
			_world_layers[co] = co.collision_layer
		co.collision_layer = _world_layers[co] if solid else 0

## Negative control (UW_PLAYTHROUGH_SABOTAGE=2): the package stays "carried" inside the car,
## the shipped bug. Debug builds only (TD-020).
static func _sabotage_autoload() -> bool:
	return OS.is_debug_build() and OS.get_environment("UW_PLAYTHROUGH_SABOTAGE").strip_edges() == "2"

func _snap_to_carrier() -> void:
	if not is_instance_valid(carrier):
		return
	var basis := (carrier as Node3D).global_transform.basis.orthonormalized()
	global_transform = Transform3D(basis, (carrier as Node3D).global_position + basis * carry_offset)

func _snap_to_vehicle(car: Node3D) -> void:
	var basis := car.global_transform.basis.orthonormalized()
	global_transform = Transform3D(basis, car.global_position + basis * vehicle_offset)

func _on_health_died(_info: DamageInfo) -> void:
	_destroyed = true
	_set_carrier_carrying(carrier, false)
	state = State.ON_GROUND
	_sync_world_collision()
	destroyed.emit()

## Restore the pre-mission state (checkpoint restart / tests).
func reset_item() -> void:
	_destroyed = false
	state = State.ON_GROUND
	_sync_world_collision()
	carrier = null
	vehicle = null
	top_level = false
	global_transform = _home_transform
	visible = true
	if health != null:
		health.reset()
