#!/usr/bin/env bash
# SK_Jason delivery verification (Bot 2, T-ART-01/02):
#  1. Tools/uwp validate on the .blend (must PASS)
#  2. Blender re-import of the exported .glb (bones, actions, frame ranges)  [verify_sk_jason_blender.py]
#  3. Godot headless import in a throw-away project with the project's real import scripts
#     (GodotProject/Scripts/import/uw_post_import.gd -> loop modes from the manifest) and
#     verify_sk_jason_godot.gd (skeleton/profile, height, +Z front, socket, lengths, loops, in place).
# Repo is not modified. Exit 0 + "SK_JASON VERIFY: PASS" on success.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
BLENDER="${BLENDER:-/workspace/tools/blender/blender}"
GODOT="${GODOT:-/workspace/tools/godot}"
A="$REPO/Assets/Characters/SK_Jason"
T="$(mktemp -d /tmp/sk_jason_verify.XXXXXX)"
FAILS=0
step() { if [ "$1" -eq 0 ]; then echo "[SK_JASON][PASS] $2"; else echo "[SK_JASON][FAIL] $2 (rc=$1, log $3)"; FAILS=$((FAILS+1)); fi; }

"$REPO/Tools/uwp" validate "$REPO/Blender/Source/Characters/SK_Jason/SK_Jason.blend" > "$T/validate.log" 2>&1
step $? "uwp validate SK_Jason.blend" "$T/validate.log"; grep -E '^\[UWP\]\[(ERROR|WARN)\]|RESULT' "$T/validate.log"

"$BLENDER" -b --factory-startup --python "$HERE/verify_sk_jason_blender.py" -- "$A/SK_Jason.glb" "$A/SK_Jason.manifest.json" > "$T/blender.log" 2>&1
step $? "Blender re-import" "$T/blender.log"; grep -E '^\[JASON-BLENDER\]' "$T/blender.log"

G="$T/godot"; mkdir -p "$G/assets/Characters/SK_Jason" "$G/Scripts/import"
printf 'config_version=5\n\n[application]\n\nconfig/name="sk_jason_verify"\n' > "$G/project.godot"
cp "$REPO/GodotProject/Scripts/import/uw_post_import.gd" "$REPO/GodotProject/Scripts/import/uw_lod_post_import.gd" "$G/Scripts/import/"
cp "$HERE/verify_sk_jason_godot.gd" "$G/"
cp "$A/SK_Jason.glb" "$A/SK_Jason.manifest.json" "$G/assets/Characters/SK_Jason/"
printf '[remap]\n\nimporter="scene"\ntype="PackedScene"\n\n[params]\n\nimport_script/path="res://Scripts/import/uw_post_import.gd"\n' > "$G/assets/Characters/SK_Jason/SK_Jason.glb.import"
"$GODOT" --headless --path "$G" --import > "$T/godot_import.log" 2>&1
rc=$?
if [ $rc -eq 0 ] && ! grep -qE '^(ERROR|SCRIPT ERROR|USER ERROR):' "$T/godot_import.log"; then step 0 "Godot import, 0 errors" ""; else step 1 "Godot import" "$T/godot_import.log"; grep -E -A2 '^(ERROR|SCRIPT ERROR|USER ERROR):' "$T/godot_import.log" | head; fi
grep -E '^\[UW-IMPORT\]' "$T/godot_import.log"
python3 - "$A/SK_Jason.manifest.json" "$G/expect.json" "$HERE/expected_bones.txt" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
bones = [l.strip() for l in open(sys.argv[3]) if l.strip()]
json.dump({"path": "res://assets/Characters/SK_Jason/SK_Jason.glb", "bones": bones,
           "animations": {a["name"]: [a["duration_s"], a["loop"]] for a in m["animations"]}}, open(sys.argv[2], "w"))
# Godot's scene importer strips a trailing _loop/-loop/_cycle/-cycle (any case) from animation names
# (TD-005 addendum, uwp NAME_ACTION_LOOP); should one slip through, the Godot check accepts the stripped name but reports [WARN].
PY
"$GODOT" --headless --path "$G" --script res://verify_sk_jason_godot.gd -- "$G/expect.json" > "$T/godot_verify.log" 2>&1
rc=$?; grep -E '^\[JASON-GODOT\]' "$T/godot_verify.log"
WARNS=$(grep -c '^\[JASON-GODOT\]\[WARN\]' "$T/godot_verify.log")
grep -qE '^(SCRIPT ERROR|USER ERROR):' "$T/godot_verify.log" && { grep -E -A3 '^(SCRIPT ERROR|USER ERROR):' "$T/godot_verify.log"; rc=1; }
step $rc "Godot verify" "$T/godot_verify.log"
echo "logs: $T"
if [ $FAILS -eq 0 ]; then echo "SK_JASON VERIFY: PASS (godot warnings: $WARNS)"; exit 0; else echo "SK_JASON VERIFY: FAIL ($FAILS)"; exit 1; fi
