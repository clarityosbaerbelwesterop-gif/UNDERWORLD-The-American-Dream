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

---

# Session 2 (2026-11-22, Auftrag 02): a **fresh** sandbox, and how the real assets came back

The container for Auftrag 02 was new: **none** of the `/workspace/tools` or `/usr/local/tools`
artefacts from session 1 existed, `git lfs` was still absent, and every binary in the tree was a
130-byte LFS pointer again. Everything below was rebuilt from scratch in ~75 minutes and is
reproducible.

## 5. What had to be rebuilt

| Piece | How | Result |
|---|---|---|
| Python venv | `python3 -m venv /usr/local/venv` | 3.11.2 |
| Blender (bpy wheel) | `pip install bpy==5.0.1 pillow scons "gdtoolkit==4.*"` | `bpy` 5.0.1 |
| X/GL stubs | see §6 — the naive "one no-op per library" approach from §2 **does not work** | `import bpy` OK |
| `blender` shim | `/usr/local/tools/blender/blender` (python shim, sets its own `LD_*`) | `blender -b --version` |
| Godot 4.7.2 | `git clone --depth 1 --branch 4.7.2-stable`, then the scons line from §2 | **00:49:53** on 2 vCPU, 153 MB binary |
| pkg-config | stub at `/usr/local/tools/bin/pkg-config` (always "not installed") | Godot probes honest |

## 6. The X/GL stub problem (this is the part that eats a day)

`libusd_ms.so` inside the bpy wheel needs **155** X11/GL/Xkb symbols, and it needs them as *real
exports of a library* — not as stubs of the library name. A single no-op `libXstub.so` symlinked
to `libX11.so.6`, `libXfixes.so.3`, … fails, because the dynamic linker resolves each symbol
against the library the binary was linked against, and a stub that only defines `uw_stub_X11()`
exports nothing.

What works: **one** shared object that defines *every* unresolved symbol, loaded via `LD_PRELOAD`
so it satisfies the loader before any of the missing libraries are searched.

```bash
# 1. collect every unresolved X*/gl*/Xkb* symbol from every .so in the wheel
/usr/local/venv/bin/python - <<'PY'
import subprocess, re, glob
libs = glob.glob("/usr/local/venv/lib/python3.11/site-packages/bpy/lib/*.so") \
     + glob.glob("/usr/local/venv/lib/python3.11/site-packages/bpy/*.so")
want = set()
for lib in libs:
    out = subprocess.run(["nm", "-D", "-u", lib], capture_output=True, text=True).stdout
    for line in out.splitlines():
        p = line.split()
        if not p: continue
        s = p[-1].split("@")[0]            # strip "@V_0.5.0" version tags
        if re.match(r"^(_?(X|xkb|Xi|Xinerama|Xext|Xrender|Xfixes|Xcursor|Xrandr|Xxf86vm|SM|ICE|gl|GL)[A-Za-z_])", s):
            want.add(s)
src = ["/* headless stubs: nothing here is ever really called */"] + [f"void* {s}(void) {{ return 0; }}" for s in sorted(want)]
open("/tmp/stub_all.c", "w").write("\n".join(src) + "\n")
PY
gcc -shared -fPIC -o /usr/local/tools/xstub/lib/libuwheadless.so /tmp/stub_all.c
# 2. empty placeholders so the loader finds a file for the DT_NEEDED names
for n in X11 Xext Xrender Xfixes Xcursor Xi Xinerama Xrandr Xxf86vm xkbcommon SM ICE GL; do
  ln -sf libuwheadless.so /usr/local/tools/xstub/lib/lib$n.so.6
done
export LD_PRELOAD=/usr/local/tools/xstub/lib/libuwheadless.so
export LD_LIBRARY_PATH=/usr/local/tools/xstub/lib
/usr/local/venv/bin/python -c "import bpy; print(bpy.app.version_string)"   # -> 5.0.1
```

