"""Score, sound design and final mix. Everything is synthesised here: no samples.

Reads ../timeline.json (scene times, VO cues, SFX cues) and audio/vo/*.wav,
writes audio/build/mix.wav (48 kHz stereo, -14 LUFS after ffmpeg loudnorm).

The music is a 120 BPM groove in F major so every cut in the picture lands on
a beat: bars are 2.0 s, beats 0.5 s. The sound design stays close to real life:
cheese sizzle, a receipt printing, phone taps; no cartoon slams. Sections follow the edit:
  0.0-1.6   bright intro, tape-stopped on "But hate the bill?"
  1.6-6.0   D minor tension (heartbeat, ticking clock)
  6.0-8.0   riser into a gap, logo slam on the 8.0 downbeat
  8.0-32.0  main groove  F C Dm Bb  (arpeggio climbs over the offer ladder)
  32.0-36.0 half-time breakdown under "Same pizza..."
  36.0-42.0 groove returns, V-I cadence, final hit at 42.0
"""
import json
import os
import subprocess

import numpy as np
import soundfile as sf
from scipy import signal
from scipy.ndimage import minimum_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TL = json.load(open(os.path.join(ROOT, "timeline.json")))
SR = 48000
DUR = TL["duration"]
N = int(SR * DUR)
BEAT = 60 / TL["bpm"]
BAR = 4 * BEAT
S16 = BEAT / 4
RNG = np.random.default_rng(20261004)


# ------------------------------------------------------------------ helpers
def tt(d):
    return np.arange(int(SR * d)) / SR


NAMES = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6,
         "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def hz(n):
    name, octv = n[:-1], int(n[-1])
    return 440.0 * 2 ** ((12 * (octv + 1) + NAMES[name] - 69) / 12)


def _sos(kind, f, order=2):
    return signal.butter(order, f, kind, fs=SR, output="sos")


def lp(x, f, o=2): return signal.sosfilt(_sos("lowpass", f, o), x, axis=0)
def hp(x, f, o=2): return signal.sosfilt(_sos("highpass", f, o), x, axis=0)
def bp(x, lo, hi, o=2): return signal.sosfilt(_sos("bandpass", [lo, hi], o), x, axis=0)


def peaking(x, f0, gain_db, q=1.0):
    a = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / SR
    al = np.sin(w0) / (2 * q)
    b = [1 + al * a, -2 * np.cos(w0), 1 - al * a]
    aa = [1 + al / a, -2 * np.cos(w0), 1 - al / a]
    return signal.lfilter(b, aa, x, axis=0)


def noise(n):
    return RNG.standard_normal(n)


def sweep_bp(x, f0, f1, q=2.0, blocks=64):
    """Band-pass with a centre frequency that glides f0 -> f1 (exponential)."""
    out = np.zeros_like(x)
    edges = np.linspace(0, len(x), blocks + 1).astype(int)
    zi = None
    for i in range(blocks):
        fc = f0 * (f1 / f0) ** (i / max(1, blocks - 1))
        lo, hi = max(30, fc / (1 + 1 / q)), min(SR / 2 - 100, fc * (1 + 1 / q))
        sos = _sos("bandpass", [lo, hi], 2)
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        out[edges[i]:edges[i + 1]], zi = signal.sosfilt(sos, x[edges[i]:edges[i + 1]], zi=zi)
    return out


def pan(sig, p=0.0):
    """Equal-power pan, 0 dB at centre."""
    if sig.ndim == 2:
        return sig
    a = (p + 1) * np.pi / 4
    return np.stack([sig * np.cos(a), sig * np.sin(a)], 1) * np.sqrt(2)


class Bus:
    def __init__(self):
        self.x = np.zeros((N, 2))

    def add(self, sig, t0, gain=1.0, p=0.0):
        st = pan(np.asarray(sig, dtype=np.float64), p) * gain
        i0 = int(round(t0 * SR))
        if i0 < 0:
            st, i0 = st[-i0:], 0
        n = min(len(st), N - i0)
        if n > 0:
            self.x[i0:i0 + n] += st[:n]


# ---------------------------------------------------------------- instruments
def kick(level=1.0, low=48.0):
    t = tt(0.5)
    f = low + 125 * np.exp(-t * 32) + 28 * np.exp(-t * 7)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.0) * (1 - np.exp(-t * 3000))
    click = hp(noise(len(t)), 2500) * np.exp(-t * 380) * 0.22
    x = np.tanh((body + click) * 1.5) / np.tanh(1.5)
    return x * level


def clap():
    t = tt(0.45)
    env = sum(np.where(t >= d, np.exp(-(t - d) * 190), 0) for d in (0.0, 0.010, 0.019, 0.029))
    env = env + np.where(t >= 0.029, 0.55 * np.exp(-(t - 0.029) * 16), 0)
    return bp(noise(len(t)), 950, 3400) * env * 0.55


def snare(dec=17):
    t = tt(0.35)
    tone = np.sin(2 * np.pi * 186 * t) * np.exp(-t * 26) * 0.5 + np.sin(2 * np.pi * 332 * t) * np.exp(-t * 32) * 0.22
    nz = bp(noise(len(t)), 1300, 8500) * np.exp(-t * dec)
    return (tone + nz * 0.85) * 0.6


