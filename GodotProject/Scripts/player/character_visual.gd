# UNDERWORLD - character visual + animation driver (T-GP-01).
#
# The PlayerController rotates this node (facing) and calls update_from_player()
# every physics frame. Player.tscn sets `model_scene` to SK_Jason v2 (T-GP-01c-Jason):
# the PT_ capsule is hidden, the model is instanced under this node, and an
# AnimationTree is built from the model's AnimationPlayer using CLIP_NAMES (contract:
# Docs/Handoffs/REQ_SK_Jason_Controller.md). Empty model_scene = PT capsule stand-in.
class_name CharacterVisual
extends Node3D

## Logical slot -> clip name inside the model's AnimationPlayer (default library "").
const CLIP_NAMES := {
	"idle": "A_Jason_Idle",
	"walk": "A_Jason_Walk",
	"run": "A_Jason_Run",
	"sprint": "A_Jason_Sprint",
	"crouch_idle": "A_Jason_Crouch_Idle",
	"crouch_walk": "A_Jason_Crouch_Walk",
	"jump_start": "A_Jason_Jump_Start",
	# Loop mode comes from the manifest, never from the name (no "_Loop" suffix, REQ-GP01-JASON).
	"jump_loop": "A_Jason_Jump_Air",
	"land": "A_Jason_Land",
	"aim_idle": "A_Jason_Aim_Pistol_Idle",
	"aim_walk_fwd": "A_Jason_Aim_Pistol_Walk_F",
	"aim_walk_back": "A_Jason_Aim_Pistol_Walk_B",
	"aim_walk_left": "A_Jason_Aim_Pistol_Walk_L",
	"aim_walk_right": "A_Jason_Aim_Pistol_Walk_R",
	# T-GP-04 one-shot / upper-body clips.
	"shoot": "A_Jason_Shoot_Pistol",
	"reload": "A_Jason_Reload_Pistol",
	"carry_idle": "A_Jason_Carry_Idle",
	"carry_walk": "A_Jason_Carry_Walk",
	"death": "A_Jason_Death",
	"car_enter": "A_Jason_Car_Enter_L",
	"car_exit": "A_Jason_Car_Exit_L",
	# B-011: seated loops. Their root is the seat socket (H-point), see set_seated().
	"sit_driver": "A_Jason_Sit_Driver",
	"sit_passenger": "A_Jason_Sit_Passenger",
}
## Speeds (m/s) at which the in-place clips were authored; must match the controller
## and the SK_Jason manifest "speed_mps" (checked in test_player_controller.gd).
const CLIP_SPEEDS := {"idle": 0.0, "walk": 1.4, "run": 3.5, "sprint": 6.0, "crouch_idle": 0.0, "crouch_walk": 1.2}

## Emitted before the current model is freed (attachments must leave it) and after a new one is in.
signal model_changing(old_model: Node3D)
signal model_changed(new_model: Node3D)

## Character model (e.g. res://Assets/Characters/SK_Jason/SK_Jason.glb). Empty = PT capsule.
@export var model_scene: PackedScene
## Clip prefix of this model. SK_Jason exports "A_Jason_*"; NPCs share the humanoid library
## "A_Humanoid_*" (A_Humanoid_Locomotion.glb). CLIP_NAMES below holds the *logical* names for
## Jason; when the prefix differs each slot is resolved by its suffix (idle -> *_Idle).
@export var clip_prefix := "A_Jason_"
## Optional: an AnimationTree authored by hand in the editor. If empty and a model
## with an AnimationPlayer is present, build_default_tree() creates one.
@export var animation_tree_path: NodePath
## Smoothing rate for blend parameters (1/s).
@export var blend_rate := 10.0

## Per-instance copy of CLIP_NAMES used to build the tree (tests / variants may override a slot).
var clip_names: Dictionary = CLIP_NAMES.duplicate()
var model: Node3D
var animation_player: AnimationPlayer
var animation_tree: AnimationTree
## Slots that were missing in the model (filled with idle); reported once.
var missing_clips: PackedStringArray = []
## True if animation_tree was built by build_default_tree() (rebuilt on model swap).
var _auto_tree := false

