#!/usr/bin/env bash
# UNDERWORLD - full headless regression suite = merge gate for main (TD-010).
#   1. pipeline smoke (T-PIPE-00)          3. asset import tests (T-PIPE-02)
#   2. pipeline tool tests (T-PIPE-01, Bot 2: Tools/underworld_pipeline/tests/run_tests.sh)
#   4. gameplay tests (T-GP-*)
# Prints "RUN_ALL: PASS" on success.
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$DIR/.." && pwd)"
"$DIR/run_pipeline_smoke.sh" || { echo "RUN_ALL: FAIL (pipeline smoke)"; exit 1; }
# Private scratch dir so parallel runs from other worktrees don't collide in /tmp/uwp_test.
UWP_DIR="$(mktemp -d /tmp/uwp_test_runall.XXXXXX)"
trap 'rm -rf "$UWP_DIR"' EXIT
echo "== pipeline tool tests (Tools/underworld_pipeline/tests/run_tests.sh)"
UWP_TEST_DIR="$UWP_DIR" "$REPO/Tools/underworld_pipeline/tests/run_tests.sh" > "$REPO/Tests/logs/uwp_tool_tests.log" 2>&1
rc=$?
grep -E '^\[TEST\]\[FAIL\]|^UWP TESTS' "$REPO/Tests/logs/uwp_tool_tests.log"
[ $rc -eq 0 ] || { echo "RUN_ALL: FAIL (pipeline tool tests, log Tests/logs/uwp_tool_tests.log)"; exit 1; }
"$DIR/run_asset_import_tests.sh" || { echo "RUN_ALL: FAIL (asset import)"; exit 1; }
"$DIR/run_gameplay_tests.sh" || { echo "RUN_ALL: FAIL (gameplay)"; exit 1; }
echo "RUN_ALL: PASS"
