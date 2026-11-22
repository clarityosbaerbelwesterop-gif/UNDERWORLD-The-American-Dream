#!/usr/bin/env bash
# UNDERWORLD - end-to-end Blender -> glTF -> Godot pipeline smoke test.
# Fails (non-zero exit) on any export error, import error, script error or
# failed assertion. Logs go to Tests/logs/ (gitignored).
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BLENDER="${BLENDER:-/workspace/tools/blender/blender}"
GODOT="${GODOT:-/workspace/tools/godot}"
LOGS="$REPO/Tests/logs"
mkdir -p "$LOGS"
strip() { sed 's/\x1b\[[0-9;]*m//g'; }
fail() { echo "SMOKE TEST FAILED: $*"; exit 1; }

[ -x "$BLENDER" ] || fail "Blender not found at $BLENDER (see /workspace/tools/README.md)"
[ -x "$GODOT" ]   || fail "Godot not found at $GODOT (see /workspace/tools/README.md)"
echo "Blender: $("$BLENDER" -b --factory-startup --version 2>/dev/null | head -1)"
echo "Godot:   $("$GODOT" --headless --version 2>/dev/null | tail -1)"

echo "== [1/3] Blender headless export"
"$BLENDER" -b --factory-startup --python-exit-code 1 \
  --python "$REPO/Tools/blender_export.py" -- --repo "$REPO" 2>&1 | strip > "$LOGS/1_blender_export.log"
rc=${PIPESTATUS[0]}
grep -E '^\[PIPELINE\]' "$LOGS/1_blender_export.log"
[ $rc -eq 0 ] || fail "Blender export exited $rc (log: $LOGS/1_blender_export.log)"
grep -q '^\[PIPELINE\]\[OK\]' "$LOGS/1_blender_export.log" || fail "Blender export did not report OK"
grep -qE 'Traceback|^\[PIPELINE\]\[ERROR\]' "$LOGS/1_blender_export.log" && fail "Blender export logged errors"

echo "== [2/3] Godot headless import"
"$GODOT" --headless --path "$REPO/GodotProject" --import 2>&1 | strip > "$LOGS/2_godot_import.log"
rc=${PIPESTATUS[0]}
[ $rc -eq 0 ] || fail "Godot import exited $rc (log: $LOGS/2_godot_import.log)"
if grep -qE '^(ERROR|SCRIPT ERROR|USER ERROR):' "$LOGS/2_godot_import.log"; then
  grep -E -A3 '^(ERROR|SCRIPT ERROR|USER ERROR):' "$LOGS/2_godot_import.log"
  fail "Godot import logged errors"
fi
[ -f "$REPO/Assets/Test/PT_PipelineTest_Crate.glb.import" ] || fail "no .import file generated for test asset"
echo "import OK"

echo "== [3/3] Godot scene smoke test"
"$GODOT" --headless --path "$REPO/GodotProject" --script res://Tests/smoke_test.gd 2>&1 | strip > "$LOGS/3_godot_smoke.log"
rc=${PIPESTATUS[0]}
grep -E '^\[SMOKE\]' "$LOGS/3_godot_smoke.log"
[ $rc -eq 0 ] || fail "Godot smoke test exited $rc"
if grep -qE '^(ERROR|SCRIPT ERROR|USER ERROR):' "$LOGS/3_godot_smoke.log"; then
  grep -E -A3 '^(ERROR|SCRIPT ERROR|USER ERROR):' "$LOGS/3_godot_smoke.log"
  fail "Godot smoke test logged engine errors"
fi
grep -q '^\[SMOKE\] RESULT: PASS' "$LOGS/3_godot_smoke.log" || fail "smoke result not PASS"

echo "PIPELINE SMOKE TEST: PASS"
