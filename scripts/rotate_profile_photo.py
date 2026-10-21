#!/usr/bin/env python3
"""Rotate the GitHub README profile photo without changing its displayed aspect ratio.

Place additional photos in images/ (JPG, PNG, WEBP, HEIC, etc.).
The generated assets/profile-current.jpg always has the same 4:5 canvas,
and the original image is never cropped; blurred edges fill the remaining space.
"""
from __future__ import annotations

import secrets
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

register_heif_opener()

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
IMAGES = ROOT / "images"
OUTPUT = ASSETS / "profile-current.jpg"
LAST_SELECTION = ASSETS / ".profile-last.txt"
SIZE = (800, 1000)  # Consistent display geometry for portrait and landscape photos.
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".bmp", ".tif", ".tiff"}
EXCLUDED = {
    "profile-current.jpg",
    "stats-column.png",  # Old generated statistics, not a photograph.
}


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
        photo for photo in sorted(list(ASSETS.iterdir()) + list(IMAGES.iterdir()))
        if photo.is_file()
        and photo.suffix.lower() in EXTENSIONS
        and photo.name not in EXCLUDED
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

    # Fit the entire foreground within the canvas: never crop heads or scenery.
    foreground = ImageOps.contain(
        rgba, (SIZE[0] - 24, SIZE[1] - 24), method=Image.Resampling.LANCZOS
    )
    x = (SIZE[0] - foreground.width) // 2
    y = (SIZE[1] - foreground.height) // 2
    card.alpha_composite(foreground, (x, y))
    card.convert("RGB").save(OUTPUT, "JPEG", quality=87, optimize=True, progressive=True)


def main() -> None:
    chosen = select_photo()
    if chosen is None:
        print("No photos in assets/: keeping the last generated image unchanged.")
        return

    render_photo(chosen)
    LAST_SELECTION.write_text(str(chosen.relative_to(ROOT)) + "\n", encoding="utf-8")
    print(f"Selected {chosen.name}; wrote {OUTPUT.relative_to(ROOT)} at {SIZE[0]}x{SIZE[1]}.")


if __name__ == "__main__":
    main()
