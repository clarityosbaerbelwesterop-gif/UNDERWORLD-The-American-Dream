@tool
extends EditorScenePostImport
## UNDERWORLD - project-wide post-import script for .glb scenes (T-PIPE-02, Bot 3).
## Enabled for every NEW scene import via [importer_defaults] scene/import_script/path
## in project.godot. Steps:
##  1. LOD visibility ranges: Bot 2's uw_lod_post_import.gd (T-PIPE-01), vendored as
##     Scripts/import/uw_lod_post_import.gd. It MUST stay byte-identical to
##     Tools/underworld_pipeline/godot/uw_lod_post_import.gd (checked by
##     Tests/run_asset_import_tests.sh). Without it every LOD is drawn at once.
##  2. Animation loop modes from <Name>.manifest.json ("animations[].loop"), because the
##     glTF file carries no loop flag (T-PIPE-01 handoff).
## Result summary is stored on the root as meta "uw_post_import" for tests.

const UwLod := preload("res://Scripts/import/uw_lod_post_import.gd")

func _post_import(scene: Node) -> Object:
	var src := get_source_file()
	var info := {"source": src, "lod_nodes": 0, "manifest": "", "loops_set": 0,
		"missing_animations": PackedStringArray(), "unlisted_animations": PackedStringArray()}
	info["lod_nodes"] = UwLod.apply_lod_ranges(scene)
	var manifest_path := src.get_basename() + ".manifest.json"
	if FileAccess.file_exists(manifest_path):
		info["manifest"] = manifest_path
		var m = JSON.parse_string(FileAccess.get_file_as_string(manifest_path))
		if m is Dictionary:
			_apply_loop_modes(scene, m, info)
		else:
			push_error("uw_post_import: cannot parse %s" % manifest_path)
	scene.set_meta("uw_post_import", info)
	print("[UW-IMPORT] %s: lod_nodes=%d loops_set=%d manifest=%s missing=%s" % [src, info["lod_nodes"],
		info["loops_set"], "yes" if info["manifest"] != "" else "no", info["missing_animations"]])
	return scene

static func _apply_loop_modes(scene: Node, m: Dictionary, info: Dictionary) -> void:
	var wanted := {}
	for a in m.get("animations", []):
		if a is Dictionary and a.has("name"):
			wanted[String(a["name"])] = bool(a.get("loop", false))
	if wanted.is_empty():
		return
	var players: Array = []
	_collect_players(scene, players)
	var found := {}
	for ap: AnimationPlayer in players:
		for lib_name in ap.get_animation_library_list():
			var lib := ap.get_animation_library(lib_name)
			for anim_name in lib.get_animation_list():
				var n := String(anim_name)
				var anim := lib.get_animation(anim_name)
				if wanted.has(n):
					anim.loop_mode = Animation.LOOP_LINEAR if wanted[n] else Animation.LOOP_NONE
					found[n] = true
					info["loops_set"] += 1
				else:
					info["unlisted_animations"].append(n)
	for n in wanted:
		if not found.has(n):
			info["missing_animations"].append(n)
	if not info["missing_animations"].is_empty():
		push_warning("uw_post_import: manifest animations not in scene: %s" % info["missing_animations"])

static func _collect_players(n: Node, out: Array) -> void:
	if n is AnimationPlayer:
		out.append(n)
	for c in n.get_children():
		_collect_players(c, out)
