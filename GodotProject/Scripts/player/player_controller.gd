# UNDERWORLD - third-person player controller (T-GP-01).
#
# Scene contract (see Scenes/Player/Player.tscn):
#   Player (CharacterBody3D, this script)
#   ├─ CollisionShape3D   capsule, origin of the body = feet (TD-004)
#   ├─ Visual             CharacterVisual: PT capsule now, SK_Jason.glb + AnimationTree later
#   └─ CameraRig          CameraRig (top_level): yaw -> Pitch -> SpringArm3D -> Camera3D
#
# Conventions: 1 unit = 1 m, Y up, model front = +Z (Vector3.MODEL_FRONT, TD-004).
# Only the Visual node is rotated to face movement/aim; the body itself never yaws,
# so the capsule collision and the camera rig are independent of facing.
#
# Input comes from the InputMap actions defined in project.godot
# (Scripts/tools/setup_input_map.gd). Tests drive it with Input.action_press().
class_name PlayerController
extends CharacterBody3D

signal jumped
signal landed(impact_speed: float)
signal aim_changed(aiming: bool)
signal crouch_changed(crouching: bool)
signal move_state_changed(state: MoveState)
## Emitted when the body was lifted onto a step (T-GP-01c).
signal stepped_up(height: float)
## Health reached 0 (T-AI-01): input is disabled; mission fail handling = T-MIS-01.
signal died

enum MoveState { IDLE, WALK, RUN, SPRINT, CROUCH, AIR }

@export_group("Speeds (m/s, match A_Jason_* clip speeds)")
@export var walk_speed := 1.4
@export var run_speed := 3.5
@export var sprint_speed := 6.0
@export var crouch_speed := 1.2
@export var aim_move_speed := 2.0
## Stick deflection below this is treated as walking (analog walk/run).
@export_range(0.1, 0.9) var walk_stick_threshold := 0.5

@export_group("Acceleration (m/s²)")
@export var ground_accel := 16.0
@export var ground_decel := 20.0
@export var sprint_accel := 10.0
@export_range(0.0, 1.0) var air_control := 0.3

@export_group("Jump & gravity")
@export var jump_height := 1.0
@export var gravity_scale := 1.0
## Extra gravity while falling, gives the jump a heavier feel (pillar "Weight").
@export var fall_gravity_multiplier := 1.5
@export var terminal_velocity := 40.0
@export var coyote_time := 0.12
@export var jump_buffer_time := 0.12

@export_group("Steps (T-GP-01c)")
## Highest step/ledge (m) the player walks onto without jumping. 0 disables step-up.
@export var step_height := 0.35
const STEP_OVERLAP := 0.02
## Ignore "steps" lower than this; the capsule slides over them anyway.
@export var step_min_height := 0.02

@export_group("Turning")
## Exponential turn rate of the Visual towards the move/aim direction.
@export var turn_rate := 12.0
@export var aim_turn_rate := 25.0

@export_group("Body shape (cylinder, see T-GP-01c)")
@export var capsule_radius := 0.35
@export var stand_height := 1.8
@export var crouch_height := 1.2

@export_group("Nodes")
@export var camera_rig_path: NodePath = ^"CameraRig"
@export var visual_path: NodePath = ^"Visual"
@export var collision_shape_path: NodePath = ^"CollisionShape3D"

## Disable to freeze player input (cutscenes, vehicle, tests).
@export var input_enabled := true
## Gameplay can block sprint (M01: carrying the package).
var can_sprint := true

var camera_rig: CameraRig
var visual: CharacterVisual
var _shape: CylinderShape3D
var _collision: CollisionShape3D

