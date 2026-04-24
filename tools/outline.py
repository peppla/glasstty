"""Outline <-> bitmap round-trip for source font glyphs.

Every pixel-font glyph in Glass_TTY_VT220.ttf is composed of axis-aligned
rounded rectangles snapped to a 50-unit grid, with each rectangle exactly
50 units tall. We exploit that regularity to parse glyphs back into a
{(y_bottom, y_top): set(col_index)} bitmap representation, which the Bold
and Strong builds transform and re-render.

Glyphs that don't fit the rectangular pattern (e.g. `.notdef`, and Ъ which
has sub-unit-offset strokes) are handed back as "opaque" and copied unchanged
into the derived fonts. That's 2 glyphs out of 323 — acceptable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fontTools.ttLib.tables._g_l_y_f import Glyph as GlyfGlyph


@dataclass(frozen=True)
class Bitmap:
    """Bitmap of a glyph. Keys are (y_bottom, y_top) in font units; values
    are the set of 50-unit-wide column indices that are on at that row. Rows
    are always 50 units tall in the source font.
    """
    rows: dict  # (int, int) -> set[int]

    def mapped(self, transform_cols):
        return Bitmap({k: transform_cols(v) for k, v in self.rows.items()})


def extract_bitmap(glyph: GlyfGlyph) -> Optional[Bitmap]:
    """Parse a simple (non-composite) glyph into a Bitmap.

    Returns None when the glyph either has zero contours or any contour
    whose bounding box isn't 50-grid-aligned — in which case the caller
    should preserve the original glyph outline unchanged.
    """
    if glyph.numberOfContours <= 0:
        return None
    if glyph.isComposite():
        return None

    coords = list(glyph.coordinates)
    start = 0
    rows: dict = {}
    for end in glyph.endPtsOfContours:
        pts = coords[start:end + 1]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        start = end + 1
        if any(v % 50 != 0 for v in (x1, y1, x2, y2)):
            return None
        if y2 - y1 != 50:
            # A pixel rect should be 50 tall. Bail on this glyph.
            return None
        col_start, col_end = x1 // 50, x2 // 50  # exclusive end
        if col_start < 0 or col_end > 16:
            return None
        key = (y1, y2)
        cols = rows.setdefault(key, set())
        for c in range(col_start, col_end):
            cols.add(c)
    return Bitmap(rows)


def dot_stretch(bitmap: Bitmap) -> Bitmap:
    """Apply the VT220 dot-stretching transform: each on-pixel's right
    neighbor becomes on too. Mirrors the hardware behavior masswerk
    describes for the VT220 CRT."""
    return bitmap.mapped(lambda cols: cols | {c + 1 for c in cols})


def runs_in(cols: set) -> list[tuple[int, int]]:
    """Contiguous column runs from a set of column indices, as
    (start, end_inclusive) pairs."""
    if not cols:
        return []
    sorted_cols = sorted(cols)
    result: list[tuple[int, int]] = []
    start = prev = sorted_cols[0]
    for c in sorted_cols[1:]:
        if c == prev + 1:
            prev = c
            continue
        result.append((start, prev))
        start = prev = c
    result.append((start, prev))
    return result
