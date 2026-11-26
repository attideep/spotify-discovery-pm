import os
import unittest
from unittest import mock

from discovery.config import get_settings
from mvp import user_store


class UserStoreStorageModeTest(unittest.TestCase):
    def setUp(self):
        get_settings.cache_clear()
        user_store._user_schema_ready = False

    def tearDown(self):
        get_settings.cache_clear()
        user_store._user_schema_ready = False

    def test_vercel_without_database_url_disables_server_auth_storage(self):
        env = {
            "VERCEL": "1",
            "VERCEL_ENV": "production",
            "DATABASE_URL": "",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            user_store._user_schema_ready = True
            with mock.patch.object(user_store, "_sqlite_conn", side_effect=AssertionError("sqlite should not open")):
                self.assertEqual(user_store.storage_mode(), "unavailable")
                self.assertFalse(user_store.ensure_user_schema())

    def test_local_without_database_url_keeps_sqlite_for_development(self):
        env = {
            "VERCEL": "",
            "VERCEL_ENV": "",
            "DATABASE_URL": "",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            self.assertEqual(user_store.storage_mode(), "sqlite")


if __name__ == "__main__":
    unittest.main()
