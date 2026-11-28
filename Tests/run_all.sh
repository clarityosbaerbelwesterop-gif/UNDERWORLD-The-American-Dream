#!/usr/bin/env bash
# UNDERWORLD - full headless regression suite = merge gate for main (TD-010).
#   1. pipeline smoke (T-PIPE-00)          3. asset import tests (T-PIPE-02)
#   2. pipeline tool tests (T-PIPE-01, Bot 2: Tools/underworld_pipeline/tests/run_tests.sh)
#   4. gameplay tests (T-GP-*)
# Prints "RUN_ALL: PASS" on success.
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$DIR/.." && pwd)"
# Hygiene (T-QA-01): the gate must not change tracked files (it once re-exported the PT crate
# into Assets/ with a different Blender build, so every run left a dirty tree). Snapshot the
# working-tree diff now and compare at the end.
tree_state() { git -C "$REPO" diff HEAD 2>/dev/null | sha1sum | cut -d' ' -f1; }
IN_GIT=0; git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 && IN_GIT=1
[ $IN_GIT -eq 1 ] && TREE_BEFORE="$(tree_state)"
# Asset integrity (T-ANIM-01): no committed .glb may be a dev placeholder. A sandbox without LFS
# once generated A_Humanoid_Locomotion.glb as a 208-byte stand-in and it got committed through
# the LFS repair - the shared animation library silently had zero clips.
placeholders="$(cd "$REPO" && git ls-files '*.glb' 2>/dev/null | while read -r f; do [ -f "$f" ] && grep -l 'uw_placeholder' "$f" 2>/dev/null; done)"
[ -z "$placeholders" ] || { echo "$placeholders"; echo "RUN_ALL: FAIL (dev placeholder .glb committed - restore the real LFS object)"; exit 1; }
"$DIR/check_toolchain.sh" || { echo "RUN_ALL: FAIL (toolchain preflight, see above)"; exit 1; }
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
if [ $IN_GIT -eq 1 ] && [ "$(tree_state)" != "$TREE_BEFORE" ]; then
  git -C "$REPO" status --short --untracked-files=no
  echo "RUN_ALL: FAIL (the test run modified tracked files - tests must write to scratch dirs)"
  exit 1
fi
echo "RUN_ALL: PASS"
