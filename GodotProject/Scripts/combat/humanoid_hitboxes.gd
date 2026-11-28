# UNDERWORLD - standard humanoid hitbox set (T-AI-01, bone-bound since T-GP-04).
#
# Two modes, chosen by the model that CharacterVisual holds:
#   * BONE MODE  - the character has a Skeleton3D with the standard humanoid bones: every Hitbox
#                  is parented to a BoneAttachment3D, so it follows the ANIMATED bone (a crouched
#                  or aiming character has his head somewhere else than his rest pose).
#   * REST MODE  - no skeleton (PT_ stand-ins, tests): the fixed offsets from ZONES are used.
#
# The zones are the same in both modes, so damage rules (headshot multiplier, limb x0.75) never
# depend on which model is running.
class_name HumanoidHitboxes
extends Node3D

## DamageReceiver that all zones forward to (path relative to this node).
@export var receiver_path: NodePath

## [name, zone, bone, shape size (Vector3 box) or radius (float sphere), bone-local offset]
## Bone offsets are in the BONE's space (Godot bone axes: Y along the bone). The head sphere sits
## at the head bone's origin - that is where the skull attachment is, verified against SK_Jason.
const ZONES := [
	["Hitbox_Head", Hitbox.Zone.HEAD, "Head", 0.13, Vector3(0, 0.08, 0)],
	["Hitbox_Body", Hitbox.Zone.BODY, "Chest", Vector3(0.5, 0.45, 0.3), Vector3(0, 0.1, 0)],
	["Hitbox_Hips", Hitbox.Zone.BODY, "Hips", Vector3(0.4, 0.3, 0.28), Vector3(0, 0.05, 0)],
	["Hitbox_Arm_L", Hitbox.Zone.LIMB, "LeftUpperArm", Vector3(0.12, 0.3, 0.14), Vector3(0, 0.14, 0)],
	["Hitbox_Arm_R", Hitbox.Zone.LIMB, "RightUpperArm", Vector3(0.12, 0.3, 0.14), Vector3(0, 0.14, 0)],
	["Hitbox_Leg_L", Hitbox.Zone.LIMB, "LeftUpperLeg", Vector3(0.16, 0.4, 0.18), Vector3(0, 0.2, 0)],
	["Hitbox_Leg_R", Hitbox.Zone.LIMB, "RightUpperLeg", Vector3(0.16, 0.4, 0.18), Vector3(0, 0.2, 0)],
]

## Rest-pose fallbacks for models without a skeleton (same zones, body-relative metres).
const REST_ZONES := [
	["Hitbox_Head", Hitbox.Zone.HEAD, 0.13, Vector3(0, 1.68, 0)],
	["Hitbox_Body", Hitbox.Zone.BODY, Vector3(0.5, 0.8, 0.3), Vector3(0, 1.15, 0)],
	["Hitbox_Hips", Hitbox.Zone.BODY, Vector3(0.4, 0.3, 0.28), Vector3(0, 0.95, 0)],
	["Hitbox_Arm_L", Hitbox.Zone.LIMB, Vector3(0.12, 0.6, 0.14), Vector3(0.31, 1.2, 0)],
	["Hitbox_Arm_R", Hitbox.Zone.LIMB, Vector3(0.12, 0.6, 0.14), Vector3(-0.31, 1.2, 0)],
	["Hitbox_Leg_L", Hitbox.Zone.LIMB, Vector3(0.16, 0.8, 0.18), Vector3(0.14, 0.45, 0)],
	["Hitbox_Leg_R", Hitbox.Zone.LIMB, Vector3(0.16, 0.8, 0.18), Vector3(-0.14, 0.45, 0)],
]

var hitboxes: Array[Hitbox] = []
## Bone attachment per hitbox (empty in REST MODE).
var attachments: Array[BoneAttachment3D] = []
## "bone" or "rest" - which mode the current set was built in.
var mode := "rest"
var skeleton: Skeleton3D
## The zone table that was used for the current set (ZONES in bone mode, REST_ZONES otherwise).
var zones: Array = []


func _ready() -> void:
	build(get_node_or_null(receiver_path) as DamageReceiver)


