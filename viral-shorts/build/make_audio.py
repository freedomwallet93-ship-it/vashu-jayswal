#!/usr/bin/env python3
"""
make_audio.py — original royalty-free music bed + SFX pack for the Short.
Everything is synthesised from scratch with numpy (no external samples, no licensing).
Output: assets/audio/music_bed.wav, assets/audio/sfx/*.wav
"""
import os, json, math
import numpy as np
import soundfile as sf

SR = 48000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "audio")
SFX = os.path.join(OUT, "sfx")
os.makedirs(SFX, exist_ok=True)
rng = np.random.default_rng(7)

# ---------------------------------------------------------------- DSP toolkit
def t_axis(dur):
    return np.arange(int(SR * dur)) / SR

def env_adsr(n, a=0.005, d=0.1, s=0.7, r=0.2, sus=1.0):
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    a_n, d_n, r_n = max(a_n, 1), max(d_n, 1), max(r_n, 1)
    s_n = max(n - a_n - d_n - r_n, 1)
    e = np.concatenate([
        np.linspace(0, 1, a_n),
        np.linspace(1, s, d_n),
        np.full(s_n, s),
        np.linspace(s, 0, r_n),
    ])
    return np.resize(e, n) * sus

def exp_decay(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))

def sine(freq, dur, phase=0.0):
    t = t_axis(dur)
    return np.sin(2 * np.pi * freq * t + phase)

def one_pole_lp(x, cutoff):
    a = math.exp(-2 * math.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y

def biquad(x, kind, f0, Q=0.707):
    """Simple RBJ biquad, vectorised enough for our sizes."""
    w0 = 2 * math.pi * f0 / SR
    cw, sw = math.cos(w0), math.sin(w0)
    alpha = sw / (2 * Q)
    if kind == "lp":
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
    elif kind == "hp":
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
    else:  # bp
        b = [alpha, 0, -alpha]
    a = [1 + alpha, -2 * cw, 1 - alpha]
    b = np.array(b) / a[0]; a = np.array(a) / a[0]
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(len(x)):
        yv = b[0] * x[i] + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        y[i] = yv
        x2, x1 = x1, x[i]
        y2, y1 = y1, yv
    return y

def sweep_lp(x, f_start, f_end, Q=1.2, n_steps=220):
    """Time-varying low-pass: process in chunks with interpolated cutoff (risers)."""
    n = len(x)
    y = np.zeros(n)
    edges = np.linspace(0, n, n_steps + 1).astype(int)
    for k in range(n_steps):
        s, e = edges[k], edges[k + 1]
        if e <= s:
            continue
        frac = k / max(n_steps - 1, 1)
        f0 = f_start * (f_end / f_start) ** frac
        y[s:e] = biquad(x[max(s - 64, 0):e], "lp", min(f0, SR * 0.45), Q)[-len(x[s:e]):]
    return y

def reverb(x, decay=0.45, mix=0.28, taps=(37, 61, 89, 131, 197, 271, 353)):
    wet = np.zeros(len(x) + max(taps) + 1)
    for i, tap in enumerate(taps):
        g = decay ** (i + 1)
        wet[tap:tap + len(x)] += x * g
    wet = wet[:len(x)]
    return (1 - mix) * x + mix * wet

def place(canvas, sig, at):
    s = int(at * SR)
    end = min(len(canvas), s + len(sig))
    if end > s:
        canvas[s:end] += sig[: end - s]
    return canvas

def stereo(mono, width=0.0):
    if width == 0:
        return np.stack([mono, mono], axis=-1)
    d = int(width * 0.001 * SR)
    l = np.concatenate([mono, np.zeros(d)])
    r = np.concatenate([np.zeros(d), mono])[:len(l)]
    return np.stack([l, r], axis=-1)

# ---------------------------------------------------------------- instruments
def kick(dur=0.45, f0=118, f1=44, punch=0.06):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / punch)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * exp_decay(n, 0.11)
    click = rng.normal(0, 1, n) * exp_decay(n, 0.004) * 0.25
    return np.tanh((body + click) * 1.6) * 0.92

def sub_bass(freq, dur, amp=0.5):
    n = int(dur * SR)
    x = np.sin(2 * np.pi * freq * np.arange(n) / SR)
    x += 0.25 * np.sin(2 * np.pi * freq * 2 * np.arange(n) / SR)
    return np.tanh(x * 1.2) * env_adsr(n, 0.01, 0.05, 0.85, 0.15, amp)

def hat(dur=0.05, amp=0.16):
    n = int(dur * SR)
    x = rng.normal(0, 1, n) * exp_decay(n, 0.012)
    return biquad(x, "hp", 7000) * amp