var is_aiming := false
var is_crouching := false
var is_sprinting := false
var move_state: MoveState = MoveState.IDLE
## Yaw (radians) the Visual faces; 0 = +Z.
var facing_yaw := 0.0
## Last raw move input (x = right, y = back), length <= 1.
var move_input := Vector2.ZERO
## World-space crosshair hit point / collider (updated every physics frame by the CameraRig).
var aim_point := Vector3.ZERO
var aim_collider: Object = null
var air_time := 0.0
## > 0: keep facing the camera/aim direction (set by the weapon controller after hip-fire).
var combat_face_time := 0.0
## Health component + hitboxes (T-AI-01: enemies shoot the player).
var health: DamageReceiver
var hitboxes: HumanoidHitboxes
var _self_rids: Array[RID] = []

var _coyote := 0.0
var _jump_buffer := 0.0
var _was_on_floor := true
var _last_fall_speed := 0.0
var _jumped_this_frame := false

func _ready() -> void:
	camera_rig = get_node_or_null(camera_rig_path) as CameraRig
	visual = get_node_or_null(visual_path) as CharacterVisual
	_collision = get_node_or_null(collision_shape_path) as CollisionShape3D
	# Flat-bottomed cylinder: rests stably on step edges (a capsule's round bottom
	# slips off stair nosings and loses floor contact); visual stays a capsule.
	assert(_collision != null and _collision.shape is CylinderShape3D, "Player needs a cylinder CollisionShape3D")
	# Each instance resizes its own capsule when crouching.
	_shape = (_collision.shape as CylinderShape3D).duplicate()
	_collision.shape = _shape
	_apply_capsule_height(stand_height)
	# Snap a bit further than the step height so walking DOWN stairs stays grounded
	# (no hop/AIR state), while real drops (> step_height + 0.05) still fall.
	floor_snap_length = step_height + 0.05
	floor_max_angle = deg_to_rad(46.0)
	floor_constant_speed = true
	floor_stop_on_slope = true
	health = get_node_or_null("Health") as DamageReceiver
	hitboxes = get_node_or_null("Visual/Hitboxes") as HumanoidHitboxes
	if health != null:
		health.died.connect(_on_died)
	if camera_rig != null:
		camera_rig.attach(self)
	_was_on_floor = is_on_floor()

func get_gravity_accel() -> float:
	return float(ProjectSettings.get_setting("physics/3d/default_gravity", 9.8)) * gravity_scale

func get_jump_velocity() -> float:
	return sqrt(2.0 * get_gravity_accel() * jump_height)

## Horizontal speed in m/s.
func get_planar_speed() -> float:
	return Vector2(velocity.x, velocity.z).length()

## Unit vector the character faces (model front +Z rotated by facing_yaw).
func get_facing_direction() -> Vector3:
	return Vector3(sin(facing_yaw), 0.0, cos(facing_yaw))

