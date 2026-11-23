# UNDERWORLD - drivable car on Godot's VehicleBody3D (T-GP-03, TD-014).
#
# The scene is only "VehicleBody3D + this script + a VehicleData .tres". At _ready the
# asset (VehicleData.model_scene = Bot 2's VH_*.glb) is instanced and wired up:
#   Wheel_FL/FR/RL/RR  -> reparented under generated VehicleWheel3D nodes (spin + steer +
#                         suspension move the asset mesh); rest position = asset wheel centre
#   UCX_*              -> its convex shape becomes this body's CollisionShape3D, the
#                         imported StaticBody3D is removed
#   Door_FL/FR/RL/RR   -> swing around their hinge pivot (local Y) via open_door()/close_door()
#   SOCKET_*           -> seat / exit / light sockets (get_socket())
# Driving input (only while a player drives): vehicle_accelerate / vehicle_brake /
# vehicle_handbrake + move_left/right; enter/exit = enter_vehicle (F / gamepad Y).
# Tests and AI drive with set_controls() + control_override.
class_name Vehicle
extends VehicleBody3D

signal entered(driver: Node3D)
signal exited(driver: Node3D)
signal exit_blocked
signal door_changed(door: StringName, open: bool)
signal crashed(impact_speed: float, damage: float)
signal wrecked

enum State { IDLE, ENTERING, DRIVING, EXITING }

const WHEEL_NAMES: Array[StringName] = [&"Wheel_FL", &"Wheel_FR", &"Wheel_RL", &"Wheel_RR"]
const DOOR_NAMES: Array[StringName] = [&"Door_FL", &"Door_FR", &"Door_RL", &"Door_RR"]
## Exit socket -> door used on that side (driver = left = +X, the car faces +Z).
const EXIT_DOORS := {&"SOCKET_Exit_Left": &"Door_FL", &"SOCKET_Exit_Right": &"Door_FR"}
const SEAT_SOCKET := &"SOCKET_Seat_Driver"
const PASSENGER_SOCKET := &"SOCKET_Seat_Passenger"
## World | Player | Characters | Vehicles
const BODY_MASK := 1 | 2 | 4 | 8

@export var data: VehicleData
## Ignore player input and use set_controls() values (tests, AI, cutscenes).
@export var control_override := false

var state: State = State.IDLE
var driver: Node3D = null
## Marco's seat in M01 (T-MIS-01b). A passenger does not drive and does not block enter/exit.
var passenger: Node3D = null
var model: Node3D
## Wheel name -> generated VehicleWheel3D (asset mesh is its child).
var wheels: Dictionary = {}
## Wheel name -> asset wheel centre in body space (design pose, from the .glb).
var wheel_design_pos: Dictionary = {}
## Wheel name -> asset wheel node (Wheel_FL ...), posed from the physics wheel.
var wheel_meshes: Dictionary = {}
var asset_wheel_radius := 0.0
## Name -> asset node (sockets / doors / panels).
var sockets: Dictionary = {}
var doors: Dictionary = {}
var collision_shape: CollisionShape3D
var chase_camera: Camera3D
var health := 0.0
## Controls 0..1 (steer -1 right .. +1 left).
var throttle := 0.0
var brake_input := 0.0
var steer_input := 0.0
var handbrake_input := 0.0
## Current front wheel angle (deg, + = left).
var steer_angle_deg := 0.0
## Signed speed along the car's forward (+Z) axis, m/s.
var forward_speed := 0.0
var engine_pitch := 1.0
var assembly_errors: PackedStringArray = []

var _ext := Vector4.ZERO   # throttle, brake, steer, handbrake from set_controls()
var _state_time := 0.0

var _exit_socket: StringName = &""
var _door_open: Dictionary = {}     # name -> 0..1 current
var _door_target: Dictionary = {}   # name -> 0..1
var _door_closed: Dictionary = {}   # name -> closed Transform3D
var _door_sign: Dictionary = {}     # name -> +1/-1 (outward swing)
var _prev_velocity := Vector3.ZERO
var _cam_pos := Vector3.ZERO
var _engine_audio: AudioStreamPlayer3D

