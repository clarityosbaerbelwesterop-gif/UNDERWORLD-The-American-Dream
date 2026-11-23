#!/usr/bin/env bash
# UNDERWORLD - one-shot toolchain for a cloud container / CI runner (T-ENV-01).
#
#   Tools/sandbox/bootstrap_cloud.sh [--templates] [--prefix /opt/uwtools]
#
# Installs the EXACT studio versions without root package managers:
#   Blender 5.2.4 LTS   as the official `bpy` wheel (PyPI) in a venv + a `blender` CLI shim
#   Godot 4.7.2 stable  official binary from GitHub Releases (sha512 checked against SHA512-SUMS)
#   export templates    (--templates) 4.7.2 Linux + Windows only, into ~/.local/share/godot/...
# and links them to the paths the repo defaults to (/workspace/tools/{godot,blender/blender}),
# so Tests/run_all.sh, Tools/uwp and Tools/build/build_linux.sh work with no env vars.
#
# Rendering without a GPU: if Mesa lavapipe (Vulkan on the CPU) is present, Godot can run the
# SHIPPING renderer Forward Plus under Xvfb (Tools/godot_fwdplus_capture.sh). That is the real
# renderer code path but NOT GPU performance - never quote its FPS as a GPU number.
#
# Idempotent; safe to re-run. Needs: python3 >= 3.13 (bpy 5.2 wheels are cp313), curl, unzip.
set -euo pipefail

PREFIX=/opt/uwtools
WANT_TEMPLATES=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --templates) WANT_TEMPLATES=1; shift ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 4 ;;
  esac
done

GODOT_VER=4.7.2
BPY_VER=5.2.4
REL="https://github.com/godotengine/godot/releases/download/${GODOT_VER}-stable"
say() { printf '\n== %s\n' "$*"; }
die() { printf 'BOOTSTRAP FAILED: %s\n' "$*" >&2; exit 1; }
mkdir -p "$PREFIX/bin"

# ---------------------------------------------------------------- 1. Blender (bpy wheel)
say "1/4 Blender $BPY_VER LTS (bpy wheel)"
PY="${PYTHON:-python3}"
"$PY" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 13) else 1)' \
  || die "python >= 3.13 required for bpy $BPY_VER (have $("$PY" --version))"
[ -x "$PREFIX/venv/bin/python" ] || "$PY" -m venv "$PREFIX/venv"
"$PREFIX/venv/bin/python" -c "import bpy,sys; sys.exit(0 if bpy.app.version_string.startswith('$BPY_VER') else 1)" 2>/dev/null \
  || "$PREFIX/venv/bin/pip" install -q "bpy==$BPY_VER" pillow numpy "gdtoolkit==4.*" \
  || die "pip install bpy==$BPY_VER"

cat > "$PREFIX/bin/blender" <<PYSHIM
#!$PREFIX/venv/bin/python
"""Headless \`blender\` CLI shim (bpy module). Accepts the flags the repo uses:
   blender -b [--factory-startup] [--python-exit-code N] --python F [-- args]"""
import os, sys, runpy
argv = sys.argv[1:]
i, script, exit_code, passthrough = 0, None, None, []
while i < len(argv):
    a = argv[i]
    if a in ("-b", "--background", "--factory-startup", "--no-window-focus", "-noaudio"):
        i += 1
    elif a == "--python-exit-code":
        exit_code = int(argv[i + 1]); i += 2
    elif a == "--python":
        script = argv[i + 1]; i += 2
    elif a in ("--version", "-v"):
        import bpy
        print("Blender", bpy.app.version_string); sys.exit(0)
    elif a == "--":
        passthrough = argv[i + 1:]; break
    elif a.startswith("-"):
        sys.stderr.write("[blender-shim] ignoring unsupported flag %r\n" % a); i += 1
    else:
        i += 1
if script is None:
    sys.stderr.write("[blender-shim] only --python <file> is supported in background mode\n")
    sys.exit(2)
