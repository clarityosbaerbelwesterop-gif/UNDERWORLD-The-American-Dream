# UNDERWORLD - headless gunplay tests (T-GP-02).
# Run via Tests/run_gameplay_tests.sh (fixed 60 fps). Uses the PT_PlayerTestRange shooting lane:
#   player spawn (25.5, 0, 0); Target_10m (27, 0, -10); Target_35m (24, 0, -35); Backstop z = -38.5.
# Input is simulated on the real actions (fire, aim, reload, sprint, move_*).
extends SceneTree

const TEST_RANGE := "res://Scenes/Test/PT_PlayerTestRange.tscn"
const PISTOL := "res://Data/Weapons/WPN_Pistol_01.tres"
const TEST_AUTO := "res://Tests/Data/PT_Weapon_TestAuto.tres"
const HZ := 60.0
const SPAWN := Vector3(25.5, 0, 0)
const ACTIONS := ["fire", "aim", "reload", "sprint", "move_forward", "move_back", "move_left", "move_right", "jump", "crouch", "walk"]

var failures: Array[String] = []
var _frames := 0

func check(cond: bool, msg: String) -> void:
	print("[GPTEST][PASS] " if cond else "[GPTEST][FAIL] ", msg)
	if not cond:
		failures.append(msg)

func approx(a: float, b: float, tol: float) -> bool:
	return absf(a - b) <= tol

func _initialize() -> void:
	_run_all()

func _process(_d: float) -> bool:
	_frames += 1
	if _frames > 60 * 180:
		print("[GPTEST][FAIL] watchdog")
		quit(1)
	return false

func frames(n: int) -> void:
	for i in n:
		await physics_frame

func seconds(s: float) -> void:
	await frames(int(round(s * HZ)))

func release_all() -> void:
	for a in ACTIONS:
		Input.action_release(a)

func tap(action: String) -> void:
	Input.action_press(action)
	await frames(1)
	Input.action_release(action)
	await frames(1)

# --- fixture ---------------------------------------------------------------
var scene: Node
var p: PlayerController
var ctrl: PlayerWeaponController
var w: Weapon
var rig: CameraRig

func setup(data_path: String = PISTOL, zero_spread := false) -> void:
	scene = (load(TEST_RANGE) as PackedScene).instantiate()
	root.add_child(scene)
	p = scene.get_node("Player")
	ctrl = p.get_node("WeaponController")
	rig = p.camera_rig
	w = ctrl.weapon
	await frames(2)
	var d: WeaponData = (load(data_path) as WeaponData).duplicate()
	if zero_spread:
		for k in ["spread_hip", "spread_aim", "spread_moving", "spread_airborne", "bloom_per_shot"]:
			d.set(k, 0.0)
	w.data = d
	w.spread_seed = 1234
	w._rng.seed = 1234
	p.global_position = SPAWN
	p.velocity = Vector3.ZERO
	await frames(5)

func teardown() -> void:
	release_all()
	scene.queue_free()
	await frames(2)

func target(n: String) -> Node:
	return scene.get_node(n)

## Point the crosshair at a world point (iterates because the camera position depends on the angles).
func aim_at(pt: Vector3) -> void:
	for i in 4:
		var r := rig.get_aim_ray()
		var dir: Vector3 = (pt - r[0]).normalized()
		rig.yaw = atan2(-dir.x, -dir.z)
		rig.pitch = asin(clampf(dir.y, -1.0, 1.0))
		rig.recoil_offset = Vector2.ZERO
		rig.apply_look(Vector2.ZERO)
		await frames(2)

## Fire one shot via the real "fire" action and return the shot dict ({} if none).
func shoot() -> Dictionary:
	var shots := []
	var cb := func(s): shots.append(s)
	w.fired.connect(cb)
	await tap("fire")
	w.fired.disconnect(cb)
	return shots[0] if shots.size() > 0 else {}

