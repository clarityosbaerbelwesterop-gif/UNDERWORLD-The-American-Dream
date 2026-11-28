extends SceneTree
## T-LOOK-01 - renders the look-dev scene through every camera for every light preset and measures
## the calibration targets (grey/white/black card, read back from the final tonemapped image).
##
##   UW_CAPTURE_DIR=/abs/dir Tools/godot_phase8_capture.sh --renderer fwdplus \
##       --script res://Tests/tools/capture_lookdev.gd
##
## Optional: UW_LOOKDEV_PRESETS=golden_hour,midday  UW_LOOKDEV_GI=sdfgi  (adds SDFGI on top).
## UW_LOOKDEV_CAMS=calibration (cards only, fast)  UW_LOOKDEV_GRADE=0 (without the chapter grade).
## Writes <preset>[_sdfgi]_<camera>.png and lookdev_metrics.json. Forward Plus on lavapipe = the
## shipping renderer on the CPU: valid for look, never for performance.

const SCENE := "res://Scenes/LookDev/LookDev_Calibration.tscn"
const SUN := preload("res://Scripts/game/sun_preset.gd")

var out_dir := "/tmp/uw_lookdev"
var metrics := {}

func _initialize() -> void:
	var d := OS.get_environment("UW_CAPTURE_DIR")
	if d != "":
		out_dir = d
	DirAccess.make_dir_recursive_absolute(out_dir)
	_run()

func frames(n: int) -> void:
	for i in n:
		await process_frame

func _run() -> void:
	var scene := (load(SCENE) as PackedScene).instantiate()
	root.add_child(scene)
	var presets := OS.get_environment("UW_LOOKDEV_PRESETS").split(",", false)
	if presets.is_empty():
		presets = PackedStringArray(["golden_hour", "midday", "night"])
	var gi := OS.get_environment("UW_LOOKDEV_GI")
	var lighting := scene.get_node("Lighting")
	var we := lighting.get_node("WorldEnvironment") as WorldEnvironment
	for preset in presets:
		var old_sun := lighting.get_node_or_null("Sun")
		if old_sun != null:
			old_sun.free()
		var sun := SUN.make_sun(preset)
		lighting.add_child(sun)
		# Calibration rig faces the sun (local +Z = toward the sun, horizontally).
		(scene.get_node("References") as Node3D).rotation.y = deg_to_rad(sun.rotation_degrees.y)
		# T-LOOK-02: measure what the player sees - the chapter grade on top (UW_LOOKDEV_GRADE=0: off)
		var env: Environment = SUN.graded_environment(preset) if OS.get_environment("UW_LOOKDEV_GRADE") != "0" \
			else (SUN.environment(preset) as Environment).duplicate() as Environment
		if gi == "sdfgi":
			env.sdfgi_enabled = true
			env.sdfgi_use_occlusion = true
			env.ssil_enabled = true
		we.environment = env
		var tag := preset + ("_sdfgi" if gi == "sdfgi" else "")
		var cams: Array = [scene.get_node("References/Cam_Calibration")]
		if OS.get_environment("UW_LOOKDEV_CAMS") != "calibration":
			cams.append_array(scene.get_node("Cameras").get_children())
		for cam in cams:
			(cam as Camera3D).make_current()
			await frames(40 if gi == "sdfgi" else 10)
			var img := root.get_viewport().get_texture().get_image()
			var p := out_dir.path_join("%s_%s.png" % [tag, cam.name])
			img.save_png(p)
			print("[LOOKDEV] wrote ", p)
			if cam.name == "Cam_Calibration":
				metrics[tag] = _measure(scene, cam as Camera3D, img)
				print("[LOOKDEV] %s cards: %s" % [tag, JSON.stringify(metrics[tag])])
	var f := FileAccess.open(out_dir.path_join("lookdev_metrics.json"), FileAccess.WRITE)
	f.store_string(JSON.stringify(metrics, "  "))
	f.close()
	quit(0)

## Mean sRGB (0..255) of a 9x9 pixel patch at the centre of each calibration card.
func _measure(scene: Node, cam: Camera3D, img: Image) -> Dictionary:
	var out := {}
	for card in ["Card_Grey18", "Card_White90", "Card_Black04", "Card_Grey18_Shade"]:
		var n := scene.get_node("References/" + card) as Node3D
		var sp := cam.unproject_position(n.global_position + n.global_basis.z * 0.02)
		var sum := Color(0, 0, 0)
		var k := 0
		for dy in range(-4, 5):
			for dx in range(-4, 5):
				var x := clampi(int(sp.x) + dx, 0, img.get_width() - 1)
				var y := clampi(int(sp.y) + dy, 0, img.get_height() - 1)
				sum += img.get_pixel(x, y)
				k += 1
		var m := sum / float(k)
		out[card] = [roundi(m.r * 255.0), roundi(m.g * 255.0), roundi(m.b * 255.0)]
	return out