sys.argv = ["blender", "--python", script] + (["--"] + passthrough if passthrough else [])
try:
    runpy.run_path(script, run_name="__main__")
except SystemExit as e:
    sys.exit(e.code if isinstance(e.code, int) else (0 if e.code is None else 1))
except BaseException:
    import traceback; traceback.print_exc()
    sys.exit(exit_code if exit_code is not None else 1)
PYSHIM
chmod +x "$PREFIX/bin/blender"
"$PREFIX/bin/blender" -b --version | grep -q "Blender $BPY_VER" || die "blender shim"

# ---------------------------------------------------------------- 2. Godot (official binary)
say "2/4 Godot $GODOT_VER stable (official)"
GBIN="$PREFIX/Godot_v${GODOT_VER}-stable_linux.x86_64"
if ! [ -x "$GBIN" ]; then
  tmp="$(mktemp -d)"
  curl -fsSL -o "$tmp/godot.zip" "$REL/Godot_v${GODOT_VER}-stable_linux.x86_64.zip" || die "godot download"
  if curl -fsSL -o "$tmp/SHA512-SUMS.txt" "$REL/SHA512-SUMS.txt"; then
    want="$(grep " Godot_v${GODOT_VER}-stable_linux.x86_64.zip\$" "$tmp/SHA512-SUMS.txt" | cut -d' ' -f1)"
    have="$(sha512sum "$tmp/godot.zip" | cut -d' ' -f1)"
    [ -z "$want" ] || [ "$want" = "$have" ] || die "godot sha512 mismatch"
  fi
  unzip -oq "$tmp/godot.zip" -d "$PREFIX"
  rm -rf "$tmp"
fi
ln -sf "$GBIN" "$PREFIX/bin/godot"
"$PREFIX/bin/godot" --headless --version | grep -q "^${GODOT_VER}.stable" || die "godot run"

# ---------------------------------------------------------------- 3. export templates
TPL_DIR="$HOME/.local/share/godot/export_templates/${GODOT_VER}.stable"
if [ "$WANT_TEMPLATES" = 1 ]; then
  say "3/4 export templates (linux + windows only)"
  if ! [ -f "$TPL_DIR/linux_release.x86_64" ]; then
    tmp="$(mktemp -d)"
    curl -fsSL -o "$tmp/t.tpz" "$REL/Godot_v${GODOT_VER}-stable_export_templates.tpz" || die "templates download"
    mkdir -p "$TPL_DIR"
    unzip -oq -j "$tmp/t.tpz" 'templates/version.txt' 'templates/linux_*.x86_64' 'templates/windows_*_x86_64.exe' -d "$TPL_DIR" \
      || die "templates unzip"
    rm -rf "$tmp"
  fi
  ls "$TPL_DIR"
else
  say "3/4 export templates skipped (pass --templates)"
fi

# ---------------------------------------------------------------- 4. repo default paths
say "4/4 /workspace/tools links (repo defaults)"
if mkdir -p /workspace/tools/blender 2>/dev/null; then
  ln -sf "$PREFIX/bin/blender" /workspace/tools/blender/blender
  ln -sf "$GBIN" /workspace/tools/godot
else
  echo "no write access to /workspace - export BLENDER=$PREFIX/bin/blender GODOT=$GBIN"
fi

LVP=""
for icd in /opt/lavapipe/lvp_icd.json /usr/share/vulkan/icd.d/lvp_icd.x86_64.json; do
  [ -f "$icd" ] && LVP="$icd" && break
done
cat <<EOF

BOOTSTRAP OK
  blender : $("$PREFIX/bin/blender" -b --version)
  godot   : $("$PREFIX/bin/godot" --headless --version)
  xvfb    : $(command -v xvfb-run || echo "missing (needed for captures)")
  ffmpeg  : $(command -v ffmpeg || echo "missing (needed for videos)")
  lavapipe: ${LVP:-missing (Forward Plus captures fall back to gl_compatibility)}
Next: ./Tests/run_all.sh   (expects RUN_ALL: PASS)
EOF
