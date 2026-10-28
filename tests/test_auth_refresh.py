import time
import unittest
from unittest.mock import patch

from mvp.auth import refreshed_session_cookie
from mvp.session import pack_session
from mvp.spotify_client import SpotifyAPIError


class FailingSpotifyClient:
    def __init__(self, access_token: str, refresh_token: str = "") -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token

    def refresh(self) -> dict:
        raise SpotifyAPIError("Session expired", 401, "auth_expired")


class RefreshedSessionCookieTest(unittest.TestCase):
    def test_refresh_failure_returns_none(self) -> None:
        cookie = pack_session(
            "expired-access-token",
            "revoked-refresh-token",
            time.time() - 60,
        )

        with patch("mvp.auth.SpotifyClient", FailingSpotifyClient):
            self.assertIsNone(refreshed_session_cookie(cookie))


if __name__ == "__main__":
    unittest.main()
