"""Glyph geometry primitives matching the Glass TTY VT220 design grid.

The existing font uses an 8-column x 7-row cell layout (cap-height glyphs),
where every cell is 50 units wide and 100 units tall. An "on" pixel is drawn
as a rounded rectangle occupying the TOP 50 units of its cell; the bottom 50
units stay empty, baking the CRT scanline effect into every glyph.

Horizontally adjacent on-pixels in the same row merge into a single wider
rectangle. Vertically adjacent rows never merge (in Regular — Strong partially
closes the scanline gap).

Coordinates are in font units. The baseline is at y=0; cap height at y=700.
Row 0 is the bottom row (y=50..100), row 6 is the top (y=650..700).
Column 0 is leftmost (x=0..50), column 7 is rightmost (x=350..400).
Advance width is 500; the body occupies x=0..400 with a 100-unit right
sidebearing.

Render modes:
  * Regular: pixels as the source font draws them — 50 wide x 50 tall,
    scanline gap of 50 below each row.
  * Bold: VT220 dot-stretching — each on-pixel extends +50 units to the
    right so adjacent pixels merge into a wider run. Matches the hardware's
    legibility trick described by masswerk.
  * SemiBold (ex-Strong): +25-unit right extension on each run plus 20-unit
    downward scanline-gap fill. Lighter weight than Bold; pairs with Regular
    in the same family at usWeightClass 600.
  * Oblique: row-shear italic. Each design row shifts horizontally by
    (row - 3) * k units, preserving axis-aligned pixels. Results in a
    stair-stepped slant that keeps the CRT pixel aesthetic intact.

Modes compose via optional fields; any mode may add row_shear_k on top of its
weight settings (unused by the current build but the plumbing is there).
"""

from __future__ import annotations

from dataclasses import dataclass

CELL_W = 50
CELL_H = 100
PIXEL_H = 50
BASELINE = 0
CAP_TOP = 700
ADVANCE = 500
BODY_W = 400
CORNER_R = 9
STRONG_VERTICAL_FILL = 20


@dataclass(frozen=True)
class Mode:
    name: str
    extend_right_cols: int = 0   # full-column dot-stretching (Bold)
    extend_right_units: int = 0  # fine-grained right extension (SemiBold)
    extend_down_units: int = 0   # scanline-gap fill (SemiBold)
    row_shear_k: int = 0         # per-row x-shift coefficient (Oblique)


REGULAR = Mode(name="Regular")
BOLD = Mode(name="Bold", extend_right_cols=1)
SEMIBOLD = Mode(
    name="SemiBold",
    extend_right_units=25,
    extend_down_units=STRONG_VERTICAL_FILL,
)
OBLIQUE = Mode(name="Oblique", row_shear_k=20)

# Backwards-compatibility alias — older build scripts/import paths may still
# refer to `STRONG`. The in-family SemiBold supersedes the old Strong family.
STRONG = SEMIBOLD


def cell_x(col: int) -> int:
    return col * CELL_W


def cell_y(row: int) -> int:
    """Bottom-Y of the drawn portion of the given row (row 0 = baseline row)."""
    return BASELINE + row * CELL_H + CELL_W


def _row_shift(row: int, mode: Mode) -> int:
    """Row-shear horizontal offset for the given design row.

    Centered so row 3 (mid cap-height) is the pivot: row 0 shifts left,
    row 6 shifts right. Descender rows (negative) continue the slant.
    """
    return (row - 3) * mode.row_shear_k


def draw_rounded_rect(pen, x1: int, y1: int, x2: int, y2: int, r: int = CORNER_R):
    """Draw a rounded rectangle via the TT glyph pen convention used by the
    existing font: 8 off-curve points with implicit on-curve midpoints."""
    pts = [
        (x1, y1 + r), (x1, y2 - r),
        (x1 + r, y2), (x2 - r, y2),
        (x2, y2 - r), (x2, y1 + r),
        (x2 - r, y1), (x1 + r, y1),
    ]
    start = ((pts[-1][0] + pts[0][0]) // 2, (pts[-1][1] + pts[0][1]) // 2)
    pen.moveTo(start)
    for i in range(0, 8, 2):
        o1 = pts[i]
        o2 = pts[i + 1]
        next_o = pts[(i + 2) % 8]
        on = ((o2[0] + next_o[0]) // 2, (o2[1] + next_o[1]) // 2)
        pen.qCurveTo(o1, o2, on)
    pen.closePath()


def draw_pixel_run(pen, row: int, col_start: int, col_end_inclusive: int, mode: Mode = REGULAR, tile_right: bool = False):
    """Draw a horizontal run of on-pixels at the given design row.

    `tile_right` forces the right edge to `ADVANCE` instead of honoring the
    mode's normal extensions — used by box-drawing glyphs whose rightmost
    pixel must butt up against the next cell to tile seamlessly.
    """
    shift = _row_shift(row, mode)
    x1 = cell_x(col_start) + shift
    if tile_right:
        x2 = ADVANCE + shift
    else:
        x2 = cell_x(col_end_inclusive + 1 + mode.extend_right_cols) + mode.extend_right_units + shift
    y_top = cell_y(row) + PIXEL_H
    y_bot = cell_y(row) - mode.extend_down_units
    draw_rounded_rect(pen, x1, y_bot, x2, y_top)


def draw_filled_rect(pen, x1: int, y1: int, x2: int, y2: int):
    """Draw a plain (non-rounded) rectangle. Used for solid fills like U+2588
    where the VT220 scanline aesthetic is suppressed and the glyph must fill
    its entire line box to tile with neighbors."""
    pen.moveTo((x1, y1))
    pen.lineTo((x2, y1))
    pen.lineTo((x2, y2))
    pen.lineTo((x1, y2))
    pen.closePath()


def draw_raw_run(pen, x1: int, y1: int, x2: int, y2: int, mode: Mode = REGULAR):
    """Draw an arbitrary-y pixel run (used when re-rendering source glyphs
    whose rows may fall outside the 7-row cap-height grid, e.g. descenders,
    accents). `y1`/`y2` are the bottom/top of the 50-tall source rect;
    `mode` adds the variant's extensions exactly as in the cap-height path.
    """
    assert y2 - y1 == 50, "source rects are always 50 tall"
    row = (y1 - CELL_W) // CELL_H  # inverse of cell_y(); works for descenders/accents
    shift = _row_shift(row, mode)
    x2_extended = x2 + mode.extend_right_cols * CELL_W + mode.extend_right_units
    y1_extended = y1 - mode.extend_down_units
    draw_rounded_rect(pen, x1 + shift, y1_extended, x2_extended + shift, y2)