func _physics_process(delta: float) -> void:
	_jumped_this_frame = false
	var wants_aim := input_enabled and Input.is_action_pressed("aim")
	_set_aiming(wants_aim)
	if input_enabled and Input.is_action_just_pressed("crouch"):
		_set_crouching(not is_crouching)

	move_input = Vector2.ZERO
	if input_enabled:
		move_input = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var basis_yaw := camera_rig.get_planar_basis() if camera_rig != null else Basis.IDENTITY
	var wish_dir := basis_yaw * Vector3(move_input.x, 0.0, move_input.y)
	wish_dir.y = 0.0
	var strength := minf(move_input.length(), 1.0)
	if wish_dir.length_squared() > 0.0:
		wish_dir = wish_dir.normalized()

	var on_floor := is_on_floor()
	if on_floor:
		_coyote = coyote_time
		air_time = 0.0
	else:
		_coyote = maxf(_coyote - delta, 0.0)
		air_time += delta

	# --- speed selection -------------------------------------------------
	var wants_sprint := input_enabled and Input.is_action_pressed("sprint")
	is_sprinting = wants_sprint and can_sprint and not is_aiming and not is_crouching \
		and strength > walk_stick_threshold
	var target_speed := run_speed
	if is_crouching:
		target_speed = crouch_speed
	elif is_aiming:
		target_speed = aim_move_speed
	elif is_sprinting:
		target_speed = sprint_speed
	elif (input_enabled and Input.is_action_pressed("walk")) or strength <= walk_stick_threshold:
		target_speed = walk_speed
	# Analog: below the walk threshold scale walk speed with stick deflection.
	var analog := 1.0 if strength > walk_stick_threshold else strength / walk_stick_threshold
	var target := wish_dir * target_speed * analog

	# --- horizontal velocity ---------------------------------------------
	var hv := Vector3(velocity.x, 0.0, velocity.z)
	var rate := ground_decel if target.length() < hv.length() else (sprint_accel if is_sprinting else ground_accel)
	if not on_floor:
		rate *= air_control
	hv = hv.move_toward(target, rate * delta)
	velocity.x = hv.x
	velocity.z = hv.z

	# --- jump / gravity ---------------------------------------------------
	if input_enabled and Input.is_action_just_pressed("jump"):
		_jump_buffer = jump_buffer_time
	else:
		_jump_buffer = maxf(_jump_buffer - delta, 0.0)
	if _jump_buffer > 0.0 and _coyote > 0.0:
		if is_crouching:
			_set_crouching(false)  # jump from crouch = stand up (if there is room)
			_jump_buffer = 0.0
		else:
			velocity.y = get_jump_velocity()
			_jump_buffer = 0.0
			_coyote = 0.0
			_jumped_this_frame = true
			jumped.emit()
	if not on_floor and not _jumped_this_frame:
		var g := get_gravity_accel()
		if velocity.y < 0.0:
			g *= fall_gravity_multiplier
		velocity.y = maxf(velocity.y - g * delta, -terminal_velocity)
	if velocity.y < 0.0:
		_last_fall_speed = -velocity.y

	if on_floor and not _jumped_this_frame and step_height > 0.0:
		_try_step_up(Vector3(velocity.x, 0.0, velocity.z), delta)

	move_and_slide()

	var now_on_floor := is_on_floor()
	if now_on_floor and not _was_on_floor:
		landed.emit(_last_fall_speed)
		_last_fall_speed = 0.0
	_was_on_floor = now_on_floor

	_update_facing(delta, hv)
	_update_move_state(now_on_floor)
	if camera_rig != null:
		camera_rig.update_rig(delta)
		aim_point = camera_rig.aim_point
		aim_collider = camera_rig.aim_collider
	if visual != null:
		visual.update_from_player(self, delta)

## Step-up: if the horizontal move this frame hits a wall-like surface whose top is a
## walkable floor at most `step_height` above the feet, lift the body onto it and let
## move_and_slide() continue forward. Returns true if the body was lifted.
## Rejects: slopes (handled by move_and_slide), ledges/walls taller than step_height
## (the probe ray starts inside them or finds the top too high), non-walkable tops,
## and steps under a ceiling with no head room.
func _try_step_up(hv: Vector3, delta: float) -> bool:
	var speed := hv.length()
	if speed < 0.05:
		return false
	var dir := hv / speed
	var xf := global_transform
	# Probe this frame's motion (+ a small look-ahead). If the riser is reached we lift
	# AND make sure the base ends up >= STEP_OVERLAP over the tread; otherwise floor
	# snap would pull the body straight back down (one-frame pop).
	var motion_len := speed * delta
	var probe := dir * (motion_len + 0.03)
	var col := KinematicCollision3D.new()
	if not test_move(xf, probe, col):
		return false
	if col.get_normal().angle_to(Vector3.UP) <= floor_max_angle:
		return false  # walkable slope, not a step
	var contact := col.get_position() + dir * 0.06
	var from := Vector3(contact.x, xf.origin.y + step_height + 0.05, contact.z)
	var to := Vector3(contact.x, xf.origin.y - 0.05, contact.z)
	var q := PhysicsRayQueryParameters3D.create(from, to, collision_mask, [get_rid()])
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty() or (hit.normal as Vector3).angle_to(Vector3.UP) > floor_max_angle:
		return false
	var h: float = hit.position.y - xf.origin.y
	if h <= step_min_height or h > step_height:
		return false
	var lift := Vector3(0.0, h + 0.02, 0.0)
	if test_move(xf, lift):
		return false  # no head room
	if test_move(xf.translated(lift), probe):
		return false  # still blocked above the step -> wall, not a step
	var to_riser := col.get_travel().length()
	var extra := maxf(0.0, to_riser + STEP_OVERLAP - motion_len)
	global_position += lift + dir * extra
	stepped_up.emit(h)
	return true

