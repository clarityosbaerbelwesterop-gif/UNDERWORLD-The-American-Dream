extends SceneTree
## P6 (T-FX-01) - generates Scenes/FX/FX_*.tscn from the table below (data-driven, like the
## Blender generators). GPUParticles3D + ParticleProcessMaterial, procedural textures only
## (GradientTexture2D / NoiseTexture2D), so no binaries enter LFS.
##
##   Tools/uwp build-fx            (= godot --headless --path GodotProject --script res://Scripts/tools/build_fx.gd)
##
## Emitters point along local +Z (an impact is spawned with +Z = surface normal).

const OUT := "res://Scenes/FX/"

# layer: [name, amount, lifetime, explosiveness, velocity (min,max), spread deg, gravity y,
#         scale (start,end), colors [start, mid, end], emissive energy, extra]
const FX := {
	"FX_MuzzleFlash": {"one_shot": true, "lifetime": 0.25, "light": [Color(1.0, 0.7, 0.35), 4.0, 3.5, 0.06], "layers": [
		["Flash", 6, 0.06, 1.0, Vector2(1.5, 3.5), 18.0, 0.0, Vector2(0.16, 0.05), [Color(1, 0.95, 0.7, 1), Color(1, 0.6, 0.15, 0.9), Color(1, 0.3, 0.05, 0)], 6.0, {}],
		["Smoke", 5, 0.6, 0.9, Vector2(0.4, 1.0), 25.0, 0.4, Vector2(0.06, 0.3), [Color(0.6, 0.6, 0.6, 0.35), Color(0.6, 0.6, 0.6, 0.2), Color(0.6, 0.6, 0.6, 0)], 0.0, {}]]},
	"FX_Impact_Concrete": {"one_shot": true, "lifetime": 1.0, "layers": [
		["Dust", 12, 0.8, 0.95, Vector2(0.6, 2.0), 40.0, -0.6, Vector2(0.08, 0.45), [Color(0.72, 0.68, 0.6, 0.6), Color(0.7, 0.66, 0.58, 0.35), Color(0.7, 0.66, 0.58, 0)], 0.0, {}],
		["Chips", 10, 0.6, 1.0, Vector2(2.0, 4.5), 45.0, -9.8, Vector2(0.025, 0.02), [Color(0.35, 0.33, 0.3, 1), Color(0.35, 0.33, 0.3, 1), Color(0.35, 0.33, 0.3, 0)], 0.0, {"hard": true}]]},
	"FX_Impact_Metal": {"one_shot": true, "lifetime": 0.6, "light": [Color(1.0, 0.75, 0.4), 2.0, 2.0, 0.05], "layers": [
		["Sparks", 22, 0.35, 1.0, Vector2(3.0, 7.0), 50.0, -9.8, Vector2(0.03, 0.01), [Color(1, 0.95, 0.7, 1), Color(1, 0.6, 0.2, 1), Color(1, 0.3, 0.05, 0)], 8.0, {"hard": true}]]},
	"FX_Impact_Glass": {"one_shot": true, "lifetime": 1.0, "layers": [
		["Shards", 16, 0.8, 1.0, Vector2(1.5, 4.0), 55.0, -9.8, Vector2(0.03, 0.03), [Color(0.75, 0.88, 0.95, 0.9), Color(0.75, 0.88, 0.95, 0.8), Color(0.75, 0.88, 0.95, 0)], 0.0, {"hard": true}]]},
	"FX_Impact_Wood": {"one_shot": true, "lifetime": 1.0, "layers": [
		["Splinters", 12, 0.7, 1.0, Vector2(1.5, 4.0), 45.0, -9.8, Vector2(0.035, 0.03), [Color(0.55, 0.38, 0.22, 1), Color(0.55, 0.38, 0.22, 1), Color(0.55, 0.38, 0.22, 0)], 0.0, {"hard": true}],
		["Dust", 6, 0.6, 0.9, Vector2(0.4, 1.2), 35.0, -0.5, Vector2(0.06, 0.3), [Color(0.6, 0.48, 0.34, 0.45), Color(0.6, 0.48, 0.34, 0.25), Color(0.6, 0.48, 0.34, 0)], 0.0, {}]]},
	"FX_Blood": {"one_shot": true, "lifetime": 0.8, "layers": [
		["Droplets", 18, 0.5, 1.0, Vector2(1.5, 3.5), 35.0, -9.8, Vector2(0.03, 0.02), [Color(0.45, 0.02, 0.02, 1), Color(0.35, 0.01, 0.01, 1), Color(0.3, 0.0, 0.0, 0)], 0.0, {"hard": true}],
		["Mist", 6, 0.35, 1.0, Vector2(0.5, 1.5), 30.0, -1.0, Vector2(0.08, 0.3), [Color(0.5, 0.03, 0.03, 0.6), Color(0.4, 0.02, 0.02, 0.3), Color(0.4, 0.02, 0.02, 0)], 0.0, {}]]},
	"FX_Sparks": {"one_shot": false, "lifetime": 1.0, "layers": [
		["Sparks", 24, 0.45, 0.2, Vector2(2.0, 5.0), 60.0, -9.8, Vector2(0.025, 0.01), [Color(1, 0.95, 0.75, 1), Color(1, 0.6, 0.2, 1), Color(1, 0.3, 0.05, 0)], 8.0, {"hard": true}]]},
	"FX_GlassShatter": {"one_shot": true, "lifetime": 1.6, "layers": [
		["Shards", 48, 1.2, 1.0, Vector2(1.0, 4.0), 70.0, -9.8, Vector2(0.06, 0.05), [Color(0.78, 0.9, 0.96, 0.9), Color(0.78, 0.9, 0.96, 0.8), Color(0.78, 0.9, 0.96, 0)], 0.0, {"hard": true}]]},
	"FX_Smoke": {"one_shot": false, "lifetime": 1.0, "layers": [
		["Smoke", 28, 4.0, 0.0, Vector2(0.6, 1.2), 12.0, 0.25, Vector2(0.5, 2.6), [Color(0.3, 0.3, 0.3, 0.55), Color(0.35, 0.35, 0.35, 0.35), Color(0.4, 0.4, 0.4, 0)], 0.0, {"noise": true}]]},
	"FX_Fire": {"one_shot": false, "lifetime": 1.0, "light": [Color(1.0, 0.55, 0.2), 3.0, 6.0, 0.0], "layers": [
		["Flames", 40, 0.8, 0.0, Vector2(0.8, 1.6), 10.0, 1.2, Vector2(0.5, 0.15), [Color(1, 0.85, 0.4, 0.95), Color(1, 0.4, 0.08, 0.8), Color(0.6, 0.1, 0.02, 0)], 5.0, {"box": Vector3(0.4, 0.4, 0.05), "noise": true}],
		["Embers", 12, 1.5, 0.0, Vector2(0.8, 2.0), 25.0, 0.6, Vector2(0.02, 0.01), [Color(1, 0.7, 0.3, 1), Color(1, 0.4, 0.1, 1), Color(1, 0.3, 0.05, 0)], 6.0, {"hard": true}],
		["Smoke", 10, 3.0, 0.0, Vector2(0.6, 1.0), 10.0, 0.4, Vector2(0.6, 2.0), [Color(0.15, 0.15, 0.15, 0.0), Color(0.18, 0.18, 0.18, 0.45), Color(0.25, 0.25, 0.25, 0)], 0.0, {"noise": true}]]},
	"FX_Explosion": {"one_shot": true, "lifetime": 4.0, "light": [Color(1.0, 0.6, 0.25), 16.0, 14.0, 0.45], "layers": [
		["Fireball", 28, 0.7, 1.0, Vector2(2.0, 6.0), 180.0, 0.5, Vector2(1.2, 2.8), [Color(1, 0.9, 0.55, 1), Color(1, 0.45, 0.1, 0.9), Color(0.3, 0.08, 0.02, 0)], 7.0, {"noise": true}],
		["Smoke", 24, 3.5, 0.9, Vector2(1.0, 3.0), 180.0, 0.6, Vector2(1.5, 4.5), [Color(0.12, 0.12, 0.12, 0.8), Color(0.2, 0.2, 0.2, 0.55), Color(0.3, 0.3, 0.3, 0)], 0.0, {"noise": true}],
		["Debris", 30, 1.6, 1.0, Vector2(5.0, 12.0), 180.0, -9.8, Vector2(0.06, 0.05), [Color(0.2, 0.18, 0.16, 1), Color(0.2, 0.18, 0.16, 1), Color(0.2, 0.18, 0.16, 0)], 0.0, {"hard": true}]]},
	"FX_Rain": {"one_shot": false, "lifetime": 1.0, "layers": [
		["Rain", 2400, 1.0, 0.0, Vector2(16.0, 20.0), 2.0, 0.0, Vector2(1.0, 1.0), [Color(0.75, 0.8, 0.85, 0.35), Color(0.75, 0.8, 0.85, 0.35), Color(0.75, 0.8, 0.85, 0.0)], 0.0, {"box": Vector3(25, 25, 0.1), "streak": true, "down": true}]]},
	"FX_Steam_NY": {"one_shot": false, "lifetime": 1.0, "layers": [
		["Steam", 30, 3.0, 0.0, Vector2(1.0, 1.6), 14.0, 0.3, Vector2(0.4, 2.2), [Color(0.95, 0.95, 0.95, 0.5), Color(0.95, 0.95, 0.95, 0.3), Color(0.95, 0.95, 0.95, 0)], 0.0, {"noise": true, "box": Vector3(0.35, 0.35, 0.05)}]]},
	"FX_TireSmoke": {"one_shot": false, "lifetime": 1.0, "layers": [
		["Smoke", 26, 2.2, 0.0, Vector2(0.3, 0.9), 50.0, 0.2, Vector2(0.4, 2.0), [Color(0.9, 0.9, 0.9, 0.55), Color(0.9, 0.9, 0.9, 0.3), Color(0.9, 0.9, 0.9, 0)], 0.0, {"noise": true}]]},
}

