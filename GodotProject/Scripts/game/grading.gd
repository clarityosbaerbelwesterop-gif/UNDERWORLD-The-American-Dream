# UNDERWORLD - chapter colour grading (T-LOOK-02). A 17^3 3D LUT per chapter, generated in code (no
# binary asset), plugged into Environment.adjustment_color_correction (display-referred, after the
# AgX tonemapper):
#   LA  "golden"  warm gold-orange highlights, gently desaturated cool-neutral shadows
#   NY  "steel"   cool blue-steel mids/shadows, firmer contrast, saturated accents kept (neon, signs)
# grade() is pure, so tests and the look-dev tool can probe single colours.
class_name Grading
extends RefCounted

const SIZE := 17
const CHAPTERS := ["LA", "NY"]
static var _cache := {}

## The LUT for a chapter ("LA" / "NY"); null for an unknown chapter (= no grading).
static func lut(chapter: String) -> Texture3D:
	if not chapter in CHAPTERS:
		return null
	if _cache.has(chapter):
		return _cache[chapter]
	var slices: Array[Image] = []
	for b in SIZE:
		var img := Image.create(SIZE, SIZE, false, Image.FORMAT_RGB8)
		for g in SIZE:
			for r in SIZE:
				img.set_pixel(r, g, grade(chapter, Color(r / (SIZE - 1.0), g / (SIZE - 1.0), b / (SIZE - 1.0))))
		slices.append(img)
	var t := ImageTexture3D.new()
	t.create(Image.FORMAT_RGB8, SIZE, SIZE, SIZE, false, slices)
	_cache[chapter] = t
	return t


static func _luma(c: Color) -> float:
	return 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b


static func _sat(c: Color, s: float) -> Color:
	var l := _luma(c)
	return Color(l + (c.r - l) * s, l + (c.g - l) * s, l + (c.b - l) * s)


## Grades one display-referred colour (0..1 sRGB).
static func grade(chapter: String, c: Color) -> Color:
	var l := _luma(c)
	var hi := smoothstep(0.35, 1.0, l)
	var lo := 1.0 - smoothstep(0.0, 0.45, l)
	var chroma := maxf(c.r, maxf(c.g, c.b)) - minf(c.r, minf(c.g, c.b))
	var dark := smoothstep(0.0, 0.12, l)        # tints fade out towards black (no crushed shadows)
	var o := c
	match chapter:
		"LA":
			o = _sat(o, 1.0 - 0.18 * lo)                                    # quieter shadows
			o += Color(0.045, 0.018, -0.035) * hi                           # golden highlights
			o += Color(0.012, 0.004, -0.010) * (1.0 - hi - lo) * dark              # warm mids
			o += Color(-0.006, 0.0, 0.008) * lo * dark                             # cool-neutral shadows
		"NY":
			var curve := l + 0.06 * sin((l - 0.5) * TAU) * 4.0 * l * (1.0 - l)  # firmer S-curve, ends kept
			var accent := smoothstep(0.4, 0.8, chroma)                       # neon / signs: untouched
			var k := lerpf(curve / maxf(l, 1e-4) if l > 1e-4 else 1.0, 1.0, accent)
			o = Color(o.r * k, o.g * k, o.b * k)
			o = _sat(o, lerpf(0.84, 1.0, smoothstep(0.35, 0.7, chroma)))   # steel, accents survive
			o += Color(-0.022, -0.004, 0.030) * (1.0 - hi) * dark * (1.0 - accent)                  # blue-steel mids/shadows
			o += Color(-0.006, 0.0, 0.010) * hi
		_:
			return c
	return Color(clampf(o.r, 0.0, 1.0), clampf(o.g, 0.0, 1.0), clampf(o.b, 0.0, 1.0))
