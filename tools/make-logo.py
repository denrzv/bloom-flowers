#!/usr/bin/env python3
"""Generate assets/siteskin/logo.png, the brand asset the SiteSkin manifest points at.

Committed as a generator rather than only as a binary so the logo can be reviewed as source and
reproduced byte-for-byte. Output is deterministic: no timestamp chunk, no randomness, fixed zlib
level.

Pure standard library on purpose. This repository is the reference integration, and a site owner
reading it should find no toolchain to install -- the whole point of SiteSkin is that integrating
costs one JSON file, and a demo that opens with `pip install` argues the opposite.

The browser's constraints on this file are not stylistic (NET-003): PNG or WebP with a matching
byte signature, at most 512 KiB, at most 1024 pixels per axis and 1,048,576 pixels in total,
same-origin. 512x512 flat colour lands about two orders of magnitude inside the byte budget.
Everything is drawn at SS x scale and box-filtered down, because the browser renders this into a
40 dp slot where aliased edges are the first thing that shows.

Usage: python3 tools/make-logo.py [output-path]
"""

import struct
import sys
import zlib
from pathlib import Path

SIZE = 512
SS = 3  # supersampling factor per axis

# The manifest's own palette, so the asset and branding.primaryColor cannot drift apart.
PETAL = (0xD9, 0x4F, 0x8A)
PETAL_LIGHT = (0xF2, 0x9A, 0xC0)
CENTRE = (0xFF, 0xC9, 0x5E)
LEAF = (0x4F, 0xA5, 0x6B)
BACKGROUND = (0xFF, 0xF7, 0xFA)

PETAL_COUNT = 5


def _blend(base, top, alpha):
    return tuple(round(b + (t - b) * alpha) for b, t in zip(base, top))


def _in_ellipse(px, py, cx, cy, rx, ry, angle):
    """True when (px, py) is inside an ellipse centred at (cx, cy) rotated by `angle` radians."""
    import math

    dx, dy = px - cx, py - cy
    cos_a, sin_a = math.cos(-angle), math.sin(-angle)
    ux = dx * cos_a - dy * sin_a
    uy = dx * sin_a + dy * cos_a
    return (ux / rx) ** 2 + (uy / ry) ** 2 <= 1.0


def _sample(px, py):
    """Colour of one supersample, or None where the mark is not drawn."""
    import math

    cx = cy = SIZE * SS / 2.0
    unit = SIZE * SS / 512.0

    # Leaf and stem, drawn first so petals overlap them.
    if _in_ellipse(px, py, cx + 46 * unit, cy + 150 * unit, 62 * unit, 30 * unit, -0.5):
        return LEAF
    if abs(px - cx) <= 7 * unit and cy + 40 * unit <= py <= cy + 205 * unit:
        return LEAF

    # The centre sits on top of the petals: they all reach the middle, so drawing it last would
    # bury it and the mark would read as a blob rather than a flower.
    if _in_ellipse(px, py, cx, cy - 24 * unit, 44 * unit, 44 * unit, 0.0):
        return CENTRE

    for index in range(PETAL_COUNT):
        angle = -math.pi / 2 + index * (2 * math.pi / PETAL_COUNT)
        distance = 92 * unit
        ex = cx + math.cos(angle) * distance
        ey = cy - 24 * unit + math.sin(angle) * distance
        if _in_ellipse(px, py, ex, ey, 58 * unit, 88 * unit, angle + math.pi / 2):
            # A lighter tint on the upper half of each petal so the mark still reads as a flower
            # at 40 dp, where the individual petals are only a few pixels across.
            return PETAL_LIGHT if index in (0, 1, PETAL_COUNT - 1) else PETAL

    return None


def render():
    """Render the mark and box-filter it down to SIZE x SIZE RGB rows."""
    rows = []
    for y in range(SIZE):
        row = bytearray()
        for x in range(SIZE):
            hits = []
            for sy in range(SS):
                for sx in range(SS):
                    px = x * SS + sx + 0.5
                    py = y * SS + sy + 0.5
                    hits.append(_sample(px, py))
            drawn = [colour for colour in hits if colour is not None]
            if not drawn:
                row.extend(BACKGROUND)
                continue
            mixed = tuple(round(sum(c[i] for c in drawn) / len(drawn)) for i in range(3))
            row.extend(_blend(BACKGROUND, mixed, len(drawn) / len(hits)))
        rows.append(bytes(row))
    return rows


def _chunk(tag, payload):
    return (
        struct.pack(">I", len(payload))
        + tag
        + payload
        + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    )


def encode_png(rows):
    """Minimal PNG: signature, IHDR, IDAT, IEND. Filter type 0 on every scanline."""
    raw = b"".join(b"\x00" + row for row in rows)
    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0)  # 8-bit, truecolour RGB
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )


def main():
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "assets/siteskin/logo.png")
    target.parent.mkdir(parents=True, exist_ok=True)
    data = encode_png(render())
    target.write_bytes(data)
    print(f"{target}: {SIZE}x{SIZE}, {len(data)} bytes")


if __name__ == "__main__":
    main()
