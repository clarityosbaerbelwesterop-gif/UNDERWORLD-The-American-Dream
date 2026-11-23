# UNDERWORLD - generates Scenes/Levels/LA_CallowayAve.tscn (T-LVL-01).
#
# Reproducible level assembly: the street is generated from the modular LA kit and the
# layout brief (Docs/LevelDesign/LA_CallowayAve_Layout.md), NOT hand-placed in the editor.
# Every mission anchor (Area3D / Marker3D) is created with the exact name M01 needs.
#
# Run headless (writes the .tscn in the repo):
#   godot --headless --path GodotProject --script res://Scripts/tools/build_level_calloway.gd
#
# The layout uses the real kit .glb files when they are present (Assets/Environment/LA/...)
# and falls back to greybox primitives with the same footprints when they are not, so the
# level can always be built and played on a machine without the LFS assets. Kit instances
# keep the kit's node names (SM_LA_*), so the art pass only replaces the files, not the level.
extends SceneTree

const OUT := "res://Scenes/Levels/LA_CallowayAve.tscn"
const KIT_DIR := "res://Assets/Environment/LA/"
const CRATE := "res://Assets/Props/SM_Prop_PackageCrate/SM_Prop_PackageCrate.glb"

# Layout constants (Docs/LevelDesign/LA_CallowayAve_Layout.md §3)
const ROAD_W := 10.0
const ROAD_LEN := 14.0
const SIDEWALK_W := 4.0
const SIDEWALK_LEN := 10.0
## Kerb lines (layout §3.1): WEST road x = -29 .. -19, EAST road x = +19 .. +29,
## NORTH/SOUTH roads z = +72 .. +86 and -86 .. -72. Road centres:
const WEST_X := -24.0
const EAST_X := 24.0
## Sidewalk centre lines: -33 .. -29 and -19 .. -15 (west), +15 .. +19 and +29 .. +33 (east).
const WSIDE_W := -31.0
const WSIDE_E := -17.0
const ESIDE_W := 17.0
const ESIDE_E := 31.0
const NORTH_Z := 79.0
const SOUTH_Z := -79.0
## Building frontage lines (gaps.cfg raises this if the building is deeper than 2 m).
## A building sits on the lot side of this line, never on a sidewalk or the roadway:
##   west block  -> front face at x = X_WEST_FRONT, body extends west (deeper x)
##   east block  -> front face at x = X_EAST_FRONT, body extends east
##   north strip -> front face at z = Z_NORTH_FRONT, body extends north
##   south strip -> front face at z = Z_SOUTH_FRONT, body extends south
const X_WEST_FRONT := -33.0
const X_EAST_FRONT := 33.0
const Z_NORTH_FRONT := 86.0
const Z_SOUTH_FRONT := -86.0

var level: Node3D
var kit: Dictionary = {}       # name -> PackedScene or null
var rng := RandomNumberGenerator.new()


func _initialize() -> void:
	rng.seed = 20261122
	level = Node3D.new()
	level.name = "LA_CallowayAve"
	root.name = "LA_CallowayAve"
	# The level has to be IN the tree before the navmesh is baked: parse_source_geometry_data()
	# only sees geometry with a global transform, so baking from a detached node silently
	# produced an empty navmesh (0 polygons).
	root.add_child(level)
	_load_kit()
	_build_ground()
	_build_streets()
	_build_buildings()
	_build_props()
	_build_lighting()
	_build_navmesh()      # region + settings (no geometry)
	# The parser reads global transforms, so the tree must have run at least one frame before the
	# geometry is there (baking right after add_child() yields 0 polygons).
	await process_frame
	await physics_frame
	_bake_navmesh()       # ... and bake it from the collision geometry above
	_build_spawns_and_ai()
	_build_mission_anchors()
	_save()
	quit(0)


# --- helpers ------------------------------------------------------------------

func _load_kit() -> void:
	for n in ["SM_LA_Road_Straight", "SM_LA_Sidewalk_Curb", "SM_LA_Bldg_ShopStucco",
			"SM_LA_Bldg_GarageM01", "SM_LA_Streetlight", "SM_LA_PalmTree"]:
		var res_path: String = KIT_DIR + n + "/" + n + ".glb"
		kit[n] = load(res_path) if ResourceLoader.exists(res_path) else null
		if kit[n] == null:
			print("[LVL] kit piece missing, greybox fallback: ", n)
	var crate_pack: PackedScene = null
	if ResourceLoader.exists(CRATE):
		crate_pack = load(CRATE) as PackedScene
	var c = crate_pack
	kit["SM_Prop_PackageCrate"] = c
	print("[LVL] kit loaded: %d/6 real, crate=%s" % [
		kit.values().filter(func(v): return v != null and v is PackedScene).size() - (1 if c != null else 0),
		str(c != null)])


func _mesh_instance(name: String, mesh: Mesh, mat: StandardMaterial3D, parent: Node, pos: Vector3, rot_y := 0.0) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.name = name
	mi.mesh = mesh
	if mat != null:
		mi.material_override = mat
	if parent != null:
		parent.add_child(mi)
	mi.position = pos
	mi.rotation.y = rot_y
	return mi


## Render-only box (paint, decals, markings): no collision, so it can never snag a character.
func _visual_box(name: String, size: Vector3, pos: Vector3, mat: StandardMaterial3D, parent: Node) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.name = name
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	if mat != null:
		mi.material_override = mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(mi)
	mi.position = pos
	return mi

func _static_box(name: String, size: Vector3, pos: Vector3, mat: StandardMaterial3D, parent: Node, rot_y := 0.0) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.name = name
	body.collision_layer = 1        # World
	body.collision_mask = 0
	parent.add_child(body)
	body.position = pos
	body.rotation.y = rot_y
	var mi := MeshInstance3D.new()
	mi.name = "Mesh"
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	if mat != null:
		mi.material_override = mat
	body.add_child(mi)
	var cs := CollisionShape3D.new()
	cs.name = "Collision"
	var sh := BoxShape3D.new()
	sh.size = size
	cs.shape = sh
	body.add_child(cs)
	return body


