extends SceneTree
## P6 (T-FX-01) - every Scenes/FX effect rendered IN ENGINE (Forward Plus) at its telling moment,
## against a dark wall + floor at dusk light (particles read best there), one PNG per effect.
##   UW_CAPTURE_DIR=/abs/dir Tools/godot_phase8_capture.sh --renderer fwdplus --res 640x360 \
##       --fixed-fps 30 --script res://Tests/tools/capture_fx.gd
## Look only (GPU particles on lavapipe = CPU), never performance.

const SUN := preload("res://Scripts/game/sun_preset.gd")
# id: [seconds after spawn to shoot, camera distance, effect height, rotate +Z to]
const SHOTS := {
	"FX_MuzzleFlash": [0.033, 1.0, 1.2, "side"], "FX_Impact_Concrete": [0.12, 2.0, 1.2, "wall"],
	"FX_Impact_Metal": [0.08, 2.0, 1.2, "wall"], "FX_Impact_Glass": [0.15, 2.0, 1.2, "wall"],
	"FX_Impact_Wood": [0.12, 2.0, 1.2, "wall"], "FX_Blood": [0.1, 2.0, 1.3, "wall"],
	"FX_Sparks": [1.0, 3.0, 1.5, "up"], "FX_GlassShatter": [0.25, 4.0, 1.5, "wall"],
	"FX_Smoke": [3.0, 9.0, 0.0, "up"], "FX_Fire": [1.5, 5.0, 0.0, "up"], "FX_Explosion": [0.25, 12.0, 1.0, "up"],
	"FX_Rain": [1.5, 6.0, 0.0, "none"], "FX_Steam_NY": [2.5, 7.0, 0.0, "up"], "FX_TireSmoke": [2.0, 6.0, 0.0, "up"],
}

func _initialize() -> void:
	_run()

func secs(s: float) -> void:
	var t := 0.0
	while t < s:
		await process_frame
		t += 1.0 / 30.0

func _run() -> void:
	var out := OS.get_environment("UW_CAPTURE_DIR")
	if out == "":
		out = "/tmp/uw_fx"
	DirAccess.make_dir_recursive_absolute(out)
	var stage := Node3D.new()
	root.add_child(stage)
	var sun := SUN.make_sun("midday")
	stage.add_child(sun)
	var we := WorldEnvironment.new()
	we.environment = (SUN.environment("midday") as Environment).duplicate()
	stage.add_child(we)
	const GLOWING := ["FX_MuzzleFlash", "FX_Impact_Metal", "FX_Sparks", "FX_Fire", "FX_Explosion"]
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.25, 0.24, 0.23)
	for spec in [[Vector3(40, 0.1, 40), Vector3(0, -0.05, 0)], [Vector3(40, 12, 0.2), Vector3(0, 6, -0.1)]]:
		var mi := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = spec[0]
		mi.mesh = bm
		mi.material_override = mat
		mi.position = spec[1]
		stage.add_child(mi)
	var cam := Camera3D.new()
	stage.add_child(cam)
	cam.make_current()
	await secs(0.5)                       # warm-up: the first frames on lavapipe compile shaders (black)
	var only := OS.get_environment("UW_FX_ONLY").split(",", false)
	for id in SHOTS:
		if not only.is_empty() and not only.has(id):
			continue
		var s: Array = SHOTS[id]
		var preset := "night" if id in GLOWING else "midday"   # glowing FX read at night, dust/smoke by day
		sun.queue_free()
		sun = SUN.make_sun(preset)
		stage.add_child(sun)
		we.environment = (SUN.environment(preset) as Environment).duplicate()
		var basis := Basis.IDENTITY                                        # +Z out of the wall
		if s[3] == "up":
			basis = Basis(Vector3.RIGHT, -PI / 2)                          # +Z -> +Y
		elif s[3] == "side":
			basis = Basis(Vector3.UP, PI / 2)                              # +Z -> +X (muzzle)
		var fx := FXEffect.spawn(id, stage, Transform3D(basis, Vector3(0, s[2], 0.05)))
		var d: float = s[1]
		cam.fov = 50
		cam.position = Vector3(d * 0.55, s[2] + d * 0.25 + 0.3, d * 0.85)
		cam.look_at(Vector3(0, s[2] + (d * 0.15 if s[3] == "up" else 0.0), 0), Vector3.UP)
		await secs(s[0])
		root.get_viewport().get_texture().get_image().save_png(out.path_join("%s.png" % id))
		print("[FX_SHOT] ", id)
		if is_instance_valid(fx):
			fx.queue_free()
		await secs(0.2)
	quit(0)
