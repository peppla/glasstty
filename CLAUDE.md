# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

This repo distributes the GlassTTY VT220 TrueType font (`Glass_TTY_VT220.ttf`) by Viacheslav Slavinsky and keeps the source assets used to produce it. Original project page: http://sensi.org/~svo/glasstty. The font and all contents are public domain (see `LICENSE`).

A modernization pipeline extends the original font with characters missing from the VT220 era (Euro, Latin-9 deltas, arrows, DEC Special Graphics equivalents, block elements) while preserving the exact pixel style. Output: `dist/GlassTTYVT220-Modern.ttf`.

## Building the modernized font

```
python3 -m pip install -r requirements.txt
python3 build.py
```

`build.py` is fully unattended: it loads `Glass_TTY_VT220.ttf`, parses every glyph DSL file in `glyphs/`, renders each new glyph, fixes font-wide metadata, writes `dist/GlassTTYVT220-Modern.ttf`, and runs `tools/verify.py` which exits non-zero on any regression. Deterministic across runs (sorted iteration, no timestamps).

## Design grid (important)

The Latin glyphs in the source font use an **8-column × 7-row cap-height grid**, with each cell 50 units wide and 100 units tall. An "on" pixel is drawn as a ~50×50 rounded rectangle (≈9-unit corner radius) occupying the top half of its cell; the bottom half is always empty, baking the **CRT scanline effect** into every glyph row. Horizontally adjacent on-cells in the same row merge into a single wider rectangle; vertically adjacent rows never merge (scanlines stay visible).

Coordinate system: baseline y=0, cap top y=700, advance 500, body x=0..400, right sidebearing 100. UPM 1000, ascender 800, descender -150.

`tools/pixel.py` encodes this geometry; all new glyphs follow it.

## Glyph DSL

Each file under `glyphs/` defines one or more glyphs. Format:

```
U+20AC Euro
..####..
.#......
##.###..
##......
##.###..
.#......
..####..
```

Header line: `U+<HEX> <PostScript name>`. Then exactly **7 rows of 8 characters** each, top-to-bottom visually (first row = cap-top = design row 6; last row = baseline row = design row 0). Any non-whitespace, non-`.` character = on; `.` or space = off.

Comments are lines starting with `# ` (hash-space) — the leading `#` alone would collide with on-pixels so the parser requires the space. Blank lines separate glyph records.

If a codepoint in the DSL already exists in the source TTF, the DSL entry is **skipped** (source glyph wins). To replace an existing glyph, delete it from the source first or add an override path in `build_font.py`.

## How the pieces fit together

- `VT200` — DEC VT220 soft-font download escape sequence (`DCS P0;0;1;4;1;1{U ... ST`). Cyrillic block glyphs, each encoded as `top/bottom` sixel pairs on a 7×10 matrix. `ord(c) - 0o77` = 6 bits.
- `vtparse.py` — **Python 2** (uses `print` statement; depends on `pypng`). Regex-extracts sixels from `VT200`, writes `u04xx.png` bitmaps. Historical glyph-extraction step — not part of the modernization build.
- `Glass_TTY_VT220.ttf` — source outline font. 323 glyphs, full Latin-1 (U+0000–00FF) + Cyrillic (U+0401, U+0410–044F, U+0451). Monospace advance 500/1000 UPM. The PNG-to-TTF pipeline is not in this repo.
- `build.py` / `tools/` — **modernization pipeline** (Python 3 + fontTools). Extends the source font without redrawing any existing glyph.
- `glyphs/*.txt` — new glyph bitmaps (Euro, Latin-9, arrows, math, box drawing, blocks, scanlines, typography).
- `dist/GlassTTYVT220-Modern.ttf` — build output (gitignored).

## Modernization metadata changes

`build_font.py` applies these beyond adding glyphs:

- Family/Full/PostScript name → "Glass TTY VT220 Modern" / `GlassTTYVT220-Modern`
- `head.fontRevision` → 2.0
- Strips the original "Use font size 15 on Windows / 20 on Mac" name records (inaccurate for the extended font)
- `post.isFixedPitch` = 1, Panose family=Modern/proportion=Monospaced
- `OS/2.xAvgCharWidth` = advance = 500 (v4+ guidance for monospace)
- `gasp` = `SYMMETRIC_SMOOTHING | DOGRAY` at all PPEM (symmetric subpixel smoothing; no grid-fit since the outlines carry no hints)
- New glyphs' `hmtx` lsb is set to their `xMin` (per TrueType convention) — setting lsb=0 when xMin>0 causes the rasterizer to shift the glyph incorrectly

## Known limitations of the current modernization

- **No TrueType hints.** The outlines have no bytecode instructions, so the rasterizer cannot snap pixel boundaries at fractional PPEM. Adding instruction stubs to align the 50-unit grid to device pixels is the largest outstanding scaling win.
- **No embedded bitmap strike.** For pixel-perfect console rendering at native size, an `EBDT`/`EBLC` strike at 10px would help. Not implemented.
- **Descender-class glyphs not supported by the DSL.** The 8×7 cap-height grid assumes glyph bodies sit on the baseline. Adding g/y/p-style descenders requires extending the DSL to 9 rows with the bottom 2 below baseline.

## References

- [DEC CRT Typography — Masswerk](https://www.masswerk.at/nowgobang/2019/dec-crt-typography) on dot-stretching (8×10 ROM → 10×10 displayed) and phosphor rendering.
- [VT220 Programmer Reference — Character Encoding](https://vt100.net/docs/vt220-rm/chapter2.html) for DEC MCS, Special Graphics, NRCS, and DRCS.
- [VT220 built-in glyphs reference](https://vt100.net/charsets/) for authoritative ROM shapes when drawing historically-faithful new glyphs.
- [Gunkies VT220](https://gunkies.org/wiki/VT220) — index of manuals on bitsavers.
