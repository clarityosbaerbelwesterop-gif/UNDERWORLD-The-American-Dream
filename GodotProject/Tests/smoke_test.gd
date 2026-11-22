# UNDERWORLD - Godot headless pipeline smoke test.
# Run: godot --headless --path GodotProject --script res://Tests/smoke_test.gd
# Loads Main.tscn and checks that the Blender-exported test asset imported
# with meshes, materials, collision (from the "-colonly" hint), correct scale
# and Y-up orientation. Exits 0 on PASS, 1 on FAIL.
extends SceneTree

var failures: Array[String] = []

func check(cond: bool, msg: String) -> void:
	if cond:
		print("[SMOKE][PASS] ", msg)
	else:
		print("[SMOKE][FAIL] ", msg)
		failures.append(msg)

func _collect(n: Node, out: Array) -> void:
	out.append(n)
	for c in n.get_children():
		_collect(c, out)

var _ran := false

# Run on the first frame so the scene is inside the tree (global transforms valid).
func _process(_delta: float) -> bool:
	if not _ran:
		_ran = true
		_run()
	return false

func _run() -> void:
	var packed: PackedScene = load("res://Scenes/Main.tscn")
	check(packed != null, "Main.tscn loads")
	if packed == null:
		quit(1)
		return
	var main := packed.instantiate()
	root.add_child(main)
	check(main.get_node_or_null("Camera3D") is Camera3D, "Camera3D present")
	check(main.get_node_or_null("Sun") is DirectionalLight3D, "DirectionalLight3D present")
	check(main.get_node_or_null("Ground") is StaticBody3D, "Ground StaticBody3D present")
	var asset := main.get_node_or_null("PipelineTest")
	check(asset != null, "PipelineTest asset instanced")
	if asset == null:
		quit(1)
		return
	var nodes: Array = []
	_collect(asset, nodes)
	var meshes: Array = nodes.filter(func(n): return n is MeshInstance3D)
	var bodies: Array = nodes.filter(func(n): return n is StaticBody3D)
	var shapes: Array = nodes.filter(func(n): return n is CollisionShape3D)
	check(meshes.size() == 2, "2 visible meshes imported (body + front marker), got %d" % meshes.size())
	check(bodies.size() >= 1 and shapes.size() >= 1, "collision generated from -colonly hint (bodies=%d shapes=%d)" % [bodies.size(), shapes.size()])
	var body: MeshInstance3D = null
	for m in meshes:
		if String(m.name).contains("Body"):
			body = m
	check(body != null, "Body mesh found by name")
	if body != null:
		var aabb: AABB = body.global_transform * body.get_aabb()
		print("[SMOKE] body AABB ", aabb)
		check(aabb.size.distance_to(Vector3.ONE) < 0.02, "body is 1x1x1 m")
		check(absf(aabb.position.y) < 0.02, "body rests on ground (Y-up, min y = 0)")
		var mat := body.get_active_material(0)
		check(mat != null, "body has material")
	var front: MeshInstance3D = null
	for m in meshes:
		if String(m.name).contains("FrontMarker"):
			front = m
	if front != null:
		var c := (front.global_transform * front.get_aabb()).get_center()
		check(c.z > 0.5, "front marker on +Z (Blender -Y -> Godot +Z), center=%s" % c)
	if failures.is_empty():
		print("[SMOKE] RESULT: PASS")
		quit(0)
	else:
		print("[SMOKE] RESULT: FAIL (%d)" % failures.size())
		quit(1)
