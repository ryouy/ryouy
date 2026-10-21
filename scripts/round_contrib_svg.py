#!/usr/bin/env python3
"""Clip the generated 3D contribution SVG to a softly rounded card.

The 3D action recreates its SVG every run; apply this after generation so
the frame keeps its rounded corners when the contribution history changes.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "profile-3d-contrib" / "profile-night-view.svg"
CLIP_ID = "ryouy-rounded-3d-frame"


def apply_rounding() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(TARGET)

    svg = TARGET.read_text(encoding="utf-8")
    if f'id="{CLIP_ID}"' in svg:
        print("3D contribution card is already rounded.")
        return

    match = re.search(
        r'<svg\b[^>]*\bviewBox="([^"]+)"[^>]*>', svg, flags=re.IGNORECASE
    )
    if not match:
        raise ValueError("3D contribution SVG is missing its viewBox.")
    x, y, width, height = [float(value) for value in match.group(1).split()]
    radius = round(min(width, height) * 0.03, 1)
    clip = (
        f'<defs><clipPath id="{CLIP_ID}">'
        f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" '
        f'rx="{radius:g}" ry="{radius:g}"/>'
        '</clipPath></defs>'
        f'<g clip-path="url(#{CLIP_ID})">'
    )

    # Leave SVG <style> at root level and clip the background plus all content.
    styles_end = svg.find("</style>")
    if styles_end < match.end():
        raise ValueError("Unexpected SVG: could not locate the root style.")
    insertion = styles_end + len("</style>")
    if not svg.rstrip().endswith("</svg>"):
        raise ValueError("Unexpected 3D contribution SVG ending.")

    rounded = svg[:insertion] + clip + svg[insertion:]
    closing = rounded.rfind("</svg>")
    rounded = rounded[:closing] + "</g>" + rounded[closing:]
    TARGET.write_text(rounded, encoding="utf-8")
    print(f"Rounded 3D contribution card with {radius:g}px corner radius.")


if __name__ == "__main__":
    apply_rounding()
