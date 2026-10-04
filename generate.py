#!/usr/bin/env python3
"""Build Bibata-RGB: Bibata-Modern-Ice with the white body replaced by a flowing rainbow.

The source is the Bibata-Modern-Ice theme in vendor/ (its hyprcursor archives carry the
original SVGs, its XCursor files the hotspots). Every shape becomes an animation: static shapes
get HYPR_FRAMES / XCUR_FRAMES frames in which a repeating rainbow gradient slides along the
shape, and the animated shapes (wait, left_ptr_watch) keep their own frames with the rainbow
advancing one step per frame.

Output (in --out, default build/Bibata-RGB):
  manifest.hl + hyprcursors/*.hlc   hyprcursor theme (SVG frames, scale-independent)
  cursors/                          XCursor theme for XWayland and GTK3 apps (bitmap frames)
  index.theme, cursor.theme         XCursor metadata, falls back to Bibata-Modern-Ice

Outline (#000000) and fixed colours (badges, the white "X" glyphs) are kept.
"""

import argparse
import os
import re
import shutil
import struct
import subprocess
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cairo
import gi

gi.require_version("Rsvg", "2.0")
from gi.repository import Rsvg  # noqa: E402

THEME_NAME = "Bibata-RGB"
SOURCE_THEME = Path(__file__).resolve().parent / "vendor/Bibata-Modern-Ice"

# One rainbow cycle lasts CYCLE_MS everywhere, so every cursor flows at the same speed.
CYCLE_MS = 2160
HYPR_FRAMES = 36  # 60 ms per frame
XCUR_FRAMES = 24  # 90 ms per frame; XCursor files are raw ARGB, so fewer frames keeps them small
XCUR_SIZES = [24, 32, 40, 48, 64]
# hyprcursor frames are SVG by default: they render at exactly the size Hyprland asks for
# (24 x the highest monitor scale). Each load renders all ~2050 frames, ~0.5 s, paid when
# Hyprland (re)loads the theme: at start, on setcursor, and twice per monitor layout change
# (resume, VT switch, hotplug).
# --hypr-format png loads instantly at these sizes, but libhyprcursor 0.1.13 crops PNG frames
# it has to scale down noticeably (e.g. 24, 30 and 40-46 px from 38/48 px frames).
HYPR_PNG_SIZES = [38, 48]

# Rainbow stops (first == last so the repeating gradient wraps seamlessly).
RAINBOW = [
    "#FF1744", "#FF6D00", "#FFEA00", "#76FF03", "#00E676",
    "#00E5FF", "#2979FF", "#7C4DFF", "#D500F9", "#F50057", "#FF1744",
]
# Length of one rainbow period along each axis, in the SVGs' 256-unit viewBox. The gradient
# runs at 45 degrees, so a period covers PERIOD*sqrt(2) units of the diagonal.
PERIOD = 192.0
GRADIENT_ID = "bibata-rgb"
# The same rainbow half a period further on, for parts that sit next to the body and must
# stand out from it.
ALT_GRADIENT_ID = "bibata-rgb-alt"

BODY_RE = re.compile(r'(fill|stroke)="#FFFFFF"', re.IGNORECASE)
RAINBOW_URL = f"url(#{GRADIENT_ID})"
CORNER_PIE = (re.compile(r'fill="#(?:96C865|FDBE2A|4FADDF|F1613A)"'), f'fill="url(#{ALT_GRADIENT_ID})"')
# Extra parts that take the rainbow, as (pattern, replacement):
# - the light outline of the shapes Bibata draws without a white body;
# - for the red "not allowed" sign, a narrow ring inside its black outline, so the sign keeps a
#   crisp edge against both the red disc and the background;
# - the coloured quarter-circles of the diagonal resize cursors, in the shifted rainbow so the
#   thin direction bracket next to them stays visible.
EXTRA_BODY = {
    "X_cursor": [(re.compile(r'stroke="white"'), f'stroke="{RAINBOW_URL}"')],
    "wayland-cursor": [(re.compile(r'(stroke|fill)="white"'), rf'\1="{RAINBOW_URL}"')],
    "crossed_circle": [(
        re.compile(r'(<path d="[^"]*") fill="#FE0000" stroke="#000000" stroke-width="17"/>'),
        rf'\g<0>\1 fill="none" stroke="{RAINBOW_URL}" stroke-width="7"/>',
    )],
    "bottom_left_corner": [CORNER_PIE],
    "bottom_right_corner": [CORNER_PIE],
    "top_left_corner": [CORNER_PIE],
    "top_right_corner": [CORNER_PIE],
}
# The busy spinner's four coloured blades turn muddy over the rainbow. Alternating light and
# dark translucent blades keep the turning visible and the rainbow bright.
SPINNER_BLADES = {
    "F05024": 'fill="white" fill-opacity="0.5"',
    "FCB813": 'fill="#000000" fill-opacity="0.3"',
    "7EBA41": 'fill="white" fill-opacity="0.25"',
    "32A0DA": 'fill="#000000" fill-opacity="0.15"',
}
SPINNER_BLADE_RE = re.compile(r'fill="#(F05024|FCB813|7EBA41|32A0DA)" fill-opacity="0\.8"')
SVG_OPEN_RE = re.compile(r"<svg\b[^>]*>")


