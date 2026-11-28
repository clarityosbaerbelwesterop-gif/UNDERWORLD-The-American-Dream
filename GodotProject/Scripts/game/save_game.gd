# UNDERWORLD - checkpoint save files on disk (T-SAVE-01).
#
# One slot = one JSON file under user://saves/<slot>.json. MissionManager writes it every time a
# checkpoint objective completes and deletes it when the mission is passed; GameBoot reads it on
# start and continues from that checkpoint (TD-035).
#
# File layout (version 1):
#   { "format": "UW_SAVE", "version": 1, "checksum": "<sha256 of payload>", "payload": "<json>" }
# The payload is kept as a string so the checksum covers exactly the bytes that were written
# (no float re-serialisation drift). A file that is missing, not JSON, from another format or
# version, or whose checksum does not match is rejected: read() returns {} and the game starts a
# new mission instead of loading half a state.
#
# Writes are atomic: the JSON goes to <slot>.json.tmp first and is renamed over the old file, so
# a crash or power loss during a save leaves the previous checkpoint intact.
#
# Tests isolate their files with UW_SAVE_DIR (debug builds only, TD-020).
# Negative control UW_SAVE_SABOTAGE=3: read() skips the checksum -> corrupted files load.
class_name SaveGame
extends RefCounted

const FORMAT := "UW_SAVE"
const VERSION := 1
const DEFAULT_DIR := "user://saves"

static func sabotage() -> int:
	if not OS.is_debug_build():
		return 0
	var s := OS.get_environment("UW_SAVE_SABOTAGE").strip_edges()
	return int(s) if s.is_valid_int() else 0

static func save_dir() -> String:
	if OS.is_debug_build():
		var d := OS.get_environment("UW_SAVE_DIR").strip_edges()
		if d != "":
			return d
	return DEFAULT_DIR

static func path(slot: String) -> String:
	return save_dir().path_join(slot + ".json")

static func _valid_slot(slot: String) -> bool:
	return slot != "" and slot.is_valid_filename() and not slot.contains("/")

static func exists(slot: String) -> bool:
	return _valid_slot(slot) and FileAccess.file_exists(path(slot))

static func delete(slot: String) -> void:
	if exists(slot):
		DirAccess.remove_absolute(path(slot))

## Write `data` (JSON-compatible Dictionary) to the slot. Returns OK or the failing Error.
static func write(slot: String, data: Dictionary) -> Error:
	if not _valid_slot(slot):
		return ERR_INVALID_PARAMETER
	var dir := save_dir()
	if not DirAccess.dir_exists_absolute(dir):
		var mk := DirAccess.make_dir_recursive_absolute(dir)
		if mk != OK:
			return mk
	var payload := JSON.stringify(data, "", true, true)
	var wrapper := {
		"format": FORMAT,
		"version": VERSION,
		"checksum": payload.sha256_text(),
		"payload": payload,
	}
	var final_path := path(slot)
	var tmp := final_path + ".tmp"
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		return FileAccess.get_open_error()
	f.store_string(JSON.stringify(wrapper, "\t"))
	f.flush()
	f.close()
	return DirAccess.rename_absolute(tmp, final_path)

## Read a slot. Returns {} if there is no valid save (missing, corrupt, wrong format/version).
static func read(slot: String) -> Dictionary:
	if not exists(slot):
		return {}
	var text := FileAccess.get_file_as_string(path(slot))
	# JSON.new().parse() reports a broken file through its return value; JSON.parse_string()
	# would log an engine ERROR for what is an expected, handled case (truncated file).
	var json := JSON.new()
	var wrapper = json.data if json.parse(text) == OK else null
	if typeof(wrapper) != TYPE_DICTIONARY:
		push_warning("SaveGame: %s is not JSON - ignored" % path(slot))
		return {}
	if wrapper.get("format", "") != FORMAT or int(wrapper.get("version", -1)) != VERSION:
		push_warning("SaveGame: %s has format %s v%s, expected %s v%d - ignored" % [path(slot),
			str(wrapper.get("format", "?")), str(wrapper.get("version", "?")), FORMAT, VERSION])
		return {}
	var payload = wrapper.get("payload", null)
	if typeof(payload) != TYPE_STRING:
		push_warning("SaveGame: %s has no payload - ignored" % path(slot))
		return {}
	if sabotage() != 3 and String(payload).sha256_text() != String(wrapper.get("checksum", "")):
		push_warning("SaveGame: %s checksum mismatch (corrupt) - ignored" % path(slot))
		return {}
	var data = json.data if json.parse(payload) == OK else null
	if typeof(data) != TYPE_DICTIONARY:
		push_warning("SaveGame: %s payload is not a Dictionary - ignored" % path(slot))
		return {}
	return data

# --- JSON helpers for engine types ----------------------------------------------

static func vec3_to_json(v: Vector3) -> Array:
	return [v.x, v.y, v.z]

static func vec3_from_json(a, fallback := Vector3.ZERO) -> Vector3:
	if typeof(a) != TYPE_ARRAY or (a as Array).size() != 3:
		return fallback
	return Vector3(float(a[0]), float(a[1]), float(a[2]))

static func basis_to_json(b: Basis) -> Array:
	return [b.x.x, b.x.y, b.x.z, b.y.x, b.y.y, b.y.z, b.z.x, b.z.y, b.z.z]

static func basis_from_json(a, fallback := Basis.IDENTITY) -> Basis:
	if typeof(a) != TYPE_ARRAY or (a as Array).size() != 9:
		return fallback
	return Basis(Vector3(float(a[0]), float(a[1]), float(a[2])),
		Vector3(float(a[3]), float(a[4]), float(a[5])),
		Vector3(float(a[6]), float(a[7]), float(a[8]))).orthonormalized()
