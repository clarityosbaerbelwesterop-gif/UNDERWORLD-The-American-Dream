# UNDERWORLD - one visual effect instance (P6, T-FX-01). Root of every Scenes/FX/FX_*.tscn.
#
# On ready it restarts all GPUParticles3D children and fades its OmniLight3D flash. One-shot effects
# free themselves after `lifetime`; looping ones (smoke, fire, rain, steam) live until removed.
class_name FXEffect
extends Node3D

@export var lifetime := 1.0
@export var one_shot := true
@export var light_energy := 0.0
@export var light_fade := 0.1

var _age := 0.0
var _light: OmniLight3D

func _ready() -> void:
	for c in find_children("*", "GPUParticles3D", true, false):
		var p := c as GPUParticles3D
		p.emitting = true
		if p.one_shot:
			p.restart()
	_light = get_node_or_null("Flash") as OmniLight3D
	if _light != null:
		_light.light_energy = light_energy

func _process(delta: float) -> void:
	_age += delta
	if _light != null and light_fade > 0.0:
		_light.light_energy = light_energy * clampf(1.0 - _age / light_fade, 0.0, 1.0)
	if one_shot and _age >= lifetime:
		queue_free()

## Spawns Scenes/FX/<id>.tscn at `xform` under `parent` (top level). Returns the effect or null.
static func spawn(id: String, parent: Node, xform: Transform3D, scale_mul := 1.0) -> FXEffect:
	var path := "res://Scenes/FX/%s.tscn" % id
	if parent == null or not parent.is_inside_tree() or not ResourceLoader.exists(path):
		return null
	var fx := (load(path) as PackedScene).instantiate() as FXEffect
	fx.top_level = true
	parent.add_child(fx)
	fx.global_transform = xform.scaled_local(Vector3.ONE * scale_mul)
	return fx

## Impact effect for what a shot hit: flesh (Hitbox), metal (vehicles), glass/wood by group,
## concrete otherwise.
static func impact_id_for(collider: Object) -> String:
	if collider is Hitbox:
		return "FX_Blood"
	if collider is VehicleBody3D or (collider is Node and (collider as Node).is_in_group(&"surface_metal")):
		return "FX_Impact_Metal"
	if collider is Node and (collider as Node).is_in_group(&"surface_glass"):
		return "FX_Impact_Glass"
	if collider is Node and (collider as Node).is_in_group(&"surface_wood"):
		return "FX_Impact_Wood"
	return "FX_Impact_Concrete"
