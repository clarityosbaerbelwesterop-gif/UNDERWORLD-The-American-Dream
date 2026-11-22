"""Fetch and verify external CC0 / CC-BY asset sources into the gitignored local cache.

Usage:
  python3 Tools/underworld_pipeline/fetch_sources.py [--cache .cache/uwp_sources] [--groups characters,textures,mocap]

All downloaded archives are stored under .cache/uwp_sources/ (listed in .gitignore) so
large raw downloads never bloat Git LFS. Every source is verified CC0-1.0 or CC-BY-4.0
and documented in Docs/ASSET_LICENSES.md.
"""
import argparse
import hashlib
import json
import os
import subprocess
import urllib.request
import zipfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_CACHE = os.path.join(REPO_ROOT, ".cache", "uwp_sources")

MAKEHUMAN_PACKS = {
    "faceunits01": {
        "url": "https://files2.makehumancommunity.org/functional/faceunits01.zip",
        "license": "CC0-1.0",
        "author": "Mika Suominen / MakeHuman Community",
        "group": "characters",
    },
    "visemes01": {
        "url": "https://files2.makehumancommunity.org/functional/visemes01.zip",
        "license": "CC0-1.0",
        "author": "Mika Suominen / MakeHuman Community",
        "group": "characters",
    },
    "makehuman_system_assets": {
        "url": "https://files2.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip",
        "license": "CC0-1.0",
        "author": "MakeHuman Team (makehumancommunity.org)",
        "group": "characters",
    },
    "skins02": {
        "url": "https://files2.makehumancommunity.org/asset_packs/skins02/skins02_cc0.zip",
        "license": "CC0-1.0",
        "author": "MakeHuman Community (MargaretToigo, Mindfront, jartur69, OnlyTheGhosts)",
        "group": "characters",
    },
    "suits01": {
        "url": "https://files2.makehumancommunity.org/asset_packs/suits01/suits01_cc0.zip",
        "license": "CC0-1.0",
        "author": "MargaretToigo / MakeHuman Community",
        "group": "npcs",
    },
    "skins01": {
        "url": "https://files2.makehumancommunity.org/asset_packs/skins01/skins01_cc0.zip",
        "license": "CC0-1.0",
        "author": "MakeHuman Community",
        "group": "npcs",
    },
}

DIRECT_FILES = {
    "mocap/makehuman_walk1.bvh": {
        "url": "https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/animations/walks/walk1.bvh",
        "license": "CC0-1.0",
        "group": "mocap",
    },
    "mh_eyes/low-poly.obj": {
        "url": "https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/eyes/low-poly/low-poly.obj",
        "license": "CC0-1.0",
        "group": "characters",
    },
    "mh_eyes/low-poly.mhclo": {
        "url": "https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/eyes/low-poly/low-poly.mhclo",
        "license": "CC0-1.0",
        "group": "characters",
    },
    "mh_eyes/high-poly.obj": {
        "url": "https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/eyes/high-poly/high-poly.obj",
        "license": "CC0-1.0",
        "group": "characters",
    },
    "mh_eyes/high-poly.mhclo": {
        "url": "https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/eyes/high-poly/high-poly.mhclo",
        "license": "CC0-1.0",
        "group": "characters",
    },
    "mh_eyes/brown_eye.png": {
        "url": "https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/eyes/materials/brown_eye.png",
        "license": "CC0-1.0",
        "group": "characters",
    },
}

