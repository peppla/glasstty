"""Glyph geometry primitives matching the Glass TTY VT220 design grid.

The existing font uses an 8-column x 7-row cell layout (cap-height glyphs),
where every cell is 50 units wide and 100 units tall. An "on" pixel is drawn
as a rounded rectangle occupying the TOP 50 units of its cell; the bottom 50
units stay empty, baking the CRT scanline effect into every glyph.

Horizontally adjacent on-pixels in the same row merge into a single wider
rectangle. Vertically adjacent rows never merge.

Coordinates are in font units. The baseline is at y=0; cap height at y=700.
Row 0 is the bottom row (y=50..100), row 6 is the top (y=650..700).
Column 0 is leftmost (x=0..50), column 7 is rightmost (x=350..400).
Advance width is 500; the body occupies x=0..400 with a 100-unit right
sidebearing.
"""

CELL_W = 50
CELL_H = 100
PIXEL_H = 50  # drawn height within a cell (scanline gap is the other 50)
BASELINE = 0
CAP_TOP = 700
ADVANCE = 500
BODY_W = 400
CORNER_R = 9


def cell_x(col: int) -> int:
    return col * CELL_W


def cell_y(row: int) -> int:
    """Bottom-Y of the drawn portion of the given row (row 0 = baseline row)."""
    return BASELINE + row * CELL_H + CELL_W  # +50, i.e., skip the scanline gap


def rounded_rect_offcurves(x1: int, y1: int, x2: int, y2: int, r: int = CORNER_R):
    """Return the 8 off-curve points of a rounded rectangle, in the same order
    and winding used throughout the existing Glass TTY font.

    Emits as an all-off-curve qCurveTo when written via a pen:
        pen.qCurveTo(*rounded_rect_offcurves(...), None)
    The on-curve points are implicit midpoints.
    """
    return [
        (x1, y1 + r), (x1, y2 - r),
        (x1 + r, y2), (x2 - r, y2),
        (x2, y2 - r), (x2, y1 + r),
        (x2 - r, y1), (x1 + r, y1),
    ]


def draw_rounded_rect(pen, x1: int, y1: int, x2: int, y2: int, r: int = CORNER_R):
    """Draw a rounded rectangle via the TT glyph pen convention used by the
    existing font: all off-curve points with implicit on-curve midpoints.

    Uses an explicit moveTo at the implicit first on-curve so ttGlyphPen is
    happy, then emits pairs of off-curves.
    """
    pts = rounded_rect_offcurves(x1, y1, x2, y2, r)
    # Implicit on-curve between last off-curve and first off-curve:
    start = (
        (pts[-1][0] + pts[0][0]) // 2,
        (pts[-1][1] + pts[0][1]) // 2,
    )
    pen.moveTo(start)
    # Emit 4 qCurveTo calls, each with 2 off-curves and the next implicit
    # on-curve as the final point. The implicit on-curve is the midpoint of
    # the two surrounding off-curves.
    for i in range(0, 8, 2):
        o1 = pts[i]
        o2 = pts[i + 1]
        next_o = pts[(i + 2) % 8]
        on = ((o2[0] + next_o[0]) // 2, (o2[1] + next_o[1]) // 2)
        pen.qCurveTo(o1, o2, on)
    pen.closePath()


def draw_pixel_run(pen, row: int, col_start: int, col_end_inclusive: int):
    """Draw a horizontal run of on-pixels from col_start..col_end_inclusive
    at the given row as a single rounded rectangle.
    """
    x1 = cell_x(col_start)
    x2 = cell_x(col_end_inclusive + 1)
    y1 = cell_y(row)
    y2 = y1 + PIXEL_H
    draw_rounded_rect(pen, x1, y1, x2, y2)