func _run_all() -> void:
	await frames(1)
	await test_setup_and_data()
	await test_fire_reduces_ammo_and_feedback()
	await test_fire_rate_semi()
	await test_fire_rate_auto_other_tres()
	await test_empty_mag_auto_reload_and_duration()
	await test_dry_fire_without_auto_reload()
	await test_reload_interrupt()
	await test_damage_body_head_falloff()
	await test_kill_and_world_hit()
	await test_spread_by_stance()
	await test_bloom_rapid_fire()
	await test_recoil_kick_and_recovery()
	await test_socket_attach()
	if failures.is_empty():
		print("[GPTEST] RESULT: PASS")
		quit(0)
	else:
		print("[GPTEST] RESULT: FAIL (%d)" % failures.size())
		for f in failures:
			print("[GPTEST]   - ", f)
		quit(1)

# --- tests -------------------------------------------------------------------

func test_setup_and_data() -> void:
	print("[GPTEST] == weapon setup + WeaponData")
	var d := load(PISTOL) as WeaponData
	check(d != null and d.id == "WPN_Pistol_01", "WPN_Pistol_01.tres loads as WeaponData")
	check(d.magazine_size == 12 and approx(d.reload_time, 1.6, 0.0001), "design values: magazine 12, reload 1.6 s")
	scene = (load(TEST_RANGE) as PackedScene).instantiate()
	root.add_child(scene)
	p = scene.get_node("Player")
	await frames(3)
	ctrl = p.get_node_or_null("WeaponController") as PlayerWeaponController
	check(ctrl != null and ctrl.weapon != null, "Player has WeaponController + Weapon")
	if ctrl == null or ctrl.weapon == null:
		await teardown()
		return
	w = ctrl.weapon
	check(w.data.id == "WPN_Pistol_01" and w.ammo == 12 and w.reserve == 60, "player starts with the pistol, 12 + 60 rounds")
	check(w.get_parent().name == "SOCKET_RightHand_Weapon" and p.visual.model.is_ancestor_of(w), "weapon sits on SK_Jason's SOCKET_RightHand_Weapon")
	check(w.model != null and w.muzzle != null and w.model.get_node_or_null("Magazine") != null, "PT_Pistol model with SOCKET_Muzzle + Magazine node")
	var mh := w.muzzle.global_position.y - p.global_position.y
	check(mh > 0.6 and mh < 1.7, "muzzle at hand height (%.2f m above the feet, Jason idle pose)" % mh)
	check(scene.get_node_or_null("Target_10m/DamageReceiver") is DamageReceiver and scene.get_node_or_null("Target_35m") != null, "shooting-lane targets present")
	await teardown()

func test_fire_reduces_ammo_and_feedback() -> void:
	print("[GPTEST] == fire: ammo, hitscan from crosshair, feedback")
	await setup(PISTOL, true)
	var t := target("Target_10m")
	Input.action_press("aim")
	await seconds(0.6)
	await aim_at(t.global_position + Vector3(0, 1.15, 0))
	var marks := []
	ctrl.hitmarker.connect(func(i): marks.append(i))
	var impacts0 := w.get_impact_count()
	var ray := rig.get_aim_ray()
	var shot := await shoot()
	check(not shot.is_empty() and w.ammo == 11, "one shot fired, ammo 12 -> %d" % w.ammo)
	check(shot.get("origin", Vector3.ZERO).distance_to(ray[0]) < 0.05 and (shot.get("direction", Vector3.ZERO) as Vector3).dot(ray[1]) > 0.9999, "shot follows the crosshair ray (zero-spread data)")
	check(shot.get("collider") is Hitbox and (shot["collider"] as Hitbox).zone == Hitbox.Zone.BODY, "hitscan hits Target_10m body hitbox")
	check(marks.size() == 1 and ctrl.last_hitmarker.get("amount", 0.0) > 0.0, "hitmarker signal + last_hitmarker data (%s)" % [ctrl.last_hitmarker])
	check(w.get_impact_count() == impacts0 + 1, "impact decal placeholder spawned (%d)" % w.get_impact_count())
	check(p.get_facing_direction().dot(-rig.get_planar_basis().z) > 0.99, "character faces the shot direction")
	await teardown()

