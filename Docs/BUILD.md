# Builds (T-BUILD-01)

`Tools/build/build_linux.sh` exports the playable Linux build from
`GodotProject/export_presets.cfg` into `Builds/linux/` and smoke-runs it.
`Builds/` is gitignored: game binaries never enter the repository.

```bash
GODOT=/path/to/godot Tools/build/build_linux.sh            # release
GODOT=/path/to/godot Tools/build/build_linux.sh --debug    # debug template
GODOT=/path/to/godot Tools/build/build_linux.sh --no-run    # export only
```

## What the export contains

Preset `Linux` (x86_64, PCK next to the binary, text→binary resources on):

| Setting | Value | Why |
|---|---|---|
| `export_filter` | `all_resources` | everything reachable by the export file system |
| `exclude_filter` | `Tests/*, Scripts/import/*` | the headless test suite and the editor-only import post-process scripts are not part of a player build (the import scripts need the editor) |
| `binary_format/embed_pck` | `false` | one `.pck` next to the binary is easier to inspect than a patched ELF |

`Assets/` is a symlink into `Assets/` at the repo root (`GodotProject/Assets -> ../Assets`, TD-006);
Godot resolves it through `res://Assets/...`, so the GLBs end up in the PCK like any other resource.

## Export templates (the honest part)

Godot's own export templates are **version-locked** to the engine binary
(`~/.local/share/godot/export_templates/<full version>/linux_release.x86_64`).
The official `.tpz` is ~1 GB and only the Linux binaries are needed (B-005);
`Docs/CLAUDE_CODE_HANDOFF.md` §3.3 says to extract exactly those two files.

On the sandbox box the download host is unreachable, so the template was built
from the engine's own source tree instead (same code, same version string):

```bash
cd /tmp/godot-src            # git clone --depth 1 --branch 4.7.2-stable
PATH=/usr/local/venv/bin:$PATH /usr/local/venv/bin/scons platform=linuxbsd target=template_release \
  x11=no wayland=no alsa=no pulseaudio=no dbus=no speechd=no fontconfig=no udev=no touch=no \
  tests=no accesskit=no vulkan=no opengl3=no -j2
mkdir -p ~/.local/share/godot/export_templates/4.7.2.stable
cp bin/godot.linuxbsd.template_release.x86_64 ~/.local/share/godot/export_templates/4.7.2.stable/linux_release.x86_64
```

Consequences of this template build, stated plainly:

- **`vulkan=no opengl3=no`**: the template has *no* rendering driver. It runs, loads the
  scene tree and the logic headless, but it cannot present a frame. That is enough for
  "does the game boot", not for a visual check. A playable-on-a-desktop build needs a
  template with Forward+ (Vulkan) – build one on a box with the Vulkan headers/loader, or
  install the official 4.7.2 template there.
- `x11=no wayland=no alsa=no ...`: no window system and no audio server, mirroring the
  sandboxed engine (TD-001/`Docs/TOOLCHAIN_SANDBOX.md`).

Because of that the smoke run in `build_linux.sh` is a **boot check**
(`--headless --quit-after 300`, no `ERROR`/`SCRIPT ERROR` lines), not a playability proof.
The template is also built with the default `disable_path_overrides=yes`, so it cannot be
pointed at a single scene from the command line – it boots `Main.tscn` from the PCK.

## Result on the sandbox box (2026-11-22)

```
build_linux: Builds/linux/Underworld.x86_64 = 79M + 189M pck
build_linux: smoke run --headless --quit-after 300
build_linux: smoke run clean
build_linux: OK          (exit 0)
```

| Artifact | Size |
|---|---|
| `Builds/linux/Underworld.x86_64` | 79 MB (82,016,992 B) – the template |
| `Builds/linux/Underworld.pck` | 189 MB (98,738,244 B) – game data |
| PCK content | 657 files, text resources converted to binary (`*.scn`, `*.gdc`, `.remap`) |
| Excluded | `Tests/` and `Scripts/import/` – verified by reading the PCK directory: 0 entries |

The 189 MB PCK is dominated by the skeleton/skin binary resources (`.godot/imported/*.scn`)
of `SK_Jason`, `A_Humanoid_Locomotion` and the placeholder GLBs; no textures were resized
for the export. It is a build of the current content, not a shipping size.
