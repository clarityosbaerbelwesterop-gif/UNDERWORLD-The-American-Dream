extends SceneTree
## T-AUD-01 - procedural audio library + AudioDirector.
##   * res://Data/Content/audio.json: >= 120 events, every event has files, every binding
##     (weapons, FX, footsteps, vehicles, UI, music, ambience) names an existing event
##   * every combat.json weapon and every catalogue vehicle has its own sound binding
##   * Ogg files: if rendered (CI renders them first, UW_AUDIO_REQUIRE_FILES=1) every event's
##     streams load, are non-empty and loop events loop
##   * runtime: a real pistol shot plays fire + tail, a reload plays the mag-out/in/slide steps
##     in order, an impact FX plays its surface sound, a fire FX gets a looping emitter, a
##     vehicle gets the 3 engine layers with a correct RPM crossfade, crash/door play, mission
##     signals play UI + stingers, combat switches the score, the voice pool steals
## Negative control: UW_AUDIO_SABOTAGE=1 resolves every event to UI_Click -> the event checks fail.

var failures: PackedStringArray = []
var d: AudioDirector

func check(cond: bool, msg: String) -> void:
	print("[GPTEST][PASS] " if cond else "[GPTEST][FAIL] ", msg)
	if not cond:
		failures.append(msg)

func _initialize() -> void:
	_run()

func frames(n: int) -> void:
	for i in n:
		await physics_frame

func _run() -> void:
	print("[GPTEST] == audio (T-AUD-01)")
	d = AudioDirector.instance
	if d == null:
		d = AudioDirector.new()
		d.name = "Audio"
		root.add_child(d)
	await frames(2)
	check(AudioDirector.instance == d, "AudioDirector singleton is live")
	_table()
	_files()
	await _weapon()
	await _fx()
	_footsteps()
	await _vehicle()
	await _mission_and_music()
	_pool()
	if failures.is_empty():
		print("[GPTEST] RESULT: PASS")
		quit(0)
	else:
		print("[GPTEST] RESULT: FAIL (%d)" % failures.size())
		quit(1)

# --- data --------------------------------------------------------------------------

func _table() -> void:
	check(d.events.size() >= 120, "%d audio events in the table (>= 120)" % d.events.size())
	var empty := []
	var files := 0
	for id in d.events:
		var n: int = (d.events[id] as Dictionary).get("files", []).size()
		files += n
		if n == 0:
			empty.append(id)
	check(empty.is_empty(), "every event has >= 1 file %s (%d files)" % [str(empty), files])
	for b in ["Music", "SFX", "Weapons", "Vehicles", "Foley", "Ambience", "UI"]:
		check(AudioServer.get_bus_index(b) != -1, "bus %s exists" % b)
	# every binding resolves
	var bad := []
	var wb: Dictionary = d.bindings.get("weapons", {})
	for wid in wb:
		for k in ["fire", "tail", "hit", "explode", "pump_after_shot"]:
			if (wb[wid] as Dictionary).has(k) and not d.has_event(String(wb[wid][k])):
				bad.append("%s.%s" % [wid, k])
		for step in (wb[wid] as Dictionary).get("reload", []):
			if not d.has_event(String(step[1])):
				bad.append("%s.reload %s" % [wid, step[1]])
	for fx in d.bindings.get("fx", {}):
		if not d.has_event(String(d.bindings["fx"][fx])):
			bad.append(fx)
	for sec in ["ui", "character"]:
		for k in d.bindings.get(sec, {}):
			var v = d.bindings[sec][k]
			if v is String and not d.has_event(v):
				bad.append("%s.%s" % [sec, k])
	for k in ["explore", "combat", "menu", "passed", "failed"]:
		if not d.has_event(String(d.bindings.get("music", {}).get(k, ""))):
			bad.append("music." + k)
	var amb: Dictionary = d.bindings.get("ambience", {})
	for k in amb:
		if amb[k] is String and not d.has_event(amb[k]):
			bad.append("ambience." + k)
	for o in amb.get("oneshots", []):
		if not d.has_event(String(o)):
			bad.append("ambience.oneshot " + String(o))
	var surfaces := ["Concrete"]
	for g in d.bindings.get("footsteps", {}).get("groups", {}):
		surfaces.append(String(d.bindings["footsteps"]["groups"][g]))
	for s in surfaces:
		for gait in ["Walk", "Run"]:
			if not d.has_event("SFX_FS_%s_%s" % [s, gait]):
				bad.append("footstep %s %s" % [s, gait])
	check(bad.is_empty(), "every audio binding names an existing event %s" % str(bad))
	# coverage: weapons + vehicles
	var combat = JSON.parse_string(FileAccess.get_file_as_string("res://Data/Content/combat.json"))
	var unbound := []
	for wid in (combat as Dictionary).get("weapons", {}):
		if not wb.has(wid):
			unbound.append(wid)
	check(unbound.is_empty(), "every combat.json weapon has its own sound set %s" % str(unbound))
	var path := ProjectSettings.globalize_path("res://").path_join("../Config/Content/catalog.json").simplify_path()
	var cat = JSON.parse_string(FileAccess.get_file_as_string(path))
	var sets: Dictionary = d.bindings.get("vehicles", {}).get("engine_sets", {})
	var no_engine := []
	for e in (cat as Dictionary).get("entries", []):
		if String(e.get("type", "")) == "vehicle":
			var kind := String(sets.get(String(e["id"]), ""))
			if kind.is_empty() or not d.has_event("SFX_VEH_%s_Engine_High" % kind):
				no_engine.append(e["id"])
	check(no_engine.is_empty(), "every catalogue vehicle has an engine set (3 RPM layers) %s" % str(no_engine))

