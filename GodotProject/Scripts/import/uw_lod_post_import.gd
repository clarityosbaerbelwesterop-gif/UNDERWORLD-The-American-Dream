@tool
extends EditorScenePostImport
## UNDERWORLD pipeline (T-PIPE-01, Bot 2): Godot post-import script for .glb files
## exported by Tools/underworld_pipeline. Reads the glTF node extras the exporter writes
##   uw_lod: int (0 = base mesh, 1.. = Tools-generated <Name>_LOD<n> children)
##   uw_visibility_range: [begin_m, end_m]
## and sets GeometryInstance3D.visibility_range_begin/end so only one LOD is drawn.
## Use: in the .glb's import settings set  import_script/path="res://<path>/uw_lod_post_import.gd"
## (Bot 3 owns import presets, T-PIPE-02.)

func _post_import(scene: Node) -> Object:
	var n := apply_lod_ranges(scene)
	print("[UWP-GODOT] %s: visibility ranges set on %d LOD nodes" % [get_source_file(), n])
	return scene

static func apply_lod_ranges(node: Node) -> int:
	var count := 0
	if node is GeometryInstance3D and node.has_meta("extras"):
		var ex = node.get_meta("extras")
		if ex is Dictionary and ex.has("uw_visibility_range"):
			var r = ex["uw_visibility_range"]
			node.visibility_range_begin = float(r[0])
			node.visibility_range_end = float(r[1])
			count += 1
	for c in node.get_children():
		count += apply_lod_ranges(c)
	return count
