import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import rotate_profile_photo as photo

class PhotoTests(unittest.TestCase):
    def test_missing_or_empty_photo_directory_keeps_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(photo,'IMAGES',root/'missing'):
                self.assertIsNone(photo.select_photo())
            (root/'empty').mkdir()
            with patch.object(photo,'IMAGES',root/'empty'):
                self.assertIsNone(photo.select_photo())
    def test_fresh_output_directory_and_transparent_rounded_corners(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'portrait.png';output=root/'new-assets'/'current.webp'
            Image.new('RGB',(20,40),'blue').save(source)
            with patch.object(photo,'OUTPUT',output),patch.object(photo,'SIZE',(96,64)):
                photo.render_photo(source)
            with Image.open(output) as rendered:
                self.assertEqual(rendered.size,(96,64))
                self.assertEqual(rendered.getpixel((0,0))[3],0)
                self.assertEqual(rendered.getpixel((48,32))[3],255)
