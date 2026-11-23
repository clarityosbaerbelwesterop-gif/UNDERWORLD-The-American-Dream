"""`Tools/uwp build-props [--only ID]` - builds prop .blend sources from props/recipes.py.

Output: Blender/Source/<category>/<ID>/<ID>.blend, ready for `Tools/uwp export --profile gate`.
CC0 texture sets come from the local cache (`fetch_sources.py --groups props`); a missing set is
an error, never a silent grey material.
"""
import os

from . import kit
from .recipes import RECIPES


def build_all(repo_root, only=None, cache_dir=None):
    cache_dir = cache_dir or os.environ.get("UWP_CACHE") or os.path.join(repo_root, ".cache", "uwp_sources")
    names = list(RECIPES) if not only else [n.strip() for n in only.split(",")]
    unknown = [n for n in names if n not in RECIPES]
    if unknown:
        raise SystemExit(f"[PROPS] unknown prop id(s): {unknown}; known: {sorted(RECIPES)}")
    out = []
    for n in names:
        fn, cat = RECIPES[n]
        P = kit.Prop(n, cat, cache_dir)
        fn(P)
        out.append(P.finish(repo_root))
    return out