## Upper-body aim layer (T-GP-04). Created as a child of the Skeleton3D because
## SkeletonModifier3D only accepts its parent; it adds the spine twist on top of the tree.
var aim_modifier: AimSpineModifier
## Clip length of the one-shot currently playing (s), -1 while idle. Used by the vehicle so the
## enter/exit timer comes from the CLIP, not from a constant (T-GP-04).
var one_shot_left := -1.0
var one_shot_name := ""
## Last one-shot that was fired, with the frame it started (tests + debugging).
var shots_played := 0
var reloads_played := 0
## Carried package (M01): the two clips replace the locomotion slots while it is true.
var carrying := false
## Aim in the character's own space (radians, + up / + left). Fed by the player camera.
var aim_pitch := 0.0
var aim_yaw := 0.0
var _carry := 0.0
var _shot := 0.0
var _reload_anim := false
var _death := 0.0
var _car_pose := 0.0

var _crouch := 0.0
var _aim := 0.0
var _air := 0.0
var _was_air := false
var _jump_requested := false
var _player: PlayerController

func _ready() -> void:
	if animation_tree_path != NodePath():
		animation_tree = get_node_or_null(animation_tree_path) as AnimationTree
	if model_scene != null:
		set_model(model_scene)

## Swap the stand-in for a real model at runtime (also used by tests).
func set_model(scene: PackedScene) -> void:
	if model != null:
		model_changing.emit(model)
		model.queue_free()
		model = null
	if _auto_tree and animation_tree != null:
		animation_tree.queue_free()
		animation_tree = null
		_auto_tree = false
	missing_clips.clear()
	model = scene.instantiate() as Node3D
	model.name = "Model"
	add_child(model)
	for c in get_children():
		if String(c.name).begins_with("PT_"):
			(c as Node3D).visible = false
	# NPC scenes (build_npc_scenes.gd) keep the PT_ capsule + front marker as SIBLINGS of this
	# node (Pose/Visual/PT_Capsule). Hide those stand-in meshes too - otherwise every enemy in
	# M01 rendered as a red capsule over its real model (T-CHAR-01). Only meshes: the sibling
	# PT_SOCKET_RightHand_Weapon carries the live weapon and must stay visible.
	if get_parent() != null and not _sabotage_capsule():
		for c in get_parent().get_children():
			if c != self and c is MeshInstance3D and String(c.name).begins_with("PT_"):
				(c as MeshInstance3D).visible = false
	animation_player = _find_animation_player(model)
	if animation_player != null and animation_tree == null:
		animation_tree = build_default_tree(animation_player)
		_auto_tree = true
	# The tree only references locomotion/one-shot clips. The remaining slots (death, car enter/
	# exit, reload) are resolved on demand by play_one_shot(), so probe them here: a model that
	# cannot serve them must report it up front, not at the first death.
	if animation_player != null:
		for slot in clip_names:
			_clip(slot, animation_player)
	# The aim layer lives on the skeleton, because SkeletonModifier3D only accepts its parent.
	aim_modifier = null
	var sk := find_skeleton()
	if sk != null and not sabotage_anim():
		aim_modifier = AimSpineModifier.new()
		aim_modifier.name = "AimSpine"
		sk.add_child(aim_modifier)
	model_changed.emit(model)

func find_skeleton() -> Skeleton3D:
	if model == null:
		return null
	var found := model.find_children("*", "Skeleton3D", true, false)
	return found[0] as Skeleton3D if not found.is_empty() else null


## Negative control (UW_ANIM_SABOTAGE=1): the upper-body layer is not created and one-shot
## clips are mapped to the wrong slot, i.e. the pre-T-GP-04 behaviour. Tests must FAIL.
static var _sabotage_anim: int = -1


static func sabotage_anim() -> bool:
	if _sabotage_anim < 0:
		_sabotage_anim = 1 if OS.is_debug_build() and OS.get_environment("UW_ANIM_SABOTAGE").strip_edges() == "1" else 0
	return _sabotage_anim == 1


func _find_animation_player(n: Node) -> AnimationPlayer:
	if n is AnimationPlayer:
		return n
	for c in n.get_children():
		var r := _find_animation_player(c)
		if r != null:
			return r
	return null