func _initialize() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT))
	var ok := 0
	for id in FX:
		if _build(id, FX[id]):
			ok += 1
	print("[FX] built %d/%d effects into %s" % [ok, FX.size(), OUT])
	quit(0 if ok == FX.size() else 1)

func _build(id: String, d: Dictionary) -> bool:
	var root := Node3D.new()
	root.name = id
	root.set_script(load("res://Scripts/fx/fx_effect.gd"))
	root.set("one_shot", d["one_shot"])
	root.set("lifetime", d["lifetime"])
	for L in d["layers"]:
		root.add_child(_layer(L, d["one_shot"]))
	if d.has("light"):
		var li := OmniLight3D.new()
		li.name = "Flash"
		var spec: Array = d["light"]
		li.light_color = spec[0]
		li.light_energy = spec[1]
		li.omni_range = spec[2]
		li.shadow_enabled = false
		root.set("light_energy", spec[1])
		root.set("light_fade", spec[3])
		li.position = Vector3(0, 0, 0.15)
		root.add_child(li)
	for c in root.get_children():
		c.owner = root
	var ps := PackedScene.new()
	var err := ps.pack(root)
	if err == OK:
		err = ResourceSaver.save(ps, OUT + id + ".tscn")
	root.free()
	print("[FX] %s -> %s (err %d)" % [id, OUT + id + ".tscn", err])
	return err == OK

