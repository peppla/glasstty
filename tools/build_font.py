"""Build GlassTTYVT220-Modern.ttf from the existing TTF + glyph DSL sources.

Pipeline:
  1. Load the source TTF.
  2. Parse all glyph DSL files.
  3. For each DSL glyph: render to a TrueType glyph, register it in the
     cmap (all 4 Unicode subtables the source uses), hmtx, glyf, post.
  4. Fix font-wide metadata: name table, post.isFixedPitch, gasp, OS/2
     avg width, font version, and clear the misleading "Use font size N"
     name records.
  5. Write to dist/.

Deterministic: glyphs iterated in sorted codepoint order, no timestamps.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph as GlyfGlyph

from .glyph_dsl import Glyph, load_all
from .pixel import ADVANCE

ROOT = Path(__file__).resolve().parent.parent
SOURCE_TTF = ROOT / "Glass_TTY_VT220.ttf"
GLYPH_DIR = ROOT / "glyphs"
DIST_DIR = ROOT / "dist"
OUTPUT_TTF = DIST_DIR / "GlassTTYVT220-Modern.ttf"

FAMILY_NAME = "Glass TTY VT220 Modern"
STYLE_NAME = "Regular"
FULL_NAME = "Glass TTY VT220 Modern Regular"
POSTSCRIPT_NAME = "GlassTTYVT220-Modern"
VERSION = "Version 002.000"
UNIQUE_ID = "GlassTTYVT220-Modern:2.000"


def _glyph_postscript_name(g: Glyph) -> str:
    """Pick a unique PS glyph name. Prefer the DSL-supplied name; fall back to
    uniXXXX / uXXXXXX to guarantee uniqueness if collisions arise."""
    return g.name or (f"uni{g.codepoint:04X}" if g.codepoint <= 0xFFFF else f"u{g.codepoint:06X}")


def _ensure_unique_glyph_name(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    # Fall back to codepoint-derived name if the DSL name clashes.
    i = 1
    while True:
        candidate = f"{base}.alt{i:02d}"
        if candidate not in existing:
            return candidate
        i += 1


def _render_glyph(font: TTFont, dsl_glyph: Glyph) -> GlyfGlyph:
    pen = TTGlyphPen(font.getGlyphSet())
    dsl_glyph.draw(pen)
    return pen.glyph()


def _add_cmap_mapping(font: TTFont, codepoint: int, glyph_name: str) -> None:
    """Add (codepoint -> glyph_name) to every Unicode cmap subtable."""
    cmap = font["cmap"]
    for sub in cmap.tables:
        if sub.isUnicode():
            sub.cmap[codepoint] = glyph_name


def _set_name(font: TTFont, name_id: int, value: str) -> None:
    name_tbl = font["name"]
    # Remove all existing entries for this name_id.
    name_tbl.names = [n for n in name_tbl.names if n.nameID != name_id]
    # Add on the three standard platforms/encodings used by this font family.
    name_tbl.setName(value, name_id, 1, 0, 0)     # Mac Roman, English
    name_tbl.setName(value, name_id, 3, 1, 0x409)  # Windows Unicode BMP, en-US


def _clear_old_notes(font: TTFont) -> None:
    """Strip the 'Use font size 15 on Windows / 20 on Mac' guidance that no
    longer applies to the rebuilt font."""
    keep = []
    for rec in font["name"].names:
        val = rec.toUnicode() if hasattr(rec, "toUnicode") else str(rec.string)
        if "Use font size" in val:
            continue
        keep.append(rec)
    font["name"].names = keep


def _fix_fixed_pitch(font: TTFont) -> None:
    font["post"].isFixedPitch = 1
    # OS/2 Panose monospace hint (family=3 Modern, proportion=9 Monospaced)
    panose = font["OS/2"].panose
    panose.bFamilyType = 3
    panose.bProportion = 9
    # Panose monospaced bit on OS/2 fsSelection is not standard, but the flag
    # that terminal apps check is post.isFixedPitch. Nothing else to set.


def _fix_gasp(font: TTFont) -> None:
    """Grayscale at every size. The existing outlines have no hints, so the
    right behavior everywhere is 'symmetric smoothing' rather than 'grid-fit'.
    If hints are added later, change the range to gridfit-small/smooth-large.
    """
    gasp = font["gasp"]
    gasp.version = 1
    # 0xFFFF means 'all sizes up to ppem FFFF use these flags'.
    # Flag bits: 0x1=GRIDFIT, 0x2=DOGRAY, 0x4=SYMMETRIC_GRIDFIT, 0x8=SYMMETRIC_SMOOTHING.
    gasp.gaspRange = {0xFFFF: 0x0A}  # DOGRAY | SYMMETRIC_SMOOTHING


def _fix_os2_avg_width(font: TTFont) -> None:
    # Monospace: xAvgCharWidth = advance width, per the OS/2 v4+ guidance.
    font["OS/2"].xAvgCharWidth = ADVANCE


def _fix_version(font: TTFont) -> None:
    # head.fontRevision: fixed-point 16.16; write 2.000
    font["head"].fontRevision = 2.0


def build() -> Path:
    if not SOURCE_TTF.exists():
        raise FileNotFoundError(f"source font missing: {SOURCE_TTF}")
    if not GLYPH_DIR.exists():
        raise FileNotFoundError(f"glyph dir missing: {GLYPH_DIR}")

    font = TTFont(SOURCE_TTF)
    dsl_glyphs = sorted(load_all(GLYPH_DIR), key=lambda g: g.codepoint)

    glyph_order = list(font.getGlyphOrder())
    existing_names: set[str] = set(glyph_order)
    cmap = font.getBestCmap()

    added = 0
    replaced = 0
    for g in dsl_glyphs:
        if g.codepoint in cmap:
            # Glyph already exists in source font. Skip — keep the hand-drawn
            # shape. (Euro/Latin-9/etc. aren't in the source, so they'll be
            # added; any collision is intentional for future overrides.)
            replaced += 1
            continue

        ps_name = _ensure_unique_glyph_name(_glyph_postscript_name(g), existing_names)
        existing_names.add(ps_name)

        glyf_glyph = _render_glyph(font, g)
        font["glyf"][ps_name] = glyf_glyph
        # lsb must match xMin for rendering to place the glyph correctly.
        glyf_glyph.recalcBounds(font["glyf"])
        font["hmtx"][ps_name] = (ADVANCE, glyf_glyph.xMin)
        glyph_order.append(ps_name)
        _add_cmap_mapping(font, g.codepoint, ps_name)
        added += 1

    font.setGlyphOrder(glyph_order)
    font["maxp"].numGlyphs = len(glyph_order)

    _clear_old_notes(font)
    _set_name(font, 1, FAMILY_NAME)            # Family
    _set_name(font, 2, STYLE_NAME)             # Subfamily
    _set_name(font, 3, UNIQUE_ID)              # Unique ID
    _set_name(font, 4, FULL_NAME)              # Full name
    _set_name(font, 5, VERSION)                # Version string
    _set_name(font, 6, POSTSCRIPT_NAME)        # PostScript name
    _fix_fixed_pitch(font)
    _fix_gasp(font)
    _fix_os2_avg_width(font)
    _fix_version(font)

    DIST_DIR.mkdir(exist_ok=True)
    font.save(OUTPUT_TTF)

    print(f"added {added} glyphs, skipped {replaced} existing", file=sys.stderr)
    return OUTPUT_TTF


if __name__ == "__main__":
    build()
