"""Parser + renderer for the 8x7 ASCII glyph DSL.

File format:

    # Lines starting with '#' are comments.
    # Blank lines separate glyph records.

    U+20AC EURO SIGN
    ..####..
    .#......
    ##.####.
    ##......
    ##.####.
    .#......
    ..####..

Each glyph record begins with a header line:

    U+<HEX> <POSTSCRIPT-LIKE NAME>

followed by exactly 7 rows of 8 characters each. '.' or ' ' = off, any other
non-whitespace char = on. Rows are top-to-bottom (first row = visual top,
corresponds to design row 6; last row = row 0, sitting on the baseline).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .pixel import REGULAR, Mode, draw_pixel_run

GRID_W = 8
GRID_H = 7

HEADER_RE = re.compile(r"^U\+([0-9A-Fa-f]{4,6})\s+(\S+(?:\s+\S+)*)$")


@dataclass(frozen=True)
class Glyph:
    codepoint: int
    name: str
    rows: tuple[tuple[bool, ...], ...]  # rows[0] = visual top

    def grid_row(self, design_row: int) -> tuple[bool, ...]:
        """Fetch by design row (0=baseline, 6=cap-top)."""
        return self.rows[GRID_H - 1 - design_row]

    def draw(self, pen, mode: Mode = REGULAR) -> None:
        for design_row in range(GRID_H):
            row = self.grid_row(design_row)
            col = 0
            while col < GRID_W:
                if not row[col]:
                    col += 1
                    continue
                start = col
                while col < GRID_W and row[col]:
                    col += 1
                draw_pixel_run(pen, design_row, start, col - 1, mode)


def _parse_row(line: str) -> tuple[bool, ...]:
    if len(line) != GRID_W:
        raise ValueError(f"row must be exactly {GRID_W} chars, got {len(line)!r}")
    return tuple(c not in (".", " ") for c in line)


def parse_file(path: Path) -> list[Glyph]:
    glyphs: list[Glyph] = []
    current_header: tuple[int, str] | None = None
    current_rows: list[tuple[bool, ...]] = []

    def flush() -> None:
        nonlocal current_header, current_rows
        if current_header is None:
            return
        if len(current_rows) != GRID_H:
            cp, nm = current_header
            raise ValueError(
                f"{path}: glyph U+{cp:04X} {nm} has {len(current_rows)} rows, "
                f"expected {GRID_H}"
            )
        glyphs.append(Glyph(current_header[0], current_header[1], tuple(current_rows)))
        current_header = None
        current_rows = []

    for raw in path.read_text().splitlines():
        line = raw.rstrip()
        stripped = line.lstrip()
        is_comment = stripped.startswith("# ") or stripped == "#"
        if not line.strip() or is_comment:
            if line.strip() == "" and current_header is not None and current_rows:
                flush()
            continue
        m = HEADER_RE.match(line)
        if m:
            flush()
            current_header = (int(m.group(1), 16), m.group(2))
            current_rows = []
            continue
        if current_header is None:
            raise ValueError(f"{path}: stray line before any header: {line!r}")
        current_rows.append(_parse_row(line))
    flush()
    return glyphs


def load_all(glyph_dir: Path) -> list[Glyph]:
    glyphs: list[Glyph] = []
    seen: dict[int, str] = {}
    for path in sorted(glyph_dir.glob("*.txt")):
        for g in parse_file(path):
            if g.codepoint in seen:
                raise ValueError(
                    f"duplicate codepoint U+{g.codepoint:04X} in "
                    f"{path.name} (already in {seen[g.codepoint]})"
                )
            seen[g.codepoint] = path.name
            glyphs.append(g)
    return glyphs
