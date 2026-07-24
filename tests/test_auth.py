import time
import unittest
from unittest.mock import patch

from mvp.auth import refreshed_session_cookie
from mvp.session import pack_session, unpack_session
from mvp.spotify_client import SpotifyAPIError


class RefreshedSessionCookieTests(unittest.TestCase):
    def test_refresh_failure_returns_none(self):
        cookie = pack_session("old-access", "revoked-refresh", time.time() - 10)

        with patch(
            "mvp.auth.SpotifyClient.refresh",
            side_effect=SpotifyAPIError("expired", 401, "auth_expired"),
        ):
            self.assertIsNone(refreshed_session_cookie(cookie))

    def test_refresh_success_repackages_new_tokens(self):
        cookie = pack_session("old-access", "refresh", time.time() - 10)

        with patch(
            "mvp.auth.SpotifyClient.refresh",
            return_value={
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_at": time.time() + 3600,
            },
        ):
            refreshed = refreshed_session_cookie(cookie)

        data = unpack_session(refreshed)
        self.assertIsNotNone(data)
        self.assertEqual(data["access_token"], "new-access")
        self.assertEqual(data["refresh_token"], "new-refresh")


if __name__ == "__main__":
    unittest.main()
