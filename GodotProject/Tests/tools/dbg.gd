extends SceneTree
func _initialize() -> void:
	var n := Node3D.new()
	n.name = "Root"
	for i in 3:
		var c := Node3D.new()
		c.name = "Child%d" % i
		n.add_child(c)
		c.owner = n
		var g := Node3D.new()
		g.name = "Grand%d" % i
		c.add_child(g)
		g.owner = n
	var ps := PackedScene.new()
	print("[DBG] pack=", ps.pack(n))
	ResourceSaver.save(ps, "user://dbg.tscn")
	print(FileAccess.get_file_as_string("user://dbg.tscn"))
	quit(0)