def pad_chord(freqs, dur, amp=0.16, cutoff=900, detune=1.6):
    n = int(dur * SR)
    out = np.zeros(n)
    for f in freqs:
        for k, d in enumerate((-detune, 0.0, detune)):
            ff = f * (1 + d / 1200)
            for h in (1, 2, 3, 5):
                out += np.sin(2 * np.pi * ff * h * np.arange(n) / SR + rng.uniform(0, 6.28)) / (h * 7)
    out = biquad(out / max(len(freqs), 1), "lp", cutoff, 0.8)
    return out * env_adsr(n, 0.9, 1.2, 0.8, 1.4, amp)

def pluck(freq, dur=0.22, amp=0.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * freq * 2.01 * t) + 0.2 * np.sin(2 * np.pi * freq * 3 * t)
    x *= np.exp(-t / 0.07)
    x = biquad(x, "lp", 3200)
    return x * amp

# ---------------------------------------------------------------- music bed
# NOTE: section times get re-synced to the final VO timing (see TIMELINE below).
TIMELINE = {
    "total": 46.0,
    "drop1": 24.4,      # "Free power forever"
    "climax": 33.0,     # satellite armada slam
    "strip": 40.2,      # Mars / outro strip-back
}
BPM = 100.0
BEAT = 60.0 / BPM
BAR = BEAT * 4

