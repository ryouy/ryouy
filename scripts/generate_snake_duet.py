#!/usr/bin/env python3
"""Experimental red-eats / blue-restores contribution snake.

Read Platane/snk SVGs from the existing output branch; never modify those files
or their workflow. The cell and progress animations alternate forward/backward.
A red snake runs during the forward half and a blue snake during the reverse
half. Blue segment sizes are reversed so its head leads in reverse motion and
the original contribution colors reappear behind its tail.

Only stdlib is required. For a reproducible offline build:
  python scripts/generate_snake_duet.py --source-light input.svg \
    --source-dark input-dark.svg --output-dir /tmp/snake-duet
"""
from __future__ import annotations

import argparse
import copy
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import Request, urlopen

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
ROOT = Path(__file__).resolve().parents[1]


def build_duet(source: str, cycle_seconds: float = 48) -> str:
    if cycle_seconds <= 0:
        raise ValueError("Cycle duration must be positive")
    root = ET.fromstring(source)
    style = root.find(f"{{{NS}}}style")
    if style is None or not style.text:
        raise ValueError("Expected a Platane/snk SVG with embedded animation CSS")
    # Fail explicitly if upstream changes its animation structure.
    if not all(token in style.text for token in ("@keyframes s0", ".c{", ".s{")):
        raise ValueError("Unrecognized source animation structure")
    segments = [el for el in root if "s" in el.get("class", "").split()]
    if len(segments) < 2:
        raise ValueError("Expected multiple animated snake segments")
    for segment in segments:
        if segment.tag != f"{{{NS}}}rect":
            raise ValueError("Expected rectangular snake segments")
        classes = segment.get("class", "").split()
        if not any(re.fullmatch(r"s\d+", cls) for cls in classes):
            raise ValueError("Missing segment animation class")

    half_ms = cycle_seconds * 500
    full_ms = cycle_seconds * 1000
    style.text += f"""
/* Independent experiment: the original SVG and workflow are read-only. */
.c,.u{{animation-duration:{half_ms:g}ms;animation-direction:alternate}}
.s{{animation-duration:{half_ms:g}ms}}
.duet-red .s{{fill:#ef5350}}
.duet-blue .s{{fill:#4593f8;animation-direction:reverse}}
.duet-red{{animation:duet-red-phase {full_ms:g}ms steps(1,end) infinite}}
.duet-blue{{opacity:0;animation:duet-blue-phase {full_ms:g}ms steps(1,end) infinite}}
@keyframes duet-red-phase{{0%{{opacity:1}}50%,100%{{opacity:0}}}}
@keyframes duet-blue-phase{{0%{{opacity:0}}50%{{opacity:1}}100%{{opacity:0}}}}
@media(prefers-reduced-motion:reduce){{.c,.u{{animation:none}}.duet-red,.duet-blue{{animation:none;opacity:0}}}}
"""
    red = ET.SubElement(root, f"{{{NS}}}g", {"class": "duet-red"})
    blue = ET.SubElement(root, f"{{{NS}}}g", {"class": "duet-blue"})
    shape_keys = ("x", "y", "width", "height", "rx", "ry")
    for index, segment in enumerate(segments):
        root.remove(segment)
        red.append(copy.deepcopy(segment))
        restored = copy.deepcopy(segment)
        # Keep this segment's path; reverse its visual rank for the new head.
        shape = segments[len(segments) - index - 1]
        for key in shape_keys:
            if key in shape.attrib:
                restored.set(key, shape.get(key))
        blue.append(restored)
    root.set("role", "img")
    root.set("aria-label", "Red snake eats contributions; blue snake restores them")
    title = ET.Element(f"{{{NS}}}title")
    title.text = "Contribution snake duet — eat and restore"
    root.insert(0, title)
    desc = root.find(f"{{{NS}}}desc")
    if desc is not None:
        desc.text = ("Experimental extension of Platane/snk. The red snake eats "
                     "the grid, then the blue snake restores the original "
                     "contribution colors along the reversed route. "
                     "https://github.com/Platane/snk")
    return ET.tostring(root, encoding="unicode") + "\n"


def load_source(local: Path | None, repository: str, dark: bool) -> str:
    if local:
        return local.read_text(encoding="utf-8")
    filename = "github-contribution-grid-snake" + ("-dark" if dark else "") + ".svg"
    url = f"https://raw.githubusercontent.com/{repository}/output/{filename}"
    request = Request(url, headers={"User-Agent": "github-snake-duet/1.0"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="ryouy/ryouy")
    parser.add_argument("--source-light", type=Path)
    parser.add_argument("--source-dark", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "assets")
    parser.add_argument("--duration", type=float, default=48)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
        parser.error("Expected owner/repository")
    # Validate both inputs before writing either artifact.
    outputs = []
    for dark, local in ((False, args.source_light), (True, args.source_dark)):
        output = args.output_dir / ("snake-duet-dark.svg" if dark else "snake-duet.svg")
        if local and output.resolve() == local.resolve():
            parser.error("Output must not overwrite a source SVG")
        outputs.append((output, build_duet(load_source(local, args.repository, dark), args.duration)))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for output, svg in outputs:
        output.write_text(svg, encoding="utf-8")
        print(f"Generated {output.name}: {args.duration:g}s eat/restore loop")


if __name__ == "__main__":
    main()
