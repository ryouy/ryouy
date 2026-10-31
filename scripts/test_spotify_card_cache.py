import unittest

from cache_spotify_card import MAX_BYTES, is_valid_svg


class SpotifyCardCacheTests(unittest.TestCase):
    def test_valid_svg(self):
        self.assertTrue(is_valid_svg(b'<svg xmlns="http://www.w3.org/2000/svg"><title>Spotify</title></svg>', "image/svg+xml; charset=utf-8"))

    def test_html_and_errors_do_not_overwrite_the_cache(self):
        self.assertFalse(is_valid_svg(b'<html>500 Internal Server Error</html>', "text/html"))
        self.assertFalse(is_valid_svg(b'<svg', "image/svg+xml"))
        self.assertFalse(is_valid_svg(b'', "image/svg+xml"))
        self.assertFalse(is_valid_svg(b'<svg></svg>', "text/plain"))

    def test_oversized_response_is_rejected(self):
        self.assertFalse(is_valid_svg(b'x' * (MAX_BYTES + 1), "image/svg+xml"))
