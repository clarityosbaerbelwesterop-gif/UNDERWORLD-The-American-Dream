# UNDERWORLD - health component (T-GP-02). Put on anything that can take damage
# (dummies, enemies T-AI-01, Jason, M01 package crate with 200 HP).
class_name DamageReceiver
extends Node

signal damaged(info: DamageInfo)
signal died(info: DamageInfo)
signal health_changed(health: float, max_health: float)

@export var max_health := 100.0
@export var invulnerable := false  ## e.g. Marco in M01
var health := 100.0
var is_dead := false
var last_hit: DamageInfo

func _ready() -> void:
	health = max_health

func apply_damage(info: DamageInfo) -> void:
	if is_dead:
		return
	info.receiver = self
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

func reset() -> void:
	health = max_health
	is_dead = false
	health_changed.emit(health, max_health)
