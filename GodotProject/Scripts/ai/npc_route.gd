# UNDERWORLD - patrol / ambient walk route (T-AI-01/02): the Marker3D children in order.
class_name NPCRoute
extends Node3D

@export var loop := true

func get_points() -> Array[Vector3]:
	var pts: Array[Vector3] = []
	for c in get_children():
		if c is Node3D:
			pts.append((c as Node3D).global_position)
	return pts

func next_index(i: int) -> int:
	var n := get_points().size()
	if n == 0:
		return 0
	return (i + 1) % n