func _ready() -> void:
	add_to_group("vehicles")
	assert(data != null and data.model_scene != null, "Vehicle needs VehicleData with model_scene")
	mass = data.mass
	center_of_mass_mode = RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
	center_of_mass = data.center_of_mass
	collision_layer = 1 << 3  # layer 4 "Vehicles"
	collision_mask = BODY_MASK
	contact_monitor = true
	max_contacts_reported = 4
	can_sleep = true
	health = data.max_health
	_assemble()
	chase_camera = get_node_or_null("ChaseCamera") as Camera3D
	if chase_camera == null:
		chase_camera = Camera3D.new()
		chase_camera.name = "ChaseCamera"
		add_child(chase_camera)
	chase_camera.top_level = true
	chase_camera.current = false
	chase_camera.fov = data.cam_fov
	_engine_audio = get_node_or_null("EngineAudio") as AudioStreamPlayer3D
	_prev_velocity = linear_velocity
	_snap_camera()

# --- asset wiring -------------------------------------------------------------

func _assemble() -> void:
	model = data.model_scene.instantiate() as Node3D
	model.name = "Model"
	add_child(model)
	var to_body := global_transform.affine_inverse()
	# Collision from the authored convex hull(s).
	var ucx: Array[Node] = []
	_find_prefix(model, "UCX_", ucx)
	for body in ucx:
		for c in body.get_children():
			if c is CollisionShape3D and (c as CollisionShape3D).shape != null:
				var cs := CollisionShape3D.new()
				cs.name = "Collision_" + String(body.name)
				cs.shape = (c as CollisionShape3D).shape
				cs.transform = to_body * (c as CollisionShape3D).global_transform
				add_child(cs)
				if collision_shape == null:
					collision_shape = cs
		body.get_parent().remove_child(body)
		body.queue_free()
	if collision_shape == null:
		assembly_errors.append("no UCX_* collision in model")
	# Asset-declared wheel radius (glTF extras on the vehicle root).
	var extras_node := _find_extras_root(model)
	if extras_node != null:
		asset_wheel_radius = float(extras_node.get_meta("extras").get("uw_wheel_radius_m", 0.0))
	# Wheels.
	var sag := get_design_sag()
	for wn in WHEEL_NAMES:
		var mesh := model.find_child(String(wn), true, false) as Node3D
		if mesh == null:
			assembly_errors.append("wheel node %s missing" % wn)
			continue
		var centre := (to_body * mesh.global_transform).origin
		wheel_design_pos[wn] = centre
		if asset_wheel_radius <= 0.0 and mesh is MeshInstance3D:
			asset_wheel_radius = (mesh as MeshInstance3D).get_aabb().size.y * 0.5
		var w := VehicleWheel3D.new()
		w.name = "VW_" + String(wn)
		# Suspension attach point above the rest centre so that the static sag puts the
		# wheel centre back on the asset position when the car stands still.
		w.position = centre + Vector3.UP * (data.suspension_rest_length - sag)
		var front := centre.z > 0.0
		w.use_as_steering = front
		w.use_as_traction = (data.drive == 2) or (data.drive == 0 and not front) or (data.drive == 1 and front)
		w.wheel_radius = data.wheel_radius
		w.wheel_rest_length = data.suspension_rest_length
		w.suspension_travel = data.suspension_travel
		w.suspension_stiffness = data.suspension_stiffness
		w.suspension_max_force = data.suspension_max_force
		w.damping_compression = data.damping_compression
		w.damping_relaxation = data.damping_relaxation
		w.wheel_friction_slip = data.friction_slip_front if front else data.friction_slip_rear
		w.wheel_roll_influence = data.roll_influence
		add_child(w)
		# The asset mesh stays in the asset hierarchy (LOD children follow it); its pose is
		# copied from the physics wheel every frame in _update_wheel_visuals().
		wheels[wn] = w
		wheel_meshes[wn] = mesh
	if asset_wheel_radius > 0.0 and absf(asset_wheel_radius - data.wheel_radius) > 0.01:
		assembly_errors.append("data.wheel_radius %.3f != asset %.3f" % [data.wheel_radius, asset_wheel_radius])
	# Doors (hinge pivot = node origin, vertical hinge = local Y).
	for dn in DOOR_NAMES:
		var d := model.find_child(String(dn), true, false) as Node3D
		if d == null:
			assembly_errors.append("door node %s missing" % dn)
			continue
		doors[dn] = d
		_door_closed[dn] = d.transform
		_door_open[dn] = 0.0
		_door_target[dn] = 0.0
		# Door leaf extends backwards (-Z) from the hinge: swing outward = rotate the
		# rear edge away from the centre line (left side +X -> negative yaw).
		_door_sign[dn] = -1.0 if (to_body * d.global_transform).origin.x > 0.0 else 1.0
	var found: Array[Node] = []
	_find_prefix(model, "SOCKET_", found)
	for s in found:
		sockets[StringName(s.name)] = s
	for need in [SEAT_SOCKET, PASSENGER_SOCKET, &"SOCKET_Exit_Left", &"SOCKET_Exit_Right"]:
		if not sockets.has(need):
			assembly_errors.append("socket %s missing" % need)
	for e in assembly_errors:
		push_warning("Vehicle %s: %s" % [data.id, e])

