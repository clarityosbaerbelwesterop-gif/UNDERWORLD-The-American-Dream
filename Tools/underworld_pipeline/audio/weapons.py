"""Weapon, melee, throwable and bullet-impact sounds (T-AUD-01).

A gunshot is layered the way a recorded one is edited in a AAA weapon pack:
  1. muzzle blast  - broadband pressure burst, sub-millisecond attack
  2. body / thump  - pitched low-frequency punch (barrel + chest-feel), saturated
  3. chamber pop   - resonant mid band (action / receiver)
  4. supersonic    - N-wave crack for rifle calibres
  5. mechanics     - slide / bolt / cylinder transients 5-60 ms after the shot
  6. space         - short street early reflections baked in; the long tail is a separate
                     "_Tail" event so the engine can layer it by distance.
"""
import math

import numpy as np

from . import dsp as D

# per-weapon character: body_hz, blast_tau, thump_tau, pop (freq, q, gain), crack, mech list, gain
WEAPONS = {
    "Pistol":   dict(body=62, blast_tau=0.006, thump_tau=0.045, pop=(1250, 3.0, 0.55), crack=0.0,
                     hi=7500, mech=[(0.009, 3400, 0.30), (0.038, 2600, 0.22)], length=0.75, drive=2.4, rt=0.9),
    "Revolver": dict(body=48, blast_tau=0.010, thump_tau=0.070, pop=(900, 2.5, 0.65), crack=0.0,
                     hi=6500, mech=[(0.004, 2100, 0.12)], length=0.95, drive=2.8, rt=1.05),
    "SMG":      dict(body=70, blast_tau=0.004, thump_tau=0.030, pop=(1600, 3.5, 0.5), crack=0.0,
                     hi=8500, mech=[(0.006, 4200, 0.28), (0.022, 3100, 0.18)], length=0.45, drive=2.0, rt=0.7),
    "Shotgun":  dict(body=42, blast_tau=0.016, thump_tau=0.110, pop=(650, 2.0, 0.7), crack=0.0,
                     hi=5500, mech=[], length=1.25, drive=3.0, rt=1.3),
    "Rifle":    dict(body=55, blast_tau=0.007, thump_tau=0.060, pop=(1400, 3.0, 0.6), crack=1.0,
                     hi=9500, mech=[(0.007, 3800, 0.25), (0.030, 2900, 0.15)], length=0.85, drive=2.6, rt=1.1),
    "Sniper":   dict(body=40, blast_tau=0.012, thump_tau=0.120, pop=(800, 2.2, 0.7), crack=1.6,
                     hi=9000, mech=[], length=1.6, drive=3.2, rt=1.6),
}


def _n_wave(rng, dur=0.0006):
    n = D.n_of(dur)
    w = np.linspace(1, -1, n)
    w = np.concatenate([[0.0], w, [0.0]])
    return D.hp(w, 1500.0) * 1.4


def _mech_click(rng, f, amp):
    """Metal-on-metal transient: inharmonic modes + a noise tick."""
    modes = [(f, 1.0, 0.012), (f * 1.73, 0.6, 0.008), (f * 2.41, 0.45, 0.006), (f * 3.9, 0.25, 0.004)]
    m = D.modal(0.08, modes, rng, jitter=0.04)
    tick = D.hp(D.white(rng, 0.08), 3000.0) * D.env_exp(0.08, 0.0015)
    return (m * 0.7 + tick * 0.6) * amp


def gunshot_dry(rng, p, variant=0):
    L = p["length"]
    blast = D.white(rng, L) * D.env_exp(L, p["blast_tau"] * rng.uniform(0.85, 1.15), attack=0.00015)
    crackle = D.hp(blast, 2500.0) * 0.65
    blast = D.bp(blast, 180.0, p["hi"]) + crackle
    body = D.sine_sweep(L, p["body"] * 3.2, p["body"] * rng.uniform(0.92, 1.08), curve=7.0)
    body *= D.env_exp(L, p["thump_tau"], attack=0.0008)
    body = D.saturate(body * 1.6, 2.0)
    f, q, g = p["pop"]
    pop = D.resonator(D.white(rng, L) * D.env_exp(L, 0.02, 0.0003), f * rng.uniform(0.93, 1.07), q) * 3.0 * g
    sub = D.lp(D.white(rng, L) * D.env_exp(L, p["thump_tau"] * 1.4, 0.001), 140.0) * 1.2
    sig = blast * 0.85 + body * 0.9 + pop + sub
    if p["crack"] > 0:
        sig = D.mix(sig, (_n_wave(rng) * p["crack"], 0.0))
    for (dt, f0, a) in p["mech"]:
        sig = D.mix(sig, (_mech_click(rng, f0 * rng.uniform(0.95, 1.05), a), dt))
    sig = D.saturate(sig, p["drive"])
    return D.pad_to(sig, L)


