extends SceneTree
## P2/P3 (T-PROP-01) - QUALITY_GATE Phase 8 for the content catalogue: every built
## environment/prop/armor entry rendered IN ENGINE (Forward Plus on lavapipe) under the shipped
## look preset (SunPreset + ENV_LA_*.tres), framed from its AABB, plus one dressed street-corner
## shot that uses the kit together (road, crosswalk, intersection, kerbs, props).
##
##   UW_CAPTURE_DIR=/abs/dir Tools/godot_phase8_capture.sh --renderer fwdplus --res 960x540 \
##       --script res://Tests/tools/capture_catalog.gd
## Optional: UW_CATALOG_PRESET=golden_hour|midday|night, UW_CATALOG_ONLY=ID,ID
## Writes <ID>.png per asset and street_corner.png. Look only - never performance (no GPU).

const SUN := preload("res://Scripts/game/sun_preset.gd")

var out_dir := "/tmp/uw_catalog_shots"

func _initialize() -> void:
	var d := OS.get_environment("UW_CAPTURE_DIR")
	if d != "":
		out_dir = d
	DirAccess.make_dir_recursive_absolute(out_dir)
	_run()

func frames(n: int) -> void:
	for i in n:
		await process_frame

func _entries() -> Array:
	var path := ProjectSettings.globalize_path("res://").path_join("../Config/Content/catalog.json").simplify_path()
	var cat = JSON.parse_string(FileAccess.get_file_as_string(path))
	var only := OS.get_environment("UW_CATALOG_ONLY").split(",", false)
	var out: Array = []
	for e in (cat as Dictionary).get("entries", []):
		if String(e.get("status", "")) == "PLANNED" or not e.has("asset"):
			continue
		if String(e.get("type", "")) not in ["environment", "prop", "armor"]:
			continue
		if not only.is_empty() and not only.has(String(e["id"])):
			continue
		out.append(e)
	return out

func _stage(preset: String) -> Node3D:
	var stage := Node3D.new()
	stage.name = "Stage"
	root.add_child(stage)
	stage.add_child(SUN.make_sun(preset))
	var we := WorldEnvironment.new()
	we.environment = (SUN.environment(preset) as Environment).duplicate()
	stage.add_child(we)
	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(400, 400)
	ground.mesh = pm
	var gm := StandardMaterial3D.new()
	gm.albedo_color = Color(0.36, 0.35, 0.33)
	gm.roughness = 0.95
	ground.material_override = gm
	ground.position.y = -0.002
	stage.add_child(ground)
	return stage

func _aabb(n: Node) -> AABB:
	var box := AABB()
	var first := true
	var stack: Array = [n]
	while not stack.is_empty():
		var c: Node = stack.pop_back()
		stack.append_array(c.get_children())
		if c is MeshInstance3D and not String(c.name).contains("_LOD") and not (c.get_parent() is CollisionObject3D):
			var b: AABB = (c as MeshInstance3D).global_transform * (c as MeshInstance3D).get_aabb()
			box = b if first else box.merge(b)
			first = false
	return box

func _run() -> void:
	var preset := OS.get_environment("UW_CATALOG_PRESET")
	if preset == "":
		preset = "golden_hour"
	var stage := _stage(preset)
	var cam := Camera3D.new()
	stage.add_child(cam)
	cam.make_current()
	for e in _entries():
		var ps := load("res://" + String(e["asset"])) as PackedScene
		if ps == null:
			print("[CATALOG_SHOT][FAIL] cannot load ", e["asset"])
			continue
		var inst := ps.instantiate() as Node3D
		stage.add_child(inst)
		await frames(2)
		var box := _aabb(inst)
		var c := box.get_center()
		var r := maxf(box.size.length() * 0.5, 0.05)
		cam.fov = 35.0
		cam.near = maxf(0.01, r * 0.02)
		var dist := r / tan(deg_to_rad(cam.fov * 0.5)) * 1.05
		# 3/4 front view (front = +Z in Godot, TD-004), slightly above
		var dir := Vector3(-0.55, 0.42, 0.72).normalized()
		cam.position = c + dir * dist
		cam.look_at(c, Vector3.UP)
		await frames(8)
		var img := root.get_viewport().get_texture().get_image()
		var p := out_dir.path_join("%s.png" % e["id"])
		img.save_png(p)
		print("[CATALOG_SHOT] wrote ", p, " aabb=", box.size)
		inst.queue_free()
		await frames(1)
	await _street_corner(stage, cam)
	quit(0)

