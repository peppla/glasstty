#!/usr/bin/env python3
"""Single-command unattended build of all Glass TTY VT220 Modern variants.

Usage:
    python3 build.py

Produces in dist/:
    GlassTTYVT220-Modern.ttf         — Regular (preserves the original pixel style)
    GlassTTYVT220-Modern-Bold.ttf    — Bold: VT220 dot-stretching applied
    GlassTTYVT220-Strong.ttf         — Strong: dot-stretching + partial
                                        scanline-gap fill; its own family

Requires fontTools (see requirements.txt).
"""

from __future__ import annotations

import sys

from tools.build_font import build_all
from tools.verify import verify


def main() -> int:
    outputs = build_all()
    for out in outputs:
        verify(out)
        print(f"wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
