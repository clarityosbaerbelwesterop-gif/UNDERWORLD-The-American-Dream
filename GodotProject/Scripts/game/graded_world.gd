# UNDERWORLD - WorldEnvironment that grades itself (T-LOOK-02). Levels keep referencing the plain
# ENV_*.tres on disk; at runtime this swaps in SunPreset.graded_environment(preset), so the chapter
# LUT (generated, ~15 KB) is never baked into a .tscn.
class_name GradedWorld
extends WorldEnvironment

@export var preset := "golden_hour"
## Level generators set this while they build + save, so the plain .tres stays referenced.
static var suspended := false

func _ready() -> void:
	if suspended:
		return
	environment = SunPreset.graded_environment(preset)