## Godot 4.7.2 (GodotPhysics) VehicleBody3D static suspension compression, measured:
## 4.0 / suspension_stiffness metres, independent of mass (0.100 m at k = 40, 0.050 m at 80).
## (Theory g / (4 k) = 0.061 m does not match the engine.) test_vehicle.gd checks that the
## parked body origin sits on the ground (+-1 cm) - recalibrate here if that test fails.
const STATIC_SAG_K := 4.0

## Static suspension compression (m) the wheel attach points are raised by, so a parked car
## stands at its design height (asset origin on the ground, tyres touching it).
func get_design_sag() -> float:
	return STATIC_SAG_K / maxf(data.suspension_stiffness, 0.01)

static func _find_prefix(n: Node, prefix: String, out: Array[Node]) -> void:
	for c in n.get_children():
		if String(c.name).begins_with(prefix):
			out.append(c)
		_find_prefix(c, prefix, out)

static func _find_extras_root(n: Node) -> Node:
	if n.has_meta("extras") and n.get_meta("extras") is Dictionary and n.get_meta("extras").has("uw_wheel_radius_m"):
		return n
	for c in n.get_children():
		var r := _find_extras_root(c)
		if r != null:
			return r
	return null

func get_socket(socket_name: StringName) -> Node3D:
	return sockets.get(socket_name) as Node3D

# --- controls -----------------------------------------------------------------

## Drive without the input map (tests / AI). Enables control_override.
func set_controls(p_throttle: float, p_brake: float, p_steer: float, p_handbrake := 0.0) -> void:
	control_override = true
	_ext = Vector4(clampf(p_throttle, 0, 1), clampf(p_brake, 0, 1), clampf(p_steer, -1, 1), clampf(p_handbrake, 0, 1))

func is_wrecked() -> bool:
	return health <= data.max_health * data.wreck_health_fraction

func _read_controls() -> void:
	if control_override:
		throttle = _ext.x; brake_input = _ext.y; steer_input = _ext.z; handbrake_input = _ext.w
	elif state == State.DRIVING:
		throttle = Input.get_action_strength("vehicle_accelerate")
		brake_input = Input.get_action_strength("vehicle_brake")
		steer_input = Input.get_axis("move_right", "move_left")
		handbrake_input = Input.get_action_strength("vehicle_handbrake")
	else:
		throttle = 0.0; brake_input = 0.0; steer_input = 0.0
		handbrake_input = 1.0 if driver == null else 0.0  # parked = handbrake on

func _physics_process(delta: float) -> void:
	_state_time += delta
	forward_speed = linear_velocity.dot(global_basis.z)
	_read_controls()
	_update_state()
	_apply_drive(delta)
	_check_crash()
	_update_doors(delta)
	_update_wheel_visuals()
	if driver != null:
		_attach_driver()
	if passenger != null:
		_attach_passenger()
	if state == State.DRIVING or state == State.ENTERING:
		_update_camera(delta)
	_update_audio()

