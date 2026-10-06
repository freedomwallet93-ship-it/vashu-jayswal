#!/usr/bin/env python3
"""
video_build.py — builds the 45s 9:16 Short:
  step align   : read the VO audio, find per-line timings (silence boundaries), write word timings
  step timeline: merge script + VO timings -> work/timeline.json
  step shots   : render every shot (Ken Burns punch-in/out + grade + grain + vignette)
  step concat  : join shots (hard cuts, 30fps)
  step mix     : final pass — caption overlay + VO + music + SFX + ducking + loudnorm
  step all     : align (if VO exists) -> timeline -> shots -> concat -> mix

Runs with a stub VO (timing-identical tone bursts) if assets/audio/vo/vo_full.wav is missing,
so the whole pipeline can be validated before the real voiceover lands.
"""
import os, sys, json, math, subprocess, shutil
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
ASSETS = os.path.join(ROOT, "assets")
WORK = os.path.join(ROOT, "work")
CLIPS = os.path.join(WORK, "clips")
IMG = os.path.join(ASSETS, "img")
SFX = os.path.join(ASSETS, "audio", "sfx")
VO_DIR = os.path.join(ASSETS, "audio", "vo")
OUT_DIR = os.path.join(ROOT, "output")
FPS = 30
DURATION = 45.0
PRE_ROLL = 0.15
TAIL = 0.55
W, H = 1080, 1920
UP_W, UP_H = 2160, 3840   # 2x oversample before zoompan (kills jitter, keeps render fast)


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


# --------------------------------------------------------------------- script
# VO lines (locked script). `est` is only used for the stub timing.
LINES = [
    ("A Google AI is running in space right now.",              2.55),
    ("Not on Earth. Up there.",                                 1.75),
    ("It launched last week on a SpaceX rocket.",               2.85),
    ("Four AI chips. One fridge-sized satellite.",              2.55),
    ("And it just woke up.",                                    1.60),
    ("But here's the problem: it can only think 15 minutes.",   3.00),
    ("Then it gets too hot. Shuts down.",                       2.35),
    ("Why? Space has no air.",                                  1.75),
    ("No air means no cooling. Heat just sits there.",          2.85),
    ("Up there, the Sun is eight times stronger.",              2.40),
    ("Free power forever.",                                     1.45),
    ("Sounds perfect. Until you do the math.",                  2.25),
    ("One space data center: 100 million dollars.",             2.40),
    ("Same money: ten data centers on Earth.",                  2.35),
    ("Next year: two more. Then a hundred.",                    2.35),
    ("One giant AI brain above us.",                            2.25),
    ("And nobody knows if it works.",                           2.30),
    ("But Mars is the coldest planet, so cooling there is easy... right?", 3.55),
    ("Tell me below. It's all happening right now.",            2.95),
]

