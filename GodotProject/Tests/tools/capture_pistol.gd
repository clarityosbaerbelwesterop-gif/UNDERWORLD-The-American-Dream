extends SceneTree
## T-ART-05 Phase 8 - WPN_Pistol_01.glb IN ENGINE: in Jason's hand on SOCKET_RightHand_Weapon
## (aim pose, gameplay over-the-shoulder camera + close shot) and the pistol alone under the
## midday sun preset. Look only (scale, silhouette, materials, clipping, framing), never performance.
##   UW_CAPTURE_DIR=/abs/dir Tools/godot_phase8_capture.sh --res 1280x720 --fixed-fps 30 \
##       --script res://Tests/tools/capture_pistol.gd
## Note: the shipped WPN_Pistol_01.tres still uses the PT stand-in (BERICHT_T-WPN-01); this script
## mounts the real .glb directly, the way the P7 swap will.
const SUN := preload("res://Scripts/game/sun_preset.gd")
const JASON := "res://Assets/Characters/SK_Jason/SK_Jason.glb"
const PISTOL := "res://Assets/Weapons/WPN_Pistol_01/WPN_Pistol_01.glb"
const POSE := "A_Jason_Aim_Pistol_Idle"

func _initialize() -> void:
	_run()

func frames(n: int) -> void:
	for i in n:
		await process_frame

func _find(n: Node, nm: String) -> Node:
	if n.name == nm:
		return n
	for c in n.get_children():
		var r := _find(c, nm)
		if r != null:
			return r
	return null

func _shot(cam: Camera3D, from: Vector3, to: Vector3, fov: float, path: String) -> void:
	cam.fov = fov
	cam.global_position = from
	cam.look_at(to, Vector3.UP)
	await frames(8)
	root.get_viewport().get_texture().get_image().save_png(path)
	print("[PISTOL_SHOT] ", path)

func _run() -> void:
	var out := OS.get_environment("UW_CAPTURE_DIR")
	if out == "":
		out = "/tmp/uw_pistol"
	DirAccess.make_dir_recursive_absolute(out)
	var stage := Node3D.new()
	root.add_child(stage)
	stage.add_child(SUN.make_sun("midday"))
	var we := WorldEnvironment.new()
	we.environment = (SUN.environment("midday") as Environment).duplicate()
	stage.add_child(we)
	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(40, 40)
	ground.mesh = pm
	var gm := StandardMaterial3D.new()
	gm.albedo_color = Color(0.42, 0.41, 0.39)
	ground.material_override = gm
	stage.add_child(ground)
	var jason := (load(JASON) as PackedScene).instantiate() as Node3D
	stage.add_child(jason)
	var ap := _find(jason, "AnimationPlayer") as AnimationPlayer
	if ap != null and ap.has_animation(POSE):
		ap.play(POSE)
	var sock := _find(jason, "SOCKET_RightHand_Weapon") as Node3D
	var gun := (load(PISTOL) as PackedScene).instantiate() as Node3D
	if sock != null:
		sock.add_child(gun)
	else:
		push_error("SOCKET_RightHand_Weapon not found")
		stage.add_child(gun)
	# pistol alone on a plinth at 1 m, 2 m to the side
	var solo := (load(PISTOL) as PackedScene).instantiate() as Node3D
	solo.position = Vector3(2.0, 1.0, 0.0)
	solo.rotation = Vector3(0, PI * 0.5, 0)     # barrel (+Z) -> +X, left side faces the camera at -Z
	stage.add_child(solo)
	await frames(20)
	var cam := Camera3D.new()
	stage.add_child(cam)
	cam.make_current()
	var g := gun.global_position
	print("[PISTOL] grip world pos ", g, " muzzle ", (_find(gun, "SOCKET_Muzzle") as Node3D).global_position)
	await _shot(cam, Vector3(0.55, 1.75, -2.4), Vector3(0.1, 1.35, 2.0), 50.0, out.path_join("pistol_gameplay_ots.png"))
	await _shot(cam, g + Vector3(0.55, 0.12, 0.35), g, 35.0, out.path_join("pistol_in_hand_close.png"))
	await _shot(cam, Vector3(2.0, 1.04, -0.55), Vector3(2.0, 1.0, 0.0), 30.0, out.path_join("pistol_solo_left.png"))
	await _shot(cam, Vector3(2.35, 1.2, -0.4), Vector3(2.0, 1.0, 0.0), 30.0, out.path_join("pistol_solo_q3.png"))
	quit(0)
