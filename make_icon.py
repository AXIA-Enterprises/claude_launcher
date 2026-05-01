"""Generate Claude Launcher app icon (.icns).

Run: python make_icon.py — produces AppIcon.icns alongside this script.
"""

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = Path(__file__).resolve().parent
ICONSET = OUT_DIR / "AppIcon.iconset"
ICNS = OUT_DIR / "AppIcon.icns"

ACCENT_TOP = (107, 184, 232)   # #6BB8E8
ACCENT_BOT = (46, 139, 209)    # #2E8BD1
WHITE = (255, 255, 255)

SIZE = 1024
RADIUS = 230


def gradient_bg(size: int) -> Image.Image:
    img = Image.new("RGB", (size, size), ACCENT_TOP)
    px = img.load()
    for y in range(size):
        t = y / (size - 1)
        r = int(ACCENT_TOP[0] * (1 - t) + ACCENT_BOT[0] * t)
        g = int(ACCENT_TOP[1] * (1 - t) + ACCENT_BOT[1] * t)
        b = int(ACCENT_TOP[2] * (1 - t) + ACCENT_BOT[2] * t)
        for x in range(size):
            px[x, y] = (r, g, b)
    return img


def rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((0, 0, size, size), radius=radius, fill=255)
    return mask


def find_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except OSError:
                continue
    return ImageFont.load_default()


def build_icon() -> Image.Image:
    bg = gradient_bg(SIZE).convert("RGBA")

    # Soft top highlight
    overlay = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse((-SIZE // 4, -SIZE // 2, SIZE + SIZE // 4, SIZE // 2),
               fill=(255, 255, 255, 38))
    overlay = overlay.filter(ImageFilter.GaussianBlur(40))
    bg = Image.alpha_composite(bg, overlay)

    # Glyph ">_"
    glyph_layer = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
    gd = ImageDraw.Draw(glyph_layer)
    font = find_font(560)
    text = ">_"
    bbox = gd.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (SIZE - tw) // 2 - bbox[0]
    y = (SIZE - th) // 2 - bbox[1] - 20

    shadow = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
    sd = ImageDraw.Draw(shadow)
    sd.text((x, y + 12), text, font=font, fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    glyph_layer = Image.alpha_composite(glyph_layer, shadow)
    gd = ImageDraw.Draw(glyph_layer)
    gd.text((x, y), text, font=font, fill=WHITE + (255,))

    composed = Image.alpha_composite(bg, glyph_layer)

    mask = rounded_mask(SIZE, RADIUS)
    final = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    final.paste(composed, (0, 0), mask)
    return final


def main():
    icon = build_icon()
    if ICONSET.exists():
        shutil.rmtree(ICONSET)
    ICONSET.mkdir()

    specs = [
        (16,   "icon_16x16.png"),
        (32,   "icon_16x16@2x.png"),
        (32,   "icon_32x32.png"),
        (64,   "icon_32x32@2x.png"),
        (128,  "icon_128x128.png"),
        (256,  "icon_128x128@2x.png"),
        (256,  "icon_256x256.png"),
        (512,  "icon_256x256@2x.png"),
        (512,  "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]
    for size, name in specs:
        icon.resize((size, size), Image.LANCZOS).save(
            ICONSET / name, format="PNG")

    subprocess.run(["iconutil", "-c", "icns",
                    str(ICONSET), "-o", str(ICNS)], check=True)
    print(f"Built {ICNS}")


if __name__ == "__main__":
    main()