# shot per VO line: image, zoom start->end, pan start->end (normalised -1..1), grade, shake
SHOTS = [
    # line 1 — hook
    dict(img="s01_hook_earth.png", z=(1.00, 1.14), pan=(0.00, 0.06), grade=dict(c=1.10, s=1.16, b=0.01, g=1.0, vig=7.0), shake=0.0,
         alt=[dict(img="s02_satellite_closeup.png", z=(1.02, 1.16), pan=(0.0, 0.04), grade=dict(c=1.12, s=1.16, b=0.02, g=1.0, vig=6.5), crop="bottom")]),
    dict(img="s02_satellite_closeup.png", z=(1.22, 1.00), pan=(0.05, 0.00), grade=dict(c=1.12, s=1.14, b=0.02, g=1.0, vig=6.0)),
    dict(img="s03_falcon_launch.png", z=(1.18, 1.00), pan=(-0.05, 0.00), grade=dict(c=1.14, s=1.20, b=0.02, g=1.0, vig=6.5)),
    dict(img="s02_satellite_closeup.png", z=(1.00, 1.30), pan=(0.00, -0.10), grade=dict(c=1.12, s=1.18, b=0.01, g=1.0, vig=6.0), crop="top"),
    dict(img="s04_tpu_chip_macro.png", z=(1.08, 1.26), pan=(0.0, 0.10), grade=dict(c=1.10, s=1.22, b=0.03, g=1.0, vig=7.0)),
    dict(img="s06_satellite_radiators.png", z=(1.05, 1.22), pan=(0.0, -0.05), grade=dict(c=1.12, s=1.10, b=0.02, g=1.0, vig=7.0)),
    dict(img="s06_satellite_radiators.png", z=(1.34, 1.05), pan=(0.10, -0.10), grade=dict(c=1.18, s=1.05, b=0.01, g=0.98, vig=8.0), shake=4.0, crop="bottom",
         alt=[dict(img="s04_tpu_chip_macro.png", z=(1.10, 1.26), pan=(0.0, -0.08), grade=dict(c=1.16, s=1.05, b=0.0, g=0.96, vig=8.5, rs=0.14, bs=-0.10), shake=3.0)]),
    dict(img="s02_satellite_closeup.png", z=(1.10, 1.02), pan=(0.0, 0.0), grade=dict(c=1.05, s=0.85, b=-0.02, g=0.95, vig=9.0), crop="bottom"),
    dict(img="s06_satellite_radiators.png", z=(1.02, 1.20), pan=(0.0, 0.05), grade=dict(c=1.10, s=1.05, b=0.01, g=1.0, vig=8.0),
         alt=[dict(img="s06_satellite_radiators.png", z=(1.30, 1.44), pan=(0.0, 0.06), grade=dict(c=1.20, s=1.02, b=0.0, g=0.97, vig=9.0), crop="top"),
              dict(img="s02_satellite_closeup.png", z=(1.06, 1.18), pan=(0.0, 0.0), grade=dict(c=1.06, s=0.82, b=-0.03, g=0.93, vig=10.0), crop="bottom")]),
    dict(img="s09_sun_blazing.png", z=(1.30, 1.02), pan=(-0.08, 0.0), grade=dict(c=1.16, s=1.25, b=0.04, g=1.02, vig=6.0), shake=5.0),
    dict(img="s05_space_solar_panels.png", z=(1.20, 1.00), pan=(0.06, 0.0), grade=dict(c=1.10, s=1.18, b=0.03, g=1.0, vig=6.0)),
    dict(img="s07_data_center_night.png", z=(1.18, 1.00), pan=(0.0, 0.05), grade=dict(c=1.12, s=1.12, b=0.0, g=1.0, vig=7.0)),
    dict(img="s07_data_center_night.png", z=(1.02, 1.24), pan=(0.0, -0.08), grade=dict(c=1.14, s=1.15, b=0.02, g=1.0, vig=7.0), crop="bottom",
         alt=[dict(img="s07_data_center_night.png", z=(1.34, 1.50), pan=(0.0, -0.10), grade=dict(c=1.20, s=1.18, b=0.03, g=1.0, vig=8.5), crop="top"),
              dict(img="s08_power_grid_dusk.png", z=(1.06, 1.20), pan=(0.0, -0.04), grade=dict(c=1.16, s=1.14, b=0.02, g=1.0, vig=8.0), shake=2.5)]),
    dict(img="s08_power_grid_dusk.png", z=(1.10, 1.24), pan=(0.0, -0.06), grade=dict(c=1.14, s=1.12, b=0.01, g=1.0, vig=7.0)),
    dict(img="s10_satellite_armada.png", z=(1.26, 1.02), pan=(0.08, 0.0), grade=dict(c=1.16, s=1.20, b=0.02, g=1.0, vig=6.5), shake=3.0),
    dict(img="s10_satellite_armada.png", z=(1.02, 1.18), pan=(0.0, 0.04), grade=dict(c=1.12, s=1.18, b=0.01, g=1.0, vig=6.5), crop="top"),
    dict(img="s10_satellite_armada.png", z=(1.16, 1.02), pan=(0.0, 0.0), grade=dict(c=1.06, s=0.80, b=-0.03, g=0.94, vig=9.0)),
    dict(img="s18_mars_canyon.png", z=(1.06, 1.20), pan=(0.0, 0.05), grade=dict(c=1.14, s=1.10, b=0.0, g=1.0, vig=7.5),
         alt=[dict(img="s20_mars_orbit.png", z=(1.20, 1.04), pan=(0.0, 0.0), grade=dict(c=1.14, s=1.12, b=0.01, g=1.0, vig=7.0))]),
    dict(img="s19_mars_storm.png", z=(1.14, 1.02), pan=(0.0, 0.0), grade=dict(c=1.12, s=1.05, b=0.0, g=1.0, vig=8.0), shake=6.0),
]