## Resolve a logical slot ("run") to a clip that exists in this model's AnimationPlayer.
func resolve_clip(slot: String, ap: AnimationPlayer) -> String:
	var logical: String = clip_names[slot] if clip_names.has(slot) else slot
	if ap.has_animation(logical):
		return logical
	if clip_prefix != "" and logical.begins_with("A_Jason_"):
		var shared := clip_prefix + logical.substr("A_Jason_".length())
		if ap.has_animation(shared):
			return shared
		return shared
	return logical

func _clip(slot: String, ap: AnimationPlayer) -> String:
	var name := resolve_clip(slot, ap)
	if ap.has_animation(name):
		return name
	# T-ANIM-01: the clip is not baked into this model - take it from the shared humanoid
	# library (same 53-bone contract), re-addressed to this model's skeleton path.
	if _borrow_shared_clip(name, ap):
		return name
	if not missing_clips.has(slot):
		missing_clips.append(slot)
	var idle := resolve_clip("idle", ap)
	return idle if ap.has_animation(idle) else name

## Contract check of the current model: one "slot: problem" line per mapped clip that is
## missing from the AnimationPlayer or named with a loop suffix. Empty = OK.
func validate_clips() -> PackedStringArray:
	var errs: PackedStringArray = []
	if animation_player == null:
		errs.append("no AnimationPlayer in model")
		return errs
	for slot in clip_names:
		var n := resolve_clip(slot, animation_player)
		if not animation_player.has_animation(n):
			errs.append("%s: clip %s not in model" % [slot, n])
		if n.ends_with("_Loop"):
			errs.append("%s: clip %s uses a _Loop suffix (loop mode comes from the manifest)" % [slot, n])
	return errs