def sub808(f, dur, level=1.0, glide_to=None):
    """A long 808: a sine that drops into pitch, saturated so it reads on phone speakers,
    optionally gliding to a second note over its last third."""
    t = tt(dur)
    f_t = f * (1 + 0.5 * np.exp(-t * 40))
    if glide_to:
        g = np.clip((t - dur * 0.66) / (dur * 0.3), 0, 1)
        f_t = f_t * (1 - g) + glide_to * g
    x = np.sin(2 * np.pi * np.cumsum(f_t) / SR)
    x = np.tanh(x * 2.2) / np.tanh(2.2)
    env = (1 - np.exp(-t * 400)) * np.exp(-t * 0.9) * np.clip((dur - t) / 0.05, 0, 1)
    return hp(lp(x * env, 1800), 38) * level


HATS = [hp(noise(int(SR * 0.09)), 7800, 4) * np.exp(-tt(0.09) * 62) for _ in range(6)]
OHATS = [hp(noise(int(SR * 0.4)), 7200, 4) * np.exp(-tt(0.4) * 9.5) for _ in range(3)]


def saw_add(f, t, fc, nmax=40, fmax=12000, phase=0.0):
    x = np.zeros_like(t)
    for n in range(1, nmax + 1):
        fn = f * n
        if fn > fmax:
            break
        w = (1 / n) / np.sqrt(1 + (fn / fc) ** 4)
        x += w * np.sin(2 * np.pi * fn * t + phase * n)
    return x


def bass(f, dur, level=1.0):
    t = tt(dur + 0.06)
    fc = 260 + 1100 * np.exp(-t * 13)
    x = saw_add(f, t, fc, nmax=36, fmax=6000) + 0.55 * np.sin(2 * np.pi * f * t)
    env = np.minimum(1, t / 0.004) * np.where(t < dur, 1.0, np.exp(-(t - dur) * 70)) * (0.82 + 0.18 * np.exp(-t * 9))
    return np.tanh(x * env * 1.3) * 0.62 * level


_STAB = {}


def stab(notes, dur=0.15, level=1.0, bright=1.0):
    key = (tuple(notes), round(dur, 3), round(bright, 2))
    if key not in _STAB:
        t = tt(dur + 0.3)
        fc = 700 + 3200 * bright * np.exp(-t * 9)
        L = np.zeros_like(t)
        R = np.zeros_like(t)
        for i, n in enumerate(notes):
            f = hz(n)
            for k, det in enumerate((-0.0058, 0.0, 0.0062)):
                v = saw_add(f * (1 + det), t, fc, nmax=28, fmax=11000, phase=0.37 * (i + k))
                if k == 0:
                    L += v
                elif k == 2:
                    R += v
                else:
                    L += v * 0.7
                    R += v * 0.7
        env = np.minimum(1, t / 0.003) * np.exp(-t * 6) * np.where(t < dur, 1.0, np.exp(-(t - dur) * 26))
        _STAB[key] = np.stack([L * env, R * env], 1) * 0.16
    return _STAB[key] * level


def pad(notes, dur, level=1.0, cut=1600, att=0.35, rel=0.9):
    t = tt(dur + rel)
    L = np.zeros_like(t)
    R = np.zeros_like(t)
    for i, n in enumerate(notes):
        f = hz(n)
        for k, det in enumerate((-0.007, 0.0, 0.0075)):
            vib = 1 + 0.0018 * np.sin(2 * np.pi * (0.23 + 0.07 * k) * t + i)
            ph = 2 * np.pi * np.cumsum(f * (1 + det) * vib) / SR
            v = np.zeros_like(t)
            for h in range(1, 18):
                fn = f * h
                if fn > 9000:
                    break
                v += (1 / h) / np.sqrt(1 + (fn / cut) ** 4) * np.sin(ph * h + 0.5 * h * k)
            if k == 0:
                L += v
            elif k == 2:
                R += v
            else:
                L += v * 0.7
                R += v * 0.7
    env = np.minimum(1, t / att) * np.where(t < dur, 1.0, np.exp(-(t - dur) * (5 / rel)))
    return np.stack([L * env, R * env], 1) * 0.07 * level


def pluck(f, dur=0.6, level=1.0, bright=1.0):
    t = tt(dur)
    idx = 2.3 * bright * np.exp(-t * 24)
    x = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * 3 * t))
    x += 0.25 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 14)
    return x * np.minimum(1, t / 0.0015) * np.exp(-t * 8.5) * 0.3 * level


def bell(f, dur=1.4, level=1.0, ratio=1.4, idx0=2.6, dec=3.2):
    t = tt(dur)
    idx = idx0 * np.exp(-t * 5)
    x = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * ratio * t))
    return x * np.minimum(1, t / 0.0008) * np.exp(-t * dec) * 0.28 * level


def tape_stop(x, length):
    """Read `x` with a playback rate falling 1 -> 0 over `length` seconds."""
    t = tt(length)
    pos = (t - t ** 2 / (2 * length)) * SR
    out = np.zeros((len(t), 2))
    for c in range(2):
        out[:, c] = np.interp(pos, np.arange(len(x)), x[:, c])
    return out * np.linspace(1, 0.2, len(t))[:, None]