func _count_shots(frames_total: int, tap_every: int, hold: bool) -> Array:
	var shot_frames := []
	var i := [0]
	var cb := func(_s): shot_frames.append(i[0])
	w.fired.connect(cb)
	if hold:
		Input.action_press("fire")
	for f in frames_total:
		i[0] = f
		if not hold:
			if f % tap_every == 0:
				Input.action_press("fire")
			else:
				Input.action_release("fire")
		await frames(1)
	Input.action_release("fire")
	w.fired.disconnect(cb)
	return shot_frames

static func _min_gap(a: Array) -> int:
	var g := 1 << 30
	for k in range(1, a.size()):
		g = mini(g, a[k] - a[k - 1])
	return g

func test_fire_rate_semi() -> void:
	print("[GPTEST] == fire rate (semi pistol, 300 rpm)")
	await setup(PISTOL)
	var interval_frames := w.data.get_fire_interval() * HZ  # 12
	var s := await _count_shots(60, 2, false)
	check(s.size() >= 5 and s.size() <= 6, "spamming fire for 1 s -> %d shots (rpm 300 => 5-6)" % s.size())
	check(_min_gap(s) >= int(interval_frames) - 1, "min gap %d frames >= interval %.0f" % [_min_gap(s), interval_frames])
	await seconds(0.5)
	var held := await _count_shots(60, 0, true)
	check(held.size() == 1, "semi-auto: holding fire for 1 s = 1 shot (got %d)" % held.size())
	await teardown()

func test_fire_rate_auto_other_tres() -> void:
	print("[GPTEST] == different .tres changes behaviour (PT_Weapon_TestAuto)")
	await setup(TEST_AUTO)
	check(w.ammo == 30 and w.data.fire_mode == WeaponData.FireMode.AUTO, "test .tres: 30-round magazine, AUTO")
	var held := await _count_shots(60, 0, true)
	check(held.size() >= 9 and held.size() <= 11, "auto 600 rpm: holding fire 1 s -> %d shots" % held.size())
	check(_min_gap(held) >= 5, "auto min gap %d frames (interval 6)" % _min_gap(held))
	await teardown()
	# Recoil pattern from data: first kick = pattern[0] * aim multiplier.
	await setup(TEST_AUTO)
	var shot := await shoot()
	var want: Vector2 = w.data.recoil_pattern[0]
	check(shot.get("kick_deg", Vector2(9, 9)).distance_to(want) < 0.001, "recoil pattern from .tres: first kick %s == %s" % [shot.get("kick_deg"), want])
	await teardown()

func test_empty_mag_auto_reload_and_duration() -> void:
	print("[GPTEST] == 12 shots, empty mag -> auto-reload, 1.6 s, no fire during reload")
	await setup(PISTOL)
	var started := []
	var finished := []
	w.reload_started.connect(func(d): started.append(_frames))
	w.reload_finished.connect(func(): finished.append(_frames))
	var n := 0
	for k in 12:
		var s := await shoot()
		if not s.is_empty():
			n += 1
		await frames(12)
	check(n == 12 and w.ammo == 0, "12 shots empty the magazine (fired %d, ammo %d)" % [n, w.ammo])
	check(w.is_reloading and started.size() == 1, "auto-reload started on the empty magazine")
	var t0: int = started[0] if started.size() > 0 else _frames
	var s2 := await shoot()
	check(s2.is_empty() and w.ammo == 0, "no shot while reloading an empty magazine")
	while finished.is_empty() and _frames - t0 < 300:
		await frames(1)
	var dur: float = (finished[0] - t0) / HZ if finished.size() > 0 else -1.0
	check(approx(dur, 1.6, 1.5 / HZ), "reload took %.3f s (1.6 s)" % dur)
	check(w.ammo == 12 and w.reserve == 48, "magazine refilled from reserve: %d + %d" % [w.ammo, w.reserve])
	var s3 := await shoot()
	check(not s3.is_empty() and w.ammo == 11, "fires again after reload")
	await teardown()

