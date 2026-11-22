# UNDERWORLD - generates the PT_ NPC stand-in scenes (T-AI-01):
#   res://Scenes/NPC/PT_NPC_Gunman.tscn   (AI_Gunman_Cartel, PT pistol in hand)
#   res://Scenes/NPC/PT_NPC_Civilian.tscn (AI_Civilian, unarmed)
# Run: godot --headless --path GodotProject --script res://Scripts/tools/build_npc_scenes.gd
# Node contract: see Scripts/ai/npc_controller.gd. SK_NPC_* models (REQ-AI01-NPC) replace Pose/Visual.
extends SceneTree

const SCENES := [
	["res://Scenes/NPC/PT_NPC_Gunman.tscn", "PT_NPC_Gunman", "res://Data/AI/AI_Gunman_Cartel.tres", Color(0.7, 0.15, 0.15), true],
	["res://Scenes/NPC/PT_NPC_Civilian.tscn", "PT_NPC_Civilian", "res://Data/AI/AI_Civilian.tres", Color(0.25, 0.45, 0.8), false],
]

var _root: Node

func _initialize() -> void:
	var ok := true
	for s in SCENES:
		ok = _build(s[0], s[1], load(s[2]) as AIProfile, s[3], s[4]) and ok
	quit(0 if ok else 1)

func _own(n: Node, parent: Node) -> Node:
	parent.add_child(n)
	n.owner = _root
	return n

func _build(path: String, nm: String, prof: AIProfile, col: Color, armed: bool) -> bool:
	var root := CharacterBody3D.new()
	_root = root
	root.name = nm
	root.set_script(load("res://Scripts/ai/npc_controller.gd"))
	root.set("profile", prof)
	root.collision_layer = 1 << 2
	root.collision_mask = 1 | 2 | 4 | 8
	var cs := CollisionShape3D.new()
	cs.name = "CollisionShape3D"
	var cyl := CylinderShape3D.new()
	cyl.radius = 0.35
	cyl.height = 1.8
	cs.shape = cyl
	cs.position = Vector3(0, 0.9, 0)
	_own(cs, root)
	var ag := NavigationAgent3D.new()
	ag.name = "NavigationAgent3D"
	ag.radius = 0.35
	ag.height = 1.8
	ag.path_desired_distance = 0.75  # navmesh surface sits ~0.5 m above the floor top (cell_height), distance is 3D
	ag.target_desired_distance = 0.75
	_own(ag, root)
	var pose := _own(Node3D.new(), root) as Node3D
	pose.name = "Pose"
	var vis := _own(Node3D.new(), pose) as Node3D
	vis.name = "Visual"
	var mat := StandardMaterial3D.new()
	mat.albedo_color = col
	var body := MeshInstance3D.new()
	body.name = "PT_Capsule"
	var cm := CapsuleMesh.new()
	cm.radius = 0.3
	cm.height = 1.8
	body.mesh = cm
	body.position = Vector3(0, 0.9, 0)
	body.material_override = mat
	_own(body, vis)
	var front := MeshInstance3D.new()
	front.name = "PT_FrontMarker"
	var bm := BoxMesh.new()
	bm.size = Vector3(0.18, 0.1, 0.2)
	front.mesh = bm
	front.position = Vector3(0, 1.55, 0.3)
	_own(front, vis)
	if armed:
		var sock := _own(Node3D.new(), vis) as Node3D
		sock.name = "PT_SOCKET_RightHand_Weapon"
		# aiming pose: pistol at shoulder/eye height so the muzzle clears 1.25 m cover when peeking
		sock.position = Vector3(-0.2, 1.45, 0.4)
		var w := Node3D.new()
		w.name = "Weapon"
		w.set_script(load("res://Scripts/combat/weapon.gd"))
		_own(w, sock)
	var hb := Node3D.new()
	hb.name = "Hitboxes"
	hb.set_script(load("res://Scripts/combat/humanoid_hitboxes.gd"))
	hb.set("receiver_path", NodePath("../../Health"))
	_own(hb, pose)
	var hp := Node.new()
	hp.name = "Health"
	hp.set_script(load("res://Scripts/combat/damage_receiver.gd"))
	_own(hp, root)
	var packed := PackedScene.new()
	var err := packed.pack(root)
	if err == OK:
		err = ResourceSaver.save(packed, path)
	print("[NPCSCENES] saved %s err=%d" % [path, err])
	root.free()
	return err == OK
