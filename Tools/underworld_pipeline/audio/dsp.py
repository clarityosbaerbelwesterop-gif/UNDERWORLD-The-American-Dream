"""DSP building blocks for the procedural audio library (T-AUD-01).

Conventions: float64 numpy arrays in [-1, 1], mono = shape (n,), stereo = shape (n, 2), SR = 48 kHz.
All randomness goes through an explicit numpy Generator so every render is reproducible.
"""
import math

import numpy as np
from scipy import signal as sps

SR = 48000


# ----------------------------------------------------------------------------- basics
def secs(n_samples):
    return n_samples / SR


def n_of(seconds):
    return max(1, int(round(seconds * SR)))


def t_axis(seconds):
    return np.arange(n_of(seconds)) / SR


def silence(seconds, stereo=False):
    n = n_of(seconds)
    return np.zeros((n, 2)) if stereo else np.zeros(n)


def db(x):
    return 10.0 ** (x / 20.0)


def white(rng, seconds):
    return rng.standard_normal(n_of(seconds))


def pink(rng, seconds):
    """Voss-McCartney-free pink noise via 1/f spectral shaping."""
    n = n_of(seconds)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1.0 / SR)
    f[0] = f[1] if n > 1 else 1.0
    spec /= np.sqrt(f)
    out = np.fft.irfft(spec, n)
    return out / (np.std(out) + 1e-12)


def brown(rng, seconds):
    n = n_of(seconds)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1.0 / SR)
    f[0] = f[1] if n > 1 else 1.0
    spec /= f
    out = np.fft.irfft(spec, n)
    out = hp(out, 18.0)
    return out / (np.std(out) + 1e-12)


# ----------------------------------------------------------------------------- filters
def _sos(kind, freq, order=2):
    nyq = SR / 2.0
    if isinstance(freq, (tuple, list)):
        lo, hi = freq
        lo = min(max(lo, 5.0), nyq * 0.95)
        hi = min(max(hi, lo * 1.05), nyq * 0.98)
        return sps.butter(order, [lo / nyq, hi / nyq], btype=kind, output="sos")
    freq = min(max(freq, 5.0), nyq * 0.98)
    return sps.butter(order, freq / nyq, btype=kind, output="sos")


def _apply(sos, x):
    if x.ndim == 2:
        return np.stack([sps.sosfilt(sos, x[:, c]) for c in range(x.shape[1])], axis=1)
    return sps.sosfilt(sos, x)


def lp(x, f, order=2):
    return _apply(_sos("lowpass", f, order), x)


def hp(x, f, order=2):
    return _apply(_sos("highpass", f, order), x)


def bp(x, lo, hi, order=2):
    return _apply(_sos("bandpass", (lo, hi), order), x)


def peak_eq(x, f0, gain_db, q=1.0):
    """RBJ peaking EQ."""
    a = db(gain_db / 2.0)
    w0 = 2 * math.pi * min(f0, SR * 0.45) / SR
    alpha = math.sin(w0) / (2 * q)
    b = np.array([1 + alpha * a, -2 * math.cos(w0), 1 - alpha * a])
    aa = np.array([1 + alpha / a, -2 * math.cos(w0), 1 - alpha / a])
    if x.ndim == 2:
        return np.stack([sps.lfilter(b / aa[0], aa / aa[0], x[:, c]) for c in range(x.shape[1])], axis=1)
    return sps.lfilter(b / aa[0], aa / aa[0], x)


def resonator(x, f0, q=20.0):
    """2-pole resonant band (constant 0 dB peak gain)."""
    w0 = 2 * math.pi * min(f0, SR * 0.45) / SR
    alpha = math.sin(w0) / (2 * q)
    b = np.array([alpha, 0.0, -alpha])
    a = np.array([1 + alpha, -2 * math.cos(w0), 1 - alpha])
    return sps.lfilter(b / a[0], a / a[0], x)


def sweep_lp(x, f_start, f_end, curve=1.0, block=256):
    """Time-varying one-pole->biquad low-pass (block-wise coefficient update, state carried over)."""
    n = len(x)
    out = np.zeros_like(x)
    zi = np.zeros((1, 2))
    for i in range(0, n, block):
        u = (i / max(n - 1, 1)) ** curve
        f = f_start * (f_end / f_start) ** u
        sos = _sos("lowpass", f, 2)
        seg = x[i:i + block]
        y, zi = sps.sosfilt(sos, seg, zi=zi)
        out[i:i + block] = y
    return out


