"""UNDERWORLD asset pipeline CLI. Runs inside Blender (headless):

  blender -b --factory-startup --python Tools/underworld_pipeline/cli.py -- <command> [options]
  (or the wrapper: Tools/uwp <command> [options])

Commands:
  validate <file.blend>   validation only, JSON report, no export
  export   <file.blend>   validate -> LODs -> collision -> .glb -> preview -> manifest -> verify
  validate-all / export-all   every .blend under Blender/Source (or --source-root)

Exit codes: 0 PASS · 1 validation failed · 2 export failed · 3 round-trip verify failed
            4 usage/input error · 5 internal error (for *-all: highest code of all assets)
"""
import argparse
import datetime
import glob
import json
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import bpy  # noqa: E402

from underworld_pipeline import VERSION  # noqa: E402
from underworld_pipeline import config as C  # noqa: E402
from underworld_pipeline import scene as S  # noqa: E402
from underworld_pipeline.config import Config, Issues  # noqa: E402


class UsageError(Exception):
    pass


class Ctx:
    pass


def build_parser():
    p = argparse.ArgumentParser(prog="uwp", description="UNDERWORLD Blender->Godot asset pipeline (T-PIPE-01)")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        sp.add_argument("--repo", default=os.path.abspath(os.path.join(HERE, "..", "..")),
                        help="repo root (default: this checkout)")
        sp.add_argument("--budgets", help="budgets JSON (default <repo>/Config/asset_budgets.json)")
        sp.add_argument("--category", help="budget category, e.g. Props, Environment/LA (default: from path)")
        sp.add_argument("--budget-key", help="explicit max_triangles key, e.g. Characters/SK_NPC")
        sp.add_argument("--strict", action="store_true", help="treat warnings as errors")
        sp.add_argument("--report", help="JSON report path (single asset) / summary path (*-all)")

    def export_opts(sp):
        sp.add_argument("--no-lod", action="store_true", help="do not generate LODs")
        sp.add_argument("--lod-ratios", help="comma list of decimate ratios, e.g. 0.5,0.25")
        sp.add_argument("--no-collision", action="store_true", help="do not generate collision")
        sp.add_argument("--collision", choices=["auto", "box", "convex", "trimesh", "none"], default="auto")
        sp.add_argument("--force-collision", action="store_true", help="generate even if UCX_ collision exists")
        sp.add_argument("--no-preview", action="store_true", help="skip the Cycles CPU preview PNG")
        sp.add_argument("--no-verify", action="store_true", help="skip the re-import round-trip check")
        sp.add_argument("--concept-turnaround", help="path to 4-panel concept art turnaround JPG/PNG for automated silhouette/proportion check")

    for name in ("validate", "export"):
        sp = sub.add_parser(name)
        sp.add_argument("blend")
        common(sp)
        if name == "export":
            sp.add_argument("--out", help="output .glb (default: Assets/<mirror of Blender/Source path>)")
            export_opts(sp)
    for name in ("validate-all", "export-all"):
        sp = sub.add_parser(name)
        sp.add_argument("--source-root", help="default <repo>/Blender/Source")
        common(sp)
        if name == "export-all":
            sp.add_argument("--out-root", help="write exports here instead of <repo>/Assets (mirrors paths)")
            export_opts(sp)

    # Unified whole-game asset generator subcommands (T-PIPE-03+)
    sp_bc = sub.add_parser("build-character", help="Build a character .blend from a JSON/YAML spec")
    sp_bc.add_argument("spec")
    sp_bc.add_argument("--repo", default=os.path.abspath(os.path.join(HERE, "..", "..")))
    sp_bc.add_argument("--no-bake", action="store_true")

    sp_sa = sub.add_parser("build-shared-anims", help="Export shared 53-bone A_Humanoid_Locomotion.glb library")
    sp_sa.add_argument("--repo", default=os.path.abspath(os.path.join(HERE, "..", "..")))

    sp_bw = sub.add_parser("build-weapon", help="Build a weapon .blend from a JSON spec")
    sp_bw.add_argument("spec")
    sp_bw.add_argument("--repo", default=os.path.abspath(os.path.join(HERE, "..", "..")))

    sp_bv = sub.add_parser("build-vehicle", help="Build a vehicle .blend from a JSON spec")
    sp_bv.add_argument("spec")
    sp_bv.add_argument("--repo", default=os.path.abspath(os.path.join(HERE, "..", "..")))

    sp_be = sub.add_parser("build-env", help="Build modular LA street environment kit .blend sources")
    sp_be.add_argument("--repo", default=os.path.abspath(os.path.join(HERE, "..", "..")))
    sp_be.add_argument("--only", default=None)

    sp_rt = sub.add_parser("retarget", help="Retarget a CC0 BVH clip onto a character .blend")
    sp_rt.add_argument("blend")
    sp_rt.add_argument("bvh")
    sp_rt.add_argument("--action-name", required=True)
    sp_rt.add_argument("--cyclic", action="store_true")
    return p


