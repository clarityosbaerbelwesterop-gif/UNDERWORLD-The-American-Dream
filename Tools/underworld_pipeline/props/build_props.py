"""`Tools/uwp build-props [--only ID]` - builds prop .blend sources from props/recipes.py.

Output: Blender/Source/<category>/<ID>/<ID>.blend, ready for `Tools/uwp export --profile gate`.
CC0 texture sets come from the local cache (`fetch_sources.py --groups props`); a missing set is
an error, never a silent grey material.
"""
import os

from . import kit
from .recipes import RECIPES
from .buildings import BUILDINGS


def build_all(repo_root, only=None, cache_dir=None, registry=None):
    cache_dir = cache_dir or os.environ.get("UWP_CACHE") or os.path.join(repo_root, ".cache", "uwp_sources")
    reg = RECIPES if registry is None else registry
    names = list(reg) if not only else [n.strip() for n in only.split(",")]
    unknown = [n for n in names if n not in reg]
    if unknown:
        raise SystemExit(f"[PROPS] unknown id(s): {unknown}; known: {sorted(reg)}")
    out = []
    for n in names:
        fn, cat = reg[n]
        P = kit.Prop(n, cat, cache_dir)
        fn(P)
        out.append(P.finish(repo_root, ground=not getattr(P, "keep_origin", False)))  # stairwells reach below z=0
    return out


def build_buildings(repo_root, only=None, cache_dir=None):
    """`Tools/uwp build-buildings [--only ID]` - building grammar (props/buildings.py, T-BLDG-01)."""
    return build_all(repo_root, only=only, cache_dir=cache_dir, registry=BUILDINGS)
