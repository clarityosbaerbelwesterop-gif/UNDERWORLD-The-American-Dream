# UNDERWORLD - combat database loader (P1, T-DATA-01).
#
# Data/Content/combat.json is THE single source for weapons, armor, NPC archetypes (civilian,
# enemy light/medium/heavy, boss, police, FBI, ally) and faction rosters. Nothing here holds numbers
# of its own: WeaponData, AIProfile and armor are built from the JSON, so a designer changes one
# file and every NPC, test and tool follows.
class_name CombatDB
extends RefCounted

const PATH := "res://Data/Content/combat.json"

static var _db: Dictionary = {}
static var _weapon_cache: Dictionary = {}

static func data() -> Dictionary:
	if _db.is_empty():
		var f := FileAccess.open(PATH, FileAccess.READ)
		if f == null:
			push_error("CombatDB: cannot open %s" % PATH)
			return {}
		var parsed = JSON.parse_string(f.get_as_text())
		if parsed is Dictionary:
			_db = parsed
	return _db

static func weapon_ids() -> Array:
	return (data().get("weapons", {}) as Dictionary).keys()

static func archetype_ids() -> Array:
	return (data().get("archetypes", {}) as Dictionary).keys().filter(func(k): return not String(k).begins_with("_"))

static func archetype(id: String) -> Dictionary:
	return (data().get("archetypes", {}) as Dictionary).get(id, {})

static func armor_def(id: String) -> Dictionary:
	return (data().get("armor", {}) as Dictionary).get(id, {})

## WeaponData built from the JSON entry. Keys that are WeaponData properties are copied verbatim
## (fire_mode, rpm, damage, falloff_*, magazine_size, ...). Cached per id; callers get a duplicate.
static func weapon(id: String) -> WeaponData:
	if not _weapon_cache.has(id):
		var w: Dictionary = (data().get("weapons", {}) as Dictionary).get(id, {})
		if w.is_empty():
			return null
		var wd := WeaponData.new()
		wd.id = id
		var props := {}
		for p in wd.get_property_list():
			props[String(p["name"])] = true
		for k in w:
			if props.has(String(k)) and String(k) != "scene":
				wd.set(String(k), w[k])
		# visual: the weapon-grammar .glb (T-WPN-01) - SOCKET_Muzzle, Magazine, Fire/Reload clips
		var sp := String(w.get("scene", ""))
		if sp != "" and ResourceLoader.exists(sp):
			wd.scene = load(sp) as PackedScene
		_weapon_cache[id] = wd
	return (_weapon_cache[id] as WeaponData).duplicate()

## Armor pieces for DamageReceiver.set_armor() from an archetype's armor id list.
static func armor_for(arch_id: String) -> Array:
	var out: Array = []
	for aid in archetype(arch_id).get("armor", []):
		var a := armor_def(String(aid))
		if not a.is_empty():
			out.append({"id": aid, "zone": int(a["zone"]), "absorb": float(a["absorb"]), "points": float(a["points"])})
	return out

## AIProfile for an archetype: its base profile with the archetype's combat values on top.
static func profile(arch_id: String) -> AIProfile:
	var a := archetype(arch_id)
	if a.is_empty():
		return null
	var base := load("res://Data/AI/%s.tres" % String(a.get("base_profile", "AI_Gunman_Cartel"))) as AIProfile
	if base == null:
		return null
	var p := base.duplicate(true) as AIProfile
	p.id = "AI_%s" % arch_id
	p.max_health = float(a.get("max_health", p.max_health))
	if a.has("aim_error_deg") and float(a["aim_error_deg"]) > 0.0:
		p.aim_error_deg = float(a["aim_error_deg"])
	if a.has("reaction_time"):
		p.reaction_time = float(a["reaction_time"])
	var burst: Array = a.get("burst", [])
	if burst.size() == 2 and int(burst[1]) > 0:
		p.burst_min = int(burst[0])
		p.burst_max = int(burst[1])
	if a.has("use_cover"):
		p.use_cover = bool(a["use_cover"])
	var weapons: Array = a.get("weapons", [])
	if not weapons.is_empty():
		p.weapon = weapon(String(weapons[0]))
	return p