# text cards: (id, text[], sub, at_line, off, dur, y, size, color)
CARDS = [
    ("hook",   ["GOOGLE AI", "IS IN SPACE?!"], None,        1, 0.10, 2.30, 380, 150, [255, 255, 255, 255]),
    ("up",     ["UP THERE."],                  None,        2, 0.10, 1.20, 470, 130, [255, 226, 0, 255]),
    ("chips",  ["4 CHIPS", "1 SATELLITE"],     None,        4, 0.10, 2.10, 400, 132, [255, 255, 255, 255]),
    ("wake",   ["IT JUST WOKE UP"],            None,        5, 0.05, 1.30, 440, 124, [110, 255, 190, 255]),
    ("15min",  ["15 MINUTES"],                 "THEN IT DIES", 6, 0.15, 2.30, 400, 150, [255, 90, 80, 255]),
    ("noair",  ["NO AIR.", "NO COOLING."],     None,        9, 0.10, 2.40, 400, 130, [255, 255, 255, 255]),
    ("8x",     ["8x POWER"],                   "FOREVER",   11, 0.00, 1.40, 420, 150, [255, 226, 0, 255]),
    ("cash",   ["$100,000,000"],               "ONE SPACE DATA CENTER", 13, 0.05, 2.20, 430, 128, [120, 255, 140, 255]),
    ("then100",["THEN 100."],                  "ONE AI BRAIN", 15, 0.05, 2.20, 430, 150, [255, 255, 255, 255]),
    ("baited", ["MARS =", "COLDEST PLANET?"],  "COMMENT IF I'M WRONG", 18, 0.10, 3.30, 390, 136, [255, 255, 255, 255]),
]

# white flashes (frame-accurate accents on the biggest hits)
FLASHES = []  # filled from line times in build_timeline()

# SFX cues: (sfx_name, line_index(1-based), offset_s, volume)
CUES = [
    ("reverse",      1, -0.15, 0.75),
    ("boom",         1, -0.15, 0.95),
    ("whoosh",       2, -0.06, 0.65),
    ("whoosh",       3, -0.06, 0.65),
    ("whoosh",       4, -0.06, 0.70),
    ("wake",         5, -0.10, 0.85),
    ("tick",         6, -0.06, 0.90),
    ("impact",       6,  0.00, 0.50),
    ("whoosh",       7, -0.02, 0.60),
    ("reverse",      8, -0.15, 0.45),
    ("riser",       10, -2.40, 0.70),
    ("impact",      10,  0.00, 0.72),
    ("whoosh",      11, -0.06, 0.55),
    ("cash",        13,  0.00, 0.85),
    ("impact",      13,  0.00, 0.45),
    ("whoosh",      14, -0.02, 0.55),
    ("riser_short", 15, -1.40, 0.80),
    ("impact",      15,  0.00, 1.00),
    ("boom",        15,  0.00, 0.80),
    ("whoosh",      17, -0.06, 0.55),
    ("mars_wind",   18, -0.10, 0.70),
    ("whoosh",      19, -0.06, 0.50),
    ("reverse",     19,  0.55, 0.65),
]


# ------------------------------------------------------------------- utilities
def run(cmd, quiet=True):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print("CMD FAILED:", " ".join(cmd)[:400])
        print(p.stderr[-3000:])
        raise SystemExit(1)
    return p.stdout + p.stderr


def stub_vo(path, lines_timing):
    """Timing-identical placeholder: one soft tone burst per line."""
    import soundfile as sf
    n = int((PRE_ROLL + sum(d for _, d in lines_timing) + TAIL + 0.6) * 48000)
    x = np.zeros(n, dtype=np.float32)
    t0 = PRE_ROLL
    for i, (txt, d) in enumerate(lines_timing):
        s = int(t0 * 48000); e = min(n, s + int(d * 48000))
        seg = np.arange(e - s) / 48000
        env = np.minimum(np.minimum(seg / 0.05, 1.0), np.minimum((d - seg) / 0.08, 1.0))
        env = np.clip(env, 0, 1)
        x[s:e] += (np.sin(2 * np.pi * (320 + 6 * i) * seg) * 0.25 * env).astype(np.float32)
        t0 += d
    sf.write(path, x, 48000, subtype="PCM_16")
    return path


