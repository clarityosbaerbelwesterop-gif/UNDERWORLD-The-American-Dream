# UNDERWORLD - data-driven NPC behaviour profile (T-AI-01 / T-AI-02 baseline).
# One .tres per archetype under res://Data/AI/ (AI_Gunman_Cartel, AI_Civilian). The state
# machine table, timings, perception, accuracy and cover rules all live here; NPCController
# only implements the states listed in NPCController.STATES.
# Values are Bot 3 [DEFAULT] starting values unless a design doc says otherwise.
class_name AIProfile
extends Resource

@export var id := "AI_Unnamed"
@export var max_health := 100.0

@export_group("State machine")
@export var initial_state := "idle"
## { state: { event: next_state } }; "*" row applies in every state.
## Events: suspicious, target_spotted, target_lost, target_dead, heard_gunshot, damaged,
## cover_found, cover_lost, cover_compromised, arrived, timeout.
@export var transitions: Dictionary = {}
## { state: seconds } -> event "timeout".
@export var state_timeouts: Dictionary = {}

@export_group("Movement (m/s)")
@export var walk_speed := 1.4
@export var run_speed := 4.0
@export var flee_speed := 5.0
@export var accel := 14.0
## Body yaw turn rate (rad/s).
@export var turn_rate := 8.0
## Seconds to wait at each route point (idle/patrol).
@export var route_idle_time := 2.0
## How far the Pose (visual + hitboxes) drops when crouching/cowering (m).
@export var crouch_drop := 0.7

@export_group("Perception")
@export var eye_height := 1.6
@export var view_distance := 35.0
## Full horizontal view-cone angle (degrees).
@export var fov_deg := 120.0
## 360° awareness radius (m) - noticed even from behind.
@export var near_awareness_radius := 2.5
## Seconds of continuous LOS to reach full awareness at <= near_distance / at view_distance.
@export var detect_time_near := 0.4
@export var detect_time_far := 1.6
@export var near_distance := 8.0
## Awareness lost per second without LOS (only below full awareness).
@export var awareness_decay := 0.25
## Gain multiplier once no longer in the initial (unaware) state.
@export var alert_gain_multiplier := 2.0
## Max distance at which gunshots are heard (capped by the weapon's noise_radius).
@export var hearing_range := 40.0
## Awareness set when a gunshot is heard.
@export var gunshot_awareness := 0.6
## Seconds without LOS (not counting hiding in cover) before "target_lost".
@export var lose_target_time := 4.0

@export_group("Combat")
@export var weapon: WeaponData
@export var reaction_time := 0.35
@export var burst_min := 2
@export var burst_max := 3
@export var burst_shot_interval := 0.35
@export var burst_pause_min := 0.9
@export var burst_pause_max := 1.5
## Aim error cone half-angle (degrees) added to the weapon's hip spread. Player aimed = 0.6° total.
@export var aim_error_deg := 4.0
## Extra error vs a target moving at run speed (3.5 m/s).
@export var aim_error_moving_target := 3.0
@export var aim_error_per_10m := 0.5
## Continuous-LOS time to reach focus_min_factor.
@export var focus_time := 2.0
@export_range(0.1, 1.0) var focus_min_factor := 0.5
@export var max_engage_distance := 30.0
@export var preferred_distance := 15.0
## Reload in cover when the magazine is below this fraction.
@export_range(0.0, 1.0) var reload_threshold := 0.34

@export_group("Cover")
@export var use_cover := true
@export var cover_search_radius := 15.0
@export var cover_min_threat_distance := 5.0
@export var cover_arrive_distance := 0.6
@export var cover_hide_min := 1.0
@export var cover_hide_max := 1.8
@export var cover_peek_min := 1.5
@export var cover_peek_max := 2.5
## Peeks in a row without LOS to the target before relocating.
@export var peeks_without_los_to_relocate := 2
## While engaging in the open, retry finding cover this often (s).
@export var cover_retry_interval := 1.5

@export_group("Flee")
@export var flee_distance := 15.0
## Cower (crouch in place) if fleeing gains less distance than this (m).
@export var cower_if_gain_below := 3.0
