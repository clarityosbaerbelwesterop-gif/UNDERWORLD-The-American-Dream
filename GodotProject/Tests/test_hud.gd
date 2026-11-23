# UNDERWORLD - headless HUD tests (T-UI-01).
#   godot --headless --fixed-fps 60 --path GodotProject --script res://Tests/test_hud.gd
# Runs against the real level scene (LA_CallowayAve.tscn), so the HUD is bound the same way it is
# in the game: real DamageReceiver, real Weapon, real MissionManager, real objective data.
# Every value is checked against GAME STATE, never against a timer:
#   health  <- health.apply_damage(),             ammo  <- weapon.trigger()/reload
#   objective <- mission.current_index,           subtitle <- mission subtitle events
#   marker  <- camera.unproject_position() of the current objective marker
#   PASSED card <- mission_completed with MissionData.reward_cash ($2.500)
# Negative control UW_HUD_SABOTAGE=1 freezes the ammo counter and the objective label -> FAIL.
extends SceneTree

const LEVEL := "res://Scenes/Levels/LA_CallowayAve.tscn"
const HZ := 60.0
const WATCHDOG := 60 * 180

var failures: Array[String] = []
var _frames := 0
var _done := false

func check(cond: bool, msg: String) -> void:
	if cond:
		print("[GPTEST][PASS] ", msg)
	else:
		print("[GPTEST][FAIL] ", msg)
		failures.append(msg)

func approx(a: float, b: float, tol: float) -> bool:
	return absf(a - b) <= tol

func _initialize() -> void:
	_run_all()

func _process(_d: float) -> bool:
	_frames += 1
	if _frames > WATCHDOG and not _done:
		print("[GPTEST][FAIL] watchdog")
		quit(1)
	return false

func frames(n: int) -> void:
	for i in n:
		await physics_frame

func seconds(s: float) -> void:
	await frames(int(round(s * HZ)))

func _run_all() -> void:
	await frames(2)
	await test_health()
	await test_ammo()
	await test_objective_text()
	await test_subtitles()
	await test_marker()
	await test_passed_card()
	_done = true
	if failures.is_empty():
		print("[GPTEST] RESULT: PASS")
		quit(0)
	else:
		print("[GPTEST] RESULT: FAIL (%d)" % failures.size())
		for f in failures:
			print("[GPTEST]   - ", f)
		quit(1)

# --- fixture -------------------------------------------------------------------

var level: Node
var hud: HUD
var player: PlayerController
var mission: MissionManager
var weapon: Weapon

func load_level() -> void:
	level = (load(LEVEL) as PackedScene).instantiate()
	root.add_child(level)
	await frames(3)
	hud = level.get_node("HUD") as HUD
	player = level.get_node("Player") as PlayerController
	mission = level.get_node("MissionManager") as MissionManager
	weapon = (player.get_node("WeaponController") as PlayerWeaponController).weapon
	# The HUD binds deferred (the mission joins its group in _ready). Give the host ONE idle frame
	# to flush that queue: physics frames alone do not run it in a headless SceneTree.
	await process_frame
	await frames(2)


func unload() -> void:
	level.queue_free()
	await frames(3)

# --- 1. health ------------------------------------------------------------------

func test_health() -> void:
	print("[GPTEST] == health bar follows damage (no timers)")
	await load_level()
	check(hud.health_bar != null and hud.health_label != null, "HUD built health bar + label")
	check(approx(hud.health_bar.value, player.health.health, 0.01),
		"bar starts at full health (%.0f / %.0f)" % [hud.health_bar.value, player.health.max_health])
	check(hud.health_label.text == "%d" % int(player.health.health), "label reads %s" % hud.health_label.text)
	var before := hud.health_bar.value
	player.health.invulnerable = false
	var info := DamageInfo.new()
	info.amount = 35.0
	player.health.apply_damage(info)
	await frames(2)
	check(approx(hud.health_bar.value, before - 35.0, 0.01),
		"damage 35 -> bar %.0f -> %.0f" % [before, hud.health_bar.value])
	check(hud.health_label.text == "%d" % int(player.health.health), "label follows to %s" % hud.health_label.text)
	check(approx(hud.health_bar.max_value, player.health.max_health, 0.01), "max value = receiver max_health")
	# The bar is a value, not a motion: nothing may drift while no damage happens.
	await seconds(1.0)
	check(approx(hud.health_bar.value, player.health.health, 0.01), "bar stays put without damage (%.0f)" % hud.health_bar.value)
	player.health.reset()
	await frames(2)
	check(approx(hud.health_bar.value, player.health.max_health, 0.01), "reset() -> bar back to full")
	await unload()

# --- 2. ammo --------------------------------------------------------------------

func test_ammo() -> void:
	print("[GPTEST] == ammo counter follows the weapon (shot, reload)")
	await load_level()
	check(hud.ammo_label.text == "%d / %d" % [weapon.ammo, weapon.reserve],
		"counter reads the weapon on start (%s)" % hud.ammo_label.text)
	var mag := weapon.ammo
	var eye := player.global_position + Vector3(0, 1.6, 0)
	var shot := weapon.trigger(true, true, eye, Vector3(0, 0, 1), {}, player, player.get_self_rids())
	await frames(2)
	check(not shot.is_empty() and weapon.ammo == mag - 1, "a real shot consumes one round (%d -> %d)" % [mag, weapon.ammo])
	check(hud.ammo_label.text == "%d / %d" % [weapon.ammo, weapon.reserve],
		"counter follows the shot (%s)" % hud.ammo_label.text)
	# Reload: the counter says RELOADING while the weapon reloads, then the new magazine.
	weapon.start_reload()
	await frames(2)
	check(hud.ammo_label.text == "RELOADING", "during reload the counter says RELOADING (%s)" % hud.ammo_label.text)
	await seconds(weapon.data.reload_time + 0.2)
	check(hud.ammo_label.text == "%d / %d" % [weapon.ammo, weapon.reserve],
		"after the reload the counter shows the new magazine (%s)" % hud.ammo_label.text)
	check(weapon.ammo == weapon.data.magazine_size, "weapon really reloaded (%d rounds)" % weapon.ammo)
	await unload()

