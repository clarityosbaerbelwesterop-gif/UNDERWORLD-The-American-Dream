# UNDERWORLD - HUD v0 (T-UI-01).
#
# CanvasLayer with a Control tree built in code, so it works headless (tests can assert on
# node state) and in-engine (Phase 8 capture shows real text). It only *reads* game state:
#   * health bar      -> Player/DamageReceiver.health_changed
#   * ammo counter    -> Weapon.ammo_changed / reload_started / reload_finished
#   * crosshair       -> Weapon bloom (spread) as a widening reticle
#   * objective text  -> MissionManager.objective_text_changed
#   * subtitles       -> MissionManager.subtitle
#   * GPS marker      -> projected world position of the current objective marker
#   * MISSION PASSED  -> MissionManager.mission_completed
# Fonts: Godot's built-in default font (no font asset needed).
class_name HUD
extends CanvasLayer

const C_TEXT := Color(0.94, 0.93, 0.90)
const C_ACCENT := Color(0.92, 0.72, 0.30)
const C_DIM := Color(0.72, 0.71, 0.68)
const C_BAD := Color(0.80, 0.24, 0.20)

@export var player_path: NodePath
@export var mission_path: NodePath
## Camera used to project the GPS marker. Empty = the player's chase camera
## (CameraRig/Pitch/SpringArm3D/Camera3D - see CameraRig).
@export var camera_path: NodePath

var root_control: Control
var health_bar: ProgressBar
var health_label: Label
var ammo_label: Label
var objective_label: Label
var subtitle_label: Label
var crosshair: Control
var marker: Label
var center_label: Label
var fail_label: Label
## 0..1 spread factor used to size the crosshair (set from the weapon's bloom).
var crosshair_spread := 0.0
## Cash shown on the PASSED card (from MissionData.reward_cash, M01 = 2500).
var passed_cash := 0
## Text of the objective currently shown, kept separately from the label so tests and the capture
## tool can read the state without parsing the UI.
var objective_name := ""


## Negative control (UW_HUD_SABOTAGE=1): the HUD stops following the game state - the ammo
## counter is frozen and the objective label keeps the first text it ever got. Real production
## code is corrupted, no self-referential check.
static var _sabotage_hud: int = -1


static func sabotage_hud() -> bool:
	if _sabotage_hud < 0:
		_sabotage_hud = 1 if OS.is_debug_build() and OS.get_environment("UW_HUD_SABOTAGE").strip_edges() == "1" else 0
	return _sabotage_hud == 1

var player: PlayerController
var weapon: Weapon
var health: DamageReceiver
var mission: MissionManager
var camera: Camera3D
var _marker_target: Node3D
var _center_timer := 0.0
var _fail_timer := 0.0

func _ready() -> void:
	layer = 10
	_build()
	# The HUD is the FIRST node of the level scene, so at this point the MissionManager has not
	# run _ready() yet (it joins its group there). Binding deferred - not per frame - keeps the
	# HUD a pure listener: no polling, no timers.
	_bind.call_deferred()

# --- construction -------------------------------------------------------------

