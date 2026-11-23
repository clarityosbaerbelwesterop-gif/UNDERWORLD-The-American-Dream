#!/usr/bin/env bash
# T-BUILD-01 - export the playable Linux build.
#
#   Tools/build/build_linux.sh [--debug] [--no-run]
#
# Produces Builds/linux/Underworld.x86_64 (+ Underworld.pck) from
# GodotProject/export_presets.cfg and then proves the binary starts: it is run
# headless for a fixed number of frames and its stderr must stay free of
# ERROR/SCRIPT ERROR lines. Builds/ is gitignored, the build is never committed.
#
# Requires the Linux export templates for exactly this engine version in
#   ~/.local/share/godot/export_templates/<version>/
# `linux_release.x86_64` (and `linux_debug.x86_64` for --debug) is enough.
# If they are missing the script says so and exits 3 - it does not download
# anything silently (the full .tpz is ~1 GB, see Docs/TOOLCHAIN_SANDBOX.md).
#
# Env: GODOT=/path/to/godot (default: /workspace/tools/godot)
#      UW_BUILD_SABOTAGE=1  negative control: fakes one engine error in the smoke
#                           log so the guard has to fail (exit 6).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
GODOT="${GODOT:-/workspace/tools/godot}"
PROJECT="$REPO/GodotProject"
OUT_DIR="$REPO/Builds/linux"
PRESET="Linux"
DEBUG=0
RUN_CHECK=1
for arg in "$@"; do
  case "$arg" in
    --debug) DEBUG=1 ;;
    --no-run) RUN_CHECK=0 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown arg: $arg" >&2; exit 4 ;;
  esac
done

if [[ ! -x "$GODOT" ]]; then
  echo "error: Godot not found at $GODOT (set GODOT=...)" >&2
  exit 2
fi

VERSION="$("$GODOT" --headless --version | sed 's/\.stable.*//; s/^\([0-9.]*\).*/\1/')"
# Godot reports e.g. 4.7.2.stable.custom_build.ed1daf0bf; the template dir is
# named after short version + status, e.g. 4.7.2.stable.
TPL_DIR="${HOME}/.local/share/godot/export_templates/$( "$GODOT" --headless --version \
  | sed 's/^\([0-9]*\.[0-9]*\.[0-9]*\)\(\.[a-z_]*\)\?.*/\1\2/' | sed 's/\.$//')"
name="linux_release.x86_64"
[[ $DEBUG -eq 1 ]] && name="linux_debug.x86_64"
if [[ ! -f "$TPL_DIR/$name" ]]; then
  echo "error: export template missing: $TPL_DIR/$name" >&2
  echo "       export templates are version-locked; install $name for this engine build." >&2
  echo "       (no network download here on purpose - see Docs/TOOLCHAIN_SANDBOX.md)" >&2
  exit 3
fi

mkdir -p "$OUT_DIR"
ARGS=( --headless --path "$PROJECT" --export-release "$PRESET" "$OUT_DIR/Underworld.x86_64" )
[[ $DEBUG -eq 1 ]] && ARGS=( --headless --path "$PROJECT" --export-debug "$PRESET" "$OUT_DIR/Underworld.x86_64" )
echo "build_linux: $GODOT ${ARGS[*]}"
"$GODOT" "${ARGS[@]}"

if [[ ! -x "$OUT_DIR/Underworld.x86_64" ]]; then
  chmod +x "$OUT_DIR/Underworld.x86_64" 2>/dev/null || true
fi
if [[ ! -f "$OUT_DIR/Underworld.x86_64" ]]; then
  echo "error: export produced no binary" >&2
  exit 5
fi

SIZE="$(du -h "$OUT_DIR/Underworld.x86_64" | cut -f1)"
PCK=""
[[ -f "$OUT_DIR/Underworld.pck" ]] && PCK=" + $(du -h "$OUT_DIR/Underworld.pck" | cut -f1) pck"
echo "build_linux: Builds/linux/Underworld.x86_64 = $SIZE$PCK"

if [[ $RUN_CHECK -eq 1 ]]; then
  LOG="$OUT_DIR/smoke.log"
  echo "build_linux: smoke run --headless --quit-after 300"
  # The engine needs a writable HOME for its user:// dir; run from the build dir
  # so a stray override.cfg next to the binary is honoured like on a real install.
  ( cd "$OUT_DIR" && "$OUT_DIR/Underworld.x86_64" --headless --quit-after 300 ) >"$LOG" 2>&1 || true
  if [[ "${UW_BUILD_SABOTAGE:-0}" == "1" ]]; then
    echo "ERROR: planted failure (UW_BUILD_SABOTAGE=1)" >>"$LOG"
  fi
  BAD="$(grep -nE '^(ERROR|SCRIPT ERROR|USER ERROR)' "$LOG" || true)"
  if [[ -n "$BAD" ]]; then
    echo "error: the build logged engine errors:" >&2
    echo "$BAD" >&2
    exit 6
  fi
  grep -q "Godot Engine v" "$LOG" || { echo "error: no engine banner in $LOG" >&2; exit 7; }
  grep -q "UNDERWORLD" "$LOG" || echo "build_linux: note: main scene printed no 'UNDERWORLD' banner (ok for the current Main.tscn)"
  echo "build_linux: smoke run clean ($LOG)"
fi

echo "build_linux: OK"