def align_vo(vo_path):
    """Silence-boundary alignment: split the VO into the 19 script lines."""
    ff = ffmpeg()
    out = run([ff, "-hide_banner", "-i", vo_path, "-af",
               "silencedetect=noise=-38dB:d=0.18", "-f", "null", "-"])
    sil = []
    cur = None
    for ln in out.splitlines():
        if "silence_start:" in ln:
            cur = float(ln.split("silence_start:")[1].split()[0])
        elif "silence_end:" in ln and cur is not None:
            sil.append((cur, float(ln.split("silence_end:")[1].split()[0])))
            cur = None
    # total duration
    dur = None
    for ln in out.splitlines():
        if "Duration:" in ln:
            h, m, s = ln.split("Duration:")[1].split(",")[0].strip().split(":")
            dur = int(h) * 3600 + int(m) * 60 + float(s)
    if dur is None:
        raise SystemExit("could not read VO duration")
    # speech segments = complement of silences
    segs = []
    t = 0.0
    for s, e in sil:
        if s - t > 0.12:
            segs.append((t, s))
        t = e
    if dur - t > 0.12:
        segs.append((t, dur))
    # keep the longest 19 segments in order (ignore stray clicks)
    if len(segs) > len(LINES):
        segs = sorted(sorted(segs, key=lambda p: p[1] - p[0], reverse=True)[:len(LINES)], key=lambda p: p[0])
    elif len(segs) < len(LINES):
        print(f"! alignment found {len(segs)} speech runs for {len(LINES)} lines — falling back to proportional split")
        total = sum(d for _, d in LINES) or 1
        segs, t = [], 0.0
        for _, d in LINES:
            segs.append((t, t + d))
            t += d
        for i in range(len(segs)):
            segs[i] = (segs[i][0], segs[i][1])
    lines = []
    for i, (txt, _) in enumerate(LINES):
        s, e = segs[i]
        words = txt.split()
        wts = np.array([max(len(w), 2) + 1.5 for w in words], dtype=float)
        wts = wts / wts.sum()
        cuts = np.concatenate([[0], np.cumsum(wts)])
        wl = []
        for j, w in enumerate(words):
            wl.append(dict(w=w, s=round(s + (e - s) * cuts[j], 3), e=round(s + (e - s) * cuts[j + 1], 3)))
        lines.append(dict(text=txt, start=round(s, 3), end=round(e, 3), words=wl))
    return lines, dur


def estimate_lines():
    """Stub timings (the browser TTS read is ~1.08x these estimates)."""
    lines, t = [], PRE_ROLL
    for txt, est in LINES:
        d = est
        words = txt.split()
        wts = np.array([max(len(w), 2) + 1.5 for w in words], dtype=float)
        wts = wts / wts.sum()
        cuts = np.concatenate([[0], np.cumsum(wts)])
        wl = [dict(w=w, s=round(t + d * cuts[j], 3), e=round(t + d * cuts[j + 1], 3)) for j, w in enumerate(words)]
        lines.append(dict(text=txt, start=round(t, 3), end=round(t + d, 3), words=wl))
        t += d + 0.06
    return lines, t


