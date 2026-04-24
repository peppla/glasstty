"""Post-build assertions. Exits non-zero on any failure."""

from __future__ import annotations

import sys
from pathlib import Path

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

from .pixel import ADVANCE

REQUIRED_CODEPOINTS = {
    0x20AC,  # €
    0x0152, 0x0153, 0x0160, 0x0161, 0x0178, 0x017D, 0x017E,  # Latin-9 deltas
    0x2190, 0x2191, 0x2192, 0x2193, 0x21B5,  # arrows + carriage return
    0x2500, 0x2502, 0x250C, 0x2510, 0x2514, 0x2518,  # box drawing corners
    0x251C, 0x2524, 0x252C, 0x2534, 0x253C,  # box drawing junctions
    0x2591, 0x2592, 0x2593, 0x2588,  # blocks/shades
    0x23BA, 0x23BB, 0x23BC, 0x23BD,  # DEC horizontal scanlines
    0x2264, 0x2265, 0x2260, 0x03C0,  # math
    0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D,  # dashes + smart quotes
    0x2022, 0x2026, 0x2122,  # bullet, ellipsis, trademark
}

# Existing coverage that must survive the rebuild.
EXISTING_CODEPOINTS = {
    0x0041, 0x0061, 0x0030, 0x0020,  # A a 0 space
    0x00A3, 0x00B0, 0x00E9,          # £ ° é
    0x0410, 0x044F,                  # Cyrillic sanity
}


def verify(ttf_path: Path) -> None:
    font = TTFont(ttf_path)
    errors: list[str] = []

    # Advance widths: every glyph must have the canonical monospace advance.
    for name, (width, _) in font["hmtx"].metrics.items():
        if width != ADVANCE:
            errors.append(f"{name}: advance {width} != {ADVANCE}")

    # post.isFixedPitch must be set.
    if not font["post"].isFixedPitch:
        errors.append("post.isFixedPitch is not set")

    cmap = font.getBestCmap()
    for cp in sorted(REQUIRED_CODEPOINTS):
        if cp not in cmap:
            errors.append(f"missing codepoint U+{cp:04X}")
    for cp in sorted(EXISTING_CODEPOINTS):
        if cp not in cmap:
            errors.append(f"regression: U+{cp:04X} was removed")

    # Every newly-added glyph's contour points must sit on the intended grid.
    # We check only the glyphs whose name is derived from a DSL codepoint
    # (those added by the build, which start with 'uni' or 'u' plus hex).
    gs = font.getGlyphSet()
    for cp in sorted(REQUIRED_CODEPOINTS):
        glyph_name = cmap.get(cp)
        if glyph_name is None:
            continue
        p = RecordingPen()
        gs[glyph_name].draw(p)
        # Bold/SemiBold push pixels into the right sidebearing (up to ADVANCE=500).
        # Italic/Oblique shear glyphs around mid-cap so both sidebearings can
        # be consumed; allow ~100 units of overhang on each side.
        for op, args in p.value:
            for pt in args:
                if not isinstance(pt, tuple):
                    continue
                x, y = pt
                if not (-100 <= x <= ADVANCE + 100 and -220 <= y <= 800):
                    errors.append(f"U+{cp:04X}: point ({x},{y}) outside glyph body")
                    break

    if errors:
        print("verify: FAIL", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    print(
        f"verify: OK ({len(cmap)} codepoints, {font['maxp'].numGlyphs} glyphs)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    verify(Path(sys.argv[1]))
