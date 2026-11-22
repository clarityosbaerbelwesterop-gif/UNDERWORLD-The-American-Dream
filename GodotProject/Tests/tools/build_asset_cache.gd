# UNDERWORLD - builds a throw-away asset cache for machines WITHOUT the Git LFS binaries.
#
#   godot --headless --path GodotProject --script res://Tests/tools/build_asset_cache.gd
#
# Why: on the build sandbox used for the M01 work the LFS objects are not downloadable
# (release/LFS hosts blocked), so every Assets/**.glb is a 130-byte pointer file. Godot's
# importer treats those as broken resources. This script replaces them with EMPTY scenes of
# the same name so scripts/scenes resolve. It is a stand-in for the real assets ONLY:
#   * it prints a loud banner and is never part of Tests/run_all.sh
#   * on a normal checkout (git lfs pull done) it refuses to run
#   * import tests that need real geometry (asset import, LOD ranges) are NOT valid here
extends SceneTree

const ASSET_ROOT := "res://Assets/"

func _initialize() -> void:
	if _real_assets_present():
		print("[ASSETCACHE] real LFS assets present - nothing to do")
		quit(0)
		return
	print("[ASSETCACHE] ============================================================")
	print("[ASSETCACHE] LFS binaries are NOT available on this machine.")
	print("[ASSETCACHE] Writing EMPTY placeholder scenes for every .glb (phase-8/visual tests")
	print("[ASSETCACHE] are NOT valid with these; logic tests only). Re-run `git lfs pull`")
	print("[ASSETCACHE] and delete GodotProject/.godot/imported to restore the real assets.")
	print("[ASSETCACHE] ============================================================")
	var made := 0
	var skipped := 0
	for p in _glbs(ASSET_ROOT):
		var target := p + ".cache_scn"
		var root_node := Node3D.new()
		root_node.name = p.get_file().get_basename()
		var ps := PackedScene.new()
		var err := ps.pack(root_node)
		if err == OK:
			err = ResourceSaver.save(ps, target)
		if err == OK:
			made += 1
			print("[ASSETCACHE] placeholder -> ", target)
		else:
			skipped += 1
		root_node.free()
	print("[ASSETCACHE] done: %d placeholders, %d skipped" % [made, skipped])
	quit(0)


func _real_assets_present() -> bool:
	for p in _glbs(ASSET_ROOT):
		var f := FileAccess.open(p, FileAccess.READ)
		if f == null:
			continue
		var head := f.get_buffer(64).get_string_from_utf8()
		f.close()
		if not head.begins_with("version https://git-lfs"):
			return true
	return false


func _glbs(dir_path: String) -> PackedStringArray:
	var out := PackedStringArray()
	var dir := DirAccess.open(dir_path)
	if dir == null:
		return out
	dir.list_dir_begin()
	var n := dir.get_next()
	while n != "":
		if n.begins_with("."):
			n = dir.get_next()
			continue
		var full := dir_path.path_join(n)
		if dir.current_is_dir():
			out.append_array(_glbs(full))
		elif n.ends_with(".glb"):
			out.append(full)
		n = dir.get_next()
	dir.list_dir_end()
	return out