func _apply_drive(delta: float) -> void:
	var engine := 0.0
	var brake_v := 0.0
	var dead := is_wrecked()
	if throttle > 0.0 and not dead:
		engine = data.engine_force * throttle * data.power_factor(forward_speed)
	if brake_input > 0.0:
		if forward_speed > data.reverse_switch_speed or throttle > 0.0:
			brake_v = data.brake_force * brake_input
		elif not dead and forward_speed > -data.reverse_top_speed:
			engine = -data.reverse_force * brake_input
	if engine == 0.0 and brake_v == 0.0:
		brake_v = data.idle_brake
	# Rolling resistance + aero drag on the planar velocity.
	var v := linear_velocity
	v.y = 0.0
	var spd := v.length()
	if spd > 0.05:
		apply_central_force(-v / spd * (data.rolling_resistance + data.air_drag * spd * spd))
	# Steering: speed-dependent limit, rate-limited.
	var target := steer_input * data.get_max_steer_deg(forward_speed)
	steer_angle_deg = move_toward(steer_angle_deg, target, data.steer_rate_deg * delta)
	steering = deg_to_rad(steer_angle_deg)
	var n_traction := 0
	for wn in wheels:
		if (wheels[wn] as VehicleWheel3D).use_as_traction:
			n_traction += 1
	for wn in wheels:
		var w := wheels[wn] as VehicleWheel3D
		var rear: bool = not w.use_as_steering
		w.engine_force = engine / maxf(n_traction, 1) if w.use_as_traction else 0.0
		var b := brake_v
		if rear and handbrake_input > 0.0:
			b += data.handbrake_force * handbrake_input
			w.engine_force = 0.0  # Godot ignores brake on a wheel with engine force
			w.wheel_friction_slip = lerpf(data.friction_slip_rear, data.handbrake_rear_slip, handbrake_input)
		elif rear:
			w.wheel_friction_slip = data.friction_slip_rear
		w.brake = b

## Asset wheel pose = physics wheel spin/steer basis, centre one radius above the ground
## contact along the suspension axis (VehicleWheel3D's own node position is drawn ~1.5/k m
## too low by Godot 4.7.2, which would sink the tyres into the road).
func _update_wheel_visuals() -> void:
	var up := global_basis.y.normalized()
	for wn in wheels:
		var w := wheels[wn] as VehicleWheel3D
		var centre := w.global_position
		if w.is_in_contact():
			centre = w.get_contact_point() + up * w.wheel_radius
		(wheel_meshes[wn] as Node3D).global_transform = Transform3D(w.global_basis, centre)

## How long the enter/exit sequence takes (T-GP-04). The CLIP drives it: SK_Jason's
## A_Jason_Car_Enter_L / A_Jason_Car_Exit_L lengths are the real timings, and VehicleData only
## supplies a fallback for a driver without a character model. Both are pure lookups (a clip
## length does not change while the car is in use), so there is no cached value to go stale.
func enter_duration() -> float:
	return _driver_clip_length("car_enter", data.enter_time)


func exit_duration() -> float:
	return _driver_clip_length("car_exit", data.exit_time)


func _driver_clip_length(slot: String, fallback: float) -> float:
	var vis := _driver_visual()
	if vis != null:
		var l := vis.clip_length(slot)
		if l > 0.0:
			return l
	return fallback


func _driver_visual() -> CharacterVisual:
	if driver == null:
		return null
	return driver.get("visual") as CharacterVisual


## Plays the driver's enter/exit clip (no-op for drivers without a character model).
func _play_driver_clip(slot: String) -> void:
	var vis := _driver_visual()
	if vis != null:
		vis.play_one_shot(slot)


## Damage entry point for gunfire (T-AI-03). Applies TD-015: the car always takes the hit, the
## driver only takes `driver_window_fraction` of a hit that comes through his window.
## Returns the DamageInfo that was applied to the CAR so callers can report a hit.
func apply_hit_damage(amount: float, hit_position: Vector3, source: Node = null) -> DamageInfo:
	var split := VehicleTargeting.split_damage(self, hit_position, amount)
	var info := DamageInfo.new()
	info.amount = float(split["car"])
	info.base_damage = amount
	info.position = hit_position
	info.source = source
	info.weapon_id = &"vehicle_hit"
	if info.amount > 0.0:
		var was := is_wrecked()
		health = maxf(health - info.amount, 0.0)
		crashed.emit(0.0, info.amount)
		if not was and is_wrecked():
			wrecked.emit()
	var drv: float = split["driver"]
	if drv > 0.0 and driver != null and driver.has_method("get") and driver.get("health") is DamageReceiver:
		var dinfo := DamageInfo.new()
		dinfo.amount = drv
		dinfo.base_damage = amount
		dinfo.position = hit_position
		dinfo.source = source
		dinfo.weapon_id = &"driver_window"
		(driver.get("health") as DamageReceiver).apply_damage(dinfo)
	return info

