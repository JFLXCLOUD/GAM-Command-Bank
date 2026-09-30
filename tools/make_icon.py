"""Regenerate the app icon (assets/icon-*.png, icon.ico and the installer
wizard images in installer/).

The icon is drawn from shapes rather than scaled from a bitmap, so every
size is sharp. Small sizes use a simpler drawing that stays readable.

    pip install pillow
    python tools/make_icon.py
"""
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]

BG_TOP = (47, 129, 247)      # primary blue, matches the app accent
BG_BOTTOM = (31, 111, 235)
FG = (255, 255, 255)


def draw(size):
    s = 4                      # supersample, then downscale for smooth edges
    W = size * s
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))

    # rounded-square background with a vertical gradient
    grad = Image.new("RGBA", (W, W))
    gd = ImageDraw.Draw(grad)
    for y in range(W):
        t = y / (W - 1)
        gd.line([(0, y), (W, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)) + (255,))
    mask = Image.new("L", (W, W), 0)
    radius = W * (0.18 if size >= 32 else 0.14)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, W - 1], radius=radius, fill=255)
    im.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(im)
    u = W / 32                 # design grid: 32 units
    small = size < 32
    cols = 3 if small else 4

    # pediment (roof)
    d.polygon([(4 * u, 11.5 * u), (16 * u, 4 * u), (28 * u, 11.5 * u)], fill=FG)
    if not small:  # cut-out inside the roof
        d.polygon([(9.5 * u, 10.2 * u), (16 * u, 6.3 * u), (22.5 * u, 10.2 * u)], fill=BG_TOP)
    d.rectangle([5 * u, 12.5 * u, 27 * u, 14 * u], fill=FG)          # architrave

    # columns
    left, right, top, bottom = 7 * u, 25 * u, 15.5 * u, 23.5 * u
    cw = (3.2 if small else 2.6) * u
    step = (right - left - cw) / (cols - 1)
    for i in range(cols):
        x = left + i * step
        d.rectangle([x, top, x + cw, bottom], fill=FG)

    # base steps
    d.rectangle([5 * u, 24.5 * u, 27 * u, 26 * u], fill=FG)
    d.rectangle([3.5 * u, 27 * u, 28.5 * u, 28.5 * u], fill=FG)

    return im.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    images = {size: draw(size) for size in SIZES}
    for size in (16, 32, 48, 64, 128, 256):
        images[size].save(os.path.join(ROOT, "assets", f"icon-{size}.png"))
    ico_sizes = [16, 20, 24, 32, 40, 48, 64, 256]
    images[256].save(os.path.join(ROOT, "icon.ico"),
                     sizes=[(s, s) for s in ico_sizes],
                     append_images=[images[s] for s in ico_sizes if s != 256])
    # Inno Setup wizard corner image: BMP without transparency, on the
    # wizard's white background; 55px plus 2x for high-DPI screens.
    for size in (55, 110):
        pad = round(size * 0.06)
        canvas = Image.new("RGB", (size, size), (255, 255, 255))
        icon = draw(size - 2 * pad)
        canvas.paste(icon, (pad, pad), icon)
        canvas.save(os.path.join(ROOT, "installer", f"wizard-small-{size}.bmp"))
    print("wrote icon.ico, assets/icon-*.png and installer/wizard-small-*.bmp")


if __name__ == "__main__":
    main()
