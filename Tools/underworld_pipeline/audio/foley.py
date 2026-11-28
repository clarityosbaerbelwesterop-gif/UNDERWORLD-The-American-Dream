"""Character foley: footsteps per surface, jump/land, cloth, body falls (T-AUD-01).

A footstep = heel strike (low thud + surface transient) followed 35-90 ms later by the toe/ball roll
(shorter, brighter), plus surface-specific detail (grit, ringing, hollow wood, crunch, splash).
`run=True` gives harder, faster strikes with less heel-toe gap.
"""
import math

import numpy as np

from . import dsp as D

SURFACES = ("Concrete", "Asphalt", "Metal", "Wood", "Grass", "Gravel", "Water")


def _strike(rng, dur, tau, lo, hi, gain):
    return D.bp(D.white(rng, dur), lo, hi) * D.env_exp(dur, tau, 0.0008) * gain


def footstep(rng, surface, v=0, run=False):
    dur = 0.38
    gap = rng.uniform(0.028, 0.045) if run else rng.uniform(0.05, 0.085)
    hard = 1.35 if run else 1.0
    heel_thud = D.lp(D.white(rng, dur), 260) * D.env_exp(dur, 0.018, 0.001) * 1.6 * hard
    if surface in ("Concrete", "Asphalt"):
        bright = 5200 if surface == "Concrete" else 3600
        heel = _strike(rng, dur, 0.008, 300, bright, 0.9 * hard)
        toe = _strike(rng, dur, 0.005, 600, bright * 1.2, 0.6 * hard)
        grit = D.crackle(rng, 0.12, 260 if surface == "Asphalt" else 140, 0.0006, 2500, 9000) * 0.35
        out = D.mix(heel_thud + heel, (grit, 0.002), (toe, gap), (grit * 0.6, gap + 0.01))
    elif surface == "Metal":
        f = rng.uniform(380, 520)
        ring = D.modal(dur, [(f, 1.0, 0.09), (f * 1.93, 0.6, 0.06), (f * 2.87, 0.45, 0.05), (f * 4.6, 0.3, 0.03)], rng, 0.03)
        heel = _strike(rng, dur, 0.004, 1000, 8000, 0.6)
        toe = D.modal(dur, [(f * 1.1, 0.6, 0.06), (f * 2.2, 0.4, 0.04)], rng, 0.04)
        out = D.mix(heel_thud * 0.8 + heel + ring * 0.5 * hard, (toe * 0.4 + _strike(rng, dur, 0.003, 1500, 8000, 0.4), gap))
    elif surface == "Wood":
        f = rng.uniform(140, 210)
        hollow = D.modal(dur, [(f, 1.0, 0.05), (f * 2.4, 0.6, 0.03), (f * 3.9, 0.3, 0.02)], rng, 0.05)
        creak = D.resonator(D.white(rng, dur), rng.uniform(900, 1400), 25) * D.env_adsr(dur, 0.02, 0.05, 0.3, 0.1) * 0.25
        heel = _strike(rng, dur, 0.006, 300, 4000, 0.6)
        out = D.mix(heel_thud + hollow * 0.8 * hard + heel, (_strike(rng, dur, 0.004, 500, 5000, 0.4) + hollow * 0.3, gap),
                    (creak if rng.random() < 0.35 else creak * 0, 0.02))
    elif surface == "Grass":
        rustle = D.bp(D.white(rng, dur), 1200, 8000) * D.env_adsr(dur, 0.01, 0.08, 0.2, 0.12) * 0.6
        crunch = D.crackle(rng, 0.2, 500, 0.0008, 2000, 9000) * np.linspace(1, 0, D.n_of(0.2)) * 0.4
        out = D.mix(heel_thud * 0.7, rustle, (crunch, gap * 0.5))
    elif surface == "Gravel":
        crunch = D.crackle(rng, 0.3, 1600 if run else 1100, 0.0009, 900, 8000) * D.env_exp(0.3, 0.07, 0.003)
        crunch2 = D.crackle(rng, 0.25, 900, 0.0009, 1200, 8000) * D.env_exp(0.25, 0.05, 0.002)
        out = D.mix(heel_thud * 0.8, crunch * 0.9 * hard, (crunch2 * 0.6, gap))
    elif surface == "Water":
        splash = D.bp(D.white(rng, dur), 700, 7000) * D.env_adsr(dur, 0.004, 0.06, 0.25, 0.2)
        bubbles = D.granular_tinkle(rng, dur, 40, 600, 2400, 0.004, 0.012, 3.0) * 0.5
        out = D.mix(heel_thud * 0.6, splash * 0.8 * hard, (bubbles, 0.02), (splash * 0.4, gap))
    else:
        raise ValueError(surface)
    out = D.fade(D.pad_to(out, dur), 0.0, 0.05)
    return D.normalize(out, -4.0 if run else -6.0)