## (Re)builds the set. Called by the owner when the visual model changed, because the bones only
## exist once the model is in the tree.
func build(receiver: DamageReceiver, sk: Skeleton3D = null) -> void:
	clear()
	skeleton = sk
	mode = "bone" if sk != null and _has_all_bones(sk) else "rest"
	if mode == "bone":
		_build_bone(receiver, sk)
	else:
		_build_rest(receiver)


func _has_all_bones(sk: Skeleton3D) -> bool:
	for z in ZONES:
		if sk.find_bone(z[2]) < 0:
			return false
	return true


func _new_hitbox(zone_name: String, zone: Hitbox.Zone, shape: Variant, receiver: DamageReceiver) -> Hitbox:
	var hb := Hitbox.new()
	hb.name = zone_name
	hb.zone = zone
	hb.receiver = receiver
	var cs := CollisionShape3D.new()
	cs.name = "Shape"
	if shape is float:
		var sp := SphereShape3D.new()
		sp.radius = shape
		cs.shape = sp
	else:
		var bx := BoxShape3D.new()
		bx.size = shape
		cs.shape = bx
	hb.add_child(cs)
	return hb


func _build_rest(receiver: DamageReceiver) -> void:
	zones = REST_ZONES.duplicate(true)
	for z in REST_ZONES:
		var hb := _new_hitbox(z[0], z[1], z[2], receiver)
		(hb.get_node("Shape") as CollisionShape3D).position = z[3]
		add_child(hb)
		hitboxes.append(hb)


func _build_bone(receiver: DamageReceiver, sk: Skeleton3D) -> void:
	# The table is the single source of zones per mode; keep it in step with the actual set.
	zones = ZONES.duplicate(true)
	for z in ZONES:
		var ba := BoneAttachment3D.new()
		ba.name = "Bone_%s" % z[2]
		ba.bone_name = z[2]
		# UW_ANIM_SABOTAGE=1: attached to the wrong bone -> the hitbox does NOT follow the bone.
		if CharacterVisual.sabotage_anim():
			ba.bone_name = "Hips"
		sk.add_child(ba)
		var hb := _new_hitbox(z[0], z[1], z[3], receiver)
		(hb.get_node("Shape") as CollisionShape3D).position = z[4]
		ba.add_child(hb)
		hitboxes.append(hb)
		attachments.append(ba)


## Frees the current set NOW (not deferred): a killed-but-alive Hitbox would keep its name, the
## rebuilt one would be renamed to "@Hitbox_Head@2" and every lookup would find the ghost - which
## is exactly how the bone mode silently fell back to rest mode.
## Canonical zone counts of the bone set (7 zones: 1 head, 3 body incl. hips, 3 limbs).
func zone_counts() -> Dictionary:
	var out := {"head": 0, "body": 0, "limb": 0}
	for z in zones:
		match z[1]:
			Hitbox.Zone.HEAD:
				out["head"] += 1
			Hitbox.Zone.BODY:
				out["body"] += 1
			_:
				out["limb"] += 1
	return out


func clear() -> void:
	for hb in hitboxes:
		if is_instance_valid(hb):
			if hb.get_parent() != null:
				hb.get_parent().remove_child(hb)
			hb.free()
	hitboxes.clear()
	for ba in attachments:
		if is_instance_valid(ba):
			if ba.get_parent() != null:
				ba.get_parent().remove_child(ba)
			ba.free()
	attachments.clear()
	mode = "rest"


func get_rids() -> Array[RID]:
	var out: Array[RID] = []
	for hb in hitboxes:
		out.append(hb.get_rid())
	return out


func set_enabled(on: bool) -> void:
	for hb in hitboxes:
		hb.set_deferred("monitorable", on)
		for c in hb.get_children():
			if c is CollisionShape3D:
				(c as CollisionShape3D).set_deferred("disabled", not on)


## Bone a hitbox is attached to ("" in REST MODE).
func bone_of(zone_name: String) -> String:
	for ba in attachments:
		if ba.get_parent() == skeleton and (ba.get_child_count() > 0) and (ba.get_child(0) as Node).name == zone_name:
			return ba.bone_name
	return ""