func _layer(L: Array, one_shot: bool) -> GPUParticles3D:
	var extra: Dictionary = L[10]
	var p := GPUParticles3D.new()
	p.name = L[0]
	p.amount = L[1]
	p.lifetime = L[2]
	p.explosiveness = L[3]
	p.one_shot = one_shot
	p.emitting = false
	p.local_coords = false
	p.visibility_aabb = AABB(Vector3(-30, -30, -30), Vector3(60, 60, 60)) if extra.get("box", Vector3.ZERO).x > 5 else AABB(Vector3(-6, -6, -6), Vector3(12, 12, 12))
	var pm := ParticleProcessMaterial.new()
	var dir := Vector3(0, 0, 1)
	if extra.get("down", false):
		dir = Vector3(0, -1, 0)
	pm.direction = dir
	pm.spread = L[5]
	pm.initial_velocity_min = (L[4] as Vector2).x
	pm.initial_velocity_max = (L[4] as Vector2).y
	pm.gravity = Vector3(0, L[6], 0)
	pm.damping_min = 0.5 if not extra.get("hard", false) else 0.0
	pm.damping_max = 1.5 if not extra.get("hard", false) else 0.2
	var sc := L[7] as Vector2
	var curve := Curve.new()
	curve.add_point(Vector2(0, 1.0))
	curve.add_point(Vector2(1, clampf(sc.y / maxf(sc.x, 0.001), 0.0, 1.0) if sc.y < sc.x else 1.0))
	var sct := CurveTexture.new()
	sct.curve = curve
	pm.scale_min = sc.x if sc.y <= sc.x else sc.x
	pm.scale_max = sc.x * 1.25 if sc.y <= sc.x else sc.x * 1.25
	if sc.y > sc.x:                         # growing puffs: scale curve 1 -> end/start
		var grow := Curve.new()
		grow.max_value = sc.y / sc.x
		grow.add_point(Vector2(0, 1.0))
		grow.add_point(Vector2(1, sc.y / sc.x))
		sct.curve = grow
	pm.scale_curve = sct
	var cols: Array = L[8]
	var g := Gradient.new()
	g.set_color(0, cols[0])
	g.set_color(1, cols[2])
	g.add_point(0.4, cols[1])
	var gt := GradientTexture1D.new()
	gt.gradient = g
	pm.color_ramp = gt
	if extra.has("box"):
		pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
		pm.emission_box_extents = extra["box"]
	pm.angle_min = -180.0
	pm.angle_max = 180.0
	pm.angular_velocity_min = -40.0
	pm.angular_velocity_max = 40.0
	p.process_material = pm
	var mesh := QuadMesh.new()
	mesh.size = Vector2(0.015, 0.6) if extra.get("streak", false) else Vector2(1, 1)
	var mat := StandardMaterial3D.new()
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED if float(L[9]) > 0.0 or extra.get("streak", false) else BaseMaterial3D.SHADING_MODE_PER_PIXEL
	mat.vertex_color_use_as_albedo = true
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y if extra.get("streak", false) else BaseMaterial3D.BILLBOARD_PARTICLES
	mat.billboard_keep_scale = true
	mat.albedo_texture = _soft_texture(extra.get("hard", false), extra.get("noise", false))
	if float(L[9]) > 0.0:
		mat.emission_enabled = true
		mat.emission = (cols[0] as Color)
		mat.emission_energy_multiplier = L[9]
		mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mesh.material = mat
	p.draw_pass_1 = mesh
	return p

