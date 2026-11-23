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
			if props.has(String(k)):
				wd.set(String(k), w[k])
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
	return true

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
