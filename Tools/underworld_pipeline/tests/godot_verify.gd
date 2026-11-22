## T-PIPE-01 test helper: verifies Tools/underworld_pipeline exports inside Godot (headless).
## godot --headless --path <tmp project> --script res://godot_verify.gd -- <expect.json>
## Expectations per asset: nodes {name: class}, lod_ranges {name: [b, e]}, collision {body: shape class},
## animations {name: length_s}, bones [...], aabb_min_y, animate [anim, bone, time].
extends SceneTree

var fails := 0

func check(c: bool, msg: String) -> void:
	print(("[GODOT][PASS] " if c else "[GODOT][FAIL] ") + msg)
	if not c:
		fails += 1

func find(n: Node, name: String) -> Node:
	if String(n.name) == name:
		return n
	for c in n.get_children():
		var r := find(c, name)
		if r:
			return r
	return null

func collect(n: Node, cls: String, out: Array) -> void:
	if n.is_class(cls):
		out.append(n)
	for c in n.get_children():
		collect(c, cls, out)

var _done := false

func _process(_d: float) -> bool:
	if _done:
		return true
	_done = true
	var args := OS.get_cmdline_user_args()
	var exp: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	for a in exp["assets"]:
		var tag: String = a["path"].get_file()
		var ps: PackedScene = load(a["path"])
		check(ps != null, "%s loads as PackedScene" % tag)
		if ps == null:
			continue
		var inst := ps.instantiate()
		root.add_child(inst)
		for nm in a.get("nodes", {}):
			var n := find(inst, nm)
			check(n != null and n.is_class(a["nodes"][nm]), "%s: node %s is %s (got %s)" % [tag, nm, a["nodes"][nm], n.get_class() if n else "missing"])
		for nm in a.get("lod_ranges", {}):
			var g := find(inst, nm) as GeometryInstance3D
			var r: Array = a["lod_ranges"][nm]
			check(g != null and is_equal_approx(g.visibility_range_begin, r[0]) and is_equal_approx(g.visibility_range_end, r[1]),
				"%s: %s visibility range %s (got %s)" % [tag, nm, r, [g.visibility_range_begin, g.visibility_range_end] if g else "missing"])
		for nm in a.get("collision", {}):
			var b := find(inst, nm)
			var shapes: Array = []
			if b:
				collect(b, "CollisionShape3D", shapes)
			check(b is StaticBody3D and shapes.size() >= 1 and shapes[0].shape.is_class(a["collision"][nm]),
				"%s: %s is StaticBody3D with %s" % [tag, nm, a["collision"][nm]])
		if a.has("aabb_min_y"):
			var meshes: Array = []
			collect(inst, "MeshInstance3D", meshes)
			var lo := INF
			for m in meshes:
				lo = minf(lo, (m.global_transform * m.get_aabb()).position.y)
			check(absf(lo - a["aabb_min_y"]) < 0.02, "%s: lowest mesh point y=%.3f (expected %.3f, Y-up, origin at bottom)" % [tag, lo, a["aabb_min_y"]])
		if a.has("animations"):
			var aps: Array = []
			collect(inst, "AnimationPlayer", aps)
			check(aps.size() == 1, "%s: one AnimationPlayer" % tag)
			if aps.size() == 1:
				var ap: AnimationPlayer = aps[0]
				for an in a["animations"]:
					var anim := ap.get_animation(an) if ap.has_animation(an) else null
					check(anim != null and absf(anim.length - float(a["animations"][an])) < 0.01,
						"%s: animation %s length %.3fs (got %s)" % [tag, an, a["animations"][an], anim.length if anim else "missing"])
				if a.has("animate"):
					var sks: Array = []
					collect(inst, "Skeleton3D", sks)
					var sk: Skeleton3D = sks[0]
					var bi := sk.find_bone(a["animate"][1])
					ap.play(a["animate"][0])
					ap.seek(0.0, true)
					var q0 := sk.get_bone_pose_rotation(bi)
					ap.seek(float(a["animate"][2]), true)
					var q1 := sk.get_bone_pose_rotation(bi)
					check(q0.angle_to(q1) > 0.1, "%s: %s rotates bone %s (%.2f rad at t=%ss)" % [tag, a["animate"][0], a["animate"][1], q0.angle_to(q1), a["animate"][2]])
		if a.has("front_bone"):
			var sks: Array = []
			collect(inst, "Skeleton3D", sks)
			var sk: Skeleton3D = sks[0]
			var toe := (sk.global_transform * sk.get_bone_global_rest(sk.find_bone(a["front_bone"]))).origin
			var lh := (sk.global_transform * sk.get_bone_global_rest(sk.find_bone(a["left_bone"]))).origin
			check(toe.z > 0.05, "%s: %s at z=%.3f > 0 -> character faces Godot +Z (TD-004)" % [tag, a["front_bone"], toe.z])
			check(lh.x > 0.1, "%s: %s at x=%.3f > 0 (character's left = +X when facing +Z)" % [tag, a["left_bone"], lh.x])
			check(absf(sk.get_bone_count() - a["bone_count"]) < 1, "%s: %d bones" % [tag, sk.get_bone_count()])
		if a.has("bones"):
			var sks: Array = []
			collect(inst, "Skeleton3D", sks)
			check(sks.size() == 1, "%s: one Skeleton3D" % tag)
			if sks.size() == 1:
				var names: Array = []
				for i in sks[0].get_bone_count():
					names.append(sks[0].get_bone_name(i))
				names.sort()
				var want: Array = a["bones"].duplicate()
				want.sort()
				check(names == want, "%s: bones %s" % [tag, names])
				var skinned: Array = sks[0].get_children().filter(func(c): return c is MeshInstance3D and c.skin != null)
				check(skinned.size() >= 1, "%s: skinned MeshInstance3D under Skeleton3D" % tag)
		root.remove_child(inst)
		inst.free()
	print("[GODOT] RESULT: %s (%d failures)" % ["PASS" if fails == 0 else "FAIL", fails])
	quit(0 if fails == 0 else 1)
	return true
