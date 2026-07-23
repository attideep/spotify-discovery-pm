from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from mvp import user_auth


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class _FakeGoogleClient:
    def __init__(self, profile: dict) -> None:
        self.profile = profile

    def __enter__(self) -> "_FakeGoogleClient":
        return self

    def __exit__(self, *args) -> None:
        return None

    def post(self, *args, **kwargs) -> _FakeResponse:
        return _FakeResponse(200, {"access_token": "google-access-token"})

    def get(self, *args, **kwargs) -> _FakeResponse:
        return _FakeResponse(200, self.profile)


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        google_client_id="client-id",
        google_client_secret="client-secret",
        api_base_url="https://example.test",
    )


class GoogleOAuthTests(unittest.TestCase):
    def test_unverified_google_email_is_rejected_before_account_lookup(self) -> None:
        profile = {
            "sub": "google-user-id",
            "email": "victim@example.com",
            "email_verified": False,
            "name": "Victim",
        }

        with (
            patch.object(user_auth, "get_settings", return_value=_settings()),
            patch.object(user_auth, "ensure_user_schema", return_value=True),
            patch.object(user_auth.httpx, "Client", return_value=_FakeGoogleClient(profile)),
            patch.object(user_auth, "get_user_by_google_id") as by_google_id,
            patch.object(user_auth, "get_user_by_email") as by_email,
            patch.object(user_auth, "create_user") as create_user,
        ):
            user, err = user_auth.exchange_google_code("oauth-code")

        self.assertIsNone(user)
        self.assertEqual(err, "Google account email is not verified.")
        by_google_id.assert_not_called()
        by_email.assert_not_called()
        create_user.assert_not_called()

    def test_verified_google_email_can_sign_into_matching_existing_account(self) -> None:
        profile = {
            "sub": "google-user-id",
            "email": " Victim@Example.com ",
            "email_verified": True,
            "name": "Victim",
        }
        existing = {
            "id": "user-1",
            "email": "victim@example.com",
            "password_hash": "scrypt$hash",
            "display_name": "Victim",
            "google_id": None,
            "avatar_url": "",
            "created_at": "2026-07-23T00:00:00+00:00",
        }

        with (
            patch.object(user_auth, "get_settings", return_value=_settings()),
            patch.object(user_auth, "ensure_user_schema", return_value=True),
            patch.object(user_auth.httpx, "Client", return_value=_FakeGoogleClient(profile)),
            patch.object(user_auth, "get_user_by_google_id", return_value=None),
            patch.object(user_auth, "get_user_by_email", return_value=existing) as by_email,
            patch.object(user_auth, "create_user") as create_user,
        ):
            user, err = user_auth.exchange_google_code("oauth-code")

        self.assertIsNone(err)
        self.assertEqual(user, {k: v for k, v in existing.items() if k != "password_hash"})
        by_email.assert_called_once_with("victim@example.com")
        create_user.assert_not_called()


if __name__ == "__main__":
    unittest.main()