def make_ir(rt60=1.7, length=2.2, damp=5500):
    t = tt(length)
    dec = np.exp(-6.91 * t / rt60)
    ir = np.stack([lp(noise(len(t)), damp) * dec, lp(noise(len(t)), damp) * dec], 1)
    ir[: int(0.012 * SR)] = 0
    return ir / np.sqrt((ir ** 2).sum(0, keepdims=True))


# ----------------------------------------------------------------------- SFX
def env_bell(t, a, b):
    return np.minimum(1, t / a) * np.exp(-np.maximum(0, t - a) / b)


def sfx(kind):
    """Returns (stereo signal, gain, send-to-reverb)."""
    if kind == "sizzle":
        # hot cheese and oil: a soft high hiss that breathes, with sparse crackles on top
        d = 3.4
        t = tt(d)
        r = np.random.default_rng(31)
        breathe = lp(np.abs(noise(len(t))), 5)
        breathe = 0.55 + 0.45 * breathe / (breathe.max() + 1e-9)
        hiss = bp(noise(len(t)), 3500, 11000) * 0.22 * breathe
        out = np.zeros((len(t), 2))
        for ch in range(2):
            ts = np.cumsum(r.exponential(1 / 48, 400))
            for ti in ts[ts < d - 0.02]:
                L = int(SR * r.uniform(0.0015, 0.007))
                burst = hp(noise(L), 1800) * np.exp(-np.arange(L) / (L / 4)) * r.uniform(0.15, 1.0) ** 2
                i0 = int(ti * SR)
                out[i0:i0 + L, ch] += burst[: len(t) - i0]
        env = np.minimum(1, t / 0.12) * np.minimum(1, (d - t) / 0.9)
        out = (out * 0.8 + hiss[:, None]) * env[:, None]
        return out / np.abs(out).max(), 0.3, 0.08
    if kind == "paper":
        # a receipt sliding in: band-limited noise with a fast, uneven flutter
        t = tt(0.42)
        flutter = 0.5 + 0.5 * np.abs(np.sin(2 * np.pi * (34 + 12 * np.sin(2 * np.pi * 3 * t)) * t))
        x = bp(noise(len(t)), 900, 6500) * flutter * env_bell(t, 0.05, 0.14)
        return pan(x, 0.1), 0.38, 0.05
    if kind == "pen":
        # a marker struck through "full price"
        t = tt(0.3)
        x = sweep_bp(noise(len(t)), 1800, 4200, 2.5, blocks=24) * env_bell(t, 0.03, 0.12)
        return pan(x, -0.15), 0.42, 0.05
    if kind == "swell":
        t = tt(0.32)
        x = sweep_bp(noise(len(t)), 1500, 9000, 1.5) * (t / 0.32) ** 2.5
        return pan(x * 0.6), 0.5, 0.2
    if kind in ("slam", "slam_big", "slam_soft"):
        big = kind == "slam_big"
        d = 0.6 if big else 0.32
        t = tt(d)
        f = (40 if big else 55) + (110 if big else 95) * np.exp(-t * 22)
        thump = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (6 if big else 11))
        crack = bp(noise(len(t)), 1800, 7000) * np.exp(-t * 90) * 0.5
        x = thump + crack
        if big:   # comic "bwomp" for "the bill?"
            fb = 196 * (0.5 ** (np.minimum(t, 0.45) / 0.45))
            bw = lp(signal.sawtooth(2 * np.pi * np.cumsum(fb) / SR), 900) * env_bell(t, 0.02, 0.22) * 0.5
            x = x + bw
        g = {"slam": 0.55, "slam_big": 0.75, "slam_soft": 0.4}[kind]
        return pan(np.tanh(x * 1.2)), g, 0.15
    if kind == "scratch":
        t = tt(0.26)
        fc = 900 + 1800 * np.abs(np.sin(2 * np.pi * 3.8 * t)) ** 1.5
        nz = noise(len(t))
        out = np.zeros_like(nz)
        for i in range(0, len(t), 256):
            seg = slice(i, min(len(t), i + 256))
            out[seg] = bp(nz[seg], fc[i] * 0.7, fc[i] * 1.4, 1)
        return pan(out * env_bell(t, 0.01, 0.12) * 1.2), 0.45, 0.0
    if kind in ("whoosh", "whoosh_up", "fly", "sheet", "wipe", "zoom"):
        d = {"whoosh": 0.5, "whoosh_up": 0.55, "fly": 0.42, "sheet": 0.4, "wipe": 0.45, "zoom": 0.85}[kind]
        t = tt(d)
        f0, f1 = {"whoosh": (500, 2600), "whoosh_up": (300, 4500), "fly": (900, 5000),
                  "sheet": (400, 2200), "wipe": (600, 3000), "zoom": (250, 7000)}[kind]
        x = sweep_bp(noise(len(t)), f0, f1, 1.8)
        if kind == "zoom":
            e = (t / d) ** 2.2
        else:
            e = np.sin(np.pi * np.minimum(1, t / d)) ** 1.5
        L = x * e * (1 - 0.5 * t / d)
        R = x * e * (0.5 + 0.5 * t / d)
        g = {"whoosh": 0.5, "whoosh_up": 0.5, "fly": 0.28, "sheet": 0.35, "wipe": 0.5, "zoom": 0.6}[kind]
        return np.stack([L, R], 1) * 1.6, g, 0.15
    if kind == "print":
        t = tt(0.16)
        buzz = (signal.square(2 * np.pi * 95 * t) * 0.5 + 0.5) * bp(noise(len(t)), 1200, 5200)
        return pan(buzz * env_bell(t, 0.005, 0.06), 0.25), 0.32, 0.0
    if kind in ("tally", "tally_short"):
        d = 0.65 if kind == "tally" else 0.38
        n = 16 if kind == "tally" else 10
        out = np.zeros(int(SR * (d + 0.05)))
        for i in range(n):
            u = i / (n - 1)
            ti = d * (1 - (1 - u) ** 1.7)
            tk = tt(0.012)
            blip = np.sin(2 * np.pi * (2300 + 500 * u) * tk) * np.exp(-tk * 400)
            i0 = int(ti * SR)
            out[i0:i0 + len(blip)] += blip
        return pan(out, 0.1), 0.22, 0.0
    if kind == "stamp":
        t = tt(0.32)
        f = 60 + 90 * np.exp(-t * 30)
        th = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)
        slap = lp(noise(len(t)), 3500) * np.exp(-t * 60) * 0.7
        return pan(np.tanh((th + slap) * 1.4)), 0.7, 0.12
    if kind == "riser":
        d = 1.95
        t = tt(d)
        x = sweep_bp(noise(len(t)), 300, 9000, 2.2, blocks=128) * (t / d) ** 2.0
        tone = lp(signal.sawtooth(2 * np.pi * np.cumsum(180 * (4.5 ** (t / d))) / SR), 2500) * (t / d) ** 2.5 * 0.25
        e = np.where(t > d - 0.04, np.maximum(0, (d - t) / 0.04), 1)
        L = (x * 1.2 + tone) * e
        R = (x * 1.2 + np.roll(tone, 90)) * e
        return np.stack([L, R], 1), 0.55, 0.25
    if kind in ("impact", "impact_soft"):
        soft = kind == "impact_soft"
        t = tt(2.2)
        f = 30 + 52 * np.exp(-t * 6)
        boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (2.6 if not soft else 4.5))
        crash = hp(noise(len(t)), 2500) * np.exp(-t * (3.2 if not soft else 6)) * 0.22
        hit = lp(noise(len(t)), 2000) * np.exp(-t * 30) * 0.8
        x = np.tanh((boom + hit) * 1.3) + crash
        return np.stack([x, np.roll(x, 30)], 1), (0.85 if not soft else 0.5), 0.35
    if kind == "coins":
        out = np.zeros((int(SR * 1.8), 2))
        r = np.random.default_rng(5)
        for i in range(34):
            ti = 1.2 * (r.random() ** 1.8)
            b = bell(r.uniform(2600, 5200), 0.35, 1.0, ratio=2.76, idx0=1.4, dec=16)
            i0 = int(ti * SR)
            out[i0:i0 + len(b)] += pan(b, r.uniform(-0.8, 0.8))[: len(out) - i0] * (1 - 0.6 * ti / 1.2)
        return out, 0.42, 0.3
    if kind in ("shine", "sparkle"):
        out = np.zeros((int(SR * 1.6), 2))
        notes = ["F6", "A6", "C7", "F7", "A7"] if kind == "shine" else None
        r = np.random.default_rng(9 if kind == "shine" else 13)
        for i in range(5 if kind == "shine" else 9):
            f = hz(notes[i]) if notes else r.uniform(3500, 8000)
            ti = i * (0.045 if kind == "shine" else 0.05) + (0 if notes else r.uniform(0, 0.05))
            b = bell(f, 0.9, 0.6, ratio=2.0, idx0=0.8, dec=6)
            i0 = int(ti * SR)
            out[i0:i0 + len(b)] += pan(b, r.uniform(-0.6, 0.6))
        return out, 0.35, 0.45
    if kind == "typing":
        out = np.zeros(int(SR * 0.75))
        r = np.random.default_rng(3)
        for i in range(18):
            ti = i * (0.62 / 18) + r.uniform(-0.006, 0.006)
            tk = tt(0.03)
            c = bp(noise(len(tk)), 2000, 7000) * np.exp(-tk * 500) + np.sin(2 * np.pi * 320 * tk) * np.exp(-tk * 260) * 0.6
            i0 = max(0, int(ti * SR))
            out[i0:i0 + len(c)] += c * r.uniform(0.7, 1.0)
        return pan(out, -0.1), 0.3, 0.0
    if kind == "ding":
        out = np.zeros((int(SR * 1.6), 2))
        out[: int(SR * 1.4)] += pan(bell(hz("C6"), 1.4, 1.0, ratio=1.0, idx0=1.2, dec=3.5))
        i0 = int(0.12 * SR)
        out[i0:i0 + int(SR * 1.4)] += pan(bell(hz("F6"), 1.4, 1.0, ratio=1.0, idx0=1.2, dec=3.5))
        return out, 0.3, 0.35
    if kind == "tap":
        t = tt(0.05)
        x = hp(noise(len(t)), 2200) * np.exp(-t * 900) * 0.6 + np.sin(2 * np.pi * 1450 * t) * np.exp(-t * 160)
        return pan(x), 0.32, 0.0
    if kind == "pop":
        t = tt(0.12)
        f = 320 + 700 * (1 - np.exp(-t * 45))
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_bell(t, 0.003, 0.035)
        return pan(x), 0.4, 0.05
    if kind == "drop":
        t = tt(0.5)
        f = 380 + 760 * np.exp(-t * 7) * (1 + 0.03 * np.sin(2 * np.pi * 18 * t))
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_bell(t, 0.004, 0.16)
        x += 0.35 * np.sin(2 * np.pi * np.cumsum(f * 2) / SR) * env_bell(t, 0.004, 0.08)
        return pan(x), 0.34, 0.15
    if kind == "tick":
        t = tt(0.04)
        x = np.sin(2 * np.pi * 1750 * t) * np.exp(-t * 220) + hp(noise(len(t)), 3000) * np.exp(-t * 1200) * 0.3
        return pan(x, 0.15), 0.22, 0.0
    if kind in ("cash", "jackpot"):
        out = np.zeros((int(SR * 2.0), 2))
        t = tt(0.06)
        clunk = bp(noise(len(t)), 600, 2400) * np.exp(-t * 90)
        out[: len(t)] += pan(clunk) * 0.8
        i0 = int(0.055 * SR)
        for f, g in ((2093, 1.0), (2637, 0.8), (3136, 0.6), (4186, 0.35)):
            b = bell(f, 1.2, g, ratio=2.76, idx0=1.1, dec=4.2)
            out[i0:i0 + len(b)] += pan(b, 0.1)
        r = np.random.default_rng(17)
        for k in range(10):
            b = bell(r.uniform(3000, 6000), 0.25, 0.4, ratio=2.4, idx0=1.0, dec=20)
            j = i0 + int(r.uniform(0, 0.25) * SR)
            out[j:j + len(b)] += pan(b, r.uniform(-0.5, 0.5))
        if kind == "jackpot":
            for k, n in enumerate(["C5", "E5", "G5", "C6", "E6"]):
                p = pluck(hz(n), 0.7, 1.4, 1.2)
                j = int((0.12 + k * 0.06) * SR)
                out[j:j + len(p)] += pan(p, -0.3 + 0.15 * k)
        return out, (0.45 if kind == "cash" else 0.55), 0.3
    raise KeyError(kind)