# ------------------------------------------------------------------- timeline
def build_timeline():
    os.makedirs(WORK, exist_ok=True)
    vo_real = os.path.join(VO_DIR, "vo_full.wav")
    vo_json = os.path.join(WORK, "vo_lines.json")
    stub = os.path.join(WORK, "vo_stub.wav")
    if os.path.exists(vo_json):
        meta = json.load(open(vo_json))
        lines = meta["lines"]
        vo_dur = meta["vo_end"]
        vo_used = meta["vo_path"]
        mode = f"real (atempo {meta.get('atempo', 1.0):.3f})"
    elif os.path.exists(vo_real):
        lines, vo_dur = align_vo(vo_real)
        vo_used = vo_real
        mode = "real"
    else:
        lines, t_end = estimate_lines()
        stub_vo(stub, [(txt, est) for txt, est in LINES])
        vo_dur = t_end
        vo_used = stub
        mode = "stub"

    # shots follow the VO line boundaries exactly
    shots = []
    for i, ln in enumerate(lines):
        if i < len(SHOTS):
            s = ln["start"]
            e = lines[i + 1]["start"] if i + 1 < len(lines) else ln["end"]
            base = SHOTS[i]
            alts = base.get("alt", [])
            n_seg = max(1, int(math.ceil((e - s) / 2.35)))
            for k in range(n_seg):
                pick = base if k == 0 else (alts[min(k - 1, len(alts) - 1)] if alts else base)
                pick = {kk: vv for kk, vv in pick.items() if kk != "alt"}
                if k > 0 and not alts:
                    # no alternate for this line: emphasise with a tight re-crop punch
                    pick = dict(pick)
                    pick["z"] = (min(pick["z"][0] + 0.16, 1.44), min(pick["z"][1] + 0.12, 1.44))
                seg_s = s + (e - s) * k / n_seg
                seg_e = s + (e - s) * (k + 1) / n_seg
                z0 = min(max(pick["z"][0], 1.0), 1.45)
                z1 = min(max(pick["z"][1], 1.0), 1.45)
                pick["z"] = (z0, z1)
                if pick.get("crop"):
                    pick = dict(pick)
                    pick["z"] = (min(z0, 1.16), min(z1, 1.16))
                shots.append(dict(**pick, start=round(seg_s, 3), end=round(seg_e, 3),
                                  line=i + 1, seg=k + 1))
    # loop tail: starts exactly when the last VO line ends (no overlap -> no concat drift)
    # and lands on the hook framing (zoom 1.006 / pan 0) so frame 45.0s == frame 0.03s
    loop_start = round(lines[-1]["end"], 3)
    shots.append(dict(img="s01_hook_earth.png", z=(1.020, 1.006), pan=(0.0, 0.0),
                      grade=dict(c=1.10, s=1.16, b=0.01, g=1.0, vig=7.0),
                      start=loop_start, end=DURATION, line=20, seg=2))
    shots[0]["start"] = 0.0
    for i in range(len(shots) - 1):
        shots[i]["end"] = max(shots[i]["end"], shots[i]["start"] + 0.4)
    total = sum(sh["end"] - sh["start"] for sh in shots)
    print(f"  shot sum = {total:.3f}s (target {DURATION:.3f}s, drift {total - DURATION:+.3f}s)")

    cards = []
    for cid, text, sub, at_line, off, dur, y, size, color in CARDS:
        base = lines[at_line - 1]["start"] if at_line <= len(lines) else 0.0
        start = max(0.0, base + off)
        cards.append(dict(id=cid, text=text, sub=sub, start=round(start, 3),
                          end=round(min(start + dur, DURATION), 3), y=y, size=size, color=color))
    flashes = []
    for line_no, off in ((6, 0.12), (13, 0.06), (15, 0.02)):
        base = lines[line_no - 1]["start"]
        flashes.append(dict(start=round(base + off, 3), end=round(base + off + 0.07, 3), alpha=170))

    cues = []
    for name, line_no, off, vol in CUES:
        base = lines[line_no - 1]["start"] if line_no <= len(lines) else 0.0
        cues.append(dict(sfx=name, at=round(max(0.0, base + off), 3), vol=vol))

    tl = dict(duration=DURATION, fps=FPS, mode=mode, vo=dict(path=vo_used, lines=lines, duration=round(vo_dur, 3)),
              shots=shots, cards=cards, flashes=flashes, cues=cues)
    json.dump(tl, open(os.path.join(WORK, "timeline.json"), "w"), indent=1)
    print(f"timeline [{mode}]: {len(shots)} shots · {len(cards)} cards · {len(cues)} sfx · vo={vo_dur:.2f}s")
    if mode == "real":
        print(f"  VO ends at {lines[-1]['end']:.2f}s (target hook+loop <= {DURATION}s)")
    return tl


# ---------------------------------------------------------------------- shots
def zexpr(z0, z1, frames):
    return f"{z0}+({z1}-{z0})*on/{max(frames - 1, 1)}"


