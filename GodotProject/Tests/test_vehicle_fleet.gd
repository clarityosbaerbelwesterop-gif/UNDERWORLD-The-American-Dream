extends SceneTree
## P5 (T-VEH-01) - every catalogue car built from a body profile assembles in the REAL Vehicle
## script (vehicle.gd) with the sedan's tuning: wheels, convex UCX collision, hinged doors,
## seat/exit sockets, asset wheel radius == data. Then it parks on the floor and drives forward.
## Negative control: UW_VEH_SABOTAGE=radius feeds a wrong wheel radius -> the contract check fails.

const SEDAN := "res://Scenes/Vehicles/VH_Sedan_01.tscn"
const HZ := 60.0
var failures: PackedStringArray = []

func check(cond: bool, msg: String) -> void:
	print("[GPTEST][PASS] " if cond else "[GPTEST][FAIL] ", msg)
	if not cond:
		failures.append(msg)

func _initialize() -> void:
	_run()

func seconds(s: float) -> void:
	for i in int(s * HZ):
		await physics_frame

func _fleet() -> Array:
	var path := ProjectSettings.globalize_path("res://").path_join("../Config/Content/catalog.json").simplify_path()
	var cat = JSON.parse_string(FileAccess.get_file_as_string(path))
	var out: Array = []
	for e in (cat as Dictionary).get("entries", []):
		if String(e.get("type", "")) == "vehicle" and String(e.get("status", "")) != "PLANNED" \
				and String(e.get("generator", "")).begins_with("build-vehicles") and e.has("asset"):
			out.append(e)
	return out

func _wheel_radius(model: PackedScene) -> float:
	var inst := model.instantiate()
	var r := 0.0
	var stack: Array = [inst]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n.has_meta("extras") and (n.get_meta("extras") as Dictionary).has("uw_wheel_radius_m"):
			r = float(n.get_meta("extras")["uw_wheel_radius_m"])
			break
		stack.append_array(n.get_children())
	inst.free()
	return r

func _run() -> void:
	print("[GPTEST] == vehicle fleet (T-VEH-01)")
	var floor_body := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(400, 1, 400)
	cs.shape = box
	cs.position.y = -0.5
	floor_body.add_child(cs)
	floor_body.collision_layer = 1
	root.add_child(floor_body)
	var fleet := _fleet()
	check(fleet.size() >= 5, "catalogue lists %d profile-built cars (>= 5)" % fleet.size())
	var sabotage := OS.is_debug_build() and OS.get_environment("UW_VEH_SABOTAGE") == "radius"
	var x := 0.0
	for e in fleet:
		var id := String(e["id"])
		var model := load("res://" + String(e["asset"])) as PackedScene
		check(model != null, "%s loads" % id)
		if model == null:
			continue
		var car := (load(SEDAN) as PackedScene).instantiate() as Vehicle
		var data := car.data.duplicate() as VehicleData
		data.id = id
		data.model_scene = model
		data.wheel_radius = _wheel_radius(model) + (0.05 if sabotage else 0.0)
		car.data = data
		car.control_override = true
		car.position = Vector3(x, 0.0, 0.0)
		x += 8.0
		root.add_child(car)
		await physics_frame
		var errs := Array(car.assembly_errors).filter(func(m): return not String(m).begins_with("door node Door_R"))
		check(errs.is_empty(), "%s assembles in vehicle.gd (errors: %s)" % [id, str(errs)])
		check(car.wheels.size() == 4 and car.sockets.has(&"SOCKET_Seat_Driver") and car.sockets.has(&"SOCKET_Exit_Left"),
			"%s: 4 wheels + seat/exit sockets" % id)
		check(car.doors.has(&"Door_FL") and car.doors.has(&"Door_FR"), "%s: front doors hinged (%d doors)" % [id, car.doors.size()])
		# T-VEH-02: an interior under see-through glass (the seated driver / passenger are visible)
		var interior := false
		var glass_ok := 0
		var glass_all := 0
		for c in car.find_children("*", "MeshInstance3D", true, false):
			var mi := c as MeshInstance3D
			if String(mi.name).begins_with("Interior") and mi.mesh != null and mi.mesh.get_surface_count() >= 2:
				interior = true
			if mi.mesh == null:
				continue
			for si in mi.mesh.get_surface_count():
				var m := mi.get_active_material(si) as BaseMaterial3D
				if m != null and m.resource_name.ends_with("_Glass"):
					glass_all += 1
					if m.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED and m.albedo_color.a < 0.6:
						glass_ok += 1
		check(interior, "%s: Interior mesh (seats, dash, wheel) present" % id)
		check(glass_all > 0 and glass_ok == glass_all, "%s: glass is see-through (%d/%d surfaces alpha-blended)" % [id, glass_ok, glass_all])
		await seconds(2.0)
		check(absf(car.global_position.y) < 0.03, "%s parks on the floor (body y %.3f m)" % [id, car.global_position.y])
		var z0 := car.global_position.z
		car.set_controls(1.0, 0.0, 0.0)
		await seconds(2.0)
		car.set_controls(0.0, 1.0, 0.0)
		check(car.forward_speed > 4.0 and car.global_position.z - z0 > 4.0,
			"%s drives forward (%.1f m/s, %.1f m)" % [id, car.forward_speed, car.global_position.z - z0])
		car.queue_free()
		await physics_frame
	if failures.is_empty():
		print("[GPTEST] RESULT: PASS")
		quit(0)
	else:
		print("[GPTEST] RESULT: FAIL (%d)" % failures.size())
		quit(1)