# ------------------------------------------------------------------- score
CH = {
    "F": {"root": "F2", "stab": ["A3", "C4", "F4"], "arp": ["F4", "A4", "C5", "F5", "A5", "C6"]},
    "C": {"root": "C2", "stab": ["G3", "C4", "E4"], "arp": ["C4", "E4", "G4", "C5", "E5", "G5"]},
    "Dm": {"root": "D2", "stab": ["A3", "D4", "F4"], "arp": ["D4", "F4", "A4", "D5", "F5", "A5"]},
    "Bb": {"root": "Bb1", "stab": ["Bb3", "D4", "F4"], "arp": ["Bb3", "D4", "F4", "Bb4", "D5", "F5"]},
    "A": {"root": "A1", "stab": ["A3", "C#4", "E4"], "arp": ["A3", "C#4", "E4", "A4"]},
}


def build_music():
    mus, verb, kicks, side = Bus(), Bus(), Bus(), np.zeros(N)
    K = kick()

    def hit_kick(t, lvl=1.0):
        kicks.add(K, t, 0.8 * lvl)
        i0 = int(t * SR)
        k = np.exp(-tt(0.32) * 14)
        n = min(len(k), N - i0)
        if n > 0:
            side[i0:i0 + n] = np.maximum(side[i0:i0 + n], k[:n] * lvl)

    # intro 0.0-1.6: playful F major, tape-stopped at 1.45-1.85
    intro = Bus()
    for b in np.arange(0, 2.0, BEAT):
        intro.add(K, b, 0.55)
    for i, b in enumerate(np.arange(0, 2.0, S16 * 2)):
        intro.add(HATS[i % 6], b, 0.35, 0.3)
    arp = ["F4", "A4", "C5", "F5", "C5", "A4", "C5", "F5"]
    for i, b in enumerate(np.arange(0, 2.0, S16 * 2)):
        intro.add(pluck(hz(arp[i % 8]), 0.5, 1.0, 1.1), b, 0.9, -0.2 + 0.05 * (i % 8))
    intro.add(pad(["A3", "C4", "F4"], 2.0, 0.9, cut=2200, att=0.25), 0.0, 1.0)
    cut = int(1.45 * SR)
    mus.x[:cut] += intro.x[:cut]
    ts = tape_stop(intro.x[cut:cut + int(0.6 * SR)], 0.4)
    mus.x[cut:cut + len(ts)] += ts

    # tension 1.9-6.0 in D minor: heartbeat, ticking clock, dark pads, D drone
    for c, a, b in (("Dm", 2.0, 4.0), ("Bb", 4.0, 5.0), ("A", 5.0, 6.0)):
        mus.add(pad(CH[c]["stab"], b - a, 0.9, cut=950, att=0.3, rel=0.4), a, 1.0)
    hb = kick(0.9, low=40)
    hb = lp(hb, 400)
    for b in np.arange(2.0, 6.0, 1.0):
        mus.add(hb, b, 0.7)
        mus.add(hb, b + 0.2, 0.45)
    for i, b in enumerate(np.arange(2.0, 6.0, BEAT)):
        tk = np.sin(2 * np.pi * (1900 if i % 2 == 0 else 1500) * tt(0.03)) * np.exp(-tt(0.03) * 260)
        mus.add(tk, b, 0.12, 0.5 if i % 2 == 0 else -0.5)
    drone = bass(hz("D2"), 3.9, 0.5)
    mus.add(lp(drone, 500), 2.0, 0.6)

    # riser bed 6.0-7.9: snare roll accelerating over an A pedal, gap before 8.0
    mus.add(pad(CH["A"]["stab"], 1.85, 0.8, cut=1300, att=1.2, rel=0.08), 6.0, 1.0)
    sn = snare(22)
    times = list(np.arange(6.0, 7.0, 0.25)) + list(np.arange(7.0, 7.5, 0.125)) + list(np.arange(7.5, 7.88, 0.0625))
    for t0 in times:
        mus.add(sn, t0, 0.15 + 0.5 * ((t0 - 6.0) / 1.9) ** 2, 0.1)

    # grooves
    def groove(t0, t1, prog, arp_level=0.0, lead=None, hat_level=1.0, stab_bright=1.0, half=False):
        bars = np.arange(t0, t1 - 1e-6, BAR)
        for bi, b in enumerate(bars):
            ch = CH[prog[bi % len(prog)]]
            # drums
            if half:
                hit_kick(b, 0.9)
                mus.add(snare(14), b + 2 * BEAT, 0.5, 0.05)
                verb.add(snare(14), b + 2 * BEAT, 0.25)
            else:
                for k in range(4):
                    hit_kick(b + k * BEAT)
                mus.add(clap(), b + BEAT, 0.75, 0.05)
                mus.add(clap(), b + 3 * BEAT, 0.75, -0.05)
                verb.add(clap(), b + BEAT, 0.3)
                verb.add(clap(), b + 3 * BEAT, 0.3)
            for k in range(16):
                if half and k % 2:
                    continue
                if k % 4 == 2:
                    mus.add(OHATS[k % 3], b + k * S16, 0.2 * hat_level, 0.35)
                else:
                    mus.add(HATS[(bi + k) % 6], b + k * S16, (0.16 if k % 2 else 0.24) * hat_level, 0.3)
            # 808 under each bar (an octave below the bass); in half-time it slides to the next root
            root = hz(ch["root"])
            nxt = hz(CH[prog[(bi + 1) % len(prog)]]["root"])
            if half:
                mus.add(sub808(root, BAR - 0.02, 1.0, glide_to=nxt), b, 0.36)
                for k in range(24):                                   # triplet hats: the trap feel
                    if k % 3 == 2 and k % 6 != 5:
                        continue
                    mus.add(HATS[k % 6], b + k * BAR / 24, 0.13 + 0.06 * (k % 3 == 0), 0.25)
            else:
                mus.add(sub808(root, BEAT * 1.9, 0.9), b, 0.26)
                mus.add(sub808(root, BEAT * 1.9, 0.8), b + 2 * BEAT, 0.2)
            if not half:
                mus.add(snare(19), b + BEAT, 0.32, 0.0)
                mus.add(snare(19), b + 3 * BEAT, 0.32, 0.0)
            # bass: off-beat eighths, octave pop on the last one
            if half:
                mus.add(bass(root, BAR - 0.05, 0.9), b, 0.75)
            else:
                for k in range(4):
                    f = root * (2 if k == 3 else 1)
                    mus.add(bass(f, 0.2, 1.0), b + k * BEAT + 2 * S16, 0.7)
            # chord stabs on the off-beats (pads in the half-time section)
            if half:
                mus.add(pad(ch["stab"], BAR, 1.0, cut=2400, att=0.08, rel=0.6), b, 1.0)
            else:
                for k in range(4):
                    s = stab(ch["stab"], 0.13, 1.0, stab_bright)
                    mus.add(s, b + k * BEAT + 2 * S16, 0.85)
                    verb.add(s, b + k * BEAT + 2 * S16, 0.25)
            # arpeggio: sixteenth plucks climbing the chord
            if arp_level > 0:
                for k in range(16):
                    n = ch["arp"][k % len(ch["arp"])] if (bi % 2 == 0) else ch["arp"][(len(ch["arp"]) - 1 - k) % len(ch["arp"])]
                    p = pluck(hz(n), 0.35, 0.8 + 0.4 * (k / 15), 0.9)
                    mus.add(p, b + k * S16, arp_level, -0.4 if k % 2 else 0.4)
                    verb.add(p, b + k * S16, arp_level * 0.4)
        if lead:
            for t_on, n, d in lead:
                p = pluck(hz(n), max(0.4, d + 0.2), 1.0, 1.2)
                mus.add(p, t_on, 0.75, 0.0)
                verb.add(p, t_on, 0.4)

    hook_over_c = [(0, "G4", 0.5), (0.5, "C5", 0.25), (0.75, "E5", 0.25), (1.0, "D5", 0.5), (1.5, "C5", 0.5)]
    hook_over_bb = [(0, "F4", 0.5), (0.5, "Bb4", 0.25), (0.75, "D5", 0.25), (1.0, "C5", 0.5), (1.5, "Bb4", 0.5)]
    lead = [(10.0 + a, n, d) for a, n, d in hook_over_c] + [(18.0 + a, n, d) for a, n, d in hook_over_c]
    groove(8.0, 24.0, ["F", "C", "Dm", "Bb"], arp_level=0.22, lead=lead)
    lead2 = [(30.0 + a, n, d) for a, n, d in hook_over_bb]
    groove(24.0, 32.0, ["F", "C", "Dm", "Bb"], arp_level=0.5, lead=lead2, hat_level=1.15, stab_bright=1.25)
    groove(32.0, 36.0, ["Bb", "C"], half=True)
    groove(36.0, 40.0, ["F", "C"], arp_level=0.3, stab_bright=1.2)
    # 40-42: Bb then C (half bars), softer, into the final F hit at 42.0
    for b, c in ((40.0, "Bb"), (41.0, "C")):
        hit_kick(b, 0.8)
        hit_kick(b + BEAT, 0.6)
        mus.add(pad(CH[c]["stab"], 1.0, 1.1, cut=2600, att=0.05, rel=0.3), b, 1.0)
        mus.add(bass(hz(CH[c]["root"]), 0.95, 0.9), b, 0.7)
    for k, n in enumerate(["C5", "D5", "E5", "F5"]):
        mus.add(pluck(hz(n), 0.5, 1.2, 1.1), 41.0 + k * 0.25, 0.6)
    # final hit
    hit_kick(42.0, 1.0)
    fin = stab(["F3", "A3", "C4", "F4", "A4"], 0.6, 1.0, 1.3)
    mus.add(fin, 42.0, 1.1)
    verb.add(fin, 42.0, 0.6)
    mus.add(pad(["F3", "A3", "C4", "F4"], 0.6, 1.4, cut=3000, att=0.01, rel=0.9), 42.0, 1.0)
    mus.add(bass(hz("F1"), 0.7, 1.0), 42.0, 0.8)
    crash = hp(noise(int(SR * 1.0)), 4000) * np.exp(-tt(1.0) * 4)
    mus.add(np.stack([crash, np.roll(crash, 40)], 1), 42.0, 0.18)
    # crashes on section downbeats
    for b in (8.0, 24.0, 36.0):
        cr = hp(noise(int(SR * 1.6)), 4500) * np.exp(-tt(1.6) * 3)
        mus.add(np.stack([cr, np.roll(cr, 55)], 1), b, 0.16)

    # hat rolls into the cuts: 1/32 notes, swelling
    for t_end in (10.0, 24.0, 32.0, 36.0):
        n = 16
        for k in range(n):
            mus.add(HATS[k % 6], t_end - 0.5 + k * 0.5 / n, 0.08 + 0.22 * (k / n) ** 1.5, 0.2 * (1 if k % 2 else -1))
    for b in (8.0, 24.0, 36.0):
        mus.add(sub808(hz("F1"), 1.6, 1.0), b, 0.36)

    # sidechain pump: everything ducks under the kick, the kick itself stays whole
    pump = 1 - 0.35 * side
    mus.x *= pump[:, None]
    mus.x += kicks.x
    return mus, verb


