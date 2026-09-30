import unittest
from types import SimpleNamespace

from fastapi import HTTPException
from starlette.datastructures import Headers

from api.main import _authorize_ingest


class DummyRequest:
    def __init__(self, headers: dict[str, str] | None = None) -> None:
        self.headers = Headers(headers or {})


class IngestAuthTests(unittest.TestCase):
    def test_live_ingest_is_disabled_without_admin_token(self) -> None:
        settings = SimpleNamespace(mock_mode=False, ingest_admin_token="")

        with self.assertRaises(HTTPException) as raised:
            _authorize_ingest(DummyRequest(), settings)

        self.assertEqual(raised.exception.status_code, 403)

    def test_mock_ingest_allows_local_seed_without_admin_token(self) -> None:
        settings = SimpleNamespace(mock_mode=True, ingest_admin_token="")

        _authorize_ingest(DummyRequest(), settings)

    def test_live_ingest_accepts_matching_admin_header(self) -> None:
        settings = SimpleNamespace(mock_mode=False, ingest_admin_token="secret-token")

        _authorize_ingest(
            DummyRequest({"x-ingest-admin-token": "secret-token"}),
            settings,
        )

    def test_live_ingest_accepts_bearer_token(self) -> None:
        settings = SimpleNamespace(mock_mode=False, ingest_admin_token="secret-token")

        _authorize_ingest(
            DummyRequest({"authorization": "Bearer secret-token"}),
            settings,
        )

    def test_live_ingest_rejects_wrong_admin_token(self) -> None:
        settings = SimpleNamespace(mock_mode=False, ingest_admin_token="secret-token")

        with self.assertRaises(HTTPException) as raised:
            _authorize_ingest(
                DummyRequest({"x-ingest-admin-token": "wrong-token"}),
                settings,
            )

        self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