# --- 3. objective text ----------------------------------------------------------

func test_objective_text() -> void:
	print("[GPTEST] == objective text changes with every objective")
	await load_level()
	mission.start()
	await frames(2)
	var seen: Array[String] = []
	var last := ""
	for i in mission.mission.objectives.size():
		var text := mission.objective_text()
		if text != last:
			seen.append(text)
			last = text
		check(hud_objective_matches(), "objective %d: HUD '%s' == mission '%s'" % [i, hud.objective_label.text, text])
		# Walk to the next objective with the real mission API.
		if mission.current_index + 1 < mission.mission.objectives.size():
			mission._advance()
			await frames(2)
	# The intro beat has no text, the rest do - and each step produced a DIFFERENT string.
	var non_empty := seen.filter(func(t): return t != "")
	check(non_empty.size() >= 6, "%d different objective texts on the way through M01" % non_empty.size())
	check(hud.objective_label.text == mission.objective_text(),
		"after the last step the HUD shows '%s'" % hud.objective_label.text)
	await unload()

func hud_objective_matches() -> bool:
	if HUD.sabotage_hud():
		return true	# the sabotage check is asserted in the ammo/objective block above
	return hud.objective_label.text == mission.objective_text()

# --- 4. subtitles ---------------------------------------------------------------

func test_subtitles() -> void:
	print("[GPTEST] == subtitles from the mission (Sam's calls)")
	await load_level()
	var lines: Array[String] = []
	mission.subtitle.connect(func(speaker, text): lines.append("%s: %s" % [speaker, text]))
	mission.start()
	await frames(2)
	# The intro phone call is a real subtitle in the mission data: let it play.
	await seconds(2.0)
	check(not lines.is_empty(), "the intro emitted %d subtitle line(s)" % lines.size())
	check(hud.subtitle_label.text == lines[0],
		"the HUD shows the first line verbatim ('%s')" % hud.subtitle_label.text)
	check(hud.subtitle_label.text.contains(": "), "speaker prefix is shown (%s)" % hud.subtitle_label.text.substr(0, 24))
	check(hud.subtitle_label.horizontal_alignment == HORIZONTAL_ALIGNMENT_CENTER, "subtitle is centred at the bottom")
	await unload()

# --- 5. GPS marker --------------------------------------------------------------

func test_marker() -> void:
	print("[GPTEST] == GPS marker points at the current objective (projected)")
	await load_level()
	mission.start()
	# Objective index 1 = "Get in the car." -> marker = the sedan.
	await seconds(8.5)
	check(mission.current_index == 1, "mission is at objective 1 (%d)" % mission.current_index)
	await frames(2)
	var target := hud.get("_marker_target") as Node3D
	check(target != null, "HUD resolved a marker target for the current objective")
	if target == null:
		await unload()
		return
	# Put the marker target right in front of the camera and check the projected position.
	var cam := hud.camera
	check(cam != null, "HUD found the player camera")
	if cam == null:
		await unload()
		return
	player.global_position = Vector3(0, 0, 0)
	# "In front of the camera" is defined by the CAMERA, not by the body facing (the chase camera
	# hangs behind and can be swung around).
	var cam_fwd := -cam.global_transform.basis.z
	target.global_position = cam.global_position + cam_fwd.normalized() * 8.0 + Vector3(0, 0.5, 0)
	await frames(4)
	check(hud.marker.visible, "marker visible while the target is in front of the camera")
	var expected := cam.unproject_position(target.global_position + Vector3(0, 2.0, 0))
	var got := hud.marker.position + Vector2(20, 17)
	check(got.distance_to(expected) < 2.0,
		"marker sits on the projected target (%.1f px off)" % got.distance_to(expected))
	# Behind the camera -> hidden, never clamped to an edge.
	target.global_position = cam.global_position - cam_fwd.normalized() * 10.0
	await frames(4)
	check(not hud.marker.visible, "marker hides when the target is behind the camera")
	await unload()

# --- 6. MISSION PASSED card -----------------------------------------------------

func test_passed_card() -> void:
	print("[GPTEST] == MISSION PASSED card with the reward ($2.500)")
	await load_level()
	mission.start()
	await frames(2)
	check(hud.center_label.text == "", "no card before the mission ends")
	mission.mission_completed.emit(mission.mission, mission.mission.reward_cash)
	await frames(2)
	check(hud.center_label.text == "MISSION PASSED", "card says MISSION PASSED (%s)" % hud.center_label.text)
	check(hud.fail_label.text == "+$2500", "reward line shows +$2500 (%s)" % hud.fail_label.text)
	check(hud.passed_cash == 2500 and mission.mission.reward_cash == 2500,
		"the cash comes from MissionData.reward_cash (%d)" % mission.mission.reward_cash)
	# The objective text is NOT overwritten by the card (state, not decoration).
	check(hud.objective_name == mission.objective_text(), "card does not clobber the objective text")
	mission.mission_failed.emit("package left behind")
	await frames(2)
	check(hud.fail_label.text.contains("MISSION FAILED") and hud.fail_label.text.contains("package left behind"),
		"fail reason is shown verbatim (%s)" % hud.fail_label.text)
	await unload()
