#!/usr/bin/env python3
"""
make_cover.py — 1080x1920 cover frame (YouTube Shorts custom cover / Reel cover).
Uses the hook visual with the same grade as the video + high-contrast title text.
Output: output/cover_frame.jpg
"""
import os, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
IMG = os.path.join(ROOT, "assets", "img")
OUT = os.path.join(ROOT, "output")
FONT = os.path.join(ROOT, "assets", "fonts", "Anton-Regular.ttf")
W, H = 1080, 1920


def fit(src, w, h):
    im = Image.open(src).convert("RGB")
    s = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * s + 0.5), int(im.height * s + 0.5)), Image.LANCZOS)
    x = (im.width - w) // 2
    y = (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def main():
    os.makedirs(OUT, exist_ok=True)
    base = fit(os.path.join(IMG, "s01_hook_earth.png"), W, H)
    # match the video's grade
    base = ImageEnhance.Contrast(base).enhance(1.10)
    base = ImageEnhance.Color(base).enhance(1.16)
    base = ImageEnhance.Brightness(base).enhance(1.02)
    # vignette
    vig = Image.new("L", (W, H), 0)
    dv = ImageDraw.Draw(vig)
    dv.ellipse((-W * 0.35, -H * 0.25, W * 1.35, H * 1.25), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(180))
    base = Image.composite(base, ImageEnhance.Brightness(base).enhance(0.45), vig)

    d = ImageDraw.Draw(base)
    f1 = ImageFont.truetype(FONT, 172)
    f2 = ImageFont.truetype(FONT, 118)
    fs = 52

    def fitted(s, size, max_w=980):
        f = ImageFont.truetype(FONT, size)
        while size > 24 and d.textbbox((0, 0), s, font=f)[2] > max_w:
            size -= 4
            f = ImageFont.truetype(FONT, size)
        return f

    def txt(y, s, f, fill=(255, 255, 255), stroke=14, max_w=980):
        if isinstance(f, int):
            f = fitted(s, f, max_w)
        d.text((W / 2 + 7, y + 9), s, font=f, fill=(0, 0, 0), anchor="mm")
        d.text((W / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0), anchor="mm")

    txt(330, "GOOGLE AI", 168, max_w=900)
    txt(492, "IS IN SPACE?!", 168, fill=(255, 226, 0), max_w=980)
    txt(645, "4 CHIPS · 1 SATELLITE · 15 MINUTES", 96, max_w=1000)
    txt(740, "PROJECT SUNCATCHER · OCT 2026", 52, fill=(190, 235, 255), max_w=900)

    out = os.path.join(OUT, "cover_frame.jpg")
    base.save(out, quality=92, subsampling=1)
    print("cover ->", out, base.size)
    return out


if __name__ == "__main__":
    main()
