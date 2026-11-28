# UNDERWORLD - checkpoint save/load tests (T-SAVE-01, TD-035).
#
#   UW_SAVE_DIR=$(mktemp -d) godot --headless --fixed-fps 60 --path GodotProject --script res://Tests/test_save.gd
#
# Drives the REAL level and the REAL shipping entry scene:
#   1. SaveGame file format: round trip, atomic write, missing / corrupt / foreign files rejected
#   2. M01 writes its checkpoints to disk (garage arrival, after the pickup) with player, car,
#      package and the dead gunmen
#   3. Quit + continue: a fresh level resumes from the file at the objective after the checkpoint,
#      package still in Jason's hands, garage still cleared, and the mission can be FINISHED from
#      there; the passed mission deletes the save
#   4. Dying after the pickup (in-memory restart) keeps the package with Jason (was a soft lock)
#   5. Invalid saves are rejected before anything in the level changes
#   6. GameBoot continues from the autosave, starts fresh on a corrupt file and on --new-game
#   7. A second Godot PROCESS (the game started again after quitting) continues from the file
#
# Negative controls (corrupt the production code path; the ordinary checks below must FAIL):
#   UW_SAVE_SABOTAGE=1  MissionManager never writes the checkpoint to disk
#   UW_SAVE_SABOTAGE=2  restoring a checkpoint ignores the package state (crate back on the bench)
#   UW_SAVE_SABOTAGE=3  SaveGame.read() skips the checksum (tampered/corrupt files load)
extends SceneTree

const LEVEL := "res://Scenes/Levels/LA_CallowayAve.tscn"
const HZ := 60.0
const WATCHDOG := 60 * 400
const SLOT := "test_m01"

var failures: Array[String] = []
var _frames := 0
var _done := false

var level: Node3D
var mm: MissionManager
var player: PlayerController
var car: Vehicle
var pkg: CarriedItem
var saved_cp5: Dictionary = {}

func check(cond: bool, msg: String) -> void:
	if cond:
		print("[GPTEST][PASS] ", msg)
	else:
		print("[GPTEST][FAIL] ", msg)
		failures.append(msg)

func _initialize() -> void:
	_run()

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

func _run() -> void:
	print("[GPTEST] == T-SAVE-01 checkpoint save/load (UW_SAVE_SABOTAGE=%s, dir %s)" % [
		OS.get_environment("UW_SAVE_SABOTAGE"), SaveGame.save_dir()])
	check(OS.get_environment("UW_SAVE_DIR") != "", "test runs in a scratch save dir (UW_SAVE_DIR), never in the player's user://")
	_clean()
	test_file_format()
	await test_checkpoints_written()
	await test_quit_and_continue()
	await test_death_after_pickup_keeps_package()
	await test_invalid_saves_rejected()
	await test_game_boot_continue()
	test_second_process()
	_clean()
	_done = true
	if failures.is_empty():
		print("[GPTEST] RESULT: PASS")
		quit(0)
	else:
		print("[GPTEST] RESULT: FAIL (%d)" % failures.size())
		for f in failures:
			print("[GPTEST]   - ", f)
		quit(1)

func _clean() -> void:
	for s in [SLOT, "autosave", "fmt", "bad"]:
		SaveGame.delete(s)

# --- fixture ------------------------------------------------------------------

func load_level(slot := SLOT) -> void:
	level = (load(LEVEL) as PackedScene).instantiate()
	root.add_child(level)
	await frames(3)
	mm = level.get_node("MissionManager") as MissionManager
	mm.save_slot = slot
	player = level.get_node("Player") as PlayerController
	car = level.get_node("VH_Sedan_01") as Vehicle
	pkg = level.get_node("Mission/Pickup_Package") as CarriedItem

func unload() -> void:
	level.queue_free()
	await frames(3)

func board_car() -> bool:
	player.global_position = car.get_socket(&"SOCKET_Exit_Left").global_position
	await frames(2)
	var ok := car.enter(player)
	await seconds(car.enter_duration() + 0.1)
	return ok and car.driver == player

