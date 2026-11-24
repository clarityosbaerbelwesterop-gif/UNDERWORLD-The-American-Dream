extends SceneTree
## T-DECAL-01 - dresses M01 (Calloway Ave) with the decal library: generates
## Scenes/Levels/LA_CallowayAve_Decals.tscn (one Node3D of Decal instances), which the level instances.
## Placement is found, not hand-typed: rays down onto the built street classify road / sidewalk by
## the hit body's names, rays sideways from the kerb find the building walls. Seeded -> reproducible.
##   godot --headless --path GodotProject --script res://Scripts/tools/build_decals_calloway.gd
const LEVEL := "res://Scenes/Levels/LA_CallowayAve.tscn"
const OUT := "res://Scenes/Levels/LA_CallowayAve_Decals.tscn"
const DECALS := "res://Scenes/Decals/%s.tscn"
const STREETS_X := [-24.0, 24.0]        # the two north-south streets (build_level_calloway.gd)
const Z_RANGE := [-74.0, 74.0]

var space: PhysicsDirectSpaceState3D
var layer: Node3D
var rng := RandomNumberGenerator.new()
var counts := {}
var placed: Array[Vector3] = []

func _initialize() -> void:
	_run()

func _run() -> void:
	GradedWorld.suspended = true
	rng.seed = 1971
	var level := (load(LEVEL) as PackedScene).instantiate() as Node3D
	var old := level.get_node_or_null("Decals")
	if old != null:
		old.free()                                   # place against the bare street
	root.add_child(level)
	for i in 3:
		await physics_frame
	space = level.get_world_3d().direct_space_state
	layer = Node3D.new()
	layer.name = "LA_CallowayAve_Decals"
	for sx in STREETS_X:
		_street(sx)
	print("[DECALS] placed ", counts)
	for c in layer.get_children():
		_own(c, layer)
	var ps := PackedScene.new()
	var err := ps.pack(layer)
	err = err if err != OK else ResourceSaver.save(ps, OUT)
	print("[DECALS] saved %s (%d decals) err=%d" % [OUT, layer.get_child_count(), err])
	layer.free()
	quit(0 if err == OK else 1)

func _own(n: Node, owner_node: Node) -> void:
	n.owner = owner_node

## What is under (x, z): "road", "sidewalk" or "" (plus the hit point).
func _ground(x: float, z: float) -> Array:
	var q := PhysicsRayQueryParameters3D.create(Vector3(x, 12.0, z), Vector3(x, -2.0, z))
	var hit := space.intersect_ray(q)
	if hit.is_empty():
		return ["", Vector3.ZERO]
	var names := ""
	var n := hit.collider as Node
	for i in 4:
		if n == null:
			break
		names += String(n.name).to_lower() + "|"
		n = n.get_parent()
	var kind := ""
	if names.contains("road") or names.contains("intersection") or names.contains("crosswalk"):
		kind = "road"
	elif names.contains("sidewalk") or names.contains("curb") or names.contains("kerb"):
		kind = "sidewalk"
	return [kind, hit.position]

func _far_enough(p: Vector3, d: float) -> bool:
	for q in placed:
		if q.distance_to(p) < d:
			return false
	return true

func _put(id: String, pos: Vector3, yaw: float, normal := Vector3.UP, min_gap := 1.5) -> bool:
	if not _far_enough(pos, min_gap):
		return false
	var d := (load(DECALS % id) as PackedScene).instantiate() as Decal
	d.name = "%s_%03d" % [id, int(counts.get(id, 0))]
	# local -Y projects into the surface: Y = surface normal, X/Z span the surface
	var up := normal.normalized()
	var side := Vector3.UP.cross(up) if absf(up.dot(Vector3.UP)) < 0.9 else Vector3.RIGHT
	var b := Basis(side.normalized(), up, side.normalized().cross(up))
	if absf(up.dot(Vector3.UP)) > 0.9:
		b = Basis(Vector3.UP, yaw)
	d.transform = Transform3D(b, pos + up * 0.02)
	layer.add_child(d)
	counts[id] = int(counts.get(id, 0)) + 1
	placed.append(pos)
	return true

