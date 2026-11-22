# Handoff Protocol

All three agents share one Linux box and filesystem, but **not** a conversation. Nothing counts as handed off until it is committed, pushed and written down here-style.

## 1. Working copies (never share one checkout)
| Agent | Path | Branch |
|---|---|---|
| Bot 1 (integration) | `/workspace/UNDERWORLD` | `main` |
| Bot 2 | `/workspace/UNDERWORLD-bot2` (git worktree) | `bot2/dev` (or `bot2/<task-id>`) |
| Bot 3 | `/workspace/UNDERWORLD-bot3` (git worktree) | `bot3/dev` (or `bot3/<task-id>`) |

Create if missing: `cd /workspace/UNDERWORLD && git worktree add ../UNDERWORLD-bot2 bot2/dev` (branch exists on origin).
Sync often: `git fetch origin && git rebase origin/main` (on your own branch only).

## 2. Before you start a task
1. `git pull` / rebase on `origin/main`; read `PROJECT_STATUS.md`, `TASK_BOARD.md`, `BLOCKERS.md`.
2. Only take tasks assigned to you. Set Status → `IN PROGRESS` in TASK_BOARD (your row only), commit.
3. Do not edit files owned by another agent (TD-007). Need a change there? Write a request (§4).

## 3. Finishing a task
1. Run `./Tests/run_pipeline_smoke.sh` (and `Tests/run_all.sh` once it exists). It must PASS.
2. Update: TASK_BOARD status → `READY FOR REVIEW`, DEVELOPMENT_LOG entry (what + how verified), ASSET_REGISTRY row (Bot 2) / INTEGRATION_LOG entry (Bot 3), BLOCKERS if anything is unresolved. An art asset stays `WIP` in the registry until the Quality Gate says otherwise.
3. Commit with message `[T-XXX-NN] short summary`, push your branch, open a PR to `main` (`gh pr create`) with the handoff note below as body. For an important asset, attach renders, a `Tools/uwp review-sheet` contact sheet, and a filled `Docs/Reviews/` draft.
4. Bot 1 reviews and merges the PR, and may set the *task* to `COMPLETED`. That is not a production art sign-off.
5. **Quality Gate (`Docs/QUALITY_GATE.md`).** The creator is never the sole reviewer. Bot 1 scores art; Bot 3 scores technical / Godot integration (Phase 8 software-GL capture on this box). Pass = ≥ 4/5 in every applicable category. Only then may the registry status become `PRODUCTION-READY`. Never mark an asset FINAL/AAA because a script succeeded.

## 4. Handoff note template (PR body or `Docs/Handoffs/<date>_<task>.md`)
```
Task: T-ART-04 · From: Bot 2 · To: Bot 3
Files: Blender/Source/Vehicles/VH_Sedan_01/VH_Sedan_01.blend, Assets/Vehicles/VH_Sedan_01/VH_Sedan_01.glb (+manifest)
What it is: ...
Key data: dims, tri count, pivot, node names, sockets, wheel radius, animation names + speeds/loop flags
How verified: command(s) run + result
Known issues / not done: ...
Needs from receiver: ...
```

## 5. Asset requests (Bot 3 → Bot 2)
Write in TASK_BOARD (via Bot 1) or `Docs/Handoffs/REQ_<name>.md`: exact name, purpose, dimensions, node/socket names, animation list with speeds, budget, deadline/priority.

## 6. Decision requests (anyone → Bot 1)
Add a row "PROPOSED" to `TECHNICAL_DECISIONS.md` at the bottom with options + recommendation; Bot 1 decides and records. Conflicts are resolved by Bot 1.

## 7. Hard rules
- Never claim done without a run log. Never mark placeholders as final (`PT_` prefix). Never call an asset `PRODUCTION-READY` or “AAA” without a passed Quality Gate (renders, reference comparison, validation, in-engine test).
- Never force-push `main`, never rewrite others' history, never delete another agent's files.
- Never commit secrets or files > 100 MB; big binaries go through LFS.