## World-space centre of the drawn wheel (tests).
func get_wheel_visual_centre(wn: StringName) -> Vector3:
	return (wheel_meshes[wn] as Node3D).global_position

func _check_crash() -> void:
	var dv := (linear_velocity - _prev_velocity).length()
	_prev_velocity = linear_velocity
	if dv > data.crash_damage_threshold:
		var dmg := (dv - data.crash_damage_threshold) * data.crash_damage_per_mps
		var was := is_wrecked()
		health = maxf(health - dmg, 0.0)
		crashed.emit(dv, dmg)
		if not was and is_wrecked():
			wrecked.emit()

func _update_audio() -> void:
	engine_pitch = lerpf(data.pitch_idle, data.pitch_max, data.rpm_fraction(forward_speed))
	if _engine_audio != null:
		_engine_audio.pitch_scale = engine_pitch

# --- doors --------------------------------------------------------------------

func open_door(door: StringName) -> void:
	if doors.has(door) and _door_target[door] != 1.0:
		_door_target[door] = 1.0
		door_changed.emit(door, true)

func close_door(door: StringName) -> void:
	if doors.has(door) and _door_target[door] != 0.0:
		_door_target[door] = 0.0
		door_changed.emit(door, false)

## 0 = closed .. 1 = fully open.
func get_door_open(door: StringName) -> float:
	return float(_door_open.get(door, 0.0))

func _update_doors(delta: float) -> void:
	var rate := 1.0 / maxf(data.door_swing_time, 0.01)
	for dn in doors:
		var cur: float = _door_open[dn]
		var tgt: float = _door_target[dn]
		if cur == tgt:
			continue
		cur = move_toward(cur, tgt, rate * delta)
		_door_open[dn] = cur
		var closed: Transform3D = _door_closed[dn]
		var yaw: float = _door_sign[dn] * deg_to_rad(data.door_open_deg) * cur
		(doors[dn] as Node3D).transform = Transform3D(closed.basis * Basis(Vector3.UP, yaw), closed.origin)

# --- enter / exit -------------------------------------------------------------

## Distance from p to the nearest exit socket, or INF if this car can't be entered now.
func get_enter_distance(p: Node3D) -> float:
	if driver != null or state != State.IDLE:
		return INF
	var best := INF
	for sn in EXIT_DOORS:
		var s := get_socket(sn)
		if s != null:
			best = minf(best, s.global_position.distance_to(p.global_position))
	return best if best <= data.enter_distance else INF

## Called by PlayerController (enter_vehicle pressed near the car).
func enter(p: Node3D) -> bool:
	if get_enter_distance(p) == INF:
		return false
	var side := _nearest_exit_socket(p.global_position)
	driver = p
	if p.has_method("set_in_vehicle"):
		p.set_in_vehicle(self)
	_play_driver_clip("car_enter")
	_exit_socket = side
	open_door(EXIT_DOORS[side])
	_set_state(State.ENTERING)
	sleeping = false
	_snap_camera()
	chase_camera.current = true
	entered.emit(p)
	return true

## Seats an ally on the passenger side (Marco in M01). Unlike enter() this does not change the
## vehicle state, takes no input and never opens a door sequence: the passenger is simply
## parented to the seat socket. False if the seat is taken or the node is not a Node3D.
func enter_passenger(p: Node3D) -> bool:
	if p == null or passenger != null or p == driver:
		return false
	var seat := get_socket(PASSENGER_SOCKET)
	if seat == null:
		push_error("%s: no %s socket" % [name, PASSENGER_SOCKET])
		return false
	passenger = p
	_attach_passenger()
	return true

## Frees the passenger seat. The caller decides where the body goes (see AllyCompanion.unboard).
func leave_passenger() -> Node3D:
	var p := passenger
	passenger = null
	return p

func _attach_passenger() -> void:
	var seat := get_socket(PASSENGER_SOCKET)
	if seat != null and passenger != null and is_instance_valid(passenger):
		passenger.global_transform = seat.global_transform

