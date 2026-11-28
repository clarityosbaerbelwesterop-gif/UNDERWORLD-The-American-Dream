extends SceneTree
## Plan view of the generated level, drawn from the scene's own data.
##
##     $GODOT --headless --path GodotProject --script res://Tests/tools/capture_level_plan.gd
##
## This is NOT a renderer screenshot: this box has no X server and no GPU, so
## `Tools/godot_phase8_capture.sh` cannot run (Docs/TOOLCHAIN_SANDBOX.md §9). What it does is
## honest and useful anyway - it walks the real level scene, projects every visible mesh's
## world AABB onto the XZ plane and fills it with the luminance of the material the mesh
## actually uses (surface override first, then the mesh material). So the picture shows the
## real footprints, the real positions and the real albedo steps that `test_level.gd` measures,
## just flat. It can catch "the buildings are inside the road" and "road and sidewalk have the
## same grey" - it cannot show lighting, shape or art quality.
##
## Writes /tmp/plan_calloway_ave.png, then copy it where you need it. PNG output is NOT
## committed: git-lfs cannot be installed on this box (Docs/Reports/BERICHT_AUFTRAG-02.md).
const LEVEL := "res://Scenes/Levels/LA_CallowayAve.tscn"
## Absolute path: res:// writing is not allowed for this scene tree, and the repo root
## is not reachable through res:// on purpose (GodotProject is the project root).
const OUT := "/tmp/plan_calloway_ave.png"
const PX_PER_M := 6
const MARGIN_M := 6.0

var _rects: Array = []   # [Rect2 (xz), Color, z-index, name]
var _bounds := Rect2()


func _initialize() -> void:
	var level := (load(LEVEL) as PackedScene).instantiate()
	root.add_child(level)
	for i in 20:
		await physics_frame
	_collect(level, 0)
	_paint()
	level.free()
	quit(0)


func _collect(node: Node, depth: int) -> void:
	if node is MeshInstance3D:
		var mi := node as MeshInstance3D
		if mi.mesh != null and mi.is_visible_in_tree():
			var box: AABB = mi.global_transform * mi.get_aabb()
			var r := Rect2(box.position.x, box.position.z, box.size.x, box.size.z)
			if r.size.x > 0.01 and r.size.y > 0.01:
				var col := _colour(mi)
				var maxy := box.position.y + box.size.y
				_rects.append([r, col, maxy, String(mi.name)])
				_bounds = r if _bounds.size == Vector2.ZERO else _bounds.merge(r)
	for c in node.get_children():
		_collect(c, depth + 1)


func _colour(mi: MeshInstance3D) -> Color:
	# The greybox props use `material_override` (not a surface override), and missing that made
	# buildings look exactly like the ground in the first version of this picture.
	var mat: Material = mi.material_override
	for i in mi.get_surface_override_material_count():
		if mat == null:
			mat = mi.get_surface_override_material(i)
	if mat == null and mi.mesh != null:
		for i in mi.mesh.get_surface_count():
			mat = mi.mesh.surface_get_material(i)
			if mat != null:
				break
	var albedo := Color(0.5, 0.5, 0.5)
	if mat is StandardMaterial3D:
		albedo = (mat as StandardMaterial3D).albedo_color
	var lum := 0.2126 * albedo.r + 0.7152 * albedo.g + 0.0722 * albedo.b
	# Keep the hue family, push contrast so the flat plan stays readable.
	var c := albedo
	if c.s < 0.06:
		c = Color(lum, lum, lum)
	return Color(c.r, c.g, c.b)


func _paint() -> void:
	var w := int((_bounds.size.x + 2 * MARGIN_M) * PX_PER_M)
	var h := int((_bounds.size.y + 2 * MARGIN_M) * PX_PER_M)
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	img.fill(Color(0.07, 0.08, 0.10))
	# Painter's order, but the 240 m ground plane goes first even though it is at y = -0.02:
	# sorting purely by top height would let it bury everything under a 0.05 m road.
	_rects.sort_custom(func(a, b): return a[2] < b[2])
	for i in range(_rects.size()):
		if String(_rects[i][3]) == "GroundMesh":
			_rects.push_front(_rects[i])
			_rects.remove_at(i + 1)
			break
	for e in _rects:
		var r: Rect2 = e[0]
		var c: Color = e[1]
		var x0 := int((r.position.x - _bounds.position.x + MARGIN_M) * PX_PER_M)
		var y0 := int((r.position.y - _bounds.position.y + MARGIN_M) * PX_PER_M)
		img.fill_rect(Rect2i(x0, y0, maxi(1, int(r.size.x * PX_PER_M)), maxi(1, int(r.size.y * PX_PER_M))), c)
	# 5 m grid for scale.
	var grid := Color(1, 1, 1, 0.09)
	var step := int(5.0 * PX_PER_M)
	for x in range(0, w, step):
		img.fill_rect(Rect2i(x, 0, 1, h), grid)
	for y in range(0, h, step):
		img.fill_rect(Rect2i(0, y, w, 1), grid)
	var err := img.save_png(OUT)
	print("[PLAN] %d meshes, %dx%d px, bounds %s, save=%d -> %s" % [_rects.size(), w, h, _bounds, err, OUT])
