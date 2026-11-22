# UNDERWORLD - AI perception + accuracy math (T-AI-01). Pure functions (no scene access) so the
# rules are unit-testable (ForgeSkills gamedev-game-testing layer 1); NPCController does the
# raycasts and calls these.
class_name AIPerception
extends RefCounted

## Group whose members get hear_noise(position, radius, source, kind).
const HEARING_GROUP := "ai_hearing"

## Broadcast a noise (gunshot, explosion, ...) to every listener.
static func emit_noise(tree: SceneTree, position: Vector3, radius: float, source: Node, kind: String) -> void:
	if tree != null:
		tree.call_group(HEARING_GROUP, "hear_noise", position, radius, source, kind)

## True if `target` lies inside the horizontal view cone (full angle fov_deg) within range.
static func in_view_cone(eye: Vector3, forward: Vector3, target: Vector3, fov_deg: float, view_range: float) -> bool:
	var to := target - eye
	if to.length() > view_range:
		return false
	var flat_to := Vector3(to.x, 0, to.z)
	var flat_fwd := Vector3(forward.x, 0, forward.z)
	if flat_to.length() < 0.01:
		return true
	if flat_fwd.length() < 0.01:
		return false
	return rad_to_deg(flat_fwd.angle_to(flat_to)) <= fov_deg * 0.5

## Awareness gained per second while the target is visible: 1/detect_time_near up to
## near_distance, linearly slower to 1/detect_time_far at view_distance.
static func awareness_rate(distance: float, p: AIProfile) -> float:
	var t := clampf((distance - p.near_distance) / maxf(p.view_distance - p.near_distance, 0.01), 0.0, 1.0)
	return 1.0 / lerpf(p.detect_time_near, p.detect_time_far, t)

## Hearing: the noise radius capped by the listener's hearing_range.
static func can_hear(listener: Vector3, noise_pos: Vector3, noise_radius: float, p: AIProfile) -> bool:
	return listener.distance_to(noise_pos) <= minf(noise_radius, p.hearing_range)

## AI aim error (cone half-angle, degrees) on top of the weapon's own spread.
## Worse for moving targets and at distance; shrinks with continuous aim time (focus).
static func aim_error_deg(p: AIProfile, distance: float, target_speed: float, focus_time: float) -> float:
	var e := p.aim_error_deg
	e += p.aim_error_moving_target * clampf(target_speed / 3.5, 0.0, 1.5)
	e += p.aim_error_per_10m * distance / 10.0
	var f := lerpf(1.0, p.focus_min_factor, clampf(focus_time / maxf(p.focus_time, 0.01), 0.0, 1.0))
	return e * f

## Random direction inside a cone of half-angle deg around dir.
static func apply_cone(dir: Vector3, deg: float, rng: RandomNumberGenerator) -> Vector3:
	if deg <= 0.0:
		return dir.normalized()
	var r := deg_to_rad(deg) * sqrt(rng.randf())
	var phi := rng.randf() * TAU
	var perp := dir.cross(Vector3.UP if absf(dir.y) < 0.99 else Vector3.RIGHT).normalized()
	return dir.rotated(perp.rotated(dir.normalized(), phi), r).normalized()

## Cover choice score (lower = better): path length proxy + distance from the preferred range.
static func cover_score(dist_self: float, dist_threat: float, p: AIProfile) -> float:
	return dist_self + absf(dist_threat - p.preferred_distance) * 0.5
