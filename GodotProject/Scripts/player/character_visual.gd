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
}
## Speeds (m/s) at which the in-place clips were authored; must match the controller
## and the SK_Jason manifest "speed_mps" (checked in test_player_controller.gd).
const CLIP_SPEEDS := {"idle": 0.0, "walk": 1.4, "run": 3.5, "sprint": 6.0, "crouch_idle": 0.0, "crouch_walk": 1.2}

## Emitted before the current model is freed (attachments must leave it) and after a new one is in.
signal model_changing(old_model: Node3D)
signal model_changed(new_model: Node3D)

## Character model (e.g. res://Assets/Characters/SK_Jason/SK_Jason.glb). Empty = PT capsule.
@export var model_scene: PackedScene
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
	animation_player = _find_animation_player(model)
	if animation_player != null and animation_tree == null:
		animation_tree = build_default_tree(animation_player)
		_auto_tree = true
	model_changed.emit(model)

func _find_animation_player(n: Node) -> AnimationPlayer:
	if n is AnimationPlayer:
		return n
	for c in n.get_children():
		var r := _find_animation_player(c)
		if r != null:
			return r
	return null

func _clip(slot: String, ap: AnimationPlayer) -> String:
	var name: String = clip_names[slot]
	if ap.has_animation(name):
		return name
	if not missing_clips.has(slot):
		missing_clips.append(slot)
	return clip_names["idle"] if ap.has_animation(clip_names["idle"]) else name

## Contract check of the current model: one "slot: problem" line per mapped clip that is
## missing from the AnimationPlayer or named with a loop suffix. Empty = OK.
func validate_clips() -> PackedStringArray:
	var errs: PackedStringArray = []
	if animation_player == null:
		errs.append("no AnimationPlayer in model")
		return errs
	for slot in clip_names:
		var n: String = clip_names[slot]
		if not animation_player.has_animation(n):
			errs.append("%s: clip %s not in model" % [slot, n])
		if n.ends_with("_Loop"):
			errs.append("%s: clip %s uses a _Loop suffix (loop mode comes from the manifest)" % [slot, n])
	return errs

## Builds the default locomotion graph:
##   loco (BlendSpace1D by speed) ─┐
##   crouch_loco (BlendSpace1D) ───┴ crouch (Blend2) ─┐
##   aim_loco (BlendSpace2D by local move dir) ───────┴ aim (Blend2) ─┐
##   jump_loop ───────────────────────────────────────────────────────┴ air (Blend2)
##     → jump (OneShot: jump_start) → land (OneShot: land) → output
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

	bt.add_node("jump_loop", _anim("jump_loop", ap), Vector2(0, 600))
	bt.add_node("crouch", AnimationNodeBlend2.new(), Vector2(300, 100))
	bt.add_node("aim", AnimationNodeBlend2.new(), Vector2(500, 200))
	bt.add_node("air", AnimationNodeBlend2.new(), Vector2(700, 300))
	var land := AnimationNodeOneShot.new()
	land.fadein_time = 0.05
	land.fadeout_time = 0.15
	bt.add_node("land", land, Vector2(900, 300))
	bt.add_node("land_clip", _anim("land", ap), Vector2(700, 500))
	var jump := AnimationNodeOneShot.new()
	jump.fadein_time = 0.05
	jump.fadeout_time = 0.2
	bt.add_node("jump", jump, Vector2(800, 300))
	bt.add_node("jump_clip", _anim("jump_start", ap), Vector2(600, 500))

	bt.connect_node("crouch", 0, "loco")
	bt.connect_node("crouch", 1, "crouch_loco")
	bt.connect_node("aim", 0, "crouch")
	bt.connect_node("aim", 1, "aim_loco")
	bt.connect_node("air", 0, "aim")
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

func update_from_player(p: PlayerController, delta: float) -> void:
	if _player != p:
		_player = p
		p.jumped.connect(_on_player_jumped)
	var t := 1.0 - exp(-blend_rate * delta)
	var in_air := p.move_state == PlayerController.MoveState.AIR and p.air_time > 0.1
	_crouch = lerpf(_crouch, 1.0 if p.is_crouching else 0.0, t)
	_aim = lerpf(_aim, 1.0 if p.is_aiming else 0.0, t)
	_air = lerpf(_air, 1.0 if in_air else 0.0, t)
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
	if _jump_requested:
		animation_tree.set("parameters/jump/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
	if _was_air and not in_air:
		animation_tree.set("parameters/land/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
	_jump_requested = false
	_was_air = in_air
