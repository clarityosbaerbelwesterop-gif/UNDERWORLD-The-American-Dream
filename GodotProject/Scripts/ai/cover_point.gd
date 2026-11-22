# UNDERWORLD - pre-placed cover spot (T-AI-01 cover-lite). Put a CoverPoint on the protected
# side of low cover (~1.2 m walls, car bodies); the NPC crouches there to hide and stands up to
# peek and shoot over it. Whether it actually protects against the current threat is checked
# at runtime with raycasts (NPCController.is_cover_protected), so placement mistakes are rejected.
class_name CoverPoint
extends Marker3D

const GROUP := "cover_points"

var occupant: Node = null

func _ready() -> void:
	add_to_group(GROUP)

func is_free_for(n: Node) -> bool:
	return occupant == null or occupant == n or not is_instance_valid(occupant)
