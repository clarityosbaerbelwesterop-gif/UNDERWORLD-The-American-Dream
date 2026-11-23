# UNDERWORLD - difficulty / combat balance layer (TD-022 PROPOSED, T-BUILD-02).
#
# One data resource that scales how hard NPC combat hits the PLAYER, separately from the weapon
# data (which stays physically consistent: a pistol does 25 to anyone). This is how open-world
# shooters keep AI lethal-looking but fair; the value was measured with the input-only M01
# autopilot (Tests/test_playthrough.gd) over several RNG seeds - see Docs/TECHNICAL_DECISIONS.md.
class_name Difficulty
extends Resource

const DEFAULT_PATH := "res://Data/Game/Difficulty_Normal.tres"

## Multiplier on damage that an NPC deals to the player (1.0 = raw weapon damage).
@export_range(0.05, 2.0) var ai_damage_to_player := 1.0

static var _current: Difficulty

static func current() -> Difficulty:
	if _current == null:
		_current = load(DEFAULT_PATH) as Difficulty
		if _current == null:
			_current = Difficulty.new()
	return _current

## Effective multiplier. UW_AI_DAMAGE_SCALE overrides it in debug builds only (balancing runs).
static func ai_damage_scale() -> float:
	if OS.is_debug_build():
		var v := OS.get_environment("UW_AI_DAMAGE_SCALE").strip_edges()
		if v.is_valid_float():
			return float(v)
	return current().ai_damage_to_player
