# UNDERWORLD - simple interactable (T-MIS-01, T-UI-01).
#
# An Area3D the player can use with the `interact` action (E / gamepad Y). M01 uses it for
# the package pickup; later missions use it for doors, cars, phone boxes, etc.
#
# The player controller does not need to know about it: the player's interaction probe
# (PlayerController.interact_probe) or MissionManager calls `try_interact(player)`.
class_name Interactable
extends Area3D

signal interacted(by: Node3D)

## HUD prompt, e.g. "Pick up the package".
@export var prompt := "Interact"
## Single use: disabled after the first successful interaction.
@export var one_shot := true
## Optional: only usable while this node returns true (e.g. mission phase).
@export var enabled := true
## Optional group the interacting body must be in (empty = any player).
@export var required_group: StringName = &"player"

var used := false

func _ready() -> void:
	collision_layer = 1 << 4          # layer 5 "Hitboxes" is used for overlap probes
	collision_mask = 1 << 1           # detect the Player layer
	monitorable = true
	monitoring = false                # queries are done by the interactor, not by polling

func can_interact(by: Node3D) -> bool:
	if not enabled or (one_shot and used):
		return false
	if by == null:
		return false
	if required_group != &"" and not by.is_in_group(required_group):
		return false
	return true

func try_interact(by: Node3D) -> bool:
	if not can_interact(by):
		return false
	used = true
	interacted.emit(by)
	return true

func reset() -> void:
	used = false
	enabled = true
