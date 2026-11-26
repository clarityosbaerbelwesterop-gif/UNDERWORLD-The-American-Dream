"""Vehicle sounds: engine RPM layers (granular firing-pulse synthesis), tyres, crashes, doors, horn,
sirens, propeller (T-AUD-01).

Engine model: every combustion event is a short exhaust pulse; the firing frequency is
rpm/60 * cylinders/2. Uneven firing orders (cross-plane V8, 270 deg twin) are modelled with a
per-cylinder amplitude/timing pattern, which is what gives a muscle car its lope. The pulse train
passes through exhaust-pipe resonances and a load-dependent low-pass; intake/valvetrain noise is
amplitude-modulated by the firing frequency. Each layer is rendered at a fixed RPM as a seamless
loop - the AudioDirector crossfades the layers and pitch-shifts them with the vehicle's RPM.
"""
import math

import numpy as np

from . import dsp as D

ENGINES = {
    # cylinders, firing pattern (amp, timing jitter), exhaust resonances, rpm per layer, character
    "Sedan":  dict(cyl=6, pattern=[1.0, 0.92, 0.97, 0.9, 1.0, 0.94], res=[(115, 6), (330, 5), (820, 4)],
                   rpm={"Idle": 780, "Low": 2400, "High": 5200}, rough=0.08, intake=0.18, bright=2600),
    "Muscle": dict(cyl=8, pattern=[1.0, 0.62, 0.95, 0.55, 0.9, 0.7, 0.98, 0.5], res=[(85, 7), (240, 5), (610, 4)],
                   rpm={"Idle": 720, "Low": 2600, "High": 5600}, rough=0.22, intake=0.15, bright=2200, lope=0.06),
    "Truck":  dict(cyl=8, pattern=[1.0, 0.85, 0.95, 0.8, 1.0, 0.88, 0.92, 0.82], res=[(70, 6), (190, 5), (480, 4)],
                   rpm={"Idle": 680, "Low": 2000, "High": 4200}, rough=0.12, intake=0.22, bright=1800, clatter=0.35),
    "Moto":   dict(cyl=2, pattern=[1.0, 0.8], res=[(150, 6), (420, 5), (1100, 4)],
                   rpm={"Idle": 1100, "Low": 4000, "High": 8500}, rough=0.15, intake=0.25, bright=3500, uneven=0.25),
}


def engine_layer(rng, kind, layer, seconds=4.0):
    E = ENGINES[kind]
    rpm = E["rpm"][layer]
    load = {"Idle": 0.25, "Low": 0.7, "High": 1.0}[layer]
    cyl = E["cyl"]
    f_fire = rpm / 60.0 * cyl / 2.0
    total = seconds + 0.5  # + loop crossfade -> make_loop returns exactly `seconds`
    n = D.n_of(total)
    imp = np.zeros(n)
    period = 1.0 / f_fire
    t = 0.0
    k = 0
    lope_phase = rng.uniform(0, 6.28)
    while t < total:
        pa = E["pattern"][k % len(E["pattern"])]
        amp = pa * (1.0 + rng.normal(0, E["rough"] * (1.2 - load)))
        if "lope" in E and layer == "Idle":
            amp *= 1.0 + E["lope"] * 4 * math.sin(2 * math.pi * 1.4 * t + lope_phase)
        idx = int(t * D.SR)
        if idx < n:
            imp[idx] += max(amp, 0.05)
        dt = period
        if "uneven" in E:
            dt = period * (1 + E["uneven"] * (1 if k % 2 == 0 else -1))
        t += dt * (1.0 + rng.normal(0, 0.004 if layer != "Idle" else 0.012))
        k += 1
    # pulse kernel: sharp exhaust pop with a short resonant tail
    kl = D.n_of(min(period * 1.6, 0.05))
    kt = np.arange(kl) / D.SR
    kern = (rng.standard_normal(kl) * 0.5 + np.sin(2 * math.pi * f_fire * 2.0 * kt)) * np.exp(-kt / (period * 0.35))
    pulses = np.convolve(imp, kern)[:n]
    ex = np.zeros(n)
    for f, q in E["res"]:
        ex += D.resonator(pulses, f * (1 + 0.15 * load), q) * 3.0
    ex += pulses * 0.6
    ex = D.lp(ex, E["bright"] * (0.55 + 0.6 * load))
    ex = D.saturate(ex * (0.8 + load), 1.5 + load)
    # intake / valvetrain: band noise modulated by firing frequency
    tt = np.arange(n) / D.SR
    mod = 0.5 + 0.5 * np.sin(2 * math.pi * f_fire * tt)
    intake = D.bp(D.white(rng, total), 900, 4500) * mod * E["intake"] * (0.4 + load)
    sub = np.sin(2 * math.pi * (f_fire / 2) * tt) * 0.25
    out = ex + intake + sub
    if "clatter" in E:
        out += D.crackle(rng, total, f_fire * 1.0, 0.0008, 1500, 6000) * E["clatter"] * 0.3
    if layer == "High":
        out += D.bp(D.white(rng, total), 300, 2000) * 0.08  # wind / road at speed
    out = D.make_loop(out, 0.5)
    return D.normalize_rms(D.pad_to(out, seconds), -16.0, -1.0)


