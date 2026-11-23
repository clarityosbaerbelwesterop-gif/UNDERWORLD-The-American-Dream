#!/usr/bin/env bash
# UNDERWORLD - rebuild the headless toolchain on a locked-down Linux sandbox.
#
#   Tools/sandbox/bootstrap_headless.sh [--no-godot]
#
# Recreates everything Tests/run_all.sh needs on a machine with no GPU, no display, no git-lfs
# and no Debian packages (see Docs/TOOLCHAIN_SANDBOX.md for why each step is needed):
#
#   /usr/local/venv                     Python venv with bpy, pillow, scons, gdtoolkit
#   /usr/local/tools/xstub/lib/         X11/GL symbol stubs + placeholder sonames for bpy
#   /usr/local/tools/blender/blender    `blender` CLI shim (background flags -> bpy module)
#   /usr/local/tools/bin/pkg-config     "everything is not installed" stub for Godot's probes
#   /tmp/godot-src/bin/godot...         Godot 4.7.2 built from source (headless)
#
# Afterwards:  export BLENDER=/usr/local/tools/blender/blender
#              export GODOT=/tmp/godot-src/bin/godot.linuxbsd.editor.x86_64
#              ./Tests/run_all.sh
#
# Idempotent: it wipes and recreates /usr/local/tools/xstub/lib on every run, because leftover
# symlinks there once made `cp` overwrite the preload library with a placeholder.
set -uo pipefail

VENV="${VENV:-/usr/local/venv}"
TOOLS="${TOOLS:-/usr/local/tools}"
XSTUB="$TOOLS/xstub/lib"
BLENDER_SHIM="$TOOLS/blender/blender"
GODOT_SRC="${GODOT_SRC:-/tmp/godot-src}"
GODOT_TAG="${GODOT_TAG:-4.7.2-stable}"
BUILD_GODOT=1
[ "${1:-}" = "--no-godot" ] && BUILD_GODOT=0

