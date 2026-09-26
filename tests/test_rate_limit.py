from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from mvp import rate_limit


def _request(host: str = "203.0.113.9") -> SimpleNamespace:
    return SimpleNamespace(headers={}, client=SimpleNamespace(host=host))


class EnforceRateLimitTests(unittest.TestCase):
    def test_configured_database_failure_fails_closed(self) -> None:
        settings = SimpleNamespace(database_url="postgres://example", rate_limit_per_minute=30)

        with (
            patch.object(rate_limit, "get_settings", return_value=settings),
            patch.object(rate_limit, "_db_check", return_value=False) as db_check,
            patch.object(rate_limit, "_memory_check") as memory_check,
        ):
            with self.assertRaises(HTTPException) as raised:
                rate_limit.enforce_rate_limit(_request(), scope="auth")

        self.assertEqual(raised.exception.status_code, 503)
        db_check.assert_called_once()
        memory_check.assert_not_called()

    def test_configured_database_success_does_not_use_memory_bucket(self) -> None:
        settings = SimpleNamespace(database_url="postgres://example", rate_limit_per_minute=30)

        with (
            patch.object(rate_limit, "get_settings", return_value=settings),
            patch.object(rate_limit, "_db_check", return_value=True) as db_check,
            patch.object(rate_limit, "_memory_check") as memory_check,
        ):
            rate_limit.enforce_rate_limit(_request(), scope="auth")

        db_check.assert_called_once()
        memory_check.assert_not_called()

    def test_local_without_database_uses_memory_bucket(self) -> None:
        settings = SimpleNamespace(database_url="", rate_limit_per_minute=30)

        with (
            patch.object(rate_limit, "get_settings", return_value=settings),
            patch.object(rate_limit, "_db_check") as db_check,
            patch.object(rate_limit, "_memory_check") as memory_check,
        ):
            rate_limit.enforce_rate_limit(_request(), scope="auth")

        db_check.assert_not_called()
        memory_check.assert_called_once()


if __name__ == "__main__":
    unittest.main()
