#!/usr/bin/env python3
"""Single-command unattended build of GlassTTYVT220-Modern.ttf.

Usage:
    python3 build.py

Requires fontTools (see requirements.txt).
"""

from __future__ import annotations

import sys

from tools.build_font import build
from tools.verify import verify


def main() -> int:
    out = build()
    verify(out)
    print(f"wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
