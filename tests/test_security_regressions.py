import unittest
from types import SimpleNamespace
from unittest.mock import patch

from discovery.config import DEFAULT_SESSION_SECRET, Settings
from mvp.rate_limit import client_key


class FakeRequest:
    def __init__(self, headers=None, host="10.0.0.10"):
        self.headers = headers or {}
        self.client = SimpleNamespace(host=host)


class RateLimitClientKeyTests(unittest.TestCase):
    def test_uses_proxy_appended_ip_not_spoofed_leftmost_xff(self):
        request = FakeRequest({"x-forwarded-for": "203.0.113.99, 198.51.100.42"})

        self.assertEqual(client_key(request), "198.51.100.42")

    def test_ignores_invalid_xff_entries_and_falls_back_to_client(self):
        request = FakeRequest({"x-forwarded-for": "spoofed, also-bad"}, host="10.1.2.3")

        self.assertEqual(client_key(request), "10.1.2.3")


class SessionSecretValidationTests(unittest.TestCase):
    def test_deployed_environment_rejects_default_secret(self):
        with patch.dict("os.environ", {"VERCEL": "1"}, clear=True):
            with self.assertRaises(RuntimeError):
                Settings(session_secret=DEFAULT_SESSION_SECRET).validate_session_secret()

    def test_deployed_environment_rejects_short_secret(self):
        with patch.dict("os.environ", {"VERCEL_ENV": "production"}, clear=True):
            with self.assertRaises(RuntimeError):
                Settings(session_secret="too-short").validate_session_secret()

    def test_deployed_environment_accepts_strong_secret(self):
        with patch.dict("os.environ", {"VERCEL": "1"}, clear=True):
            Settings(session_secret="a" * 32).validate_session_secret()

    def test_local_environment_allows_default_secret(self):
        with patch.dict("os.environ", {}, clear=True):
            Settings(session_secret=DEFAULT_SESSION_SECRET).validate_session_secret()


if __name__ == "__main__":
    unittest.main()
