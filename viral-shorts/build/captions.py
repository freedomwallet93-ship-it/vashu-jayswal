#!/usr/bin/env python3
"""
captions.py — renders burned-in captions + text cards + flashes into ONE alpha overlay
.mov (qtrle, 1080x1920, 30fps).

- word-level karaoke captions (Anton, white + heavy black stroke, active word yellow)
- big text cards stacked on top when scheduled
- frame-accurate: every 1/30s frame is composited from whatever is active at that time,
  identical consecutive frames are collapsed into duration runs
- safe-zone aware: cards below y=250, captions above y=1345 (YouTube UI bands)
"""
import os, json, subprocess
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
ASSETS = os.path.join(ROOT, "assets")
OUTDIR = os.path.join(ASSETS, "captions")
WORK = os.path.join(ROOT, "work")
FRAMES = os.path.join(WORK, "ov_frames")
FONT_PATH = os.path.join(ASSETS, "fonts", "Anton-Regular.ttf")
FPS = 30
W, H = 1080, 1920
YELLOW = (255, 226, 0, 255)
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)
CAP_CENTER_Y = 1225     # captions sit at ~64% height (above the bottom UI band)


def find_ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def font(size):
    return ImageFont.truetype(FONT_PATH, size)


def text_size(draw, s, f):
    box = draw.textbbox((0, 0), s, font=f)
    return box[2] - box[0], box[3] - box[1]


