# UNDERWORLD - data-driven weapon definition (T-GP-02).
# One .tres per weapon under res://Data/Weapons/. Values marked [DOC] come from the design
# docs (GAME_DESIGN §5, TASK_BOARD T-GP-02); [DEFAULT] = Bot 3 placeholder until Bot 1 sets
# a value (see Docs/TASK_BOARD.md T-GP-02 "Tuning defaults").
class_name WeaponData
extends Resource

enum FireMode { SEMI, AUTO }

@export var id := "WPN_Unnamed"
@export var display_name := "Weapon"
## Scene with the visual + Muzzle marker (PT_ stand-in now, Bot 2's .glb later).
@export var scene: PackedScene

@export_group("Fire")
@export var fire_mode: FireMode = FireMode.SEMI
## Rounds per minute (minimum time between shots = 60 / rpm).
@export var rpm := 300.0
@export var max_range := 150.0

@export_group("Damage")
@export var damage := 25.0
@export var headshot_multiplier := 2.0
@export var limb_multiplier := 0.75
## Full damage up to falloff_start; linear down to falloff_min_multiplier at falloff_end.
@export var falloff_start := 15.0
@export var falloff_end := 40.0
@export_range(0.0, 1.0) var falloff_min_multiplier := 0.5

@export_group("Ammo / reload")
@export var magazine_size := 12
@export var reserve_ammo := 60
@export var reload_time := 1.6
## Reload is cancelled by sprinting, and by firing while rounds are left in the magazine.
@export var reload_interruptible := true
## Start reloading automatically when the trigger is pulled on an empty magazine.
@export var auto_reload_on_empty := true

@export_group("Spread (degrees, cone half-angle)")
@export var spread_hip := 2.0
@export var spread_aim := 0.6
@export var crouch_multiplier := 0.7
## Added at full run speed (scaled by speed / run speed).
@export var spread_moving := 2.5
@export var spread_airborne := 5.0
## Bloom added per shot (degrees, raw value before bloom_aim_multiplier).
@export var bloom_per_shot := 0.8
## Cap for the accumulated raw bloom (degrees).
@export var bloom_max := 4.0
## Bloom recovery in degrees per second, starts bloom_recovery_delay seconds after the last shot.
@export var bloom_recovery := 6.0
## Seconds after a shot before bloom starts to recover (keep > fire interval so rapid fire stacks).
@export var bloom_recovery_delay := 0.35
## Bloom is scaled by this while aiming (aimed spread grows less than hip fire).
@export var bloom_aim_multiplier := 0.5

@export_group("Recoil (camera kick, degrees)")
@export var recoil_pitch := 2.2
## Random yaw kick in [-recoil_yaw, +recoil_yaw].
@export var recoil_yaw := 0.6
## Optional per-shot pattern (x = yaw, y = pitch, degrees); overrides the values above while it lasts.
@export var recoil_pattern: PackedVector2Array = PackedVector2Array()
@export var recoil_aim_multiplier := 0.7
## Exponential recovery rate (1/s) back to the pre-shot aim.
@export var recoil_recovery := 8.0

func get_fire_interval() -> float:
	return 60.0 / maxf(rpm, 1.0)

## Damage multiplier for a hit at distance d (metres).
func falloff_multiplier(d: float) -> float:
	if d <= falloff_start:
		return 1.0
	if d >= falloff_end:
		return falloff_min_multiplier
	return lerpf(1.0, falloff_min_multiplier, (d - falloff_start) / (falloff_end - falloff_start))

func zone_multiplier(zone: int) -> float:
	match zone:
		Hitbox.Zone.HEAD:
			return headshot_multiplier
		Hitbox.Zone.LIMB:
			return limb_multiplier
	return 1.0