func _build() -> void:
	# A stale widget tree saved into a scene file (B-UI-03) would sit under the live one.
	var stale := get_node_or_null("Root")
	if stale != null:
		remove_child(stale)
		stale.queue_free()
	root_control = Control.new()
	root_control.name = "Root"
	root_control.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root_control.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root_control)

	# Health (bottom-left)
	var hp_box := VBoxContainer.new()
	hp_box.name = "HealthBox"
	hp_box.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	hp_box.position = Vector2(40, -96)
	hp_box.custom_minimum_size = Vector2(280, 56)
	root_control.add_child(hp_box)
	health_label = _label("HealthLabel", "100", 16, C_DIM)
	hp_box.add_child(health_label)
	health_bar = ProgressBar.new()
	health_bar.name = "HealthBar"
	health_bar.custom_minimum_size = Vector2(280, 14)
	health_bar.max_value = 100.0
	health_bar.value = 100.0
	health_bar.show_percentage = false
	hp_box.add_child(health_bar)

	# Ammo (bottom-right)
	ammo_label = _label("AmmoLabel", "12 / 60", 30, C_TEXT)
	ammo_label.name = "AmmoLabel"
	ammo_label.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	ammo_label.position = Vector2(-220, -110)
	ammo_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	ammo_label.custom_minimum_size = Vector2(180, 40)
	root_control.add_child(ammo_label)

	# Objective (top-left)
	objective_label = _label("ObjectiveLabel", "", 24, C_TEXT)
	objective_label.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
	objective_label.position = Vector2(44, 40)
	objective_label.custom_minimum_size = Vector2(760, 40)
	root_control.add_child(objective_label)

	# Subtitles (bottom-centre)
	subtitle_label = _label("SubtitleLabel", "", 22, C_TEXT)
	subtitle_label.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	subtitle_label.position = Vector2(-480, -180)
	subtitle_label.custom_minimum_size = Vector2(960, 60)
	subtitle_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	subtitle_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	root_control.add_child(subtitle_label)

	# Crosshair (centre)
	crosshair = Control.new()
	crosshair.name = "Crosshair"
	crosshair.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	crosshair.mouse_filter = Control.MOUSE_FILTER_IGNORE
	crosshair.custom_minimum_size = Vector2.ZERO
	root_control.add_child(crosshair)
	for spec in [["Dot", Vector2(2, 2), Vector2(-1, -1)], ["L", Vector2(8, 1), Vector2(-22, 0)],
			["R", Vector2(8, 1), Vector2(14, 0)], ["T", Vector2(1, 8), Vector2(0, -22)],
			["B", Vector2(1, 8), Vector2(0, 14)]]:
		var r := ColorRect.new()
		r.name = spec[0]
		r.color = Color(1, 1, 1, 0.85)
		r.size = spec[1]
		r.position = spec[2]
		r.mouse_filter = Control.MOUSE_FILTER_IGNORE
		crosshair.add_child(r)

	# GPS marker (world-projected)
	marker = _label("Marker", "◆", 26, C_ACCENT)
	marker.name = "Marker"
	marker.custom_minimum_size = Vector2(40, 34)
	marker.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	root_control.add_child(marker)

	# Centre cards (MISSION PASSED / failed)
	center_label = _label("CenterLabel", "", 54, C_ACCENT)
	center_label.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	center_label.position = Vector2(-600, -80)
	center_label.custom_minimum_size = Vector2(1200, 80)
	center_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	root_control.add_child(center_label)
	fail_label = _label("FailLabel", "", 34, C_BAD)
	fail_label.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	fail_label.position = Vector2(-600, 20)
	fail_label.custom_minimum_size = Vector2(1200, 60)
	fail_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	root_control.add_child(fail_label)


func _label(name: String, text: String, size: int, color: Color) -> Label:
	var l := Label.new()
	l.name = name
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.75))
	l.add_theme_constant_override("shadow_offset_x", 2)
	l.add_theme_constant_override("shadow_offset_y", 2)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l

# --- binding ------------------------------------------------------------------

func _bind() -> void:
	if not is_inside_tree():
		return
	player = _resolve(player_path, &"player") as PlayerController
	if player != null:
		health = player.get_node_or_null("Health") as DamageReceiver
		camera = _resolve(camera_path, &"__none__") as Camera3D
		if camera == null:
			camera = player.get_node_or_null("CameraRig/Pitch/SpringArm3D/Camera3D") as Camera3D
		if camera == null and player.camera_rig != null:
			camera = player.camera_rig.get_node_or_null("Pitch/SpringArm3D/Camera3D") as Camera3D
		var wc := player.get_node_or_null("WeaponController")
		if wc != null:
			weapon = wc.get("weapon") as Weapon
	if health != null:
		health.health_changed.connect(_on_health_changed)
		_on_health_changed(health.health, health.max_health)
	if weapon != null:
		weapon.ammo_changed.connect(_on_ammo_changed)
		weapon.reload_started.connect(_on_reload_started)
		weapon.reload_finished.connect(_on_reload_finished)
		_on_ammo_changed(weapon.ammo, weapon.reserve)
	mission = _resolve(mission_path, &"mission_manager") as MissionManager
	if mission != null:
		mission.objective_text_changed.connect(_on_objective_text)
		mission.subtitle.connect(_on_subtitle)
		mission.mission_completed.connect(_on_mission_completed)
		mission.mission_failed.connect(_on_mission_failed)
		mission.objective_started.connect(_on_objective_started)
		_on_objective_text(mission.objective_text())