say() { printf '\n== %s\n' "$*"; }
die() { printf 'BOOTSTRAP FAILED: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- 1. Python + bpy
say "1/5 Python venv + bpy"
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV" || die "venv"
fi
"$VENV/bin/pip" install -q --upgrade pip || die "pip upgrade"
"$VENV/bin/pip" install -q bpy==5.0.1 pillow scons "gdtoolkit==4.*" || die "pip install"

# ---------------------------------------------------------------- 2. X/GL stubs
say "2/5 X11/GL symbol stubs"
mkdir -p "$TOOLS/bin" "$TOOLS/blender"
rm -rf "$XSTUB"          # leftovers are symlinks; `cp` through them corrupts the preload lib
mkdir -p "$XSTUB"
"$VENV/bin/python" - <<'PY' || die "symbol collection"
import glob, re, subprocess
libs = glob.glob("/usr/local/venv/lib/python3.11/site-packages/bpy/lib/*.so") \
     + glob.glob("/usr/local/venv/lib/python3.11/site-packages/bpy/*.so")
want = set()
for lib in libs:
    out = subprocess.run(["nm", "-D", "-u", lib], capture_output=True, text=True).stdout
    for line in out.splitlines():
        p = line.split()
        if not p:
            continue
        s = p[-1].split("@")[0]          # xkb_context_new@V_0.5.0 -> xkb_context_new
        if re.match(r"^(_?(X|xkb|Xi|Xinerama|Xext|Xrender|Xfixes|Xcursor|Xrandr|Xxf86vm|SM|ICE|gl|GL)[A-Za-z_])", s):
            want.add(s)
if not want:
    raise SystemExit("no unresolved X/GL symbols found - is the bpy wheel installed?")
src = ["/* headless stubs: nothing here is ever really called */"]
src += ["void* %s(void) { return 0; }" % s for s in sorted(want)]
open("/tmp/uw_stub_all.c", "w").write("\n".join(src) + "\n")
print("   %d symbols" % len(want))
PY
gcc -shared -fPIC -o "$XSTUB/libuwheadless.so" /tmp/uw_stub_all.c || die "stub compile"
# Placeholders for the DT_NEEDED sonames. They must be *separate* objects: one shared object
# mapped under twelve names makes ld.so's version check assert.
printf 'int uw_placeholder;\n' > /tmp/uw_placeholder.c
gcc -shared -fPIC -o /tmp/uw_placeholder.so /tmp/uw_placeholder.c || die "placeholder"
for n in X11 Xext Xrender Xfixes Xcursor Xi Xinerama Xrandr Xxf86vm xkbcommon SM ICE GL; do
  for v in "" .0 .1 .2 .3 .4 .5 .6 .7; do
    cp /tmp/uw_placeholder.so "$XSTUB/lib$n.so$v"
  done
done
LD_LIBRARY_PATH="$XSTUB" LD_PRELOAD="$XSTUB/libuwheadless.so" \
  "$VENV/bin/python" -c "import bpy; print('   bpy', bpy.app.version_string)" || die "import bpy"

# ---------------------------------------------------------------- 3. blender shim
say "3/5 blender CLI shim"
cat > "$BLENDER_SHIM" <<'PY'
#!/usr/local/venv/bin/python
"""Headless `blender` CLI shim: accepts Blender's background flags, boots the bpy module.

The repo's tools call `blender -b --factory-startup --python-exit-code N --python F -- args`.
The bpy wheel needs the sandbox's X/GL stubs, so this shim sets them and re-execs once.
"""
import os, sys, runpy

_XLIB = "/usr/local/tools/xstub/lib"
if os.path.isdir(_XLIB):
    os.environ["LD_LIBRARY_PATH"] = _XLIB + (":" + os.environ["LD_LIBRARY_PATH"] if os.environ.get("LD_LIBRARY_PATH") else "")
    _pre = os.path.join(_XLIB, "libuwheadless.so")
    if os.path.exists(_pre) and "libuwheadless.so" not in os.environ.get("LD_PRELOAD", ""):
        os.environ["LD_PRELOAD"] = _pre + (":" + os.environ["LD_PRELOAD"] if os.environ.get("LD_PRELOAD") else "")
        os.execve(sys.executable, [sys.executable, os.path.abspath(__file__)] + sys.argv[1:], os.environ)

argv = sys.argv[1:]
i = 0
script = None
exit_code = None
passthrough = []
while i < len(argv):
    a = argv[i]
    if a in ("-b", "--background", "--factory-startup", "--no-window-focus"):
        i += 1
    elif a == "--python-exit-code":
        exit_code = int(argv[i + 1]); i += 2
    elif a == "--python":
        script = argv[i + 1]; i += 2
    elif a == "--version":
        import bpy
        print("Blender", bpy.app.version_string)
        sys.exit(0)
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
    import traceback
    traceback.print_exc()
    sys.exit(exit_code if exit_code is not None else 1)
PY
chmod +x "$BLENDER_SHIM"
"$BLENDER_SHIM" -b --version || die "blender shim"

# ---------------------------------------------------------------- 4. pkg-config stub
say "4/5 pkg-config stub"
cat > "$TOOLS/bin/pkg-config" <<'SH'
#!/bin/sh
# Headless sandbox stub: every optional system library is "not installed", so Godot's
# optional-feature probes stay off instead of half-detect headers that are not there.
case "$1" in
  --version) echo 0.29.2; exit 0 ;;
  *) exit 1 ;;
esac
SH
printf '#!/bin/sh\nexit 1\n' > "$TOOLS/bin/sdl2-config"
chmod +x "$TOOLS/bin/pkg-config" "$TOOLS/bin/sdl2-config"

# ---------------------------------------------------------------- 5. Godot
if [ "$BUILD_GODOT" = "1" ]; then
  say "5/5 Godot $GODOT_TAG from source (expect ~50 min on 2 vCPU)"
  if [ ! -d "$GODOT_SRC" ]; then
    git clone --depth 1 --branch "$GODOT_TAG" https://github.com/godotengine/godot.git "$GODOT_SRC" \
      || die "godot clone"
  fi
  ( cd "$GODOT_SRC" && \
    PATH="$VENV/bin:$TOOLS/bin:$PATH" "$VENV/bin/scons" platform=linuxbsd target=editor \
      x11=no wayland=no alsa=no pulseaudio=no dbus=no speechd=no fontconfig=no udev=no \
      touch=no tests=no accesskit=no vulkan=no opengl3=no -j"$(nproc)" ) || die "godot build"
  "$GODOT_SRC/bin/godot.linuxbsd.editor.x86_64" --headless --version || die "godot run"
else
  say "5/5 Godot build skipped (--no-godot)"
fi

cat <<EOF

BOOTSTRAP OK

  export BLENDER=$BLENDER_SHIM
  export GODOT=$GODOT_SRC/bin/godot.linuxbsd.editor.x86_64
  ./Tests/run_all.sh

Real asset binaries are a separate problem (no git-lfs here). See Docs/TOOLCHAIN_SANDBOX.md §7.
EOF