def gradient_defs(phase, axis):
    """Repeating rainbows shifted by `phase` (0..1) of one period. axis "diag" runs top-left to
    bottom-right, "anti" runs top-right to bottom-left."""
    sx = -1 if axis == "anti" else 1
    n = len(RAINBOW) - 1
    stops = "".join(
        f'<stop offset="{i / n:.4f}" stop-color="{c}"/>' for i, c in enumerate(RAINBOW)
    )

    def gradient(gid, shift):
        return (
            f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
            f'x1="0" y1="0" x2="{sx * PERIOD:g}" y2="{PERIOD:g}" spreadMethod="repeat" '
            f'gradientTransform="translate({sx * shift:.3f} {shift:.3f})">{stops}</linearGradient>'
        )

    shift = phase * PERIOD
    return f"<defs>{gradient(GRADIENT_ID, shift)}{gradient(ALT_GRADIENT_ID, shift + PERIOD / 2)}</defs>"


def recolor(svg, phase, name, axis="diag"):
    svg, replaced = BODY_RE.subn(rf'\1="{RAINBOW_URL}"', svg)
    for pattern, replacement in EXTRA_BODY.get(name, []):
        svg, n = pattern.subn(replacement, svg)
        replaced += n
    if replaced == 0:
        raise ValueError(f"{name}: no body colour to replace")
    svg = SPINNER_BLADE_RE.sub(lambda m: SPINNER_BLADES[m.group(1)], svg)
    m = SVG_OPEN_RE.search(svg)
    if not m:
        raise ValueError(f"{name}: no <svg> element")
    return svg[: m.end()] + gradient_defs(phase, axis) + svg[m.end():]


def body_axis(svg):
    """"anti" when the white body lies along the top-right/bottom-left diagonal (pencil,
    fd_double_arrow): across such a body the 45-degree rainbow would show one flat colour
    pulsing instead of flowing."""
    size = 64
    surface = render_surface(svg, size)
    data = surface.get_data()
    sums, diffs = [], []
    for y in range(size):
        for x in range(size):
            b, g, r, a = data[(y * size + x) * 4: (y * size + x) * 4 + 4]
            if a > 240 and min(r, g, b) > 235:
                sums.append(x + y)
                diffs.append(x - y)
    if len(sums) < 20:
        return "diag"

    def spread(v):
        v = sorted(v)
        return v[int(len(v) * 0.95)] - v[int(len(v) * 0.05)]

    return "anti" if spread(sums) < 0.6 * spread(diffs) else "diag"


def parse_meta(text):
    """Split a hyprcursor meta.hl into (header lines, [(size, file, delay)], override lines)."""
    header, frames, overrides = [], [], []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("define_size"):
            size, file, *rest = [p.strip() for p in s.split("=", 1)[1].split(",")]
            frames.append((int(size), file, int(rest[0]) if rest else 0))
        elif s.startswith("define_override"):
            overrides.append(s)
        elif s:
            header.append(s)
    return header, frames, overrides


def read_source_shape(hlc):
    with zipfile.ZipFile(hlc) as z:
        meta = z.read("meta.hl").decode()
        header, frames, overrides = parse_meta(meta)
        svgs = [z.read(f).decode() for _, f, _ in frames]
    return header, frames, overrides, svgs