func _resolve(path: NodePath, group: StringName) -> Node:
	if not path.is_empty():
		var n := get_node_or_null(path)
		if n != null:
			return n
	var nodes := get_tree().get_nodes_in_group(group)
	return nodes[0] if not nodes.is_empty() else null

# --- state updates ------------------------------------------------------------

func _on_health_changed(hp: float, max_hp: float) -> void:
	health_bar.max_value = max_hp
	health_bar.value = hp
	health_label.text = "%d" % int(round(hp))
	var f := hp / maxf(max_hp, 1.0)
	var fill := StyleBoxFlat.new()
	fill.bg_color = C_BAD.lerp(C_TEXT, clampf(f, 0.0, 1.0)) if f < 0.35 else C_TEXT
	health_bar.add_theme_stylebox_override("fill", fill)


func _on_ammo_changed(mag: int, reserve: int) -> void:
	if sabotage_hud():
		return	# corrupted: the counter never moves again
	ammo_label.text = "%d / %d" % [mag, reserve]


func _on_reload_started(_d: float) -> void:
	ammo_label.text = "RELOADING"


func _on_reload_finished() -> void:
	if weapon != null:
		_on_ammo_changed(weapon.ammo, weapon.reserve)


func _on_objective_text(text: String) -> void:
	objective_name = text
	if sabotage_hud():
		return	# corrupted: the label keeps whatever it showed first
	objective_label.text = text
	_marker_target = null


func _on_objective_started(_index: int, obj: ObjectiveData) -> void:
	var p := obj.marker_path if not obj.marker_path.is_empty() else obj.target_path
	_marker_target = null
	if not p.is_empty() and mission != null and mission.level != null:
		var n := mission.level.get_node_or_null(p)
		if n is Node3D:
			_marker_target = n as Node3D


func _on_subtitle(speaker: String, text: String) -> void:
	subtitle_label.text = ("%s: %s" % [speaker, text]) if speaker != "" else text


func _on_mission_completed(_mission: MissionData, cash: int) -> void:
	passed_cash = cash
	center_label.text = "MISSION PASSED"
	fail_label.text = "+$%d" % cash
	fail_label.add_theme_color_override("font_color", C_ACCENT)
	center_label.modulate.a = 1.0
	print("[HUD] MISSION PASSED +$%d" % cash)


func _on_mission_failed(reason: String) -> void:
	fail_label.text = "MISSION FAILED - %s" % reason
	fail_label.add_theme_color_override("font_color", C_BAD)
	_fail_timer = 0.0
	print("[HUD] MISSION FAILED: ", reason)

# --- per-frame ----------------------------------------------------------------

func _process(delta: float) -> void:
	if weapon != null:
		crosshair_spread = clampf(weapon.bloom / maxf(weapon.data.bloom_max if weapon.data else 4.0, 0.001), 0.0, 1.0)
	_update_crosshair()
	_update_marker()
	if _center_timer > 0.0:
		_center_timer -= delta
		if _center_timer <= 0.0:
			center_label.text = ""


func _update_crosshair() -> void:
	if crosshair == null:
		return
	# Children are positioned relative to this Control, so it has to sit ON the screen centre.
	var vp_size := get_viewport().get_visible_rect().size if get_viewport() != null else Vector2(1920, 1080)
	crosshair.position = (vp_size * 0.5).round()
	var gap := 6.0 + crosshair_spread * 18.0
	(crosshair.get_node("L") as ColorRect).position = Vector2(-gap - 8.0, 0)
	(crosshair.get_node("R") as ColorRect).position = Vector2(gap, 0)
	(crosshair.get_node("T") as ColorRect).position = Vector2(0, -gap - 8.0)
	(crosshair.get_node("B") as ColorRect).position = Vector2(0, gap)


func _update_marker() -> void:
	if marker == null:
		return
	if _marker_target == null or not is_instance_valid(_marker_target) or camera == null:
		marker.visible = false
		return
	var vp := get_viewport()
	if vp == null:
		return
	var world := _marker_target.global_position + Vector3(0, 2.0, 0)
	if camera.is_position_behind(world):
		marker.visible = false
		return
	var sp := camera.unproject_position(world)
	marker.visible = true
	marker.position = sp - Vector2(20, 17)