## Starts the exit sequence; false if too fast or both exits are blocked.
func request_exit() -> bool:
	if state != State.DRIVING or driver == null:
		return false
	if absf(forward_speed) > data.exit_max_speed:
		return false
	var side := &""
	for sn in [&"SOCKET_Exit_Left", &"SOCKET_Exit_Right"]:
		if is_exit_free(sn):
			side = sn
			break
	if side == &"":
		exit_blocked.emit()
		return false
	_exit_socket = side
	open_door(EXIT_DOORS[side])
	_set_state(State.EXITING)
	return true

## True if a standing player cylinder fits at the exit socket (own car included).
func is_exit_free(socket_name: StringName) -> bool:
	var s := get_socket(socket_name)
	if s == null:
		return false
	var probe := CylinderShape3D.new()
	probe.radius = data.exit_check_radius
	probe.height = data.exit_check_height - 0.1
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = probe
	q.transform = Transform3D(Basis.IDENTITY, s.global_position + Vector3.UP * (0.05 + probe.height * 0.5))
	q.collision_mask = 1 | 4 | 8  # World | Characters | Vehicles
	if driver is CollisionObject3D:
		q.exclude = [(driver as CollisionObject3D).get_rid()]
	return get_world_3d().direct_space_state.intersect_shape(q, 1).is_empty()

func _nearest_exit_socket(pos: Vector3) -> StringName:
	var best := &"SOCKET_Exit_Left"
	var bd := INF
	for sn in EXIT_DOORS:
		var s := get_socket(sn)
		if s != null and s.global_position.distance_to(pos) < bd:
			bd = s.global_position.distance_to(pos)
			best = sn
	return best

func _set_state(s: State) -> void:
	state = s
	_state_time = 0.0
	if s == State.EXITING:
		_play_driver_clip("car_exit")

func _update_state() -> void:
	match state:
		State.ENTERING:
			if _state_time >= enter_duration():
				close_door(EXIT_DOORS[_exit_socket])
				_set_state(State.DRIVING)
		State.DRIVING:
			if not control_override and _state_time > 0.2 and Input.is_action_just_pressed("enter_vehicle"):
				request_exit()
		State.EXITING:
			if _state_time >= exit_duration():
				_finish_exit()

func _finish_exit() -> void:
	var p := driver
	var s := get_socket(_exit_socket)
	close_door(EXIT_DOORS[_exit_socket])
	driver = null
	_set_state(State.IDLE)
	chase_camera.current = false
	var yaw := global_rotation.y
	var at := Transform3D(Basis(Vector3.UP, yaw), s.global_position)
	if p.has_method("leave_vehicle"):
		p.leave_vehicle(self, at)
	else:
		p.global_transform = at
	exited.emit(p)

func _attach_driver() -> void:
	var seat := get_socket(SEAT_SOCKET)
	if seat != null:
		driver.global_position = seat.global_position

# --- chase camera ------------------------------------------------------------

func _cam_target() -> Vector3:
	var fwd := global_basis.z
	fwd.y = 0.0
	fwd = fwd.normalized() if fwd.length() > 0.01 else Vector3.FORWARD
	return global_position - fwd * data.cam_distance + Vector3.UP * data.cam_height

func _snap_camera() -> void:
	if chase_camera == null:
		return
	_cam_pos = _cam_target()
	_place_camera()

func _update_camera(delta: float) -> void:
	_cam_pos = _cam_pos.lerp(_cam_target(), 1.0 - exp(-data.cam_follow_rate * delta))
	var t := clampf(absf(forward_speed) / maxf(data.top_speed, 0.1), 0.0, 1.0)
	chase_camera.fov = lerpf(data.cam_fov, data.cam_fov_at_top_speed, t)
	_place_camera()

func _place_camera() -> void:
	var v := linear_velocity
	v.y = 0.0
	var ahead := v * data.cam_look_ahead
	if ahead.length() > 4.0:
		ahead = ahead.normalized() * 4.0
	var look := global_position + Vector3.UP * data.cam_look_height + ahead
	chase_camera.global_position = _cam_pos
	if _cam_pos.distance_to(look) > 0.1:
		chase_camera.look_at(look, Vector3.UP)
