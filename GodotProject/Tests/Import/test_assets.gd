# UNDERWORLD - headless import tests for Bot 2's pipeline exports (T-PIPE-02, Bot 3).
# File: GodotProject/Tests/Import/test_assets.gd (kept out of the gameplay runner's Tests/test_*.gd glob).
# Run via Tests/run_asset_import_tests.sh (it exports the test assets with Tools/uwp into
# res://Tests/_generated/ and runs `godot --import` first).
# Checks:
#  - import preset: new .glb imports get import_script/path = uw_post_import.gd
#  - LODs: per manifest object exactly ONE level is visible at any camera distance; at 0 m only LOD0
#  - control: the same .glb imported WITHOUT the script shows all LODs at 0 m (the bug the preset fixes)
#  - loop modes of every animation == manifest "loop"; lengths == manifest duration_s
#  - humanoid test rig: Skeleton3D bones all belong to SkeletonProfileHumanoid
#  - every .glb under res://Assets and res://Tests/_generated loads; manifest aabb_godot == Godot AABB
#    (LOD0 visual meshes only; legacy T-PIPE-00 manifests without aabb_godot are skipped)
# Prints [ASSETTEST][PASS]/[FAIL]; exit 0 on PASS, 1 on any failure.
extends SceneTree

const GEN := "res://Tests/_generated"
const PRESET_SCRIPT := "res://Scripts/import/uw_post_import.gd"

var failures: Array[String] = []

func check(cond: bool, msg: String) -> void:
	print("[ASSETTEST][PASS] " if cond else "[ASSETTEST][FAIL] ", msg)
	if not cond:
		failures.append(msg)

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	var barrel := GEN + "/PT_UWP_Barrel/PT_UWP_Barrel.glb"
	var rig := GEN + "/PT_UWP_RigTest/PT_UWP_RigTest.glb"
	var human := GEN + "/PT_UWP_Humanoid/PT_UWP_Humanoid.glb"
	var noscript := GEN + "/NoScript/PT_UWP_Barrel.glb"
	for p in [barrel, rig, human]:
		check(_import_param(p, "import_script/path") == PRESET_SCRIPT, "%s: import preset applied (import_script/path=%s)" % [p.get_file(), _import_param(p, "import_script/path")])
	test_lods(barrel)
	test_lods_without_script(noscript, barrel)
	test_loops(rig)
	test_humanoid(human)
	test_all_assets()
	test_catalog_assets()
	if failures.is_empty():
		print("[ASSETTEST] RESULT: PASS")
		quit(0)
	else:
		print("[ASSETTEST] RESULT: FAIL (%d)" % failures.size())
		for f in failures:
			print("[ASSETTEST]   - ", f)
		quit(1)

# --- helpers ---------------------------------------------------------------

func _import_param(glb: String, key: String) -> String:
	var cf := ConfigFile.new()
	if cf.load(glb + ".import") != OK:
		return "<no .import>"
	return str(cf.get_value("params", key, "<unset>"))

func _manifest(glb: String) -> Dictionary:
	var p := glb.get_basename() + ".manifest.json"
	if not FileAccess.file_exists(p):
		return {}
	var d = JSON.parse_string(FileAccess.get_file_as_string(p))
	return d if d is Dictionary else {}

func _instance(glb: String) -> Node:
	var ps := load(glb) as PackedScene
	if ps == null:
		return null
	var n := ps.instantiate()
	root.add_child(n)
	return n

func _find(n: Node, name: String) -> Node:
	if String(n.name) == name:
		return n
	for c in n.get_children():
		var r := _find(c, name)
		if r != null:
			return r
	return null

func _collect(n: Node, cls: String, out: Array) -> void:
	if n.is_class(cls):
		out.append(n)
	for c in n.get_children():
		_collect(c, cls, out)

static func _in_range(g: GeometryInstance3D, d: float) -> bool:
	# Godot: begin/end 0 = no limit on that side.
	var b := g.visibility_range_begin
	var e := g.visibility_range_end
	return (b <= 0.0 or d >= b) and (e <= 0.0 or d < e)

## Number of levels of one manifest LOD object drawn at camera distance d.
func _visible_levels(inst: Node, levels: Array, d: float) -> Array:
	var out := []
	for lv in levels:
		var g := _find(inst, lv["name"]) as GeometryInstance3D
		if g != null and g.is_visible_in_tree() and _in_range(g, d):
			out.append(int(lv["level"]))
	return out

const DISTANCES := [0.0, 1.0, 5.0, 10.0, 15.0, 20.0, 30.0, 40.0, 60.0, 80.0, 100.0, 150.0, 200.0, 400.0]

# --- tests -----------------------------------------------------------------

