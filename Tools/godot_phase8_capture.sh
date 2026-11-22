#!/usr/bin/env bash
# Phase 8 (QUALITY_GATE.md): capture a Godot gameplay/look-dev viewport on this
# no-GPU box via Xvfb + Mesa llvmpipe (OpenGL 4.5 compatibility).
#
# The shipping project uses Forward Plus (Vulkan). This box has no lavapipe ICD,
# so the capture forces gl_compatibility + opengl3. Lighting will not match the
# shipping renderer; use the shot for scale, silhouette, materials and camera
# framing, and note the renderer difference on the review sheet.
#
# Usage:
#   Tools/godot_phase8_capture.sh [--path GodotProject] [--scene res://Scenes/Main.tscn] [--out Docs/Reviews/sheets/phase8.png]
# The scene (or a helper script in it) must write the PNG itself, or pass a
# --script that calls Viewport.get_texture().get_image().save_png().
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
GODOT="${GODOT:-/workspace/tools/godot}"
PROJECT="$REPO/GodotProject"
SCENE=""
SCRIPT=""
OUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --path) PROJECT="$2"; shift 2 ;;
    --scene) SCENE="$2"; shift 2 ;;
    --script) SCRIPT="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 4 ;;
  esac
done
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
args=( --path "$PROJECT" --display-driver x11 --rendering-driver opengl3 --rendering-method gl_compatibility )
if [[ -n "$SCRIPT" ]]; then
  args+=( --script "$SCRIPT" )
elif [[ -n "$SCENE" ]]; then
  args+=( "$SCENE" )
fi
# --quit-after is a safety net if the scene does not quit itself.
args+=( --quit-after 300 )
echo "phase8 capture: xvfb + llvmpipe + opengl3/gl_compatibility"
echo "  project=$PROJECT scene=${SCENE:-} script=${SCRIPT:-} out=${OUT:-}"
xvfb-run -a -s "-screen 0 1920x1080x24" "$GODOT" "${args[@]}"
if [[ -n "$OUT" && -f "$OUT" ]]; then
  echo "phase8 capture wrote $OUT"
fi
