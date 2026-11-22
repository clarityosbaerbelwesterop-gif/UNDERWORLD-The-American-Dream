# UNDERWORLD - hitscan weapon runtime (T-GP-02). All tuning comes from `data` (WeaponData .tres).
# Owner-agnostic: the player (PlayerWeaponController) or later the enemy AI (T-AI-01) calls
# trigger() with an aim ray + stance; the weapon handles fire rate, ammo, reload, spread/bloom,
# hitscan with muzzle correction, damage (falloff + hit zones), hit feedback and impact FX.
class_name Weapon
extends Node3D

signal fired(shot: Dictionary)          ## every shot: origin, direction, end, spread_deg, kick_deg, hit
signal hit_confirmed(info: DamageInfo)  ## hit marker payload (a DamageReceiver was hit)
signal impact(position: Vector3, normal: Vector3, collider: Object)
signal dry_fired
signal reload_started(duration: float)
signal reload_finished
signal reload_cancelled
signal ammo_changed(magazine: int, reserve: int)

## World | Vehicles | Hitboxes. Character bodies (layer 3) are NOT shot directly.
const SHOT_MASK := 1 | 8 | 16
const MAX_IMPACTS := 32

@export var data: WeaponData:
	set(v):
		data = v
		if is_inside_tree():
			_apply_data()
## 0 = random seed; tests set a fixed seed for deterministic spread.
@export var spread_seed := 0

var ammo := 0
var reserve := 0
var is_reloading := false
var reload_left := 0.0
var cooldown := 0.0
var bloom := 0.0
var shots_fired := 0
var model: Node3D
var muzzle: Node3D
var _rng := RandomNumberGenerator.new()
var _impacts: Node3D
var _flash: Node3D
var _flash_left := 0.0
var _pattern_index := 0

func _ready() -> void:
	if spread_seed != 0:
		_rng.seed = spread_seed
	else:
		_rng.randomize()
	_impacts = Node3D.new()
	_impacts.name = "PT_Impacts"
	_impacts.top_level = true
	add_child(_impacts)
	_apply_data()

func _apply_data() -> void:
	if data == null:
		return
	if model != null:
		model.queue_free()
		model = null
	muzzle = null
	_flash = null
	if data.scene != null:
		model = data.scene.instantiate() as Node3D
		model.name = "Model"
		add_child(model)
		muzzle = _find(model, "SOCKET_Muzzle") as Node3D
		_flash = _find(model, "PT_MuzzleFlash") as Node3D
	ammo = data.magazine_size
	reserve = data.reserve_ammo
	is_reloading = false
	cooldown = 0.0
	bloom = 0.0
	_pattern_index = 0
	ammo_changed.emit(ammo, reserve)

func _find(n: Node, nm: String) -> Node:
	if String(n.name) == nm:
		return n
	for c in n.get_children():
		var r := _find(c, nm)
		if r != null:
			return r
	return null

func _physics_process(delta: float) -> void:
	if data == null:
		return
	cooldown = maxf(cooldown - delta, 0.0)
	bloom = maxf(bloom - data.bloom_recovery * delta, 0.0)
	if bloom <= 0.0:
		_pattern_index = 0
	if _flash_left > 0.0:
		_flash_left -= delta
		if _flash_left <= 0.0 and _flash != null:
			_flash.visible = false
	if is_reloading:
		reload_left -= delta
		if reload_left <= 0.0:
			_finish_reload()

# --- ammo / reload ----------------------------------------------------------

func can_reload() -> bool:
	return data != null and not is_reloading and ammo < data.magazine_size and reserve > 0

func start_reload() -> bool:
	if not can_reload():
		return false
	is_reloading = true
	reload_left = data.reload_time
	reload_started.emit(data.reload_time)
	return true

func cancel_reload() -> bool:
	if not is_reloading or not data.reload_interruptible:
		return false
	is_reloading = false
	reload_left = 0.0
	reload_cancelled.emit()
	return true

func _finish_reload() -> void:
	is_reloading = false
	reload_left = 0.0
	var take := mini(data.magazine_size - ammo, reserve)
	ammo += take
	reserve -= take
	reload_finished.emit()
	ammo_changed.emit(ammo, reserve)

# --- spread -----------------------------------------------------------------

## Current cone half-angle in degrees for a stance:
## {aiming: bool, crouching: bool, airborne: bool, move_frac: float (speed / run speed)}.
func get_spread_deg(stance: Dictionary) -> float:
	var aiming: bool = stance.get("aiming", false)
	var s := data.spread_aim if aiming else data.spread_hip
	if stance.get("crouching", false):
		s *= data.crouch_multiplier
	s += data.spread_moving * clampf(float(stance.get("move_frac", 0.0)), 0.0, 1.5) * (0.5 if aiming else 1.0)
	if stance.get("airborne", false):
		s += data.spread_airborne
	return s + bloom

func _spread_dir(dir: Vector3, spread_deg: float) -> Vector3:
	if spread_deg <= 0.0:
		return dir
	var r := deg_to_rad(spread_deg) * sqrt(_rng.randf())
	var phi := _rng.randf() * TAU
	var perp := dir.cross(Vector3.UP if absf(dir.y) < 0.99 else Vector3.RIGHT).normalized()
	var axis := perp.rotated(dir, phi)
	return dir.rotated(axis, r).normalized()

