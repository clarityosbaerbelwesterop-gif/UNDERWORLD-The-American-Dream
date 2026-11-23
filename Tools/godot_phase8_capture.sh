#!/usr/bin/env bash
# Phase 8 (QUALITY_GATE.md): capture a Godot gameplay/look-dev viewport on a box
# without a GPU, under Xvfb.
#
# Renderer (--renderer, default auto):
#   fwdplus  the SHIPPING renderer Forward Plus on Vulkan, via Mesa lavapipe (CPU Vulkan ICD).
#            Same shaders/GI/fog/tonemap code path as on a GPU, but CPU speed: never quote FPS.
#   compat   gl_compatibility on Mesa llvmpipe (OpenGL) - legacy fallback, lighting differs.
#   auto     fwdplus if a lavapipe ICD is found (UW_LAVAPIPE_ICD or the usual paths), else compat.
# Every shot must be labelled with the renderer it came from (printed below).
#
# Usage:
#   Tools/godot_phase8_capture.sh [--renderer auto|fwdplus|compat] [--path GodotProject]
#        [--scene res://Scenes/Main.tscn | --script res://Tests/tools/x.gd] [--out file.png]
#        [--movie out.avi|out.png --fps 30 --frames N]   (Godot Movie Maker: deterministic video)
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
RENDERER=auto
MOVIE=""
FPS=30
FRAMES=300
while [[ $# -gt 0 ]]; do
  case "$1" in
    --path) PROJECT="$2"; shift 2 ;;
    --scene) SCENE="$2"; shift 2 ;;
    --script) SCRIPT="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --renderer) RENDERER="$2"; shift 2 ;;
    --movie) MOVIE="$2"; shift 2 ;;
    --fps) FPS="$2"; shift 2 ;;
    --frames) FRAMES="$2"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 4 ;;
  esac
done
LVP_ICD=""
for c in "${UW_LAVAPIPE_ICD:-}" /opt/lavapipe/lvp_icd.json /usr/share/vulkan/icd.d/lvp_icd.x86_64.json; do
  [[ -n "$c" && -f "$c" ]] && { LVP_ICD="$c"; break; }
done
if [[ "$RENDERER" == auto ]]; then
  [[ -n "$LVP_ICD" ]] && RENDERER=fwdplus || RENDERER=compat
fi
case "$RENDERER" in
  fwdplus)
    [[ -n "$LVP_ICD" ]] || { echo "error: --renderer fwdplus needs a lavapipe ICD (UW_LAVAPIPE_ICD)" >&2; exit 5; }
    unset VK_DRIVER_FILES
    export VK_ICD_FILENAMES="$LVP_ICD"
    args=( --path "$PROJECT" --display-driver x11 --rendering-driver vulkan --rendering-method forward_plus )
    LABEL="Forward Plus / Vulkan / lavapipe (CPU) - shipping renderer, NOT GPU performance" ;;
  compat)
    export LIBGL_ALWAYS_SOFTWARE=1
    export GALLIUM_DRIVER=llvmpipe
    args=( --path "$PROJECT" --display-driver x11 --rendering-driver opengl3 --rendering-method gl_compatibility )
    LABEL="gl_compatibility / OpenGL / llvmpipe - NOT the shipping renderer" ;;
  *) echo "error: --renderer must be auto|fwdplus|compat" >&2; exit 4 ;;
esac
if [[ -n "$MOVIE" ]]; then
  args+=( --write-movie "$MOVIE" --fixed-fps "$FPS" )
fi
if [[ -n "$SCRIPT" ]]; then
  args+=( --script "$SCRIPT" )
elif [[ -n "$SCENE" ]]; then
  args+=( "$SCENE" )
fi
# --quit-after is a safety net if the scene does not quit itself.
if [[ -n "$MOVIE" ]]; then args+=( --quit-after "$FRAMES" ); else args+=( --quit-after 3000 ); fi
echo "phase8 capture: renderer=$RENDERER ($LABEL)"
echo "  project=$PROJECT scene=${SCENE:-} script=${SCRIPT:-} out=${OUT:-} movie=${MOVIE:-}"
export UW_CAPTURE_RENDERER="$RENDERER"
xvfb-run -a -s "-screen 0 1920x1080x24" "$GODOT" "${args[@]}"
if [[ -n "$OUT" && -f "$OUT" ]]; then
  echo "phase8 capture wrote $OUT"
fi
