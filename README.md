# GlassTTY: TrueType VT220 font

This repository is a fork of Viacheslav Slavinsky's **GlassTTY VT220** TrueType font. All credit for the original glyph work, the VT220 bitmap extraction (`VT200`, `vtparse.py`), and the source `Glass_TTY_VT220.ttf` goes to him — original project page: http://sensi.org/~svo/glasstty.

The fork adds a modernization pipeline (`build.py` + `tools/`) that extends the original font with missing characters (Euro, Latin-9, arrows, box drawing, block elements) and derives weight and slant variants, while preserving Slavinsky's pixel style exactly. The original `Glass_TTY_VT220.ttf` is included unchanged.

Download the unmodified original: [Glass_TTY_VT220.ttf](Glass_TTY_VT220.ttf).

## No programming ligatures

The Modern variants will not ship programming ligatures (`->` → `→`, `!=` → `≠`, `>=` → `≥`, `=>` → `⇒`, etc.). The reasoning, following Matthew Butterick's [Ligatures in programming fonts: hell no](https://practicaltypography.com/ligatures-in-programming-fonts-hell-no.html):

- **Unicode collision.** Rendering `!=` as `≠` makes it visually indistinguishable from the real `U+2260`, and likewise for every other ligated pair. Two distinct source strings are no longer distinguishable on screen — in code, that's a bug surface, not a feature.
- **Context-free substitution is semantically wrong.** Ligature lookup matches character sequences, not meaning. The same bytes can mean different things across languages, inside strings, inside regexes, inside comments — any ligature rule is guaranteed to misfire some of the time.
- **VT220-specific.** A terminal font lives on a fixed character grid. Merging adjacent cells into a single wider glyph breaks that grid and the scanline aesthetic this font exists to preserve.

If you want ligatures, Fira Code and JetBrains Mono already do it well. This font is for people who want the VT220 cell grid untouched.

GlassTTY VT220 is free and unencumbered software released into the public domain. For details, see [LICENSE](LICENSE).
