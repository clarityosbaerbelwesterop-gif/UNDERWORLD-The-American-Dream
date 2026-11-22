# UNDERWORLD - third-person orbit camera with over-shoulder aim mode (T-GP-01).
#
#   CameraRig (Node3D, top_level, yaw)  follows the player's head pivot
#   └─ Pitch (Node3D, pitch)
#      └─ SpringArm3D (collision, shoulder offset in local X)
#         └─ Camera3D
#
# Mouse look (captured mouse) and right-stick look ("look_*" actions).
# The player calls update_rig() once per physics frame after move_and_slide(),
# so follow + aim raycast are deterministic and in sync with the body.
class_name CameraRig
extends Node3D

signal shoulder_swapped(side: float)

@export_group("Look")
@export var mouse_sensitivity := 0.0025  ## rad per pixel
@export var stick_look_speed := 3.0      ## rad/s at full deflection
@export var aim_sensitivity_scale := 0.6
@export var invert_y := false
@export_range(-89.0, 0.0) var min_pitch_deg := -70.0
@export_range(0.0, 89.0) var max_pitch_deg := 50.0
## Mouse motion is only applied while the mouse is captured (set false for tests/tools).
@export var require_mouse_capture := true

@export_group("Explore framing")
@export var pivot_height := 1.6
@export var crouch_pivot_height := 1.15
@export var arm_length := 3.2
@export var shoulder_offset := 0.45
@export var fov := 70.0

@export_group("Aim framing (over the shoulder)")
@export var aim_arm_length := 1.3
@export var aim_shoulder_offset := 0.6
@export var aim_pivot_raise := 0.05
@export var aim_fov := 55.0
## Exponential blend rate explore <-> aim (1/s).
@export var aim_blend_rate := 12.0
@export var follow_rate := 20.0

@export_group("Aim ray")
@export var aim_ray_length := 250.0
## World | Characters | Vehicles | Hitboxes (layer names in project.godot).
@export_flags_3d_physics var aim_ray_mask := 1 | 4 | 8 | 16

@onready var pitch_node: Node3D = $Pitch
@onready var spring_arm: SpringArm3D = $Pitch/SpringArm3D
@onready var camera: Camera3D = $Pitch/SpringArm3D/Camera3D

var player: PlayerController
var yaw := 0.0
var pitch := deg_to_rad(-12.0)
## 0 = explore framing, 1 = full aim framing.
var aim_blend := 0.0
## +1 = camera over the right shoulder, -1 = left.
var shoulder_side := 1.0
var aim_point := Vector3.ZERO
var aim_normal := Vector3.UP
var aim_collider: Object = null
## Weapon recoil offset in radians (x = yaw, y = pitch up), added on top of yaw/pitch and
## recovering to zero at recoil_recovery_rate (1/s, set from WeaponData by the weapon controller).
var recoil_offset := Vector2.ZERO
var recoil_recovery_rate := 8.0
var _pending_look := Vector2.ZERO
var _pivot := Vector3.ZERO

func _ready() -> void:
	top_level = true
	_apply_framing()

func attach(p: PlayerController) -> void:
	player = p
	spring_arm.add_excluded_object(p.get_rid())
	_pivot = p.global_position + Vector3(0.0, pivot_height, 0.0)
	global_position = _pivot
	_apply_rotation()

## Camera yaw only (no pitch): use to map move input to world space.
func get_planar_basis() -> Basis:
	return Basis(Vector3.UP, yaw)

## Add look input in radians (x = yaw right, y = pitch up). Used by mouse, stick and tests.
func apply_look(delta_rad: Vector2) -> void:
	yaw -= delta_rad.x
	pitch = clampf(pitch + delta_rad.y, deg_to_rad(min_pitch_deg), deg_to_rad(max_pitch_deg))
	_apply_rotation()

func set_yaw(rad: float) -> void:
	yaw = rad
	_apply_rotation()

## Instant camera kick in degrees (x = yaw right, y = pitch up) - T-GP-02 recoil.
func add_recoil(kick_deg: Vector2) -> void:
	recoil_offset += Vector2(-deg_to_rad(kick_deg.x), deg_to_rad(kick_deg.y))
	_apply_rotation()

## Effective pitch (look + recoil), radians.
func get_effective_pitch() -> float:
	return clampf(pitch + recoil_offset.y, deg_to_rad(min_pitch_deg), deg_to_rad(max_pitch_deg))