def _rel(cfg, path):
    try:
        r = os.path.relpath(path, cfg.repo)
        return path if r.startswith("..") else r
    except ValueError:
        return path


def process(blend, args, cfg, do_export, out=None):
    """One asset. Returns (exit_code, report dict)."""
    t0 = time.time()
    iss = Issues(strict=args.strict)
    report = {"tool": "underworld_pipeline", "version": VERSION, "blender": bpy.app.version_string,
              "timestamp": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
              "command": args.command, "input": _rel(cfg, os.path.abspath(blend)), "steps": {}}
    code = C.EXIT_OK
    try:
        if not os.path.isfile(blend):
            raise UsageError(f"input not found: {blend}")
        name = os.path.splitext(os.path.basename(blend))[0]
        cat = args.category or C.category_from_path(cfg.repo, blend)[0]
        if not cat:
            raise UsageError("cannot derive category from path; pass --category (Characters, Vehicles, Weapons, Environment/LA, Props, Test)")
        if C.Config.top(cat) not in C.CATEGORIES:
            raise UsageError(f"unknown category {cat}")
        bkey = cfg.resolve_budget_key(cat, name, args.budget_key)
        ctx = Ctx()
        ctx.cfg, ctx.issues, ctx.asset_name, ctx.category, ctx.budget_key, ctx.opts = cfg, iss, name, cat, bkey, args
        report.update({"asset": name, "category": cat, "budget_key": bkey})
        print(f"[UWP] === {name}  category={cat}  budget_key={bkey}  ({report['input']})")

        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend), load_ui=False)
        from underworld_pipeline import validate as V
        stats = V.validate(ctx)
        report["steps"]["validate"] = {"errors": iss.count("error"), "warnings": iss.count("warning")}
        if iss.has_errors:
            code = C.EXIT_VALIDATION
            return code, report
        if not do_export:
            return code, report

        from underworld_pipeline import exporter as E
        from underworld_pipeline import generate as G
        out = os.path.abspath(out or args.out or C.default_output(cfg.repo, blend) or "")
        if not out or not out.endswith(".glb"):
            raise UsageError("output path unknown or not .glb; pass --out <file.glb>")
        out_dir = os.path.dirname(out)

        # LODs
        lods = []
        if not args.no_lod:
            spec = cfg.per_category("lods", cat) or {}
            ratios = [float(x) for x in args.lod_ratios.split(",")] if args.lod_ratios else spec.get("ratios", [])
            lods = G.generate_lods(ctx, ratios, spec.get("distances_m", []))
        report["steps"]["lods"] = lods if not args.no_lod else "skipped (--no-lod)"
        # collision
        if args.no_collision:
            col = {"mode": "skipped (--no-collision)", "generated": [],
                   "existing": [o.name for o in bpy.context.scene.objects if S.is_collision(o)]}
        else:
            mode = cfg.per_category("collision", cat) if args.collision == "auto" else args.collision
            col = G.generate_collision(ctx, mode)
        report["steps"]["collision"] = col
        # Walkable-collision rule (B-PT-01): only for categories people walk/drive on.
        lip_cfg = cfg.get("collision_walkability") or {}
        if C.Config.top(cat) in lip_cfg.get("categories", ["Environment"]):
            lips = G.check_collision_micro_lips(ctx, float(lip_cfg.get("micro_lip_max_m", 0.02)),
                                                float(lip_cfg.get("micro_lip_min_m", 0.0005)))
            report["steps"]["collision"]["micro_lips"] = len(lips)
            if iss.has_errors:
                return C.EXIT_VALIDATION, report

        sc = bpy.context.scene
        exported = sorted(o.name for o in sc.objects if o.type not in ("CAMERA", "LIGHT"))
        lod_nodes = [lv["name"] for l in lods for lv in l["levels"] if lv["level"] > 0]
        col_nodes = [c["name"] for c in col["generated"]] + list(col["existing"])
        n_arm = sum(1 for o in sc.objects if o.type == "ARMATURE")
        anim_names = [a["name"] for a in stats["animations"]]

        if not E.export_glb(out):
            iss.error("EXPORT", f"glTF export did not produce {out}")
            return C.EXIT_EXPORT, report
        summ = E.glb_summary(out)
        report["steps"]["export"] = {"glb": _rel(cfg, out), "bytes": summ["bytes"]}
        print(f"[UWP] exported {out} ({summ['bytes']} bytes, {len(summ['nodes'])} nodes, {len(summ['animations'])} animations)")

        preview = None
        previews_map = {}
        silhouette_rep = None
        if not args.no_preview and stats.get("bbox"):
            if C.Config.top(cat) == "Characters" and not name.startswith("PT_"):
                previews_map = E.render_character_previews(ctx, out_dir, name, stats["bbox"])
                preview = previews_map.get("default")
                report["steps"]["preview"] = {k: _rel(cfg, v) for k, v in previews_map.items()}
            else:
                preview = os.path.join(out_dir, name + "_preview.png")
                ok = E.render_preview(ctx, preview, stats["bbox"])
                if not ok:
                    iss.warn("PREVIEW", "preview render failed")
                    preview = None
                report["steps"]["preview"] = _rel(cfg, preview) if preview else "failed"
        else:
            report["steps"]["preview"] = "skipped"

        # Automated silhouette & proportion comparison against turnaround concept art (if present)
        root_ob = sc.objects.get(name)
        concept_rel = getattr(args, "concept_turnaround", None) or (root_ob.get("uw_concept_turnaround") if root_ob else None)
        if concept_rel and previews_map.get("front") and previews_map.get("side"):
            concept_abs = concept_rel if os.path.isabs(concept_rel) else os.path.join(cfg.repo, concept_rel)
            if os.path.isfile(concept_abs):
                from underworld_pipeline import silhouette_check as SIL
                sil_path = os.path.join(out_dir, name + ".silhouette_report.json")
                try:
                    silhouette_rep = SIL.compare_turnaround(concept_abs, previews_map["front"], previews_map["side"], out_report_path=sil_path)
                except SIL.ConceptArtUnavailable as exc:
                    silhouette_rep = None
                    iss.warn("CONCEPT_UNAVAILABLE",
                             f"silhouette comparison skipped: {exc} (the reference board must be "
                             f"restored before any PRODUCTION-READY claim)", name)
                    report["steps"]["silhouette"] = {"skipped": str(exc)}
                if silhouette_rep is None:
                    pass
                else:
                    report["steps"]["silhouette"] = {
                        "report": _rel(cfg, sil_path),
                        "mean_iou": silhouette_rep["mean_iou"],
                        "mean_proportion_delta": silhouette_rep["mean_proportion_delta"],
                        "pass": silhouette_rep["pass"],
                    }
                if silhouette_rep is not None and silhouette_rep["pass"]:
                    iss.info("SILHOUETTE_MATCH",
                             f"turnaround match PASS: mean IoU={silhouette_rep['mean_iou']:.3f}, mean proportion delta={silhouette_rep['mean_proportion_delta']:.4f}",
                             name, **report["steps"]["silhouette"])
                elif silhouette_rep is not None:
                    iss.warn("SILHOUETTE_MATCH",
                             f"turnaround match below threshold: mean IoU={silhouette_rep['mean_iou']:.3f}, mean proportion delta={silhouette_rep['mean_proportion_delta']:.4f}",
                             name, **report["steps"]["silhouette"])

        # Collect blendshape names on exported meshes
        blendshapes = sorted({
            kb.name
            for o in sc.objects
            if o.type == "MESH" and o.data.shape_keys and len(o.data.shape_keys.key_blocks) > 1
            for kb in o.data.shape_keys.key_blocks[1:]
        })

        bb = stats.get("bbox")
        lod_totals = {}
        for l in lods:
            for lv in l["levels"]:
                lod_totals[lv["level"]] = lod_totals.get(lv["level"], 0) + lv["triangles"]
        manifest = {
            "asset": name,
            "status": "PIPELINE TEST PLACEHOLDER - NOT FINAL ART" if name.startswith("PT_") else "READY FOR REVIEW",
            "category": cat,
            "budget_key": bkey,
            "source_blend": _rel(cfg, os.path.abspath(blend)),
            "export_glb": _rel(cfg, out),
            "preview_png": _rel(cfg, preview) if preview else None,
            "previews": {k: _rel(cfg, v) for k, v in previews_map.items()} if previews_map else None,
            "tool": f"underworld_pipeline {VERSION}",
            "blender_version": bpy.app.version_string,
            "units": "metres (1 BU = 1 m = 1 Godot unit)",
            "up_axis": "Blender +Z -> glTF/Godot +Y",
            "front": "Blender -Y -> Godot +Z",
            "aabb_godot": S.bbox_godot(bb) if bb else None,
            "triangles": {"lod0": stats["triangles_lod0"], "budget": stats["triangle_budget"],
                          "per_lod_total": {f"LOD{k}": v for k, v in sorted(lod_totals.items())}},
            "lods": lods,
            "collision": col,
            "materials": stats["materials"],
            "textures": stats["textures"],
            "uv_overlap": stats.get("uv_overlap", {}),
            "texel_density": stats.get("texel_density", {}),
            "clipping": stats.get("clipping", []),
            "armatures": stats["armatures"],
            "blendshapes": blendshapes,
            "animations": stats["animations"],
            "sockets": stats["sockets"],
            "silhouette": report["steps"].get("silhouette"),
            "nodes": summ["nodes"],
            "glb_bytes": summ["bytes"],
        }
        man_path = os.path.join(out_dir, name + ".manifest.json")
        with open(man_path, "w") as f:
            json.dump(manifest, f, indent=2)
            f.write("\n")
        report["steps"]["manifest"] = _rel(cfg, man_path)

        if not args.no_verify:
            ok, det = E.verify_roundtrip(out, {"nodes": exported, "animations": anim_names, "lod_nodes": lod_nodes,
                                               "collision_nodes": col_nodes, "armatures": n_arm})
            report["steps"]["verify"] = det
            if not ok:
                for pmsg in det["problems"]:
                    iss.error("VERIFY", pmsg)
                return C.EXIT_VERIFY, report
            print(f"[UWP] round-trip OK: {len(det['reimport_objects'])} objects, {len(det['reimport_actions'])} actions")
        return code, report
    except UsageError as e:
        iss.error("USAGE", str(e))
        return C.EXIT_USAGE, report
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        iss.error("INTERNAL", f"{type(e).__name__}: {e}")
        return C.EXIT_INTERNAL, report
    finally:
        report["issues"] = iss.items
        report["summary"] = {"errors": iss.count("error"), "warnings": iss.count("warning"), "infos": iss.count("info")}
        report["seconds"] = round(time.time() - t0, 2)


