"""Ambience beds and environmental loops (T-AUD-01). All stereo, seamless loops.

Beds are built in layers like a field-recording edit: a low city drone, distant traffic wash with
slow swells, discrete events (pass-bys with Doppler, distant horns, sirens, dogs), and biology
(birds by day, crickets at night). Every layer has its own decorrelated stereo image.
"""
import math

import numpy as np

from . import dsp as D
from . import vehicles as V


def _wash(rng, seconds, lo, hi, swell_hz=0.05, depth=0.5):
    n = D.n_of(seconds)
    tt = np.arange(n) / D.SR
    ch = []
    for c in range(2):
        x = D.bp(D.pink(rng, seconds), lo, hi)
        mod = 1.0 + depth * np.sin(2 * math.pi * swell_hz * tt + rng.uniform(0, 6.28)) \
            + depth * 0.5 * np.sin(2 * math.pi * swell_hz * 2.7 * tt + rng.uniform(0, 6.28))
        ch.append(x * np.clip(mod, 0.1, None))
    return np.stack(ch, axis=1)


def _drone(rng, seconds, f=55.0):
    n = D.n_of(seconds)
    tt = np.arange(n) / D.SR
    hum = sum(a * np.sin(2 * math.pi * f * h * tt + rng.uniform(0, 6.28)) for h, a in ((1, 0.5), (2, 0.25), (3, 0.12)))
    rumble = D.lp(D.brown(rng, seconds), 110)
    return D.to_stereo(hum * 0.15 + rumble * 0.8, 0.8)


def car_pass(rng, speed=None, dist=None, dur=5.0, kind="Sedan"):
    speed = speed or rng.uniform(11, 20)
    dist = dist or rng.uniform(6, 25)
    eng = V.engine_layer(rng, kind, "Low", dur) * 0.6
    tyre = D.lp(D.brown(rng, dur), 900) * 0.7 + D.bp(D.pink(rng, dur), 500, 3000) * 0.3
    src = eng + tyre * 0.8
    return D.normalize(D.fade(D.doppler_pass(src, speed, dist, dur), 0.3, 0.3), -3.0)


def distant_horn(rng):
    h = V.horn(rng, rng.uniform(0.25, 0.7), truck=rng.random() < 0.3)
    h = D.lp(h, 1800) * D.env_adsr(len(h) / D.SR, 0.01, 0.05, 0.9, 0.08)
    ir = D.street_ir(rng, 1.4, 1.8)
    return D.convolve(h, ir, wet=0.9, dry=0.2) * 0.25


def distant_siren(rng, seconds=8.0):
    s = V.siren(rng, "Wail", seconds)
    s = D.lp(s, 1500) * np.sin(np.linspace(0, math.pi, len(s))) ** 1.5
    ir = D.street_ir(rng, 2.0, 2.6)
    return D.convolve(s, ir, wet=1.0, dry=0.1) * 0.18


def dog_bark(rng):
    """Distant dog: pitched noisy formant bursts."""
    out = D.silence(1.6)
    t = 0.0
    for i in range(int(rng.integers(2, 4))):
        dur = rng.uniform(0.12, 0.2)
        tt = D.t_axis(dur)
        f0 = rng.uniform(380, 520) * (1 - 0.3 * tt / dur)
        src = D.osc(dur, f0, "saw") * 0.6 + D.white(rng, dur) * 0.4
        v = sum(D.resonator(src, fr, 6) for fr in (700, 1300, 2600)) * np.sin(np.pi * tt / dur) ** 0.6
        out = D.mix(out, (v, t))
        t += dur + rng.uniform(0.15, 0.35)
    out = D.lp(out, 2200)
    ir = D.street_ir(rng, 1.2, 1.6)
    return D.convolve(out, ir, wet=0.8, dry=0.3) * 0.25