func leave_car() -> void:
	car.request_exit()
	await seconds(car.exit_duration() + 0.6)

func kill_all_enemies() -> void:
	for guard in 4:
		for n in get_nodes_in_group("mission_enemies"):
			var e := n as MissionEnemy
			if e != null and not e.is_dead() and e.health != null:
				e.health.apply_damage(_damage(1000.0))
		await frames(12)
		if _dead_enemies() == get_nodes_in_group("mission_enemy").size():
			return

func _dead_enemies() -> int:
	var c := 0
	for n in get_nodes_in_group("mission_enemy"):
		if (n as MissionEnemy).is_dead():
			c += 1
	return c

func _active_enemies() -> int:
	var c := 0
	for n in get_nodes_in_group("mission_enemy"):
		var e := n as MissionEnemy
		if e.is_active() and not e.is_dead():
			c += 1
	return c

func _damage(amount: float) -> DamageInfo:
	var info := DamageInfo.new()
	info.amount = amount
	return info

## Plays M01 from the start up to the checkpoint after the pickup (objective 6 running).
func play_to_pickup(check_cp2 := false) -> void:
	var car_at_cp := {}
	mm.checkpoint_persisted.connect(func(i: int, _p: String) -> void: car_at_cp[i] = car.global_position)
	mm.start()
	await seconds(8.5)
	await board_car()
	car.global_position = level.get_node("Mission/Area_GarageArrival").global_position
	car.linear_velocity = Vector3.ZERO
	await frames(8)
	if check_cp2:
		check(mm.checkpoint_index == 2, "checkpoint 2 reached (garage arrival)")
		var d := SaveGame.read(SLOT)
		check(SaveGame.exists(SLOT) and int(d.get("checkpoint_index", -9)) == 2,
			"garage-arrival checkpoint written to disk (%s, index %s)" % [SaveGame.path(SLOT), str(d.get("checkpoint_index", "-"))])
		check(not FileAccess.file_exists(SaveGame.path(SLOT) + ".tmp"), "atomic write: no .tmp left behind")
		var cp := SaveGame.vec3_from_json(d.get("car", {}).get("pos"), Vector3.INF)
		var at: Vector3 = car_at_cp.get(2, Vector3.INF)
		check(cp.distance_to(at) < 0.01, "saved car position = car at the moment of the checkpoint (%.3f m)" % cp.distance_to(at))
		var pp := SaveGame.vec3_from_json(d.get("player", {}).get("pos"), Vector3.INF)
		check(pp.distance_to(car.get_socket(&"SOCKET_Exit_Left").global_position) < 0.3,
			"saved player position is the driver's exit socket, not the seat (B-M01-05)")
		check(String(d.get("package", {}).get("state", "")) == "ON_GROUND", "package on the bench at checkpoint 2")
		check((d.get("dead_enemies", [-1]) as Array).is_empty(), "no dead gunmen at checkpoint 2")
	await leave_car()
	player.global_position = level.get_node("Mission/Area_GarageInside").global_position
	await frames(6)
	await kill_all_enemies()
	await frames(8)
	player.global_position = pkg.global_position + Vector3(0, -1.0, 0.9)
	await frames(3)
	mm.try_interact(player)
	await frames(6)

# --- 1. file format -------------------------------------------------------------

