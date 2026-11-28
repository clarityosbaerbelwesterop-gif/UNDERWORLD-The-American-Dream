## WPN_Pistol_01 delivery check inside Godot (headless), Bot 2 (T-ART-05 / REQ-GP02-PISTOL §4).
## godot --headless --path <tmp copy of GodotProject> --script res://verify_wpn_pistol_01_godot.gd
extends SceneTree

const GLB := "res://Assets/Weapons/WPN_Pistol_01/WPN_Pistol_01.glb"
var fails := 0
var _done := false

func check(c: bool, msg: String) -> void:
	print(("[PISTOL-GODOT][PASS] " if c else "[PISTOL-GODOT][FAIL] ") + msg)
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

func _process(_d: float) -> bool:
	if _done:
		return true
	_done = true
	var ps: PackedScene = load(GLB)
	check(ps != null, "WPN_Pistol_01.glb loads as PackedScene")
	if ps == null:
		quit(1)
		return true
	var inst := ps.instantiate() as Node3D
	root.add_child(inst)
	for nm in ["Frame", "Slide", "Magazine"]:
		check(find(inst, nm) is MeshInstance3D, "%s is a MeshInstance3D" % nm)
	for nm in ["SOCKET_Muzzle", "SOCKET_Eject", "SOCKET_Grip"]:
		check(find(inst, nm) is Node3D, "%s present" % nm)
	var mz := find(inst, "SOCKET_Muzzle") as Node3D
	var ej := find(inst, "SOCKET_Eject") as Node3D
	var gp := find(inst, "SOCKET_Grip") as Node3D
	var m := mz.global_transform
	check(m.origin.z >= 0.16 and m.origin.z <= 0.20 and absf(m.origin.x) < 0.002, "muzzle %.3f m in front of the origin on +Z (REQ 0.16-0.2), at %s" % [m.origin.z, m.origin])
	check(m.basis.z.normalized().dot(Vector3.BACK) > 0.999 and m.basis.y.normalized().dot(Vector3.UP) > 0.999, "SOCKET_Muzzle +Z out of the barrel, +Y up")
	var e := ej.global_transform
	check(e.origin.x < 0.0 and e.basis.x.normalized().dot(Vector3.LEFT) > 0.999 and e.basis.y.normalized().dot(Vector3.UP) > 0.999,
		"SOCKET_Eject at the right-side port (x=%.3f), its local +X points out of the port (world -X), +Y up" % e.origin.x)
	check(gp.global_transform.origin.length() < 1e-4 and gp.global_transform.basis.is_equal_approx(Basis()), "SOCKET_Grip = origin, identity")
	# size
	var ms: Array = []
	collect(inst, "MeshInstance3D", ms)
	var box := AABB()
	var first := true
	for mi in ms:
		if String(mi.name).contains("_LOD"):
			continue
		var b: AABB = mi.global_transform * mi.get_aabb()
		box = b if first else box.merge(b)
		first = false
	check(box.size.z > 0.18 and box.size.z < 0.22 and box.size.y > 0.12 and box.size.y < 0.15 and box.size.x < 0.035,
		"size %.3f x %.3f x %.3f m (w x h x l; REQ ~0.03 x 0.13 x 0.19)" % [box.size.x, box.size.y, box.size.z])
	# LODs + collision from uw_post_import / uwp
	var lod1 := find(inst, "Slide_LOD1") as GeometryInstance3D
	var s0 := find(inst, "Slide") as GeometryInstance3D
	check(lod1 != null and s0.visibility_range_end > 0.0 and lod1.visibility_range_begin > 0.0, "LOD visibility ranges applied (Slide 0-%.0f m, LOD1 from %.0f m)" % [s0.visibility_range_end, lod1.visibility_range_begin if lod1 else -1])
	var shapes: Array = []
	collect(inst, "CollisionShape3D", shapes)
	check(shapes.size() == 1 and shapes[0].shape is ConvexPolygonShape3D, "one convex collision shape (pickup)")
	# material: PBR textures
	var mat := (find(inst, "Frame") as MeshInstance3D).mesh.surface_get_material(0) as StandardMaterial3D
	check(mat != null and mat.albedo_texture != null and mat.normal_enabled and mat.normal_texture != null and mat.roughness_texture != null
		and mat.metallic_texture != null and mat.ao_enabled, "StandardMaterial3D with albedo, normal, roughness/metallic (ORM) and AO textures")
	if mat and mat.albedo_texture:
		check(mat.albedo_texture.get_width() == 2048, "texture size %d" % mat.albedo_texture.get_width())
	# animations
	var aps: Array = []
	collect(inst, "AnimationPlayer", aps)
	check(aps.size() == 1, "one AnimationPlayer")
	var ap: AnimationPlayer = aps[0]
	var want := {"A_WPN_Pistol_01_Fire": 0.1, "A_WPN_Pistol_01_Reload": 1.6, "A_WPN_Pistol_01_Empty": 1.0 / 30.0}
	for an in want:
		var a := ap.get_animation(an) if ap.has_animation(an) else null
		check(a != null and absf(a.length - want[an]) < 0.005 and a.loop_mode == Animation.LOOP_NONE,
			"%s length %.4f s, not looping (got %s)" % [an, want[an], a.length if a else "missing"])
	var slide := find(inst, "Slide") as Node3D
	var mag := find(inst, "Magazine") as Node3D
	var rest_s := slide.position
	ap.play("A_WPN_Pistol_01_Fire")
	ap.seek(1.0 / 30.0, true)
	ap.advance(0.0)
	check(absf((slide.position - rest_s).z + 0.028) < 0.002, "Fire: slide back 28 mm at t=1/30 s (dz=%.4f)" % (slide.position - rest_s).z)
	ap.seek(0.1, true)
	ap.advance(0.0)
	check((slide.position - rest_s).length() < 0.001, "Fire: slide back in battery at 0.1 s")
	ap.play("A_WPN_Pistol_01_Reload")
	ap.seek(9.0 / 30.0, true)
	ap.advance(0.0)
	check(mag.position.y < -0.10, "Reload f9: magazine dropped out (y=%.3f)" % mag.position.y)
	ap.seek(20.0 / 30.0, true)
	ap.advance(0.0)
	check(mag.scale.length() < 0.01, "Reload f20: old magazine hidden (scale 0)")
	ap.seek(34.0 / 30.0, true)
	ap.advance(0.0)
	check(mag.position.length() < 0.001 and mag.scale.is_equal_approx(Vector3.ONE), "Reload f34: new magazine seated")
	ap.play("A_WPN_Pistol_01_Empty")
	ap.seek(0.0, true)
	ap.advance(0.0)
	check(absf((slide.position - rest_s).z + 0.028) < 0.002, "Empty: slide locked back")
	root.remove_child(inst)
	inst.free()
	print("[PISTOL-GODOT] RESULT: %s (%d failures)" % ["PASS" if fails == 0 else "FAIL", fails])
	quit(0 if fails == 0 else 1)
	return true