## Builds the default locomotion graph:
##   loco (BlendSpace1D by speed) ─┐
##   crouch_loco (BlendSpace1D) ───┴ crouch (Blend2) ─┐
##   aim_loco (BlendSpace2D by local move dir) ───────┴ aim (Blend2) ─┐
##   oneshot (OneShot: shoot / reload / car) ─────────────────────────┴ oneshot ─┐
##   carry_loco (BlendSpace1D) ───────────────────────────────────────┴ carry (Blend2) ─┐
##   jump_loop ─────────────────────────────────────────────────────────────────────────┴ air
##     → jump (OneShot: jump_start) → land (OneShot: land) → output
##
## The spine twist on top of all of this is AimSpineModifier (upper-body layer, T-GP-04) - a
## SkeletonModifier3D, because a bone filter inside the tree would have to be maintained as a
## NodePath list that breaks on every re-export. The modifier only touches Spine/Chest/UpperChest,
## so the legs always keep the locomotion clip.
func build_default_tree(ap: AnimationPlayer) -> AnimationTree:
	var bt := AnimationNodeBlendTree.new()

	var loco := AnimationNodeBlendSpace1D.new()
	loco.min_space = 0.0
	loco.max_space = 6.0
	for slot in ["idle", "walk", "run", "sprint"]:
		loco.add_blend_point(_anim(slot, ap), CLIP_SPEEDS[slot], -1, slot)
	bt.add_node("loco", loco, Vector2(0, 0))

	var cloco := AnimationNodeBlendSpace1D.new()
	cloco.min_space = 0.0
	cloco.max_space = 2.0
	for slot in ["crouch_idle", "crouch_walk"]:
		cloco.add_blend_point(_anim(slot, ap), CLIP_SPEEDS[slot], -1, slot)
	bt.add_node("crouch_loco", cloco, Vector2(0, 200))

	var aloco := AnimationNodeBlendSpace2D.new()
	aloco.add_blend_point(_anim("aim_idle", ap), Vector2.ZERO, -1, "aim_idle")
	aloco.add_blend_point(_anim("aim_walk_fwd", ap), Vector2(0, 1), -1, "aim_walk_fwd")
	aloco.add_blend_point(_anim("aim_walk_back", ap), Vector2(0, -1), -1, "aim_walk_back")
	aloco.add_blend_point(_anim("aim_walk_left", ap), Vector2(-1, 0), -1, "aim_walk_left")
	aloco.add_blend_point(_anim("aim_walk_right", ap), Vector2(1, 0), -1, "aim_walk_right")
	bt.add_node("aim_loco", aloco, Vector2(0, 400))

	var cloco2 := AnimationNodeBlendSpace1D.new()
	cloco2.min_space = 0.0
	cloco2.max_space = 2.0
	cloco2.add_blend_point(_anim("carry_idle", ap), 0.0, -1, "carry_idle")
	cloco2.add_blend_point(_anim("carry_walk", ap), CLIP_SPEEDS["walk"], -1, "carry_walk")
	bt.add_node("carry_loco", cloco2, Vector2(0, 500))

	bt.add_node("jump_loop", _anim("jump_loop", ap), Vector2(0, 700))
	bt.add_node("crouch", AnimationNodeBlend2.new(), Vector2(300, 100))
	bt.add_node("aim", AnimationNodeBlend2.new(), Vector2(500, 200))
	bt.add_node("oneshot_clip", _anim("shoot", ap), Vector2(600, 450))
	var oneshot := AnimationNodeOneShot.new()
	oneshot.fadein_time = 0.04
	oneshot.fadeout_time = 0.12
	bt.add_node("oneshot", oneshot, Vector2(700, 250))
	bt.add_node("carry", AnimationNodeBlend2.new(), Vector2(900, 250))
	bt.add_node("air", AnimationNodeBlend2.new(), Vector2(1100, 300))
	var land := AnimationNodeOneShot.new()
	land.fadein_time = 0.05
	land.fadeout_time = 0.15
	bt.add_node("land", land, Vector2(1300, 300))
	bt.add_node("land_clip", _anim("land", ap), Vector2(1100, 550))
	var jump := AnimationNodeOneShot.new()
	jump.fadein_time = 0.05
	jump.fadeout_time = 0.2
	bt.add_node("jump", jump, Vector2(1200, 300))
	bt.add_node("jump_clip", _anim("jump_start", ap), Vector2(1000, 550))

	bt.connect_node("crouch", 0, "loco")
	bt.connect_node("crouch", 1, "crouch_loco")
	bt.connect_node("aim", 0, "crouch")
	bt.connect_node("aim", 1, "aim_loco")
	bt.connect_node("oneshot", 0, "aim")
	bt.connect_node("oneshot", 1, "oneshot_clip")
	bt.connect_node("carry", 0, "oneshot")
	bt.connect_node("carry", 1, "carry_loco")
	bt.connect_node("air", 0, "carry")
	bt.connect_node("air", 1, "jump_loop")
	bt.connect_node("jump", 0, "air")
	bt.connect_node("jump", 1, "jump_clip")
	bt.connect_node("land", 0, "jump")
	bt.connect_node("land", 1, "land_clip")
	bt.connect_node("output", 0, "land")

	var tree := AnimationTree.new()
	tree.name = "AnimationTree"
	tree.tree_root = bt
	add_child(tree)
	tree.anim_player = tree.get_path_to(ap)
	tree.active = true
	if not missing_clips.is_empty():
		push_warning("CharacterVisual: model is missing clips for %s (using idle)" % ", ".join(missing_clips))
	return tree

func _anim(slot: String, ap: AnimationPlayer) -> AnimationNodeAnimation:
	var a := AnimationNodeAnimation.new()
	a.animation = _clip(slot, ap)
	return a

func _on_player_jumped() -> void:
	_jump_requested = true

# --- T-GP-04: one-shot clips (shoot / reload / death / car) ----------------------

## Length of a slot's clip in seconds (0 if the model has none). This is what drives the
## vehicle's enter/exit timing, so animation and gameplay can never drift apart.
func clip_length(slot: String) -> float:
	if animation_player == null:
		return 0.0
	var name := resolve_clip(slot, animation_player)
	if not animation_player.has_animation(name):
		return 0.0
	return animation_player.get_animation(name).length


func is_one_shot_playing() -> bool:
	return one_shot_left > 0.0


