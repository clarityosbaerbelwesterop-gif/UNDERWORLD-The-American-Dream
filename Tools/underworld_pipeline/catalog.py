#!/usr/bin/env python3
"""UNDERWORLD content catalog tool (P1, T-DATA-01). Pure Python - does not boot Blender.

    Tools/uwp catalog status [--out Docs/Reports/CATALOG_STATUS.md]
    Tools/uwp catalog plan   [--milestone P3]
    Tools/uwp catalog check  [--catalog X] [--combat Y]       # exit 1 on any error
    Tools/uwp catalog build  [--milestone P3] [--id ID] [--profile dev|gate] [--dry-run]

Config/Content/catalog.json lists every asset of chapters 1+2 (built and planned) with its
milestone, generator command, source .blend and exported .glb. `check` is the cross-check the
merge gate runs: catalogue <-> combat database <-> files on disk. `build` runs each entry's
generator and then the validating exporter, so a milestone is produced with one command.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
TYPES = {"character", "animation", "environment", "prop", "vehicle", "weapon", "armor",
         "fx", "trim_sheet", "decal_set", "terrain", "audio", "ui"}
STATUSES = ("PLANNED", "WIP", "PRODUCTION-READY")
MILESTONES = tuple("P%d" % i for i in range(1, 11))
REQUIRED = ("id", "type", "milestone", "generator", "status")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def implemented_generators(repo):
    """uwp subcommands that exist today (parsed from cli.py, no Blender needed)."""
    try:
        src = open(os.path.join(repo, "Tools", "underworld_pipeline", "cli.py"), encoding="utf-8").read()
    except OSError:
        return set()
    return set(re.findall(r'add_parser\(\s*"([a-z0-9-]+)"', src)) | {"export", "validate"}


def generator_cmd(entry):
    g = entry.get("generator", "")
    return g.split()[0] if g and not g.startswith("authored") else None


def check(cat, combat, repo):
    """Returns (errors, warnings)."""
    errs, warns = [], []
    entries = cat.get("entries", [])
    ids = Counter(e.get("id") for e in entries)
    for i, n in ids.items():
        if n > 1:
            errs.append("duplicate id %s (%d entries)" % (i, n))
    by_id = {e.get("id"): e for e in entries}
    for e in entries:
        eid = e.get("id", "<no id>")
        for k in REQUIRED:
            if not e.get(k):
                errs.append("%s: missing field '%s'" % (eid, k))
        if e.get("type") not in TYPES:
            errs.append("%s: unknown type '%s'" % (eid, e.get("type")))
        if e.get("status") not in STATUSES:
            errs.append("%s: unknown status '%s'" % (eid, e.get("status")))
        if e.get("milestone") not in MILESTONES:
            errs.append("%s: unknown milestone '%s'" % (eid, e.get("milestone")))
        if e.get("status") != "PLANNED":
            for k in ("asset", "source"):
                p = e.get(k)
                if k == "asset" and not p:
                    errs.append("%s: status %s but no asset path" % (eid, e.get("status")))
                elif p and not os.path.exists(os.path.join(repo, p)):
                    errs.append("%s: %s %s does not exist" % (eid, k, p))
        if e.get("status") == "PRODUCTION-READY" and not e.get("review"):
            errs.append("%s: PRODUCTION-READY without a review record (QUALITY_GATE)" % eid)
    # combat database -> catalogue
    for wid, w in (combat.get("weapons") or {}).items():
        a = w.get("asset")
        if a and a not in by_id:
            errs.append("combat weapon %s: asset %s not in catalogue" % (wid, a))
        elif a and by_id[a].get("type") != "weapon":
            errs.append("combat weapon %s: catalogue entry %s is not a weapon" % (wid, a))
    for aid, a in (combat.get("armor") or {}).items():
        if aid.startswith("_") or not isinstance(a, dict):
            continue
        if a.get("asset") and a["asset"] not in by_id:
            errs.append("combat armor %s: asset %s not in catalogue" % (aid, a["asset"]))
    for fid, f in (combat.get("factions") or {}).items():
        for arch, models in (f.get("roster") or {}).items():
            for m in models:
                if m not in by_id:
                    errs.append("faction %s/%s: model %s not in catalogue" % (fid, arch, m))
                elif by_id[m].get("type") != "character":
                    errs.append("faction %s/%s: %s is not a character" % (fid, arch, m))
    # files on disk -> catalogue (nothing ships uncatalogued)
    catalogued = {os.path.normpath(e["asset"]) for e in entries if e.get("asset")}
    assets_root = os.path.join(repo, "Assets")
    for root, _dirs, files in os.walk(assets_root):
        rel_root = os.path.relpath(root, repo)
        if rel_root.split(os.sep)[:2] == ["Assets", "Test"]:
            continue
        for fn in files:
            if fn.endswith(".glb"):
                rel = os.path.normpath(os.path.join(rel_root, fn))
                if rel not in catalogued:
                    errs.append("uncatalogued asset on disk: %s" % rel)
    # generators that do not exist yet are planned work, not errors
    gens = implemented_generators(repo)
    missing = OrderedDict()
    for e in entries:
        g = generator_cmd(e)
        if g and g not in gens:
            missing.setdefault(g, []).append(e)
        elif g and spec_missing(e, repo):
            warns.append("%s: spec %s not written yet (%s)" % (e["id"], spec_missing(e, repo), e["milestone"]))
    for g, es in missing.items():
        warns.append("generator '%s' not implemented yet: %d entries (%s)"
                     % (g, len(es), ", ".join(sorted({e["milestone"] for e in es}))))
    return errs, warns


def spec_missing(entry, repo):
    """The JSON spec a build-* generator takes, if it does not exist yet."""
    for tok in entry.get("generator", "").split()[1:]:
        if tok.endswith(".json") and not os.path.exists(os.path.join(repo, tok)):
            return tok
    return None


def summarize(cat, repo):
    gens = implemented_generators(repo)
    rows = []
    for e in cat["entries"]:
        g = generator_cmd(e)
        rows.append(dict(e, generator_ready=(g in gens) if g else None,
                         on_disk=bool(e.get("asset")) and os.path.exists(os.path.join(repo, e["asset"]))))
    return rows


def cmd_status(args, cat, combat):
    rows = summarize(cat, args.repo)
    by_m = OrderedDict((m, []) for m in MILESTONES)
    for r in rows:
        by_m.setdefault(r["milestone"], []).append(r)
    st = Counter(r["status"] for r in rows)
    lines = ["# Content-Katalog – Status (automatisch erzeugt)", "",
             "Quelle: `Config/Content/catalog.json` · Werkzeug: `Tools/uwp catalog status`. "
             "Nicht von Hand editieren.", "",
             "| Status | Anzahl |", "|---|---|"]
    for s in STATUSES:
        lines.append("| %s | %d |" % (s, st.get(s, 0)))
    lines += ["| **gesamt** | **%d** |" % len(rows), ""]
    lines += ["| Meilenstein | gesamt | PLANNED | WIP | PRODUCTION-READY | Generator vorhanden |", "|---|---|---|---|---|---|"]
    for m, rs in by_m.items():
        if not rs:
            continue
        c = Counter(r["status"] for r in rs)
        gen_ok = sum(1 for r in rs if r["generator_ready"])
        gen_n = sum(1 for r in rs if r["generator_ready"] is not None)
        lines.append("| %s | %d | %d | %d | %d | %d/%d |" % (m, len(rs), c["PLANNED"], c["WIP"], c["PRODUCTION-READY"], gen_ok, gen_n))
    for m, rs in by_m.items():
        if not rs:
            continue
        lines += ["", "## %s" % m, "", "| ID | Typ | Status | Ziel | Generator | Datei |", "|---|---|---|---|---|---|"]
        for r in sorted(rs, key=lambda r: (r["type"], r["id"])):
            gen = "`%s`" % r["generator"] + ("" if r["generator_ready"] in (True, None) else " (fehlt)")
            lines.append("| %s | %s | %s | %s | %s | %s |" % (
                r["id"], r["type"], r["status"], r.get("quality_target", ""), gen, "✓" if r["on_disk"] else "–"))
    text = "\n".join(lines) + "\n"
    if args.out:
        out = os.path.join(args.repo, args.out) if not os.path.isabs(args.out) else args.out
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        print("[CATALOG] wrote %s" % os.path.relpath(out, args.repo))
    print("[CATALOG] %d entries: %s" % (len(rows), ", ".join("%s %d" % (s, st.get(s, 0)) for s in STATUSES)))
    return 0


def cmd_plan(args, cat, combat):
    rows = [r for r in summarize(cat, args.repo) if r["status"] != "PRODUCTION-READY"
            and (not args.milestone or r["milestone"] == args.milestone)]
    for r in sorted(rows, key=lambda r: (r["milestone"], r["type"], r["id"])):
        flag = "ready" if r["generator_ready"] else ("authored" if r["generator_ready"] is None else "NEEDS-GENERATOR")
        print("[CATALOG][PLAN] %s %-11s %-30s %-8s %-15s %s" % (r["milestone"], r["type"], r["id"], r["status"], flag, r["generator"]))
    print("[CATALOG] %d open entries" % len(rows))
    return 0


def cmd_check(args, cat, combat):
    errs, warns = check(cat, combat, args.repo)
    for w in warns:
        print("[CATALOG][WARN] %s" % w)
    for e in errs:
        print("[CATALOG][ERROR] %s" % e)
    print("[CATALOG] check: %d entries, %d errors, %d warnings -> %s"
          % (len(cat.get("entries", [])), len(errs), len(warns), "PASS" if not errs else "FAIL"))
    return 0 if not errs else 1


def cmd_build(args, cat, combat):
    gens = implemented_generators(args.repo)
    uwp = os.path.join(args.repo, "Tools", "uwp")
    sel = [e for e in cat["entries"]
           if (not args.milestone or e["milestone"] == args.milestone) and (not args.id or e["id"] in args.id)]
    if not sel:
        print("[CATALOG] nothing selected")
        return 2
    failed, skipped, built = [], [], []
    for e in sel:
        g = generator_cmd(e)
        why = ("authored by hand" if g is None else "generator '%s' not implemented" % g if g not in gens
               else "spec %s missing" % spec_missing(e, args.repo) if spec_missing(e, args.repo) else None)
        if why:
            skipped.append(e["id"])
            print("[CATALOG][SKIP] %s: %s" % (e["id"], why))
            continue
        steps = [[uwp] + e["generator"].split()]
        if e.get("source"):
            steps.append([uwp, "export", e["source"], "--profile", args.profile])
        for cmd in steps:
            print("[CATALOG][RUN] %s" % " ".join(cmd[1:]))
            if args.dry_run:
                continue
            rc = subprocess.call(cmd, cwd=args.repo)
            if rc != 0:
                failed.append("%s (%s -> exit %d)" % (e["id"], cmd[1], rc))
                break
        else:
            built.append(e["id"])
    print("[CATALOG] build%s: %d built, %d skipped, %d failed"
          % (" (dry run)" if args.dry_run else "", len(built), len(skipped), len(failed)))
    for f in failed:
        print("[CATALOG][FAIL] %s" % f)
    return 0 if not failed else 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="uwp catalog")
    p.add_argument("--repo", default=REPO)
    p.add_argument("--catalog", help="default <repo>/Config/Content/catalog.json")
    p.add_argument("--combat", help="default <repo>/GodotProject/Data/Content/combat.json")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status"); s.add_argument("--out", default="Docs/Reports/CATALOG_STATUS.md")
    s = sub.add_parser("plan"); s.add_argument("--milestone", choices=MILESTONES)
    sub.add_parser("check")
    s = sub.add_parser("build")
    s.add_argument("--milestone", choices=MILESTONES)
    s.add_argument("--id", action="append")
    s.add_argument("--profile", choices=["dev", "gate"], default="dev")
    s.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    a.repo = os.path.abspath(a.repo)
    try:
        cat = load(a.catalog or os.path.join(a.repo, "Config", "Content", "catalog.json"))
        combat = load(a.combat or os.path.join(a.repo, "GodotProject", "Data", "Content", "combat.json"))
    except (OSError, ValueError) as ex:
        print("[CATALOG][ERROR] cannot load catalogue/combat data: %s" % ex)
        return 2
    return {"status": cmd_status, "plan": cmd_plan, "check": cmd_check, "build": cmd_build}[a.cmd](a, cat, combat)


if __name__ == "__main__":
    sys.exit(main())