func test_dry_fire_without_auto_reload() -> void:
	print("[GPTEST] == empty mag, auto_reload_on_empty = false (test .tres)")
	await setup(TEST_AUTO)
	w.ammo = 0
	var dry := [0]
	w.dry_fired.connect(func(): dry[0] += 1)
	var s := await shoot()
	check(s.is_empty() and dry[0] == 1 and not w.is_reloading, "dry fire: no shot, dry_fired signal, no auto-reload")
	await tap("reload")
	check(w.is_reloading, "manual reload starts")
	var s2 := await shoot()
	check(s2.is_empty(), "non-interruptible reload: fire does nothing")
	await seconds(2.6)
	check(not w.is_reloading and w.ammo == 30, "test .tres reload (2.5 s) completes -> 30 rounds")
	await teardown()

func test_reload_interrupt() -> void:
	print("[GPTEST] == interruptible reload (pistol)")
	await setup(PISTOL)
	for k in 3:
		await shoot()
		await frames(13)
	check(w.ammo == 9, "3 shots -> 9 rounds")
	var cancelled := [0]
	w.reload_cancelled.connect(func(): cancelled[0] += 1)
	await tap("reload")
	check(w.is_reloading, "R starts reload with 9 rounds left")
	await seconds(0.5)
	var s := await shoot()
	check(cancelled[0] == 1 and not s.is_empty() and w.ammo == 8 and not w.is_reloading, "firing with rounds left cancels the reload and shoots (ammo %d)" % w.ammo)
	await frames(13)
	await tap("reload")
	Input.action_press("move_forward")
	Input.action_press("sprint")
	await seconds(0.3)
	Input.action_release("move_forward")
	Input.action_release("sprint")
	check(cancelled[0] == 2 and not w.is_reloading and w.ammo == 8, "sprinting cancels the reload")
	Input.action_press("move_forward")
	Input.action_press("sprint")
	await seconds(0.4)
	var s2 := await shoot()
	Input.action_release("move_forward")
	Input.action_release("sprint")
	check(s2.is_empty(), "no firing while sprinting")
	await teardown()

func test_damage_body_head_falloff() -> void:
	print("[GPTEST] == damage: body, head, falloff (zero-spread copy of the pistol data)")
	await setup(PISTOL, true)
	var near := target("Target_10m")
	var far := target("Target_35m")
	var recv: DamageReceiver = near.get_node("DamageReceiver")
	Input.action_press("aim")
	await seconds(0.6)
	await aim_at(near.global_position + Vector3(0, 1.15, 0))
	var s := await shoot()
	var info: DamageInfo = s.get("damage")
	check(info != null and info.zone == Hitbox.Zone.BODY and approx(info.amount, 25.0, 0.001), "body @ %.1f m = 25 dmg (got %s)" % [info.distance if info else -1.0, info.amount if info else null])
	check(approx(recv.health, 75.0, 0.001), "Target_10m health 100 -> %.1f" % recv.health)
	await seconds(0.4)
	await aim_at(near.global_position + Vector3(0, 1.68, 0))
	s = await shoot()
	info = s.get("damage")
	check(info != null and info.headshot and approx(info.amount, 50.0, 0.001), "headshot x2 = 50 dmg (got %s)" % [info.amount if info else null])
	await seconds(0.4)
	await aim_at(near.global_position + Vector3(0, 0.4, 0))
	s = await shoot()
	info = s.get("damage")
	check(info != null and info.zone == Hitbox.Zone.LIMB and approx(info.amount, 18.75, 0.001), "leg x0.75 = 18.75 dmg (got %s)" % [info.amount if info else null])
	await seconds(0.4)
	await aim_at(far.global_position + Vector3(0, 1.15, 0))
	s = await shoot()
	info = s.get("damage")
	var want: float = 25.0 * w.data.falloff_multiplier(info.distance) if info else -1.0
	check(info != null and info.distance > 34.0 and info.distance < 38.0, "far target hit at %.2f m" % [info.distance if info else -1.0])
	check(info != null and approx(info.amount, want, 0.001) and info.amount < 25.0 * 0.65 and info.amount >= 12.5, "falloff: %.2f dmg at %.1f m (expected %.2f; 25 -> 12.5 between 15-40 m)" % [info.amount if info else -1.0, info.distance if info else -1.0, want])
	check(approx(w.data.falloff_multiplier(10.0), 1.0, 0.0001) and approx(w.data.falloff_multiplier(27.5), 0.75, 0.0001) and approx(w.data.falloff_multiplier(60.0), 0.5, 0.0001), "falloff curve 10 m=1.0, 27.5 m=0.75, 60 m=0.5")
	await teardown()

