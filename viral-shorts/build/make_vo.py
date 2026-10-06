#!/usr/bin/env python3
"""
make_vo.py — builds the final voice track from the 6 recorded groups:

  1. decode + trim each group
  2. detect per-sentence speech runs (RMS activity)
  3. map sentences -> script lines (with automatic run split/merge to match)
  4. re-assemble with tightened pauses (max_gap) so the read keeps its punch
  5. uniform atempo fit to the 45s runtime (pitch-preserving)
  6. emit word-level timings that exactly match the assembled audio

Outputs: assets/audio/vo/vo_full.wav, work/vo_lines.json
"""
import os, json, re, subprocess, sys
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
VO_DIR = os.path.join(ROOT, "assets", "audio", "vo")
WORK = os.path.join(ROOT, "work")
SR = 48000
DURATION = 45.0
PRE_ROLL = 0.15
TAIL = 0.40
MAX_GAP = 0.13          # pauses longer than this get tightened
GROUP_GAP = 0.10        # pause between recorded groups
MAX_ATEMPO = 1.42       # hard ceiling on the speed-up

sys.path.insert(0, HERE)
from video_build import LINES, ffmpeg

GROUPS = [("g1", 1, 2), ("g2", 3, 5), ("g3", 6, 9), ("g4", 10, 12), ("g5", 13, 17), ("g6", 18, 19)]


def decode(path):
    ff = ffmpeg()
    out = path + ".tmp.wav"
    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", path,
                    "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", out], check=True)
    x, _ = sf.read(out, dtype="float32")
    os.remove(out)
    return x


def speech_runs(x, sr=SR, min_run=0.06, merge_gap=0.11, pad=0.02):
    hop = int(0.01 * sr)
    n = len(x) // hop
    if n == 0:
        return []
    fr = x[:n * hop].reshape(n, hop)
    rms = np.sqrt(np.mean(fr ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12)
    thr = max(-42.0, np.percentile(db, 92) - 30.0)
    act = db > thr
    runs, i = [], 0
    while i < n:
        if act[i]:
            j = i
            while j + 1 < n and (act[j + 1] or (j + 2 < n and act[j + 2])):
                j += 1
            runs.append([i * hop / sr, (j + 1) * hop / sr])
            i = j + 1
        else:
            i += 1
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] < merge_gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    merged = [m for m in merged if m[1] - m[0] >= min_run]
    return [[max(0.0, a - pad), b + pad] for a, b in merged]


def sentences(text):
    """Split a script line into spoken sentences (keeps '...' and '?' as boundaries)."""
    parts = re.split(r'(?<=[.?!])\s+', text.strip())
    return [p for p in parts if p.strip()]


def fit_runs(runs, count):
    """Force `runs` to have exactly `count` entries by splitting/merging sensibly."""
    runs = [list(r) for r in runs]
    while len(runs) > count:
        # merge the pair with the smallest gap
        gaps = [runs[i + 1][0] - runs[i][1] for i in range(len(runs) - 1)]
        i = int(np.argmin(gaps))
        runs[i] = [runs[i][0], runs[i + 1][1]]
        del runs[i + 1]
    while len(runs) < count:
        # split the longest run in half (weighted by its length)
        lens = [r[1] - r[0] for r in runs]
        i = int(np.argmax(lens))
        mid = runs[i][0] + lens[i] * 0.5
        a, b = runs[i]
        runs[i] = [a, mid]
        runs.insert(i + 1, [mid, b])
    return runs


def word_times(text, start, end):
    words = text.split()
    if not words:
        return []
    wts = np.array([max(len(w), 2) + 1.5 for w in words], dtype=float)
    wts /= wts.sum()
    cuts = np.concatenate([[0], np.cumsum(wts)])
    return [dict(w=w, s=round(start + (end - start) * cuts[j], 3),
                 e=round(start + (end - start) * cuts[j + 1], 3)) for j, w in enumerate(words)]


