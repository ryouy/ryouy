# Profile photos

Put original photographs in this directory (JPG, PNG, WebP, HEIC, etc.).
`scripts/rotate_profile_photo.py` picks from **images/** every hour and generates the
rounded, 3:2 `assets/profile-current.webp` card used by the profile README.
Portrait photographs are retained in full with a blurred backdrop.

Keep original photos here. Generated output belongs in `assets/`.