func test_kill_and_world_hit() -> void:
	print("[GPTEST] == kill + world impact (no hitmarker)")
	await setup(PISTOL, true)
	var near := target("Target_10m")
	var recv: DamageReceiver = near.get_node("DamageReceiver")
	var died := [0]
	recv.died.connect(func(_i): died[0] += 1)
	Input.action_press("aim")
	await seconds(0.6)
	var last: DamageInfo
	for k in 4:
		await aim_at(near.global_position + Vector3(0, 1.15, 0))
		var s := await shoot()
		last = s.get("damage")
		await frames(12)
	check(recv.is_dead and died[0] == 1 and last != null and last.killed, "4 body shots (4 x 25) kill the 100 HP dummy, killed flag in hitmarker")
	await frames(3)
	var marks := []
	ctrl.hitmarker.connect(func(i): marks.append(i))
	var imp := w.get_impact_count()
	await aim_at(near.global_position + Vector3(0, 1.15, 0))
	var s2 := await shoot()
	check(s2.get("hit", false) and not (s2.get("collider") is Hitbox) and marks.is_empty(), "dead dummy's hitboxes off: shot hits the world, no hitmarker (%s)" % [s2.get("collider")])
	check(w.get_impact_count() == imp + 1, "world hit still spawns an impact decal")
	near.reset()
	check(not recv.is_dead and recv.health == 100.0, "dummy reset()")
	await teardown()

func test_spread_by_stance() -> void:
	print("[GPTEST] == spread by stance + bloom")
	await setup(PISTOL)
	await seconds(0.3)
	var hip_still := w.get_spread_deg(ctrl.get_stance())
	Input.action_press("aim")
	await seconds(0.3)
	var aim_still := w.get_spread_deg(ctrl.get_stance())
	Input.action_press("move_forward")
	await seconds(1.0)
	var aim_moving := w.get_spread_deg(ctrl.get_stance())
	Input.action_release("aim")
	await seconds(1.0)
	var hip_moving := w.get_spread_deg(ctrl.get_stance())
	var shot_moving := await shoot()
	Input.action_release("move_forward")
	await seconds(1.5)
	Input.action_press("jump")
	await frames(10)
	Input.action_release("jump")
	var airborne := w.get_spread_deg(ctrl.get_stance())
	await seconds(1.5)
	await tap("crouch")
	Input.action_press("aim")
	await seconds(0.3)
	var crouch_aim := w.get_spread_deg(ctrl.get_stance())
	var shot_aim := await shoot()
	print("[GPTEST] spread deg: crouch_aim %.2f aim_still %.2f aim_moving %.2f hip_still %.2f hip_moving %.2f airborne %.2f" % [crouch_aim, aim_still, aim_moving, hip_still, hip_moving, airborne])
	check(crouch_aim < aim_still and aim_still < hip_still, "crouched-aim < aim < hip while standing still")
	check(aim_moving > aim_still and hip_moving > hip_still, "moving widens spread")
	check(airborne > hip_moving, "airborne is widest (%.2f)" % airborne)
	check(not shot_moving.is_empty() and not shot_aim.is_empty() and shot_moving["spread_deg"] > 2.0 * shot_aim["spread_deg"], "actual shot cone: running hip %.2f° vs crouched aim %.2f°" % [shot_moving.get("spread_deg", -1.0), shot_aim.get("spread_deg", -1.0)])
	# Bloom: 3 quick shots widen the cone, then it recovers.
	await seconds(1.0)
	var base := w.get_spread_deg(ctrl.get_stance())
	var bloomed := base
	for k in 3:
		await shoot()
		bloomed = maxf(bloomed, w.get_spread_deg(ctrl.get_stance()))
		await frames(12)
	await seconds(1.5)
	var recovered := w.get_spread_deg(ctrl.get_stance())
	check(bloomed >= base + w.data.bloom_per_shot * 0.9 and approx(recovered, base, 0.01), "bloom %.2f -> %.2f -> recovers %.2f" % [base, bloomed, recovered])
	await teardown()

