# UNDERWORLD - connects the player (T-GP-01) to a Weapon (T-GP-02).
# Reads the fire/reload actions, feeds the camera crosshair ray + stance to the weapon,
# applies recoil to the CameraRig, keeps the character facing the shot while hip-firing,
# and re-emits hit markers for the HUD (T-UI-01).
# Weapon attachment: SOCKET_RightHand_Weapon inside the character model (SK_Jason, REQ-GP01-JASON)
# if present, else the PT_ hand marker on the stand-in.
class_name PlayerWeaponController
extends Node

signal hitmarker(info: DamageInfo)
signal shot_fired(shot: Dictionary)

@export var weapon_path: NodePath = ^"../Visual/PT_SOCKET_RightHand_Weapon/Weapon"
## Seconds the character keeps facing the aim direction after a hip-fire shot.
@export var hip_fire_face_time := 0.6
@export var block_fire_while_sprinting := true

var player: PlayerController
var weapon: Weapon
var last_hitmarker: Dictionary = {}

func _ready() -> void:
	player = get_parent() as PlayerController
	weapon = get_node_or_null(weapon_path) as Weapon
	if weapon != null:
		weapon.hit_confirmed.connect(_on_hit)
		weapon.fired.connect(_on_weapon_fired)
		# T-GP-04: the reload CLIP is driven by the weapon's own reload, so animation and
		# gameplay cannot drift apart (both are 1.6 s; the test asserts the clip length).
		weapon.reload_started.connect(func(_d): _play("reload"))
		_stand_in_parent = weapon.get_parent()
	# Follow model swaps: weapon goes to the model's SOCKET_RightHand_Weapon, and back to
	# the PT_ socket before the old model is freed (else it would be freed with it).
	# (Children are ready before the player, so player.visual is not set yet here.)
	var vis := _visual()
	if vis != null:
		vis.model_changing.connect(_on_model_changing)
		vis.model_changed.connect(func(_m): attach_to_model_socket())
		if vis.model != null:
			attach_to_model_socket()

var _stand_in_parent: Node

func _visual() -> CharacterVisual:
	if player == null:
		return null
	return player.get_node_or_null(player.visual_path) as CharacterVisual

func _on_model_changing(old_model: Node3D) -> void:
	if weapon != null and _stand_in_parent != null and old_model.is_ancestor_of(weapon):
		weapon.reparent(_stand_in_parent, false)
		weapon.transform = Transform3D.IDENTITY

## Move the weapon onto the model's hand socket once a real character model is set.
func attach_to_model_socket() -> bool:
	var vis := _visual()
	if weapon == null or vis == null or vis.model == null:
		return false
	var sock := _find(vis.model, "SOCKET_RightHand_Weapon")
	if sock == null:
		return false
	weapon.reparent(sock, false)
	weapon.transform = Transform3D.IDENTITY
	return true

func _find(n: Node, nm: String) -> Node:
	if String(n.name) == nm:
		return n
	for c in n.get_children():
		var r := _find(c, nm)
		if r != null:
			return r
	return null

func get_stance() -> Dictionary:
	return {"aiming": player.is_aiming, "crouching": player.is_crouching,
		"airborne": not player.is_on_floor(),
		"move_frac": player.get_planar_speed() / maxf(player.run_speed, 0.01)}

func _physics_process(_delta: float) -> void:
	if weapon == null or player == null or player.camera_rig == null:
		return
	player.camera_rig.recoil_recovery_rate = weapon.data.recoil_recovery if weapon.data else 8.0
	if not player.input_enabled:
		return
	if player.is_sprinting and weapon.is_reloading:
		weapon.cancel_reload()  # sprinting interrupts the reload
	if Input.is_action_just_pressed("reload"):
		weapon.start_reload()
	var just := Input.is_action_just_pressed("fire")
	var held := Input.is_action_pressed("fire")
	if not (just or held):
		return
	if block_fire_while_sprinting and player.is_sprinting:
		return
	var ray := player.camera_rig.get_aim_ray()
	var exclude: Array[RID] = player.get_self_rids()
	var shot := weapon.trigger(just, held, ray[0], ray[1], get_stance(), player, exclude)
	if not shot.is_empty():
		player.camera_rig.add_recoil(shot["kick_deg"])
		player.combat_face_time = hip_fire_face_time

## Every real shot plays the Shoot clip; the rate limiter is the weapon's own fire rate, so
## holding the trigger at 300 rpm cannot restart the clip 5x per second.
func _on_weapon_fired(shot: Dictionary) -> void:
	var vis := _visual()
	if vis != null:
		vis.play_one_shot("shoot")
	shot_fired.emit(shot)


func _play(slot: String) -> void:
	var vis := _visual()
	if vis != null:
		vis.play_one_shot(slot)


func _on_hit(info: DamageInfo) -> void:
	last_hitmarker = info.to_dict()
	hitmarker.emit(info)
