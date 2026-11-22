# Blockers & Risks

Any agent may add entries. Format: ID · date (Europe/Berlin) · reporter · status (OPEN / MITIGATED / RESOLVED) · impact · workaround · owner.

| ID | Date | By | Status | Issue | Impact | Workaround / next step | Owner |
|---|---|---|---|---|---|---|---|
| B-001 | 2026-11-22 | Bot 1 | MITIGATED | **No Blender MCP connector** available in this environment. | No live/interactive Blender session for agents. | Blender 5.2.4 LTS headless + bpy scripts (`Tools/`), fully scriptable and reproducible (TD-002). | Bot 2 |
| B-002 | 2026-11-22 | Bot 1 | RESOLVED | **Unreal Engine 5 not feasible** (no GPU, ~14 GB free disk, UE5 needs 100+ GB + GPU editor). | Brief asked for UE5. | Godot 4.7.2 chosen (owner allowed open engine/Unity) – TD-001. | Bot 1 |
| B-003 | 2026-11-22 | Bot 1 | OPEN | **No GPU on the box.** Godot `--headless` uses a dummy renderer → no in-engine screenshots/visual QA; real-time look & fps cannot be measured here. | Visual quality and performance unverified. | Logic/physics/import tested headless; Blender Cycles **CPU** preview renders for asset visuals (T-PIPE-01). Later: test on a GPU machine or a GPU cloud runner. Possibly try Godot with software GL (Mesa llvmpipe) for low-res screenshots – untested. | Bot 3 / Bot 2 |
| B-004 | 2026-11-22 | Bot 1 | OPEN (owner) | Open owner decisions: Jason's surname; currency detail (brief: arrives in NY with **€5,000** – kept as written: he carries euros from his Colombia work); working names "Los Cuervos", "La Hermandad del Sur", "Marco Ruiz", "Dana Whitlock", "Calloway Avenue/East Hollow". | Story text only; not blocking M1 code. | Use working names; rename later centrally. | Owner / Bot 1 |
| B-005 | 2026-11-22 | Bot 1 | OPEN (risk) | **Disk:** ~13 GB free on /workspace after tool install. **GitHub LFS quota:** free accounts get ~1 GB LFS storage + ~1 GB/month bandwidth. | Large textures/blends could exhaust disk or LFS quota. | Budgets TD-009; 1024² textures by default; no raw source textures > 4K in git; Godot export templates: extract Linux only. Watch `git lfs ls-files -s` sizes. Owner may need an LFS data pack later. | Bot 1 |
| B-006 | 2026-11-22 | Bot 1 | RESOLVED | git-lfs not installed initially. | – | Installed git-lfs 3.8.1 to `/workspace/tools/git-lfs`, symlinked `/usr/local/bin/git-lfs`. | Bot 1 |
