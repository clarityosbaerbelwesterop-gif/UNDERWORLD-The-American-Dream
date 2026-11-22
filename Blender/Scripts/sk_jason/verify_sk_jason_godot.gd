## SK_Jason delivery check inside Godot (headless), Bot 2 (T-ART-01/02). Mirrors REQ-GP01-JASON §6.
## godot --headless --path <tmp project> --script res://verify_sk_jason_godot.gd -- <expect.json>
extends SceneTree

var fails := 0
var _done := false

func check(c: bool, msg: String) -> void:
	print(("[JASON-GODOT][PASS] " if c else "[JASON-GODOT][FAIL] ") + msg)
	if not c:
		fails += 1

func collect(n: Node, cls: String, out: Array) -> void:
	if n.is_class(cls):
		out.append(n)
	for c in n.get_children():
		collect(c, cls, out)

func find(n: Node, name: String) -> Node:
	if String(n.name) == name:
		return n
	for c in n.get_children():
		var r := find(c, name)
		if r:
			return r
	return null

func godot_name(n: String) -> String:
	var low := n.to_lower()
	for suf in ["_loop", "-loop", "_cycle", "-cycle"]:
		if low.ends_with(suf):
			return n.substr(0, n.length() - suf.length())
	return n

func mesh_bounds(inst: Node) -> AABB:
	var ms: Array = []
	collect(inst, "MeshInstance3D", ms)
	var box := AABB()
	var first := true
	for m in ms:
		var b: AABB = m.global_transform * m.get_aabb()
		box = b if first else box.merge(b)
		first = false
	return box

