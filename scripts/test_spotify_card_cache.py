import unittest

from cache_spotify_card import MAX_BYTES, is_valid_svg, is_playing_card


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

    def test_offline_cards_are_never_saved(self):
        live = b'<svg xmlns="http://www.w3.org/2000/svg"><div class="artist">Artist</div><div class="song">Song</div></svg>'
        offline = b'<svg xmlns="http://www.w3.org/2000/svg"><div class="artist">Offline</div><div class="song">Currently not playing on Spotify</div></svg>'
        self.assertTrue(is_playing_card(live, "image/svg+xml"))
        self.assertFalse(is_playing_card(offline, "image/svg+xml"))
        self.assertFalse(is_playing_card(b'<svg xmlns="http://www.w3.org/2000/svg"/>', "image/svg+xml"))
