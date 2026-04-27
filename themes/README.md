# GlassTTY Ghostty Themes

This directory contains two Ghostty themes designed for GlassTTY VT220:

- `GlassTTY-Amber` - dark amber phosphor colors.
- `GlassTTY-Green` - dark green phosphor colors.

Both themes keep normal text in a single phosphor color and make bold text brighter, rather than heavier. That mirrors the practical VT220-style behavior where bold/intense text was an intensity change on the display, not a separate bold typeface.

## Install

Ghostty looks for custom themes by name in:

```sh
~/.config/ghostty/themes
```

Create that directory and copy the theme files:

```sh
mkdir -p ~/.config/ghostty/themes
cp themes/GlassTTY-Amber ~/.config/ghostty/themes/
cp themes/GlassTTY-Green ~/.config/ghostty/themes/
```

Then set one of these in your Ghostty config file, usually `~/.config/ghostty/config`:

```ini
theme = GlassTTY-Amber
```

or:

```ini
theme = GlassTTY-Green
```

Reload Ghostty after changing the config.

You can also load a theme directly by absolute path:

```ini
theme = /absolute/path/to/glasstty/themes/GlassTTY-Amber
```

## Recommended Font Setting

The themes do not force a font family. To use the font from this repository, add this to your Ghostty config:

```ini
font-family = "Glass TTY VT220"
```

If you use the modernized build, use the family name installed by that font instead:

```ini
font-family = "Glass TTY VT220 Modern"
```

You may also want to set a larger font size. The original GlassTTY notes suggested larger sizes, and the CRT-style scanline shapes are easier to read when the cell grid has enough pixels:

```ini
font-size = 20
```

## Theme Details

Each theme is a normal Ghostty configuration file. The important settings are:

- `background` and `foreground` define the default terminal colors.
- `palette = 0..15` defines the ANSI normal and bright color slots.
- `bold-color = bright` tells Ghostty to map bold/intense text to the bright palette slots.
- `font-style-bold = false` and `font-style-bold-italic = false` tell Ghostty to render bold requests with the regular font style.
- `font-synthetic-style = no-bold,no-bold-italic` prevents Ghostty from synthesizing heavier bold outlines when the font lacks a bold face.

The regular foreground is palette slot 7. The brighter bold/intense foreground is palette slot 15. The remaining ANSI colors stay close to the phosphor family so terminal applications can still use color without breaking the amber or green terminal feel.
