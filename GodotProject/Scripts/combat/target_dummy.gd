# UNDERWORLD - PT_ shooting-range dummy (T-GP-02). Falls over when killed, reset() restores it.
extends StaticBody3D

@onready var receiver: DamageReceiver = $DamageReceiver
@onready var visual: Node3D = $Visual

func _ready() -> void:
	receiver.died.connect(_on_died)

func _on_died(_info: DamageInfo) -> void:
	visual.rotation_degrees.x = -80.0  # ragdoll-lite placeholder
	for c in get_children():
		if c is Hitbox:
			(c as Hitbox).set_deferred("monitorable", false)
			for s in c.get_children():
				if s is CollisionShape3D:
					s.set_deferred("disabled", true)

func reset() -> void:
	receiver.reset()
	visual.rotation_degrees.x = 0.0
	for c in get_children():
		if c is Hitbox:
			c.monitorable = true
			for s in c.get_children():
				if s is CollisionShape3D:
					s.disabled = false
