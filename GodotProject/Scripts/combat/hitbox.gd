# UNDERWORLD - damage zone (T-GP-02). Area3D on physics layer 5 "Hitboxes" that forwards
# hits to a DamageReceiver. Character movement collision lives on layer 3 and is NOT in the
# weapon ray mask, so shots always resolve against hitboxes (head/body/limb).
# For SK_Jason / NPCs: attach Hitbox areas to BoneAttachment3D nodes (Head, Chest, limbs).
class_name Hitbox
extends Area3D

enum Zone { BODY, HEAD, LIMB }

@export var zone: Zone = Zone.BODY
@export var receiver_path: NodePath
## Direct reference (set by HumanoidHitboxes); wins over receiver_path.
var receiver: DamageReceiver

func _ready() -> void:
	collision_layer = 1 << 4  # layer 5 "Hitboxes"
	collision_mask = 0
	monitoring = false
	monitorable = true

func get_receiver() -> DamageReceiver:
	if receiver != null:
		return receiver
	return get_node_or_null(receiver_path) as DamageReceiver