def engine_start(rng, kind):
    E = ENGINES[kind]
    crank = D.silence(1.6)
    starter = D.osc(0.9, 260 + 30 * np.sin(np.linspace(0, 40, D.n_of(0.9))), "saw") * 0.15
    starter = D.bp(starter, 300, 3000) * D.env_adsr(0.9, 0.02, 0.1, 0.8, 0.15)
    chug = []
    for i in range(int(rng.integers(4, 7))):
        chug.append((D.lp(D.white(rng, 0.12), 500) * D.env_exp(0.12, 0.03) * 0.8, 0.05 + i * 0.13))
    idle = engine_layer(rng, kind, "Idle", 2.2)
    rev = engine_layer(rng, kind, "Low", 0.9) * np.concatenate(
        [np.linspace(0, 1, D.n_of(0.25)), np.linspace(1, 0, D.n_of(0.65))])[:D.n_of(0.9)][:, None].ravel()[:D.n_of(0.9)]
    out = D.mix(crank, starter, *chug, (rev * 0.8, 0.75), (idle * np.linspace(0, 1, len(idle)) ** 0.3, 0.95))
    return D.normalize(D.fade(out, 0.005, 0.4), -2.0)


def engine_stop(rng, kind):
    idle = engine_layer(rng, kind, "Idle", 1.2)
    env = np.linspace(1, 0, len(idle)) ** 2
    slow = idle * env
    tick = D.modal(0.6, [(2200, 0.2, 0.08)], rng)
    return D.normalize(D.mix(slow, (D.lp(D.white(rng, 0.3), 400) * D.env_exp(0.3, 0.05) * 0.5, 0.9), (tick * 0.3, 1.2)), -4.0)


def tire_skid(rng, seconds=3.0):
    total = seconds + 0.5
    n = D.n_of(total)
    tt = np.arange(n) / D.SR
    base = rng.uniform(950, 1200)
    f = base * (1 + 0.04 * np.sin(2 * math.pi * 3.1 * tt) + 0.02 * np.sin(2 * math.pi * 7.7 * tt + 1))
    tone = np.zeros(n)
    for h, a in ((1, 1.0), (2, 0.5), (3, 0.3), (4.2, 0.15)):
        tone += a * np.sin(2 * math.pi * np.cumsum(f * h) / D.SR)
    am = 0.7 + 0.3 * D.lp(rng.standard_normal(n), 25) * 4
    rub = D.bp(D.white(rng, total), 700, 5000) * 0.5
    out = D.make_loop((tone * 0.35 * am + rub) * 0.8, 0.5)
    return D.normalize_rms(D.pad_to(out, seconds), -16.0, -1.0)


