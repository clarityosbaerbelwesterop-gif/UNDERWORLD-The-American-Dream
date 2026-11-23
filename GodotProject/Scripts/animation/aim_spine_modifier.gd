# UNDERWORLD - upper-body aim layer for humanoids (T-GP-04).
#
# A SkeletonModifier3D that runs AFTER the AnimationTree has posed the skeleton and twists the
# spine chain towards where the character looks. This is Godot's bone-mask equivalent: the legs
# keep their locomotion clip untouched (they are simply not in CHAIN), the upper body leans.
#
# It has to be a child of the Skeleton3D it modifies - SkeletonModifier3D only accepts its parent
# (see SkeletonModifier3D::_update_skeleton_path), and CharacterVisual creates it there.
#
# The modifier never invents animation: it adds a rotation on top of the animated pose, so the
# clip's own spine motion survives, weighted per bone (Spine < Chest < UpperChest) which is what
# makes the bend read as a real spine and not as a hinge.
class_name AimSpineModifier
extends SkeletonModifier3D

## Bones that take the lean, with their share of the total rotation. The legs are deliberately
## absent: locomotion owns the pelvis and below (that is the "blend mask from the spine up").
const CHAIN := {
	"Spine": 0.35,
	"Chest": 0.35,
	"UpperChest": 0.30,
}

## How far the upper body may follow the camera (deg). Kept below the camera limits so the
## spine does not fold in on itself when the player looks straight up/down.
@export var max_pitch_deg := 45.0
@export var max_yaw_deg := 60.0
## Pitch is softened: a human torso leans less than the head tilts.
@export_range(0.0, 1.0) var pitch_scale := 0.75

## Aim direction in the character's own space (radians). Set by CharacterVisual every frame.
var aim_pitch := 0.0  # + = looking up
var aim_yaw := 0.0    # + = looking left
## 0 = off (fully animated pose), 1 = full lean. Smoothed by CharacterVisual while aiming.
var weight := 0.0

func _process_modification_with_delta(_delta: float) -> void:
	var sk := get_skeleton()
	if sk == null or weight <= 0.001:
		return
	var pitch := clampf(aim_pitch, -deg_to_rad(max_pitch_deg), deg_to_rad(max_pitch_deg)) * pitch_scale * weight
	var yaw := clampf(aim_yaw, -deg_to_rad(max_yaw_deg), deg_to_rad(max_yaw_deg)) * weight
	for bone_name in CHAIN:
		var idx := sk.find_bone(bone_name)
		if idx < 0:
			continue
		var share: float = CHAIN[bone_name]
		var q := Quaternion(Vector3.RIGHT, -pitch * share) * Quaternion(Vector3.UP, yaw * share)
		sk.set_bone_pose_rotation(idx, sk.get_bone_pose_rotation(idx) * q)

## Bones this modifier may move (tests assert the legs are NOT in it).
func chain_bones() -> Array:
	return CHAIN.keys()
