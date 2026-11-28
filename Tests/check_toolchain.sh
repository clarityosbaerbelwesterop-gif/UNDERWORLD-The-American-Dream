#!/usr/bin/env bash
# UNDERWORLD - toolchain preflight for the merge gate (T-QA-03, Bot 1).
# run_all.sh calls this first. It fails in seconds with a clear fix instead of letting the
# pipeline tool tests die minutes later with "exit 5" (root cause of the "flaky" uwp build-props
# failure seen on 2026-11-28: Blender's own Python had no Pillow; it "passed on rerun" only
# because Pillow had been installed in between - the failure was deterministic, not flaky).
#
# Checks:
#   1. Blender's Python imports PIL + numpy (props/kit.py label atlases, build-buildings,
#      build-weapons run inside Blender). bootstrap_cloud.sh gets this for free (bpy venv with
#      pillow + numpy); a Blender binary install needs:
#        <blender>/5.2/python/bin/python3.13 -m pip install pillow
#   2. A Python with numpy + scipy + soundfile for `uwp build-audio` (T-AUD-01), found the same
#      way Tools/uwp finds it (UWP_PYTHON, python3, then the bpy-shim venv python).
# Negative control: UW_TOOLCHAIN_SABOTAGE=1 pretends PIL is missing -> exit 1.
set -uo pipefail
BLENDER="${BLENDER:-/workspace/tools/blender/blender}"
fails=0
probe="$(mktemp /tmp/uw_toolchain_probe.XXXXXX.py)"
trap 'rm -f "$probe"' EXIT
mod="PIL"; [ "${UW_TOOLCHAIN_SABOTAGE:-}" = "1" ] && mod="PIL_uw_sabotage_missing"
cat > "$probe" <<PY
import sys
try:
    import $mod, numpy
except Exception as e:
    print("[TOOLCHAIN] blender python import failed:", e); sys.exit(3)
print("[TOOLCHAIN] blender python: PIL + numpy OK (%s)" % sys.version.split()[0])
PY
if [ ! -x "$BLENDER" ]; then
  echo "[TOOLCHAIN][FAIL] Blender not found at $BLENDER"; fails=$((fails+1))
else
  out="$("$BLENDER" -b --factory-startup --python-exit-code 3 --python "$probe" 2>&1)"; rc=$?
  echo "$out" | grep '^\[TOOLCHAIN\]'
  if [ $rc -ne 0 ] || ! echo "$out" | grep -q 'PIL + numpy OK'; then
    echo "[TOOLCHAIN][FAIL] Blender's Python lacks Pillow/numpy (uwp build-props/-buildings/-weapons would exit 5)."
    echo "                  fix: <blender dir>/<ver>/python/bin/python3.* -m pip install pillow   (or Tools/sandbox/bootstrap_cloud.sh)"
    fails=$((fails+1))
  fi
fi
apy=""
for c in "${UWP_PYTHON:-}" python3 "$(head -1 "$(readlink -f "$BLENDER")" 2>/dev/null | sed -n 's/^#!//p' | awk '{print $1}')"; do
  [ -n "$c" ] && "$c" -c "import numpy, scipy, soundfile" 2>/dev/null && { apy="$c"; break; }
done
if [ -z "$apy" ]; then
  echo "[TOOLCHAIN][FAIL] no Python with numpy + scipy + soundfile for uwp build-audio (set UWP_PYTHON or pip install numpy scipy soundfile)"
  fails=$((fails+1))
else
  echo "[TOOLCHAIN] audio python: $apy"
fi
[ $fails -eq 0 ] && { echo "TOOLCHAIN: PASS"; exit 0; }
echo "TOOLCHAIN: FAIL ($fails)"; exit 1
