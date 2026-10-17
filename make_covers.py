#!/usr/bin/env python3
"""Make extra Gumroad cover images for CLIENT MACHINE from real product frames.

Each cover is 1280x720 (same as the existing covers): a headline on the left
and a real page from the product (taken from the Demo ad video) on the right.
Output: assets/gumroad_covers/cover_N_<name>.png

  python make_covers.py
"""

import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
VIDEO = ROOT / "assets/creative_backup/CM_Ad3_Demo_FINAL_4x5.mp4"
OUT = ROOT / "assets/gumroad_covers"
FONT = "/usr/share/fonts/opentype/inter/Inter-{}.otf"
W, H = 1280, 720
NAVY_TOP, NAVY_BOTTOM = (13, 27, 58), (6, 14, 32)
BLUE = (47, 128, 255)
WHITE = (255, 255, 255)
MUTED = (178, 192, 220)

# (file name, video time, crop box in the 1080x1350 frame, label, headline, points)
COVERS = [
    ("1_30_day_plan", 8.5, (40, 130, 1040, 1350), "THE PLAN",
     "A day-by-day\n30-day plan",
     ["One action a day, in order", "Offer, portfolio, prospects,\noutreach, follow-up", "You always know what to do next"]),
    ("2_prospect_tracker", 15.5, (40, 130, 1040, 1350), "THE TRACKER",
     "See who to follow\nup today",
     ["Prospect Tracker spreadsheet (.xlsx)", "Pipeline, follow-up queue\nand activity log", "Dashboard updates automatically"]),
    ("3_whats_inside", 2.5, (110, 260, 950, 1350), "WHAT'S INSIDE",
     "10 workbooks.\n192 pages.",
     ["Offer, Pricing and Portfolio builders", "Outreach Script Library", "Sales, Proposal, Onboarding\nand Delivery kits"]),
    ("4_scripts_templates", 17.5, (40, 130, 1040, 1350), "READY TO USE",
     "Scripts and\ntemplates",
     ["Outreach scripts you adapt,\nnot copy-paste spam", "Proposal + onboarding templates", "2 editable Canva templates\n(free Canva account)"]),
]


def frame(t):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "f.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(VIDEO),
                        "-frames:v", "1", str(p)], check=True)
        return Image.open(p).convert("RGB")


def background():
    bg = Image.new("RGB", (W, H))
    px = bg.load()
    for y in range(H):
        f = y / (H - 1)
        c = tuple(int(NAVY_TOP[i] * (1 - f) + NAVY_BOTTOM[i] * f) for i in range(3))
        for x in range(W):
            px[x, y] = c
    # faint grid, like the ad videos
    d = ImageDraw.Draw(bg)
    for x in range(0, W, 48):
        d.line([(x, 0), (x, H)], fill=(20, 38, 76), width=1)
    for y in range(0, H, 48):
        d.line([(0, y), (W, y)], fill=(20, 38, 76), width=1)
    return bg


def paste_card(bg, img, box):
    """Paste img inside box (x0,y0,x1,y1) keeping aspect, with rounded corners and shadow."""
    x0, y0, x1, y1 = box
    scale = min((x1 - x0) / img.width, (y1 - y0) / img.height)
    img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    x = x0 + ((x1 - x0) - img.width) // 2
    y = y0 + ((y1 - y0) - img.height) // 2
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.width - 1, img.height - 1], 18, fill=255)
    shadow = Image.new("RGBA", (img.width + 80, img.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([40, 52, img.width + 40, img.height + 52], 22,
                                             fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    bg.paste(shadow, (x - 40, y - 40), shadow)
    bg.paste(img, (x, y), mask)


def text_block(d, x, y, text, font, fill, spacing=10):
    d.multiline_text((x, y), text, font=font, fill=fill, spacing=spacing)
    return d.multiline_textbbox((x, y), text, font=font, spacing=spacing)[3]


def make(name, t, crop, label, headline, points):
    bg = background()
    paste_card(bg, frame(t).crop(crop), (700, 50, 1230, 670))
    d = ImageDraw.Draw(bg)
    f_brand = ImageFont.truetype(FONT.format("Bold"), 22)
    f_label = ImageFont.truetype(FONT.format("Bold"), 20)
    f_head = ImageFont.truetype(FONT.format("ExtraBold"), 62)
    f_point = ImageFont.truetype(FONT.format("Medium"), 25)
    x = 72
    d.text((x, 64), "CLIENT", font=f_brand, fill=BLUE)
    d.text((x + d.textlength("CLIENT ", font=f_brand), 64), "MACHINE", font=f_brand, fill=WHITE)
    # label pill
    lw = d.textlength(label, font=f_label)
    d.rounded_rectangle([x, 128, x + lw + 32, 166], 19, fill=BLUE)
    d.text((x + 16, 135), label, font=f_label, fill=WHITE)
    y = text_block(d, x, 190, headline, f_head, WHITE, spacing=6) + 36
    for p in points:
        d.ellipse([x, y + 9, x + 14, y + 23], fill=BLUE)
        y = text_block(d, x + 30, y, p, f_point, MUTED, spacing=6) + 20
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"cover_{name}.png"
    bg.save(path, optimize=True)
    return path


if __name__ == "__main__":
    for c in COVERS:
        print(make(*c).relative_to(ROOT))
