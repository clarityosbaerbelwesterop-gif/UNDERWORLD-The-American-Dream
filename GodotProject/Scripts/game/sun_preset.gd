# UNDERWORLD - key light presets (T-LOOK-01, TD-023). ONE source for the sun/moon used by the level
# generator and the look-dev scene, paired 1:1 with Assets/Environments/ENV_LA_<Preset>.tres.
# Before this, build_level_calloway.gd carried its own sun + an inline Environment that did not
# match the look-dev presets (FILMIC vs ACES, 2x the fog density) - the game never showed the look.
class_name SunPreset
extends RefCounted

## preset -> [elevation_deg, azimuth_deg, colour, energy, shadow_max_distance_m]
## Azimuth: 0 = sun in the -Z (north in level space), 90 = +X ... matches rotation_degrees.y.
const PRESETS := {
	# LA golden hour: low western sun ~12 deg, ~3500 K warm key, long shadows.
	"golden_hour": [12.0, 250.0, Color(1.0, 0.80, 0.58), 1.6, 150.0],
	# LA midday: high, near-neutral (~5600 K) key.
	"midday": [62.0, 200.0, Color(1.0, 0.97, 0.93), 2.2, 120.0],
	# Night: cold moon key, very low; street practicals carry the scene.
	"night": [35.0, 120.0, Color(0.58, 0.68, 1.0), 0.35, 80.0],
}

const ENVIRONMENTS := {
	"golden_hour": "res://Assets/Environments/ENV_LA_GoldenHour.tres",
	"midday": "res://Assets/Environments/ENV_LA_Midday.tres",
	"night": "res://Assets/Environments/ENV_LA_Night.tres",
}

static func make_sun(preset: String) -> DirectionalLight3D:
	var p: Array = PRESETS.get(preset, PRESETS["golden_hour"])
	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	sun.rotation_degrees = Vector3(-float(p[0]), float(p[1]), 0.0)
	sun.light_color = p[2]
	sun.light_energy = float(p[3])
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	sun.directional_shadow_max_distance = float(p[4])
	sun.directional_shadow_blend_splits = true
	sun.shadow_bias = 0.03
	sun.shadow_normal_bias = 1.0
	return sun

static func environment(preset: String) -> Environment:
	return load(ENVIRONMENTS.get(preset, ENVIRONMENTS["golden_hour"])) as Environment