def road_roll(rng, seconds=4.0):
    total = seconds + 0.5
    rumble = D.lp(D.brown(rng, total), 300) + D.bp(D.pink(rng, total), 400, 2500) * 0.25
    out = D.make_loop(rumble, 0.5)
    return D.normalize_rms(D.pad_to(out, seconds), -20.0, -3.0)


def crash(rng, v=0, heavy=False):
    dur = 2.4 if heavy else 1.4
    boom = D.sine_sweep(dur, 120, 40, 5) * D.env_exp(dur, 0.12 if heavy else 0.06, 0.001)
    crunch = D.crackle(rng, dur * 0.6, 400 if heavy else 220, 0.003, 300, 6000) * np.exp(-np.linspace(0, 6, D.n_of(dur * 0.6)))
    f = rng.uniform(300, 500)
    panel = D.modal(dur, [(f, 1.0, 0.25), (f * 1.6, 0.8, 0.18), (f * 2.7, 0.6, 0.12), (f * 4.1, 0.4, 0.08), (f * 5.3, 0.3, 0.05)], rng, 0.05)
    hit = D.lp(D.white(rng, 0.3), 3000) * D.env_exp(0.3, 0.02, 0.0005)
    parts = [boom * 1.2, crunch * 1.1, panel * 0.35, hit]
    if heavy:
        parts.append((D.granular_tinkle(rng, 1.6, 160, 2500, 9000, 0.003, 0.025, 2.5) * 0.4, 0.05))
        parts.append((D.crackle(rng, 1.0, 50, 0.004, 400, 3000) * 0.4, 0.4))
    out = D.mix(*parts)
    out = D.saturate(out, 2.0)
    ir = D.street_ir(rng, 0.8, 1.0)
    out = D.convolve(out, ir[:, 0], wet=0.25)
    return D.normalize(D.fade(out, 0, 0.3), -0.8)


def door(rng, v=0, open_=True):
    if open_:
        latch = D.modal(0.3, [(1400, 0.6, 0.02), (2600, 0.4, 0.012)], rng, 0.05)
        pull = D.lp(D.white(rng, 0.25), 1500) * D.env_adsr(0.25, 0.02, 0.06, 0.3, 0.1) * 0.4
        seal = D.bp(D.white(rng, 0.15), 200, 1200) * D.env_exp(0.15, 0.03) * 0.5
        out = D.mix(latch, (seal, 0.03), (pull, 0.05))
        return D.normalize(out, -6.0)
    thump = D.sine_sweep(0.6, 140, 55, 6) * D.env_exp(0.6, 0.05, 0.001)
    body = D.lp(D.white(rng, 0.6), 900) * D.env_exp(0.6, 0.025, 0.0008)
    panel = D.modal(0.6, [(rng.uniform(180, 230), 0.5, 0.08), (520, 0.3, 0.05), (1250, 0.2, 0.03)], rng, 0.05)
    latch = D.modal(0.2, [(2100, 0.4, 0.01), (3300, 0.25, 0.008)], rng, 0.05)
    out = D.saturate(D.mix(thump * 1.3, body, panel * 0.6, (latch, 0.006)), 1.8)
    return D.normalize(out, -2.5)


def horn(rng, seconds=1.0, truck=False):
    total = seconds + 0.2
    f1, f2 = (300, 375) if truck else (420, 525)
    n = D.n_of(total)
    tt = np.arange(n) / D.SR
    sig = np.zeros(n)
    for f in (f1, f2):
        ph = 2 * math.pi * f * tt + 0.3 * np.sin(2 * math.pi * 5 * tt)
        sig += np.sign(np.sin(ph)) * 0.5 + 0.3 * np.sin(2 * ph)
    sig = D.bp(sig, 350, 4000)
    for fr in (1100, 2300, 3200):
        sig += D.resonator(sig, fr, 4) * 0.6
    sig = D.saturate(sig * 0.6, 2.0)
    out = D.make_loop(sig, 0.2)
    return D.normalize_rms(D.pad_to(out, seconds), -14.0, -1.0)


