import unittest
from unittest.mock import patch

from mvp import user_store


class FakeCursor:
    def __init__(self, existing_tables):
        self.existing_tables = existing_tables
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, *args):
        self.statements.append(str(sql))

    def fetchall(self):
        return [(name,) for name in self.existing_tables]


class FakePostgresConnection:
    def __init__(self, existing_tables):
        self.cursor_obj = FakeCursor(existing_tables)
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_obj

    def close(self):
        self.closed = True


class EnsureUserSchemaPostgresTests(unittest.TestCase):
    def setUp(self):
        user_store._user_schema_ready = False

    def tearDown(self):
        user_store._user_schema_ready = False

    def test_runs_schema_when_saved_bridges_is_missing(self):
        conn = FakePostgresConnection({"app_users"})

        with patch.object(user_store, "_pg_conn", return_value=conn):
            self.assertTrue(user_store.ensure_user_schema())

        self.assertTrue(
            any("CREATE TABLE IF NOT EXISTS saved_bridges" in statement for statement in conn.cursor_obj.statements)
        )
        self.assertTrue(conn.closed)

    def test_skips_schema_when_all_user_tables_exist(self):
        conn = FakePostgresConnection({"app_users", "saved_bridges"})

        with patch.object(user_store, "_pg_conn", return_value=conn):
            self.assertTrue(user_store.ensure_user_schema())

        self.assertFalse(
            any("CREATE TABLE IF NOT EXISTS app_users" in statement for statement in conn.cursor_obj.statements)
        )
        self.assertTrue(conn.closed)


if __name__ == "__main__":
    unittest.main()