def frame_plan(src_frames, src_svgs, count):
    """[(svg, phase, delay_ms)] for one output animation of `count` frames for static shapes."""
    if len(src_frames) > 1:
        # Already animated (spinner): keep its frames and timing, advance the rainbow per frame.
        n = len(src_frames)
        return [(src_svgs[i], i / n, src_frames[i][2]) for i in range(n)]
    delay = round(CYCLE_MS / count)
    return [(src_svgs[0], i / count, delay) for i in range(count)]


def render_surface(svg, size):
    handle = Rsvg.Handle.new_from_data(svg.encode())
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surface)
    viewport = Rsvg.Rectangle()
    viewport.x, viewport.y, viewport.width, viewport.height = 0, 0, size, size
    handle.render_document(ctx, viewport)
    surface.flush()
    return surface


def render_argb(svg, size):
    """Render an SVG to premultiplied little-endian ARGB, the pixel format XCursor uses."""
    surface = render_surface(svg, size)
    assert surface.get_stride() == size * 4
    return bytes(surface.get_data())


def read_xcursor_hotspots(path):
    """{nominal size: (xhot, yhot)} from an XCursor file."""
    data = path.read_bytes()
    magic, _, _, ntoc = struct.unpack_from("<4sIII", data, 0)
    if magic != b"Xcur":
        raise ValueError(f"{path} is not an XCursor file")
    hot = {}
    for i in range(ntoc):
        typ, subtype, pos = struct.unpack_from("<III", data, 16 + i * 12)
        if typ == 0xFFFD0002 and subtype not in hot:
            _, _, _, _, _, _, xh, yh, _ = struct.unpack_from("<9I", data, pos)
            hot[subtype] = (xh, yh)
    return hot


def xcursor_file(images):
    """images: [(nominal, xhot, yhot, delay, argb_bytes)] grouped by size, frames in order."""
    ntoc = len(images)
    out = [struct.pack("<4sIII", b"Xcur", 16, 0x10000, ntoc)]
    pos = 16 + 12 * ntoc
    chunks = []
    for nominal, xh, yh, delay, px in images:
        out.append(struct.pack("<III", 0xFFFD0002, nominal, pos))
        chunk = struct.pack("<9I", 36, 0xFFFD0002, nominal, 1, nominal, nominal, xh, yh, delay) + px
        chunks.append(chunk)
        pos += len(chunk)
    return b"".join(out + chunks)