## Radial soft disc (puffs), hard disc (chips/sparks) or noise-broken puff (smoke/fire/steam).
func _soft_texture(hard: bool, noise: bool) -> Texture2D:
	var g := Gradient.new()
	if hard:
		g.set_color(0, Color(1, 1, 1, 1))
		g.set_color(1, Color(1, 1, 1, 0))
		g.add_point(0.55, Color(1, 1, 1, 1))
	else:
		g.set_color(0, Color(1, 1, 1, 1))
		g.set_color(1, Color(1, 1, 1, 0))
		g.add_point(0.35, Color(1, 1, 1, 0.75))
	var t := GradientTexture2D.new()
	t.gradient = g
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(1.0, 0.5)
	t.width = 64
	t.height = 64
	if not noise:
		return t
	# noise-broken puff: multiply a radial falloff with simplex noise (baked once into an Image)
	var n := FastNoiseLite.new()
	n.frequency = 0.08
	n.seed = 7
	var img := Image.create(64, 64, false, Image.FORMAT_RGBA8)
	for y in 64:
		for x in 64:
			var r := Vector2(x - 31.5, y - 31.5).length() / 32.0
			var a := clampf(1.0 - r, 0.0, 1.0)
			a = a * a * (0.55 + 0.45 * (n.get_noise_2d(x, y) * 0.5 + 0.5))
			img.set_pixel(x, y, Color(1, 1, 1, a))
	return ImageTexture.create_from_image(img)