def horn_honk(rng, v=0):
    h = horn(rng, 0.6)
    env = D.env_adsr(0.6, 0.01, 0.05, 0.9, 0.06)
    return D.normalize(h * env, -2.0)


def siren(rng, mode="Wail", seconds=None):
    """US-style electronic siren: wail (slow up/down sweep), yelp (fast), through a horn speaker."""
    if mode == "Wail":
        period, lo, hi = 4.0, 650, 1450
    elif mode == "Yelp":
        period, lo, hi = 0.32, 700, 1550
    else:  # HiLo (European-ish / fire), used for the FBI/ambulance variant
        period, lo, hi = 1.4, 600, 900
    seconds = seconds or (period * (2 if mode == "Wail" else 12))
    xf = 0.04  # crossfade between pitch-identical points one loop apart -> seamless wrap
    loop_len = seconds
    seconds = seconds + xf
    n = D.n_of(seconds)
    tt = np.arange(n) / D.SR
    ph = (tt / period) % 1.0
    if mode == "HiLo":
        f = np.where(ph < 0.5, hi, lo).astype(float)
        f = D.lp(f, 60.0)
    else:
        tri = np.where(ph < 0.5, ph * 2, 2 - ph * 2)
        f = lo + (hi - lo) * np.sin(tri * math.pi / 2) ** 1.2
    wave = D.osc(seconds, f, "square", pw=0.5) * 0.4 + D.osc(seconds, f, "sine") * 0.6
    wave = D.bp(wave, 500, 5000)
    wave = D.saturate(wave * 1.2, 2.0)
    wave += D.resonator(wave, 2400, 3) * 0.4
    wave = D.pad_to(D.make_loop(wave, xf), loop_len)
    return D.normalize_rms(wave, -15.0, -1.0)


PROP_RPM = {"Idle": 900, "Low": 1800, "High": 2600}


def propeller(rng, layer="Idle", seconds=4.0):
    """Light aircraft: 2-blade prop chop + air noise over a flat-engine body."""
    rpm = PROP_RPM[layer]
    f_blade = rpm / 60.0 * 2
    eng = engine_layer(rng, "Sedan", layer, seconds)
    total = seconds + 0.5
    n = D.n_of(total)
    tt = np.arange(n) / D.SR
    chop = 0.5 + 0.5 * np.sin(2 * math.pi * f_blade * tt) ** 8
    air = D.bp(D.white(rng, total), 150, 2500) * chop
    buzz = D.osc(total, f_blade, "saw") * 0.3
    buzz = D.lp(buzz, 900)
    out = D.make_loop(air * 0.7 + buzz, 0.5)
    out = D.pad_to(out, seconds) + eng * 0.5
    return D.normalize_rms(out, -15.0, -1.0)


def helicopter_loop(rng, seconds=6.0):
    total = seconds + 0.5
    n = D.n_of(total)
    tt = np.arange(n) / D.SR
    f_blade = 4 * 290 / 60.0
    chop = (0.5 + 0.5 * np.cos(2 * math.pi * f_blade * tt)) ** 10
    slap = D.lp(D.white(rng, total), 700) * chop * 2.0
    turb = D.bp(D.white(rng, total), 1800, 7000) * 0.15
    whine = np.sin(2 * math.pi * 1950 * tt) * 0.03
    out = D.make_loop(slap + turb + whine + D.lp(D.brown(rng, total), 120) * 0.4, 0.5)
    return D.normalize_rms(D.to_stereo(D.pad_to(out, seconds), 0.5), -16.0, -1.0)
