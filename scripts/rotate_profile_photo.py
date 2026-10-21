#!/usr/bin/env python3
"""Rotate the GitHub README profile photo without changing its displayed aspect ratio.

Put original photos in images/ (JPG, PNG, WEBP, HEIC, etc.).
The generated assets/profile-current.webp uses a consistent 3:2 landscape canvas.
Photos close to that ratio are gently cropped; portraits and extreme ratios
are shown in full against a blurred background. Only images/ is scanned.
"""
from __future__ import annotations

import hashlib
import re
import secrets
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

register_heif_opener()

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
IMAGES = ROOT / "images"
OUTPUT = ASSETS / "profile-current.webp"
LAST_SELECTION = ASSETS / ".profile-last.txt"
README = ROOT / "README.md"
# A changing query string forces the GitHub README image proxy to request fresh artwork.
PHOTO_TAG = re.compile(r'(?<=src=")\./assets/profile-current\.(?:jpg|webp)(?:\?v=[0-9a-f]{12})?(?=")')
SIZE = (960, 640)  # Desktop-friendly 3:2 image; stable layout across source photos.
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".bmp", ".tif", ".tiff"}

def valid_photo(path: Path) -> bool:
    try:
        with Image.open(path) as picture:
            picture.verify()
        return True
    except (OSError, ValueError, UnidentifiedImageError):
        print(f"Skipping unsupported or damaged photo: {path.name}")
        return False


def select_photo() -> Path | None:
    candidates = [
        photo for photo in sorted(IMAGES.iterdir())
        if photo.is_file()
        and photo.suffix.lower() in EXTENSIONS
        and valid_photo(photo)
    ]
    if not candidates:
        return None

    previous = LAST_SELECTION.read_text(encoding="utf-8").strip() if LAST_SELECTION.exists() else ""
    alternatives = [photo for photo in candidates if str(photo.relative_to(ROOT)) != previous]
    return secrets.choice(alternatives or candidates)


def render_photo(source: Path) -> None:
    with Image.open(source) as original:
        oriented = ImageOps.exif_transpose(original)
        rgba = oriented.convert("RGBA")

    # A dark, blurred background fills a fixed canvas without letterboxing.
    backdrop = ImageOps.fit(rgba, SIZE, method=Image.Resampling.LANCZOS)
    backdrop = backdrop.filter(ImageFilter.GaussianBlur(radius=30))
    tint = Image.new("RGBA", SIZE, "#101b2b")
    card = Image.blend(backdrop, tint, 0.28)

    # Slightly crop landscape images close to the target aspect ratio.
    # For portraits and very wide photos, retain the whole image with a soft backdrop.
    ratio = rgba.width / rgba.height
    if 1.27 <= ratio <= 1.80:
        foreground = ImageOps.fit(
            rgba, SIZE, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)
        )
    else:
        foreground = ImageOps.contain(
            rgba, (SIZE[0] - 18, SIZE[1] - 18), method=Image.Resampling.LANCZOS
        )
    x = (SIZE[0] - foreground.width) // 2
    y = (SIZE[1] - foreground.height) // 2
    card.alpha_composite(foreground, (x, y))
    # Render real transparent rounded corners. GitHub does not preserve custom CSS
    # border-radius styling in profile READMEs; the output itself must be rounded.
    # Supersample the corner mask for smooth anti-aliased edges.
    scale = 3
    radius = 27
    mask_large = Image.new("L", (SIZE[0] * scale, SIZE[1] * scale), 0)
    draw = ImageDraw.Draw(mask_large)
    draw.rounded_rectangle(
        (0, 0, SIZE[0] * scale - 1, SIZE[1] * scale - 1),
        radius=radius * scale,
        fill=255,
    )
    alpha = mask_large.resize(SIZE, Image.Resampling.LANCZOS)
    card.putalpha(alpha)
    card.save(OUTPUT, "WEBP", quality=87, method=6)


def refresh_readme_photo_url() -> None:
    """Update the README URL when the generated photo actually changes.

    GitHub caches README images independently of the linked original. Keeping
    the same image path can leave the profile showing an older thumbnail.
    """
    token = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()[:12]
    current = README.read_text(encoding="utf-8")
    refreshed, occurrences = PHOTO_TAG.subn(
        f"./assets/profile-current.webp?v={token}", current
    )
    if occurrences != 1:
        raise RuntimeError("Expected one versioned profile photo <img> in README.md")
    if refreshed != current:
        README.write_text(refreshed, encoding="utf-8")
    print(f"Profile README image cache key: {token}")


def main() -> None:
    chosen = select_photo()
    if chosen is None:
        print("No valid photos in images/: keeping last generated image unchanged.")
        return

    render_photo(chosen)
    refresh_readme_photo_url()
    LAST_SELECTION.write_text(str(chosen.relative_to(ROOT)) + "\n", encoding="utf-8")
    print(f"Selected {chosen.name}; wrote {OUTPUT.relative_to(ROOT)} at {SIZE[0]}x{SIZE[1]}.")


if __name__ == "__main__":
    main()
