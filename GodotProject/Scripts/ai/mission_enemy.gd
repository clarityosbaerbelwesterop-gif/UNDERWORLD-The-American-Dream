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


## Where the level placed this gunman (restored on every checkpoint restart).
var spawn_transform := Transform3D.IDENTITY

func _ready() -> void:
	super._ready()
	spawn_transform = global_transform
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
	_brief_on_player()
	activated.emit()


## B-AI-05 (T-BUILD-02): an ambush wave is sent AT Jason - it must know where he is. Released
## gunmen used to start "idle" with zero awareness; if Jason stayed out of their view cone (in
## cover, which is what a player does) they never engaged and the objective never finished.
## Same knowledge a gunshot gives them (last known position + gunshot awareness), no more:
## they still have to find and see him before they shoot.
func _brief_on_player() -> void:
	if OS.is_debug_build() and OS.get_environment("UW_PLAYTHROUGH_SABOTAGE").strip_edges() == "3":
		return   # negative control: the shipped behaviour (waves can stay idle forever)
	var p := get_tree().get_first_node_in_group(&"player") as Node3D
	if p == null:
		return
	target = p
	last_known_pos = p.global_position
	has_last_known = true
	awareness = maxf(awareness, profile.gunshot_awareness)
	send_event("heard_gunshot")


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
	# Ambush pressure (B-AI-07, T-BUILD-02): a released ambusher that lost Jason fell back to
	# "idle" and stood there forever - the SURVIVE objective could never finish unless the player
	# hunted him down. After 3 s idle it is briefed again on Jason's position (no free shots: it
	# still has to see him).
	# Only for gunmen the MISSION sent (activate()); stand-alone gunmen keep normal perception.
	if activated_once and not is_dead() and fsm.state == profile.initial_state:
		_idle_t += delta
		if _idle_t > 3.0:
			_idle_t = 0.0
			_brief_on_player()
	else:
		_idle_t = 0.0

var _idle_t := 0.0


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


## B-M01-08 (T-BUILD-02): a checkpoint restart revived the dead but left every gunman where the
## last fight ended - alert, in "engage", at the garage door - so the restarted player walked
## straight into fire. Back to the spawn point with a clean mind (the wave stays dormant until
## MissionManager releases it again).
func reset_to_spawn() -> void:
	if is_dead():
		revive()
	global_transform = spawn_transform
	velocity = Vector3.ZERO
	awareness = 0.0
	target = null
	target_visible = false
	visible_time = 0.0
	unseen_time = 0.0
	has_last_known = false
	last_known_pos = Vector3.ZERO
	_events.clear()
	_stop()
	fsm.force(profile.initial_state, "checkpoint")