def gunshot_close(rng, name, variant=0):
    p = WEAPONS[name]
    dry = gunshot_dry(rng, p, variant)
    ir = D.street_ir(rng, rt60=0.35, seconds=0.45)     # tight early reflections only
    wet = D.convolve(dry, ir[:, 0], wet=0.22, dry=1.0)
    out = D.pad_to(wet, p["length"])
    out = D.fade(out, 0.0, 0.08)
    return D.normalize(out, -0.8)


def gunshot_tail(rng, name, variant=0):
    """Distant / environmental layer: low-passed blast through a long street IR + building echoes."""
    p = WEAPONS[name]
    dry = gunshot_dry(rng, p, variant)
    dry = D.lp(dry, 2200.0 if p["crack"] == 0 else 3200.0)
    rt = p["rt"] * 1.8
    ir = D.street_ir(rng, rt60=rt, seconds=rt * 1.4)
    wet = D.convolve(dry, ir, wet=1.0, dry=0.15)
    echoes = []
    for k in range(rng.integers(2, 5)):
        dt = rng.uniform(0.18, 0.95)
        echoes.append((D.lp(dry, 1200.0) * rng.uniform(0.15, 0.4) * math.exp(-dt), dt))
    out = D.mix(wet, *[(D.to_stereo(e, 0.6), dt) for e, dt in echoes])
    out = D.lp(out, 5000.0)
    out = D.fade(out, 0.002, 0.4)
    return D.normalize(out, -3.0)


# ----------------------------------------------------------------------------- handling
def dry_fire(rng, v=0):
    c = _mech_click(rng, rng.uniform(2800, 3400), 1.0)
    c2 = _mech_click(rng, rng.uniform(1800, 2200), 0.4)
    return D.normalize(D.mix(c, (c2, 0.012)), -6.0)


def mag_out(rng, v=0, rifle=False):
    rel = _mech_click(rng, 2400 if not rifle else 1700, 0.8)
    slide = D.bp(D.white(rng, 0.18), 900, 5000) * D.env_adsr(0.18, 0.01, 0.06, 0.4, 0.08) * 0.35
    thunk = D.modal(0.15, [(420 if rifle else 610, 1.0, 0.02), (980, 0.4, 0.012)], rng, 0.05)
    return D.normalize(D.mix(rel, (slide, 0.01), (thunk, 0.12)), -5.0)


def mag_in(rng, v=0, rifle=False):
    slide = D.bp(D.white(rng, 0.12), 1200, 6000) * D.env_adsr(0.12, 0.02, 0.05, 0.5, 0.04) * 0.3
    seat = _mech_click(rng, 1500 if rifle else 2100, 1.0)
    latch = _mech_click(rng, 3600, 0.55)
    body = D.modal(0.2, [(300 if rifle else 450, 0.8, 0.03), (760, 0.4, 0.02)], rng, 0.05)
    return D.normalize(D.mix(slide, (seat, 0.09), (body, 0.09), (latch, 0.11)), -4.0)


def slide_rack(rng, v=0):
    pull = D.bp(D.white(rng, 0.09), 1500, 7000) * D.env_adsr(0.09, 0.005, 0.03, 0.6, 0.03) * 0.5
    back = _mech_click(rng, 2700, 0.9)
    fwd = _mech_click(rng, 2200, 1.0)
    return D.normalize(D.mix(pull, (back, 0.07), (pull * 0.7, 0.13), (fwd, 0.19)), -4.0)


def bolt_action(rng, v=0):
    up = _mech_click(rng, 1900, 0.7)
    back = D.bp(D.white(rng, 0.14), 1100, 6000) * D.env_adsr(0.14, 0.01, 0.05, 0.6, 0.05) * 0.5
    stop = _mech_click(rng, 1500, 1.0)
    fwd = _mech_click(rng, 1700, 0.9)
    lock = _mech_click(rng, 2300, 0.8)
    return D.normalize(D.mix(up, (back, 0.06), (stop, 0.2), (back * 0.8, 0.32), (fwd, 0.45), (lock, 0.55)), -4.0)