func _files() -> void:
	var require := OS.get_environment("UW_AUDIO_REQUIRE_FILES") == "1"
	var present := 0
	var total := 0
	for id in d.events:
		for f in (d.events[id] as Dictionary).get("files", []):
			total += 1
			if FileAccess.file_exists(String(f)) or ResourceLoader.exists(String(f)):
				present += 1
	print("[GPTEST] audio files on disk: %d / %d" % [present, total])
	if present == 0 and not require:
		print("[GPTEST] note: Ogg library not rendered on this box (Tools/uwp build-audio) - stream checks skipped")
		return
	check(present == total, "all %d Ogg files are on disk (%d)" % [total, present])
	var bad := []
	for id in d.events:
		var ev: Dictionary = d.events[id]
		var s := d.load_stream(String(ev["files"][0]), bool(ev.get("loop", false)))
		if s == null or s.get_length() <= 0.02:
			bad.append(id)
		elif bool(ev.get("loop", false)) and s is AudioStreamOggVorbis and not (s as AudioStreamOggVorbis).loop:
			bad.append(id + " (no loop)")
	check(bad.is_empty(), "every event's stream loads (non-empty, loops loop) %s" % str(bad))

# --- runtime -----------------------------------------------------------------------

func _weapon() -> void:
	var world := Node3D.new()
	root.add_child(world)
	var w := Weapon.new()
	w.data = (load("res://Data/Weapons/WPN_Pistol_01.tres") as WeaponData).duplicate()
	w.spread_seed = 7
	world.add_child(w)
	await frames(3)
	d.clear_history()
	var r := w.trigger(true, true, Vector3(0, 1.4, 0), Vector3(0, 0, 1), {"aiming": true, "crouch": false, "moving": false})
	await frames(1)
	check(d.played("SFX_WPN_Pistol_Fire"), "pistol shot plays SFX_WPN_Pistol_Fire (shot fired: %s)" % str(not r.is_empty()))
	check(d.played("SFX_WPN_Pistol_Tail"), "pistol shot plays the distance tail SFX_WPN_Pistol_Tail")
	await frames(45)
	check(d.played("SFX_WPN_ShellCasing"), "the ejected casing lands (SFX_WPN_ShellCasing)")
	d.clear_history()
	check(w.start_reload(), "reload starts")
	await frames(int(w.data.reload_time * 60.0) + 10)
	var seq := []
	for id in d.history:
		if id.begins_with("SFX_WPN_Mag") or id == "SFX_WPN_SlideRack":
			seq.append(id)
	check(seq == ["SFX_WPN_MagOut_Pistol", "SFX_WPN_MagIn_Pistol", "SFX_WPN_SlideRack"],
		"reload plays mag out -> mag in -> slide in time (%s)" % str(seq))
	d.clear_history()
	w.ammo = 0
	w.reserve = 0
	w.cooldown = 0.0
	w.trigger(true, true, Vector3(0, 1.4, 0), Vector3(0, 0, 1), {"aiming": true, "crouch": false, "moving": false})
	await frames(2)
	check(d.played("SFX_WPN_DryFire"), "empty trigger plays the dry fire click")
	world.queue_free()
	await frames(2)

func _fx() -> void:
	var holder := Node3D.new()
	root.add_child(holder)
	await frames(1)
	d.clear_history()
	var imp := FXEffect.spawn("FX_Impact_Metal", holder, Transform3D(Basis(), Vector3(2, 0, 0)))
	await frames(2)
	check(imp != null and d.played("SFX_IMP_Metal"), "FX_Impact_Metal plays SFX_IMP_Metal")
	var fire := FXEffect.spawn("FX_Fire", holder, Transform3D.IDENTITY)
	await frames(2)
	var em := fire.get_node_or_null("UW_Audio_SFX_FIRE_Loop") if fire != null else null
	check(em is AudioStreamPlayer3D, "FX_Fire carries a looping SFX_FIRE_Loop emitter")
	holder.queue_free()
	await frames(2)

