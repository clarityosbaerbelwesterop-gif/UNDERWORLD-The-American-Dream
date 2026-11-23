extends SceneTree
## Bot 1 review of PR #17: the shipping entry point really starts M01.
##
## Before this test the project's main scene was the pipeline smoke scene (PT crate) and nothing
## outside the tests called MissionManager.start(), so the Linux export booted into a test crate.
## This test instances whatever `application/run/main_scene` points at - exactly what the
## exported binary runs - and checks that the M01 level, Jason, the HUD and a RUNNING mission
## come up without any test-side start() call.
##
##   $GODOT --headless --fixed-fps 60 --path GodotProject --script res://Tests/test_boot.gd
##
## Negative control: UW_BOOT_SABOTAGE=1 makes GameBoot skip MissionManager.start() (debug builds
## only) -> the mission checks below must FAIL.

const HZ := 60.0
const WATCHDOG := 60 * 60

var failures: Array[String] = []
var _frames := 0
var _done := false

func check(cond: bool, msg: String) -> void:
	if cond:
		print("[GPTEST][PASS] ", msg)
	else:
		print("[GPTEST][FAIL] ", msg)
		failures.append(msg)

func _initialize() -> void:
	_run_all()

func _process(_d: float) -> bool:
	_frames += 1
	if _frames > WATCHDOG and not _done:
		print("[GPTEST][FAIL] watchdog")
		quit(1)
	return false

func frames(n: int) -> void:
	for i in n:
		await physics_frame

func _run_all() -> void:
	await frames(2)
	await test_main_scene_boots_m01()
	_done = true
	if failures.is_empty():
		print("[GPTEST] RESULT: PASS")
		quit(0)
	else:
		print("[GPTEST] RESULT: FAIL (%d)" % failures.size())
		for f in failures:
			print("[GPTEST]   - ", f)
		quit(1)

func test_main_scene_boots_m01() -> void:
	print("[GPTEST] == main scene boots straight into M01 (sabotage=%s)" % str(GameBoot.sabotage()))
	var path := str(ProjectSettings.get_setting("application/run/main_scene", ""))
	check(path != "" and not path.ends_with("Main.tscn"), "main scene is not the pipeline smoke scene (%s)" % path)
	var packed := load(path) as PackedScene
	check(packed != null, "main scene loads")
	if packed == null:
		return
	var game := packed.instantiate()
	root.add_child(game)
	await frames(10)
	await process_frame
	await frames(2)
	var level := game.get_node_or_null("LA_CallowayAve")
	check(level != null, "the M01 level LA_CallowayAve is instanced by the entry scene")
	if level == null:
		game.queue_free()
		return
	var player := level.get_node_or_null("Player") as PlayerController
	var mm := level.get_node_or_null("MissionManager") as MissionManager
	var hud := level.get_node_or_null("HUD") as HUD
	check(player != null and player.is_inside_tree(), "Jason (PlayerController) is in the running scene")
	check(mm != null and mm.state == MissionManager.State.RUNNING, "M01 is RUNNING without a test-side start() (state %s)" % (str(mm.state) if mm != null else "null"))
	check(mm != null and mm.current_index >= 0, "an objective is active (index %d)" % (mm.current_index if mm != null else -99))
	check(hud != null and hud.mission == mm, "HUD is bound to the running mission")
	game.queue_free()
	await frames(3)