def jump(rng, v=0):
    push = footstep(rng, "Concrete", run=True) * 0.8
    cloth = D.bp(D.white(rng, 0.4), 400, 3500) * D.env_adsr(0.4, 0.05, 0.1, 0.4, 0.2) * 0.25
    breath = D.bp(D.white(rng, 0.3), 500, 2500) * D.env_adsr(0.3, 0.02, 0.1, 0.3, 0.15) * 0.12
    return D.normalize(D.mix(push, (cloth, 0.02), (breath, 0.03)), -6.0)


def land(rng, v=0, heavy=False):
    a = footstep(rng, "Concrete", run=True)
    b = footstep(rng, "Concrete", run=True)
    thump = D.lp(D.white(rng, 0.4), 200) * D.env_exp(0.4, 0.04, 0.002) * (2.2 if heavy else 1.4)
    cloth = D.bp(D.white(rng, 0.3), 300, 3000) * D.env_exp(0.3, 0.05) * 0.4
    return D.normalize(D.mix(a, (b, 0.02), thump, (cloth, 0.01)), -3.0 if heavy else -5.0)


def cloth(rng, v=0):
    dur = rng.uniform(0.35, 0.6)
    n = D.white(rng, dur)
    shape = np.sin(np.linspace(0, math.pi, D.n_of(dur))) ** 1.5
    mod = 0.6 + 0.4 * np.sin(np.linspace(0, rng.uniform(8, 16), D.n_of(dur)))
    out = D.bp(n, 500, 5000) * shape * mod
    out += D.crackle(rng, dur, 120, 0.001, 2000, 7000) * 0.15
    return D.normalize(out, -12.0)


def body_fall(rng, v=0):
    thud = D.sine_sweep(0.6, 110, 45, 4) * D.env_exp(0.6, 0.08, 0.003)
    slap = D.lp(D.white(rng, 0.6), 1500) * D.env_exp(0.6, 0.03, 0.002)
    second = D.lp(D.white(rng, 0.4), 900) * D.env_exp(0.4, 0.03, 0.002) * 0.6
    cloth_ = D.bp(D.white(rng, 0.6), 300, 3000) * D.env_exp(0.6, 0.12) * 0.25
    gear = D.modal(0.4, [(1800, 0.2, 0.05), (2600, 0.15, 0.04)], rng, 0.1)
    return D.normalize(D.saturate(D.mix(thud * 1.2 + slap + cloth_, (second, rng.uniform(0.12, 0.2)), (gear, 0.05)), 1.5), -2.5)


def pickup_item(rng, v=0, kind="cash"):
    if kind == "cash":
        rif = D.crackle(rng, 0.35, 900, 0.0006, 2500, 10000) * D.env_adsr(0.35, 0.02, 0.1, 0.4, 0.15)
        slap = D.bp(D.white(rng, 0.2), 800, 6000) * D.env_exp(0.2, 0.01) * 0.6
        return D.normalize(D.mix(rif, (slap, 0.25)), -6.0)
    grab = D.lp(D.white(rng, 0.3), 2000) * D.env_exp(0.3, 0.03) * 0.8
    cloth_ = cloth(rng)
    return D.normalize(D.mix(grab, (cloth_ * 0.6, 0.03)), -6.0)
