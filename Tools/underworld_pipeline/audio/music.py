"""UI sounds and the procedural score (T-AUD-01).

Music is sequenced from code: synthesized drums (kick, snare, hats, rim), an 808-style bass with
glide, detuned super-saw pads through a resonant low-pass, Karplus-Strong plucks and riser/impact
FX. Key/tempo per cue; loops are rendered bar-exact so they repeat without a seam.
"""
import math

import numpy as np

from . import dsp as D

NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7,
        "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def hz(name, octave):
    return 440.0 * 2 ** ((NOTE[name] + 12 * (octave + 1) - 69) / 12.0)


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


# ----------------------------------------------------------------------------- instruments
def kick(rng, punch=1.0):
    body = D.sine_sweep(0.5, 160 * punch, 45, curve=9.0) * D.env_exp(0.5, 0.16, 0.0005)
    click = D.hp(D.white(rng, 0.01), 2500) * D.env_exp(0.01, 0.0015) * 0.5
    return D.saturate(D.mix(body, click) * 1.3, 1.8)


def snare(rng):
    tone = D.modal(0.3, [(190, 0.7, 0.05), (330, 0.4, 0.03)], rng)
    noise = D.bp(D.white(rng, 0.3), 1200, 9000) * D.env_exp(0.3, 0.07, 0.0005)
    return D.saturate((tone + noise * 1.1) * 0.9, 1.5)


def clap(rng):
    out = D.silence(0.3)
    for i, dt in enumerate((0.0, 0.009, 0.018, 0.028)):
        b = D.bp(D.white(rng, 0.25), 900, 6000) * D.env_exp(0.25, 0.01 if i < 3 else 0.08)
        out = D.mix(out, (b, dt))
    return out * 0.8


def hat(rng, open_=False):
    dur = 0.35 if open_ else 0.06
    metal = sum(D.osc(dur, f, "square") for f in (2950, 3540, 4720, 5920, 7310, 8460)) / 6
    n = D.hp(metal * 0.6 + D.white(rng, dur) * 0.6, 7000) * D.env_exp(dur, 0.12 if open_ else 0.015, 0.0003)
    return n * 0.5


def rim(rng):
    return D.mix(D.modal(0.1, [(1650, 0.6, 0.01), (2400, 0.3, 0.008)], rng), D.hp(D.white(rng, 0.02), 3000) * D.env_exp(0.02, 0.002) * 0.4)


def sub808(freq, dur, glide_from=None):
    tt = D.t_axis(dur)
    f = np.full_like(tt, freq)
    if glide_from:
        f = freq + (glide_from - freq) * np.exp(-tt / 0.05)
    s = np.sin(2 * math.pi * np.cumsum(f) / D.SR)
    env = D.env_adsr(dur, 0.003, 0.15, 0.7, min(0.12, dur * 0.4))
    return D.saturate(s * env * 1.4, 2.0)


def pad(rng, freqs, dur, cutoff=1200.0, attack=0.8):
    out = np.zeros(D.n_of(dur))
    for f in freqs:
        out += D.supersaw(dur, f, 7, 0.011, rng)
    out = D.lp(out / len(freqs), cutoff, order=4)
    return out * D.env_adsr(dur, attack, 0.5, 0.85, min(1.2, dur * 0.3))


def pluck(rng, freq, dur, bright=0.5):
    """Karplus-Strong string."""
    n = D.n_of(dur)
    p = max(2, int(D.SR / freq))
    buf = rng.uniform(-1, 1, p)
    out = np.zeros(n)
    damp = 0.4 + 0.1 * bright
    for i in range(n):
        out[i] = buf[i % p]
        nxt = (i + 1) % p
        buf[i % p] = damp * (buf[i % p] + buf[nxt]) * 0.996 + (1 - 2 * damp) * buf[i % p] * 0.0
    return D.lp(out, 2000 + 5000 * bright) * D.env_exp(dur, dur * 0.5, 0.001)