def main():
    os.makedirs(WORK, exist_ok=True)
    seg_src, seg_old = [], []      # kept audio pieces and their old/new start times
    line_old = []                  # (line_index, old_start, old_end)
    new_pos = 0.0
    first = True

    for name, a, b in GROUPS:
        x = decode(os.path.join(VO_DIR, f"{name}.mp3"))
        runs = speech_runs(x)
        if not runs:
            raise SystemExit(f"no speech found in {name}")
        # trim leading/trailing silence
        x = x[int(max(0, runs[0][0] - 0.02) * SR): int(min(len(x) / SR, runs[-1][1] + 0.04) * SR)]
        runs = [[r[0] - max(0, runs[0][0] - 0.02), r[1] - max(0, runs[0][0] - 0.02)] for r in runs]

        # sentences of the lines in this group
        sents = []
        for k in range(a, b + 1):
            for s in sentences(LINES[k - 1][0]):
                sents.append((k, s))
        runs = fit_runs(runs, len(sents))
        print(f"{name}: {len(sents)} sentences, {len(runs)} runs, speech {sum(r[1]-r[0] for r in runs):.2f}s, "
              f"clip {len(x)/SR:.2f}s")

        # piecewise time map: old sentence times -> new tightened times
        for s_i, (line_no, s_txt) in enumerate(sents):
            o_s, o_e = runs[s_i]
            seg_old.append((o_s, o_e))
            seg_src.append((x, o_s, o_e))
        for s_i, (line_no, s_txt) in enumerate(sents):
            o_s, o_e = runs[s_i]
            n_s = new_pos
            n_e = new_pos + (o_e - o_s)
            line_old.append((line_no, s_i, n_s, n_e))
            new_pos = n_e + (GROUP_GAP if s_i == len(sents) - 1 else MAX_GAP)
        # remove the group gap after the last sentence of the last group
    # ---- assemble the tightened track
    total_new = sum(o_e - o_s for (o_s, o_e) in seg_old) + MAX_GAP * (len(seg_old) - len(GROUPS)) \
        + GROUP_GAP * (len(GROUPS) - 1) + 0.2
    n = int((total_new + 1.0) * SR)
    track = np.zeros(n, dtype=np.float32)
    pos = 0.0
    s_i = 0
    for g_i, (name, a, b) in enumerate(GROUPS):
        nsents = sum(len(sentences(LINES[k - 1][0])) for k in range(a, b + 1))
        for k in range(nsents):
            x, o_s, o_e = seg_src[s_i]
            piece = x[int(o_s * SR):int(o_e * SR)]
            st = int(pos * SR)
            track[st:st + len(piece)] += piece
            pos += len(piece) / SR
            s_i += 1
            if k < nsents - 1:
                pos += MAX_GAP / (1.0)
        if g_i < len(GROUPS) - 1:
            pos += GROUP_GAP
        else:
            pos -= GROUP_GAP
    assembled_end = pos

    # ---- uniform atempo fit
    target_end = DURATION - TAIL
    atempo = 1.0
    if assembled_end > target_end - PRE_ROLL:
        atempo = min(MAX_ATEMPO, assembled_end / (target_end - PRE_ROLL))
    print(f"\nassembled VO (pauses tightened): {assembled_end:.2f}s -> target {target_end - PRE_ROLL:.2f}s "
          f"| atempo {atempo:.3f} ({'net speed-up on speech' if atempo > 1 else 'unchanged'})")

    if abs(atempo - 1.0) > 1e-4:
        idx = np.arange(int(len(track) / atempo)) * atempo
        track = np.interp(idx, np.arange(len(track)), track).astype(np.float32)
    # place at pre-roll and normalise
    out = np.zeros(int(DURATION * SR) + SR, dtype=np.float32)
    st = int(PRE_ROLL * SR)
    out[st:st + len(track)] += track
    pk = float(np.max(np.abs(out))) + 1e-9
    out = out / pk * 0.72
    sf.write(os.path.join(VO_DIR, "vo_full.wav"), np.stack([out, out], axis=-1), SR, subtype="PCM_16")

    # ---- final word timings (times in the assembled track, after atempo)
    lines = []
    per_line = {}
    for line_no, s_i, n_s, n_e in line_old:
        per_line.setdefault(line_no, []).append((n_s, n_e))
    for k in range(1, len(LINES) + 1):
        if k not in per_line:
            continue
        spans = per_line[k]
        s = PRE_ROLL + spans[0][0] / atempo
        e = PRE_ROLL + spans[-1][1] / atempo
        txt = LINES[k - 1][0]
        # word times: distribute across the line's total span, proportional to characters
        lines.append(dict(text=txt, start=round(s, 3), end=round(e, 3), words=word_times(txt, s, e)))

    end = max(l["end"] for l in lines)
    json.dump(dict(vo_path=os.path.join(VO_DIR, "vo_full.wav"), vo_end=round(end, 3),
                   atempo=round(atempo, 4), lines=lines),
              open(os.path.join(WORK, "vo_lines.json"), "w"), indent=1)
    print(f"VO -> assets/audio/vo/vo_full.wav | lines: {len(lines)} | last line ends {end:.2f}s "
          f"| loop headroom {DURATION - end:.2f}s")
    for i, l in enumerate(lines, 1):
        print(f"  {i:2d} {l['start']:6.2f}-{l['end']:6.2f}  {l['text'][:58]}")


if __name__ == "__main__":
    main()
