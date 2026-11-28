#!/usr/bin/env bash
# UNDERWORLD - T-PIPE-02 import tests (Bot 3): Bot 2's pipeline export -> Godot import preset.
# 1. builds Bot 2's procedural test assets (Tools/underworld_pipeline/tests/make_test_assets.py)
# 2. exports them with Tools/uwp into GodotProject/Tests/_generated/ (gitignored) + a control copy
#    whose .import has NO post-import script
# 3. godot --import (fresh .import files pick up [importer_defaults] from project.godot)
# 4. GodotProject/Tests/Import/test_assets.gd asserts LOD ranges, loop modes, rig, AABBs
# Also checks the vendored uw_lod_post_import.gd is identical to Bot 2's original.
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
. "$REPO/Tests/lib/godot_errors.sh"
BLENDER="${BLENDER:-/workspace/tools/blender/blender}"
GODOT="${GODOT:-/workspace/tools/godot}"
LOGS="$REPO/Tests/logs"; mkdir -p "$LOGS"
GEN="$REPO/GodotProject/Tests/_generated"
SRC="$(mktemp -d /tmp/uw_assetimport.XXXXXX)"
trap 'rm -rf "$SRC"' EXIT
strip() { sed 's/\x1b\[[0-9;]*m//g'; }
fail() { echo "ASSET IMPORT TESTS FAILED: $*"; exit 1; }

cmp -s "$REPO/Tools/underworld_pipeline/godot/uw_lod_post_import.gd" "$REPO/GodotProject/Scripts/import/uw_lod_post_import.gd" \
  || fail "GodotProject/Scripts/import/uw_lod_post_import.gd differs from Tools/underworld_pipeline/godot/ (re-copy it)"
echo "vendored uw_lod_post_import.gd identical to Bot 2's original"

echo "== build + export test assets (Blender, Tools/uwp)"
"$BLENDER" -b --factory-startup --python-exit-code 1 --python "$REPO/Tools/underworld_pipeline/tests/make_test_assets.py" -- --out-dir "$SRC" > "$LOGS/asset_0_make.log" 2>&1 \
  || fail "make_test_assets.py (log $LOGS/asset_0_make.log)"
rm -rf "$GEN"; mkdir -p "$GEN"
exp() { # name category extra-args...
  local n="$1" c="$2"; shift 2
  "$REPO/Tools/uwp" export "$SRC/$n.blend" --category "$c" --no-preview --out "$GEN/$n/$n.glb" "$@" > "$LOGS/asset_export_$n.log" 2>&1 \
    || fail "uwp export $n (log $LOGS/asset_export_$n.log)"
  echo "exported $n"
}
exp PT_UWP_Barrel Props
exp PT_UWP_RigTest Test
exp PT_UWP_Humanoid Characters --budget-key Test
# Control: identical barrel, .import pre-seeded WITHOUT the post-import script.
mkdir -p "$GEN/NoScript"
cp "$GEN/PT_UWP_Barrel/PT_UWP_Barrel.glb" "$GEN/NoScript/"
printf '[remap]\n\nimporter="scene"\ntype="PackedScene"\n\n[params]\n\nimport_script/path=""\n' > "$GEN/NoScript/PT_UWP_Barrel.glb.import"

echo "== godot --import"
"$GODOT" --headless --path "$REPO/GodotProject" --import 2>&1 | strip > "$LOGS/asset_1_import.log"
[ ${PIPESTATUS[0]} -eq 0 ] || fail "godot --import"
errs="$(godot_log_errors "$LOGS/asset_1_import.log")"
if [ -n "$errs" ]; then
  fail "import logged errors:
$errs"
fi
grep -E '^\[UW-IMPORT\]' "$LOGS/asset_1_import.log" | sed 's#res://Tests/_generated/##'

echo "== Import/test_assets.gd"
"$GODOT" --headless --path "$REPO/GodotProject" --script res://Tests/Import/test_assets.gd 2>&1 | strip > "$LOGS/asset_2_test.log"
rc=${PIPESTATUS[0]}
grep -E '^\[ASSETTEST\]' "$LOGS/asset_2_test.log" | grep -vE '^\[ASSETTEST\]\[PASS\]' || true
echo "   $(grep -c '^\[ASSETTEST\]\[PASS\]' "$LOGS/asset_2_test.log") checks passed"
[ $rc -eq 0 ] || fail "test_assets.gd exited $rc (log $LOGS/asset_2_test.log)"
if grep -qE '^(ERROR|SCRIPT ERROR|USER ERROR):' "$LOGS/asset_2_test.log"; then
  grep -E -A3 '^(ERROR|SCRIPT ERROR|USER ERROR):' "$LOGS/asset_2_test.log"; fail "test logged errors"
fi
grep -q '^\[ASSETTEST\] RESULT: PASS' "$LOGS/asset_2_test.log" || fail "result not PASS"
echo "ASSET IMPORT TESTS: PASS"