def shotgun_pump(rng, v=0):
    slide = D.bp(D.white(rng, 0.12), 700, 4500) * D.env_adsr(0.12, 0.01, 0.04, 0.6, 0.04) * 0.6
    back = D.mix(_mech_click(rng, 1300, 1.0), (D.modal(0.2, [(220, 0.9, 0.04), (510, 0.5, 0.03)], rng), 0.0))
    fwd = D.mix(_mech_click(rng, 1600, 1.0), (D.modal(0.2, [(260, 0.9, 0.04), (640, 0.5, 0.03)], rng), 0.0))
    return D.normalize(D.mix(slide, (back, 0.1), (slide, 0.24), (fwd, 0.33)), -3.0)


def shell_load(rng, v=0):
    push = D.bp(D.white(rng, 0.07), 900, 5000) * D.env_exp(0.07, 0.02) * 0.4
    click = _mech_click(rng, rng.uniform(1900, 2300), 0.8)
    return D.normalize(D.mix(push, (click, 0.05)), -6.0)


def revolver_cylinder(rng, v=0):
    parts = []
    for i in range(6):
        parts.append((_mech_click(rng, 3000 + rng.uniform(-150, 150), 0.35), 0.03 + i * 0.045))
    swing = D.mix(_mech_click(rng, 1400, 1.0), (D.modal(0.2, [(380, 1, 0.03)], rng), 0.0))
    return D.normalize(D.mix(D.silence(0.45), *parts, (swing, 0.33)), -5.0)


def shell_casing(rng, v=0):
    """Brass case dropping on concrete: a few bounces with ringing brass modes."""
    f = rng.uniform(4200, 5600)
    out = D.silence(0.7)
    t = 0.0
    a = 1.0
    for b in range(rng.integers(3, 6)):
        ping = D.modal(0.25, [(f, 1.0, 0.05), (f * 2.32, 0.5, 0.03), (f * 0.61, 0.35, 0.04), (f * 3.7, 0.2, 0.02)], rng, 0.03)
        out = D.mix(out, (ping * a, t))
        t += rng.uniform(0.06, 0.16) * a
        a *= rng.uniform(0.45, 0.65)
    roll = D.granular_tinkle(rng, 0.4, 25, 3500, 7000, 0.002, 0.008) * 0.12
    out = D.mix(out, (roll, t))
    return D.normalize(D.fade(D.pad_to(out, 0.8), 0, 0.1), -8.0)


def equip(rng, v=0):
    cloth = D.bp(D.white(rng, 0.35), 500, 4000) * D.env_adsr(0.35, 0.08, 0.1, 0.5, 0.15) * 0.25
    holster = D.lp(D.white(rng, 0.2), 1800) * D.env_exp(0.2, 0.03) * 0.4
    clack = _mech_click(rng, 2500, 0.7)
    return D.normalize(D.mix(cloth, (holster, 0.12), (clack, 0.22)), -8.0)


# ----------------------------------------------------------------------------- melee
def whoosh(rng, v=0, heavy=False):
    dur = 0.42 if heavy else 0.3
    n = D.white(rng, dur)
    e = np.sin(np.linspace(0, math.pi, D.n_of(dur))) ** (2.2 if not heavy else 1.6)
    centre = rng.uniform(900, 1500) if not heavy else rng.uniform(450, 800)
    sig = np.zeros_like(n)
    blocks = 24
    L = len(n)
    for i in range(blocks):
        s, e2 = i * L // blocks, (i + 1) * L // blocks
        f = centre * (0.6 + 0.9 * math.sin(math.pi * i / blocks))
        sig[s:e2] = D.bp(n, f * 0.6, f * 1.6)[s:e2]
    out = sig * e
    return D.normalize(D.to_stereo(out, 0.3)[:, 0], -6.0)


def punch(rng, v=0):
    thud = D.sine_sweep(0.25, 180, 70, 6) * D.env_exp(0.25, 0.04, 0.001)
    slap = D.bp(D.white(rng, 0.2), 700, 5000) * D.env_exp(0.2, 0.012, 0.0005)
    cloth = D.bp(D.white(rng, 0.15), 300, 2500) * D.env_exp(0.15, 0.03) * 0.4
    return D.normalize(D.saturate(D.mix(thud * 1.1, slap * 0.7, cloth), 1.8), -2.0)


def bat_hit(rng, v=0):
    wood = D.modal(0.5, [(rng.uniform(350, 420), 1.0, 0.05), (rng.uniform(870, 960), 0.6, 0.03),
                         (rng.uniform(1600, 1800), 0.35, 0.02)], rng)
    body = D.sine_sweep(0.3, 160, 60, 5) * D.env_exp(0.3, 0.05)
    crack = D.bp(D.white(rng, 0.1), 1500, 8000) * D.env_exp(0.1, 0.006)
    return D.normalize(D.saturate(D.mix(wood * 0.7, body, crack * 0.8), 2.0), -1.5)


