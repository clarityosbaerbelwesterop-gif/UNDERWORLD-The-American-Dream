extends SceneTree
## P4 (T-CHAR-01) - line-up of the combat archetypes IN ENGINE (Forward Plus): one real NPC per
## tier (civilian, enemy light/medium/heavy, boss), CombatDB.apply() on each, so weapons, worn
## armor and the faction's roster model show exactly what the game spawns.
##
##   UW_CAPTURE_DIR=/abs/dir UW_FACTION=los_cuervos Tools/godot_phase8_capture.sh --renderer fwdplus \
##       --res 1280x720 --script res://Tests/tools/capture_archetypes.gd
## Writes lineup_<faction>.png (front 3/4) - look only, never performance.

const SUN := preload("res://Scripts/game/sun_preset.gd")
const NPC := "res://Scenes/NPC/PT_NPC_Gunman.tscn"
const TIERS := ["civilian", "enemy_light", "enemy_medium", "enemy_heavy", "boss"]

func _initialize() -> void:
	_run()

func frames(n: int) -> void:
	for i in n:
		await process_frame

func _model_for(faction: String, arch: String) -> PackedScene:
	var f: Dictionary = (CombatDB.data().get("factions", {}) as Dictionary).get(faction, {})
	var ids: Array = (f.get("roster", {}) as Dictionary).get(arch, [])
	if arch == "civilian":
		ids = ((CombatDB.data()["factions"]["civilians"] as Dictionary)["roster"] as Dictionary).get("civilian", [])
	for id in ids:
		var p := "res://Assets/Characters/%s/%s.glb" % [id, id]
		if ResourceLoader.exists(p):
			return load(p) as PackedScene
	return null

func _run() -> void:
	var out_dir := OS.get_environment("UW_CAPTURE_DIR")
	if out_dir == "":
		out_dir = "/tmp/uw_archetypes"
	DirAccess.make_dir_recursive_absolute(out_dir)
	var faction := OS.get_environment("UW_FACTION")
	if faction == "":
		faction = "los_cuervos"
	var stage := Node3D.new()
	root.add_child(stage)
	stage.add_child(SUN.make_sun("midday"))
	var we := WorldEnvironment.new()
	we.environment = (SUN.environment("midday") as Environment).duplicate()
	stage.add_child(we)
	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(60, 60)
	ground.mesh = pm
	var gm := StandardMaterial3D.new()
	gm.albedo_color = Color(0.42, 0.41, 0.39)
	ground.material_override = gm
	stage.add_child(ground)
	var floor_body := StaticBody3D.new()
	var fcs := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(60, 1, 60)
	fcs.shape = box
	fcs.position.y = -0.5
	floor_body.add_child(fcs)
	stage.add_child(floor_body)
	var roster: Dictionary = ((CombatDB.data()["factions"] as Dictionary).get(faction, {}) as Dictionary).get("roster", {})
	var tiers: Array = ["civilian"]
	for t in ["enemy_light", "enemy_medium", "enemy_heavy", "police_patrol", "fbi_tactical", "ally", "boss"]:
		if roster.has(t):
			tiers.append(t)
	var x := -(tiers.size() - 1)
	var npcs: Array = []
	for arch in tiers:
		var npc := (load(NPC) as PackedScene).instantiate() as NPCController
		CombatDB.apply(npc, arch)
		var model := _model_for(faction, arch)
		if model != null:
			(npc.get_node("Pose/Visual/CharacterVisual") as CharacterVisual).model_scene = model
		npc.position = Vector3(x, 0, 0)
		stage.add_child(npc)
		npcs.append([npc, Vector3(x, 0, 0)])
		var l := Label3D.new()
		l.text = "%s\n%.0f HP  %s" % [arch, npc.profile.max_health, npc.profile.weapon.id if npc.profile.weapon else "-"]
		l.font_size = 40
		l.position = Vector3(x, 2.25, 0)
		l.rotation = Vector3(0, PI, 0)
		stage.add_child(l)
		x += 2.0
	await frames(30)                                       # idle clips settle, visuals swap in
	for pair in npcs:                                      # then freeze: pose only, no AI wandering
		var n := pair[0] as NPCController
		n.global_position = pair[1]
		n.rotation = Vector3(0, PI, 0)                     # face the camera on the sun side (-Z)
		n.process_mode = Node.PROCESS_MODE_DISABLED
	var cam := Camera3D.new()
	stage.add_child(cam)
	cam.fov = 40
	cam.position = Vector3(-1.0, 1.6, -7.5)
	cam.look_at(Vector3(0, 1.05, 0), Vector3.UP)
	cam.make_current()
	await frames(12)
	var p := out_dir.path_join("lineup_%s.png" % faction)
	root.get_viewport().get_texture().get_image().save_png(p)
	print("[ARCHETYPES] wrote ", p)
	quit(0)
