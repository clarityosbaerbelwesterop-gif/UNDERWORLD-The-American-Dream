# UNDERWORLD - data-driven vehicle definition (T-GP-03). One .tres per vehicle under
# res://Data/Vehicles/. [DOC] = from design docs (TASK_BOARD T-GP-03 / T-ART-04 / M01),
# [DEFAULT] = Bot 3 starting value (data-driven, Bot 1 accepted [DEFAULT] values as starting points).
class_name VehicleData
extends Resource

@export var id := "VEH_Unnamed"
@export var display_name := "Car"
## Bot 2's VH_*.glb (required). Vehicle.gd builds wheels, collision, doors and sockets from its nodes.
@export var model_scene: PackedScene

@export_group("Body")
@export var mass := 1450.0
## Centre of mass relative to the body origin (low = stable).
@export var center_of_mass := Vector3(0, 0.45, 0)

@export_group("Engine / speed (m/s, N)")
## Total drive force at full throttle (split over the traction wheels).
@export var engine_force := 6500.0
@export var top_speed := 38.0
## Full force up to this fraction of top speed, then linear fade to 0 at top speed.
@export_range(0.1, 1.0) var power_fade_start := 0.85
@export var reverse_force := 3500.0
@export var reverse_top_speed := 8.0
## Aerodynamic drag coefficient k in F = k * v² (N per (m/s)²).
@export var air_drag := 0.4
## Rolling resistance (N, opposes motion while rolling).
@export var rolling_resistance := 200.0
## Below this forward speed the brake input engages reverse instead of braking.
@export var reverse_switch_speed := 1.0

@export_group("Drivetrain")
## Which axle gets the engine force (late-90s US full-size sedan = rear-wheel drive).
@export_enum("RWD", "FWD", "AWD") var drive := 0

@export_group("Brakes")
## VehicleBody3D brake value at full brake input (all wheels).
@export var brake_force := 30.0
## Brake applied when no throttle/brake input (engine braking + parking).
@export var idle_brake := 1.0
@export var handbrake_force := 25.0

@export_group("Steering (degrees)")
## Max wheel angle at low speed ...
@export var steer_max_deg := 35.0
## ... shrinking linearly to this at steer_min_speed and above (speed-dependent steering).
@export var steer_min_deg := 8.0
@export var steer_full_speed := 5.0
@export var steer_min_speed := 30.0
## Wheel turn rate (deg/s) - steering is rate-limited, not instant.
@export var steer_rate_deg := 140.0

@export_group("Suspension / grip (per wheel)")
@export var wheel_radius := 0.34
@export var suspension_rest_length := 0.2
@export var suspension_travel := 0.2
@export var suspension_stiffness := 40.0
@export var suspension_max_force := 20000.0
@export var damping_compression := 2.0
@export var damping_relaxation := 3.0
@export var friction_slip_front := 3.0
@export var friction_slip_rear := 3.0
## Rear wheel friction while the handbrake is held (lower = more drift).
@export var handbrake_rear_slip := 0.9
@export var roll_influence := 0.1

@export_group("Damage")
@export var max_health := 1000.0
## Impacts below this speed change (m/s) do no damage.
@export var crash_damage_threshold := 3.0
## Vehicle damage per m/s of impact speed change above the threshold.
@export var crash_damage_per_mps := 40.0
## Engine dies (no drive force) at this health fraction or below.
@export_range(0.0, 1.0) var wreck_health_fraction := 0.0

@export_group("Enter / exit")
## Player must be within this distance of a door/exit socket to get in (m).
@export var enter_distance := 2.5
## Can only get out at or below this speed (m/s).
@export var exit_max_speed := 2.0
## Radius/height of the free-space check at the exit socket (player cylinder, TD-011).
@export var exit_check_radius := 0.35
@export var exit_check_height := 1.8

@export_group("Doors (hinge pivots Door_FL/FR/RL/RR)")
## Opening angle of a door around its vertical hinge (deg), and time to swing it open/closed (s).
@export var door_open_deg := 65.0
@export var door_swing_time := 0.25
## Enter/exit sequence length (s) - door stays open this long. Matches nothing yet;
## A_Humanoid_Car_Enter_L / Car_Exit_L clips will drive it in the Jason swap.
@export var enter_time := 0.6
@export var exit_time := 0.5

@export_group("Chase camera")
@export var cam_distance := 6.0
@export var cam_height := 2.2
@export var cam_look_height := 1.0
## Exponential follow rate (1/s), framerate independent.
@export var cam_follow_rate := 6.0
## Look-ahead along the velocity (m per m/s, clamped).
@export var cam_look_ahead := 0.08
@export var cam_fov := 70.0
@export var cam_fov_at_top_speed := 82.0

@export_group("Engine audio (placeholder)")
## Gear change speeds (m/s) for the RPM sawtooth.
@export var gear_speeds: PackedFloat32Array = PackedFloat32Array([8.0, 15.0, 23.0, 31.0, 40.0])
@export var pitch_idle := 0.7
@export var pitch_max := 1.9

func get_max_steer_deg(speed: float) -> float:
	var t := clampf((absf(speed) - steer_full_speed) / maxf(steer_min_speed - steer_full_speed, 0.01), 0.0, 1.0)
	return lerpf(steer_max_deg, steer_min_deg, t)

## Drive force multiplier (0..1) at forward speed v (fades out near top speed).
func power_factor(v: float) -> float:
	var start := top_speed * power_fade_start
	if v <= start:
		return 1.0
	return clampf((top_speed - v) / maxf(top_speed - start, 0.01), 0.0, 1.0)

## Engine RPM fraction 0..1 (sawtooth over gear_speeds), for the audio pitch.
func rpm_fraction(speed: float) -> float:
	var s := absf(speed)
	var lo := 0.0
	for g in gear_speeds:
		if s <= g:
			return clampf((s - lo) / maxf(g - lo, 0.01), 0.0, 1.0) * 0.75 + 0.25 * (1.0 if lo > 0.0 else s / maxf(g, 0.01))
		lo = g
	return 1.0