def stab(rng, freqs, dur=0.25):
    out = sum(D.osc(dur, f, "saw") + 0.5 * D.osc(dur, f * 1.004, "saw") for f in freqs) / len(freqs)
    out = D.sweep_lp(out, 4000, 600, 0.5)
    return out * D.env_adsr(dur, 0.004, 0.1, 0.4, 0.08)


def riser(rng, dur):
    n = D.white(rng, dur)
    out = D.sweep_lp(n, 300, 9000, 1.6) * np.linspace(0, 1, D.n_of(dur)) ** 2
    return out * 0.4


def impact_hit(rng, dur=3.0):
    boom = D.sine_sweep(dur, 120, 35, 4) * D.env_exp(dur, 0.6, 0.002)
    noise = D.sweep_lp(D.brown(rng, dur) * D.env_exp(dur, 0.4, 0.002), 5000, 200, 0.4)
    return D.saturate(boom * 1.2 + noise * 0.8, 2.0)


# ----------------------------------------------------------------------------- sequencer
class Track:
    def __init__(self, bpm, bars, beats_per_bar=4):
        self.bpm = bpm
        self.beat = 60.0 / bpm
        self.bars = bars
        self.length = bars * beats_per_bar * self.beat
        self.tail = 4.0
        self.buf = np.zeros((D.n_of(self.length + self.tail), 2))

    def place(self, sig, beat_pos, gain=1.0, pan=0.0, width=0.0):
        st = D.to_stereo(sig, width, pan=pan) if sig.ndim == 1 else sig
        s = D.n_of(beat_pos * self.beat)
        m = min(len(st), len(self.buf) - s)
        if m > 0:
            self.buf[s:s + m] += st[:m] * gain

    def render_loop(self):
        """Fold the tail (reverb/decay past the loop end) back onto the head -> bar-exact seamless loop."""
        L = D.n_of(self.length)
        out = self.buf[:L].copy()
        tail = self.buf[L:]
        out[:len(tail)] += tail
        return out


def _bus_reverb(rng, x, rt=2.2, wet=0.35):
    ir = D.make_ir(rt * 1.2, rt, rng, early=[(0.013, 0.3), (0.021, 0.25), (0.034, 0.2)], damping=6000, predelay=0.02)
    y = D.convolve(x, ir, wet=wet)
    return y[:len(x)]


