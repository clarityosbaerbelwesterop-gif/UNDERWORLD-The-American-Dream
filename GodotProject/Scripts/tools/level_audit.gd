# UNDERWORLD - level audit helpers (T-LVL-01a).
#
# The level is generated (Scripts/tools/build_level_calloway.gd), so "is the greybox readable and
# clean?" is a property of the DATA, not of an editor session. These are the measurements the
# tests and the review use, in one place:
#   * auto_named()      - Godot's "@Node3D@12" fallback names (a debugging trap)
#   * unused_ext()      - ext_resource entries nothing references any more
#   * contrast()        - luminance difference road / sidewalk (the capture requirement)
# Everything is a pure function of the scene, so it works headless.
class_name LevelAudit
extends RefCounted

## Negative control (UW_LEVEL_SABOTAGE=1): the contrast measurement clamps to a "good" value,
## i.e. the audit lies about a level whose surfaces are unreadable. The readability check must
## then FAIL - that is the whole point of the control.
static var _sabotage: int = -1


static func sabotage() -> bool:
	if _sabotage < 0:
		_sabotage = 1 if OS.is_debug_build() and OS.get_environment("UW_LEVEL_SABOTAGE").strip_edges() == "1" else 0
	return _sabotage == 1


## Every node in `root` whose name is still an engine fallback ("@Node3D@12").
static func auto_named(root: Node) -> PackedStringArray:
	var out: PackedStringArray = []
	_scan_names(root, out)
	return out


static func _scan_names(n: Node, out: PackedStringArray) -> void:
	if String(n.name).begins_with("@"):
		out.append("%s (%s)" % [n.name, n.get_path()])
	for c in n.get_children():
		_scan_names(c, out)


## ext_resource ids of a .tscn that are declared but never used.
static func unused_ext(tscn_path: String) -> PackedStringArray:
	var out: PackedStringArray = []
	if not FileAccess.file_exists(tscn_path):
		return out
	var text := FileAccess.get_file_as_string(tscn_path)
	for line in text.split("\n"):
		if not line.begins_with("[ext_resource"):
			continue
		var at := line.find("id=\"")
		if at < 0:
			continue
		var rest := line.substr(at + 4)
		var id := rest.substr(0, rest.find("\""))
		# The declaration itself is the first hit; a used id appears at least once more.
		if text.count("\"%s\"" % id) <= 1:
			out.append(id)
	return out


static func luminance(c: Color) -> float:
	return 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b


## Albedo of the first MeshInstance3D under `n`, in the order the renderer uses it:
## material_override -> per-surface override -> the mesh's surface material.
static func albedo_of(n: Node) -> Color:
	if n is MeshInstance3D:
		var mi := n as MeshInstance3D
		if mi.material_override is StandardMaterial3D:
			return (mi.material_override as StandardMaterial3D).albedo_color
		if mi.mesh != null:
			for i in mi.mesh.get_surface_count():
				var ov = mi.get_surface_override_material(i)
				if ov is StandardMaterial3D:
					return (ov as StandardMaterial3D).albedo_color
			if mi.mesh.get_surface_count() > 0:
				var m = mi.mesh.surface_get_material(0)
				if m is StandardMaterial3D:
					return (m as StandardMaterial3D).albedo_color
	for c in n.get_children():
		var got := albedo_of(c)
		if got.a > 0.0:
			return got
	return Color(0, 0, 0, 0)


## Road vs sidewalk vs kerb-line luminance for the whole level:
##   {"road": float, "sidewalk": float, "kerb": float, "diff": float}
static func contrast(root: Node) -> Dictionary:
	var road := 0.0
	var side := 0.0
	var kerb := 0.0
	var have := {"road": false, "sidewalk": false, "kerb": false}
	for n in root.find_children("*", "Node", true, false):
		# Only look at OUR nodes: an instanced kit piece has internal Meshes whose surface
		# material is the (white) import default - measuring those says nothing about the level.
		if n.owner == null:
			continue
		var nm := String(n.name)
		# The PAINTED copies ("Road_Straight_01_SM_LA_Road_Straight") are the visible surface and
		# they come first in tree order, so they must match before the hidden kit instance does.
		if not have["road"] and nm.begins_with("Road_Straight") and n.has_method("set_surface_override_material"):
			var c := albedo_of(n)
			if c.a > 0.0:
				road = luminance(c)
				have["road"] = true
		elif not have["sidewalk"] and nm.begins_with("Sidewalk_Curb") and n.has_method("set_surface_override_material"):
			var c2 := albedo_of(n)
			if c2.a > 0.0:
				side = luminance(c2)
				have["sidewalk"] = true
		elif not have["kerb"] and nm.begins_with("Kerb_Line"):
			var c3 := albedo_of(n)
			if c3.a > 0.0:
				kerb = luminance(c3)
				have["kerb"] = true
	var diff := absf(road - side)
	if sabotage():
		diff = 0.02   # "looks fine to me" - the audit reports a value that hides the problem
	return {"road": road, "sidewalk": side, "kerb": kerb, "diff": diff,
		"found": have}