## Plays a one-shot slot on top of the locomotion graph (see build_default_tree: "oneshot").
## The reload clip is 1.6 s and the weapon's reload is 1.6 s, so the tree keeps the clip instead
## of stretching it; mismatch is visible in the tests.
func play_one_shot(slot: String) -> float:
	if animation_tree == null or animation_player == null:
		return 0.0
	var len := clip_length(slot)
	if len <= 0.0:
		return 0.0
	if sabotage_anim():
		slot = "idle"  # wrong mapping on purpose (negative control)
		len = clip_length("idle")
	var clip := resolve_clip(slot, animation_player)
	var anim_name := "oneshot_clip"
	if animation_tree.tree_root is AnimationNodeBlendTree:
		var bt := animation_tree.tree_root as AnimationNodeBlendTree
		# AnimationNodeBlendTree uses StringName keys (no NodePath lookup, no null-returning get).
		var n := bt.get_node(StringName(anim_name)) as AnimationNodeAnimation
		if n != null:
			n.animation = clip
	animation_tree.set("parameters/oneshot/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
	one_shot_left = len
	one_shot_name = clip
	match slot:
		"shoot":
			shots_played += 1
		"reload":
			reloads_played += 1
	one_shot_played.emit(clip)
	return len


signal one_shot_played(clip: String)


func _tick_one_shots(delta: float) -> void:
	if one_shot_left > 0.0:
		one_shot_left = maxf(one_shot_left - delta, 0.0)


## --- generic (NPC) driver ---------------------------------------------------------
## PlayerController drives the player through update_from_player(); NPCs only have a speed and
## an FSM state, so they push these values and the visual smooths them the same way.
var speed := 0.0
var aiming := false
var crouching := false
var dead := false
## True once the death clip has been started (so it is not restarted every frame).
var _death_stopped := false

func set_speed(v: float) -> void:
	speed = v

func set_aiming(v: bool) -> void:
	aiming = v

func set_crouching(v: bool) -> void:
	crouching = v

func set_dead(v: bool) -> void:
	dead = v

## Called by NPCController every physics frame (there is no PlayerController to read from).
func update_generic(delta: float) -> void:
	var t := 1.0 - exp(-blend_rate * delta)
	_crouch = lerpf(_crouch, 1.0 if crouching else 0.0, t)
	_aim = lerpf(_aim, 1.0 if aiming else 0.0, t)
	_air = lerpf(_air, 0.0, t)
	_death = lerpf(_death, 1.0 if dead else 0.0, t)
	_sync_aim_modifier(t)
	_tick_one_shots(delta)
	if animation_tree == null:
		return
	if dead:
		# Death clip, then freeze the pose at its end (no locomotion, no aim lean).
		if _death_stopped:
			if one_shot_left <= 0.0 and animation_tree.active:
				animation_tree.active = false
			return
		animation_tree.set("parameters/loco/blend_position", 0.0)
		animation_tree.set("parameters/crouch_loco/blend_position", 0.0)
		animation_tree.set("parameters/crouch/blend_amount", 0.0)
		animation_tree.set("parameters/aim/blend_amount", 0.0)
		animation_tree.set("parameters/air/blend_amount", 0.0)
		return
	animation_tree.set("parameters/loco/blend_position", speed)
	animation_tree.set("parameters/crouch_loco/blend_position", speed)
	animation_tree.set("parameters/aim_loco/blend_position", Vector2.ZERO)
	animation_tree.set("parameters/crouch/blend_amount", _crouch)
	animation_tree.set("parameters/aim/blend_amount", _aim)
	animation_tree.set("parameters/air/blend_amount", _air)

func _shoot_blend(_t: float) -> void:
	pass


## Aim weight follows the aim state (0.35 s ramp, so the spine does not snap).
func _sync_aim_modifier(t: float) -> void:
	if aim_modifier != null:
		aim_modifier.aim_pitch = aim_pitch
		aim_modifier.aim_yaw = aim_yaw
		aim_modifier.weight = lerpf(aim_modifier.weight, _aim, minf(t * 2.0, 1.0))


func update_from_player(p: PlayerController, delta: float) -> void:
	if _player != p:
		_player = p
		p.jumped.connect(_on_player_jumped)
	# Death wins over locomotion: the same one-shot path the NPCs use (T-GP-04). It starts on the
	# FIRST frame after death (no ramp), because the death clip is not a blend - it is the event.
	if p.dying:
		dead = true
		aiming = false
		speed = 0.0
		if not _death_stopped and animation_tree != null:
			play_one_shot("death")
			_death_stopped = true
		update_generic(delta)
		return
	var t := 1.0 - exp(-blend_rate * delta)
	var in_air := p.move_state == PlayerController.MoveState.AIR and p.air_time > 0.1
	_crouch = lerpf(_crouch, 1.0 if p.is_crouching else 0.0, t)
	_aim = lerpf(_aim, 1.0 if p.is_aiming else 0.0, t)
	_air = lerpf(_air, 1.0 if in_air else 0.0, t)
	# T-GP-04: the upper-body layer only leans while aiming, and it leans towards the CAMERA -
	# not towards the body facing, which is why the camera rig owns the angles.
	if p.camera_rig != null:
		var fwd := p.camera_rig.get_flat_forward()
		# Camera pitch is negative when looking up; the modifier wants + = up.
		aim_pitch = -p.camera_rig.get_effective_pitch()
		# Signed angle from the body facing to the look direction (+ = looking left of the body).
		aim_yaw = wrapf(p.facing_yaw - atan2(fwd.x, fwd.z), -PI, PI)
	_sync_aim_modifier(t)
	_carry = lerpf(_carry, 1.0 if carrying else 0.0, t)
	_tick_one_shots(delta)
	_shoot_blend(t)
	if animation_tree == null:
		_was_air = in_air
		_jump_requested = false
		return
	var speed := p.get_planar_speed()
	# Local move direction relative to facing (for aim strafing), normalised to aim speed.
	# Model faces +Z, so its right-hand side is -X: x = right, y = forward.
	var local := Vector3(p.velocity.x, 0.0, p.velocity.z).rotated(Vector3.UP, -p.facing_yaw)
	var strafe := Vector2(-local.x, local.z) / maxf(p.aim_move_speed, 0.01)
	animation_tree.set("parameters/loco/blend_position", speed)
	animation_tree.set("parameters/crouch_loco/blend_position", speed)
	animation_tree.set("parameters/aim_loco/blend_position", strafe.limit_length(1.0))
	animation_tree.set("parameters/crouch/blend_amount", _crouch)
	animation_tree.set("parameters/aim/blend_amount", _aim)
	animation_tree.set("parameters/air/blend_amount", _air)
	animation_tree.set("parameters/carry/blend_amount", _carry)
	animation_tree.set("parameters/carry_loco/blend_position", speed)
	if _jump_requested:
		animation_tree.set("parameters/jump/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
	if _was_air and not in_air:
		animation_tree.set("parameters/land/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
	_jump_requested = false
	_was_air = in_air


# --- seated in a vehicle (B-011) -------------------------------------------------

## Slot of the sit clip while seated ("sit_driver" / "sit_passenger"), "" on foot.
var seated_slot := ""
var _seat: Node3D
var _seat_scale := Vector3.ONE
var _saved_xform := Transform3D.IDENTITY
var _saved_top_level := false

## Seats the character: the AnimationTree pauses, the looping sit clip plays on the
## AnimationPlayer and this node is pinned to `seat` (SOCKET_Seat_*) - the clip's root IS the
## seat's H-point, so no per-car offset exists. `slot` "" stands the character up again (the
## transform and the tree come back). False if the model cannot serve the sit clip.
func set_seated(slot: String, seat: Node3D = null) -> bool:
	if slot == "":
		if seated_slot == "":
			return true
		seated_slot = ""
		_seat = null
		top_level = _saved_top_level
		transform = _saved_xform
		if animation_player != null:
			animation_player.stop()
		if animation_tree != null:
			animation_tree.active = true
		return true
	if animation_player == null or seat == null:
		return false
	var clip := _clip(slot, animation_player)
	if missing_clips.has(slot) or not animation_player.has_animation(clip):
		return false
	if seated_slot == "":
		_saved_xform = transform
		_saved_top_level = top_level
		_seat_scale = global_basis.get_scale()
	seated_slot = slot
	_seat = seat
	if animation_tree != null:
		animation_tree.active = false
	if aim_modifier != null:
		aim_modifier.weight = 0.0
	var anim := animation_player.get_animation(clip)
	if anim != null:
		anim.loop_mode = Animation.LOOP_LINEAR
	animation_player.play(clip)
	top_level = true
	_pin_to_seat()
	return true


func is_seated() -> bool:
	return seated_slot != ""


## World position of a skeleton bone of the current model (Vector3.INF without one). Used by the
## seat checks (head under the roof, pelvis on the seat) and handy for attachments.
func bone_global_position(bone: String) -> Vector3:
	var sk := find_skeleton()
	if sk == null:
		return Vector3.INF
	var i := sk.find_bone(bone)
	if i < 0:
		return Vector3.INF
	return (sk.global_transform * sk.get_bone_global_pose(i)).origin


func _pin_to_seat() -> void:
	if _seat != null and is_instance_valid(_seat) and _seat.is_inside_tree():
		global_transform = Transform3D(_seat.global_basis.orthonormalized() * Basis.from_scale(_seat_scale), _seat.global_position)


func _process(_delta: float) -> void:
	if seated_slot != "":
		_pin_to_seat()


# --- shared animation library (T-ANIM-01) -----------------------------------------

## Every character shares the 53-bone SkeletonProfileHumanoid contract, so a clip authored once in
## Assets/Characters/Shared/A_Humanoid_Locomotion.glb can drive any of them. NPC models used to
## bake only 16 of the 21 library clips (no Carry_*), hence the "missing clips" warnings.
const SHARED_LIBRARY := "res://Assets/Characters/Shared/A_Humanoid_Locomotion.glb"
const SHARED_PREFIX := "A_Humanoid_"
## Returns a duplicate of `clip` from the shared library and the library's scene-root name, or
## [null, ""]. The PackedScene is cached by ResourceLoader; the instance is freed right away (a
## static node cache leaked 22 resources at exit).
static func _shared_clip(clip: String) -> Array:
	if not ResourceLoader.exists(SHARED_LIBRARY):
		return [null, ""]
	var ps := load(SHARED_LIBRARY) as PackedScene
	if ps == null:
		return [null, ""]
	var inst := ps.instantiate()
	var out: Array = [null, String(inst.name)]
	var found := inst.find_children("*", "AnimationPlayer", true, false)
	if not found.is_empty() and (found[0] as AnimationPlayer).has_animation(clip):
		out[0] = ((found[0] as AnimationPlayer).get_animation(clip) as Animation).duplicate(true)
	inst.free()
	return out

## Copies `clip` (e.g. "A_Humanoid_Carry_Walk") from the shared library into `ap`, rewriting the
## first track-path component (the source scene root) to this model's root. False if unavailable.
func _borrow_shared_clip(clip: String, ap: AnimationPlayer) -> bool:
	if OS.is_debug_build() and OS.get_environment("UW_ANIM_SABOTAGE").strip_edges() == "noshared":
		return false
	if model == null:
		return false
	var got := CharacterVisual._shared_clip(clip)
	# A model with its own prefix (SK_Jason: A_Jason_*) borrows a clip it does not bake (e.g.
	# A_Jason_Sit_Driver) from the library by suffix (A_Humanoid_Sit_Driver), under its own name.
	if got[0] == null and clip_prefix != "" and clip.begins_with(clip_prefix) and clip_prefix != SHARED_PREFIX:
		got = CharacterVisual._shared_clip(SHARED_PREFIX + clip.substr(clip_prefix.length()))
	var anim := got[0] as Animation
	if anim == null:
		return false
	var model_root := String(model.get_child(0).name) if model.get_child_count() > 0 and model.get_child(0) is Node3D else ""
	# Track paths look like "<SceneRoot>/Armature/Skeleton3D:Hips". Find this model's own prefix
	# from one of its baked clips, so the copy addresses the same skeleton node.
	var own_prefix := ""
	for n in ap.get_animation_list():
		var a := ap.get_animation(n)
		if a.get_track_count() > 0:
			var tp := String(a.track_get_path(0))
			own_prefix = tp.substr(0, tp.find("/"))
			break
	if own_prefix == "":
		own_prefix = model_root
	for t in anim.get_track_count():
		var path := String(anim.track_get_path(t))
		var slash := path.find("/")
		if slash > 0 and own_prefix != "":
			anim.track_set_path(t, NodePath(own_prefix + path.substr(slash)))
	var lib := ap.get_animation_library("") if ap.has_animation_library("") else null
	if lib == null:
		lib = AnimationLibrary.new()
		ap.add_animation_library("", lib)
	lib.add_animation(clip, anim)
	return true

## Negative control for the capsule fix: UW_ANIM_SABOTAGE=capsule keeps the stand-in visible.
static func _sabotage_capsule() -> bool:
	return OS.is_debug_build() and OS.get_environment("UW_ANIM_SABOTAGE").strip_edges() == "capsule"