func _process(_d: float) -> bool:
	if _done:
		return true
	_done = true
	var exp: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]))
	var ps: PackedScene = load(exp["path"])
	check(ps != null, "%s loads as PackedScene" % exp["path"])
	if ps == null:
		quit(1)
		return true
	var inst := ps.instantiate() as Node3D
	root.add_child(inst)
	var sks: Array = []
	collect(inst, "Skeleton3D", sks)
	check(sks.size() == 1, "one Skeleton3D (got %d)" % sks.size())
	var sk: Skeleton3D = sks[0]
	# --- bones
	var names := PackedStringArray()
	for i in sk.get_bone_count():
		names.append(sk.get_bone_name(i))
	var missing := []
	for b in exp["bones"]:
		if sk.find_bone(b) < 0:
			missing.append(b)
	check(missing.is_empty(), "skeleton has all %d expected bones (missing %s), total %d" % [exp["bones"].size(), missing, sk.get_bone_count()])
	check(sk.get_bone_parent(sk.find_bone("Hips")) == sk.find_bone("Root") and sk.get_bone_parent(sk.find_bone("Root")) == -1, "Root is the skeleton root and parent of Hips")
	var prof := SkeletonProfileHumanoid.new()
	var unmapped := []
	for i in prof.bone_size:
		var bn := String(prof.get_bone_name(i))
		if sk.find_bone(bn) < 0 and not bn in ["LeftEye", "RightEye", "Jaw"]:
			unmapped.append(bn)
	check(unmapped.is_empty(), "all SkeletonProfileHumanoid bones present except optional eyes/jaw (missing %s)" % [unmapped])
	var skinned: Array = sk.get_children().filter(func(c): return c is MeshInstance3D and c.skin != null)
	check(skinned.size() >= 1, "skinned MeshInstance3D under Skeleton3D (%d)" % skinned.size())
	# --- rest pose: size, ground, front
	var box := mesh_bounds(inst)
	check(absf(box.size.y - 1.82) <= 0.02, "height %.3f m (1.82 +- 0.02)" % box.size.y)
	check(absf(box.position.y) < 0.005, "min y %.4f (feet on ground, origin at feet)" % box.position.y)
	var toe := (sk.global_transform * sk.get_bone_global_rest(sk.find_bone("LeftToes"))).origin
	var lh := (sk.global_transform * sk.get_bone_global_rest(sk.find_bone("LeftHand"))).origin
	check(toe.z > 0.05 and lh.x > 0.3, "faces +Z (LeftToes z=%.3f > 0, LeftHand x=%.3f > 0) TD-004" % [toe.z, lh.x])
	# --- socket
	var sock := find(inst, "SOCKET_RightHand_Weapon") as Node3D
	var ba: BoneAttachment3D = null
	var p := sock.get_parent() if sock else null
	while p and not (p is BoneAttachment3D):
		p = p.get_parent()
	ba = p as BoneAttachment3D
	check(sock != null and ba != null and ba.bone_name == "RightHand", "SOCKET_RightHand_Weapon under BoneAttachment3D(RightHand) (%s)" % [ba.bone_name if ba else "none"])
	# --- animations
	var aps: Array = []
	collect(inst, "AnimationPlayer", aps)
	check(aps.size() == 1, "one AnimationPlayer")
	var ap: AnimationPlayer = aps[0]
	var want: Dictionary = exp["animations"]
	var seen := {}
	for an in want:
		var gname := godot_name(an)
		seen[gname] = true
		if gname != an:
			print("[JASON-GODOT][WARN] %s is imported by Godot as %s (loop/cycle name hint stripped, loop forced); consumers asking for %s will not find it" % [an, gname, an])
		var a := ap.get_animation(gname) if ap.has_animation(gname) else null
		var len_ok := a != null and absf(a.length - float(want[an][0])) < 0.005
		var loop_ok := a != null and ((a.loop_mode != Animation.LOOP_NONE) == bool(want[an][1]))
		check(len_ok and loop_ok, "%s length %.4f s loop %s (got %s, loop_mode %s)" % [an, want[an][0], want[an][1], a.length if a else "missing", a.loop_mode if a else "-"])
		if a:
			var rt := a.find_track(NodePath("%s:Root" % inst.get_path_to(sk)), Animation.TYPE_POSITION_3D)
			var moving := false
			if rt >= 0:
				for k in a.track_get_key_count(rt):
					if (a.track_get_key_value(rt, k) as Vector3).length() > 1e-4:
						moving = true
			check(not moving, "%s: Root not translated (in place)" % an)
	var extra := []
	for an in ap.get_animation_list():
		if not seen.has(String(an)):
			extra.append(an)
	check(extra.is_empty(), "no unexpected animations (%s)" % [extra])
	# --- posed checks: aim socket orientation, in-place hips, feet on ground during Walk
	# socket relative to its bone, taken in the current (rest) pose; BoneAttachment3D updates deferred,
	# so the posed socket is rebuilt from the bone's global pose after seeking
	var rh := sk.find_bone("RightHand")
	var sock_off := (sk.global_transform * sk.get_bone_global_pose(rh)).affine_inverse() * sock.global_transform
	ap.play("A_Jason_Aim_Pistol_Idle")
	ap.seek(0.0, true)
	ap.advance(0.0)
	var sock_g := sk.global_transform * sk.get_bone_global_pose(rh) * sock_off
	var g := sock_g.basis.orthonormalized()
	check(g.y.dot(Vector3.UP) > 0.95 and g.z.dot(Vector3.BACK) > 0.95,
		"aim pose: socket +Y up (%.3f) and +Z barrel forward along +Z (%.3f)" % [g.y.dot(Vector3.UP), g.z.dot(Vector3.BACK)])
	print("[JASON-GODOT] aim socket at %s (rest %s)" % [sock_g.origin, sock.global_position])
	# max height of the lower ankle: walks always have a foot down; run/sprint have a flight phase
	var low_max := {"A_Jason_Walk": 0.2, "A_Jason_Aim_Pistol_Walk_F": 0.2, "A_Jason_Crouch_Walk": 0.2, "A_Jason_Run": 0.3, "A_Jason_Sprint": 0.3}
	for an in low_max:
		ap.play(an)
		var a := ap.get_animation(an)
		var hmax := 0.0
		var lowest := INF
		var highest_low := -INF
		var n := 24
		for i in n:
			ap.seek(a.length * i / n, true)
			ap.advance(0.0)
			var hips := (sk.global_transform * sk.get_bone_global_pose(sk.find_bone("Hips"))).origin
			hmax = maxf(hmax, Vector2(hips.x, hips.z).length())
			var lf := (sk.global_transform * sk.get_bone_global_pose(sk.find_bone("LeftFoot"))).origin.y
			var rf := (sk.global_transform * sk.get_bone_global_pose(sk.find_bone("RightFoot"))).origin.y
			lowest = minf(lowest, minf(lf, rf))
			highest_low = maxf(highest_low, minf(lf, rf))
		check(hmax < 0.06, "%s: hips stay in place (max horizontal offset %.3f m)" % [an, hmax])
		check(highest_low < low_max[an] and lowest > 0.0, "%s: lower ankle y in [%.3f, %.3f] (max %.2f)" % [an, lowest, highest_low, low_max[an]])
	root.remove_child(inst)
	inst.free()
	print("[JASON-GODOT] RESULT: %s (%d failures)" % ["PASS" if fails == 0 else "FAIL", fails])
	quit(0 if fails == 0 else 1)
	return true
