# UNDERWORLD - shader/material pass (T-LOOK-02). glTF cannot carry everything the look needs
# (Blender's coat layer never arrives, SSS has no glTF slot), so imported StandardMaterial3Ds
# are upgraded by NAME (TD-005 M_<asset>_<role>) right after a model is instanced:
#   *_Paint / *_DoorPaint / *_Stripe   car paint: clear coat over the metallic base
#   *_Skin                             skin: subsurface scattering (skin mode) + soft rim
#   *_Eyes                             wet cornea: clear coat
#   cloth (*_Jacket/_TShirt/_Jeans/_Suit/_Hoodie/_Shirt/_Pants/_Interior/...)   fabric sheen (rim)
#   *_Hair                             anisotropic highlight
# set_wetness() darkens + smooths asphalt / concrete / road paint for rain (NY).
# Every upgrade is idempotent (materials are shared resources: one upgrade serves all instances).
class_name MaterialPass
extends RefCounted

const CLOTH := ["_Jacket", "_TShirt", "_Jeans", "_Suit", "_Hoodie", "_Shirt", "_Pants", "_Trousers",
	"_Coat", "_Vest", "_Interior", "_Dress", "_Skirt", "_Sweater", "_Cap", "_Beanie"]
const WET_KEYS := ["asphalt", "concrete", "road", "sidewalk", "kerb", "curb", "pavement"]

## Upgrades every StandardMaterial3D under `root` (surface + override materials). Returns the
## number of materials touched by a rule. UW_LOOK_SABOTAGE=1 (debug) disables it (negative control).
static func apply(root: Node) -> int:
	if root == null or _sabotaged():
		return 0
	var n := 0
	for m in _materials(root):
		if _upgrade(m):
			n += 1
	return n


static func _sabotaged() -> bool:
	return OS.is_debug_build() and OS.get_environment("UW_LOOK_SABOTAGE").strip_edges() == "1"


static func _materials(root: Node) -> Array:
	var out: Array = []
	var seen := {}
	var nodes: Array = [root]
	nodes.append_array(root.find_children("*", "GeometryInstance3D", true, false))
	for c in nodes:
		var mats: Array = []
		if c is MeshInstance3D:
			var mi := c as MeshInstance3D
			if mi.mesh != null:
				for si in mi.mesh.get_surface_count():
					mats.append(mi.get_active_material(si))
		if c is GeometryInstance3D and (c as GeometryInstance3D).material_override != null:
			mats.append((c as GeometryInstance3D).material_override)
		for m in mats:
			if m is StandardMaterial3D and not seen.has(m):
				seen[m] = true
				out.append(m)
	return out


static func _upgrade(m: StandardMaterial3D) -> bool:
	var nm := m.resource_name
	if nm.ends_with("_Paint") or nm.ends_with("_DoorPaint") or nm.ends_with("_Stripe"):
		m.clearcoat_enabled = true
		m.clearcoat = 0.9
		m.clearcoat_roughness = 0.06
		m.roughness = clampf(m.roughness, 0.28, 0.45)      # base coat under the lacquer
		return true
	if nm.ends_with("_Skin"):
		m.subsurf_scatter_enabled = true
		m.subsurf_scatter_skin_mode = true
		m.subsurf_scatter_strength = 0.35
		m.rim_enabled = true
		m.rim = 0.18
		m.rim_tint = 0.75
		return true
	if nm.ends_with("_Eyes"):
		m.clearcoat_enabled = true
		m.clearcoat = 1.0
		m.clearcoat_roughness = 0.02
		return true
	if nm.ends_with("_Hair") or nm.ends_with("_Beard"):
		m.anisotropy_enabled = true
		m.anisotropy = 0.45
		return true
	for k in CLOTH:
		if nm.ends_with(k):
			m.rim_enabled = true
			m.rim = 0.28
			m.rim_tint = 0.55
			return true
	return false


## Rain (NY chapter): asphalt / concrete / road paint get darker and glossy. `amount` 0..1.
## The dry values are remembered in metadata, so wetness can go back to 0.
static func set_wetness(root: Node, amount: float) -> int:
	if root == null or _sabotaged():
		return 0
	amount = clampf(amount, 0.0, 1.0)
	var n := 0
	for m in _materials(root):
		var low := (m as StandardMaterial3D).resource_name.to_lower()
		var hit := false
		for k in WET_KEYS:
			if low.contains(k):
				hit = true
				break
		if not hit:
			continue
		var mat := m as StandardMaterial3D
		if not mat.has_meta("uw_dry"):
			mat.set_meta("uw_dry", [mat.roughness, mat.albedo_color, mat.metallic_specular])
		var dry: Array = mat.get_meta("uw_dry")
		mat.roughness = lerpf(float(dry[0]), 0.08, amount)
		mat.albedo_color = (dry[1] as Color).darkened(0.45 * amount)
		mat.metallic_specular = lerpf(float(dry[2]), 0.7, amount)
		if mat.roughness_texture != null:
			# a roughness map would override the scalar: scale it down instead (wet film)
			mat.roughness = lerpf(float(dry[0]), 0.15, amount)
		n += 1
	return n