def birds(rng, seconds, rate=0.4):
    n = D.n_of(seconds)
    out = np.zeros((n, 2))
    t = rng.uniform(0, 2)
    while t < seconds - 1.5:
        pan = rng.uniform(-0.8, 0.8)
        phrase = D.silence(1.4)
        tc = 0.0
        base = rng.uniform(2800, 4800)
        for i in range(int(rng.integers(2, 7))):
            dur = rng.uniform(0.04, 0.12)
            tt = D.t_axis(dur)
            f = base * (1 + rng.uniform(-0.25, 0.35) * np.sin(np.pi * tt / dur * rng.uniform(0.5, 2)))
            chirp = np.sin(2 * math.pi * np.cumsum(f) / D.SR) * np.sin(np.pi * tt / dur) ** 2
            phrase = D.mix(phrase, (chirp, tc))
            tc += dur + rng.uniform(0.02, 0.12)
        phrase = D.lp(phrase, 7000) * rng.uniform(0.03, 0.09)
        st = D.to_stereo(phrase, 0.2, pan=pan)
        s = D.n_of(t)
        m = min(len(st), n - s)
        out[s:s + m] += st[:m]
        t += rng.exponential(1.0 / rate)
    return out


def crickets(rng, seconds, insects=7):
    n = D.n_of(seconds)
    tt = np.arange(n) / D.SR
    out = np.zeros((n, 2))
    for i in range(insects):
        f = rng.uniform(3900, 5200)
        chirp_rate = rng.uniform(1.6, 3.2)
        pulses = rng.integers(3, 6)
        pulse_rate = rng.uniform(28, 42)
        ph = (tt * chirp_rate + rng.uniform(0, 1)) % 1.0
        gate = (ph < pulses / pulse_rate * chirp_rate) * (0.5 + 0.5 * np.sin(2 * math.pi * pulse_rate * tt)) ** 4
        tone = np.sin(2 * math.pi * f * tt) * gate
        tone = D.lp(tone, 9000) * rng.uniform(0.02, 0.06) * (0.6 + 0.4 * np.sin(2 * math.pi * 0.03 * tt + i))
        out += D.to_stereo(tone, 0.0, pan=rng.uniform(-0.9, 0.9))
    return out


def street_bed(rng, seconds, city="LA", night=False):
    total = seconds + 3.0
    layers = []
    layers.append(_drone(rng, total, 50.0 if city == "LA" else 60.0) * (0.5 if night else 0.7))
    traffic = _wash(rng, total, 80, 900, 0.04, 0.45) * (0.35 if night else 0.6)
    hiss = _wash(rng, total, 900, 6000, 0.07, 0.3) * (0.06 if night else 0.12)
    layers += [traffic, hiss]
    base = D.mix(*layers)
    events = []
    n_pass = int(total / (9 if night else (4.5 if city == "LA" else 3.0)))
    for _ in range(n_pass):
        events.append((car_pass(rng, kind=rng.choice(["Sedan", "Sedan", "Truck", "Muscle"])) * rng.uniform(0.15, 0.4),
                       rng.uniform(0, total - 5)))
    n_horn = int(total / (25 if city == "LA" else 7))
    for _ in range(n_horn):
        events.append((distant_horn(rng), rng.uniform(0, total - 2)))
    if night:
        events.append((distant_siren(rng, 9.0), rng.uniform(2, total - 12)))
        events.append((dog_bark(rng), rng.uniform(0, total - 3)))
    if city == "NY":
        # subway rumble under the street, steam hiss
        rum = D.lp(D.brown(rng, 8.0), 90) * np.sin(np.linspace(0, math.pi, D.n_of(8.0))) ** 2 * 1.2
        events.append((D.to_stereo(rum, 0.7), rng.uniform(0, total - 9)))
    out = D.mix(base, *events)
    if night and city == "LA":
        out = D.mix(out, crickets(rng, total) * 1.0)
    if not night:
        out = D.mix(out, birds(rng, total, 0.35 if city == "LA" else 0.12))
    out = D.make_loop(out, 3.0)
    return D.normalize_rms(D.pad_to(out, seconds), -24.0, -6.0)


def rain(rng, seconds, heavy=False):
    total = seconds + 2.0
    n = D.n_of(total)
    chans = []
    for c in range(2):
        drops = D.crackle(rng, total, 5000 if heavy else 2600, 0.0004, 1500, 12000, amp_sigma=0.9) * 0.4
        patter = D.crackle(rng, total, 900 if heavy else 450, 0.0015, 400, 5000, amp_sigma=0.7) * 0.5
        hiss = D.bp(D.pink(rng, total), 800, 10000) * (0.5 if heavy else 0.3)
        chans.append(drops + patter + hiss)
    out = np.stack(chans, axis=1)
    gutter = D.to_stereo(D.bp(D.pink(rng, total), 200, 1500) * 0.2, 0.8)
    out = D.mix(out, gutter)
    out = D.make_loop(out, 2.0)
    return D.normalize_rms(D.pad_to(out, seconds), -22.0 if heavy else -25.0, -6.0)


