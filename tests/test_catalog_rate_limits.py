import unittest
from unittest.mock import patch

from fastapi import HTTPException

from api import main


class CatalogRateLimitTests(unittest.TestCase):
    def _limit(self, *_args, **_kwargs):
        raise HTTPException(status_code=429, detail="limited")

    def test_search_tracks_is_rate_limited_before_spotify(self):
        with (
            patch("api.main.enforce_rate_limit", side_effect=self._limit) as limited,
            patch("api.main.SpotifyClient.from_client_credentials") as spotify,
        ):
            with self.assertRaises(HTTPException) as ctx:
                main.api_search_tracks("khruangbin", request=object())

        self.assertEqual(ctx.exception.status_code, 429)
        limited.assert_called_once()
        self.assertEqual(limited.call_args.kwargs["scope"], "catalog")
        spotify.assert_not_called()

    def test_track_lookup_is_rate_limited_before_lookup(self):
        with (
            patch("api.main.enforce_rate_limit", side_effect=self._limit) as limited,
            patch("api.main.lookup_track") as lookup,
        ):
            with self.assertRaises(HTTPException) as ctx:
                main.api_track_lookup("0" * 22, request=object())

        self.assertEqual(ctx.exception.status_code, 429)
        limited.assert_called_once()
        self.assertEqual(limited.call_args.kwargs["scope"], "catalog")
        lookup.assert_not_called()

    def test_track_lookup_post_is_rate_limited_before_lookup(self):
        with (
            patch("api.main.enforce_rate_limit", side_effect=self._limit) as limited,
            patch("api.main.lookup_track") as lookup,
        ):
            with self.assertRaises(HTTPException) as ctx:
                main.api_track_lookup_post({"anchor": "0" * 22}, request=object())

        self.assertEqual(ctx.exception.status_code, 429)
        limited.assert_called_once()
        self.assertEqual(limited.call_args.kwargs["scope"], "catalog")
        lookup.assert_not_called()

    def test_preview_is_rate_limited_before_preview_lookup(self):
        with (
            patch("api.main.enforce_rate_limit", side_effect=self._limit) as limited,
            patch("api.main.lookup_preview_url") as preview,
        ):
            with self.assertRaises(HTTPException) as ctx:
                main.api_preview(request=object(), name="Song", artist="Artist")

        self.assertEqual(ctx.exception.status_code, 429)
        limited.assert_called_once()
        self.assertEqual(limited.call_args.kwargs["scope"], "catalog")
        preview.assert_not_called()


if __name__ == "__main__":
    unittest.main()