func _footsteps() -> void:
	check(d.footstep_event(null, 1.4) == "SFX_FS_Concrete_Walk", "walking on untagged ground = concrete walk")
	var metal := StaticBody3D.new()
	metal.add_to_group(&"surface_metal")
	check(d.footstep_event(metal, 3.5) == "SFX_FS_Metal_Run", "running on surface_metal = metal run")
	var grass := StaticBody3D.new()
	grass.add_to_group(&"surface_grass")
	check(d.footstep_event(grass, 1.0) == "SFX_FS_Grass_Walk", "surface_grass = grass walk")
	metal.free()
	grass.free()

func _vehicle() -> void:
	var floor_body := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(60, 1, 60)
	cs.shape = box
	cs.position.y = -0.5
	floor_body.add_child(cs)
	root.add_child(floor_body)
	var car := (load("res://Scenes/Vehicles/VH_Sedan_01.tscn") as PackedScene).instantiate() as Vehicle
	car.control_override = true
	car.position = Vector3(0, 0.5, 0)
	root.add_child(car)
	await frames(30)
	var layers := ["Idle", "Low", "High"]
	var ok := true
	for l in layers:
		ok = ok and car.get_node_or_null("UW_Engine_" + l) is AudioStreamPlayer3D
	check(ok, "vehicle gets the 3 engine RPM layers (Idle/Low/High)")
	var rec: Dictionary = {}
	for r in d._vehicles:
		if r["node"] == car:
			rec = r
	check(not rec.is_empty() and String(rec["kind"]) == "Sedan", "VH_Sedan_01 uses the Sedan engine set")
	if not rec.is_empty():
		car.engine_pitch = car.data.pitch_idle
		var lo := d.engine_mix(rec)
		car.engine_pitch = car.data.pitch_max
		var hi := d.engine_mix(rec)
		check(float(lo["Idle"][1]) > 0.95 and float(lo["High"][1]) < 0.05, "idle RPM -> idle layer only")
		check(float(hi["High"][1]) > 0.7 and float(hi["Idle"][1]) < 0.05, "top RPM -> high layer")
		check(absf(float(hi["High"][0]) - 1.05) < 0.1 and float(lo["Idle"][0]) <= 1.05,
			"layer pitch follows rpm / layer rpm (idle %.2f, high %.2f)" % [lo["Idle"][0], hi["High"][0]])
	d.clear_history()
	car.crashed.emit(14.0, 20.0)
	car.door_changed.emit(&"Door_FL", true)
	await frames(1)
	check(d.played("SFX_VEH_Crash_Heavy"), "a 14 m/s crash plays SFX_VEH_Crash_Heavy")
	check(d.played("SFX_VEH_Door_Open"), "opening a door plays SFX_VEH_Door_Open")
	d.set_siren(car, true)
	await frames(1)
	check(car.get_node_or_null("UW_Siren") is AudioStreamPlayer3D, "set_siren() attaches the wail loop")
	car.queue_free()
	floor_body.queue_free()
	await frames(2)

func _mission_and_music() -> void:
	var mm := MissionManager.new()
	root.add_child(mm)
	await frames(2)
	d.clear_history()
	mm.mission_started.emit(null)
	mm.objective_completed.emit(0, null)
	await frames(1)
	check(d.music_state == "explore" and d.played("MUS_M01_Tension"), "mission start starts the explore score")
	check(d.played("UI_Objective_Complete"), "objective complete plays UI_Objective_Complete")
	d._combat_ping()
	check(d.music_state == "combat" and d.played("MUS_M01_Combat"), "combat switches to MUS_M01_Combat")
	mm.mission_completed.emit(null, 500)
	await frames(1)
	check(d.played("MUS_Stinger_MissionPassed") and d.music_state == "", "mission passed: stinger, score stops")
	var info := DamageInfo.new()
	info.killed = true
	d._on_hitmarker(info)
	check(d.played("UI_Killmarker"), "a kill hitmarker plays UI_Killmarker")
	d.start_ambience("NY_night")
	check(d.ambience_key == "NY_night" and d.played("AMB_NY_Street_Night"), "ambience bed NY_night")
	d.stop_ambience()
	mm.queue_free()
	await frames(1)

func _pool() -> void:
	var before := int(d.stats["stolen"])
	var voices := 0
	for i in 60:
		if d.play_at("SFX_IMP_Concrete", Vector3(i, 0, 0)) != null:
			voices += 1
	var files_present := d.pick_stream("SFX_IMP_Concrete") != null
	if files_present:
		check(int(d.stats["stolen"]) > before, "60 simultaneous one-shots steal the oldest voices (pool %d)" % AudioDirector.POOL_3D)
	else:
		check(voices == 0, "no stream -> no voice (graceful without rendered files)")