## T-GP-02a: rapid fire stacks bloom up to the cap, recovery only after bloom_recovery_delay, aimed < hip.
func _rapid_fire(n: int) -> Array:
	var out := []
	for k in n:
		var shot := await shoot()
		out.append({"fired": not shot.is_empty(), "bloom": w.bloom, "spread": w.get_spread_deg(ctrl.get_stance())})
		await frames(11)  # 2 (tap) + 11 = 13 frames > 12-frame fire interval at 300 rpm
	return out

func test_bloom_rapid_fire() -> void:
	print("[GPTEST] == rapid-fire bloom: stacking, cap, recovery delay, aimed < hip (T-GP-02a)")
	await setup(PISTOL)
	var d := w.data
	check(d.bloom_recovery_delay > d.get_fire_interval(), "data: recovery delay %.2f s > fire interval %.2f s (bloom can stack)" % [d.bloom_recovery_delay, d.get_fire_interval()])
	check(d.bloom_aim_multiplier < 1.0, "data: aimed bloom multiplier %.2f < 1" % d.bloom_aim_multiplier)
	await seconds(0.3)
	var hip_base := w.get_spread_deg(ctrl.get_stance())
	# Time-based clock: seconds (sum of physics deltas) since the last shot.
	var clk := {"since": 0.0}
	var on_shot := func(_s): clk["since"] = 0.0
	var on_tick := func(): clk["since"] += root.get_physics_process_delta_time()
	w.fired.connect(on_shot)
	physics_frame.connect(on_tick)
	var r := await _rapid_fire(8)
	var fired := r.filter(func(x): return x["fired"]).size()
	check(fired == 8, "8 rapid shots fired (%d)" % fired)
	var to_cap := int(ceil(d.bloom_max / d.bloom_per_shot))  # 5
	var grows := true
	for k in range(1, to_cap):
		grows = grows and approx(r[k]["bloom"] - r[k - 1]["bloom"], d.bloom_per_shot, 0.001)
	print("[GPTEST] hip spread per shot: %s" % [r.map(func(x): return snappedf(x["spread"], 0.01))])
	check(grows and r[to_cap - 1]["spread"] > hip_base + d.bloom_max - 0.01, "rapid fire stacks +%.1f°/shot: %.2f -> %.2f after %d shots" % [d.bloom_per_shot, hip_base, r[to_cap - 1]["spread"], to_cap])
	var capped := true
	for k in range(to_cap, 8):
		capped = capped and approx(r[k]["bloom"], d.bloom_max, 0.0001) and approx(r[k]["spread"], hip_base + d.bloom_max, 0.0001)
	check(capped, "bloom capped at %.1f°: shots %d-8 stay at %.2f°" % [d.bloom_max, to_cap + 1, hip_base + d.bloom_max])
	var dt := root.get_physics_process_delta_time()  # tolerances below: clock vs weapon tick order differs by <= 3 frames
	var delay := d.bloom_recovery_delay
	var held := true
	var held_until := 0.0
	while clk["since"] < delay - 2.0 * dt:
		held = held and approx(w.bloom, d.bloom_max, 0.0001)
		held_until = clk["since"]
		await physics_frame
	check(held and held_until >= delay - 4.0 * dt, "no recovery during the delay: bloom stays %.1f° until %.3f s after the last shot (delay %.2f s)" % [d.bloom_max, held_until, delay])
	while clk["since"] < delay + 0.2:
		await physics_frame
	var after: float = clk["since"] - delay
	var want_b := d.bloom_max - d.bloom_recovery * after
	check(w.bloom < d.bloom_max and approx(w.bloom, want_b, d.bloom_recovery * 3.0 * dt), "recovery starts at the delay: %.2f s later bloom %.2f° (expected %.2f° at %.0f°/s)" % [after, w.bloom, want_b, d.bloom_recovery])
	while clk["since"] < delay + d.bloom_max / d.bloom_recovery + 2.0 * dt:
		await physics_frame
	check(w.bloom == 0.0 and approx(w.get_spread_deg(ctrl.get_stance()), hip_base, 0.0001), "fully recovered to %.2f° at %.2f s (delay + max / rate)" % [hip_base, clk["since"]])
	w.fired.disconnect(on_shot)
	physics_frame.disconnect(on_tick)
	# Aimed: same 8 shots -> smaller spread at every shot, aimed bloom = bloom * multiplier.
	w.ammo = d.magazine_size  # refill (8 of 12 rounds used above)
	Input.action_press("aim")
	await seconds(0.6)
	var aim_base := w.get_spread_deg(ctrl.get_stance())
	var ra := await _rapid_fire(8)
	check(ra.filter(func(x): return x["fired"]).size() == 8, "8 aimed rapid shots fired")
	var smaller := true
	for k in 8:
		smaller = smaller and ra[k]["spread"] < r[k]["spread"]
	print("[GPTEST] aimed spread per shot: %s" % [ra.map(func(x): return snappedf(x["spread"], 0.01))])
	check(smaller, "aimed spread < hip spread at every shot (aim cap %.2f vs hip cap %.2f)" % [ra[7]["spread"], r[7]["spread"]])
	check(approx(ra[7]["spread"] - aim_base, d.bloom_max * d.bloom_aim_multiplier, 0.001), "aimed bloom cap = %.1f x %.1f = %.2f°" % [d.bloom_max, d.bloom_aim_multiplier, ra[7]["spread"] - aim_base])
	await teardown()