def finish(report, code, path):
    report["exit_code"] = code
    report["result"] = C.EXIT_NAMES[code]
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
            f.write("\n")
        print(f"[UWP] report: {path}")


def main(argv):
    args = build_parser().parse_args(argv)
    if args.command == "build-character":
        from underworld_pipeline.characters import build_character as BC
        BC.build_from_spec(args.spec, repo_root=args.repo, do_bake=not args.no_bake)
        return C.EXIT_OK
    if args.command == "build-shared-anims":
        from underworld_pipeline.characters import build_shared_anims as BSA
        BSA.build_shared_library(repo_root=args.repo)
        return C.EXIT_OK
    if args.command == "build-weapon":
        from underworld_pipeline.weapons import build_weapon as BW
        BW.build_pistol_from_spec(args.spec, repo_root=args.repo)
        return C.EXIT_OK
    if args.command == "build-vehicle":
        from underworld_pipeline.vehicles import build_vehicle as BV
        BV.build_sedan_from_spec(args.spec, repo_root=args.repo)
        return C.EXIT_OK
    if args.command == "build-env":
        from underworld_pipeline.environment import build_la_kit as BLA
        BLA.build_all(repo_root=args.repo, only=args.only)
        return C.EXIT_OK
    if args.command == "retarget":
        from underworld_pipeline.characters import retarget as RT
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(args.blend), load_ui=False)
        arm = next((o for o in bpy.context.scene.objects if o.type == "ARMATURE"), None)
        if arm is None:
            print("[UWP][ERROR] RETARGET: no Armature found in", args.blend)
            return C.EXIT_USAGE
        act, n_frames = RT.retarget_bvh_to_armature(arm, args.bvh, args.action_name, cyclic=args.cyclic)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.blend), compress=True)
        print(f"[UWP] retargeted {args.bvh} -> {act.name} ({n_frames} frames) in {args.blend}")
        return C.EXIT_OK

    cfg = Config(args.repo, args.budgets)
    do_export = args.command.startswith("export")
    if args.command in ("validate", "export"):
        code, rep = process(args.blend, args, cfg, do_export)
        path = args.report
        if not path and do_export and code != C.EXIT_USAGE and rep.get("asset"):
            out = os.path.abspath(args.out or C.default_output(cfg.repo, args.blend) or "")
            if out.endswith(".glb"):
                path = os.path.join(os.path.dirname(out), rep["asset"] + ".validation.json")
        finish(rep, code, path)
        print(f"[UWP] RESULT: {C.EXIT_NAMES[code]} (exit {code}) errors={rep['summary']['errors']} warnings={rep['summary']['warnings']}")
        return code

    src_root = os.path.abspath(args.source_root or os.path.join(cfg.repo, "Blender", "Source"))
    blends = sorted(glob.glob(os.path.join(src_root, "**", "*.blend"), recursive=True))
    skip = cfg.defaults.get("export_all_skip_in_repo", {}) if do_export and not getattr(args, "out_root", None) else {}
    results, worst = [], C.EXIT_OK
    for b in blends:
        rel = _rel(cfg, b)
        if rel in skip:
            print(f"[UWP] skip {rel}: {skip[rel]}")
            results.append({"input": rel, "result": "SKIPPED", "reason": skip[rel]})
            continue
        out = None
        if do_export and args.out_root:
            out = os.path.join(os.path.abspath(args.out_root), os.path.splitext(os.path.relpath(b, src_root))[0] + ".glb")
        if do_export:
            o = out or C.default_output(cfg.repo, b)
            args.out = o
        code, rep = process(b, args, cfg, do_export, out=out)
        if do_export and rep.get("asset") and args.out:
            finish(rep, code, os.path.join(os.path.dirname(os.path.abspath(args.out)), rep["asset"] + ".validation.json"))
        else:
            finish(rep, code, None)
        results.append({"input": rel, "asset": rep.get("asset"), "result": C.EXIT_NAMES[code], "exit_code": code,
                        "errors": rep["summary"]["errors"], "warnings": rep["summary"]["warnings"],
                        "issues": [i for i in rep["issues"] if i["severity"] != "info"]})
        worst = max(worst, code)
        print(f"[UWP] {rel}: {C.EXIT_NAMES[code]}")
    summary = {"tool": "underworld_pipeline", "version": VERSION, "command": args.command, "source_root": _rel(cfg, src_root),
               "timestamp": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
               "assets": results, "exit_code": worst, "result": C.EXIT_NAMES[worst]}
    if args.report:
        with open(args.report, "w") as f:
            json.dump(summary, f, indent=2)
            f.write("\n")
    print(f"[UWP] RESULT: {C.EXIT_NAMES[worst]} (exit {worst}) assets={len(blends)}")
    return worst


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    try:
        rc = main(argv)
    except SystemExit as e:  # argparse
        rc = C.EXIT_USAGE if e.code not in (0, None) else 0
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        rc = C.EXIT_INTERNAL
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)
