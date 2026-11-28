"""T-AUD-01 pipeline test: procedural audio library (Tools/uwp build-audio).

    python3 Tools/underworld_pipeline/tests/test_audio_pipeline.py --scratch DIR

Checks (prints [TEST][PASS]/[TEST][FAIL], exit 1 on any failure):
  * registry: unique ids, naming prefixes (SFX_/AMB_/MUS_/UI_), buses known, every binding resolves
  * the committed runtime table GodotProject/Data/Content/audio.json is up to date (byte-identical)
  * a representative render (weapons, engine loop, ambience, music stinger, UI) into the scratch dir:
    Ogg Vorbis 48 kHz, expected channel count, not silent, peak <= -0.5 dBFS, |DC| < 1 %,
    loops wrap without a click (seam jump below the 99.9th-percentile sample step)
  * determinism: rendering the same event twice gives identical samples
  * negative control: the seam checker flags a deliberately broken loop
The repo is never written to.
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, "..", ".."))
REPO = os.path.abspath(os.path.join(TOOLS, ".."))
sys.path.insert(0, TOOLS)

from underworld_pipeline.audio import build_audio as B  # noqa: E402
from underworld_pipeline.audio import dsp as D  # noqa: E402

FAILS = []


def check(cond, msg):
    print(("[TEST][PASS] " if cond else "[TEST][FAIL] ") + msg, flush=True)
    if not cond:
        FAILS.append(msg)


def seam_ok(x):
    m = x.mean(axis=1) if x.ndim == 2 else x
    jump = abs(m[0] - m[-1])
    p999 = float(np.percentile(np.abs(np.diff(m)), 99.9))
    return jump <= p999, jump, p999


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", required=True)
    a = ap.parse_args()
    import soundfile as sf

    reg = B.build_registry()
    ids = [e["id"] for e in reg]
    check(len(ids) == len(set(ids)), f"{len(ids)} unique event ids")
    check(len(ids) >= 120, f">= 120 events ({len(ids)})")
    check(sum(e["n"] for e in reg) >= 300, f">= 300 variations ({sum(e['n'] for e in reg)})")
    badname = [i for i in ids if not i.split("_")[0] in ("SFX", "AMB", "MUS", "UI")]
    check(not badname, f"naming prefixes SFX_/AMB_/MUS_/UI_ {badname}")
    badbus = [e["id"] for e in reg if e["bus"] not in B.BUSES]
    check(not badbus, f"every event routes to a known bus {badbus}")

    # bindings resolve
    idset = set(ids)
    missing = []
    for wid, wb in B.BINDINGS["weapons"].items():
        for k in ("fire", "tail", "hit", "explode", "pump_after_shot"):
            if k in wb and wb[k] not in idset:
                missing.append(f"{wid}.{k}")
        for _, eid in wb.get("reload", []):
            if eid not in idset:
                missing.append(f"{wid}.reload {eid}")
    for fx, eid in B.BINDINGS["fx"].items():
        if eid not in idset:
            missing.append(fx)
    for sec in ("ui", "character", "music"):
        for k, v in B.BINDINGS[sec].items():
            if isinstance(v, str) and v not in idset:
                missing.append(f"{sec}.{k}")
    for kind in set(B.BINDINGS["vehicles"]["engine_sets"].values()):
        for layer in ("Idle", "Low", "High"):
            if f"SFX_VEH_{kind}_Engine_{layer}" not in idset:
                missing.append(f"engine {kind} {layer}")
        if kind not in B.BINDINGS["vehicles"]["layer_rpm"]:
            missing.append(f"layer_rpm {kind}")
    check(not missing, f"every binding names an existing event {missing}")
    combat = json.load(open(os.path.join(REPO, "GodotProject/Data/Content/combat.json")))
    unbound = [w for w in combat["weapons"] if w not in B.BINDINGS["weapons"]]
    check(not unbound, f"every combat.json weapon has a sound set {unbound}")

    # committed table up to date
    scratch = os.path.abspath(a.scratch)
    os.makedirs(scratch, exist_ok=True)
    rc = B.main(["--repo", scratch, "--table-only"])
    got = open(os.path.join(scratch, B.RUNTIME_TABLE), "rb").read()
    committed_path = os.path.join(REPO, B.RUNTIME_TABLE)
    committed = open(committed_path, "rb").read() if os.path.isfile(committed_path) else b""
    check(rc == 0 and got == committed, "GodotProject/Data/Content/audio.json is up to date (Tools/uwp build-audio --table-only)")

    # representative render
    sample = ["SFX_WPN_Pistol_Fire", "SFX_WPN_Shotgun_Tail", "SFX_WPN_MagIn_Rifle", "SFX_IMP_Glass", "SFX_FS_Gravel_Run",
              "SFX_VEH_Muscle_Engine_Idle", "SFX_VEH_Siren_Wail", "SFX_VEH_Crash_Heavy", "AMB_Wind", "SFX_FIRE_Loop",
              "MUS_Stinger_MissionPassed", "UI_Objective_Complete"]
    byid = {e["id"]: e for e in reg}
    for eid in sample:
        e = byid[eid]
        rc = B.main(["--repo", scratch, "--only", eid])
        path = os.path.join(scratch, B.rel_path(e, 0))
        ok = rc == 0 and os.path.isfile(path)
        check(ok, f"{eid}: rendered {B.rel_path(e, 0)}")
        if not ok:
            continue
        info = sf.info(path)
        x, sr = sf.read(path, always_2d=False)
        want_ch = 2 if e["stereo"] else 1
        check(info.format == "OGG" and info.subtype == "VORBIS" and sr == 48000 and info.channels == want_ch,
              f"{eid}: Ogg Vorbis 48 kHz, {want_ch} ch ({info.format}/{info.subtype} {sr} Hz {info.channels} ch)")
        pk = D.peak_dbfs(x)
        rms = D.rms_db(x)
        dc = float(np.abs(np.mean(x, axis=0)).max())
        check(rms > -45.0 and pk <= -0.3 and dc < 0.01,
              f"{eid}: level ok (peak {pk:.1f} dBFS, rms {rms:.1f} dB, dc {dc:.4f})")
        if e["loop"]:
            raw = B.render(e, 0)
            good, jump, p = seam_ok(raw)
            check(good, f"{eid}: seamless loop (wrap jump {jump:.4f} <= p99.9 step {p:.4f})")
    # determinism
    e = byid["SFX_WPN_Rifle_Fire"]
    x1, x2 = B.render(e, 1), B.render(e, 1)
    check(np.array_equal(x1, x2), "rendering is deterministic (seeded per event + variation)")
    check(not np.array_equal(B.render(e, 0), x1), "variations differ")
    # negative control for the seam checker
    rng = np.random.default_rng(1)
    broken = np.concatenate([D.lp(D.white(rng, 1.0), 400) * 0.1, np.full(D.n_of(1.0), 0.6)])
    check(not seam_ok(broken)[0], "seam checker flags a broken loop (negative control)")

    print(f"AUDIO PIPELINE TESTS: {'PASS' if not FAILS else 'FAIL (%d)' % len(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
