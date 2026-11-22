extends SceneTree
func _initialize() -> void:
	for p in ["res://Assets/Environment/LA/SM_LA_Road_Straight/SM_LA_Road_Straight.glb",
			"res://Assets/Environment/LA/SM_LA_Bldg_GarageM01/SM_LA_Bldg_GarageM01.glb",
			"res://Assets/Weapons/WPN_Pistol_01/WPN_Pistol_01.glb"]:
		var ps := load(p) as PackedScene
		print("[GLB] ", p.get_file(), " packed=", ps != null)
		if ps == null:
			continue
		var i := ps.instantiate()
		var n := 0
		var names: Array[String] = []
		_collect(i, [0, names])
		print("[GLB]   children=", i.get_child_count(), " meshes=", names.size(), " first=", names.slice(0, 4))
		i.free()
	quit(0)

func _collect(n: Node, acc: Array) -> void:
	if n is MeshInstance3D:
		acc[0] += 1
		acc[1].append(String(n.name))
	for c in n.get_children():
		_collect(c, acc)