func test_lods(glb: String) -> void:
	print("[ASSETTEST] == LODs with preset: ", glb.get_file())
	var m := _manifest(glb)
	var inst := _instance(glb)
	check(inst != null and not m.is_empty(), "%s loads, manifest present" % glb.get_file())
	if inst == null or m.is_empty():
		return
	var info: Dictionary = inst.get_meta("uw_post_import", {})
	var total_levels := 0
	for obj in m["lods"]:
		total_levels += obj["levels"].size()
	check(int(info.get("lod_nodes", -1)) > 0, "post-import ran: lod_nodes=%s (manifest levels %d)" % [info.get("lod_nodes"), total_levels])
	for obj in m["lods"]:
		var levels: Array = obj["levels"]
		for lv in levels:
			check(_find(inst, lv["name"]) is MeshInstance3D, "%s present as MeshInstance3D" % lv["name"])
		var at0 := _visible_levels(inst, levels, 0.0)
		check(at0 == [0], "%s at 0 m: only LOD0 drawn (got %s)" % [obj["object"], at0])
		var bad := []
		var seen := {}
		for d in DISTANCES:
			var v := _visible_levels(inst, levels, d)
			if v.size() > 1:
				bad.append([d, v])
			for l in v:
				seen[l] = true
		check(bad.is_empty(), "%s: never more than one LOD drawn (overlaps %s)" % [obj["object"], bad])
		check(seen.size() == levels.size(), "%s: every LOD level is used at some distance (%s)" % [obj["object"], seen.keys()])
		var ranges := []
		for lv in levels:
			var g := _find(inst, lv["name"]) as GeometryInstance3D
			ranges.append([lv["level"], g.visibility_range_begin, g.visibility_range_end])
		print("[ASSETTEST] %s ranges [level, begin, end]: %s" % [obj["object"], ranges])
	inst.queue_free()

func test_lods_without_script(noscript: String, with_script: String) -> void:
	print("[ASSETTEST] == control: same asset imported without the post-import script")
	check(_import_param(noscript, "import_script/path") == "", "control import has no import_script")
	var m := _manifest(with_script)
	var inst := _instance(noscript)
	if inst == null or m.is_empty():
		check(false, "control asset loads")
		return
	var at0 := _visible_levels(inst, m["lods"][0]["levels"], 0.0)
	check(at0.size() == m["lods"][0]["levels"].size(), "without the script ALL %d LODs are drawn at 0 m (got %s) – test detects the bug" % [m["lods"][0]["levels"].size(), at0])
	inst.queue_free()

func test_loops(glb: String) -> void:
	print("[ASSETTEST] == loop modes from manifest: ", glb.get_file())
	var m := _manifest(glb)
	var inst := _instance(glb)
	if inst == null or m.is_empty():
		check(false, "%s loads with manifest" % glb.get_file())
		return
	var aps: Array = []
	_collect(inst, "AnimationPlayer", aps)
	check(aps.size() == 1, "one AnimationPlayer")
	if aps.size() != 1:
		return
	var ap: AnimationPlayer = aps[0]
	var info: Dictionary = inst.get_meta("uw_post_import", {})
	check(int(info.get("loops_set", 0)) == m["animations"].size() and info.get("missing_animations", []).is_empty(), "post-import set %s loop modes, missing %s" % [info.get("loops_set"), info.get("missing_animations")])
	for a in m["animations"]:
		var name: String = a["name"]
		var anim := ap.get_animation(name) if ap.has_animation(name) else null
		check(anim != null, "%s imported" % name)
		if anim == null:
			continue
		var want := Animation.LOOP_LINEAR if a["loop"] else Animation.LOOP_NONE
		check(anim.loop_mode == want, "%s loop_mode %d == manifest loop=%s" % [name, anim.loop_mode, a["loop"]])
		check(absf(anim.length - float(a["duration_s"])) < 0.02, "%s length %.3f s == manifest %.3f s" % [name, anim.length, a["duration_s"]])
	inst.queue_free()

func test_humanoid(glb: String) -> void:
	print("[ASSETTEST] == humanoid rig vs SkeletonProfileHumanoid: ", glb.get_file())
	var inst := _instance(glb)
	if inst == null:
		check(false, "%s loads" % glb.get_file())
		return
	var sks: Array = []
	_collect(inst, "Skeleton3D", sks)
	check(sks.size() == 1, "one Skeleton3D")
	if sks.size() == 1:
		var profile := SkeletonProfileHumanoid.new()
		var known := {}
		for i in profile.bone_size:
			known[String(profile.get_bone_name(i))] = true
		var unknown := []
		for i in sks[0].get_bone_count():
			if not known.has(sks[0].get_bone_name(i)):
				unknown.append(sks[0].get_bone_name(i))
		check(unknown.is_empty() and sks[0].get_bone_count() >= 22, "%d bones, all SkeletonProfileHumanoid names (unknown %s)" % [sks[0].get_bone_count(), unknown])
	inst.queue_free()

