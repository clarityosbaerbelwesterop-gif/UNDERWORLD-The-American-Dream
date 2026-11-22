# Toolchain on a locked-down sandbox (2026-11-22, Arena agent session)

The docs assume the original studio box: `/workspace/tools/blender/blender` (Blender 5.2.4 LTS
binary) and `/workspace/tools/godot` (Godot 4.7.2 release binary), plus `git-lfs` and Mesa
llvmpipe for Phase 8 captures. **The M01 mission/level work in this session ran on a different,
much more restricted machine.** This file records exactly what that machine could do, so the
next agent does not waste a day rediscovering it, and so every result below can be reproduced.

## 1. What the sandbox allows

| Thing | Status | Consequence |
|---|---|---|
| Outbound HTTP | only `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org` | **GitHub Release assets are unreachable** (`release-assets.githubusercontent.com` is not allowed) → no official Godot binary, no Blender binary download |
| `git-lfs` | binary not installed, and LFS objects are served from `github-cloud.githubusercontent.com` (blocked) | **No asset binaries.** Every `.glb`/`.blend`/`.png` in `Assets/` and `Blender/Source/` is a 130-byte pointer file |
| `apt` / Debian mirrors | blocked | no system packages (`pkg-config`, X11 headers, Mesa, `git-lfs`, `xvfb`) |
| Display / GPU | none (no `/dev/dri`, no Mesa, no launcher) | **no rendering at all** – Phase 8 capture is impossible here |
| CPU / RAM | 2 vCPU, 3 GB RAM (+6 GB swap added) | long compiles, `scons -j2` |
| Python | 3.11 system + a venv at `/usr/local/venv` | |

## 2. What was installed instead (reproducible)

```bash
# 1. Blender, via the PyPI bpy wheel (Python 3.11 -> newest wheel is Blender 5.0.1, not 5.2.4)
python3 -m venv /usr/local/venv
/usr/local/venv/bin/pip install bpy==5.0.1 pillow scons "gdtoolkit==4.*"

# 2. The wheel links desktop X/GL libraries the image does not ship. They are stubbed with
#    no-op shared objects (headless Blender never opens a display):
#    /usr/local/tools/xstub/lib/libXrender.so.1, libXfixes.so.3, libXi.so.6,
#    libxkbcommon.so.0, libSM.so.6, libICE.so.6, libGL.so.1  ->  ../libXstub.so
#    LD_LIBRARY_PATH=/usr/local/tools/xstub/lib

# 3. A `blender` CLI shim that speaks Blender's headless flags but runs the bpy module:
#    /usr/local/tools/blender/blender -b --factory-startup --python-exit-code N --python F -- args
BLENDER=/usr/local/tools/blender/blender ./Tools/uwp validate <file.blend>

# 4. Godot 4.7.2 built from the source tarball (headless: no X11, no Wayland, no audio servers)
#    A stub pkg-config keeps Godot's optional-library probes honest (everything "not installed"),
#    thirdparty/ supplies freetype/pcre2/zstd/mbedtls/... so the build needs no system dev libs.
cd godot-4.7.2-stable
PATH=/usr/local/tools/bin:$PATH /usr/local/venv/bin/scons platform=linuxbsd target=editor \
  x11=no wayland=no alsa=no pulseaudio=no dbus=no speechd=no fontconfig=no udev=no touch=no \
  tests=no accesskit=no vulkan=no opengl3=no -j2
GODOT=/tmp/godot-4.7.2-stable/bin/godot.linuxbsd.editor.x86_64

# 5. GDScript syntax/lint without Godot: gdparse / gdlint (gdtoolkit)
gdparse GodotProject/Scripts/mission/mission_manager.gd
```

`Tools/uwp` and the test scripts already honour `BLENDER=` and `GODOT=`, so no repo change is
needed. `Tools/uwp review-sheet` runs in system `python3` and needs Pillow (`/usr/local/bin/python3`
was pointed at the venv).

## 3. What is proven here vs. what is not

| Proven on the sandbox | Not provable here |
|---|---|
| `Tools/underworld_pipeline` generator + validator + exporter on procedurally built assets (uwp tool suite) | any **rendered** image (Cycles), any in-engine screenshot |
| Godot 4.7.2 headless: project import, GDScript, scene/glTF parsing, physics, AI, vehicles, weapons, missions | Forward Plus / gl_compatibility look, FPS, camera feel, animation blending quality |
| `Tests/run_all.sh` structure and all logic-level tests | the **real** hero assets (`Assets/**/*.glb` are placeholders here) |

The gameplay suite's asset-dependent tests (player visual clip validation, vehicle assembly from
`VH_Sedan_01.glb`, weapon model sockets, `Scenes/Levels/LA_CallowayAve_Block.tscn`) cannot be
judged on this machine. They are reported separately and must be re-run on the studio box.

## 4. Carrying this session back to the studio box

```bash
cd /workspace/UNDERWORLD && git lfs pull
./Tests/run_all.sh                      # must print RUN_ALL: PASS with the REAL assets
BLENDER=/workspace/tools/blender/blender GODOT=/workspace/tools/godot ./Tests/run_all.sh
```

Nothing in this session depends on the sandbox paths: no repo file points at `/tmp` or
`/usr/local`. The only sandbox-specific artefact is `GodotProject/Tests/tools/build_asset_cache.gd`
(a dev helper that writes placeholder scenes when LFS binaries are missing; it refuses to run when
real assets are present and is not part of the merge gate).