func test_recoil_kick_and_recovery() -> void:
	print("[GPTEST] == recoil kick + recovery")
	await setup(PISTOL)
	Input.action_press("aim")
	await seconds(0.6)
	var pitch0 := rig.get_effective_pitch()
	var want := deg_to_rad(w.data.recoil_pitch * w.data.recoil_aim_multiplier)
	Input.action_press("fire")
	await frames(2)  # physics_frame fires before node processing: the shot happens during frame 1
	var k: Vector2 = rig.recoil_offset
	Input.action_release("fire")
	# one frame of exponential recovery (rate 8/s) may already have run: >= 85 % of the kick
	check(k.y <= want + 0.0005 and k.y >= want * 0.85, "camera kicks up %.2f° (expected %.2f°)" % [rad_to_deg(k.y), rad_to_deg(want)])
	check(rig.get_effective_pitch() > pitch0 + want * 0.5, "effective pitch raised right after the shot")
	await seconds(1.0)
	check(rig.recoil_offset.length() < want * 0.05 and approx(rig.get_effective_pitch(), pitch0, 0.002), "recovers to the original aim after 1 s (offset %.5f rad)" % rig.recoil_offset.length())
	await teardown()

func test_socket_attach() -> void:
	print("[GPTEST] == weapon moves to SOCKET_RightHand_Weapon of a real model")
	await setup(PISTOL)
	var m := Node3D.new()
	m.name = "PT_DummyJason"
	var sock := Node3D.new()
	sock.name = "SOCKET_RightHand_Weapon"
	m.add_child(sock)
	sock.owner = m
	sock.position = Vector3(-0.2, 1.1, 0.3)
	var ps := PackedScene.new()
	ps.pack(m)
	m.free()
	p.visual.set_model(ps)
	await frames(1)
	check(ctrl.attach_to_model_socket() and w.get_parent().name == "SOCKET_RightHand_Weapon", "weapon reparented to the model socket")
	var s := await shoot()
	check(not s.is_empty(), "still fires after re-attachment")
	await teardown()
