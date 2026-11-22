# UNDERWORLD - standard humanoid hitbox set (T-AI-01). Builds Head / Body / Legs / Arm_L / Arm_R
# Hitbox areas (layer 5) for a 1.82 m character standing at y = 0, facing +Z (TD-004), all
# forwarding to one DamageReceiver. Used by the player and the PT_ NPC stand-ins; when SK_Jason /
# SK_NPC_* arrive (REQ-AI01-NPC), the same zones go onto BoneAttachment3D nodes instead.
class_name HumanoidHitboxes
extends Node3D

## DamageReceiver that all zones forward to (path relative to this node).
@export var receiver_path: NodePath

# [name, zone, shape size (Vector3 box) or radius (float sphere), centre]
const ZONES := [
	["Hitbox_Head", Hitbox.Zone.HEAD, 0.13, Vector3(0, 1.68, 0)],
	["Hitbox_Body", Hitbox.Zone.BODY, Vector3(0.5, 0.8, 0.3), Vector3(0, 1.15, 0)],
	["Hitbox_Legs", Hitbox.Zone.LIMB, Vector3(0.4, 0.75, 0.3), Vector3(0, 0.375, 0)],
	["Hitbox_Arm_L", Hitbox.Zone.LIMB, Vector3(0.12, 0.6, 0.14), Vector3(0.31, 1.2, 0)],
	["Hitbox_Arm_R", Hitbox.Zone.LIMB, Vector3(0.12, 0.6, 0.14), Vector3(-0.31, 1.2, 0)],
]

var hitboxes: Array[Hitbox] = []

func _ready() -> void:
	var recv := get_node_or_null(receiver_path) as DamageReceiver
	for z in ZONES:
		var hb := Hitbox.new()
		hb.name = z[0]
		hb.zone = z[1]
		hb.receiver = recv
		var cs := CollisionShape3D.new()
		cs.name = "Shape"
		if z[2] is float:
			var sp := SphereShape3D.new()
			sp.radius = z[2]
			cs.shape = sp
		else:
			var bx := BoxShape3D.new()
			bx.size = z[2]
			cs.shape = bx
		cs.position = z[3]
		hb.add_child(cs)
		add_child(hb)
		hitboxes.append(hb)

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