# --- firing -----------------------------------------------------------------

## Trigger input for one physics frame. Returns the shot dictionary if a round was fired, else {}.
## `just_pressed` = trigger pulled this frame, `held` = trigger held (AUTO fire).
func trigger(just_pressed: bool, held: bool, aim_origin: Vector3, aim_dir: Vector3,
		stance: Dictionary, shooter: Node = null, exclude: Array[RID] = []) -> Dictionary:
	if data == null:
		return {}
	var wants := just_pressed if data.fire_mode == WeaponData.FireMode.SEMI else (held or just_pressed)
	if not wants:
		return {}
	if is_reloading:
		if ammo > 0 and data.reload_interruptible:
			cancel_reload()
		else:
			return {}  # no fire during (non-interruptible / empty-mag) reload
	if ammo <= 0:
		if just_pressed:
			dry_fired.emit()
			if data.auto_reload_on_empty:
				start_reload()
		return {}
	if cooldown > 0.0:
		return {}
	return _fire(aim_origin, aim_dir.normalized(), stance, shooter, exclude)

func _fire(origin: Vector3, aim_dir: Vector3, stance: Dictionary, shooter: Node, exclude: Array[RID]) -> Dictionary:
	ammo -= 1
	shots_fired += 1
	cooldown = data.get_fire_interval()
	var spread := get_spread_deg(stance)
	var dir := _spread_dir(aim_dir, spread)
	var space := get_world_3d().direct_space_state
	var to := origin + dir * data.max_range
	var q := PhysicsRayQueryParameters3D.create(origin, to, SHOT_MASK, exclude)
	q.collide_with_areas = true
	var hit := space.intersect_ray(q)
	var end := to if hit.is_empty() else hit.position as Vector3
	# Muzzle correction: the bullet really leaves the muzzle; if something sits between the
	# muzzle and the crosshair point (e.g. a wall corner next to the shoulder), it is hit instead.
	if muzzle != null and muzzle.is_inside_tree():
		var m := muzzle.global_position
		var seg := end - m
		if seg.length() > 0.1:
			var q2 := PhysicsRayQueryParameters3D.create(m, end - seg.normalized() * 0.05, SHOT_MASK, exclude)
			q2.collide_with_areas = true
			var hit2 := space.intersect_ray(q2)
			if not hit2.is_empty():
				hit = hit2
				end = hit2.position
	var kick := _next_kick(stance.get("aiming", false))
	bloom = minf(bloom + data.bloom_per_shot, data.bloom_max)
	var shot := {"origin": origin, "direction": dir, "end": end, "spread_deg": spread, "kick_deg": kick,
		"hit": not hit.is_empty(), "collider": hit.get("collider"), "damage": null}
	if not hit.is_empty():
		var info := _resolve_hit(hit, origin, dir, shooter)
		shot["damage"] = info
		impact.emit(hit.position, hit.normal, hit.collider)
		_spawn_impact(hit.position, hit.normal)
	if _flash != null:
		_flash.visible = true
		_flash_left = 0.05
	ammo_changed.emit(ammo, reserve)
	fired.emit(shot)
	if ammo == 0 and data.auto_reload_on_empty:
		start_reload()
	return shot

func _next_kick(aiming: bool) -> Vector2:
	var k: Vector2
	if _pattern_index < data.recoil_pattern.size():
		k = data.recoil_pattern[_pattern_index]
	else:
		k = Vector2(_rng.randf_range(-data.recoil_yaw, data.recoil_yaw), data.recoil_pitch)
	_pattern_index += 1
	return k * (data.recoil_aim_multiplier if aiming else 1.0)

func _resolve_hit(hit: Dictionary, origin: Vector3, dir: Vector3, shooter: Node) -> DamageInfo:
	var box := hit.collider as Hitbox
	if box == null:
		return null
	var recv := box.get_receiver()
	if recv == null:
		return null
	var info := DamageInfo.new()
	info.distance = origin.distance_to(hit.position)
	info.base_damage = data.damage
	info.falloff = data.falloff_multiplier(info.distance)
	info.zone = box.zone
	info.headshot = box.zone == Hitbox.Zone.HEAD
	info.amount = data.damage * info.falloff * data.zone_multiplier(box.zone)
	info.position = hit.position
	info.normal = hit.normal
	info.direction = dir
	info.source = shooter
	info.weapon_id = data.id
	recv.apply_damage(info)
	hit_confirmed.emit(info)
	return info

## Placeholder impact decal (thin dark quad aligned to the surface). Pooled, max MAX_IMPACTS.
func _spawn_impact(pos: Vector3, normal: Vector3) -> void:
	if _impacts.get_child_count() >= MAX_IMPACTS:
		var old := _impacts.get_child(0)
		_impacts.remove_child(old)
		old.free()
	var mi := MeshInstance3D.new()
	mi.name = "PT_ImpactDecal"
	var bm := BoxMesh.new()
	bm.size = Vector3(0.06, 0.06, 0.004)
	mi.mesh = bm
	_impacts.add_child(mi)
	var up := Vector3.UP if absf(normal.y) < 0.99 else Vector3.FORWARD
	mi.global_transform = Transform3D(Basis.looking_at(-normal, up), pos + normal * 0.003)

func get_impact_count() -> int:
	return _impacts.get_child_count()
