# UNDERWORLD - makes an instanced asset purely visual (T-LVL-02): removes every physics body under
# it when it enters the tree. Used for level dressing that sits on authored cover boxes (parked
# cars in M01): the asset's own hull must not change the cover geometry the ambush is balanced on.
# Instanced sub-scenes cannot be edited persistently, so this lives on a level-owned parent.
class_name VisualOnly
extends Node3D

func _ready() -> void:
	strip(self)

static func strip(n: Node) -> int:
	var removed := 0
	for body in n.find_children("*", "CollisionObject3D", true, false):
		body.get_parent().remove_child(body)
		body.free()
		removed += 1
	return removed
