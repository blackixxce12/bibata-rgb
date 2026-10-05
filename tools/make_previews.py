#!/usr/bin/env python3
"""Render docs/cursors.gif (cursors animating) and docs/borders.gif (an illustration of the
turning rainbow border) from the built theme in build/Bibata-RGB."""
import math
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

here = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(here))
import generate  # noqa: E402

theme = here / "build/Bibata-RGB/hyprcursors"
SHAPES = ["left_ptr", "hand2", "xterm", "grabbing", "wait", "left_ptr_watch",
          "crossed_circle", "top_left_corner", "fd_double_arrow", "zoom-in"]
SIZE, PAD, STEP_MS, CYCLE_MS = 64, 14, 60, generate.DEFAULT_CYCLE_MS


def load(name):
    with zipfile.ZipFile(theme / f"{name}.hlc") as z:
        _, frames, _ = generate.parse_meta(z.read("meta.hl").decode())
        return [(z.read(f).decode(), delay) for _, f, delay in frames]


def frame_at(frames, t):
    total = sum(d for _, d in frames)
    t %= total
    for svg, d in frames:
        if t < d:
            return svg
        t -= d
    return frames[-1][0]


def cursors_gif(out):
    shapes = {n: load(n) for n in SHAPES}
    cache = {}
    w = len(SHAPES) * (SIZE + PAD) + PAD
    h = 2 * (SIZE + PAD) + PAD
    frames = []
    for t in range(0, CYCLE_MS, STEP_MS):
        img = Image.new("RGB", (w, h), (36, 36, 42))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, w, h // 2], fill=(236, 236, 240))
        for i, n in enumerate(SHAPES):
            svg = frame_at(shapes[n], t)
            if svg not in cache:
                cache[svg] = Image.frombuffer("RGBA", (SIZE, SIZE), generate.render_argb(svg, SIZE), "raw", "BGRa", 0, 1)
            cur = cache[svg]
            x = PAD + i * (SIZE + PAD)
            img.paste(cur, (x, PAD // 2 + 4), cur)
            img.paste(cur, (x, h // 2 + PAD // 2 + 4), cur)
        frames.append(img.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG))
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=STEP_MS, loop=0, optimize=True)


RAINBOW = [(0xff, 0x17, 0x44), (0xff, 0x91, 0x00), (0xff, 0xea, 0x00), (0x00, 0xe6, 0x76),
           (0x00, 0xe5, 0xff), (0x29, 0x79, 0xff), (0xd5, 0x00, 0xf9), (0xff, 0x17, 0x44)]


def gradient_color(p):
    p = min(max(p, 0.0), 1.0) * (len(RAINBOW) - 1)
    i = min(int(p), len(RAINBOW) - 2)
    f = p - i
    a, b = RAINBOW[i], RAINBOW[i + 1]
    return tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3))


def borders_gif(out, w=360, h=220, border=5, radius=16, steps=40):
    """Hyprland draws a linear gradient across the window box at an angle that keeps turning."""
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    inner = Image.new("L", (w, h), 0)
    ImageDraw.Draw(inner).rounded_rectangle([border, border, w - 1 - border, h - 1 - border],
                                            radius=radius - border, fill=255)
    frames = []
    for s in range(steps):
        ang = math.radians(45) + 2 * math.pi * s / steps
        dx, dy = math.cos(ang), math.sin(ang)
        half = (abs(dx) * w + abs(dy) * h) / 2
        grad = Image.new("RGB", (w, h))
        px = grad.load()
        for y in range(h):
            for x in range(w):
                proj = (x - w / 2) * dx + (y - h / 2) * dy
                px[x, y] = gradient_color((proj + half) / (2 * half))
        img = Image.new("RGB", (w + 40, h + 40), (24, 24, 30))
        win = Image.new("RGB", (w, h), (40, 42, 54))
        win.paste(grad, (0, 0), Image.eval(Image.composite(Image.new("L", (w, h), 0), mask, inner), lambda v: v))
        img.paste(win, (20, 20), mask)
        frames.append(img.quantize(colors=255, method=Image.Quantize.MEDIANCUT))
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=5000 // steps, loop=0, optimize=True)


if __name__ == "__main__":
    if not theme.is_dir():
        sys.exit(f"{theme} not found: build the theme first (python3 generate.py)")
    cursors_gif(here / "docs/cursors.gif")
    borders_gif(here / "docs/borders.gif")
    print("wrote docs/cursors.gif and docs/borders.gif")
