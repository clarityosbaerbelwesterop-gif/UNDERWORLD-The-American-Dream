# UNDERWORLD - health component (T-GP-02). Put on anything that can take damage
# (dummies, enemies T-AI-01, Jason, M01 package crate with 200 HP).
class_name DamageReceiver
extends Node

signal damaged(info: DamageInfo)
signal died(info: DamageInfo)
signal health_changed(health: float, max_health: float)

@export var max_health := 100.0
@export var invulnerable := false  ## e.g. Marco in M01
## Player only: NPC damage is scaled by the difficulty layer (TD-022, Difficulty.ai_damage_scale()).
@export var scale_npc_damage := false
var health := 100.0
var is_dead := false
var last_hit: DamageInfo

func _ready() -> void:
	health = max_health

func apply_damage(info: DamageInfo) -> void:
	if is_dead:
		return
	info.receiver = self
	if scale_npc_damage and info.source is NPCController:
		info.amount *= Difficulty.ai_damage_scale()
	_absorb_with_armor(info)
	if not invulnerable:
		health = maxf(health - info.amount, 0.0)
	last_hit = info
	if health <= 0.0:
		is_dead = true
		info.killed = true
	health_changed.emit(health, max_health)
	damaged.emit(info)
	if is_dead:
		died.emit(info)

## Armor pieces (P1, T-DATA-01, Data/Content/combat.json): [{id, zone, absorb, points, max_points}].
## A hit in a covered zone loses `absorb * (1 - armor_penetration)` of its damage to the piece
## until the piece's points are used up. Limbs are never armored.
var armor_pieces: Array = []
signal armor_changed(points: float, max_points: float)

func set_armor(pieces: Array) -> void:
	armor_pieces.clear()
	for p in pieces:
		var d: Dictionary = (p as Dictionary).duplicate()
		d["max_points"] = float(d.get("points", 0.0))
		d["points"] = float(d.get("points", 0.0))
		armor_pieces.append(d)
	armor_changed.emit(armor_points(), armor_max_points())

func armor_points() -> float:
	var t := 0.0
	for p in armor_pieces:
		t += float(p["points"])
	return t

func armor_max_points() -> float:
	var t := 0.0
	for p in armor_pieces:
		t += float(p["max_points"])
	return t

func _absorb_with_armor(info: DamageInfo) -> void:
	if armor_pieces.is_empty() or _sabotage_armor():
		return
	for p in armor_pieces:
		if int(p["zone"]) != info.zone or float(p["points"]) <= 0.0:
			continue
		var share := float(p["absorb"]) * (1.0 - clampf(info.armor_penetration, 0.0, 1.0))
		var taken := minf(info.amount * share, float(p["points"]))
		p["points"] = float(p["points"]) - taken
		info.amount -= taken
		info.absorbed += taken
		armor_changed.emit(armor_points(), armor_max_points())
		return

## Negative control (UW_COMBAT_SABOTAGE=1): armor does nothing. Debug builds only (TD-020).
static func _sabotage_armor() -> bool:
	return OS.is_debug_build() and OS.get_environment("UW_COMBAT_SABOTAGE").strip_edges() == "1"

func reset() -> void:
	for p in armor_pieces:
		p["points"] = float(p["max_points"])
	health = max_health
	is_dead = false
	health_changed.emit(health, max_health)