func _mat(color: Color, rough := 0.85, metal := 0.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = rough
	m.metallic = metal
	return m


## Running counter per piece name, so a level greps like a level: Road_Straight_01 .. _26.
var _name_counter: Dictionary = {}


## Instance a kit piece if available, else its greybox fallback (same footprint + collision).
## Names are ALWAYS speaking (piece + running index): Godot's automatic "@Node3D@NN" names are a
## debugging trap and the level review (T-LVL-01a) rejects them.
func _kit_piece(name: String, pos: Vector3, rot_y: float, fallback_size: Vector3, fallback_mat: StandardMaterial3D, parent: Node, paint: Array = []) -> Node3D:
	var short := name.trim_prefix("SM_LA_").trim_prefix("SM_Prop_")
	_name_counter[short] = int(_name_counter.get(short, 0)) + 1
	var piece_name := "%s_%02d" % [short, int(_name_counter[short])]
	var scene = kit.get(name)
	if scene != null and scene is PackedScene:
		var inst := (scene as PackedScene).instantiate()
		inst.name = piece_name
		parent.add_child(inst)
		inst.position = pos
		inst.rotation.y = rot_y
		# T-LVL-01a: until now the fallback material was ONLY used for the greybox, so the real
		# kit pieces kept their near-black asphalt / light concrete textures and the capture showed
		# three greys that nobody could tell apart. `paint` overrides selected SURFACES by their
		# material name, so the lane markings of the road piece survive.
		#
		# The override cannot live on the instanced meshes: PackedScene only serialises the
		# instance root, so per-surface overrides inside a sub-scene are silently dropped when the
		# level is saved (measured: 0 "surface_override_material" entries in the .tscn). So the
		# painted surfaces become LEVEL-OWNED mesh instances; the kit instance stays hidden and
		# keeps its exported hull, which is what the physics and the navmesh parse.
		if not paint.is_empty():
			_own_painted_meshes(inst, parent, piece_name, paint)
			inst.visible = false
		return inst
	var body := _static_box(piece_name, fallback_size, pos, fallback_mat, parent, rot_y)
	return body


## Copies every MeshInstance of `inst` that carries a painted surface into `parent` as a
## level-owned node (so it survives packing) and overrides only the named materials.
func _own_painted_meshes(inst: Node3D, parent: Node, piece_name: String, paint: Array) -> void:
	for mi in inst.find_children("*", "MeshInstance3D", true, false):
		var src := mi as MeshInstance3D
		if src.mesh == null:
			continue
		var wanted := {}
		for entry in paint:
			for i in src.mesh.get_surface_count():
				var m = src.mesh.surface_get_material(i)
				if m is BaseMaterial3D and String((m as BaseMaterial3D).resource_name).contains(String(entry[0])):
					wanted[i] = entry[1]
		if wanted.is_empty():
			continue
		var copy := MeshInstance3D.new()
		copy.name = "%s_%s" % [piece_name, String(src.name).trim_suffix("_Mesh")]
		copy.mesh = src.mesh
		# Compose the chain from the kit instance down to this mesh BY HAND.
		# global_transform is useless here: `_initialize()` of a --script SceneTree runs before
		# SceneTree::initialize() sets the tree, so `root.add_child(level)` does NOT make the level
		# "inside tree", and every global_transform still reads identity. (Measured: all 26 road
		# copies were stored at (0,0,0) and the whole street was invisible in-game - the plan
		# capture found it, the luminance test did not.)
		var chain := Transform3D.IDENTITY
		var walk: Node = src
		while walk != null and walk != inst:
			if walk is Node3D:
				chain = (walk as Node3D).transform * chain
			walk = walk.get_parent()
		copy.transform = inst.transform * chain
		parent.add_child(copy)
		for i in wanted:
			copy.set_surface_override_material(i, wanted[i])


## Override every surface of `n` whose material name contains `needle` (keeps the others).
func _paint_surfaces(n: Node, needle: String, mat: StandardMaterial3D) -> void:
	if n is MeshInstance3D:
		var mi := n as MeshInstance3D
		if mi.mesh != null:
			for i in mi.mesh.get_surface_count():
				var m = mi.mesh.surface_get_material(i)
				if m is BaseMaterial3D and String((m as BaseMaterial3D).resource_name).contains(needle):
					mi.set_surface_override_material(i, mat)
	for c in n.get_children():
		_paint_surfaces(c, needle, mat)


# --- geometry -----------------------------------------------------------------

func _build_ground() -> void:
	var g := Node3D.new()
	g.name = "Ground"
	level.add_child(g)
	var mat := _mat(Color(0.24, 0.22, 0.20), 0.95)
	var plane := PlaneMesh.new()
	plane.size = Vector2(240, 240)
	_mesh_instance("GroundMesh", plane, mat, g, Vector3(0, -0.02, 0))
	var body := StaticBody3D.new()
	body.name = "GroundBody"
	body.collision_layer = 1
	body.collision_mask = 0
	g.add_child(body)
	var cs := CollisionShape3D.new()
	cs.name = "Collision"
	var sh := BoxShape3D.new()
	sh.size = Vector3(240, 0.2, 240)
	cs.shape = sh
	cs.position = Vector3(0, -0.12, 0)
	body.add_child(cs)


func _build_streets() -> void:
	var s := Node3D.new()
	s.name = "Streets"
	level.add_child(s)
	# T-LVL-01a: the kit textures are near-black asphalt and light concrete and the ambient sky
	# washed both out to the same grey in the capture. Explicit override materials give road,
	# kerb and sidewalk three clearly different values (measured in check_level.gd / test_level).
	var asphalt := _mat(Color(0.15, 0.15, 0.16), 0.95)
	var concrete := _mat(Color(0.62, 0.60, 0.56), 0.90)

	# West street: road strip along Z from -86..+86, modules of 14 m
	var z := -86.0 + ROAD_LEN * 0.5
	while z <= 86.0:
		_kit_piece("SM_LA_Road_Straight", Vector3(WEST_X, 0, z), 0.0,
			Vector3(ROAD_W, 0.04, ROAD_LEN), asphalt, s, [["Asphalt", asphalt]])
		_kit_piece("SM_LA_Road_Straight", Vector3(EAST_X, 0, z), 0.0,
			Vector3(ROAD_W, 0.04, ROAD_LEN), asphalt, s, [["Asphalt", asphalt]])
		z += ROAD_LEN
	# Sidewalks: 4 m wide, on both sides of both N-S lanes (layout §3.1):
	# west lane kerbs at -29 / -19 -> sidewalk centres -31 / -17; east lane -> +17 / +31.
	var zz := -85.0 + SIDEWALK_LEN * 0.5
	while zz <= 85.0:
		for x in [WSIDE_E, WSIDE_W, ESIDE_W, ESIDE_E]:
			_kit_piece("SM_LA_Sidewalk_Curb", Vector3(x, 0, zz), 0.0,
				Vector3(SIDEWALK_W, 0.16, SIDEWALK_LEN), concrete, s, [["Concrete", concrete]])
		zz += SIDEWALK_LEN
	# A bright kerb line on the street side of every sidewalk: 0.18 m wide, 0.02 m above the
	# sidewalk, so the edge reads even when the sun is flat (glyph, not decoration).
	var kerb_mat := _mat(Color(0.80, 0.78, 0.72), 0.85)
	# Kerb lines: PAINT, not geometry (B-LVL-01, T-BUILD-02). They used to be 2 cm proud static
	# boxes - a 2 cm lip right at the player's step threshold - and all four ran along the
	# BUILDING side of the sidewalks, i.e. across the M01 garage door: a player could not walk in.
	# Now: visual-only strips on the street-side edge, 3 mm proud, no collision.
	# All four used to sit on the building side (sign error); street side = the edge facing the road.
	for kx in [WSIDE_E - SIDEWALK_W * 0.5 + 0.09, WSIDE_W + SIDEWALK_W * 0.5 - 0.09,
			ESIDE_W + SIDEWALK_W * 0.5 - 0.09, ESIDE_E - SIDEWALK_W * 0.5 + 0.09]:
		_visual_box("Kerb_Line_%+.1f" % kx, Vector3(0.18, 0.006, 170.0),
			Vector3(kx, 0.16, 0.0), kerb_mat, s)
	# Same line along the two closing segments (south/north).
	for kz in [Z_SOUTH_FRONT + 4.0 - 0.09, Z_NORTH_FRONT - 4.0 + 0.09]:
		_visual_box("Kerb_Line_z%+.1f" % kz, Vector3(66.0, 0.006, 0.18),
			Vector3(0.0, 0.16, kz), kerb_mat, s)
	# Sidewalks along the south and north segments too, so pedestrians never walk on the
	# roadway and the block edge is readable (z = -86 / +86 kerb, 4 m deep).
	var xx := -33.0
	while xx <= 33.0:
		_kit_piece("SM_LA_Sidewalk_Curb", Vector3(xx, 0, Z_SOUTH_FRONT + 2.0), PI * 0.5,
			Vector3(SIDEWALK_W, 0.16, SIDEWALK_LEN), concrete, s, [["Concrete", concrete]])
		_kit_piece("SM_LA_Sidewalk_Curb", Vector3(xx, 0, Z_NORTH_FRONT - 2.0), PI * 0.5,
			Vector3(SIDEWALK_W, 0.16, SIDEWALK_LEN), concrete, s, [["Concrete", concrete]])
		xx += SIDEWALK_LEN
	# North and south closing roads (X from -33..+33, 8 m deep)
	for x in [-30.0, -16.0, -2.0, 12.0, 26.0]:
		for zc in [NORTH_Z, SOUTH_Z]:
			_kit_piece("SM_LA_Road_Straight", Vector3(x + 2.0, 0, zc), PI * 0.5,
				Vector3(14.0, 0.04, ROAD_W), asphalt, s, [["Asphalt", asphalt]])
	# Kerb-gap alley on the west side (never a dead end, layout §3.1)
	for zc in [-4.0, 4.0]:
		_kit_piece("SM_LA_Road_Straight", Vector3(-42.0, 0, zc), PI * 0.5,
			Vector3(14.0, 0.04, 8.0), concrete, s, [["Asphalt", _mat(Color(0.42, 0.40, 0.37), 0.93)]])


## Footprint of a kit piece as the ART actually ships it (manifest aabb_godot), not the
## nominal grid size. Falls back to `fallback` when the manifest is missing.
func _kit_size(name: String, axis: int, fallback: float) -> float:
	var path := KIT_DIR + name + "/" + name + ".manifest.json"
	if not FileAccess.file_exists(path):
		return fallback
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return fallback
	var parsed = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(parsed) != TYPE_DICTIONARY or not parsed.has("aabb_godot"):
		return fallback
	var size: Array = parsed["aabb_godot"]["size"]
	return float(size[axis]) if size.size() > axis else fallback


## Place a building so that its FRONT FACE sits on `front`, with the body on the lot side:
##   "west"  -> body at -X, front face at +X (faces east onto the west street)
##   "east"  -> body at +X, front face at -X (faces west onto the east service lane)
##   "north" -> body at +Z, front face at -Z (faces south onto the north segment)
##   "south" -> body at -Z, front face at +Z (faces north onto the south segment)
## `along` is the coordinate on the other axis. Never overlaps a sidewalk or the roadway,
## which is what makes the M01 drive loop drivable.
## Returns the placed block; the caller attaches it to the scene (it is created detached here,
## because a Node can only have one parent - attaching it twice renames it to "@Node3D@NN").
func _building(name: String, front: float, along: float, facing: String, size: Vector3, mat: StandardMaterial3D) -> Node3D:
	var b := Node3D.new()
	b.name = name + "_Block"
	var body := _kit_piece(name, Vector3.ZERO, 0.0, size, mat, b)
	# kit pieces carry their manifest footprint; the greybox fallback uses `size`
	var depth_x := size.x
	var depth_z := size.z
	if kit.get(name) is PackedScene:
		depth_x = _kit_size(name, 0, size.x)
		depth_z = _kit_size(name, 2, size.z)
	match facing:
		"west":
			body.position = Vector3(front - depth_x * 0.5, 0.0, along)
			body.rotation.y = -PI * 0.5          # front face (+Z of the piece) -> +X
		"east":
			body.position = Vector3(front + depth_x * 0.5, 0.0, along)
			body.rotation.y = PI * 0.5           # front face -> -X
		"north":
			body.position = Vector3(along, 0.0, front + depth_z * 0.5)
			body.rotation.y = PI                 # front face -> -Z
		"south":
			body.position = Vector3(along, 0.0, front - depth_z * 0.5)
			body.rotation.y = 0.0                # front face -> +Z
		_:
			push_error("unknown facing %s" % facing)
	# Return the BLOCK, not the piece: the piece is already parented to it, and re-parenting the
	# piece is what made every building silently disappear from the saved scene (T-LVL-01a).
	return b


func _build_buildings() -> void:
	var b := Node3D.new()
	b.name = "BlockBuildings"
	level.add_child(b)
	var stucco_a := _mat(Color(0.72, 0.62, 0.48), 0.9)
	var stucco_b := _mat(Color(0.62, 0.52, 0.44), 0.9)
	var brick := _mat(Color(0.45, 0.28, 0.24), 0.95)
	var industrial := _mat(Color(0.52, 0.53, 0.50), 0.85)
	var shop_size := Vector3(10.0, 7.2, 8.0)
	# West block: shop row behind the west sidewalk (front face on the kerb line x = -33)
	# The drive loop runs east of these, on x = -29 .. -19.
	for entry in [
			["Bldg_Shop_01", -60.0, stucco_a],
			["Bldg_Shop_02", -38.0, stucco_b],
			["Bldg_Shop_03", 20.0, stucco_a],
			["Bldg_Apartment_A", 52.0, brick],
			]:
		var n: String = entry[0]
		var node := _building(n, X_WEST_FRONT, entry[1], "west", shop_size, entry[2])
		b.add_child(node)
	# East block: garage + industrial behind the east sidewalk (front face x = +33).
	# Their entrances face west onto the east service lane.
	for entry in [
			["Bldg_Industrial_01", -50.0, industrial],
			["Bldg_Warehouse", 78.0, industrial],
			]:
		b.add_child(_building(entry[0], X_EAST_FRONT, entry[1], "east", shop_size, entry[2]))
	# 4-storey apartment over Shop03/Apartment_A: stacked mass, same lot
	_static_box("Bldg_Apartment_A_Upper", Vector3(10.0, 6.0, 8.0),
		Vector3(X_WEST_FRONT - 5.0, 10.2, 52.0), brick, b)
	# Shop 04 faces north onto the south segment, behind the south sidewalk (z = -86)
	b.add_child(_building("Bldg_Shop_04", Z_SOUTH_FRONT, -4.0, "south", shop_size, stucco_b))
	# Warehouse roll-up door on the west face of the warehouse (facing the east lane)
	_static_box("Warehouse_Door", Vector3(0.3, 4.2, 6.0), Vector3(X_EAST_FRONT - 0.15, 2.1, 78.0),
		_mat(Color(0.35, 0.37, 0.40), 0.5, 0.6), b)
	_build_garage(b)


## The M01 garage: 10 x 8 m interior, hollow, roll-up door facing WEST onto the east service
## lane. Sits in the east block behind the east sidewalk, exactly where the kit shell is.
## Areas/markers keep their documented world positions (layout §3.3); moving the building
## instead of the anchors means no mission / HUD code has to change.
func _build_garage(b: Node3D) -> void:
	var garage_pos := Vector3(X_EAST_FRONT + 5.0, 0.0, 6.0)
	# The kit shell is HOLLOW (roll-up door facing west) - never replace it with a solid box,
	# or the player can never walk in to the ambush / package. Its own collision comes from the
	# exported UCX_-colonly hull; the interior walls below add the explicit physics we need.
	if kit.get("SM_LA_Bldg_GarageM01") is PackedScene:
		# Kit front (bay) = local +Z (TD-004). -90 deg turns +Z to world -X = WEST, onto the service
		# lane. It was +90 deg (B-LVL-02, T-BUILD-02): the bay faced the back lot and the west face
		# - door marker, mission flow, level opening - was a solid wall nobody could walk through.
		var shell := _kit_piece("SM_LA_Bldg_GarageM01", garage_pos, -PI * 0.5,
			Vector3(10.0, 4.9, 8.0), _mat(Color(0.58, 0.55, 0.50), 0.9), b)
		shell.name = "Bldg_GarageM01"
	else:
		# Greybox fallback: four walls + a roof, no solid interior.
		var shell_mat := _mat(Color(0.58, 0.55, 0.50), 0.9)
		_static_box("Bldg_GarageM01_W", Vector3(0.3, 4.9, 8.0), garage_pos + Vector3(-5.0, 2.45, 0), shell_mat, b)
		_static_box("Bldg_GarageM01_E", Vector3(0.3, 4.9, 8.0), garage_pos + Vector3(5.0, 2.45, 0), shell_mat, b)
		_static_box("Bldg_GarageM01_N", Vector3(10.0, 4.9, 0.3), garage_pos + Vector3(0, 2.45, 4.0), shell_mat, b)
		_static_box("Bldg_GarageM01_S", Vector3(10.0, 4.9, 0.3), garage_pos + Vector3(0, 2.45, -4.0), shell_mat, b)
		_static_box("Bldg_GarageM01_Roof", Vector3(10.0, 0.3, 8.0), garage_pos + Vector3(0, 4.9, 0), shell_mat, b)
	# Hollow it out visually: the interior box is drawn, the shell stays collision only.
	var walls := _mat(Color(0.52, 0.50, 0.47), 0.92)
	var g := garage_pos
	_static_box("Garage_Floor", Vector3(10.0, 0.2, 8.0), g + Vector3(0, -0.1, 0), walls, b)
	_static_box("Garage_Wall_N", Vector3(10.0, 4.6, 0.3), g + Vector3(0, 2.3, 4.0), walls, b)
	_static_box("Garage_Wall_S", Vector3(10.0, 4.6, 0.3), g + Vector3(0, 2.3, -4.0), walls, b)
	_static_box("Garage_Wall_E", Vector3(0.3, 4.6, 8.0), g + Vector3(5.0, 2.3, 0), walls, b)
	# West wall split by the 3 m roll-up door (opening at the centre of the west face)
	_static_box("Garage_Wall_W_N", Vector3(0.3, 4.6, 2.5), g + Vector3(-5.0, 2.3, 2.75), walls, b)
	_static_box("Garage_Wall_W_S", Vector3(0.3, 4.6, 2.5), g + Vector3(-5.0, 2.3, -2.75), walls, b)
	_static_box("Garage_Wall_W_Lintel", Vector3(0.3, 1.6, 3.0), g + Vector3(-5.0, 3.8, 0), walls, b)
	# North wall split by a 1.0 m personnel door at x = g.x - 2.0 (flank route, layout §5)
	_static_box("Garage_Wall_N_W", Vector3(4.0, 4.6, 0.3), g + Vector3(-3.0, 2.3, 4.0), walls, b)
	_static_box("Garage_Wall_N_E", Vector3(5.0, 4.6, 0.3), g + Vector3(2.5, 2.3, 4.0), walls, b)
	_static_box("Garage_Wall_N_Lintel", Vector3(1.0, 2.4, 0.3), g + Vector3(-2.0, 3.4, 4.0), walls, b)
	# Interior cover (layout §5)
	_static_box("Garage_Bench", Vector3(2.4, 0.95, 0.9), g + Vector3(2.5, 0.48, 2.5),
		_mat(Color(0.34, 0.24, 0.16), 0.8), b)
	_static_box("Garage_WreckCar", Vector3(1.8, 1.1, 4.2), g + Vector3(-1.0, 0.55, -2.0),
		_mat(Color(0.30, 0.32, 0.34), 0.6, 0.4), b)
	_static_box("Garage_Crate_A", Vector3(1.2, 1.2, 1.2), g + Vector3(3.5, 0.6, -1.0),
		_mat(Color(0.42, 0.34, 0.24), 0.9), b)
	_static_box("Garage_Crate_B", Vector3(1.0, 1.0, 1.0), g + Vector3(3.5, 1.7, -1.0),
		_mat(Color(0.42, 0.34, 0.24), 0.9), b)
	_static_box("Garage_Pillar_N", Vector3(0.4, 4.6, 0.4), g + Vector3(-3.0, 2.3, 3.5), walls, b)
	_static_box("Garage_Pillar_S", Vector3(0.4, 4.6, 0.4), g + Vector3(-3.0, 2.3, -1.5), walls, b)
	_static_box("Forecourt_Dumpster", Vector3(2.0, 1.3, 1.2), Vector3(X_EAST_FRONT - 2.0, 0.65, -2.0),
		_mat(Color(0.18, 0.32, 0.24), 0.8), b)
	# Cover anchors (layout §3.3 + §5 are binding: 6 x CoverPoint). They were missing - neither the
	# AI cover-lite nor a player-side check had anything to use (B-LVL-04, T-BUILD-02). Each sits
	# on the side away from the roll-up door / street, where wave 1 and 2 come from.
	var cover_script := load("res://Scripts/ai/cover_point.gd")
	var covers := {
		# Every spot keeps >= 0.6 m to walls (navmesh agent radius 0.5) - test_level checks
		# that each one sits ON the navmesh, otherwise "go to cover" routes around the building.
		"Cover_Garage_Car_L": g + Vector3(0.55, 0.16, -2.0),     # east of the wreck (x 36.1..37.9)
		"Cover_Garage_Crate_A": g + Vector3(3.5, 0.16, -2.45),   # south of the crate stack (kit bench is north)
		"Cover_Garage_Bench": g + Vector3(2.5, 0.16, 1.5),       # south of the bench
		"Cover_Garage_Pillar_N": g + Vector3(-2.4, 0.16, 3.2),
		"Cover_Garage_Pillar_S": g + Vector3(-3.0, 0.16, -2.3),  # south of the pillar, clear of the wreck
		"Cover_Forecourt_Dumpster": Vector3(X_EAST_FRONT - 2.0, 0.16, -0.8),  # north of it
	}
	for cn in covers:
		var cp := Marker3D.new()
		cp.set_script(cover_script)
		cp.name = cn
		b.add_child(cp)
		cp.position = covers[cn]


func _build_props() -> void:
	var p := Node3D.new()
	p.name = "Props"
	level.add_child(p)
	var metal := _mat(Color(0.30, 0.30, 0.32), 0.5, 0.7)
	var bark := _mat(Color(0.32, 0.26, 0.20), 0.95)
	# Streetlights + palms down the west street (2 m grid friendly spacing)
	var z := -70.0
	while z <= 70.0:
		_kit_piece("SM_LA_Streetlight", Vector3(WSIDE_W + 1.2, 0.16, z), -PI * 0.5,
			Vector3(0.3, 7.2, 0.3), metal, p)
		_kit_piece("SM_LA_PalmTree", Vector3(WSIDE_E - 1.0, 0.16, z + 10.0), 0.0,
			Vector3(0.5, 11.5, 0.5), bark, p)
		z += 20.0
	# Parked cars (cover, layer 4 is for vehicles; these are static world props)
	for entry in [[Vector3(-18.9, 0.05, -30.0), 0.0], [Vector3(-18.9, 0.05, 34.0), 0.0],
			[Vector3(19.0, 0.05, -22.0), PI]]:
		_static_box("Prop_ParkedCar", Vector3(1.9, 1.45, 4.8), entry[0] + Vector3(0, 0.72, 0),
			_mat(Color(0.35, 0.12, 0.12), 0.45, 0.5), p, entry[1])
	# Traffic light + crosswalk (north-west corner)
	_static_box("Prop_TrafficLight", Vector3(0.3, 5.6, 0.3), Vector3(-17.5, 2.8, 70.0),
		_mat(Color(0.15, 0.15, 0.16), 0.6, 0.5), p)
	for i in 4:
		# Paint, not a 2 cm kerb across the road (B-PT-01 class: micro-lips snag the player).
		_visual_box("Prop_CrosswalkStripe_%d" % i, Vector3(0.6, 0.004, 4.0),
			Vector3(WEST_X - 3.6 + i * 2.4, 0.042, 68.0), _mat(Color(0.85, 0.85, 0.83), 0.9), p)


func _build_lighting() -> void:
	var l := Node3D.new()
	l.name = "Lighting"
	level.add_child(l)
	# Golden-hour sun, matching ENV_LA_GoldenHour (look never verified on a GPU, B-003)
	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	sun.rotation_degrees = Vector3(-12, 250, 0)
	sun.light_color = Color(1.0, 0.86, 0.66)
	sun.light_energy = 1.35
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 120.0
	l.add_child(sun)
	var we := WorldEnvironment.new()
	we.name = "WorldEnvironment"
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sm := ProceduralSkyMaterial.new()
	sm.sky_top_color = Color(0.32, 0.44, 0.62)
	sm.sky_horizon_color = Color(0.92, 0.72, 0.52)
	sm.ground_horizon_color = Color(0.55, 0.45, 0.36)
	sm.sun_angle_max = 12.0
	sky.sky_material = sm
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.55
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.fog_enabled = true
	env.fog_light_color = Color(0.86, 0.74, 0.58)
	env.fog_density = 0.006
	we.environment = env
	l.add_child(we)
	# Garage sodium practicals - positioned from the garage that is actually built (it sits in
	# the east block since T-MIS-01b), not from the old hard-coded numbers.
	var gpos := Vector3(X_EAST_FRONT + 5.0, 0.0, 6.0)
	for i in 2:
		var lamp := OmniLight3D.new()
		lamp.name = "GarageLamp_%d" % i
		lamp.light_color = Color(1.0, 0.72, 0.36)
		lamp.light_energy = 2.6
		lamp.omni_range = 11.0
		lamp.position = gpos + Vector3(-2.2 if i == 0 else 2.2, 4.1, -2.0 if i == 0 else 2.0)
		l.add_child(lamp)
	# One street practical per lane end, so the road reads at night-ish exposure too.
	for zi in [-70.0, 0.0, 70.0]:
		var sl := OmniLight3D.new()
		sl.name = "StreetLamp_E_%+.0f" % zi
		sl.light_color = Color(1.0, 0.86, 0.62)
		sl.light_energy = 1.6
		sl.omni_range = 14.0
		sl.position = Vector3(WEST_X + 6.5, 5.2, zi)
		l.add_child(sl)


func _build_navmesh() -> void:
	# The block navmesh is baked at runtime from the collision geometry (T-AI-01). It is NOT a
	# flat carpet: a 150 x 190 m box would bury the 0.16 m sidewalk in the road surface.
	var nav := NavigationRegion3D.new()
	nav.name = "NavRegion_Block"
	level.add_child(nav)
	var nm := NavigationMesh.new()
	nm.cell_size = 0.25
	nm.cell_height = 0.25
	nm.agent_radius = 0.5
	nm.agent_height = 2.0
	nm.agent_max_climb = 0.25
	nm.geometry_parsed_geometry_type = NavigationMesh.PARSED_GEOMETRY_MESH_INSTANCES
	nm.geometry_source_geometry_mode = NavigationMesh.SOURCE_GEOMETRY_ROOT_NODE_CHILDREN
	nm.geometry_collision_mask = 1
	nav.navigation_mesh = nm


## Bakes the level navmesh from the real collision geometry (walkable = road AND sidewalk), so
## the polygon set ships in the scene instead of being baked by whoever opens the level.
## NavigationServer3D works headless; the region is created first, then baked into it.
func _bake_navmesh() -> void:
	var nav := level.get_node_or_null("NavRegion_Block") as NavigationRegion3D
	if nav == null:
		return
	var nm := nav.navigation_mesh
	nav.navigation_mesh = null     # do not parse the (stale) baked mesh as geometry
	var src := NavigationMeshSourceGeometryData3D.new()
	NavigationServer3D.parse_source_geometry_data(nm, src, level)
	NavigationServer3D.bake_from_source_geometry_data(nm, src)
	nav.navigation_mesh = nm
	print("[LVL] navmesh: %d polygons, %d vertices" % [nm.get_polygon_count(), nm.get_vertices().size()])


## Ambush anchors. Wave 1 activates when the player walks into Area_GarageInside, wave 2 comes
## from a van parked on the east service lane (docs/Missions/M01_DeadDrop.md beat 4).
## Positions are inside the garage / on the lane, i.e. on navmesh, never inside a wall.
func _build_spawns_and_ai() -> void:
	var ai := Node3D.new()
	ai.name = "AI"
	level.add_child(ai)
	var gunman := load("res://Scenes/NPC/PT_NPC_Gunman.tscn") as PackedScene
	var civilian := load("res://Scenes/NPC/PT_NPC_Civilian.tscn") as PackedScene
	var garage := Vector3(X_EAST_FRONT + 5.0, 0.16, 6.0)
	var markers := {
		# Layout §5 (binding): "the AI never spawns behind the player's back inside the garage
		# (wave 1 comes from the street)". They used to stand INSIDE the garage, 2-4 m from the
		# door: Jason died 1.3 s after walking in (B-LVL-03, T-BUILD-02). Now: east service lane
		# and the far sidewalk, 12-20 m from the door, so the player has the interior cover.
		"Spawn_Wave1_A": Vector3(EAST_X - 1.0, 0.16, 22.0),
		"Spawn_Wave1_B": Vector3(EAST_X + 2.0, 0.16, -6.0),
		"Spawn_Wave1_C": Vector3(ESIDE_W, 0.16, 12.0),
		"Spawn_Wave2_Van": Vector3(EAST_X, 0.16, -8.0),
		# On the garage ROOF above the door (layout §3.3 "rooftop"). It was (EAST_X + 1, 4.9, 2):
		# in mid-air over the service lane - the gunman dropped onto Jason's parked car roof
		# (B-LVL-05, T-BUILD-02).
		"Spawn_Wave2_Roof": garage + Vector3(-3.5, 4.95, -1.5),
	}
	for k in markers:
		var m := Marker3D.new()
		m.name = k
		m.position = markers[k]
		ai.add_child(m)
	# Civilian routes down the west sidewalks (T-AI-02). The outer sidewalk is x = -31,
	# the inner one x = -17; both are clear of the new building line at x = -33.
	var routes := Node3D.new()
	routes.name = "Routes"
	ai.add_child(routes)
	var route_a := Node3D.new()
	route_a.name = "Route_WestSidewalk"
	route_a.set_script(load("res://Scripts/ai/npc_route.gd"))
	routes.add_child(route_a)
	# T-LVL-01a: the route stays on the OUTER west sidewalk. The old route crossed the road at
	# z = 40 - a pedestrian standing in the lane is a solid 0.56 m obstacle that stops the player's
	# sedan dead with no feedback, and there is no traffic logic that would justify the crossing.
	var pts := [Vector3(-31.0, 0.16, -60.0), Vector3(-31.0, 0.16, -20.0),
		Vector3(-31.0, 0.16, 20.0), Vector3(-31.0, 0.16, 60.0)]
	for i in pts.size():
		var p := Marker3D.new()
		p.name = "P%d" % i
		p.position = pts[i]
		route_a.add_child(p)
	if civilian != null:
		# Spawn them 6 m off the road: a pedestrian standing on the kerb line is a 0.56 m
		# obstacle that stops the sedan dead (measured in the T-LVL-01a drive test).
		for i in 3:
			var c := civilian.instantiate()
			c.name = "Civilian_%d" % (i + 1)
			var spawn: Vector3 = pts[i % pts.size()]
			var lane_x := -17.0 if absf(spawn.x - (-17.0)) < absf(spawn.x - (-31.0)) else -31.0
			c.position = Vector3(spawn.x + (1.4 if spawn.x > lane_x else -1.4), spawn.y, spawn.z)
			c.set("route_path", NodePath("../Routes/Route_WestSidewalk"))
			c.set("route_start_index", i % pts.size())
			ai.add_child(c)
	# Five gunmen for M01. Wave 2 is built but starts inactive (see MissionEnemy): before the
	# ambush nobody perceives, shoots or is drawn.
	if gunman != null:
		var wave1 := [markers["Spawn_Wave1_A"], markers["Spawn_Wave1_B"], markers["Spawn_Wave1_C"]]
		for i in wave1.size():
			var g := gunman.instantiate()
			g.name = "Enemy_Wave1_%d" % (i + 1)
			g.position = wave1[i]
			# persistent=true: only persistent groups are written into the .tscn by
			# PackedScene.pack(), otherwise the saved level has no mission_enemies group.
			g.set("wave", 1)
			g.set("active", false)
			g.add_to_group("mission_enemies", true)
			g.add_to_group("wave1", true)
			ai.add_child(g)
		var wave2 := [markers["Spawn_Wave2_Van"], markers["Spawn_Wave2_Roof"]]
		for i in wave2.size():
			var g2 := gunman.instantiate()
			g2.name = "Enemy_Wave2_%d" % (i + 1)
			g2.position = wave2[i]
			g2.set("wave", 2)
			g2.set("active", false)
			g2.add_to_group("mission_enemies", true)
			g2.add_to_group("wave2", true)
			ai.add_child(g2)


## Mission anchors. NAMES are binding (Docs/Missions/M01_DeadDrop.md, test_mission.gd);
## the world positions follow the geometry: the garage now sits at x = +38 (east block
## behind the east sidewalk), so the forecourt Area_GarageArrival moved from x = +16 to the
## lane in front of the roll-up door, and the package moved onto the garage bench.
func _build_mission_anchors() -> void:
	var m := Node3D.new()
	m.name = "Mission"
	level.add_child(m)
	var garage_door := Vector3(X_EAST_FRONT - 0.2, 0.16, 6.0)
	# Player spawn + start car: on the west lane, facing north along the drive loop.
	var spawn := Marker3D.new()
	spawn.name = "PlayerSpawn"
	spawn.position = Vector3(WEST_X, 0.2, -78.0)
	m.add_child(spawn)
	var car := Marker3D.new()
	car.name = "CarSpawn"
	car.position = Vector3(WEST_X, 0.1, -72.0)
	m.add_child(car)
	# Marco's seat marker: next to the car's passenger side, BEFORE he boards (test reads it).
	var seat := Marker3D.new()
	seat.name = "Marco_Seat"
	seat.position = Vector3(WEST_X - 1.6, 0.2, -72.0)
	m.add_child(seat)
	# Trigger areas with the exact M01 names
	_area("Area_GarageArrival", garage_door + Vector3(-6.0, 0.0, 0.0), 8.0, true)
	_area_box("Area_GarageInside", Vector3(X_EAST_FRONT + 5.0, 1.5, 6.0), Vector3(10.0, 3.0, 8.0))
	_area_box("Area_Warehouse", Vector3(X_EAST_FRONT - 3.0, 3.0, 78.0), Vector3(12.0, 6.0, 10.0))
	var door := Marker3D.new()
	door.name = "Marker_GarageDoor"
	door.position = garage_door
	m.add_child(door)
	# Package: crate + interactable + 200 HP (M01 step 5), on the garage bench
	var pkg := Node3D.new()
	pkg.name = "Pickup_Package"
	pkg.set_script(load("res://Scripts/mission/carried_item.gd"))
	pkg.position = Vector3(X_EAST_FRONT + 7.5, 1.35, 8.5)
	pkg.add_to_group("interactables", true)
	m.add_child(pkg)
	var crate: Node3D = null
	if kit["SM_Prop_PackageCrate"] != null:
		crate = (kit["SM_Prop_PackageCrate"] as PackedScene).instantiate()
	else:
		var mi := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = Vector3(0.61, 0.41, 0.41)
		mi.mesh = bm
		mi.material_override = _mat(Color(0.45, 0.36, 0.24), 0.9)
		crate = mi
	crate.name = "CrateMesh"
	pkg.add_child(crate)
	var inter := Area3D.new()
	inter.name = "Interact"
	inter.set_script(load("res://Scripts/mission/interactable.gd"))
	inter.set("prompt", "Pick up the package")
	pkg.add_child(inter)
	var ics := CollisionShape3D.new()
	var ibox := BoxShape3D.new()
	ibox.size = Vector3(1.2, 1.2, 1.2)
	ics.shape = ibox
	inter.add_child(ics)
	var health := Node.new()
	health.name = "DamageReceiver"
	health.set_script(load("res://Scripts/combat/damage_receiver.gd"))
	health.set("max_health", 200.0)
	pkg.add_child(health)
	# Player + car instances placed in the level (tests and the game both use these)
	var player_scene := load("res://Scenes/Player/Player.tscn") as PackedScene
	if player_scene != null:
		var pl := player_scene.instantiate()
		pl.name = "Player"
		pl.position = spawn.position
		level.add_child(pl)
	var car_scene := load("res://Scenes/Vehicles/VH_Sedan_01.tscn") as PackedScene
	if car_scene != null:
		var c := car_scene.instantiate()
		c.name = "VH_Sedan_01"
		c.position = car.position
		level.add_child(c)
	# Marco, the ally (T-MIS-01b): stands next to the car at mission start and is put on the
	# passenger seat by MissionManager.start(). He is an AllyCompanion, not a mission enemy.
	var marco_scene := load("res://Scenes/NPC/Ally_Marco.tscn") as PackedScene
	if marco_scene != null:
		var marco := marco_scene.instantiate()
		marco.name = "Ally_Marco"
		marco.position = seat.position
		ai_root().add_child(marco)
	# HUD (T-UI-01) - CanvasLayer, builds its Control tree in code
	var hud := CanvasLayer.new()
	hud.name = "HUD"
	hud.set_script(load("res://Scripts/ui/hud.gd"))
	level.add_child(hud)
	# Mission manager with M01 data
	var mm := Node.new()
	mm.name = "MissionManager"
	mm.set_script(load("res://Scripts/mission/mission_manager.gd"))
	mm.set("level_root", NodePath(".."))
	var mdata := load("res://Data/Missions/M01_DeadDrop.tres")
	if mdata != null:
		mm.set("mission", mdata)
	level.add_child(mm)


func _area(name: String, pos: Vector3, radius: float, is_sphere: bool) -> Area3D:
	var a := Area3D.new()
	a.name = name
	a.position = pos
	a.collision_layer = 0
	a.collision_mask = (1 << 1) | (1 << 3)   # Player | Vehicles
	a.monitoring = true
	var cs := CollisionShape3D.new()
	if is_sphere:
		var sp := SphereShape3D.new()
		sp.radius = radius
		cs.shape = sp
	else:
		var bx := BoxShape3D.new()
		bx.size = Vector3(radius, radius, radius)
		cs.shape = bx
	a.add_child(cs)
	_mission_root().add_child(a)
	return a


func _area_box(name: String, pos: Vector3, size: Vector3) -> Area3D:
	var a := Area3D.new()
	a.name = name
	a.position = pos
	a.collision_layer = 0
	a.collision_mask = (1 << 1) | (1 << 3)
	a.monitoring = true
	var cs := CollisionShape3D.new()
	var bx := BoxShape3D.new()
	bx.size = size
	cs.shape = bx
	a.add_child(cs)
	_mission_root().add_child(a)
	return a


func ai_root() -> Node3D:
	var n := level.get_node_or_null("AI") as Node3D
	if n == null:
		n = Node3D.new()
		n.name = "AI"
		level.add_child(n)
	return n


func _mission_root() -> Node3D:
	var n := level.get_node_or_null("Mission") as Node3D
	if n == null:
		n = Node3D.new()
		n.name = "Mission"
		level.add_child(n)
	return n


func _save() -> void:
	# PackedScene only serialises nodes whose owner is the scene root, and the root itself
	# must already carry its final name (set in _initialize). Without this every child is
	# dropped and the .tscn saves as a single empty node.
	level.name = "LA_CallowayAve"
	_name_children(level)
	_own_all(level, level)
	var packed := PackedScene.new()
	var err := packed.pack(level)
	if err != OK:
		push_error("pack failed: %d" % err)
		quit(1)
		return
	err = ResourceSaver.save(packed, OUT)
	print("[LVL] saved %s (%d nodes) err=%d" % [OUT, _count(level), err])
	if err != OK:
		quit(1)


## Every node we create gets a speaking name from its role - a "Props" child that comes out of
## the scene as "@StaticBody3D@3" is exactly the debugging trap T-LVL-01a is about.
func _name_children(n: Node) -> void:
	for c in n.get_children():
		if String(c.name).begins_with("@"):
			var base := String(c.name).trim_prefix("@").split("@")[0]
			c.name = {"StaticBody3D": "Prop", "CollisionShape3D": "Collision", "Node3D": "Node"}.get(base, base)
		_name_children(c)


## Give every node of *our own* hierarchy an owner so PackedScene.pack() keeps it.
##
## Nodes that belong to an instanced sub-scene (kit pieces, Player.tscn, the sedan, NPC
## scenes) must keep owner == null for their internal nodes: owning them makes Godot serialise
## a full copy of the sub-scene into the level instead of an instance reference, and every later
## edit to that sub-scene (e.g. adding the real SK_NPC character model) would never reach the
## level. Instances whose own root we placed stay instances; only nodes we created in *this*
## script are owned.
func _own_all(n: Node, owner_node: Node) -> void:
	for c in n.get_children():
		c.owner = owner_node
		# Do not descend into an instanced sub-scene: owning its internal nodes makes Godot
		# write a full copy of that scene into the level instead of an instance reference.
		if c.scene_file_path == "":
			_own_all(c, owner_node)


func _count(n: Node) -> int:
	var c := 1
	for ch in n.get_children():
		c += _count(ch)
	return c