func test_file_format() -> void:
	print("[GPTEST] == SaveGame file format")
	var data := {"mission_id": "M01_DeadDrop", "checkpoint_index": 5, "elapsed": 123.25,
		"player": {"pos": [1.5, 0.0, -2.25], "health": 80.0}, "dead_enemies": ["A", "B"]}
	check(SaveGame.write("fmt", data) == OK, "write() returns OK")
	check(SaveGame.exists("fmt"), "slot exists after write")
	var back := SaveGame.read("fmt")
	check(int(back.get("checkpoint_index", -1)) == 5 and String(back.get("mission_id", "")) == "M01_DeadDrop"
		and is_equal_approx(float(back.get("elapsed", 0.0)), 123.25)
		and SaveGame.vec3_from_json(back["player"]["pos"]).is_equal_approx(Vector3(1.5, 0.0, -2.25))
		and (back.get("dead_enemies", []) as Array).size() == 2,
		"round trip keeps every value")
	var b := Basis(Vector3.UP, 0.7) * Basis(Vector3.RIGHT, 0.1)
	check(SaveGame.basis_from_json(SaveGame.basis_to_json(b)).is_equal_approx(b.orthonormalized()), "basis round trip")
	check(SaveGame.read("does_not_exist").is_empty(), "missing slot -> {}")
	check(SaveGame.write("../escape", data) != OK and SaveGame.write("", data) != OK, "slot names cannot leave the save dir")
	# Tampered payload: still valid JSON, still a plausible save (other checkpoint), checksum stale.
	var text := FileAccess.get_file_as_string(SaveGame.path("fmt"))
	var w: Dictionary = JSON.parse_string(text)
	w["payload"] = String(w["payload"]).replace("\"checkpoint_index\":5", "\"checkpoint_index\":2")
	check(String(w["payload"]).contains("\"checkpoint_index\":2"), "tamper fixture changed the payload")
	_write_raw("bad", JSON.stringify(w))
	check(SaveGame.read("bad").is_empty(), "tampered file (checksum mismatch) is rejected")
	_write_raw("bad", text.substr(0, text.length() / 2))
	check(SaveGame.read("bad").is_empty(), "truncated file is rejected")
	w = JSON.parse_string(text)
	w["version"] = SaveGame.VERSION + 1
	_write_raw("bad", JSON.stringify(w))
	check(SaveGame.read("bad").is_empty(), "file from another save version is rejected")
	SaveGame.delete("fmt")
	SaveGame.delete("bad")
	check(not SaveGame.exists("fmt"), "delete() removes the slot")

func _write_raw(slot: String, text: String) -> void:
	DirAccess.make_dir_recursive_absolute(SaveGame.save_dir())
	var f := FileAccess.open(SaveGame.path(slot), FileAccess.WRITE)
	f.store_string(text)
	f.close()

# --- 2. checkpoints written -----------------------------------------------------

func test_checkpoints_written() -> void:
	print("[GPTEST] == M01 writes its checkpoints to disk")
	await load_level()
	await play_to_pickup(true)
	check(mm.current_index == 6 and pkg.is_carried(), "package picked up, objective 6 running")
	var d := SaveGame.read(SLOT)
	check(int(d.get("checkpoint_index", -9)) == 5, "pickup checkpoint written to disk (index %s)" % str(d.get("checkpoint_index", "-")))
	check(String(d.get("package", {}).get("state", "")) == "CARRIED", "saved package state CARRIED (%s)" % str(d.get("package", {}).get("state", "-")))
	var n_enemies := get_nodes_in_group("mission_enemy").size()
	check(n_enemies == 5 and (d.get("dead_enemies", []) as Array).size() == n_enemies,
		"all %d gunmen saved as dead (%d)" % [n_enemies, (d.get("dead_enemies", []) as Array).size()])
	check(String(d.get("mission_id", "")) == "M01_DeadDrop", "save names the mission")
	saved_cp5 = d
	await unload()

# --- 3. quit + continue ---------------------------------------------------------