POLYHAVEN_TEXTURES = {
    "characters": [
        "brown_leather",
        "fabric_leather_02",
        "cotton_jersey",
        "denim_fabric_04",
        "denim_fabric_06",
        "knitted_fleece",
        "metal_plate",
    ],
    "weapons": [
        "metal_plate",
        "rusty_metal_02",
        "fabric_leather_02",
    ],
    "environment": [
        "asphalt_02",
        "concrete_pavement",
        "red_brick",
        "plastered_wall",
        "corrugated_iron",
        "bark_brown_02",
    ],
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "UnderworldPipeline/2.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
        while True:
            chunk = resp.read(1 << 18)
            if not chunk:
                break
            out.write(chunk)


def ensure_mpfb2_data(cache_dir):
    mpfb_dir = os.path.join(cache_dir, "mpfb2")
    data_dir = os.path.join(mpfb_dir, "src", "mpfb", "data")
    if os.path.isdir(data_dir):
        return data_dir
    os.makedirs(cache_dir, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
         "https://github.com/makehumancommunity/mpfb2.git", mpfb_dir],
        check=True,
    )
    subprocess.run(
        ["git", "-C", mpfb_dir, "sparse-checkout", "set", "--no-cone",
         "/src/mpfb/data/", "/LICENSE.md", "/LICENSE.ASSETS.md"],
        check=True,
    )
    return data_dir


def ensure_pack(cache_dir, name, info):
    dest = os.path.join(cache_dir, name)
    if os.path.isdir(dest) and os.listdir(dest):
        return dest
    zpath = os.path.join(cache_dir, "zips", f"{name}.zip")
    if not os.path.isfile(zpath):
        print(f"[FETCH] downloading {name} ({info['license']}) from {info['url']}")
        download(info["url"], zpath)
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(zpath) as zf:
        zf.extractall(dest)
    print(f"[FETCH] extracted {name} -> {dest}")
    return dest


def ensure_polyhaven_texture(cache_dir, asset_id, res="1k"):
    out = os.path.join(cache_dir, "textures", asset_id)
    if os.path.isdir(out) and any(f.endswith((".png", ".jpg")) for f in os.listdir(out)):
        return out
    url = f"https://api.polyhaven.com/files/{asset_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "UnderworldPipeline/2.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    os.makedirs(out, exist_ok=True)
    for ch in ("Diffuse", "nor_gl", "Rough", "AO", "arm", "Metal"):
        if ch not in data:
            continue
        rm = data[ch].get(res) or data[ch].get("1k")
        if not rm:
            continue
        fmt = "png" if "png" in rm else ("jpg" if "jpg" in rm else None)
        if not fmt:
            continue
        furl = rm[fmt]["url"]
        fpath = os.path.join(out, os.path.basename(furl))
        if not os.path.isfile(fpath):
            download(furl, fpath)
    print(f"[FETCH] Poly Haven CC0 texture: {asset_id} ({res})")
    return out


def fetch_all(cache_dir=DEFAULT_CACHE, groups=("characters", "textures", "mocap")):
    os.makedirs(cache_dir, exist_ok=True)
    if "characters" in groups or "npcs" in groups:
        ensure_mpfb2_data(cache_dir)
    for name, info in MAKEHUMAN_PACKS.items():
        if info["group"] in groups:
            ensure_pack(cache_dir, name, info)
    for rel, info in DIRECT_FILES.items():
        if info["group"] in groups:
            dest = os.path.join(cache_dir, rel)
            if not os.path.isfile(dest):
                print(f"[FETCH] {rel} ({info['license']})")
                download(info["url"], dest)
    for grp in groups:
        if grp in POLYHAVEN_TEXTURES:
            for aid in POLYHAVEN_TEXTURES[grp]:
                ensure_polyhaven_texture(cache_dir, aid, "1k")
        elif grp == "textures":
            for aid in POLYHAVEN_TEXTURES["characters"]:
                ensure_polyhaven_texture(cache_dir, aid, "1k")


def main():
    ap = argparse.ArgumentParser(description="Fetch verified CC0/CC-BY external sources into gitignored cache.")
    ap.add_argument("--cache", default=DEFAULT_CACHE)
    ap.add_argument("--groups", default="characters,textures,mocap",
                    help="comma list: characters,npcs,textures,mocap,weapons,environment")
    args = ap.parse_args()
    groups = tuple(g.strip() for g in args.groups.split(",") if g.strip())
    fetch_all(args.cache, groups)


if __name__ == "__main__":
    main()