def cue_tension(rng):
    """M01 tension / stealth loop: D minor, 92 BPM, 16 bars. Pulse bass, dark pad, ticking percussion."""
    T = Track(92, 16)
    prog = [("D", ["D", "F", "A"]), ("Bb", ["Bb", "D", "F"]), ("G", ["G", "Bb", "D"]), ("A", ["A", "C#", "E"])]
    pads = np.zeros_like(T.buf)
    for bar in range(16):
        root, chord = prog[(bar // 2) % 4]
        if bar % 2 == 0:
            fr = [hz(n, 3 if n in ("A", "Bb", "G") else 4) for n in chord]
            p = pad(rng, fr, T.beat * 8, cutoff=700 + 300 * math.sin(bar / 16 * math.pi), attack=1.4)
            s = D.n_of(bar * 4 * T.beat)
            st = D.to_stereo(p, 0.9)
            m = min(len(st), len(pads) - s)
            pads[s:s + m] += st[:m] * 0.32
        for e in range(8):  # 8th-note pulse bass with sidechain feel
            f = hz(root, 1)
            b = sub808(f, T.beat * 0.45) * (1.0 if e % 2 == 0 else 0.6)
            T.place(D.lp(b, 400), bar * 4 + e * 0.5, 0.5)
        T.place(kick(rng, 0.8), bar * 4, 0.55)
        if bar % 2 == 1:
            T.place(kick(rng, 0.8), bar * 4 + 2.5, 0.35)
        for s16 in range(16):
            if rng.random() < 0.55:
                T.place(hat(rng), bar * 4 + s16 * 0.25, 0.12 + 0.08 * (s16 % 4 == 2), pan=0.3)
        if bar >= 4:
            T.place(rim(rng), bar * 4 + 3.0, 0.25, pan=-0.3)
        if bar >= 8 and bar % 4 == 3:
            T.place(riser(rng, T.beat * 4), bar * 4, 0.25, width=0.9)
    # sparse pluck motif
    motif = [("D", 5), ("F", 5), ("A", 4), ("E", 5)]
    for bar in range(4, 16, 2):
        for i, (n, o) in enumerate(motif):
            T.place(pluck(rng, hz(n, o), 1.2, 0.4), bar * 4 + i * 0.75, 0.18, pan=(-0.4 + 0.25 * i))
    T.buf = T.buf + _bus_reverb(rng, pads, 2.8, 0.45)
    T.buf = _bus_reverb(rng, T.buf, 1.4, 0.12)
    return D.normalize_rms(T.render_loop(), -18.0, -1.0)


def cue_combat(rng):
    """Shoot-out loop: E minor, 104 BPM, 16 bars. Driving drums, 808 line, staccato stabs, risers."""
    T = Track(104, 16)
    prog = [["E", "G", "B"], ["C", "E", "G"], ["D", "F#", "A"], ["B", "D#", "F#"]]
    roots = ["E", "C", "D", "B"]
    bass_pat = [0, 0.75, 1.5, 2.0, 2.75, 3.5]
    for bar in range(16):
        ci = (bar // 2) % 4
        for b in (0, 1.5, 2.5):
            T.place(kick(rng, 1.0), bar * 4 + b, 0.7)
        T.place(snare(rng), bar * 4 + 1, 0.5)
        T.place(snare(rng), bar * 4 + 3, 0.5)
        T.place(clap(rng), bar * 4 + 3, 0.25, width=0.5)
        for s8 in range(8):
            T.place(hat(rng, open_=(s8 == 7)), bar * 4 + s8 * 0.5, 0.18 if s8 % 2 else 0.25, pan=0.25)
        for i, bpos in enumerate(bass_pat):
            f = hz(roots[ci], 1) * (2 if i == 4 else 1)
            T.place(sub808(f, T.beat * 0.6, glide_from=f * 1.5 if i == 0 else None), bar * 4 + bpos, 0.45)
        fr = [hz(n, 4) for n in prog[ci]]
        for spos in (0.5, 2.0, 3.25):
            T.place(stab(rng, fr), bar * 4 + spos, 0.22, width=0.8)
        if bar % 4 == 3:
            T.place(riser(rng, T.beat * 4), bar * 4, 0.3, width=1.0)
            T.place(snare(rng), bar * 4 + 3.5, 0.4)
            T.place(snare(rng), bar * 4 + 3.75, 0.45)
        if bar % 8 == 0:
            T.place(impact_hit(rng, 2.5), bar * 4, 0.4, width=0.8)
    pads_ = np.zeros_like(T.buf)
    for bar in range(0, 16, 2):
        fr = [hz(n, 3) for n in prog[(bar // 2) % 4]]
        p = D.to_stereo(pad(rng, fr, T.beat * 8, 900, 0.3), 0.9)
        s = D.n_of(bar * 4 * T.beat)
        m = min(len(p), len(pads_) - s)
        pads_[s:s + m] += p[:m] * 0.18
    T.buf = T.buf + _bus_reverb(rng, pads_, 2.0, 0.4)
    T.buf = _bus_reverb(rng, T.buf, 1.1, 0.1)
    return D.normalize_rms(T.render_loop(), -16.0, -1.0)


def cue_menu(rng):
    """Main theme bed: A minor, 80 BPM, 8 bars, wide pads + pluck arpeggio + soft sub."""
    T = Track(80, 8)
    prog = [["A", "C", "E"], ["F", "A", "C"], ["C", "E", "G"], ["G", "B", "D"]]
    pads_ = np.zeros_like(T.buf)
    for bar in range(8):
        ci = bar % 4
        fr = [hz(n, 3) for n in prog[ci]]
        p = D.to_stereo(pad(rng, fr, T.beat * 4.5, 1500, 0.9), 1.0)
        s = D.n_of(bar * 4 * T.beat)
        m = min(len(p), len(pads_) - s)
        pads_[s:s + m] += p[:m] * 0.3
        T.place(D.lp(sub808(hz(prog[ci][0], 1), T.beat * 3.5), 300), bar * 4, 0.35)
        arp = [prog[ci][0], prog[ci][1], prog[ci][2], prog[ci][1]] * 2
        for i, n in enumerate(arp):
            T.place(pluck(rng, hz(n, 5), 1.0, 0.6), bar * 4 + i * 0.5, 0.12, pan=math.sin(i) * 0.5)
        if bar >= 4:
            T.place(kick(rng, 0.7), bar * 4, 0.35)
            T.place(snare(rng), bar * 4 + 2, 0.2)
    T.buf = T.buf + _bus_reverb(rng, pads_, 3.2, 0.5)
    T.buf = _bus_reverb(rng, T.buf, 2.0, 0.2)
    return D.normalize_rms(T.render_loop(), -19.0, -1.0)


def stinger_passed(rng):
    dur = 5.0
    fr = [hz("D", 3), hz("F#", 3), hz("A", 3), hz("D", 4), hz("A", 4)]
    brass = sum(D.supersaw(dur, f, 5, 0.006, rng) for f in fr) / len(fr)
    brass = D.sweep_lp(brass, 600, 5000, 0.4) * D.env_adsr(dur, 0.05, 0.6, 0.6, 2.5)
    hitp = impact_hit(rng, 4.0) * 0.6
    cym = D.hp(D.white(rng, dur), 5000) * D.env_exp(dur, 1.2, 0.002) * 0.25
    out = D.mix(D.to_stereo(brass, 0.9), D.to_stereo(hitp, 0.4), D.to_stereo(cym, 1.0))
    out = _bus_reverb(rng, D.pad_to(out, dur + 1.0), 2.5, 0.35)
    return D.normalize(D.fade(out, 0.002, 1.0), -1.0)


def stinger_failed(rng):
    dur = 5.0
    drone = sum(D.supersaw(dur, f, 5, 0.01, rng) for f in (hz("C", 2), hz("Gb", 2), hz("C", 3))) / 3
    tt = D.t_axis(dur)
    drone = D.lp(drone, 900) * D.env_adsr(dur, 0.02, 0.4, 0.7, 3.0)
    bend = np.interp(np.arange(len(drone)) * (1 - 0.08 * tt / dur), np.arange(len(drone)), drone)
    hitp = impact_hit(rng, 4.5)
    out = D.mix(D.to_stereo(bend, 0.9), D.to_stereo(hitp, 0.4))
    out = _bus_reverb(rng, D.pad_to(out, dur + 1.0), 3.0, 0.4)
    return D.normalize(D.fade(out, 0.002, 1.2), -1.0)


# ----------------------------------------------------------------------------- UI
def ui_click(rng, v=0):
    c = D.mix(D.modal(0.08, [(2400, 0.7, 0.008), (4100, 0.3, 0.004)], rng), D.hp(D.white(rng, 0.02), 4000) * D.env_exp(0.02, 0.001) * 0.3)
    return D.normalize(D.to_stereo(c, 0.2), -9.0)


def ui_hover(rng, v=0):
    c = D.osc(0.06, 1800, "sine") * D.env_exp(0.06, 0.012, 0.002)
    return D.normalize(D.to_stereo(c, 0.2), -16.0)


def ui_back(rng, v=0):
    c = D.sine_sweep(0.12, 1200, 600, 3) * D.env_exp(0.12, 0.03, 0.002)
    return D.normalize(D.to_stereo(c, 0.2), -11.0)


def _bell(rng, f, dur, idx=2.0):
    tt = D.t_axis(dur)
    mod = np.sin(2 * math.pi * f * 3.5 * tt) * idx * np.exp(-tt / (dur * 0.2))
    return np.sin(2 * math.pi * f * tt + mod) * np.exp(-tt / (dur * 0.3))


def ui_objective_new(rng, v=0):
    out = D.mix(_bell(rng, hz("A", 5), 1.2), (_bell(rng, hz("E", 6), 1.2) * 0.8, 0.09))
    out = D.to_stereo(out, 0.6)
    return D.normalize(_bus_reverb(rng, D.pad_to(out, 1.8), 1.2, 0.25), -6.0)


def ui_objective_complete(rng, v=0):
    out = D.mix(_bell(rng, hz("D", 5), 1.5), (_bell(rng, hz("F#", 5), 1.5), 0.07), (_bell(rng, hz("A", 5), 1.5), 0.14),
                (_bell(rng, hz("D", 6), 1.8) * 0.9, 0.21))
    sub = D.lp(D.sine_sweep(0.6, 200, 70, 4) * D.env_exp(0.6, 0.15), 300) * 0.5
    out = D.mix(D.to_stereo(out, 0.6), D.to_stereo(sub, 0))
    return D.normalize(_bus_reverb(rng, D.pad_to(out, 2.4), 1.4, 0.25), -4.0)


def ui_checkpoint(rng, v=0):
    out = D.mix(_bell(rng, hz("G", 5), 1.0, 1.0), (_bell(rng, hz("D", 6), 1.0, 1.0), 0.12))
    return D.normalize(D.to_stereo(D.pad_to(out, 1.3), 0.5), -8.0)


def ui_cash(rng, v=0):
    coins = D.granular_tinkle(rng, 0.7, 40, 3000, 7500, 0.01, 0.05, 5.0)
    reg = D.mix(_bell(rng, hz("E", 6), 0.8, 0.6), (_bell(rng, hz("B", 6), 0.9, 0.6) * 0.7, 0.08))
    out = D.mix(coins * 0.5, (reg * 0.6, 0.05))
    return D.normalize(D.to_stereo(out, 0.6), -6.0)


def ui_hitmarker(rng, v=0):
    c = D.mix(D.hp(D.white(rng, 0.05), 2500) * D.env_exp(0.05, 0.006), D.osc(0.05, 3200) * D.env_exp(0.05, 0.01) * 0.4)
    return D.normalize(D.to_stereo(c, 0.1), -10.0)


def ui_killmarker(rng, v=0):
    c = D.mix(ui_hitmarker(rng)[:, 0], (D.sine_sweep(0.25, 900, 300, 4) * D.env_exp(0.25, 0.06) * 0.6, 0.02))
    return D.normalize(D.to_stereo(c, 0.2), -8.0)


def ui_phone_ring(rng, seconds=3.0):
    """Original two-tone handset ringtone (loop)."""
    out = D.silence(seconds)
    for k in range(int(seconds / 1.5)):
        for i in range(10):
            f = 1300 if i % 2 == 0 else 1650
            b = D.osc(0.045, f) * D.env_adsr(0.045, 0.003, 0.01, 0.8, 0.01)
            out = D.mix(out, (b, k * 1.5 + i * 0.05))
    out = D.pad_to(out, seconds)
    out = D.bp(out, 400, 5000)
    return D.normalize(D.to_stereo(out, 0.0), -8.0)


def ui_phone_notify(rng, v=0):
    out = D.mix(_bell(rng, 1568, 0.4, 0.8), (_bell(rng, 2093, 0.5, 0.8), 0.1))
    return D.normalize(D.to_stereo(D.pad_to(out, 0.7), 0.2), -8.0)


def ui_wanted(rng, v=0):
    out = D.silence(0.9)
    for i, f in enumerate((660, 880, 660, 880)):
        out = D.mix(out, (D.osc(0.12, f, "square") * D.env_adsr(0.12, 0.005, 0.03, 0.6, 0.04) * 0.3, i * 0.16))
    return D.normalize(D.to_stereo(D.lp(out, 3000), 0.3), -9.0)
