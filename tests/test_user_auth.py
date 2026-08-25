from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

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
    def test_google_sign_in_does_not_enter_password_account_with_same_email(self) -> None:
        profile = {
            "sub": "victim-google-id",
            "email": "victim@example.com",
            "email_verified": True,
            "name": "Victim",
        }
        existing_password_account = {
            "id": "attacker-created-user",
            "email": "victim@example.com",
            "password_hash": "scrypt$salt$digest",
            "display_name": "Victim",
            "google_id": None,
            "avatar_url": "",
            "created_at": "2026-08-25T00:00:00+00:00",
        }

        with (
            patch.object(user_auth, "get_settings", return_value=_settings()),
            patch.object(user_auth, "ensure_user_schema", return_value=True),
            patch.object(user_auth.httpx, "Client", return_value=_FakeGoogleClient(profile)),
            patch.object(user_auth, "get_user_by_google_id", return_value=None),
            patch.object(user_auth, "get_user_by_email", return_value=existing_password_account),
            patch.object(user_auth, "create_user") as create_user,
        ):
            user, err = user_auth.exchange_google_code("oauth-code")

        self.assertIsNone(user)
        self.assertEqual(
            err,
            "An account with this email already exists. Sign in with email and password.",
        )
        create_user.assert_not_called()

    def test_existing_google_linked_account_still_signs_in_by_google_id(self) -> None:
        profile = {
            "sub": "google-user-id",
            "email": "person@example.com",
            "email_verified": True,
            "name": "Person",
        }
        existing_google_account = {
            "id": "user-1",
            "email": "person@example.com",
            "password_hash": None,
            "display_name": "Person",
            "google_id": "google-user-id",
            "avatar_url": "",
            "created_at": "2026-08-25T00:00:00+00:00",
        }

        with (
            patch.object(user_auth, "get_settings", return_value=_settings()),
            patch.object(user_auth, "ensure_user_schema", return_value=True),
            patch.object(user_auth.httpx, "Client", return_value=_FakeGoogleClient(profile)),
            patch.object(user_auth, "get_user_by_google_id", return_value=existing_google_account),
            patch.object(user_auth, "get_user_by_email") as by_email,
            patch.object(user_auth, "create_user") as create_user,
        ):
            user, err = user_auth.exchange_google_code("oauth-code")

        self.assertIsNone(err)
        self.assertEqual(user, {k: v for k, v in existing_google_account.items() if k != "password_hash"})
        by_email.assert_not_called()
        create_user.assert_not_called()


if __name__ == "__main__":
    unittest.main()
