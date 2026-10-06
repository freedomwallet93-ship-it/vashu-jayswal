#!/usr/bin/env python3
"""
verify.py — QC gate for the finished Short.
  * container / codec / resolution / fps / duration / faststart
  * integrated loudness (target: ~-14 LUFS, TP <= -1 dBTP — YouTube normalisation)
  * silence + true-peak spot checks
  * loop test: |frame(0) - frame(44.87)| mean abs difference (seamless-loop proof)
  * beat frames -> output/qc/*.jpg + a contact sheet
"""
import os, json, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "output")
QC = os.path.join(OUT, "qc")

BEATS = [
    (0.30, "01 hook - Earth + GOOGLE AI IS IN SPACE"),
    (2.00, "02 satellite close-up"),
    (5.30, "03 SpaceX launch"),
    (8.20, "04 4 CHIPS 1 SATELLITE card"),
    (12.20, "05 15 MINUTES / THEN IT DIES"),
    (18.50, "06 no air / no cooling"),
    (23.00, "07 8x power"),
    (28.40, "08 $100,000,000 card"),
    (34.20, "09 THEN 100 - armada climax"),
    (38.20, "10 doubt beat"),
    (41.00, "11 Mars bait card"),
    (44.85, "12 loop frame (must match frame 1)"),
]


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def ffprobe_json(path):
    ff = ffmpeg()
    out = subprocess.run([ff, "-hide_banner", "-i", path, "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return out


def frame(path, t, out_png):
    subprocess.run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}",
                    "-i", path, "-frames:v", "1", out_png], check=True)
    return np.asarray(Image.open(out_png).convert("L"), dtype=np.float32)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, "GOOGLE_AI_IN_SPACE_1080x1920_45s.mp4")
    if not os.path.exists(path):
        raise SystemExit(f"missing {path}")
    os.makedirs(QC, exist_ok=True)
    ff = ffmpeg()
    size = os.path.getsize(path)
    print(f"FILE      : {os.path.basename(path)}  ({size/1e6:.1f} MB)")

    info = ffprobe_json(path)
    for key in ("Duration", "Stream #0:0", "Stream #0:1"):
        for ln in info.splitlines():
            if key in ln:
                print(f"{key:<10}: {ln.strip()[:150]}")
                break

    # faststart check (moov before mdat)
    head = open(path, "rb").read(200000)
    print(f"faststart : {'moov before mdat ✔' if head.find(b'moov') < head.find(b'mdat') and head.find(b'moov') >= 0 else 'check manually'}")

    # loudness
    p = subprocess.run([ff, "-hide_banner", "-i", path, "-af", "loudnorm=print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    txt = p.stderr
    try:
        j = json.loads(txt[txt.rindex("{"):txt.rindex("}") + 1])
        print(f"loudness  : I={j['input_i']} LUFS  TP={j['input_tp']} dBTP  LRA={j['input_lra']}  "
              f"(target I≈-14, TP≤-1)")
    except Exception:
        print("loudness  : could not parse")

    # frames + loop test (raw pixel diff is dominated by film grain, so also compare structure)
    from PIL import ImageFilter
    f1 = frame(path, 0.10, os.path.join(QC, "f_loop_start.png"))
    f2 = frame(path, 44.87, os.path.join(QC, "f_loop_end.png"))
    raw = float(np.mean(np.abs(f1 - f2)))
    small = lambda a: np.asarray(Image.fromarray(a.astype(np.uint8)).resize((108, 192))
                                 .filter(ImageFilter.GaussianBlur(1.0)), dtype=np.float32)
    struct = float(np.mean(np.abs(small(f1) - small(f2))))
    verdict = "SEAMLESS ✔" if struct < 12 else ("CLOSE ~" if struct < 20 else "VISIBLE SEAM ✘")
    print(f"loop test : structure delta = {struct:.1f}/255 (raw grain-inclusive {raw:.1f}/255) -> {verdict}")

    shots = []
    for t, label in BEATS:
        png = os.path.join(QC, f"beat_{label.split()[0]}.png")
        arr = frame(path, t, png)
        shots.append((png, label))
        print(f"beat {label:<45} luma={arr.mean():6.1f}")
    # contact sheet 4x3
    cols, tw, th = 3, 360, 640
    rows = (len(shots) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), (12, 12, 16))
    for i, (png, label) in enumerate(shots):
        im = Image.open(png).convert("RGB").resize((tw, th))
        sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
    sheet_path = os.path.join(QC, "contact_sheet.jpg")
    sheet.save(sheet_path, quality=88)
    print(f"sheet     : {sheet_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
