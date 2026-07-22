from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import mvp.user_store as user_store


class FakeCursor:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, statement: str, *args) -> None:
        self.statements.append(statement)


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.closed = False

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def cursor(self) -> FakeCursor:
        return self._cursor

    def close(self) -> None:
        self.closed = True


class UserStorePostgresTests(unittest.TestCase):
    def setUp(self) -> None:
        user_store._user_schema_ready = False

    def tearDown(self) -> None:
        user_store._user_schema_ready = False

    def test_configured_postgres_does_not_fall_back_to_sqlite_when_unavailable(self) -> None:
        settings = SimpleNamespace(database_url="postgresql://example/db")
        with (
            patch.object(user_store, "get_settings", return_value=settings),
            patch.object(user_store, "_pg_conn", return_value=None),
            patch.object(user_store, "_sqlite_conn", side_effect=AssertionError("sqlite fallback used")),
        ):
            self.assertFalse(user_store.ensure_user_schema())
            self.assertIsNone(
                user_store.create_user(
                    email="person@example.com",
                    password_hash="hash",
                    display_name="Person",
                )
            )

    def test_cached_postgres_schema_does_not_allow_write_fallback_to_sqlite(self) -> None:
        settings = SimpleNamespace(database_url="postgresql://example/db")
        user_store._user_schema_ready = True
        with (
            patch.object(user_store, "get_settings", return_value=settings),
            patch.object(user_store, "_pg_conn", return_value=None),
            patch.object(user_store, "_sqlite_conn", side_effect=AssertionError("sqlite fallback used")),
        ):
            self.assertIsNone(
                user_store.save_bridge(
                    "user-1",
                    {
                        "tracks": [{"id": "track-1"}],
                        "anchor_track": "Anchor",
                        "intent": "Explore",
                    },
                )
            )

    def test_postgres_schema_initialization_always_runs_full_idempotent_ddl(self) -> None:
        settings = SimpleNamespace(database_url="postgresql://example/db")
        cursor = FakeCursor()
        conn = FakeConnection(cursor)
        with (
            patch.object(user_store, "get_settings", return_value=settings),
            patch.object(user_store, "_pg_conn", return_value=conn),
        ):
            self.assertTrue(user_store.ensure_user_schema())

        ddl = "\n".join(cursor.statements)
        self.assertIn("CREATE TABLE IF NOT EXISTS app_users", ddl)
        self.assertIn("CREATE TABLE IF NOT EXISTS saved_bridges", ddl)
        self.assertIn("CREATE INDEX IF NOT EXISTS idx_saved_bridges_user", ddl)
        self.assertTrue(conn.closed)


if __name__ == "__main__":
    unittest.main()
