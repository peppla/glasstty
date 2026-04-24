"""Generate dist/preview.html for visual inspection of all font variants.

Open the file in any browser to sanity-check each variant before installing
system-wide. @font-face loads every TTF straight out of dist/, so the page
renders exactly what ships. No server required — file:// works.
"""

from __future__ import annotations

import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"

FAMILY_MAIN = "GlassTTYModern"
FAMILY_OBLIQUE = "GlassTTYOblique"

# (display label, css family, css weight, css style, ttf filename)
VARIANTS = [
    ("Regular",         FAMILY_MAIN,    400, "normal", "GlassTTYVT220-Modern.ttf"),
    ("Italic",          FAMILY_MAIN,    400, "italic", "GlassTTYVT220-Modern-Italic.ttf"),
    ("SemiBold",        FAMILY_MAIN,    600, "normal", "GlassTTYVT220-Modern-SemiBold.ttf"),
    ("SemiBold Italic", FAMILY_MAIN,    600, "italic", "GlassTTYVT220-Modern-SemiBoldItalic.ttf"),
    ("Bold",            FAMILY_MAIN,    700, "normal", "GlassTTYVT220-Modern-Bold.ttf"),
    ("Bold Italic",     FAMILY_MAIN,    700, "italic", "GlassTTYVT220-Modern-BoldItalic.ttf"),
    ("Oblique",         FAMILY_OBLIQUE, 400, "normal", "GlassTTYVT220-Oblique.ttf"),
]

PANGRAM = (
    "The quick brown fox jumps over the lazy dog. "
    "Съешь же ещё этих мягких французских булок, да выпей чаю. "
    "Despús-ahir el pingüí bèl·lic atenyé aïrat l'emú esquifit "
    "i menjà zelós xoriç, òvid i kiwi."
)