func _glbs(dir: String, out: Array) -> void:
	var d := DirAccess.open(dir)
	if d == null:
		return
	for f in d.get_files():
		if f.ends_with(".glb"):
			out.append(dir.path_join(f))
	for sub in d.get_directories():
		_glbs(dir.path_join(sub), out)

func test_all_assets() -> void:
	print("[ASSETTEST] == all .glb: load + manifest AABB")
	var all: Array = []
	_glbs("res://Assets", all)
	_glbs(GEN, all)
	check(all.size() >= 4, "found %d .glb files" % all.size())
	for glb in all:
		var inst := _instance(glb)
		check(inst != null, "%s loads" % glb)
		if inst == null:
			continue
		var m := _manifest(glb)
		if not m.has("aabb_godot"):
			print("[ASSETTEST] SKIP AABB %s (no aabb_godot in manifest – legacy/control)" % glb)
			inst.queue_free()
			continue
		var meshes: Array = []
		_collect(inst, "MeshInstance3D", meshes)
		var box := AABB()
		var first := true
		for mi: MeshInstance3D in meshes:
			if String(mi.name).contains("_LOD") or mi.get_parent() is CollisionObject3D:
				continue
			var b := mi.global_transform * mi.get_aabb()
			box = b if first else box.merge(b)
			first = false
		var want_min := Vector3(m["aabb_godot"]["min"][0], m["aabb_godot"]["min"][1], m["aabb_godot"]["min"][2])
		var want_size := Vector3(m["aabb_godot"]["size"][0], m["aabb_godot"]["size"][1], m["aabb_godot"]["size"][2])
		check(not first and box.position.distance_to(want_min) < 0.02 and box.size.distance_to(want_size) < 0.02,
			"%s AABB %s == manifest min %s size %s" % [glb.get_file(), box, want_min, want_size])
		inst.queue_free()

## P1/P2 (T-DATA-01, T-PROP-01): every built catalogue entry imports as a usable game asset.
## Environment/props: real collision (a StaticBody shape), LOD chain wired (visibility ranges),
## textured PBR materials. Negative control: UW_ASSET_SABOTAGE=nocollision drops the collision
## count to zero for every entry (debug builds only).
func test_catalog_assets() -> void:
	print("[ASSETTEST] == content catalogue: built entries import as game assets")
	var path := ProjectSettings.globalize_path("res://").path_join("../Config/Content/catalog.json").simplify_path()
	var f := FileAccess.open(path, FileAccess.READ)
	check(f != null, "catalogue readable (%s)" % path)
	if f == null:
		return
	var cat = JSON.parse_string(f.get_as_text())
	var sabotage := OS.is_debug_build() and OS.get_environment("UW_ASSET_SABOTAGE") == "nocollision"
	var n := 0
	for e in (cat as Dictionary).get("entries", []):
		var typ := String(e.get("type", ""))
		if String(e.get("status", "")) == "PLANNED" or not e.has("asset") or typ not in ["environment", "prop", "armor"]:
			continue
		var glb := "res://" + String(e["asset"])
		var inst := _instance(glb)
		check(inst != null, "%s loads" % e["id"])
		if inst == null:
			continue
		n += 1
		var shapes: Array = []
		_collect(inst, "CollisionShape3D", shapes)
		if sabotage:
			shapes.clear()
		check(shapes.size() > 0, "%s has collision (%d shapes)" % [e["id"], shapes.size()])
		var meshes: Array = []
		_collect(inst, "MeshInstance3D", meshes)
		var lods := 0
		var ranged := 0
		var textured := 0
		var surfaces := 0
		for mi: MeshInstance3D in meshes:
			if mi.get_parent() is CollisionObject3D:
				continue
			if String(mi.name).contains("_LOD"):
				lods += 1
				if mi.visibility_range_begin > 0.0:
					ranged += 1
			if mi.mesh == null:
				continue
			for si in mi.mesh.get_surface_count():
				var mat := mi.get_active_material(si) as BaseMaterial3D
				surfaces += 1
				if mat and (mat.albedo_texture != null or mat.emission_enabled):
					textured += 1
		check(lods == 0 or ranged == lods, "%s: %d LOD meshes, %d with visibility ranges" % [e["id"], lods, ranged])
		# generated props (T-PROP-01) must be fully textured; the older kit may have flat parts
		if String(e.get("generator", "")).begins_with("build-props"):
			check(surfaces > 0 and textured == surfaces, "%s: %d/%d surfaces textured or emissive" % [e["id"], textured, surfaces])
		inst.queue_free()
	check(n >= 30, "catalogue: %d built environment/prop/armor entries imported (>= 30)" % n)