def build_shape(args):
    name, hlc, hypr_dir, xcur_dir, src_xcursor, hypr_format = args
    header, frames, overrides, svgs = read_source_shape(hlc)
    hotspot = {}
    for line in header:
        key, _, value = line.partition("=")
        if key.strip().startswith("hotspot"):
            hotspot[key.strip()] = float(value)

    axis = body_axis(svgs[0])

    # hyprcursor
    shape_dir = Path(hypr_dir) / name
    shape_dir.mkdir(parents=True, exist_ok=True)
    plan = frame_plan(frames, svgs, HYPR_FRAMES)
    if hypr_format == "svg":
        lines = list(header) + [""]
        for i, (svg, phase, delay) in enumerate(plan):
            fname = f"{name}-{i + 1:02d}.svg"
            (shape_dir / fname).write_text(recolor(svg, phase, name, axis))
            lines.append(f"define_size = 0, {fname}, {delay}")
    else:
        lines = [l if not l.startswith("resize_algorithm") else "resize_algorithm = bilinear" for l in header] + [""]
        for size in HYPR_PNG_SIZES:
            for i, (svg, phase, delay) in enumerate(plan):
                fname = f"{name}-{size}-{i + 1:02d}.png"
                render_surface(recolor(svg, phase, name, axis), size).write_to_png(str(shape_dir / fname))
                lines.append(f"define_size = {size}, {fname}, {delay}")
    if overrides:
        lines += [""] + overrides
    (shape_dir / "meta.hl").write_text("\n".join(lines) + "\n")

    # XCursor: PNG frames at fixed sizes, hotspots copied from the original theme
    hot = read_xcursor_hotspots(Path(src_xcursor)) if src_xcursor else {}
    xplan = frame_plan(frames, svgs, XCUR_FRAMES)
    images = []
    for size in XCUR_SIZES:
        xh, yh = hot.get(size, (round(hotspot.get("hotspot_x", 0) * size), round(hotspot.get("hotspot_y", 0) * size)))
        for svg, phase, delay in xplan:
            images.append((size, xh, yh, delay, render_argb(recolor(svg, phase, name, axis), size)))
    (Path(xcur_dir) / name).write_bytes(xcursor_file(images))
    return name, axis, len(plan), len(xplan)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(__file__).resolve().parent
    ap.add_argument("--source", type=Path, default=SOURCE_THEME)
    ap.add_argument("--work", type=Path, default=here / "build/work")
    ap.add_argument("--out", type=Path, default=here / f"build/{THEME_NAME}")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--hypr-format", choices=["svg", "png"], default="svg",
                    help="hyprcursor frame format (default: svg; see HYPR_PNG_SIZES for png)")
    a = ap.parse_args()

    src_hypr = a.source / "hyprcursors"
    src_xcur = a.source / "cursors"
    shapes = sorted(p.stem for p in src_hypr.glob("*.hlc"))
    if not shapes or not src_xcur.is_dir():
        sys.exit(f"{a.source} is incomplete (needs hyprcursors/*.hlc and cursors/); "
                 "re-clone the repository or pass --source")
    if not shutil.which("hyprcursor-util"):
        sys.exit("hyprcursor-util not found (package: hyprcursor)")

    # Build next to the output and move it into place at the end, so an interrupted or failed
    # build never leaves a half-made theme where install.sh would pick it up.
    out = a.out.with_name(f".{a.out.name}.tmp")
    for d in (a.work, out):
        if d.exists():
            shutil.rmtree(d)
    hypr_src = a.work / "hyprcursor-src"
    (hypr_src / "hyprcursors").mkdir(parents=True)
    (out / "cursors").mkdir(parents=True)
    (hypr_src / "manifest.hl").write_text(
        f"name = {THEME_NAME}\n"
        "description = Bibata Modern with a flowing rainbow body\n"
        "version = 1.0\n"
        "cursors_directory = hyprcursors\n"
    )

    jobs = []
    for name in shapes:
        x = src_xcur / name
        jobs.append((name, src_hypr / f"{name}.hlc", hypr_src / "hyprcursors", out / "cursors",
                     x if x.is_file() and not x.is_symlink() else None, a.hypr_format))
    with ProcessPoolExecutor(max_workers=a.jobs) as pool:
        for name, axis, nh, nx in pool.map(build_shape, jobs):
            print(f"{name}: {nh} hyprcursor frames, {nx} xcursor frames, rainbow axis {axis}")

    # Compile the hyprcursor archives
    compiled = a.work / "compiled"
    compiled.mkdir()
    subprocess.run(["hyprcursor-util", "--create", str(hypr_src), "-o", str(compiled)], check=True,
                   stdout=subprocess.DEVNULL)
    theme_dir = compiled / f"theme_{THEME_NAME}"
    shutil.copy2(theme_dir / "manifest.hl", out / "manifest.hl")
    shutil.copytree(theme_dir / "hyprcursors", out / "hyprcursors")

    # XCursor aliases: mirror the original theme's symlinks
    for entry in sorted(src_xcur.iterdir()):
        if entry.is_symlink():
            os.symlink(os.readlink(entry), out / "cursors" / entry.name)
        elif entry.name not in shapes:
            print(f"warning: XCursor {entry.name} has no hyprcursor source, left to the fallback theme")

    (out / "index.theme").write_text(
        f"[Icon Theme]\nName={THEME_NAME}\nComment=Bibata Modern with a flowing rainbow body\n"
        "Inherits=Bibata-Modern-Ice,hicolor\n"
    )
    (out / "cursor.theme").write_text(f"[Icon Theme]\nName={THEME_NAME}\nInherits=Bibata-Modern-Ice\n")
    # The theme is a modified Bibata (GPL-3.0): ship the licence and where it comes from.
    shutil.copy2(here / "LICENSE", out / "LICENSE")
    (out / "NOTICE").write_text(
        f"{THEME_NAME}: an animated rainbow version of the Bibata-Modern-Ice cursor theme.\n"
        "Generated by https://github.com/blackixxce12/bibata-rgb (source: generate.py).\n"
        "Bibata Cursor by Abdulkaiz Khatri (ful1e5), https://github.com/ful1e5/Bibata_Cursor.\n"
        "Licensed under the GNU General Public License v3.0, see LICENSE.\n"
    )

    if a.out.exists():
        shutil.rmtree(a.out)
    out.rename(a.out)
    print(f"built {a.out}")


if __name__ == "__main__":
    main()
