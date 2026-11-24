extends SceneTree
## P1 / T-DATA-01 - the combat database (Data/Content/combat.json) and the armor system.
##   * every reference resolves (weapons, armor, base profiles, faction rosters)
##   * tiers are ordered (civilian < light < medium < heavy < boss)
##   * time-to-kill with the pistol lies in the design_targets bands (armor simulated for real)
##   * armor: covered zone only, penetration, depletion, reset
##   * CombatDB.apply() turns a real NPC into an archetype
##   * the shipped WPN_Pistol_01.tres agrees with the database (one source of truth)
## Negative control: UW_COMBAT_SABOTAGE=1 switches armor off -> armor + TTK checks fail.

var failures: PackedStringArray = []

func check(cond: bool, msg: String) -> void:
	if cond:
		print("[GPTEST][PASS] ", msg)
	else:
		print("[GPTEST][FAIL] ", msg)
		failures.append(msg)

func _initialize() -> void:
	_run()

func _run() -> void:
	print("[GPTEST] == combat database + armor (P1)")
	var db := CombatDB.data()
	check(not db.is_empty(), "combat.json loads")
	test_references(db)
	test_tiers()
	test_ttk(db)
	test_armor()
	test_pistol_matches_shipped()
	test_weapon_assets(db)
	await test_apply_to_npc()
	if failures.is_empty():
		print("[GPTEST] RESULT: PASS")
		quit(0)
	else:
		print("[GPTEST] RESULT: FAIL (%d)" % failures.size())
		for f in failures:
			print("[GPTEST]   - ", f)
		quit(1)

func test_references(db: Dictionary) -> void:
	var weapons: Dictionary = db.get("weapons", {})
	check(weapons.size() >= 10, "weapon catalogue has >= 10 weapons (%d)" % weapons.size())
	var bad := []
	for aid in CombatDB.archetype_ids():
		var a := CombatDB.archetype(aid)
		for w in a.get("weapons", []):
			if not weapons.has(w):
				bad.append("%s->%s" % [aid, w])
		for ar in a.get("armor", []):
			if CombatDB.armor_def(String(ar)).is_empty():
				bad.append("%s->armor %s" % [aid, ar])
		if not ResourceLoader.exists("res://Data/AI/%s.tres" % String(a.get("base_profile", ""))):
			bad.append("%s->profile %s" % [aid, a.get("base_profile")])
	for fid in (db.get("factions", {}) as Dictionary):
		for arch in ((db["factions"][fid] as Dictionary).get("roster", {}) as Dictionary):
			if CombatDB.archetype(String(arch)).is_empty():
				bad.append("%s roster->%s" % [fid, arch])
	check(bad.is_empty(), "every weapon/armor/profile/roster reference resolves %s" % str(bad))
	for wid in weapons:
		var wd := CombatDB.weapon(wid)
		check(wd != null and wd.id == wid and wd.damage > 0.0, "%s builds a WeaponData (damage %.0f)" % [wid, wd.damage if wd else -1.0])

func test_tiers() -> void:
	var order := ["civilian", "enemy_light", "enemy_medium", "enemy_heavy", "boss"]
	var prev := 0.0
	var ok := true
	for t in order:
		var hp := float(CombatDB.archetype(t).get("max_health", 0))
		if hp <= prev:
			ok = false
		prev = hp
	check(ok, "health rises with the tier (civilian < light < medium < heavy < boss)")
	var e_light := float(CombatDB.archetype("enemy_light")["aim_error_deg"])
	var e_heavy := float(CombatDB.archetype("enemy_heavy")["aim_error_deg"])
	var e_boss := float(CombatDB.archetype("boss")["aim_error_deg"])
	check(e_light > e_heavy and e_heavy > e_boss, "accuracy rises with the tier (aim error %.1f > %.1f > %.1f)" % [e_light, e_heavy, e_boss])
	check((CombatDB.archetype("boss").get("phases", []) as Array).size() >= 2, "the boss has >= 2 phases")

func test_ttk(db: Dictionary) -> void:
	var bands: Dictionary = (db.get("design_targets", {}) as Dictionary).get("pistol_body_hits_to_kill", {})
	for arch in bands:
		var b: Array = bands[arch]
		var n := CombatDB.pistol_hits_to_kill(String(arch))
		check(n >= int(b[0]) and n <= int(b[1]), "%s dies to %d pistol body hits (band %d-%d)" % [arch, n, int(b[0]), int(b[1])])

func test_armor() -> void:
	var hp := DamageReceiver.new()
	hp.max_health = 100.0
	hp.reset()
	hp.set_armor([{"id": "vest", "zone": 0, "absorb": 0.5, "points": 20.0}, {"id": "helmet", "zone": 1, "absorb": 0.6, "points": 10.0}])
	var body := _hit(hp, 20.0, 0, 0.0)
	check(is_equal_approx(body.absorbed, 10.0) and is_equal_approx(hp.health, 90.0), "vest absorbs half of a body hit (health %.1f, absorbed %.1f)" % [hp.health, body.absorbed])
	var limb := _hit(hp, 20.0, 2, 0.0)
	check(is_zero_approx(limb.absorbed) and is_equal_approx(hp.health, 70.0), "limbs are not armored (health %.1f)" % hp.health)
	var pen := _hit(hp, 10.0, 0, 0.5)
	check(is_equal_approx(pen.absorbed, 2.5), "armor penetration 0.5 halves the absorption (absorbed %.2f)" % pen.absorbed)
	_hit(hp, 40.0, 0, 0.0)   # vest has 7.5 left -> takes 7.5
	var after := _hit(hp, 10.0, 0, 0.0)
	check(is_zero_approx(after.absorbed), "a depleted vest absorbs nothing")
	var head := _hit(hp, 10.0, 1, 0.0)
	check(is_equal_approx(head.absorbed, 6.0), "the helmet covers head hits (absorbed %.1f)" % head.absorbed)
	hp.reset()
	check(is_equal_approx(hp.armor_points(), hp.armor_max_points()) and hp.armor_points() > 0.0, "reset restores armor (%.1f)" % hp.armor_points())
	hp.free()