def draw_outlined(draw, xy, s, f, fill, stroke=11, anchor="mm", shadow=True):
    x, y = xy
    if shadow:
        draw.text((x + 6, y + 8), s, font=f, fill=(0, 0, 0, 175), anchor=anchor)
    draw.text((x, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=BLACK, anchor=anchor)


def wrap_chunks(words, max_words=3, max_chars=13):
    chunks, cur = [], []
    for w in words:
        cand = cur + [w]
        if len(cand) > max_words or (sum(len(x) for x in cand) + len(cand) - 1 > max_chars):
            if cur:
                chunks.append(cur)
            cur = [w]
        else:
            cur = cand
    if cur:
        chunks.append(cur)
    if len(chunks) >= 2 and len(chunks[-1]) == 1 and len(chunks[-2]) == 3:
        chunks[-1] = [chunks[-2].pop()] + chunks[-1]
    return chunks


def build_caption_track(lines, outdir):
    """Karaoke captions: one PNG per word, showing its chunk with the active word lit."""
    os.makedirs(outdir, exist_ok=True)
    f = font(102)
    events = []
    idx = 0
    for line in lines:
        words = line["words"]
        chunks = wrap_chunks([w["w"] for w in words])
        wi = 0
        for chunk in chunks:
            chunk_words = words[wi:wi + len(chunk)]
            wi += len(chunk)
            for cw in chunk_words:
                img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                d = ImageDraw.Draw(img)
                space, max_w = 32, 1000
                widths = [text_size(d, w["w"].upper(), f)[0] for w in chunk_words]
                one_row = sum(widths) + space * (len(chunk_words) - 1)
                if one_row <= max_w:
                    rows = [list(range(len(chunk_words)))]
                else:
                    best = None
                    for k in range(1, len(chunk_words)):
                        wl = sum(widths[:k]) + space * (k - 1)
                        wr = sum(widths[k:]) + space * (len(chunk_words) - k - 1)
                        if best is None or abs(wl - wr) < best[0]:
                            best = (abs(wl - wr), k)
                    k = best[1] if best else 1
                    rows = [list(range(k)), list(range(k, len(chunk_words)))]
                row_h = 128
                y0 = CAP_CENTER_Y - (len(rows) - 1) * row_h / 2
                for r_i, idxs in enumerate(rows):
                    rw = [widths[i] for i in idxs]
                    total = sum(rw) + space * (len(idxs) - 1)
                    x = W / 2 - total / 2
                    for j, i in enumerate(idxs):
                        wobj = chunk_words[i]
                        fill = YELLOW if wobj is cw else WHITE
                        draw_outlined(d, (x + rw[j] / 2, y0 + r_i * row_h), wobj["w"].upper(), f, fill, stroke=11)
                        x += rw[j] + space
                if cw["e"] > cw["s"]:
                    p = os.path.join(outdir, f"cap_{idx:04d}.png")
                    img.save(p)
                    events.append(dict(png=p, start=cw["s"], end=cw["e"], z=1))
                    idx += 1
    return events


def build_card(text_lines, sub, y, size, color, out, sub_size=62, sub_color=YELLOW):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(size)
    for i, line in enumerate(text_lines):
        draw_outlined(d, (W / 2, y + i * size * 1.06), line.upper(), f, tuple(color), stroke=13)
    if sub:
        sf = font(sub_size)
        draw_outlined(d, (W / 2, y + len(text_lines) * size * 1.06 + 26), sub.upper(), sf, sub_color, stroke=8)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    return dict(png=out, z=2)


def solid_frame(color, out, alpha=255):
    img = Image.new("RGBA", (W, H), tuple(color[:3]) + (int(alpha),))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    return dict(png=out, z=3)


def render_overlay(events, total, out_mov):
    """Composite every frame, collapse identical runs, encode qtrle alpha mov."""
    ff = find_ffmpeg()
    os.makedirs(FRAMES, exist_ok=True)
    for f_ in os.listdir(FRAMES):
        os.remove(os.path.join(FRAMES, f_))
    n_frames = int(round(total * FPS))
    runs = []           # (png_path, frame_count)
    last_key, last_png, count = None, None, 0
    for fi in range(n_frames):
        t = (fi + 0.5) / FPS
        active = sorted([e for e in events if e["start"] <= t < e["end"]], key=lambda e: e["z"])
        key = tuple(e["png"] for e in active)
        if key != last_key:
            if last_png is not None and count > 0:
                runs.append((last_png, count))
            if not active:
                base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            else:
                base = Image.open(active[0]["png"]).convert("RGBA")
                for e in active[1:]:
                    base.alpha_composite(Image.open(e["png"]).convert("RGBA"))
            last_png = os.path.join(FRAMES, f"ov_{len(runs):04d}.png")
            base.save(last_png)
            last_key, count = key, 1
        else:
            count += 1
    if last_png is not None and count > 0:
        runs.append((last_png, count))

    lst = os.path.join(WORK, "overlay_list.txt")
    with open(lst, "w") as fh:
        for png, cnt in runs:
            fh.write(f"file '{png}'\nduration {cnt / FPS:.5f}\n")
        fh.write(f"file '{runs[-1][0]}'\n")
    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-vsync", "vfr", "-pix_fmt", "yuva420p", "-c:v", "qtrle", out_mov], check=True)
    return out_mov, len(runs)


def main():
    tl = json.load(open(os.path.join(WORK, "timeline.json")))
    os.makedirs(OUTDIR, exist_ok=True)
    for f_ in os.listdir(OUTDIR):
        os.remove(os.path.join(OUTDIR, f_))
    events = build_caption_track(tl["vo"]["lines"], OUTDIR)
    for card in tl.get("cards", []):
        ev = build_card(card["text"], card.get("sub"), card.get("y", 430), card.get("size", 140),
                        card.get("color", [255, 255, 255, 255]),
                        os.path.join(OUTDIR, f"card_{card['id']}.png"))
        ev["start"], ev["end"] = card["start"], card["end"]
        events.append(ev)
    for i, fl in enumerate(tl.get("flashes", [])):
        ev = solid_frame((255, 255, 255), os.path.join(OUTDIR, f"flash_{i}.png"), fl.get("alpha", 255))
        ev["start"], ev["end"] = fl["start"], fl["end"]
        events.append(ev)
    out, n_runs = render_overlay(events, tl["duration"], os.path.join(WORK, "captions_overlay.mov"))
    print(f"overlay: {len(events)} elements -> {n_runs} unique frames -> {out}")


if __name__ == "__main__":
    main()
