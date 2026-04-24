"""Build Glass TTY VT220 Modern TTFs (Regular, Bold, Strong) from the
source font plus the glyph DSL.

Each variant:
  * Regular keeps every source glyph as-is, then appends the DSL-defined
    extensions rendered with the Regular pixel mode.
  * Bold/Strong re-render each source glyph through extract_bitmap →
    dot_stretch → render (with the variant's pixel mode). Glyphs whose
    geometry isn't grid-aligned (2 of 323) are copied untouched.
  * The DSL glyphs are rendered in the variant's pixel mode too, so
    everything gains weight coherently.

Deterministic: glyphs iterated in sorted codepoint / glyph-order order,
no timestamps or random state.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph as GlyfGlyph

from .glyph_dsl import Glyph as DslGlyph, load_all
from .outline import Bitmap, dot_stretch, extract_bitmap, runs_in
from .pixel import (
    ADVANCE,
    BOLD,
    OBLIQUE,
    REGULAR,
    SEMIBOLD,
    Mode,
    draw_raw_run,
)

ROOT = Path(__file__).resolve().parent.parent
SOURCE_TTF = ROOT / "Glass_TTY_VT220.ttf"
GLYPH_DIR = ROOT / "glyphs"
DIST_DIR = ROOT / "dist"

FAMILY_MODERN = "Glass TTY VT220 Modern"
FAMILY_OBLIQUE = "Glass TTY VT220 Oblique"

VERSION = "Version 002.000"

# Affine-shear italic: x' = x + (y - SHEAR_PIVOT_Y) * SHEAR_SLANT.
# slant 0.1763 = tan(10°); pivot at mid-cap so the glyph stays centered
# within the 500-unit advance.
SHEAR_SLANT = 0.1763
SHEAR_PIVOT_Y = 350
ITALIC_ANGLE_DEG = -10.0


# ---- variant descriptors ----------------------------------------------------

class Variant:
    def __init__(
        self,
        mode: Mode,
        family: str,
        subfamily: str,
        ps_name: str,
        output_name: str,
        is_bold: bool = False,
        is_italic: bool = False,
        weight: int = 400,
        italic_angle: float = 0.0,
        affine_shear: float = 0.0,
    ):
        self.mode = mode
        self.family = family
        self.subfamily = subfamily
        self.ps_name = ps_name
        self.output_name = output_name
        self.is_bold = is_bold
        self.is_italic = is_italic
        self.weight = weight
        self.italic_angle = italic_angle
        self.affine_shear = affine_shear

    @property
    def unique_id(self) -> str:
        return f"{self.ps_name}:2.000"

    @property
    def full_name(self) -> str:
        return f"{self.family} {self.subfamily}"


V_REGULAR = Variant(
    mode=REGULAR,
    family=FAMILY_MODERN,
    subfamily="Regular",
    ps_name="GlassTTYVT220-Modern",
    output_name="GlassTTYVT220-Modern.ttf",
    weight=400,
)
V_BOLD = Variant(
    mode=BOLD,
    family=FAMILY_MODERN,
    subfamily="Bold",
    ps_name="GlassTTYVT220-Modern-Bold",
    output_name="GlassTTYVT220-Modern-Bold.ttf",
    is_bold=True,
    weight=700,
)
V_SEMIBOLD = Variant(
    mode=SEMIBOLD,
    family=FAMILY_MODERN,
    subfamily="SemiBold",
    ps_name="GlassTTYVT220-Modern-SemiBold",
    output_name="GlassTTYVT220-Modern-SemiBold.ttf",
    weight=600,
)
V_ITALIC = Variant(
    mode=REGULAR,
    family=FAMILY_MODERN,
    subfamily="Italic",
    ps_name="GlassTTYVT220-Modern-Italic",
    output_name="GlassTTYVT220-Modern-Italic.ttf",
    is_italic=True,
    weight=400,
    italic_angle=ITALIC_ANGLE_DEG,
    affine_shear=SHEAR_SLANT,
)
V_BOLD_ITALIC = Variant(
    mode=BOLD,
    family=FAMILY_MODERN,
    subfamily="Bold Italic",
    ps_name="GlassTTYVT220-Modern-BoldItalic",
    output_name="GlassTTYVT220-Modern-BoldItalic.ttf",
    is_bold=True,
    is_italic=True,
    weight=700,
    italic_angle=ITALIC_ANGLE_DEG,
    affine_shear=SHEAR_SLANT,
)
V_SEMIBOLD_ITALIC = Variant(
    mode=SEMIBOLD,
    family=FAMILY_MODERN,
    subfamily="SemiBold Italic",
    ps_name="GlassTTYVT220-Modern-SemiBoldItalic",
    output_name="GlassTTYVT220-Modern-SemiBoldItalic.ttf",
    is_italic=True,
    weight=600,
    italic_angle=ITALIC_ANGLE_DEG,
    affine_shear=SHEAR_SLANT,
)
V_OBLIQUE = Variant(
    mode=OBLIQUE,
    family=FAMILY_OBLIQUE,
    subfamily="Regular",
    ps_name="GlassTTYVT220-Oblique",
    output_name="GlassTTYVT220-Oblique.ttf",
    weight=400,
    italic_angle=ITALIC_ANGLE_DEG,
)

VARIANTS = [
    V_REGULAR,
    V_BOLD,
    V_SEMIBOLD,
    V_ITALIC,
    V_BOLD_ITALIC,
    V_SEMIBOLD_ITALIC,
    V_OBLIQUE,
]


# ---- glyph rendering -------------------------------------------------------

def _glyph_postscript_name(g: DslGlyph) -> str:
    return g.name or (f"uni{g.codepoint:04X}" if g.codepoint <= 0xFFFF else f"u{g.codepoint:06X}")


def _ensure_unique_glyph_name(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    i = 1
    while True:
        candidate = f"{base}.alt{i:02d}"
        if candidate not in existing:
            return candidate
        i += 1


def _render_dsl_glyph(font: TTFont, dsl_glyph: DslGlyph, mode: Mode) -> GlyfGlyph:
    pen = TTGlyphPen(font.getGlyphSet())
    dsl_glyph.draw(pen, mode)
    return pen.glyph()


def _render_bitmap(font: TTFont, bitmap: Bitmap, mode: Mode) -> GlyfGlyph:
    pen = TTGlyphPen(font.getGlyphSet())
    for (y1, y2), cols in sorted(bitmap.rows.items()):
        for c_start, c_end in runs_in(cols):
            x1 = c_start * 50
            x2 = (c_end + 1) * 50
            draw_raw_run(pen, x1, y1, x2, y2, mode)
    return pen.glyph()


# ---- font-wide metadata ----------------------------------------------------

def _add_cmap_mapping(font: TTFont, codepoint: int, glyph_name: str) -> None:
    for sub in font["cmap"].tables:
        if sub.isUnicode():
            sub.cmap[codepoint] = glyph_name


def _set_name(font: TTFont, name_id: int, value: str) -> None:
    name_tbl = font["name"]
    name_tbl.names = [n for n in name_tbl.names if n.nameID != name_id]
    name_tbl.setName(value, name_id, 1, 0, 0)
    name_tbl.setName(value, name_id, 3, 1, 0x409)


def _clear_old_notes(font: TTFont) -> None:
    keep = []
    for rec in font["name"].names:
        val = rec.toUnicode() if hasattr(rec, "toUnicode") else str(rec.string)
        if "Use font size" in val:
            continue
        keep.append(rec)
    font["name"].names = keep


def _apply_variant_metadata(font: TTFont, variant: Variant) -> None:
    _clear_old_notes(font)
    _set_name(font, 1, variant.family)
    _set_name(font, 2, variant.subfamily)
    _set_name(font, 3, variant.unique_id)
    _set_name(font, 4, variant.full_name)
    _set_name(font, 5, VERSION)
    _set_name(font, 6, variant.ps_name)

    font["post"].isFixedPitch = 1
    font["post"].italicAngle = variant.italic_angle
    panose = font["OS/2"].panose
    panose.bFamilyType = 3   # Modern
    panose.bProportion = 9   # Monospaced

    head = font["head"]
    os2 = font["OS/2"]

    # Style flags. REGULAR bit is exclusive with BOLD/ITALIC.
    mac = head.macStyle & ~(0x0001 | 0x0002)
    if variant.is_bold:
        mac |= 0x0001
    if variant.is_italic:
        mac |= 0x0002
    head.macStyle = mac

    fs = os2.fsSelection & ~(0x0001 | 0x0020 | 0x0040)
    if variant.is_italic:
        fs |= 0x0001
    if variant.is_bold:
        fs |= 0x0020
    if not variant.is_bold and not variant.is_italic:
        fs |= 0x0040
    os2.fsSelection = fs
    os2.usWeightClass = variant.weight

    gasp = font["gasp"]
    gasp.version = 1
    gasp.gaspRange = {0xFFFF: 0x0A}  # DOGRAY | SYMMETRIC_SMOOTHING
    os2.xAvgCharWidth = ADVANCE
    head.fontRevision = 2.0


# ---- affine-shear post-process ---------------------------------------------

def _apply_affine_shear(font: TTFont, slant: float) -> None:
    """Shear every simple-glyph outline by x' = x + (y - SHEAR_PIVOT_Y) * slant.

    Composite glyphs inherit the shear automatically through their component
    references (components are drawn with their source glyph's already-sheared
    coordinates), so we skip them here.
    """
    glyf = font["glyf"]
    for name in font.getGlyphOrder():
        g = glyf[name]
        if getattr(g, "numberOfContours", 0) <= 0:
            continue
        coords = g.coordinates
        for i in range(len(coords)):
            x, y = coords[i]
            coords[i] = (x + round((y - SHEAR_PIVOT_Y) * slant), y)
        g.recalcBounds(glyf)
        advance, _ = font["hmtx"].metrics[name]
        font["hmtx"][name] = (advance, g.xMin)


# ---- glyph rebuild ---------------------------------------------------------

def _mode_rebuilds_source(mode: Mode) -> bool:
    return (
        mode.extend_right_cols
        or mode.extend_right_units
        or mode.extend_down_units
        or mode.row_shear_k
    ) != 0


def _rebuild_source_glyphs(font: TTFont, mode: Mode) -> int:
    """Re-render every source glyph through the bitmap round-trip using `mode`.

    Bitmap-level dot-stretching (adding a neighbor column per on-pixel) only
    fires for modes that opt in via `extend_right_cols > 0` — i.e. Bold.
    Other weight/shear modes extend runs at render time instead.

    Returns the number of glyphs kept as-is because they weren't grid-aligned.
    """
    if not _mode_rebuilds_source(mode):
        return 0

    kept_as_is = 0
    for name in list(font.getGlyphOrder()):
        g = font["glyf"][name]
        bitmap = extract_bitmap(g)
        if bitmap is None:
            kept_as_is += 1
            continue
        if not bitmap.rows:
            continue
        if mode.extend_right_cols > 0:
            bitmap = dot_stretch(bitmap)
        new_glyph = _render_bitmap(font, bitmap, mode)
        font["glyf"][name] = new_glyph
        new_glyph.recalcBounds(font["glyf"])
        advance, _ = font["hmtx"].metrics[name]
        font["hmtx"][name] = (advance, new_glyph.xMin)
    return kept_as_is


# ---- entry point -----------------------------------------------------------

def build_variant(variant: Variant) -> Path:
    if not SOURCE_TTF.exists():
        raise FileNotFoundError(f"source font missing: {SOURCE_TTF}")
    if not GLYPH_DIR.exists():
        raise FileNotFoundError(f"glyph dir missing: {GLYPH_DIR}")

    font = TTFont(SOURCE_TTF)
    dsl_glyphs = sorted(load_all(GLYPH_DIR), key=lambda g: g.codepoint)

    kept_as_is = _rebuild_source_glyphs(font, variant.mode)

    glyph_order = list(font.getGlyphOrder())
    existing_names: set[str] = set(glyph_order)
    cmap = font.getBestCmap()

    added = 0
    for g in dsl_glyphs:
        if g.codepoint in cmap:
            continue
        ps_name = _ensure_unique_glyph_name(_glyph_postscript_name(g), existing_names)
        existing_names.add(ps_name)

        glyf_glyph = _render_dsl_glyph(font, g, variant.mode)
        font["glyf"][ps_name] = glyf_glyph
        glyf_glyph.recalcBounds(font["glyf"])
        font["hmtx"][ps_name] = (ADVANCE, glyf_glyph.xMin)
        glyph_order.append(ps_name)
        _add_cmap_mapping(font, g.codepoint, ps_name)
        added += 1

    font.setGlyphOrder(glyph_order)
    font["maxp"].numGlyphs = len(glyph_order)

    if variant.affine_shear != 0.0:
        _apply_affine_shear(font, variant.affine_shear)

    _apply_variant_metadata(font, variant)

    DIST_DIR.mkdir(exist_ok=True)
    out = DIST_DIR / variant.output_name
    font.save(out)

    print(
        f"[{variant.mode.name:>7}] added {added} DSL glyphs, "
        f"{kept_as_is} source glyphs passthrough",
        file=sys.stderr,
    )
    return out


def build_all() -> list[Path]:
    return [build_variant(v) for v in VARIANTS]


# Backwards-compatible entry point used by verify.py and older call sites.
def build() -> Path:
    return build_variant(V_REGULAR)


if __name__ == "__main__":
    build_all()