def pan_expr(axis, p0, p1, frames, shake):
    base = f"(i{'w' if axis == 'x' else 'h'}-i{'w' if axis == 'x' else 'h'}/zoom)/2"
    p = f"({p0}+({p1}-{p0})*on/{max(frames - 1, 1)})"
    jitter = f"+{shake}*sin(on*1.7)" if shake else ""
    return f"{base}*(1+{p}){jitter}"


def render_shots(tl, crf=21, limit=None):
    ff = ffmpeg()
    if os.path.isdir(CLIPS):
        shutil.rmtree(CLIPS)
    os.makedirs(CLIPS, exist_ok=True)
    shots = tl["shots"] if not limit else tl["shots"][:limit]
    for i, sh in enumerate(shots):
        img = os.path.join(IMG, sh["img"])
        if not os.path.exists(img):
            fallback = os.path.join(IMG, "s01_hook_earth.png")
            print(f"  ! missing {sh['img']} -> using {os.path.basename(fallback)}")
            img = fallback
        dur = max(sh["end"] - sh["start"], 0.3)
        frames = int(round(dur * FPS))
        g = sh["grade"]
        crop = sh.get("crop")
        pre = [f"scale={UP_W}:{UP_H}:force_original_aspect_ratio=increase:flags=lanczos",
               f"crop={UP_W}:{UP_H}"]
        if crop == "top":
            pre = [f"scale={UP_W}:{UP_H}:force_original_aspect_ratio=increase:flags=lanczos",
                   f"crop={UP_W}:{int(UP_H*0.88)}:0:0", f"scale={UP_W}:{UP_H}:flags=lanczos"]
        elif crop == "bottom":
            pre = [f"scale={UP_W}:{UP_H}:force_original_aspect_ratio=increase:flags=lanczos",
                   f"crop={UP_W}:{int(UP_H*0.88)}:0:{UP_H-int(UP_H*0.88)}", f"scale={UP_W}:{UP_H}:flags=lanczos"]
        vf = (",".join(pre) +
              f",zoompan=z='{zexpr(sh['z'][0], sh['z'][1], frames)}'"
              f":x='{pan_expr('x', sh['pan'][0], sh['pan'][1], frames, sh.get('shake', 0))}'"
              f":y='{pan_expr('y', 0.0, 0.0, frames, sh.get('shake', 0))}'"
              f":d=1:s={W}x{H}:fps={FPS}"
              f",eq=contrast={g['c']}:saturation={g['s']}:brightness={g['b']}:gamma={g['g']}"
              f",colorbalance=rs={g.get('rs',0)}:gs={g.get('gs',0)}:bs={g.get('bs',0)}"
              f",unsharp=5:5:0.55:5:5:0.0,vignette=PI/{g['vig']}"
              f",noise=alls=6:allf=t+u"
              f",format=yuv420p")
        out = os.path.join(CLIPS, f"shot_{i:02d}.mp4")
        run([ff, "-y", "-hide_banner", "-loglevel", "error", "-framerate", "30", "-loop", "1", "-t", f"{dur:.3f}", "-i", img,
             "-vf", vf, "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
             "-pix_fmt", "yuv420p", "-an", out])
        print(f"  shot_{i:02d} {sh['img'][:26]:<28} {sh['start']:6.2f}-{sh['end']:6.2f}s  z{sh['z']}")
    return len(shots)


def concat_shots():
    ff = ffmpeg()
    files = sorted(f for f in os.listdir(CLIPS) if f.startswith("shot_") and f.endswith(".mp4"))
    lst = os.path.join(WORK, "clips.txt")
    with open(lst, "w") as fh:
        for f in files:
            fh.write(f"file '{os.path.join(CLIPS, f)}'\n")
    out = os.path.join(WORK, "base.mp4")
    run([ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
         "-c", "copy", out])
    print(f"concat: {len(files)} clips -> {out}")
    return out