def knife_hit(rng, v=0):
    stab = D.lp(D.white(rng, 0.25), 1500) * D.env_exp(0.25, 0.03, 0.002)
    squelch = D.resonator(D.white(rng, 0.25), rng.uniform(380, 520), 6) * D.env_exp(0.25, 0.05) * 2.5
    ring = D.modal(0.4, [(6200, 0.25, 0.06), (8900, 0.15, 0.04)], rng, 0.05)
    return D.normalize(D.mix(stab, squelch, ring * 0.4), -3.0)


# ----------------------------------------------------------------------------- impacts
def impact(rng, surface, v=0):
    if surface == "Concrete":
        crack = D.hp(D.white(rng, 0.4), 1200) * D.env_exp(0.4, 0.004, 0.0002)
        thud = D.lp(D.white(rng, 0.4), 600) * D.env_exp(0.4, 0.015) * 1.2
        debris = D.crackle(rng, 0.4, 90, 0.0015, 1500, 9000) * np.linspace(1, 0, D.n_of(0.4)) ** 2 * 0.6
        out = crack + thud + debris
    elif surface == "Metal":
        f = rng.uniform(900, 1500)
        ring = D.modal(0.7, [(f, 1.0, 0.18), (f * 1.58, 0.7, 0.12), (f * 2.33, 0.5, 0.09), (f * 3.11, 0.35, 0.06),
                             (f * 4.4, 0.2, 0.04)], rng, 0.02)
        clank = D.hp(D.white(rng, 0.2), 2500) * D.env_exp(0.2, 0.003)
        out = D.mix(ring * 0.6, clank)
    elif surface == "Glass":
        crack = D.hp(D.white(rng, 0.1), 3000) * D.env_exp(0.1, 0.003)
        tink = D.granular_tinkle(rng, 0.9, 70, 2500, 9500, 0.003, 0.02, 4.0)
        out = D.mix(crack, tink * 0.8)
    elif surface == "Wood":
        f = rng.uniform(260, 380)
        knock = D.modal(0.4, [(f, 1.0, 0.03), (f * 2.3, 0.6, 0.02), (f * 3.7, 0.3, 0.012)], rng, 0.05)
        splinter = D.crackle(rng, 0.35, 140, 0.001, 2000, 8000) * np.linspace(1, 0, D.n_of(0.35)) ** 3
        out = D.mix(knock, splinter * 0.7, D.bp(D.white(rng, 0.35), 600, 3000) * D.env_exp(0.35, 0.008))
    elif surface == "Flesh":
        thump = D.sine_sweep(0.35, 140, 55, 5) * D.env_exp(0.35, 0.05, 0.001)
        wet = D.lp(D.white(rng, 0.35), 2200) * D.env_exp(0.35, 0.02)
        sq = D.resonator(D.white(rng, 0.35), rng.uniform(300, 450), 5) * D.env_exp(0.35, 0.06) * 2.0
        out = thump * 1.1 + wet * 0.8 + sq
    elif surface == "Dirt":
        thud = D.lp(D.white(rng, 0.4), 900) * D.env_exp(0.4, 0.02)
        spray = D.crackle(rng, 0.4, 220, 0.001, 1000, 6000) * np.linspace(1, 0, D.n_of(0.4)) ** 2
        out = thud + spray * 0.6
    elif surface == "Water":
        plop = D.sine_sweep(0.3, 900, 250, 5) * D.env_exp(0.3, 0.03)
        spl = D.bp(D.white(rng, 0.5), 800, 7000) * D.env_adsr(0.5, 0.003, 0.08, 0.3, 0.3) * 0.6
        out = D.mix(plop * 0.6, spl)
    else:
        raise ValueError(surface)
    return D.normalize(D.fade(out, 0, 0.05), -2.0)


def ricochet(rng, v=0):
    dur = rng.uniform(0.45, 0.75)
    t = D.t_axis(dur)
    f0, f1 = rng.uniform(3200, 4600), rng.uniform(900, 1500)
    f = f1 + (f0 - f1) * np.exp(-t * rng.uniform(3, 6))
    f *= 1 + 0.02 * np.sin(2 * math.pi * rng.uniform(25, 45) * t)
    tone = np.sin(2 * math.pi * np.cumsum(f) / D.SR) * np.exp(-t / (dur * 0.45))
    zing = D.bp(D.white(rng, dur), 2000, 7000) * np.exp(-t / 0.02) * 0.7
    out = D.mix(impact(rng, "Concrete") * 0.5, (tone * 0.6 + zing, 0.004))
    return D.normalize(D.fade(out, 0, 0.1), -3.0)