Three traps, all hit:
- `nm -D -u` prints versioned names (`xkb_context_new@V_0.5.0`) — they have to be stripped, or
  the C file will not compile.
- X11 needs both `libX11.so.6` **and** `libX11.so` present; `libxkbcommon.so.0` is what bpy
  actually links, not `.so.1`.
- `glXGetProcAddress` must not return a null pointer to a **no-op with the wrong signature** in
  code paths that call it, but for `import bpy` (no GL context) `return 0` is enough.

`/usr/local/tools/blender/blender` sets `LD_PRELOAD`/`LD_LIBRARY_PATH` itself and re-`exec`s, so
`BLENDER=/usr/local/tools/blender/blender ./Tests/run_all.sh` works with a clean environment. Its
shebang points at `/usr/local/venv/bin/python` because system `python3` has no `bpy`.

## 7. Git LFS is still unavailable — the real binaries came back out of *history*

`release-assets.githubusercontent.com`, `github-cloud.githubusercontent.com` and
`objects.githubusercontent.com` are all still blocked (`curl: (35) SSL_ERROR_SYSCALL` / no
route), there is no Go to build git-lfs, and npm/PyPI ship no binary. **Do not retry these.**

The binaries themselves are not lost, though: PR #14 committed them as **regular blobs**, and
PR #15 replaced them with LFS pointers afterwards. 106 of the 114 pointers in `HEAD` can be
restored **byte-identically** from that history:

```bash
git fetch --unshallow origin        # the arena clone is shallow (1 commit) by default
python3 Tools/sandbox/restore_lfs_from_history.py
```

The tool (in the repo, so it survives a sandbox reset) reads every
`version https://git-lfs.github.com/spec/v1` pointer in the working tree, walks all revisions of
that exact path and restores the first blob whose **SHA-256 matches the pointer's `oid`** and
whose size matches — a wrong or corrupt file can therefore never be restored. It then marks all
114 pointer paths `git update-index --skip-worktree`, so the binaries can never be committed back
as plain blobs: `git status` stays clean and `git add -A` ignores them.

> Undo with `git update-index --no-skip-worktree <path>` and `git checkout -- <path>`; that brings
> the LFS pointer back.

Still missing after the restore (8 files, never in history as blobs): the three
`Docs/ArtDirection/Concepts/CA_Jason_*.jpg`, the five `Docs/Reviews/sheets/*_ref_compare.png`
and the six `Docs/Reports/renders_m01/*.png` from PR #14's report.
None of them is needed by `Tests/run_all.sh`; the silhouette check reports them as
`WARN CONCEPT_UNAVAILABLE`, exactly as in session 1.

## 8. Verified baseline on this sandbox (2026-11-22)

`./Tests/run_all.sh` with `BLENDER=/usr/local/tools/blender/blender` and
`GODOT=/tmp/godot-src/bin/godot.linuxbsd.editor.x86_64`:

```
smoke 12 · uwp 58 · asset import 71 · AI 80 · mission 75 · player 137 · vehicle 88 · weapon 68
= 589 checks, RUN_ALL: PASS
```

Identical to the numbers in the work order §3, **with the real assets**, not placeholders. The
four sabotage modes give the documented failures:

| Mode | FAIL count |
|---|---|
| `UW_JASON_SABOTAGE=1` | 3 |
| `UW_VEHICLE_SABOTAGE=1` / `=2` | 9 / 22 |
| `UW_MISSION_SABOTAGE=1` | 5 |

`Tools/uwp validate-all` and `export-all` pass on all 17 `Blender/Source` assets (Blender 5.0.1
reads them; the LFS pointers obviously do not).

## 9. What is *still* not possible here

No GPU, no display, no Mesa → **no Phase-8 capture** (`Tools/godot_phase8_capture.sh` needs Xvfb +
llvmpipe), no Forward-Plus look, no FPS, no gameplay feel. Those stay "unverified" in the report.
Everything else in the work order — headless logic, AI, vehicles, weapons, missions, the asset
pipeline, `gdparse` — runs here.
