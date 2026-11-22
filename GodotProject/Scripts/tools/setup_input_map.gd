# UNDERWORLD - (re)writes the gameplay input map into project.godot.
# Single source of truth for default bindings (GAME_DESIGN.md §5 "Controls").
# Run: godot --headless --path GodotProject --script res://Scripts/tools/setup_input_map.gd
# Then review `git diff GodotProject/project.godot`.
extends SceneTree

const DEADZONE := 0.2

static func key(physical_keycode: Key) -> InputEventKey:
	var e := InputEventKey.new()
	e.device = -1
	e.physical_keycode = physical_keycode
	return e

static func mouse(button: MouseButton) -> InputEventMouseButton:
	var e := InputEventMouseButton.new()
	e.device = -1
	e.button_index = button
	return e

static func joy_button(button: JoyButton) -> InputEventJoypadButton:
	var e := InputEventJoypadButton.new()
	e.device = -1
	e.button_index = button
	return e

static func joy_axis(axis: JoyAxis, value: float) -> InputEventJoypadMotion:
	var e := InputEventJoypadMotion.new()
	e.device = -1
	e.axis = axis
	e.axis_value = value
	return e

## action name -> [events]. Gamepad layout uses Godot's SDL (Xbox) naming.
static func bindings() -> Dictionary:
	return {
		"move_forward": [key(KEY_W), joy_axis(JOY_AXIS_LEFT_Y, -1.0)],
		"move_back": [key(KEY_S), joy_axis(JOY_AXIS_LEFT_Y, 1.0)],
		"move_left": [key(KEY_A), joy_axis(JOY_AXIS_LEFT_X, -1.0)],
		"move_right": [key(KEY_D), joy_axis(JOY_AXIS_LEFT_X, 1.0)],
		"look_left": [joy_axis(JOY_AXIS_RIGHT_X, -1.0)],
		"look_right": [joy_axis(JOY_AXIS_RIGHT_X, 1.0)],
		"look_up": [joy_axis(JOY_AXIS_RIGHT_Y, -1.0)],
		"look_down": [joy_axis(JOY_AXIS_RIGHT_Y, 1.0)],
		"sprint": [key(KEY_SHIFT), joy_button(JOY_BUTTON_LEFT_STICK)],
		"walk": [key(KEY_ALT)],
		"crouch": [key(KEY_C), joy_button(JOY_BUTTON_B)],
		"jump": [key(KEY_SPACE), joy_button(JOY_BUTTON_A)],
		"aim": [mouse(MOUSE_BUTTON_RIGHT), joy_axis(JOY_AXIS_TRIGGER_LEFT, 1.0)],
		"fire": [mouse(MOUSE_BUTTON_LEFT), joy_axis(JOY_AXIS_TRIGGER_RIGHT, 1.0)],
		"reload": [key(KEY_R), joy_button(JOY_BUTTON_X)],
		# GDD lists gamepad "A" for both jump and interact; interact is KB-only
		# until that is resolved (context-sensitive A is a T-MIS-01 question).
		"interact": [key(KEY_E)],
		"enter_vehicle": [key(KEY_F), joy_button(JOY_BUTTON_Y)],
		"shoulder_swap": [key(KEY_Q), joy_button(JOY_BUTTON_RIGHT_STICK)],
		"pause": [key(KEY_ESCAPE), joy_button(JOY_BUTTON_START)],
	}

func _initialize() -> void:
	var b := bindings()
	for action in b:
		ProjectSettings.set_setting("input/" + action, {"deadzone": DEADZONE, "events": b[action]})
	# Physics layer names used by the gameplay code (see Scripts/player/*.gd).
	var layers := ["World", "Player", "Characters", "Vehicles", "Hitboxes"]
	for i in layers.size():
		ProjectSettings.set_setting("layer_names/3d_physics/layer_%d" % (i + 1), layers[i])
	# Serialize with Godot's own writer to a temp file, then splice only the
	# [input] and [layer_names] sections into project.godot so hand-written
	# comments and explicit defaults elsewhere in the file are preserved.
	var tmp := OS.get_cache_dir().path_join("underworld_inputmap_%d.godot" % OS.get_process_id())
	var err := ProjectSettings.save_custom(tmp)
	if err != OK:
		push_error("save_custom failed: %d" % err)
		quit(1)
		return
	var generated := _sections(FileAccess.get_file_as_string(tmp))
	DirAccess.remove_absolute(tmp)
	var path := ProjectSettings.globalize_path("res://project.godot")
	var text := FileAccess.get_file_as_string(path)
	for sec in ["input", "layer_names"]:
		text = _replace_section(text, sec, generated.get(sec, ""))
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string(text)
	f.close()
	print("[INPUTMAP] wrote %d actions + %d layer names to project.godot" % [b.size(), layers.size()])
	quit(0)

## Splits an engine config file into {section_name: "[section]\n...body"}.
static func _sections(text: String) -> Dictionary:
	var out := {}
	var current := ""
	for line in text.split("\n"):
		if line.begins_with("[") and line.ends_with("]") and not line.contains("="):
			current = line.substr(1, line.length() - 2)
			out[current] = line + "\n"
		elif current != "":
			out[current] += line + "\n"
	for k in out:
		out[k] = out[k].strip_edges(false, true) + "\n"
	return out

static func _replace_section(text: String, sec: String, body: String) -> String:
	var header := "\n[%s]\n" % sec
	var start := text.find(header)
	if start == -1:
		return text.strip_edges(false, true) + "\n\n" + body
	var end := text.find("\n[", start + header.length())
	var tail := "" if end == -1 else text.substr(end)
	return text.substr(0, start) + "\n" + body + tail