func _update_facing(delta: float, hv: Vector3) -> void:
	var target_yaw := facing_yaw
	var rate := turn_rate
	combat_face_time = maxf(combat_face_time - delta, 0.0)
	if (is_aiming or combat_face_time > 0.0) and camera_rig != null:
		# Face where the camera looks (yaw of camera forward = -Z of the rig).
		var fwd := -camera_rig.get_planar_basis().z
		target_yaw = atan2(fwd.x, fwd.z)
		rate = aim_turn_rate
	elif hv.length() > 0.2:
		target_yaw = atan2(hv.x, hv.z)
	facing_yaw = lerp_angle(facing_yaw, target_yaw, 1.0 - exp(-rate * delta))
	if visual != null:
		visual.rotation.y = facing_yaw

func _update_move_state(on_floor: bool) -> void:
	var speed := get_planar_speed()
	var s: MoveState
	if not on_floor:
		s = MoveState.AIR
	elif is_crouching:
		s = MoveState.CROUCH
	elif speed < 0.1:
		s = MoveState.IDLE
	elif is_sprinting and speed > run_speed * 0.9:
		s = MoveState.SPRINT
	elif speed > (walk_speed + run_speed) * 0.5:
		s = MoveState.RUN
	else:
		s = MoveState.WALK
	if s != move_state:
		move_state = s
		move_state_changed.emit(s)

func _set_aiming(value: bool) -> void:
	if value == is_aiming:
		return
	is_aiming = value
	aim_changed.emit(value)

func _set_crouching(value: bool) -> void:
	if value == is_crouching:
		return
	if not value and not can_stand_up():
		return
	is_crouching = value
	_apply_capsule_height(crouch_height if value else stand_height)
	if hitboxes != null:
		hitboxes.position.y = -(stand_height - crouch_height) if value else 0.0
	crouch_changed.emit(value)

## True if a standing capsule fits at the current position (crouch -> stand).
func can_stand_up() -> bool:
	if not is_inside_tree():
		return true
	var probe := CylinderShape3D.new()
	probe.radius = capsule_radius * 0.95
	probe.height = stand_height - 0.1
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = probe
	q.transform = Transform3D(Basis.IDENTITY, global_position + Vector3(0.0, 0.05 + probe.height * 0.5, 0.0))
	q.collision_mask = collision_mask
	q.exclude = [get_rid()]
	return get_world_3d().direct_space_state.intersect_shape(q, 1).is_empty()

func _apply_capsule_height(h: float) -> void:
	_shape.radius = capsule_radius
	_shape.height = h
	_collision.position = Vector3(0.0, h * 0.5, 0.0)

# --- combat hooks (T-AI-01) -------------------------------------------------

## Body + own hitboxes: excluded from the player's own shots and crosshair ray.
func get_self_rids() -> Array[RID]:
	if _self_rids.is_empty():
		_self_rids.append(get_rid())
		if hitboxes != null:
			_self_rids.append_array(hitboxes.get_rids())
	return _self_rids

## Points AI perception tests for line of sight: [head, chest] (lower when crouched).
func get_visibility_points() -> Array:
	var drop := (stand_height - crouch_height) if is_crouching else 0.0
	return [global_position + Vector3(0, 1.65 - drop, 0), global_position + Vector3(0, 1.15 - drop, 0)]

func is_dead() -> bool:
	return health != null and health.is_dead

func _on_died(_info: DamageInfo) -> void:
	input_enabled = false
	died.emit()