# ------------------------------------------------------------------ final mix
def final_mix(tl, base, audio_out="GOOGLE_AI_IN_SPACE_1080x1920_45s.mp4"):
    """Caption overlay + VO + ducked music + full-level SFX -> YouTube-normalised master."""
    ff = ffmpeg()
    os.makedirs(OUT_DIR, exist_ok=True)
    overlay = os.path.join(WORK, "captions_overlay.mov")
    vo = tl["vo"]["path"]
    if vo.endswith(".mp3"):
        vo_wav = os.path.join(WORK, "vo.wav")
        run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", vo, "-ar", "48000", "-ac", "2", vo_wav])
        vo = vo_wav
    music = os.path.join(ASSETS, "audio", "music_bed.wav")

    ins = ["-i", base, "-i", overlay, "-i", vo, "-i", music]
    cue_map = {}
    for c in tl["cues"]:
        p = os.path.join(SFX, f"{c['sfx']}.wav")
        cue_map.setdefault(p, []).append(c)
    for p in cue_map:
        ins += ["-i", p]

    A = "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    MUSIC_LEVEL = 0.15        # bed sits ~10 dB under the voice, then ducks further
    SFX_TRIM = 0.85
    fc = []
    # ---- picture: burn the overlay
    fc.append("[0:v]format=yuv420p[base]")
    fc.append("[1:v]format=yuva420p[ov]")
    fc.append("[base][ov]overlay=0:0:format=auto:alpha=straight,format=yuv420p[vout]")
    # ---- voice: cleanup + presence, then split (one copy drives the duck)
    fc.append(f"[2:a]{A},highpass=f=85,acompressor=threshold=-18dB:ratio=3:attack=6:release=180:makeup=2,"
              f"volume=1.25[a_vo]")
    fc.append("[a_vo]asplit=2[vo_main][vo_sc]")
    # ---- music: EQ out the muddy band under the voice, then duck with the voice sidechain
    fc.append(f"[3:a]{A},highpass=f=38,equalizer=f=250:t=q:w=1:g=-2,volume={MUSIC_LEVEL},"
              f"atrim=0:{tl['duration']},asetpts=N/SR/TB[music]")
    fc.append("[music][vo_sc]sidechaincompress=threshold=0.06:ratio=5:attack=10:release=350:makeup=1[musicd]")
    # ---- sfx: added AFTER the duck so hits keep their punch
    sfx_labels = ""
    for idx, (p, cues) in enumerate(cue_map.items(), start=4):
        parts = []
        for k, c in enumerate(cues):
            delay = int(round(c["at"] * 1000))
            parts.append(f"[{idx}:a]{A},volume={c['vol'] * SFX_TRIM:.3f},adelay={delay}|{delay}[sx{idx}_{k}]")
        fc += parts
        labels = "".join(f"[sx{idx}_{k}]" for k in range(len(cues)))
        if len(cues) == 1:
            fc.append(f"[sx{idx}_0]acopy[sfxgrp{idx}]")
        else:
            fc.append(f"{labels}amix=inputs={len(cues)}:normalize=0:dropout_transition=0[sfxgrp{idx}]")
        sfx_labels += f"[sfxgrp{idx}]"
    fc.append(f"[musicd]{sfx_labels}amix=inputs={1 + len(cue_map)}:normalize=0:dropout_transition=0[bed]")
    # ---- master: voice on top, limit, then YouTube loudness target
    fc.append("[vo_main][bed]amix=inputs=2:normalize=0:dropout_transition=0[mixed]")
    fc.append("[mixed]alimiter=limit=0.95:level=disabled,loudnorm=I=-14:TP=-1.3:LRA=9[aout]")

    out = os.path.join(OUT_DIR, audio_out)
    cmd = [ff, "-y", "-hide_banner", "-loglevel", "error"] + ins + [
        "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-profile:v", "high", "-level", "4.2",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-g", str(FPS * 2), "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-t", str(tl["duration"]), out]
    run(cmd)
    print("FINAL ->", out)
    return out


def main():
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("timeline", "all"):
        tl = build_timeline()
    else:
        tl = json.load(open(os.path.join(WORK, "timeline.json")))
    if step in ("shots", "all"):
        render_shots(tl)
    if step in ("concat", "all"):
        base = concat_shots()
    else:
        base = os.path.join(WORK, "base.mp4")
    if step in ("mix", "all"):
        final_mix(tl, base)


if __name__ == "__main__":
    main()
