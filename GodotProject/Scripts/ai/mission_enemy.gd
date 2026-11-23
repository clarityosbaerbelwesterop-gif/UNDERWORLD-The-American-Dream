# UNDERWORLD - M01 ambush enemy that starts INACTIVE until its wave is triggered (T-MIS-01b).
#
# NPCController alone has no idea about waves: it perceives and shoots as soon as the player is
# in range, which is why the old level had all five gunmen live from frame one. MissionEnemy is
# the thin mission layer on top:
#
#   * `wave`           1 = street gunmen (Area_GarageInside), 2 = the van crew
#   * inactive state   no perception, no shooting, no collision, no hitboxes, not drawn
#   * activation       MissionManager (or a test) calls activate(); wave 2 is only activated by
#                      the mission once wave 1 is dead - the ordering lives in the mission data
#
# The controller keeps its own state machine; MissionEnemy only gates the *inputs* to it, so a
# deactivated enemy can never "remember" the player from before the ambush started.
class_name MissionEnemy
extends NPCController

signal activated

## Wave this gunman belongs to (1 = garage/street, 2 = van/roof).
@export var wave := 1
## Inactive enemies are hidden and cannot be perceived, shot or collided with until activated.
## DEFAULT TRUE: being dormant is a MISSION decision (the M01 level builds both waves asleep and
## MissionManager wakes them), not a property of "gunman". Scenes that spawn a gunman directly -
## the AI test range, future side missions - get a working enemy without extra setup.
@export var active := true

## True between activate() and a deactivate/reset - used by the mission tests.
var activated_once := false


func _ready() -> void:
	super._ready()
	# Enemy group membership is what the SURVIVE objective counts. The level groups are
	# persistent (saved in the .tscn), this one is for code that only has the node.
	add_to_group(&"mission_enemy")
	if not active:
		_apply_active(false)


## Bring this gunman into the fight: visible, collidable, perceiving, hearing.
func activate() -> void:
	if active:
		return
	active = true
	activated_once = true
	_apply_active(true)
	activated.emit()


## Take it out of the fight again (mission restart / test setup). Also used by
## MissionManager when a checkpoint rewinds to before the ambush.
func deactivate() -> void:
	active = false
	_apply_active(false)


func is_active() -> bool:
	return active


## Per-frame: an inactive gunman must not tick its state machine at all. Without this the
## navigation agent, the perception cone and the weapon cooldown would still advance while the
## node merely sits invisible, and the ambush would start with a fully aware enemy.
func _physics_process(delta: float) -> void:
	if not active:
		return
	super._physics_process(delta)


func _apply_active(on: bool) -> void:
	# Perception + events: the controller's own _physics_process is what polls these, so
	# gating it (above) is the real switch. The rest is about being findable and shootable.
	visible = on
	# Collision + hitboxes: layer 3 (Characters) back on, or off so the car/player pass through
	# and not a single ray can connect with a gunman who is not in the scene yet.
	collision_layer = (1 << 2) if on else 0
	var hb := get_node_or_null("Pose/Hitboxes") as HumanoidHitboxes
	if hb != null:
		hb.set_enabled(on)
	if not on:
		awareness = 0.0
		target_visible = false
		visible_time = 0.0
		unseen_time = 0.0
		has_last_known = false
		target = null