# ----------------------------------------------------------------------------- envelopes
def env_exp(seconds, tau, attack=0.0005):
    t = t_axis(seconds)
    e = np.exp(-t / max(tau, 1e-5))
    if attack > 0:
        e *= np.clip(t / attack, 0.0, 1.0)
    return e


def env_adsr(seconds, a, d, s, r):
    n = n_of(seconds)
    t = np.arange(n) / SR
    e = np.zeros(n)
    rel_start = max(seconds - r, a + d)
    e = np.where(t < a, t / max(a, 1e-6), e)
    m = (t >= a) & (t < a + d)
    e[m] = 1.0 - (1.0 - s) * (t[m] - a) / max(d, 1e-6)
    m = (t >= a + d) & (t < rel_start)
    e[m] = s
    m = t >= rel_start
    e[m] = s * np.clip(1.0 - (t[m] - rel_start) / max(r, 1e-6), 0.0, 1.0)
    return e


def fade(x, fin=0.002, fout=0.01):
    x = x.copy()
    ni, no = n_of(fin), n_of(fout)
    ni, no = min(ni, len(x)), min(no, len(x))
    ramp_i = np.linspace(0, 1, ni) ** 2
    ramp_o = np.linspace(1, 0, no) ** 2
    if x.ndim == 2:
        x[:ni] *= ramp_i[:, None]
        x[len(x) - no:] *= ramp_o[:, None]
    else:
        x[:ni] *= ramp_i
        x[len(x) - no:] *= ramp_o
    return x


# ----------------------------------------------------------------------------- oscillators
def sine_sweep(seconds, f0, f1, curve=3.0, phase=0.0):
    """Exponential-ish pitch glide f0 -> f1 (curve = speed of the drop)."""
    t = t_axis(seconds)
    f = f1 + (f0 - f1) * np.exp(-t * curve / max(seconds, 1e-4) * 4.0)
    ph = phase + 2 * math.pi * np.cumsum(f) / SR
    return np.sin(ph)


def osc(seconds, freq, kind="sine", phase=0.0, pw=0.5):
    t = t_axis(seconds)
    if np.isscalar(freq):
        ph = phase + 2 * math.pi * freq * t
    else:
        ph = phase + 2 * math.pi * np.cumsum(freq) / SR
    if kind == "sine":
        return np.sin(ph)
    frac = (ph / (2 * math.pi)) % 1.0
    if kind == "saw":
        return 2.0 * frac - 1.0
    if kind == "square":
        return np.where(frac < pw, 1.0, -1.0)
    if kind == "tri":
        return 4.0 * np.abs(frac - 0.5) - 1.0
    raise ValueError(kind)


def supersaw(seconds, freq, voices=5, detune=0.012, rng=None):
    rng = rng or np.random.default_rng(1)
    out = np.zeros(n_of(seconds))
    for i in range(voices):
        d = 1.0 + detune * (i - (voices - 1) / 2) / max((voices - 1) / 2, 1)
        out += osc(seconds, freq * d, "saw", phase=rng.uniform(0, 2 * math.pi))
    return out / voices


def modal(seconds, modes, rng=None, jitter=0.0):
    """Sum of exponentially decaying sinusoids: modes = [(freq, amp, decay_tau), ...]."""
    t = t_axis(seconds)
    out = np.zeros_like(t)
    for f, a, tau in modes:
        if rng is not None and jitter:
            f *= 1.0 + rng.uniform(-jitter, jitter)
        out += a * np.sin(2 * math.pi * f * t + (rng.uniform(0, 6.28) if rng is not None else 0.0)) * np.exp(-t / tau)
    return out


# ----------------------------------------------------------------------------- shaping
def saturate(x, drive=2.0):
    return np.tanh(x * drive) / np.tanh(drive)


def normalize(x, peak_db=-1.0):
    p = np.max(np.abs(x)) + 1e-12
    return x * (db(peak_db) / p)


def rms_db(x):
    return 20 * math.log10(math.sqrt(float(np.mean(np.square(x)))) + 1e-12)


def peak_dbfs(x):
    return 20 * math.log10(float(np.max(np.abs(x))) + 1e-12)


def normalize_rms(x, target_db=-20.0, peak_ceiling_db=-1.0):
    g = db(target_db - rms_db(x))
    y = x * g
    p = np.max(np.abs(y))
    ceil = db(peak_ceiling_db)
    if p > ceil:
        y = soft_limit(y, ceil)
    return y