def wind(rng, seconds):
    total = seconds + 2.0
    out = _wash(rng, total, 150, 1800, 0.08, 0.7)
    whistle = D.to_stereo(D.resonator(D.white(rng, total), 900, 40) * 0.15
                          * (0.5 + 0.5 * np.sin(np.linspace(0, 6, D.n_of(total)))), 0.6)
    out = D.make_loop(D.mix(out, whistle), 2.0)
    return D.normalize_rms(D.pad_to(out, seconds), -26.0, -6.0)


def interior_garage(rng, seconds):
    total = seconds + 2.0
    n = D.n_of(total)
    tt = np.arange(n) / D.SR
    hum = (np.sin(2 * math.pi * 120 * tt) * 0.4 + np.sin(2 * math.pi * 240 * tt) * 0.15
           + np.sin(2 * math.pi * 360 * tt) * 0.06)  # fluorescent ballast
    buzz = D.bp(D.white(rng, total), 2000, 8000) * 0.02 * (0.8 + 0.2 * np.sin(2 * math.pi * 0.5 * tt))
    tone = D.lp(D.brown(rng, total), 200) * 0.6
    drip = np.zeros(n)
    for _ in range(int(total / 3)):
        s = rng.integers(0, n - D.n_of(0.3))
        d = D.sine_sweep(0.12, 1800, 900, 6) * D.env_exp(0.12, 0.02) * 0.15
        drip[s:s + len(d)] += d
    ir = D.room_ir(rng, 1.2)
    out = D.convolve(D.to_stereo(hum * 0.3 + buzz + tone, 0.6), ir, wet=0.3)
    out = D.mix(out, D.convolve(drip, ir, wet=0.6))
    out = D.make_loop(D.pad_to(out, total), 2.0)
    return D.normalize_rms(D.pad_to(out, seconds), -30.0, -8.0)


def fire_loop(rng, seconds, big=False):
    total = seconds + 1.0
    roar = D.lp(D.brown(rng, total), 500 if big else 350)
    n = D.n_of(total)
    tt = np.arange(n) / D.SR
    roar *= 0.7 + 0.3 * D.lp(rng.standard_normal(n), 3.0) * 6
    crack = D.crackle(rng, total, 30 if big else 18, 0.003, 800, 8000, amp_sigma=1.1) * 1.2
    pops = D.crackle(rng, total, 4, 0.01, 300, 3000, amp_sigma=1.0) * 0.8
    hiss = D.bp(D.white(rng, total), 2500, 9000) * 0.06
    out = D.to_stereo(roar * (0.9 if big else 0.6) + crack + pops + hiss, 0.7)
    out = D.make_loop(out, 1.0)
    return D.normalize_rms(D.pad_to(out, seconds), -18.0, -2.0)


def steam_loop(rng, seconds):
    total = seconds + 1.0
    n = D.n_of(total)
    hiss = D.bp(D.white(rng, total), 1200, 10000) * (0.85 + 0.15 * D.lp(rng.standard_normal(n), 2.0) * 6)
    gurgle = D.granular_tinkle(rng, total, 8, 300, 900, 0.01, 0.03, 0.5) * 0.3
    out = D.make_loop(D.to_stereo(hiss + gurgle, 0.5), 1.0)
    return D.normalize_rms(D.pad_to(out, seconds), -20.0, -3.0)


def sparks_loop(rng, seconds):
    total = seconds + 1.0
    zap = D.crackle(rng, total, 80, 0.0008, 2000, 12000, amp_sigma=1.2)
    n = D.n_of(total)
    tt = np.arange(n) / D.SR
    hum = np.sign(np.sin(2 * math.pi * 60 * tt)) * 0.05
    hum = D.bp(hum, 100, 3000)
    out = D.make_loop(D.to_stereo(zap + hum, 0.4), 1.0)
    return D.normalize_rms(D.pad_to(out, seconds), -20.0, -2.0)