def build_sfx():
    fx, verb = Bus(), Bus()
    ladder_notes = {25.0: "C5", 25.5: "D5", 26.0: "E5", 26.5: "F5", 27.0: "G5"}
    for e in TL["sfx"]:
        t0, k = e["t"], e["k"]
        if k == "riser":
            sig, g, send = sfx(k)
            fx.add(sig, t0, g)
            verb.add(sig, t0, g * send)
            continue
        sig, g, send = sfx(k)
        fx.add(sig, t0, g)
        if send:
            verb.add(sig, t0, g * send)
        if k == "pop" and t0 in ladder_notes:
            p = pluck(hz(ladder_notes[t0]), 0.6, 1.3, 1.3)
            fx.add(p, t0, 0.9)
            verb.add(p, t0, 0.4)
    return fx, verb


# ---------------------------------------------------------------------- VO
def compress(x, thr_db=-24.0, ratio=3.0, att=0.004, rel=0.12):
    lvl = signal.lfilter([1 - np.exp(-1 / (SR * 0.01))], [1, -np.exp(-1 / (SR * 0.01))], x ** 2)
    lvl_db = 10 * np.log10(np.maximum(lvl, 1e-10))
    gr = np.where(lvl_db > thr_db, (thr_db - lvl_db) * (1 - 1 / ratio), 0.0)
    # attack/release smoothing of gain reduction
    out = np.empty_like(gr)
    a_a, a_r = np.exp(-1 / (SR * att)), np.exp(-1 / (SR * rel))
    g = 0.0
    for i in range(0, len(gr), 64):        # block-wise is plenty for speech
        target = gr[i:i + 64].min()
        g = a_a * g + (1 - a_a) * target if target < g else a_r * g + (1 - a_r) * target
        out[i:i + 64] = g
    return x * 10 ** (out / 20)