def bullet_flyby(rng, v=0):
    dur = 0.35
    t = D.t_axis(dur) - 0.12
    crack = np.zeros_like(t)
    k = D.n_of(0.12)
    crack[k:k + D.n_of(0.0004)] = np.linspace(1, -1, D.n_of(0.0004))
    crack = D.hp(crack, 2000) * 2.0
    whiz = D.bp(D.white(rng, dur), 1500, 6000) * np.exp(-(t ** 2) / 0.0012) * 0.5
    st = D.doppler_pass(crack + whiz, 300.0, 1.2, dur)
    return D.normalize(st, -3.0)


# ----------------------------------------------------------------------------- throwables & explosions
def grenade_pin(rng, v=0):
    pin = D.mix(_mech_click(rng, 3800, 0.8), (D.modal(0.5, [(5200, 0.4, 0.15), (7300, 0.2, 0.1)], rng), 0.0))
    spoon = D.modal(0.35, [(2600, 0.7, 0.06), (3900, 0.4, 0.04)], rng, 0.05)
    return D.normalize(D.mix(pin, (spoon, 0.35)), -5.0)


def grenade_bounce(rng, v=0):
    return D.normalize(D.mix(D.modal(0.3, [(rng.uniform(700, 900), 1, 0.03), (1900, 0.4, 0.02)], rng),
                             (D.lp(D.white(rng, 0.2), 1200) * D.env_exp(0.2, 0.01), 0.0)), -6.0)


def explosion(rng, v=0, size=1.0, debris=True):
    """size 0.6 = grenade, 1.0 = car, 1.3 = gas tank / large."""
    dur = 3.5 + 2.0 * size
    boom = D.sine_sweep(dur, 95 * (1.2 - 0.25 * size), 28, curve=5.0) * D.env_exp(dur, 0.25 * size, 0.002)
    boom = D.saturate(boom * 2.0, 2.5)
    blast = D.brown(rng, dur) * D.env_exp(dur, 0.35 * size, 0.001)
    blast = D.sweep_lp(blast, 7000, 180, curve=0.35)
    crack = D.hp(D.white(rng, 0.2), 1500) * D.env_exp(0.2, 0.012, 0.0002)
    rumble = D.lp(D.brown(rng, dur), 140) * D.env_adsr(dur, 0.05, 0.5, 0.5, dur * 0.7) * 0.7
    sig = D.mix(boom * 1.1, blast * 1.2, crack * 0.9, rumble)
    if debris:
        deb = D.crackle(rng, dur * 0.6, 160, 0.003, 600, 7000) * np.exp(-np.linspace(0, 5, D.n_of(dur * 0.6)))
        tink = D.granular_tinkle(rng, dur * 0.7, 30 * size, 1500, 6000, 0.004, 0.03, 2.5)
        sig = D.mix(sig, (deb * 0.5, 0.15), (tink * 0.25, 0.4))
    ir = D.street_ir(rng, rt60=1.8, seconds=2.4)
    out = D.convolve(sig, ir, wet=0.55, dry=1.0)
    out = D.lp(out, 9000)
    out = D.fade(out, 0.0, 0.8)
    return D.normalize(out, -0.5)


def molotov_break(rng, v=0):
    glass = impact(rng, "Glass")
    whoomp = D.lp(D.brown(rng, 1.8), 900) * D.env_adsr(1.8, 0.08, 0.4, 0.4, 1.0)
    whoomp = D.sweep_lp(whoomp, 400, 2500, 0.6) * 1.2
    return D.normalize(D.mix(glass, (whoomp, 0.05), (D.crackle(rng, 1.5, 60, 0.002, 1500, 7000) * 0.4, 0.3)), -1.5)


def glass_shatter(rng, v=0, big=False):
    dur = 2.2 if big else 1.4
    crack = D.hp(D.white(rng, 0.15), 1500) * D.env_exp(0.15, 0.006)
    body = D.bp(D.white(rng, dur), 2000, 10000) * D.env_exp(dur, 0.12) * 0.5
    tink = D.granular_tinkle(rng, dur, 260 if big else 140, 2200, 11000, 0.003, 0.03, 3.0)
    falls = D.granular_tinkle(rng, dur, 90 if big else 50, 1800, 7000, 0.005, 0.04, 1.4) * 0.5
    out = D.mix(crack, body, tink, (falls, 0.25))
    return D.normalize(D.fade(out, 0, 0.3), -1.5)