func _street(cx: float) -> void:
	# manholes in the lanes, drains in the gutters, every ~24 m
	var z: float = Z_RANGE[0] + 6.0
	while z < Z_RANGE[1]:
		var g := _ground(cx + 2.4 * (1.0 if int(z) % 2 == 0 else -1.0), z)
		if g[0] == "road":
			_put("DC_LA_Manhole_01", g[1], rng.randf() * TAU, Vector3.UP, 3.0)
		for side in [-1.0, 1.0]:
			var gx: float = cx + side * 4.75
			var gd := _ground(gx, z + 9.0)
			if gd[0] == "road":
				_put("DC_LA_Drain_01", gd[1], PI / 2.0, Vector3.UP, 3.0)
		z += 24.0
	# scattered wear on the road
	for i in 26:
		var p := _ground(cx + rng.randf_range(-4.2, 4.2), rng.randf_range(Z_RANGE[0], Z_RANGE[1]))
		if p[0] != "road":
			continue
		var pick := rng.randf()
		var id := "DC_LA_OilStain_01" if pick < 0.3 else ("DC_LA_OilStain_02" if pick < 0.5 else ("DC_LA_Crack_02" if pick < 0.8 else "DC_LA_Crack_01"))
		_put(id, p[1], rng.randf() * TAU, Vector3.UP, 2.5)
	# skid marks near the ends of the block (where cars brake for the intersections)
	for zz in [Z_RANGE[0] + 8.0, Z_RANGE[1] - 8.0]:
		var t := _ground(cx + rng.randf_range(-2.5, 2.5), zz)
		if t[0] == "road":
			_put("DC_LA_TireMarks_01", t[1], PI / 2.0 + rng.randf_range(-0.2, 0.2), Vector3.UP, 4.0)
	# sidewalks: cracks + litter
	for side in [-1.0, 1.0]:
		for i in 18:
			var sp := _ground(cx + float(side) * rng.randf_range(5.6, 8.6), rng.randf_range(Z_RANGE[0], Z_RANGE[1]))
			if sp[0] != "sidewalk":
				continue
			_put("DC_LA_Trash_01" if rng.randf() < 0.35 else "DC_LA_Crack_01", sp[1], rng.randf() * TAU, Vector3.UP, 2.5)
	# walls: graffiti at eye height, grime higher up, found by rays from the kerb outwards
	for side in [-1.0, 1.0]:
		var zw: float = Z_RANGE[0] + 4.0
		while zw < Z_RANGE[1]:
			var from := Vector3(cx + float(side) * 7.0, 1.7, zw)
			var q := PhysicsRayQueryParameters3D.create(from, from + Vector3(float(side) * 30.0, 0, 0))
			var hit := space.intersect_ray(q)
			if OS.get_environment("UW_DECAL_DEBUG") == "1":
				print("[DECALS][ray] side %d z %.0f -> %s %s" % [side, zw, "miss" if hit.is_empty() else String((hit.collider as Node).name), "" if hit.is_empty() else str(hit.position)])
			if not hit.is_empty() and absf((hit.normal as Vector3).y) < 0.2:
				var roll := rng.randf()
				if roll < 0.45:
					var tag := "DC_LA_Graffiti_01" if rng.randf() < 0.55 else "DC_LA_Graffiti_02"
					_put(tag, hit.position + Vector3(0, rng.randf_range(-0.3, 0.2), 0), 0.0, hit.normal, 4.0)
				elif roll < 0.8:
					_put("DC_LA_Grime_01", hit.position + Vector3(0, 1.4, 0), 0.0, hit.normal, 4.0)
			zw += rng.randf_range(4.0, 7.0)