def soft_limit(x, ceiling=0.89):
    return np.tanh(x / ceiling) * ceiling


def mix(*parts):
    """Mix arrays of different lengths (pad to longest). Each part = array or (array, offset_s, gain)."""
    items = []
    for p in parts:
        if isinstance(p, tuple):
            arr, off, g = (p + (1.0,))[:3] if len(p) == 2 else p
        else:
            arr, off, g = p, 0.0, 1.0
        items.append((arr, n_of(off) if off > 0 else 0, g))
    stereo = any(a.ndim == 2 for a, _, _ in items)
    n = max(o + len(a) for a, o, _ in items)
    out = np.zeros((n, 2)) if stereo else np.zeros(n)
    for a, o, g in items:
        if stereo and a.ndim == 1:
            a = np.stack([a, a], axis=1)
        out[o:o + len(a)] += a * g
    return out


def pad_to(x, seconds):
    n = n_of(seconds)
    if len(x) >= n:
        return x[:n]
    shape = (n - len(x),) + x.shape[1:]
    return np.concatenate([x, np.zeros(shape)])


def to_stereo(x, width=0.0, rng=None, pan=0.0):
    """Mono -> stereo. width>0 decorrelates with a short Haas/all-pass difference signal."""
    if x.ndim == 2:
        return x
    l = x * math.cos((pan + 1) * math.pi / 4)
    r = x * math.sin((pan + 1) * math.pi / 4)
    if width > 0:
        d = n_of(0.00045 + 0.0006 * width)
        side = np.concatenate([np.zeros(d), x[:-d]]) - x
        side = hp(side, 300.0)
        l = l + side * width * 0.35
        r = r - side * width * 0.35
    return np.stack([l, r], axis=1) * math.sqrt(2) * 0.5 * 1.41


