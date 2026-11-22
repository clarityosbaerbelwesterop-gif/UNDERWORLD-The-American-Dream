# UNDERWORLD – THE AMERICAN DREAM

Original open-world third-person crime game (cinematic, realistic; inspired by the *quality bar* of modern open-world crime games, with 100 % original characters, story, assets and locations).

Built by a three-agent virtual studio:

| Agent | Role | Owns |
|---|---|---|
| **Bot 1** – Project Director | Architecture, story, production, integration on `main` | `Docs/`, `Config/`, `README.md` |
| **Bot 2** – "Tripple A 3D Designer" | Blender, 3D art, tech art, rigging, animation | `Blender/`, `Tools/`, `Assets/` |
| **Bot 3** – "Game Developer" | Godot gameplay, AI, vehicles, QA, builds | `GodotProject/`, `Source/`, `Tests/`, `Builds/` |

## Tech stack (see `Docs/TECHNICAL_DECISIONS.md`)
- **Engine:** Godot 4.7.2 (GDScript; C++ GDExtension in `Source/` later if needed). *Deviation from the brief's UE5 – UE5 is not feasible on this machine (TD-001).*
- **DCC:** Blender 5.2.4 LTS, driven headless via Blender Python (`bpy`).
- **Interchange:** glTF 2.0 binary (`.glb`), metres, Y-up in Godot (exporter converts Blender Z-up).
- **Binaries:** Git LFS for `.blend/.glb/.png/.wav/...`.

Shared tools on the box: `/workspace/tools/README.md` (`/workspace/tools/blender/blender`, `/workspace/tools/godot`).

## Layout
```
Docs/          design + production docs (task board, status, logs, decisions, blockers)
GodotProject/  Godot 4 project (replaces UnrealProject/ from the brief). GodotProject/Assets -> ../Assets (symlink)
Blender/       Source/ = .blend sources, Scripts/ = asset-specific bpy scripts
Tools/         pipeline python (blender_export.py, later the production exporter)
Assets/        exported .glb (+ Godot .import sidecars + manifests), mirrors Blender/Source/ layout
Source/        native code (GDExtension C++) – empty for now
Tests/         pipeline + gameplay tests (run_pipeline_smoke.sh)
Builds/        build output (gitignored)
Config/        shared configuration (naming rules, budgets)
```

## Quick start
```bash
git lfs install
./Tests/run_pipeline_smoke.sh      # Blender export -> Godot import -> scene asserts; must print PASS
/workspace/tools/godot --path GodotProject   # (needs a display) open the editor
```

Start reading at `Docs/PROJECT_STATUS.md`, then `Docs/TASK_BOARD.md` and `Docs/HANDOFF_PROTOCOL.md`.