func _hit(hp: DamageReceiver, amount: float, zone: int, pen: float) -> DamageInfo:
	var i := DamageInfo.new()
	i.amount = amount
	i.zone = zone
	i.armor_penetration = pen
	hp.apply_damage(i)
	return i

func test_pistol_matches_shipped() -> void:
	var shipped := load("res://Data/Weapons/WPN_Pistol_01.tres") as WeaponData
	var db := CombatDB.weapon("WPN_Pistol_01")
	var same := shipped != null and db != null and shipped.damage == db.damage and shipped.rpm == db.rpm \
		and shipped.magazine_size == db.magazine_size and shipped.reload_time == db.reload_time \
		and shipped.headshot_multiplier == db.headshot_multiplier
	check(same, "shipped WPN_Pistol_01.tres agrees with combat.json (damage/rpm/mag/reload/headshot)")

func test_apply_to_npc() -> void:
	var ps := load("res://Scenes/NPC/PT_NPC_Gunman.tscn") as PackedScene
	var npc := ps.instantiate() as NPCController
	check(CombatDB.apply(npc, "enemy_heavy"), "CombatDB.apply(enemy_heavy) on a real gunman")
	root.add_child(npc)
	for i in 3:
		await physics_frame
	var hp := npc.get_node("Health") as DamageReceiver
	check(is_equal_approx(hp.max_health, 150.0) and is_equal_approx(hp.health, 150.0), "heavy gunman has 150 HP (%.0f)" % hp.health)
	check(hp.armor_pieces.size() == 2 and hp.armor_points() > 150.0, "heavy gunman wears vest + helmet (%.0f armor)" % hp.armor_points())
	check(npc.profile.weapon != null and npc.profile.weapon.id == "WPN_Rifle_01", "heavy gunman carries the rifle")
	var i := DamageInfo.new()
	i.amount = 25.0
	i.zone = 0
	i.armor_penetration = 0.1
	hp.apply_damage(i)
	check(hp.health > 125.0 and hp.health < 140.0, "a 25-damage pistol body hit costs the heavy %.1f HP, not 25" % (150.0 - hp.health))
	npc.queue_free()
	await physics_frame

## T-WPN-01: every combat.json weapon with a `scene` resolves to its weapon-grammar asset and keeps
## the REQ-GP02 contract: SOCKET_Muzzle in front (+Z) of the grip origin, firearms have a
## Magazine node and Fire/Reload/Empty clips, and the Reload clip is exactly as long as the
## gameplay reload_time (animation and gameplay cannot drift apart).
func test_weapon_assets(db: Dictionary) -> void:
	var firearms := ["pistol", "smg", "shotgun", "rifle", "sniper"]
	var n := 0
	for wid in (db.get("weapons", {}) as Dictionary):
		var w: Dictionary = db["weapons"][wid]
		if not w.has("scene"):
			continue
		n += 1
		var wd := CombatDB.weapon(wid)
		check(wd.scene != null, "%s: WeaponData.scene loaded from %s" % [wid, w["scene"]])
		if wd.scene == null:
			continue
		var inst := wd.scene.instantiate() as Node3D
		var muzzle := _find(inst, "SOCKET_Muzzle") as Node3D
		var fwd := muzzle.position.z if muzzle else -1.0
		var is_gun := String(w.get("class", "")) in firearms
		check(muzzle != null and fwd >= (0.15 if is_gun else 0.0), "%s: SOCKET_Muzzle %.3f m in front of the grip" % [wid, fwd])
		if is_gun:
			check(_find(inst, "Magazine") != null, "%s: Magazine node present" % wid)
			var ap := _find_class(inst, "AnimationPlayer") as AnimationPlayer
			var ok := ap != null
			for clip in ["Fire", "Reload", "Empty"]:
				ok = ok and ap.has_animation("A_%s_%s" % [wid, clip])
			check(ok, "%s: clips A_%s_Fire/Reload/Empty" % [wid, wid])
			if ok:
				var rl := ap.get_animation("A_%s_Reload" % wid).length
				var want := float(w.get("reload_time", 0.0))
				check(not _reload_mismatch(rl, want), "%s: Reload clip %.2f s == reload_time %.2f s" % [wid, rl, want])
				check(_reload_mismatch(rl, want + 0.5), "%s: the reload check bites (+0.5 s would fail)" % wid)
		inst.free()
	check(n >= 9, "combat.json links %d weapons to built assets (>= 9)" % n)

func _reload_mismatch(clip_len: float, reload_time: float) -> bool:
	return absf(clip_len - reload_time) > 1.0 / 30.0 + 0.001

func _find(n: Node, nm: String) -> Node:
	if String(n.name) == nm:
		return n
	for c in n.get_children():
		var r := _find(c, nm)
		if r != null:
			return r
	return null

func _find_class(n: Node, cls: String) -> Node:
	if n.is_class(cls):
		return n
	for c in n.get_children():
		var r := _find_class(c, cls)
		if r != null:
			return r
	return null
