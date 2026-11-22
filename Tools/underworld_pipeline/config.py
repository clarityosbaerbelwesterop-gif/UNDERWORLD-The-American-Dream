"""Budget/config resolution and the issue report (no bpy needed)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

EXIT_OK = 0
EXIT_VALIDATION = 1
EXIT_EXPORT = 2
EXIT_VERIFY = 3
EXIT_USAGE = 4
EXIT_INTERNAL = 5
EXIT_NAMES = {0: "PASS", 1: "VALIDATION_FAILED", 2: "EXPORT_FAILED", 3: "VERIFY_FAILED",
              4: "USAGE_ERROR", 5: "INTERNAL_ERROR"}

CATEGORIES = ("Characters", "Vehicles", "Weapons", "Environment", "Props", "Test")
# Allowed asset-root prefixes per top-level category (TD-005). PT_ is allowed everywhere.
CATEGORY_PREFIXES = {
    "Characters": ("SK_",),
    "Vehicles": ("VH_",),
    "Weapons": ("WPN_",),
    "Environment": ("SM_",),
    "Props": ("SM_",),
    "Test": ("PT_",),
}


class Issues:
    """Collects validation/export issues. severity: error | warning | info."""

    def __init__(self, strict=False):
        self.items = []
        self.strict = strict

    def add(self, severity, code, message, obj=None, **data):
        if severity == "warning" and self.strict:
            severity = "error"
        item = {"severity": severity, "code": code, "object": obj, "message": message}
        if data:
            item["data"] = data
        self.items.append(item)
        tag = {"error": "ERROR", "warning": "WARN", "info": "INFO"}[severity]
        print(f"[UWP][{tag}] {code}: {message}" + (f" ({obj})" if obj else ""))

    def error(self, code, message, obj=None, **d):
        self.add("error", code, message, obj, **d)

    def warn(self, code, message, obj=None, **d):
        self.add("warning", code, message, obj, **d)

    def info(self, code, message, obj=None, **d):
        self.add("info", code, message, obj, **d)

    def count(self, severity):
        return sum(1 for i in self.items if i["severity"] == severity)

    @property
    def has_errors(self):
        return self.count("error") > 0


def load_json(path):
    with open(path) as f:
        return json.load(f)


class Config:
    def __init__(self, repo, budgets_path=None):
        self.repo = os.path.abspath(repo)
        self.budgets_path = budgets_path or os.path.join(self.repo, "Config", "asset_budgets.json")
        self.budgets = load_json(self.budgets_path)
        self.defaults = load_json(os.path.join(HERE, "defaults.json"))

    def get(self, key):
        """Budgets file wins over tool defaults."""
        if key in self.budgets:
            return self.budgets[key]
        return self.defaults.get(key)

    @staticmethod
    def top(category):
        return category.split("/")[0]

    def per_category(self, key, category, fallback_key="default"):
        table = self.get(key) or {}
        if not isinstance(table, dict):
            return table
        for k in (category, self.top(category), fallback_key):
            if k in table:
                return table[k]
        return None

    def resolve_budget_key(self, category, asset_name, override=None):
        """Most specific max_triangles key: '<Top>/<prefix of asset>' > '<Category>' > '<Top>'."""
        table = self.budgets.get("max_triangles", {})
        if override:
            return override if override in table else None
        top = self.top(category)
        best = None
        for key in table:
            if "/" in key:
                cat, stem = key.split("/", 1)
                if cat == top and (asset_name == stem or asset_name.startswith(stem + "_")):
                    if best is None or len(key) > len(best):
                        best = key
        if best:
            return best
        for k in (category, top):
            if k in table:
                return k
        return None

    def max_triangles(self, key):
        return self.budgets.get("max_triangles", {}).get(key)

    def max_texture_size(self, category):
        sizes = self.get("max_texture_size") or {"default": 1024}
        hero = self.get("hero_categories") or []
        tier = "hero" if self.top(category) in hero else "default"
        return sizes.get(tier, sizes.get("default")), tier

    def reference_height(self, asset_name):
        for k, v in (self.get("reference_heights_m") or {}).items():
            parts = asset_name.split("_")
            if k in parts:
                return k, v
        return None, None


def category_from_path(repo, blend_path):
    """Blender/Source/<Category>[/<Sub>]/.../<Name>.blend -> 'Category' or 'Environment/LA'."""
    src = os.path.join(repo, "Blender", "Source")
    rel = os.path.relpath(os.path.abspath(blend_path), src)
    if rel.startswith(".."):
        return None, None
    parts = rel.split(os.sep)
    if len(parts) < 2 or parts[0] not in CATEGORIES:
        return None, rel
    if parts[0] == "Environment" and len(parts) >= 3:
        return "Environment/" + parts[1], rel
    return parts[0], rel


def default_output(repo, blend_path):
    """Mirror Blender/Source/<rel>/<Name>.blend -> Assets/<rel>/<Name>.glb (TD-006)."""
    src = os.path.join(repo, "Blender", "Source")
    rel = os.path.relpath(os.path.abspath(blend_path), src)
    if rel.startswith(".."):
        return None
    return os.path.join(repo, "Assets", os.path.splitext(rel)[0] + ".glb")