def build_vo():
    vo = np.zeros(N)
    for lid, t0 in TL["vo"].items():
        a, sr = sf.read(os.path.join(HERE, "vo", f"{lid}.wav"))
        a = signal.resample_poly(a, SR // 1000, sr // 1000)
        a = hp(a, 85)
        a = peaking(a, 280, -2.0, 1.0)
        a = peaking(a, 3400, 3.0, 0.9)
        a = peaking(a, 9000, 2.0, 0.7)
        i0 = int(t0 * SR)
        n = min(len(a), N - i0)
        vo[i0:i0 + n] += a[:n]
    vo = compress(vo, -26, 3.0)
    active = np.abs(vo) > 1e-4
    rms = np.sqrt((vo[active] ** 2).mean())
    # hold the crest factor to ~12 dB so the master limiter never has to grab speech
    vo = limiter(vo[:, None], ceiling=rms * 10 ** (12 / 20), look=0.002, rel=0.04)[:, 0]
    rms = np.sqrt((vo[active] ** 2).mean())
    vo *= 10 ** (-17 / 20) / rms            # speech sits at about -17 dBFS RMS
    return vo


def duck_curve(vo, depth_db=-9.0):
    env = signal.lfilter([1 - np.exp(-1 / (SR * 0.02))], [1, -np.exp(-1 / (SR * 0.02))], np.abs(vo))
    on = np.clip(env / (env.max() * 0.08), 0, 1)
    # fast attack, slow release, so the bed doesn't pump between words
    g = np.empty_like(on)
    a_a, a_r = np.exp(-1 / (SR * 0.03)), np.exp(-1 / (SR * 0.35))
    s = 0.0
    for i in range(0, len(on), 64):
        target = on[i:i + 64].max()
        s = a_a * s + (1 - a_a) * target if target > s else a_r * s + (1 - a_r) * target
        g[i:i + 64] = s
    return 10 ** (depth_db * g / 20)


def limiter(x, ceiling=0.89, look=0.004, rel=0.08):
    peak = np.abs(x).max(axis=1)
    need = np.minimum(1.0, ceiling / np.maximum(peak, 1e-9))
    w = int(look * SR)
    need = minimum_filter1d(need, size=2 * w + 1, origin=0)
    g = np.empty_like(need)
    a_r = np.exp(-1 / (SR * rel))
    s = 1.0
    for i in range(0, len(need), 32):
        target = need[i:i + 32].min()
        s = target if target < s else a_r * s + (1 - a_r) * target
        g[i:i + 32] = s
    return x * g[:, None]


def main():
    out_dir = os.path.join(HERE, "build")
    os.makedirs(out_dir, exist_ok=True)
    mus, mverb = build_music()
    fx, fverb = build_sfx()
    vo = build_vo()

    ir = make_ir()
    wet = np.stack([signal.fftconvolve(mverb.x[:, c] + fverb.x[:, c], ir[:, c])[:N] for c in range(2)], 1)

    music = mus.x + wet * 0.55
    music = hp(music, 30)
    music = peaking(music, 350, -1.5, 0.8)
    music *= 10 ** (-18.5 / 20) / np.sqrt((music ** 2).mean())   # bed at about -18.5 dBFS RMS
    duck = duck_curve(vo)
    sfx_bus = fx.x * 10 ** (-3.0 / 20)
    sfx_bus *= (0.5 + 0.5 * duck)[:, None]                        # SFX dip a little under speech

    master = music * duck[:, None] + sfx_bus + pan(vo)
    # fades: in over 40 ms, out over the last 0.6 s
    fade = np.ones(N)
    fade[: int(0.04 * SR)] = np.linspace(0, 1, int(0.04 * SR))
    fade[-int(0.6 * SR):] = np.linspace(1, 0, int(0.6 * SR)) ** 1.5
    master *= fade[:, None]
    master = limiter(master)

    raw = os.path.join(out_dir, "mix_raw.wav")
    sf.write(raw, master.astype(np.float32), SR, subtype="FLOAT")
    for name, sig in (("stem_music.wav", music * duck[:, None]), ("stem_vo.wav", pan(vo)), ("stem_sfx.wav", sfx_bus)):
        sf.write(os.path.join(out_dir, name), sig.astype(np.float32), SR, subtype="FLOAT")

    # two-pass loudnorm to -14 LUFS / -2.5 dBTP (social platforms; the headroom absorbs AAC overshoot)
    m = subprocess.run(["ffmpeg", "-hide_banner", "-i", raw, "-af", "loudnorm=I=-14:TP=-2.5:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    js = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    final = os.path.join(out_dir, "mix.wav")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", raw, "-af",
                    f"loudnorm=I=-14:TP=-2.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
                    f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true",
                    "-ar", str(SR), "-c:a", "pcm_s16le", final], check=True)
    print("measured", {k: js[k] for k in ("input_i", "input_tp", "input_lra")})
    print("wrote", final)


if __name__ == "__main__":
    main()