func test_quit_and_continue() -> void:
	print("[GPTEST] == quit, load a fresh level, continue from the file, finish M01")
	await load_level()
	check(mm.state == MissionManager.State.IDLE and _dead_enemies() == 0 and not pkg.is_carried(), "fresh level: nothing carried over in memory")
	var d := SaveGame.read(SLOT)
	check(not d.is_empty(), "save file readable after the level was freed")
	var ok := mm.resume_from_save(d)
	await frames(6)
	check(ok and mm.state == MissionManager.State.RUNNING, "resume_from_save() accepted the file")
	check(mm.checkpoint_index == 5 and mm.current_index == 6, "continues at objective 6 'Deliver' (cp %d, obj %d)" % [mm.checkpoint_index, mm.current_index])
	check(mm.objective_text() == "Deliver the package to the warehouse.", "HUD objective after continue: %s" % mm.objective_text())
	check(pkg.is_carried() and pkg.carrier == player, "package is in Jason's hands again (state %s)" % CarriedItem.State.keys()[pkg.state])
	var pp := SaveGame.vec3_from_json(d.get("player", {}).get("pos"), Vector3.INF)
	check(player.global_position.distance_to(pp) < 0.5, "Jason at the saved position (%.2f m)" % player.global_position.distance_to(pp))
	var cp := SaveGame.vec3_from_json(d.get("car", {}).get("pos"), Vector3.INF)
	check(car.global_position.distance_to(cp) < 0.5, "sedan at the saved position (%.2f m)" % car.global_position.distance_to(cp))
	check(_dead_enemies() == 5 and _active_enemies() == 0, "garage stays cleared: %d dead, %d active" % [_dead_enemies(), _active_enemies()])
	check(SaveGame.exists(SLOT), "save still on disk while the mission runs")
	# Finish the mission from the loaded state: get in (the crate goes into the boot), drive.
	check(await board_car(), "Jason gets into the sedan after continuing")
	await frames(4)
	check(pkg.is_loaded(), "package loaded into the sedan by getting in")
	car.global_position = level.get_node("Mission/Area_Warehouse").global_position
	car.linear_velocity = Vector3.ZERO
	await frames(10)
	check(mm.current_index == 7, "delivered at the warehouse after continuing (obj %d)" % mm.current_index)
	mm.debug_complete_current()
	await frames(4)
	check(mm.state == MissionManager.State.COMPLETED, "mission COMPLETED from a loaded checkpoint")
	check(not SaveGame.exists(SLOT), "passed mission deletes its save (next boot starts fresh)")
	await unload()

# --- 4. die after the pickup ------------------------------------------------------

func test_death_after_pickup_keeps_package() -> void:
	print("[GPTEST] == die after the pickup -> restart keeps the package (B-M01-09, was a soft lock)")
	await load_level()
	await play_to_pickup()
	check(mm.checkpoint_index == 5 and pkg.is_carried(), "at checkpoint 5 with the package")
	var hp := player.get_node("Health") as DamageReceiver
	hp.apply_damage(_damage(999.0))
	await frames(4)
	check(mm.state == MissionManager.State.FAILED, "Jason died -> FAILED")
	await seconds(2.0)
	check(mm.state == MissionManager.State.RUNNING and mm.current_index == 6, "restart at objective 6")
	check(pkg.is_carried() and pkg.carrier == player, "restart gives Jason the package back (state %s)" % CarriedItem.State.keys()[pkg.state])
	check(_dead_enemies() == 5 and _active_enemies() == 0, "restart keeps the garage cleared (%d dead, %d active)" % [_dead_enemies(), _active_enemies()])
	check(await board_car(), "back into the sedan")
	await frames(4)
	car.global_position = level.get_node("Mission/Area_Warehouse").global_position
	car.linear_velocity = Vector3.ZERO
	await frames(10)
	check(mm.current_index == 7, "mission can still be delivered after the restart (obj %d)" % mm.current_index)
	await unload()
	SaveGame.delete(SLOT)

# --- 5. invalid saves --------------------------------------------------------------

func test_invalid_saves_rejected() -> void:
	print("[GPTEST] == invalid saves are rejected before the level is touched")
	await load_level()
	var base := saved_cp5.duplicate(true)
	if base.is_empty():
		base = {"mission_id": "M01_DeadDrop", "checkpoint_index": 5, "player": {"pos": [0, 0, 0]}}
	var other := base.duplicate(true)
	other["mission_id"] = "M99_Nothing"
	check(not mm.resume_from_save(other), "save of another mission rejected")
	var not_cp := base.duplicate(true)
	not_cp["checkpoint_index"] = 3
	check(not mm.resume_from_save(not_cp), "index of a non-checkpoint objective rejected")
	var bad_pkg := base.duplicate(true)
	bad_pkg["package"] = {"state": "EXPLODED"}
	check(not mm.resume_from_save(bad_pkg), "unknown package state rejected")
	check(mm.state == MissionManager.State.IDLE and mm.current_index == -1, "rejected saves left the mission untouched")
	await unload()

