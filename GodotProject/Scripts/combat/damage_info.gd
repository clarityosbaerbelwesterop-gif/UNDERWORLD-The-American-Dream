# UNDERWORLD - one damage event (T-GP-02). Also the hit-marker payload for the HUD (T-UI-01).
class_name DamageInfo
extends RefCounted

var amount := 0.0          ## final damage applied
var base_damage := 0.0
var distance := 0.0
var falloff := 1.0
var zone := 0              ## Hitbox.Zone
var headshot := false
var position := Vector3.ZERO
var normal := Vector3.UP
var direction := Vector3.FORWARD
var source: Node = null    ## shooter
var weapon_id := ""
var killed := false        ## set by the receiver
var receiver: Node = null  ## DamageReceiver that took it (null = world hit)

func to_dict() -> Dictionary:
	return {"amount": amount, "base_damage": base_damage, "distance": distance, "falloff": falloff,
		"zone": zone, "headshot": headshot, "position": position, "killed": killed, "weapon_id": weapon_id}