func swap_shoulder() -> void:
	shoulder_side = -shoulder_side
	shoulder_swapped.emit(shoulder_side)

func is_aiming() -> bool:
	return player != null and player.is_aiming

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		if require_mouse_capture and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
			return
		var m := (event as InputEventMouseMotion).relative * mouse_sensitivity
		_pending_look += Vector2(m.x, -m.y if not invert_y else m.y)
	elif event is InputEventMouseButton and event.pressed and require_mouse_capture \
			and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED and DisplayServer.get_name() != "headless":
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	elif event.is_action_pressed("pause") and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func update_rig(delta: float) -> void:
	if player == null:
		return
	# Look input: mouse (accumulated) + stick (rate based).
	var sens := lerpf(1.0, aim_sensitivity_scale, aim_blend)
	var stick := Vector2.ZERO
	if player.input_enabled:
		stick = Input.get_vector("look_left", "look_right", "look_down", "look_up")
		if invert_y:
			stick.y = -stick.y
		if Input.is_action_just_pressed("shoulder_swap"):
			swap_shoulder()
	var look := (_pending_look + stick * stick_look_speed * delta) * sens
	_pending_look = Vector2.ZERO
	if look != Vector2.ZERO:
		apply_look(look)
	if recoil_offset != Vector2.ZERO:
		recoil_offset = recoil_offset.lerp(Vector2.ZERO, 1.0 - exp(-recoil_recovery_rate * delta))
		if recoil_offset.length() < 0.00005:
			recoil_offset = Vector2.ZERO
		_apply_rotation()

	# Blend framing.
	var target_aim := 1.0 if player.is_aiming else 0.0
	aim_blend = lerpf(aim_blend, target_aim, 1.0 - exp(-aim_blend_rate * delta))
	if absf(aim_blend - target_aim) < 0.001:
		aim_blend = target_aim

	# Follow the head pivot (smoothed vertically so steps/landings don't jolt).
	var h := crouch_pivot_height if player.is_crouching else pivot_height
	h += aim_pivot_raise * aim_blend
	var target_pivot := player.global_position + Vector3(0.0, h, 0.0)
	var t := 1.0 - exp(-follow_rate * delta)
	_pivot = Vector3(target_pivot.x, lerpf(_pivot.y, target_pivot.y, t), target_pivot.z)
	global_position = _pivot
	_apply_framing()
	_update_aim_ray()

func _apply_rotation() -> void:
	rotation = Vector3(0.0, yaw + recoil_offset.x, 0.0)
	if pitch_node != null:
		pitch_node.rotation = Vector3(get_effective_pitch(), 0.0, 0.0)

func _apply_framing() -> void:
	spring_arm.spring_length = lerpf(arm_length, aim_arm_length, aim_blend)
	spring_arm.position = Vector3(lerpf(shoulder_offset, aim_shoulder_offset, aim_blend) * shoulder_side, 0.0, 0.0)
	camera.fov = lerpf(fov, aim_fov, aim_blend)

## Crosshair ray [origin, direction]: from the camera along its -Z (screen centre),
## computed from the arm so it is valid before SpringArm3D's own update.
func get_aim_ray() -> Array:
	var arm_xf := spring_arm.global_transform
	var length := spring_arm.get_hit_length() if spring_arm.get_hit_length() > 0.0 else spring_arm.spring_length
	var origin := arm_xf.origin + arm_xf.basis.z.normalized() * length
	return [origin, -arm_xf.basis.z.normalized()]

## Crosshair = screen centre = camera -Z. Ray starts at the camera, excludes the player.
func _update_aim_ray() -> void:
	var r := get_aim_ray()
	var origin: Vector3 = r[0]
	var dir: Vector3 = r[1]
	var to := origin + dir * aim_ray_length
	var excl: Array[RID] = player.get_self_rids() if player.has_method("get_self_rids") else [player.get_rid()]
	var q := PhysicsRayQueryParameters3D.create(origin, to, aim_ray_mask, excl)
	q.collide_with_areas = true
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty():
		aim_point = to
		aim_normal = -dir
		aim_collider = null
	else:
		aim_point = hit.position
		aim_normal = hit.normal
		aim_collider = hit.collider
