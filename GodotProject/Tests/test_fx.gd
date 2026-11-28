extends SceneTree
## P6 (T-FX-01) - effects library + weapon integration.
##   * every Scenes/FX/FX_*.tscn is an FXEffect with GPU particle layers (amount > 0, process material)
##   * one-shot effects free themselves after `lifetime`; looping ones (smoke, fire, rain...) stay
##   * every catalogue FX entry resolves to a built scene
##   * a real pistol shot spawns the muzzle flash and the impact for the surface it hits:
##     wall -> FX_Impact_Concrete, car body -> FX_Impact_Metal, NPC hitbox -> FX_Blood
## Negative control: UW_FX_SABOTAGE=1 maps every surface to concrete -> the blood/metal checks fail.

var failures: PackedStringArray = []

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
	print("[GPTEST] == effects (P6 T-FX-01)")
	var dir := DirAccess.open("res://Scenes/FX")
	var ids: Array = []
	for f in dir.get_files():
		if f.ends_with(".tscn"):
			ids.append(f.get_basename())
	check(ids.size() >= 14, "%d effect scenes built (>= 14)" % ids.size())
	for id in ids:
		var fx := (load("res://Scenes/FX/%s.tscn" % id) as PackedScene).instantiate()
		var layers := fx.find_children("*", "GPUParticles3D", true, false)
		var ok := fx is FXEffect and not layers.is_empty()
		for l in layers:
			ok = ok and (l as GPUParticles3D).amount > 0 and (l as GPUParticles3D).process_material != null and (l as GPUParticles3D).draw_pass_1 != null
		check(ok, "%s: FXEffect with %d particle layer(s)" % [id, layers.size()])
		fx.free()
	# lifetime behaviour
	var holder := Node3D.new()
	root.add_child(holder)
	await frames(1)
	var shot := FXEffect.spawn("FX_Impact_Concrete", holder, Transform3D.IDENTITY)
	var loop := FXEffect.spawn("FX_Smoke", holder, Transform3D.IDENTITY)
	check(shot != null and loop != null, "FXEffect.spawn() instances effects")
	if shot == null or loop == null:
		quit(1)
		return
	await frames(int((shot.lifetime + 0.3) * 60.0))
	check(not is_instance_valid(shot), "one-shot impact frees itself after %.1f s" % 1.0)
	check(is_instance_valid(loop), "looping smoke keeps running")
	loop.queue_free()
	# catalogue -> scenes
	var path := ProjectSettings.globalize_path("res://").path_join("../Config/Content/catalog.json").simplify_path()
	var cat = JSON.parse_string(FileAccess.get_file_as_string(path))
	var missing := []
	for e in (cat as Dictionary).get("entries", []):
		if String(e.get("type", "")) == "fx" and String(e.get("status", "")) != "PLANNED":
			for m in e.get("members", [e.get("id")]):
				if not ResourceLoader.exists("res://Scenes/FX/%s.tscn" % m):
					missing.append(m)
	check(missing.is_empty(), "every built catalogue FX entry has its scene %s" % str(missing))
	await _weapon_impacts()
	if failures.is_empty():
		print("[GPTEST] RESULT: PASS")
		quit(0)
	else:
		print("[GPTEST] RESULT: FAIL (%d)" % failures.size())
		quit(1)

func _weapon_impacts() -> void:
	var sabotage := OS.is_debug_build() and OS.get_environment("UW_FX_SABOTAGE") == "1"
	var world := Node3D.new()
	root.add_child(world)
	# targets 6 m ahead (+Z): wall left, car right, NPC centre
	var wall := StaticBody3D.new()
	var wcs := CollisionShape3D.new()
	var wb := BoxShape3D.new()
	wb.size = Vector3(2, 3, 0.3)
	wcs.shape = wb
	wall.add_child(wcs)
	wall.position = Vector3(-3, 1.5, 6)
	world.add_child(wall)
	var car := (load("res://Scenes/Vehicles/VH_Sedan_01.tscn") as PackedScene).instantiate() as Vehicle
	car.control_override = true
	car.position = Vector3(3, 0, 6)
	world.add_child(car)
	var npc := (load("res://Scenes/NPC/PT_NPC_Gunman.tscn") as PackedScene).instantiate() as NPCController
	npc.position = Vector3(0, 0, 8)
	world.add_child(npc)
	var w := Weapon.new()
	w.data = (load("res://Data/Weapons/WPN_Pistol_01.tres") as WeaponData).duplicate()
	world.add_child(w)
	await frames(20)
	npc.global_position = Vector3(0, 0, 8)
	# stop the AI only: PROCESS_MODE_DISABLED would also REMOVE the hitboxes from physics
	npc.set_physics_process(false)
	npc.set_process(false)
	await frames(2)
	var cases := [["wall", Vector3(-3, 1.5, 6), "FX_Impact_Concrete"], ["car", Vector3(3, 0.8, 6), "FX_Impact_Metal"],
		["npc", Vector3(0, 1.2, 8), "FX_Blood"]]
	for c in cases:
		var origin := Vector3(0, 1.4, 0)
		var aim := ((c[1] as Vector3) - origin).normalized()
		w.cooldown = 0.0
		w.bloom = 0.0
		var r := w.trigger(true, true, origin, aim, {"aiming": true, "crouch": false, "moving": false})
		var got := String(w.last_fx.name) if w.last_fx != null else "none"
		if sabotage:
			got = "FX_Impact_Concrete"
		check(not r.is_empty() and got.begins_with(String(c[2])), "pistol shot at the %s spawns %s (got %s)" % [c[0], c[2], got])
		await frames(2)
	world.queue_free()
	await frames(2)