## Turns any NPCController into the archetype: profile values, health and armor. Call before the
## NPC enters the tree (or right after, before its first physics frame).
static func apply(npc: NPCController, arch_id: String) -> bool:
	var p := profile(arch_id)
	if p == null:
		return false
	npc.profile = p
	var hp := npc.get_node_or_null("Health") as DamageReceiver
	if hp != null:
		hp.max_health = p.max_health
		hp.reset()
		hp.set_armor(armor_for(arch_id))
	npc.set_meta(&"archetype", arch_id)
	# Visible armor (T-CHAR-01): the archetype's vest/helmet props ride on the skeleton, so the
	# player reads the tier before the first shot. Needs the visual -> after the NPC's _ready.
	if not armor_for(arch_id).is_empty():
		if npc.is_node_ready():
			attach_armor_visuals(npc, arch_id)
		else:
			npc.ready.connect(attach_armor_visuals.bind(npc, arch_id), CONNECT_ONE_SHOT)
	return true

## Attaches the archetype's armor props (combat.json armor.<id>.asset) to the NPC skeleton:
## vests on Chest (bottom at the hips, scaled to the shoulder width), helmets on Head. The props'
## pickup collision is stripped - only the hitboxes take shots. Returns the attachments made.
static func attach_armor_visuals(npc: NPCController, arch_id: String) -> Array:
	var made: Array = []
	if npc.visual == null:
		return made
	var skel := npc.visual.find_skeleton()
	if skel == null:
		return made
	var hips := skel.find_bone("Hips")
	var head := skel.find_bone("Head")
	var lua := skel.find_bone("LeftUpperArm")
	var rua := skel.find_bone("RightUpperArm")
	for aid in archetype(arch_id).get("armor", []):
		var a := armor_def(String(aid))
		var asset := String(a.get("asset", ""))
		var path := "res://Assets/Props/%s/%s.glb" % [asset, asset]
		if asset == "" or not ResourceLoader.exists(path):
			continue
		var is_head := int(a.get("zone", 0)) == 1
		var bone_name := "Head" if is_head else "Chest"
		var bone := skel.find_bone(bone_name)
		if bone < 0 or hips < 0:
			continue
		var att := BoneAttachment3D.new()
		att.name = "Armor_%s" % aid
		att.bone_name = bone_name
		skel.add_child(att)
		var m := (load(path) as PackedScene).instantiate() as Node3D
		for body in m.find_children("*", "CollisionObject3D", true, false):
			body.get_parent().remove_child(body)
			body.free()
		var want := Transform3D.IDENTITY                      # in skeleton space, front +Z
		if is_head:
			want.origin = skel.get_bone_global_rest(head).origin + Vector3(0, -0.02, 0.0)
		else:
			var sc := 1.0
			if lua >= 0 and rua >= 0:
				var w := skel.get_bone_global_rest(lua).origin.distance_to(skel.get_bone_global_rest(rua).origin)
				sc = clampf(w / 0.30, 0.9, 1.3)
			want = Transform3D(Basis.IDENTITY.scaled(Vector3(sc, 1.0, sc)), skel.get_bone_global_rest(hips).origin + Vector3(0, 0.04, 0.0))
		m.transform = skel.get_bone_global_rest(bone).affine_inverse() * want
		att.add_child(m)
		made.append(att)
	return made

## Pistol body hits needed to kill an archetype (<= falloff_start, no headshots) - the TTK the
## design_targets bands are written in. Simulates the real DamageReceiver, armor included.
static func pistol_hits_to_kill(arch_id: String) -> int:
	var a := archetype(arch_id)
	var hp := DamageReceiver.new()
	hp.max_health = float(a.get("max_health", 100.0))
	hp.reset()
	hp.set_armor(armor_for(arch_id))
	var pistol := weapon("WPN_Pistol_01")
	var n := 0
	while not hp.is_dead and n < 500:
		var info := DamageInfo.new()
		info.amount = pistol.damage
		info.zone = 0
		info.armor_penetration = pistol.armor_penetration
		hp.apply_damage(info)
		n += 1
	hp.free()
	return n