SECTIONS = [
    ("ASCII upper",      "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    ("ASCII lower",      "abcdefghijklmnopqrstuvwxyz"),
    ("Digits",           "0123456789"),
    ("Punctuation",      "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"),
    ("Latin-1 accents",  "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞß àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"),
    ("Latin-1 symbols",  "¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿×÷"),
    ("Latin-9 deltas",   "Š š Ž ž Ÿ Œ œ €"),
    ("Cyrillic upper",   "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"),
    ("Cyrillic lower",   "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"),
    ("Smart quotes",     "‘single’ “double” – — … • ™"),
    ("Apostrophe vs U+2019", "'straight'  vs  ’smart’"),
    ("Math",             "≤ ≥ ≠ π"),
    ("Arrows",           "← ↑ → ↓ ↵"),
    ("Scanlines",        "⎺⎻⎼⎽"),
    ("No ligatures",     "-> != >= <= => == || && :: ++ --"),
]

BOX_DRAWING = """┌─────────────┐   ┌───┬───┬───┐
│ Box drawing │   │ A │ B │ C │
├─────────────┤   ├───┼───┼───┤
│ tiles clean │   │ D │ E │ F │
│ ─────────── │   ├───┼───┼───┤
└─────────────┘   └───┴───┴───┘"""

BLOCKS_LABELED = """████████████ full block   (U+2588)
▓▓▓▓▓▓▓▓▓▓▓▓ dark shade   (U+2593)
▒▒▒▒▒▒▒▒▒▒▒▒ medium shade (U+2592)
░░░░░░░░░░░░ light shade  (U+2591)

Ramp:      ░░░░▒▒▒▒▓▓▓▓████"""

TILE_TEST = """Tile test: ░░░░░░░░░░░░░░░░
           ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
           ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"""

CODE_SAMPLE = """/* smart-quote test: 'single' vs ‘smart’ */
int max(int a, int b) {
    if (a >= b && b != -1) return a;
    return b;  // arrows stay ASCII: a -> b, !=
}

struct Point {
    double x, y;
};"""


def _face_rules() -> str:
    rules = []
    for _label, family, weight, style, ttf in VARIANTS:
        rules.append(
            f"@font-face {{ font-family: '{family}'; src: url('{ttf}'); "
            f"font-weight: {weight}; font-style: {style}; }}"
        )
    return "\n".join(rules)


def _anchor(label: str) -> str:
    return label.lower().replace(" ", "-")


def _variant_block(label: str, family: str, weight: int, style: str) -> str:
    css = f"font-family: '{family}'; font-weight: {weight}; font-style: {style};"
    parts = [
        f'<h2 id="{_anchor(label)}">{html.escape(label)}</h2>',
        f'<div class="sample" style="{css}">{html.escape(PANGRAM)}</div>',
    ]
    for title, text in SECTIONS:
        parts.append(
            f'<div class="row">'
            f'<span class="label">{html.escape(title)}</span>'
            f'<span class="glyphs" style="{css}">{html.escape(text)}</span>'
            f'</div>'
        )
    parts.append(f'<pre class="block tight" style="{css}">{html.escape(BOX_DRAWING)}</pre>')
    parts.append(f'<pre class="block" style="{css}">{html.escape(BLOCKS_LABELED)}</pre>')
    parts.append(f'<pre class="block tight" style="{css}">{html.escape(TILE_TEST)}</pre>')
    parts.append(f'<pre class="block" style="{css}">{html.escape(CODE_SAMPLE)}</pre>')
    return f'<section class="variant">{"".join(parts)}</section>'


def render_html() -> str:
    body = "\n".join(
        _variant_block(label, family, weight, style)
        for label, family, weight, style, _ttf in VARIANTS
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Glass TTY VT220 Modern — preview</title>
<style>
{_face_rules()}
:root {{
  --fg: #b7ffbf;
  --fg-dim: #6a8a6f;
  --bg: #0c0c0c;
  --panel: #000;
  --border: #222;
  --rule: #333;
  --tick: #1a1a1a;
  --chrome: #8cf;
  --chrome-bright: #cff;
}}
body.amber {{
  --fg: #ffb000;
  --fg-dim: #8a6420;
  --bg: #100800;
  --border: #2a1a00;
  --rule: #3a2400;
  --tick: #1e1200;
}}
* {{ box-sizing: border-box; }}
html, body {{ background: var(--bg); color: var(--fg); margin: 0; }}
body {{ padding: 2em; font-family: -apple-system, system-ui, sans-serif; }}
h1 {{ color: var(--chrome-bright); font-weight: normal; margin: 0 0 .2em; }}
h2 {{ color: var(--chrome); margin-top: 2.5em; border-bottom: 1px solid var(--rule);
      padding-bottom: .25em; font-weight: normal; }}
p.note {{ color: var(--fg-dim); margin-top: 0; }}
.variant {{ margin-bottom: 3em; }}
.sample {{ font-size: 24px; line-height: 1.4; margin: 1em 0; padding: .6em .8em;
           background: var(--panel); border: 1px solid var(--border); }}
.row {{ display: grid; grid-template-columns: 170px 1fr; gap: 1em;
        align-items: center; padding: .35em 0; border-bottom: 1px dotted var(--tick); }}
.label {{ color: var(--fg-dim); font-size: 13px; }}
.glyphs {{ font-size: 22px; line-height: 1.25; white-space: pre-wrap;
           word-break: break-all; }}
.block {{ font-size: 20px; line-height: 1.2; background: var(--panel); padding: .6em .8em;
          margin: .8em 0 0; border: 1px solid var(--border); overflow-x: auto;
          white-space: pre; }}
.block.tight {{ line-height: 0.7; }}
nav {{ position: sticky; top: 0; background: var(--bg); padding: .4em 0 .8em;
       border-bottom: 1px solid var(--border); margin-bottom: 1em;
       display: flex; flex-wrap: wrap; align-items: center; gap: .5em 1em; }}
nav a {{ color: var(--chrome); text-decoration: none; font-size: 13px; }}
nav a:hover {{ text-decoration: underline; }}
.phosphor-toggle {{ margin-left: auto; background: transparent;
                    color: var(--chrome); border: 1px solid var(--chrome);
                    padding: .3em .8em; font-size: 12px; cursor: pointer;
                    font-family: inherit; }}
.phosphor-toggle:hover {{ background: var(--chrome); color: var(--bg); }}
</style>
</head>
<body>
<h1>Glass TTY VT220 Modern &mdash; preview</h1>
<p class="note">
Every variant shipped in <code>dist/</code> rendered by the browser.
If something looks wrong here, that's what will install.
</p>
<nav>
{''.join(f'<a href="#{_anchor(lbl)}">{html.escape(lbl)}</a>' for lbl, *_ in VARIANTS)}
<button class="phosphor-toggle" id="phosphor-toggle" type="button">Phosphor: green</button>
</nav>
{body}
<script>
(function () {{
  var KEY = 'glasstty-phosphor';
  var btn = document.getElementById('phosphor-toggle');
  function apply(mode) {{
    if (mode === 'amber') {{
      document.body.classList.add('amber');
      btn.textContent = 'Phosphor: amber';
    }} else {{
      document.body.classList.remove('amber');
      btn.textContent = 'Phosphor: green';
    }}
  }}
  apply(localStorage.getItem(KEY) === 'amber' ? 'amber' : 'green');
  btn.addEventListener('click', function () {{
    var next = document.body.classList.contains('amber') ? 'green' : 'amber';
    localStorage.setItem(KEY, next);
    apply(next);
  }});
}})();
</script>
</body>
</html>
"""


def main() -> Path:
    DIST.mkdir(exist_ok=True)
    out = DIST / "preview.html"
    out.write_text(render_html(), encoding="utf-8")
    return out


if __name__ == "__main__":
    path = main()
    print(f"wrote {path}")
