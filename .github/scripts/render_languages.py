#!/usr/bin/env python3
"""Render a self-contained, refresh-animated GitHub language card."""
from __future__ import annotations

import html
import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

USER = "ryouy"
ROOT = Path(__file__).resolve().parents[2]
SVG_PATH = ROOT / "assets" / "languages-animated.svg"
README_PATH = ROOT / "README.md"

ORIGINAL_IMAGE = '<img src="https://github-readme-stats.vercel.app/api/top-langs/?username=ryouy&layout=compact&theme=tokyonight&hide_border=true&langs_count=7&card_width=500" width="500" alt="Most used programming languages">'
NEW_IMAGE = '<img src="./assets/languages-animated.svg" width="500" alt="Animated Most Used Languages chart">'

LANGUAGE_COLORS = {
    "Python": "#3572A5",
    "Jupyter Notebook": "#DA5B0B",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "HTML": "#e34c26",
    "CSS": "#663399",
    "SCSS": "#c6538c",
    "Vue": "#41b883",
    "Svelte": "#ff3e00",
    "Java": "#b07219",
    "C": "#555555",
    "C++": "#f34b7d",
    "C#": "#178600",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Shell": "#89e051",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "Dart": "#00B4AB",
    "PHP": "#4F5D95",
    "Ruby": "#701516",
}


def get_json(path: str):
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ryouy-profile-language-card",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request("https://api.github.com" + path, headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def fetch_languages() -> Counter:
    repositories = []
    for page in range(1, 11):
        chunk = get_json(
            f"/users/{USER}/repos?type=owner&per_page=100&page={page}&sort=updated"
        )
        if not isinstance(chunk, list):
            raise RuntimeError("Unexpected repository list from GitHub.")
        repositories.extend(chunk)
        if len(chunk) < 100:
            break
    else:
        raise RuntimeError("Repository pagination exceeded configured limit.")

    counts = Counter()
    eligible = 0
    for repo in repositories:
        if repo.get("fork") or repo.get("archived") or repo.get("disabled"):
            continue
        if not repo.get("full_name"):
            continue
        eligible += 1
        name = urllib.parse.quote(repo["full_name"], safe="/")
        languages = get_json(f"/repos/{name}/languages")
        if not isinstance(languages, dict):
            raise RuntimeError(f"Unexpected language data for {name}.")
        for language, num_bytes in languages.items():
            if isinstance(num_bytes, int) and num_bytes > 0:
                counts[language] += num_bytes

    if not counts:
        raise RuntimeError(f"No public language data for {USER} in {eligible} repositories.")
    return counts


def render_card(counts: Counter) -> str:
    top = counts.most_common(7)
    total = sum(counts.values())
    bar_x, bar_y, bar_w, bar_h = 22, 62, 456, 14

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="500" height="225" viewBox="0 0 500 225" role="img" aria-label="Most Used Languages">',
        f'<title>Most Used Languages · {USER}</title>',
        '<desc>Language share by source-code bytes in public non-fork repositories. The bar and labels animate when this image loads.</desc>',
        '<rect width="500" height="225" rx="12" fill="#1a1b27"/>',
        '<text x="22" y="37" fill="#70a5fd" font-family="Arial,Helvetica,sans-serif" font-weight="700" font-size="19">Most Used Languages</text>',
        f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="7" fill="#30364c"/>',
        '<defs><clipPath id="bar-progress-clip">',
        f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="7">',
        f'<animate attributeName="width" from="0" to="{bar_w}" begin="0.03s" dur="1.15s" fill="freeze"/>',
        '</rect></clipPath></defs>',
        '<g clip-path="url(#bar-progress-clip)">',
    ]
    progress = 0
    for language, num_bytes in top:
        segment = bar_w * num_bytes / total
        color = LANGUAGE_COLORS.get(language, "#7aa2f7")
        lines.append(
            f'<rect x="{bar_x + progress:.3f}" y="{bar_y}" width="{segment + 0.002:.3f}" height="{bar_h}" fill="{color}"/>'
        )
        progress += segment
    lines.append('</g>')

    for idx, (language, num_bytes) in enumerate(top):
        col, row = idx % 2, idx // 2
        x = 22 if col == 0 else 270
        y = 107 + 30 * row
        color = LANGUAGE_COLORS.get(language, "#7aa2f7")
        percentage = num_bytes * 100 / total
        name = html.escape(language)
        lines.extend([
            '<g opacity="1">',
            f'<animate attributeName="opacity" from="0" to="1" begin="{0.15 + idx * 0.1:.2f}s" dur="0.36s" fill="freeze"/>',
            f'<circle cx="{x + 5}" cy="{y - 5}" r="5" fill="{color}"/>',
            f'<text x="{x + 18}" y="{y}" fill="#c0caf5" font-family="Arial,Helvetica,sans-serif" font-size="13">{name}</text>',
            f'<text x="{x + 223}" y="{y}" fill="#9aa5c6" font-family="Arial,Helvetica,sans-serif" font-size="12" text-anchor="end">{percentage:.1f}%</text>',
            '</g>',
        ])
    lines.append('</svg>')
    svg = "\n".join(lines) + "\n"
    ET.fromstring(svg)
    return svg


def main():
    counts = fetch_languages()
    svg = render_card(counts)
    old_readme = README_PATH.read_text(encoding="utf-8")

    if ORIGINAL_IMAGE in old_readme:
        new_readme = old_readme.replace(ORIGINAL_IMAGE, NEW_IMAGE, 1)
    elif NEW_IMAGE in old_readme:
        new_readme = old_readme
    else:
        raise RuntimeError("Expected language card marker was not found; README unchanged.")

    SVG_PATH.parent.mkdir(parents=True, exist_ok=True)
    SVG_PATH.write_text(svg, encoding="utf-8")
    if new_readme != old_readme:
        README_PATH.write_text(new_readme, encoding="utf-8")
    print("Updated language chart:", ", ".join(k for k, v in counts.most_common(7)))


if __name__ == "__main__":
    main()