def doppler_pass(x, speed_mps, closest_m, dur, rng=None):
    """Simulates a source passing the listener: pitch shift + distance gain + air absorption."""
    n = len(x)
    t = np.arange(n) / SR - dur / 2
    pos = speed_mps * t
    dist = np.sqrt(pos ** 2 + closest_m ** 2)
    vr = speed_mps * pos / dist            # radial velocity (+ = receding)
    ratio = 343.0 / (343.0 + vr)
    idx = np.cumsum(ratio)
    idx = idx - idx[n // 2] + n // 2
    idx = np.clip(idx, 0, n - 1)
    y = np.interp(idx, np.arange(n), x)
    g = closest_m / dist
    y = y * g
    # air absorption: darker when far
    far = lp(y, 2500.0)
    w = np.clip((dist - closest_m) / (closest_m * 6 + 1e-3), 0, 1)
    pan = np.clip(pos / (closest_m * 3), -1, 1)
    yy = y * (1 - w) + far * w
    l = yy * np.cos((pan + 1) * np.pi / 4)
    r = yy * np.sin((pan + 1) * np.pi / 4)
    return np.stack([l, r], axis=1) * 1.41


# ----------------------------------------------------------------------------- space
def make_ir(seconds, rt60, rng, early=(), damping=4000.0, predelay=0.004, stereo=True, density=1.0):
    """Synthetic impulse response: discrete early reflections + exponentially decaying diffuse tail
    that darkens over time (frequency-dependent decay)."""
    n = n_of(seconds)
    t = np.arange(n) / SR
    chans = []
    for c in range(2 if stereo else 1):
        tail = rng.standard_normal(n) * density
        decay = np.exp(-6.91 * t / max(rt60, 1e-3))
        bright = tail * decay
        dark = lp(tail, damping * 0.35) * decay
        mixw = np.clip(t / max(rt60 * 0.6, 1e-3), 0, 1)
        ir = bright * (1 - mixw) + dark * mixw * 1.6
        ir = lp(ir, damping)
        pd = n_of(predelay)
        ir = np.concatenate([np.zeros(pd), ir])[:n]
        ir[:pd + n_of(0.002)] *= np.linspace(0, 1, min(n, pd + n_of(0.002)))
        for (dt, g) in early:
            k = n_of(dt * (1.0 + (0.03 * (c - 0.5) if stereo else 0)))
            if k < n:
                ir[k] += g * (1 if rng.random() > 0.3 else -1)
        ir[0] = 0.0
        chans.append(ir / (np.sqrt(np.sum(ir ** 2)) + 1e-12))
    return np.stack(chans, axis=1) if stereo else chans[0]


def convolve(x, ir, wet=0.3, dry=1.0):
    """Mono/stereo x with mono/stereo IR (FFT convolution). Output length = len(x) + len(ir) - 1."""
    if x.ndim == 1 and ir.ndim == 2:
        wetsig = np.stack([sps.fftconvolve(x, ir[:, c]) for c in range(2)], axis=1)
        drysig = np.stack([x, x], axis=1)
    elif x.ndim == 2 and ir.ndim == 2:
        wetsig = np.stack([sps.fftconvolve(x[:, c], ir[:, c]) for c in range(2)], axis=1)
        drysig = x
    elif x.ndim == 2:
        wetsig = np.stack([sps.fftconvolve(x[:, c], ir) for c in range(2)], axis=1)
        drysig = x
    else:
        wetsig = sps.fftconvolve(x, ir)
        drysig = x
    out = wetsig * wet
    out[:len(drysig)] += drysig * dry
    return out


def street_ir(rng, rt60=1.1, seconds=None):
    """Urban street: strong facade slap-backs (15-60 ms) and a long, dark flutter tail."""
    early = [(0.011, 0.55), (0.019, 0.42), (0.031, 0.35), (0.047, 0.30), (0.063, 0.22),
             (0.089, 0.16), (0.120, 0.12), (0.170, 0.08)]
    return make_ir(seconds or rt60 * 1.3, rt60, rng, early=early, damping=5200.0, predelay=0.006)


def alley_ir(rng):
    early = [(0.006, 0.6), (0.009, 0.55), (0.013, 0.45), (0.018, 0.4), (0.024, 0.3), (0.033, 0.25)]
    return make_ir(1.0, 0.75, rng, early=early, damping=6000.0, predelay=0.002)


def room_ir(rng, rt60=0.5):
    early = [(0.004, 0.5), (0.007, 0.45), (0.011, 0.35), (0.016, 0.3)]
    return make_ir(rt60 * 1.4, rt60, rng, early=early, damping=7000.0, predelay=0.001)


# ----------------------------------------------------------------------------- loops
def make_loop(x, xfade_s=1.0):
    """Seamless loop: equal-power crossfade of the last `xfade_s` into the head; returns len - xfade."""
    n = len(x)
    k = n_of(xfade_s)
    if k * 2 >= n:
        k = n // 4
    head = x[:k]
    tail = x[n - k:]
    w = np.linspace(0, 1, k)
    fi, fo = np.sin(w * math.pi / 2), np.cos(w * math.pi / 2)
    if x.ndim == 2:
        fi, fo = fi[:, None], fo[:, None]
    body = x[:n - k].copy()
    body[:k] = head * fi + tail * fo
    return body


def crackle(rng, seconds, rate, tau=0.002, lo=800.0, hi=9000.0, amp_sigma=0.8):
    """Poisson clicks with lognormal amplitude, each a short damped noise burst (fire, debris, gravel)."""
    n = n_of(seconds)
    out = np.zeros(n)
    count = rng.poisson(rate * seconds)
    pos = rng.integers(0, n, size=count)
    amps = rng.lognormal(0.0, amp_sigma, size=count)
    kern_n = n_of(tau * 6)
    kern = rng.standard_normal(kern_n) * np.exp(-np.arange(kern_n) / (tau * SR))
    imp = np.zeros(n)
    np.add.at(imp, pos, amps)
    out = sps.fftconvolve(imp, kern)[:n]
    return bp(out, lo, hi)


def granular_tinkle(rng, seconds, rate, f_lo, f_hi, tau_lo=0.004, tau_hi=0.03, decay_rate=3.0):
    """Many tiny resonant pings (glass shards, coins, brass) whose density decays over time."""
    n = n_of(seconds)
    out = np.zeros(n)
    count = int(rate * seconds)
    for _ in range(count):
        tt = rng.exponential(seconds / decay_rate)
        if tt >= seconds:
            continue
        f = math.exp(rng.uniform(math.log(f_lo), math.log(f_hi)))
        tau = rng.uniform(tau_lo, tau_hi)
        m = n_of(min(tau * 6, seconds - tt))
        k = np.arange(m) / SR
        ping = np.sin(2 * math.pi * f * k + rng.uniform(0, 6.28)) * np.exp(-k / tau)
        ping += 0.4 * np.sin(2 * math.pi * f * 2.76 * k) * np.exp(-k / (tau * 0.5))
        s = n_of(tt)
        a = rng.lognormal(-0.3, 0.6) * math.exp(-tt * 1.5)
        out[s:s + m] += ping[:n - s] * a
    return out