def build_music(total=46.0, drop1=24.4, climax=33.0, strip=40.2):
    n = int(total * SR)
    music = np.zeros(n)
    A, C, E, F, G = 55.0, 65.41, 82.41, 43.65, 49.0
    chords = [
        [A * 2, C * 3, E * 3], [F * 2, A * 2, C * 4],
        [C * 3, E * 3, G * 3], [G * 2, E * 3, A * 3],
    ]
    # --- pads: one chord per bar, evolving filter
    bar = 0
    tt = 0.0
    while tt < total:
        f = chords[bar % len(chords)]
        prog = min(tt / max(climax, 1), 1.0)
        cutoff = 500 + 1500 * prog + (900 if tt > climax else 0)
        amp = 0.13 if tt < drop1 else (0.17 if tt < strip else 0.10)
        music = place(music, pad_chord(f, BAR * 1.05, amp=amp, cutoff=cutoff), tt)
        bar += 1
        tt += BAR
    # --- kick + sub pulse
    tt = 0.0
    while tt < total:
        beat_i = round(tt / BEAT)
        # kick pattern: 1 and 3 of every bar, plus double-time after the climax
        on_kick = (beat_i % 4 in (0, 2)) or (tt > climax and beat_i % 2 == 1)
        if tt > strip:
            on_kick = beat_i % 4 == 0
        if on_kick:
            music = place(music, kick() * (0.55 if tt < drop1 else 0.7), tt)
        # sub bass follows the root
        root = [A, F, C, G][int((tt // BAR) % 4)]
        if beat_i % 4 in (0, 2):
            music = place(music, sub_bass(root, BEAT * 1.6, amp=0.42 if tt < drop1 else 0.5), tt)
        # hats: 8ths, only after the build starts
        if tt > 12.0 and tt < strip:
            music = place(music, hat(amp=0.13 if tt < climax else 0.16), tt)
            music = place(music, hat(amp=0.07), tt + BEAT / 2)
        tt += BEAT
    # --- arp: 16ths, tension layer from 12s to the climax, then shimmering top line
    tt = 12.0
    scale = [220.0, 261.63, 293.66, 329.63, 392.0, 440.0, 523.25]
    i = 0
    while tt < total - 1:
        if tt < strip:
            note = scale[(i * 3) % len(scale)] * (2 if tt > climax else 1)
            amp = 0.05 + 0.05 * min((tt - 12) / max(climax - 12, 1), 1)
            music = place(music, pluck(note, amp=amp), tt)
        i += 1
        tt += BEAT / 4
    # --- risers into the two drops
    for when in (drop1, climax):
        dur = 2.4 if when == climax else 1.4
        x = rng.normal(0, 1, int(dur * SR))
        x = sweep_lp(x, 300, 9000, Q=1.4)
        x *= np.linspace(0, 1, len(x)) ** 1.7
        music = place(music, x * (0.30 if when == climax else 0.20), when - dur)
    music = reverb(music, decay=0.42, mix=0.20)
    return music

def master(x, peak=0.94):
    x = np.tanh(x * 1.05)
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    return x

# ---------------------------------------------------------------- SFX pack
def sfx_boom(dur=1.9):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 30 + 70 * np.exp(-t / 0.09)
    ph = 2 * np.pi * np.cumsum(f) / SR
    sub = np.sin(ph) * exp_decay(n, 0.55)
    air = rng.normal(0, 1, n) * exp_decay(n, 0.14)
    air = biquad(air, "lp", 2600)
    x = sub * 1.0 + air * 0.5
    return reverb(x, decay=0.5, mix=0.3) * 0.95

def sfx_impact(dur=2.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 40 + 120 * np.exp(-t / 0.05)
    ph = 2 * np.pi * np.cumsum(f) / SR
    core = np.sin(ph) * exp_decay(n, 0.7)
    crack = rng.normal(0, 1, n) * exp_decay(n, 0.02)
    crack = biquad(crack, "lp", 5200)
    metal = np.sin(2 * np.pi * 187 * t) * exp_decay(n, 0.25) * 0.3
    x = core + crack * 0.6 + metal
    return reverb(x, decay=0.55, mix=0.32) * 0.98

def sfx_riser(dur=2.4):
    n = int(dur * SR)
    noise = rng.normal(0, 1, n)
    noise = sweep_lp(noise, 400, 8000, Q=1.5)
    tone = np.sin(2 * np.pi * np.cumsum(np.linspace(220, 1400, n)) / SR) * 0.35
    x = (noise + tone) * np.linspace(0, 1, n) ** 1.8
    return x * 0.8

def sfx_whoosh(dur=0.55):
    n = int(dur * SR)
    x = rng.normal(0, 1, n)
    x = sweep_lp(x, 3200, 380, Q=1.8)
    x *= np.sin(np.pi * np.linspace(0, 1, n)) ** 1.4
    return x * 0.75

def sfx_reverse(dur=1.1):
    n = int(dur * SR)
    x = rng.normal(0, 1, n)
    x = sweep_lp(x, 900, 6000, Q=1.5)
    x *= np.linspace(0, 1, n) ** 2.2
    return x * 0.7

def sfx_tick(dur=0.06):
    n = int(dur * SR)
    x = rng.normal(0, 1, n) * exp_decay(n, 0.006)
    x += np.sin(2 * np.pi * 1800 * np.arange(n) / SR) * exp_decay(n, 0.004) * 0.5
    return biquad(x, "hp", 900) * 0.55

def sfx_wake(dur=1.6):
    """'it just woke up' — rising shimmer + soft chime."""
    n = int(dur * SR)
    x = np.zeros(n)
    for i, f in enumerate([523, 659, 784, 1046, 1318]):
        x = place(x, np.sin(2 * np.pi * f * np.arange(n) / SR) * exp_decay(n, 0.25) * 0.16, i * 0.11)
    shimmer = rng.normal(0, 1, n) * np.linspace(0, 1, n) ** 2
    shimmer = biquad(shimmer, "hp", 5000)
    return reverb(x + shimmer * 0.25, decay=0.4, mix=0.35) * 0.8

def sfx_cash(dur=1.2):
    """count-up ticks + coin-like ping for the $100,000,000 card."""
    n = int(dur * SR)
    x = np.zeros(n)
    for i in range(14):
        at = i * 0.045
        x = place(x, sfx_tick(0.03) * 0.7, at)
    ping = np.sin(2 * np.pi * 1320 * np.arange(n) / SR) * exp_decay(n, 0.3)
    ping += np.sin(2 * np.pi * 1980 * np.arange(n) / SR) * exp_decay(n, 0.18) * 0.5
    return reverb(x + ping * 0.4, decay=0.35, mix=0.3) * 0.75

def sfx_mars_wind(dur=3.6):
    n = int(dur * SR)
    l = rng.normal(0, 1, n)
    r = rng.normal(0, 1, n)
    l = biquad(l, "lp", 900); r = biquad(r, "lp", 780)
    l = biquad(l, "hp", 90);  r = biquad(r, "hp", 110)
    mod = 0.55 + 0.45 * np.sin(2 * np.pi * 0.22 * np.arange(n) / SR)
    l *= mod; r *= mod * 0.96
    x = np.stack([l, r], axis=-1)
    x *= np.minimum(np.linspace(0, 3, n), 1.0)[:, None]
    x *= np.minimum(np.linspace(3, 0, n), 1.0)[:, None]
    return x * 0.5

def main():
    music = master(build_music(**{k: v for k, v in TIMELINE.items() if k != "total"},
                              total=TIMELINE["total"]), peak=0.9)
    sf.write(os.path.join(OUT, "music_bed.wav"), music, SR, subtype="PCM_16")

    pack = {
        "boom.wav": sfx_boom(),
        "impact.wav": sfx_impact(),
        "riser.wav": sfx_riser(2.4),
        "riser_short.wav": sfx_riser(1.4),
        "whoosh.wav": sfx_whoosh(),
        "reverse.wav": sfx_reverse(),
        "tick.wav": sfx_tick(),
        "wake.wav": sfx_wake(),
        "cash.wav": sfx_cash(),
    }
    for name, sig in pack.items():
        sf.write(os.path.join(SFX, name), master(sig, peak=0.92), SR, subtype="PCM_16")
    sf.write(os.path.join(SFX, "mars_wind.wav"), np.clip(sfx_mars_wind(), -0.92, 0.92), SR, subtype="PCM_16")

    print("music_bed.wav ->", round(len(music) / SR, 2), "s")
    for f in sorted(os.listdir(SFX)):
        info = sf.info(os.path.join(SFX, f))
        print(f"  sfx/{f:<18} {info.duration:.2f}s  {info.channels}ch")

if __name__ == "__main__":
    main()
