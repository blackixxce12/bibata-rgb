#!/usr/bin/env python3
"""Contact sheet of the built XCursor theme: every shape at 4 animation phases, on light and
dark backgrounds.

usage: preview.py [theme dir] [output png] [size]   (default build/Bibata-RGB, build/preview.png, 64)
"""
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw

here = Path(__file__).resolve().parent
theme = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "build/Bibata-RGB"
out = Path(sys.argv[2]) if len(sys.argv) > 2 else here / "build/preview.png"
size = int(sys.argv[3]) if len(sys.argv) > 3 else 64
COLS, PHASES = 8, 4


def frames(path, nominal):
    """All images of one nominal size from an XCursor file, in animation order."""
    data = path.read_bytes()
    ntoc = struct.unpack_from("<I", data, 12)[0]
    images = []
    for i in range(ntoc):
        _, subtype, pos = struct.unpack_from("<III", data, 16 + i * 12)
        if subtype != nominal:
            continue
        _, _, _, _, w, h, _, _, _ = struct.unpack_from("<9I", data, pos)
        pixels = data[pos + 36: pos + 36 + w * h * 4]
        images.append(Image.frombuffer("RGBA", (w, h), pixels, "raw", "BGRa", 0, 1))
    return images


if not (theme / "cursors").is_dir():
    sys.exit(f"{theme}/cursors not found: build the theme first (python3 generate.py)")
names = sorted(p.name for p in (theme / "cursors").iterdir() if not p.is_symlink())
cell = size + 12
rows = (len(names) + COLS - 1) // COLS
sheet = Image.new("RGB", (COLS * PHASES * cell, rows * cell * 2), (240, 240, 240))
draw = ImageDraw.Draw(sheet)
for idx, name in enumerate(names):
    images = frames(theme / "cursors" / name, size)
    if not images:
        sys.exit(f"{name} has no {size} px images; the built sizes are in {theme}/BUILD-INFO (xcursor_sizes)")
    r, c = divmod(idx, COLS)
    for p in range(PHASES):
        img = images[len(images) * p // PHASES]
        for band, bg in enumerate([(235, 235, 235), (30, 30, 34)]):
            x, y = (c * PHASES + p) * cell, (r * 2 + band) * cell
            draw.rectangle([x, y, x + cell - 1, y + cell - 1], fill=bg)
            sheet.paste(img, (x + 6, y + 6), img)
out.parent.mkdir(parents=True, exist_ok=True)
sheet.save(out)
print(out, sheet.size, len(names), "shapes")
