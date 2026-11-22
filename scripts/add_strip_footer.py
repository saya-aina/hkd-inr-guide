#!/usr/bin/env python3
"""Add the nriremit.com copyright band and metadata to a Mumbai Buzurg strip.

Usage: python3 scripts/add_strip_footer.py assets/cartoon-NAME.jpg [...]
Run ONCE per new strip image (it skips files already marked). Then set the
<img> height attribute to the new image height (printed).
"""
import sys, datetime
from PIL import Image, ImageDraw, ImageFont

YEAR = datetime.date.today().year
LINE = f"© {YEAR} nriremit.com  ·  Mumbai Buzurg  ·  Do not copy or reuse without permission"
MARK = f"© {YEAR} nriremit.com"
BAND = 44
FONT = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"

for path in sys.argv[1:]:
    im = Image.open(path)
    if "nriremit.com" in str(im.getexif().get(0x8298, "")):
        print("skip (already marked):", path); continue
    im = im.convert("RGB")
    w, h = im.size
    out = Image.new("RGB", (w, h + BAND), (24, 24, 27))
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    f = ImageFont.truetype(FONT, 17)
    tw = d.textlength(LINE, font=f)
    d.text(((w - tw) / 2, h + (BAND - 17) / 2 - 2), LINE, font=f, fill=(228, 228, 231))
    # faint corner mark on the artwork itself
    ov = Image.new("RGBA", out.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    f2 = ImageFont.truetype(FONT, 15)
    t = "nriremit.com"
    od.text((w - d.textlength(t, font=f2) - 14, h - 28), t, font=f2, fill=(0, 0, 0, 110))
    out = Image.alpha_composite(out.convert("RGBA"), ov).convert("RGB")
    ex = Image.Exif()
    ex[0x8298] = MARK + ". All rights reserved."
    ex[0x013B] = "nriremit.com site owner"
    out.save(path, quality=84, optimize=True, progressive=True, exif=ex)
    print(path, out.size)