func _place(stage: Node3D, id: String, pos: Vector3, yaw_deg := 0.0) -> void:
	var dir := "res://Assets/Environment/LA/%s/%s.glb" % [id, id]
	if not ResourceLoader.exists(dir):
		dir = "res://Assets/Props/%s/%s.glb" % [id, id]
	var ps := load(dir) as PackedScene
	if ps == null:
		print("[CATALOG_SHOT] skip ", id)
		return
	var n := ps.instantiate() as Node3D
	n.position = pos
	n.rotation_degrees.y = yaw_deg
	stage.add_child(n)

## A dressed LA corner made only of catalogue assets (layout follows M01's Calloway Ave kit:
## road tiles 10 x 14 m, kerb tiles 4 x 10 m, top of asphalt at 0.04 m, kerb top 0.16 m).
func _street_corner(stage: Node3D, cam: Camera3D) -> void:
	# road along Godot -Z (Blender +Y); intersection at the far end
	_place(stage, "SM_LA_Road_Straight", Vector3(0, 0, 14))
	_place(stage, "SM_LA_Road_Crosswalk", Vector3(0, 0, 0))
	_place(stage, "SM_LA_Road_Intersection", Vector3(0, 0, -14))
	for z in [14.0, 4.0, -6.0 + 10.0 - 10.0]:
		_place(stage, "SM_LA_Sidewalk_Curb", Vector3(7.0, 0, z))
		_place(stage, "SM_LA_Sidewalk_Curb", Vector3(-7.0, 0, z))
	var k := 0.16
	_place(stage, "SM_LA_TrafficLight", Vector3(6.0, k, -6.0), 90.0)
	_place(stage, "SM_LA_StreetSign", Vector3(5.6, k, -4.6), 0.0)
	_place(stage, "SM_LA_Hydrant", Vector3(5.6, k, 2.0), -90.0)
	_place(stage, "SM_LA_TrashCan", Vector3(6.2, k, 6.0))
	_place(stage, "SM_LA_BusStop", Vector3(7.6, k, 12.0), -90.0)
	_place(stage, "SM_LA_ParkingMeter", Vector3(5.5, k, 9.0), -90.0)
	_place(stage, "SM_LA_ParkingMeter", Vector3(5.5, k, 16.0), -90.0)
	_place(stage, "SM_LA_NewspaperBox", Vector3(6.4, k, 3.4), -90.0)
	_place(stage, "SM_LA_Streetlight", Vector3(-5.6, k, 8.0), 90.0)
	_place(stage, "SM_LA_PalmTree", Vector3(-6.5, k, 1.0))
	_place(stage, "SM_LA_PalmTree", Vector3(-6.8, k, 15.0))
	_place(stage, "SM_LA_PhoneBooth", Vector3(-6.0, k, -2.0), 90.0)
	_place(stage, "SM_LA_Dumpster", Vector3(-8.0, k, 11.0), 90.0)
	_place(stage, "SM_LA_Bush", Vector3(8.4, k, 4.5))
	_place(stage, "SM_LA_Fence_Chainlink", Vector3(-9.0, k, 4.5), 90.0)
	_place(stage, "SM_LA_Fence_Chainlink", Vector3(-9.0, k, 7.5), 90.0)
	_place(stage, "SM_LA_PowerPole", Vector3(-8.6, k, -6.0))
	_place(stage, "SM_LA_Billboard", Vector3(-12.0, 0, -12.0), 45.0)
	_place(stage, "SM_Prop_Barrel", Vector3(-8.2, k, 13.0))
	_place(stage, "SM_Prop_Pallet", Vector3(-8.0, k, 14.6), 10.0)
	await frames(4)
	cam.fov = 50.0
	cam.near = 0.05
	cam.position = Vector3(2.6, 1.7, 22.0)
	cam.look_at(Vector3(0.0, 1.6, 0.0), Vector3.UP)
	await frames(12)
	var p := out_dir.path_join("street_corner.png")
	root.get_viewport().get_texture().get_image().save_png(p)
	print("[CATALOG_SHOT] wrote ", p)
