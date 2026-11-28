#!/usr/bin/env bash
# UNDERWORLD - headless gameplay regression tests (Bot 3).
# Imports the Godot project (so class_name scripts resolve on a fresh clone),
# then runs every GodotProject/Tests/test_*.gd (top level only; Tests/Import/ = run_asset_import_tests.sh) with a fixed 60 fps timestep.
# Fails (non-zero) on a failed assertion, a non-PASS result or any engine/script error.
# Logs: Tests/logs/gameplay_*.log (gitignored).
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
. "$REPO/Tests/lib/godot_errors.sh"
GODOT="${GODOT:-/workspace/tools/godot}"
LOGS="$REPO/Tests/logs"
mkdir -p "$LOGS"
strip() { sed 's/\x1b\[[0-9;]*m//g'; }
fail() { echo "GAMEPLAY TESTS FAILED: $*"; exit 1; }

[ -x "$GODOT" ] || fail "Godot not found at $GODOT (see /workspace/tools/README.md)"
echo "Godot: $("$GODOT" --headless --version 2>/dev/null | tail -1)"

echo "== Godot headless import"
"$GODOT" --headless --path "$REPO/GodotProject" --import 2>&1 | strip > "$LOGS/gameplay_0_import.log"
rc=${PIPESTATUS[0]}
[ $rc -eq 0 ] || fail "Godot import exited $rc (log: $LOGS/gameplay_0_import.log)"
errs="$(godot_log_errors "$LOGS/gameplay_0_import.log")"
[ -z "$errs" ] || fail "Godot import logged errors:
$errs"

shopt -s nullglob
tests=("$REPO"/GodotProject/Tests/test_*.gd)
[ ${#tests[@]} -gt 0 ] || fail "no GodotProject/Tests/test_*.gd found"
for t in "${tests[@]}"; do
  name="$(basename "$t" .gd)"
  log="$LOGS/gameplay_${name}.log"
  echo "== $name"
  # T-SAVE-01: every test gets its own empty save dir, so a checkpoint written by one test (or by
  # a real play session in user://) can never change how GameBoot starts in another.
  save_dir="$(mktemp -d)"
  UW_SAVE_DIR="$save_dir" timeout 600 "$GODOT" --headless --fixed-fps 60 --path "$REPO/GodotProject" --script "res://Tests/$name.gd" 2>&1 | strip > "$log"
  rc=${PIPESTATUS[0]}
  rm -rf "$save_dir"
  grep -E '^\[GPTEST\]' "$log" | grep -vE '^\[GPTEST\]\[PASS\]' || true
  echo "   $(grep -c '^\[GPTEST\]\[PASS\]' "$log") checks passed"
  [ $rc -eq 0 ] || fail "$name exited $rc (log: $log)"
  if grep -qE '^(ERROR|SCRIPT ERROR|USER ERROR):' "$log"; then
    grep -E -A3 '^(ERROR|SCRIPT ERROR|USER ERROR):' "$log"
    fail "$name logged engine/script errors"
  fi
  grep -q '^\[GPTEST\] RESULT: PASS' "$log" || fail "$name result not PASS"
done

echo "GAMEPLAY TESTS: PASS"
