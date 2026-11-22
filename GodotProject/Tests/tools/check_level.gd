extends SceneTree

func _initialize() -> void:
	var ps := load("res://Scenes/Levels/LA_CallowayAve.tscn") as PackedScene
	var inst := ps.instantiate()
	root.add_child(inst)
	await process_frame
	var acc := {"meshes": 0, "verts": 0}
	_count(inst, acc)
	print("[CHK] meshes=", acc["meshes"], " verts=", acc["verts"])
	var streets := inst.get_node_or_null("Streets")
	print("[CHK] Streets children=", streets.get_child_count() if streets else -1)
	if streets != null and streets.get_child_count() > 0:
		var c: Node = streets.get_child(0)
		print("[CHK] first child=", c.name, " class=", c.get_class(), " children=", c.get_child_count())
		for g in c.get_children():
			print("[CHK]   ", g.name, " ", g.get_class(), " mesh=", (g.mesh != null) if g is MeshInstance3D else "n/a")
	quit(0)

func _count(n: Node, acc: Dictionary) -> void:
	if n is MeshInstance3D and n.mesh != null:
		acc["meshes"] += 1
		if n.mesh is ArrayMesh:
			for s in (n.mesh as ArrayMesh).get_surface_count():
				acc["verts"] += (n.mesh as ArrayMesh).surface_get_array_len(s)
	for c in n.get_children():
		_count(c, acc)
