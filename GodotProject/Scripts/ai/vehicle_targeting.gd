# UNDERWORLD - how enemy AI treats a player who is inside a vehicle (T-AI-03, TD-015).
#
# The bug this replaces: NPCController called `target_points(player)` unconditionally. While
# Jason sat in the sedan, his visibility points were still his capsule's head/chest - i.e. two
# points *inside the car*, at seat height - so gunmen shot "through the roof" at a body they
# could not see, and the damage went to the player's DamageReceiver instead of the car.
#
# Rules (TD-015, PROPOSED for Bot 1):
#   R1  A seated target is REPLACED by its vehicle. Perception, cover choice and aiming all
#       operate on the car's body/glass points, never on the player capsule.
#   R2  A hit on the car goes to `Vehicle.health` (crash damage is a separate, existing path).
#   R3  The driver only takes damage through a defined channel: a hit that arrives **through the
#       driver-side window** transfers `driver_window_fraction` of the damage to him, and only
#       while the car's health is above zero. Every other hit on the car is car-only. The
#       fraction is data (VehicleData.driver_window_fraction), not a magic number in code.
#   R4  Entering/leaving changes the target class immediately: the AI re-evaluates every frame
#       via `resolve()`, so a player who gets out is targeted as a person again on the next
#       physics frame, and one who gets in is targeted as a car.
#
# Everything here is a pure function of (target, vehicle) so the rules are unit-testable
# without a scene (Test/test_ai.gd "in-car targeting" block).
class_name VehicleTargeting
extends RefCounted

## DamageInfo.damage_channel values, so a HUD/hit report can tell the two apart.
const CHANNEL_CAR := &"vehicle"
const CHANNEL_DRIVER := &"driver"
const CHANNEL_PERSON := &"person"

## The vehicle a target is riding in, or null. Uses PlayerController.vehicle when present, so a
## player who is *entering* (driver set, state ENTERING) already counts as seated.
static func vehicle_of(target: Node3D) -> Vehicle:
	if target == null:
		return null
	var v = target.get("vehicle")
	if v is Vehicle:
		return v as Vehicle
	if target is Vehicle:
		return target as Vehicle
	return null


## Negative control (UW_AI_SABOTAGE=incar): disables R1, so the AI keeps aiming at the player's
## capsule inside the car - the pre-T-AI-03 bug, deliberately restored. Read once per run.
static var _sabotage_incar: int = -1


static func sabotage_incar() -> bool:
	if _sabotage_incar < 0:
		_sabotage_incar = 1 if OS.is_debug_build() and OS.get_environment("UW_AI_SABOTAGE").strip_edges() == "incar" else 0
	return _sabotage_incar == 1


## The node the AI should perceive and shoot at: the car when the target is seated, else the
## target itself. This is R1 - the single place where the substitution happens.
static func resolve(target: Node3D) -> Node3D:
	if sabotage_incar():
		return target
	var v := vehicle_of(target)
	return v if v != null else target


## Visibility points for perception. Seated target -> the car's window/body points (so a gunman
## needs line of sight to the CAR, not to the player's capsule). On foot -> the target's own
## get_visibility_points() (head/chest), unchanged.
static func perception_points(target: Node3D) -> Array:
	var v := vehicle_of(target)
	if v != null:
		return car_points(v)
	if target != null and target.has_method("get_visibility_points"):
		return target.get_visibility_points()
	if target != null:
		return [target.global_position + Vector3(0, 1.65, 0), target.global_position + Vector3(0, 1.15, 0)]
	return []


## Points on the car that can be hit: [cabin/glass, body]. The cabin point is where the driver
## actually sits, at window height - that is what a gunman can see and what counts for R3.
static func car_points(car: Vehicle) -> Array:
	if car == null:
		return []
	var body := car.global_position + Vector3(0, 0.9, 0)
	var cabin := body
	var seat := car.get_socket(&"SOCKET_Seat_Driver")
	if seat != null:
		cabin = seat.global_position + Vector3(0, 0.55, 0)
	return [cabin, body]


## Which part of the car a hit landed on, from the hit position (R3). "driver_window" when the
## hit is within `window_radius` of the driver's window point, else "body".
static func hit_zone(car: Vehicle, hit_position: Vector3, window_radius := 0.75) -> StringName:
	if car == null:
		return CHANNEL_CAR
	var pts := car_points(car)
	if pts.is_empty():
		return CHANNEL_CAR
	return &"driver_window" if hit_position.distance_to(pts[0]) <= window_radius else &"body"


## Damage split for one hit on the car (R2 + R3) -> {"car": float, "driver": float, "channel": ...}.
## The driver only ever takes `fraction` of a window hit and never dies from the car being shot
## while the car still has health (the mission's own fail states stay in charge of death).
static func split_damage(car: Vehicle, hit_position: Vector3, amount: float) -> Dictionary:
	if car == null or amount <= 0.0:
		return {"car": 0.0, "driver": 0.0, "channel": CHANNEL_CAR}
	var zone := hit_zone(car, hit_position)
	# R3: the window channel only exists while the car is intact ("only while the car's health
	# is above zero"). A wreck is cover for nobody - the driver is then just a person again.
	if car.health <= 0.0 or zone != &"driver_window" or car.driver == null:
		return {"car": amount, "driver": 0.0, "channel": CHANNEL_CAR}
	var fraction := 0.0
	if car.data != null:
		fraction = clampf(car.data.driver_window_fraction, 0.0, 1.0)
	return {"car": amount, "driver": amount * fraction, "channel": CHANNEL_DRIVER}
