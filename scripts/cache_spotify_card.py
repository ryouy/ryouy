#!/usr/bin/env python3
"""Keep the last successful Spotify SVG when the provider fails during ads.

GitHub Actions updates this repository-backed fallback at a low frequency.
The Vercel proxy serves the provider directly when it is healthy.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "spotify-last-good.svg"
SOURCE = (
    "https://spotify-github-profile.kittinanx.com/api/view"
    "?uid=31ransghntv6c7ihvjpjkkn54uju"
    "&cover_image=true&theme=default&show_offline=true"
    "&background_color=101b2b&interchange=false"
    "&profanity=false&hide_remaster=false"
)
MAX_BYTES = 2_000_000


def is_valid_svg(body: bytes, content_type: str) -> bool:
    """Reject HTML error pages and malformed or excessively large responses."""
    if not body or len(body) > MAX_BYTES:
        return False
    if "image/svg+xml" not in content_type.lower():
        return False
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return False
    return root.tag == "svg" or root.tag.endswith("}svg")


def refresh_card() -> bool:
    request = Request(SOURCE, headers={"User-Agent": "ryouy-profile-card-cache/1.0"})
    try:
        with urlopen(request, timeout=12) as response:
            body = response.read(MAX_BYTES + 1)
            content_type = response.headers.get("Content-Type", "")
            if response.status != 200 or not is_valid_svg(body, content_type):
                print("Provider did not return a valid Spotify SVG; keeping last good card")
                return False
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        print(f"Spotify temporarily unavailable ({type(error).__name__}); keeping last good card")
        return False

    if OUTPUT.exists() and OUTPUT.read_bytes() == body:
        print("Spotify card unchanged")
        return False
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(body)
    print(f"Cached latest healthy Spotify card ({len(body)} bytes)")
    return True


if __name__ == "__main__":
    refresh_card()