# --- 6. GameBoot ----------------------------------------------------------------------

func _boot() -> Dictionary:
	var game: Node = (load(str(ProjectSettings.get_setting("application/run/main_scene"))) as PackedScene).instantiate()
	root.add_child(game)
	await frames(12)
	var lvl := game.get_node("LA_CallowayAve")
	var m := lvl.get_node("MissionManager") as MissionManager
	var out := {"resumed": (game as GameBoot).resumed, "index": m.current_index, "state": m.state,
		"slot": m.save_slot, "carried": (lvl.get_node("Mission/Pickup_Package") as CarriedItem).is_carried()}
	game.queue_free()
	await frames(3)
	return out

func test_game_boot_continue() -> void:
	print("[GPTEST] == GameBoot continues from the autosave")
	SaveGame.delete("autosave")
	var r := await _boot()
	check(not r["resumed"] and r["state"] == MissionManager.State.RUNNING and r["index"] <= 1, "no save -> new mission (obj %d)" % r["index"])
	check(r["slot"] == "autosave", "GameBoot hands the autosave slot to the mission")
	check(not saved_cp5.is_empty() and SaveGame.write("autosave", saved_cp5) == OK, "autosave written from the checkpoint-5 state")
	r = await _boot()
	check(r["resumed"] and r["index"] == 6 and r["carried"], "boot continues at objective 6 with the package (resumed %s, obj %d)" % [str(r["resumed"]), r["index"]])
	# Tampered autosave (other checkpoint, stale checksum) -> refuse, start fresh.
	var text := FileAccess.get_file_as_string(SaveGame.path("autosave"))
	var w: Dictionary = JSON.parse_string(text)
	w["payload"] = String(w["payload"]).replace("\"checkpoint_index\":5", "\"checkpoint_index\":2")
	_write_raw("autosave", JSON.stringify(w))
	r = await _boot()
	check(not r["resumed"] and r["index"] <= 1, "corrupt autosave -> new mission, not a half-loaded one (resumed %s, obj %d)" % [str(r["resumed"]), r["index"]])
	SaveGame.write("autosave", saved_cp5)
	SaveGame.delete("autosave")

# --- 7. second process ----------------------------------------------------------------

func test_second_process() -> void:
	print("[GPTEST] == quit + start the game again (second Godot process)")
	check(not saved_cp5.is_empty() and SaveGame.write("autosave", saved_cp5) == OK, "autosave on disk before the restart")
	var out: Array = []
	var args := PackedStringArray(["--headless", "--fixed-fps", "60", "--path", ProjectSettings.globalize_path("res://"),
		"--script", "res://Tests/tools/save_resume_child.gd"])
	var code := OS.execute(OS.get_executable_path(), args, out, true)
	var text := "\n".join(PackedStringArray(out))
	var line := ""
	for l in text.split("\n"):
		if l.begins_with("[SAVECHILD]"):
			line = l
	print("[GPTEST] child: %s (exit %d)" % [line, code])
	check(code == 0, "second process exited 0")
	check(line.contains("resumed=true") and line.contains("index=6") and line.contains("checkpoint=5")
		and line.contains("carried=true") and line.contains("dead=5"),
		"restarted game continues at objective 6 with the package and a cleared garage")
	var errs := 0
	for l in text.split("\n"):
		if (l.begins_with("ERROR:") or l.begins_with("SCRIPT ERROR:")) and not l.contains("fontconfig"):
			errs += 1
			print("[GPTEST] child error: ", l)
	check(errs == 0, "second process logged no engine/script errors")
	SaveGame.delete("autosave")
