from pathlib import Path
import unittest


CUSTOMER_JS = Path(__file__).resolve().parents[1] / "web" / "customer.js"


class CustomerLocalAuthStaticTests(unittest.TestCase):
    def test_local_library_is_scoped_to_active_account(self):
        source = CUSTOMER_JS.read_text()

        self.assertIn("function localLibraryKey(user = authUser)", source)
        self.assertIn("`${LOCAL_LIB_KEY}:${owner}`", source)
        self.assertIn("owner_email: normalizeEmail(authUser.email)", source)
        self.assertIn("owner_id: authUser.id || \"\"", source)
        self.assertNotIn("localStorage.setItem(LOCAL_LIB_KEY", source)

    def test_signed_out_users_do_not_render_local_library(self):
        source = CUSTOMER_JS.read_text()

        self.assertIn("if (!authUser) {\n        panel?.classList.add(\"hidden\");", source)
        self.assertIn("libraryPanel?.classList.add(\"hidden\");", source)
        self.assertIn("$(\"savedBridges\")?.replaceChildren();", source)

    def test_device_only_auth_can_save_and_load_local_bridges(self):
        source = CUSTOMER_JS.read_text()

        self.assertIn("let serverAuthed = false;", source)
        self.assertIn("if (!serverAuthed) {\n          await saveOnDevice", source)
        self.assertIn("if (serverAuthed) {\n        try {\n          const r = await fetch(\"/api/bridges/saved\"", source)
        self.assertIn("serverAuthed = false;\n        authUser = local?.active ? localUserFromAuth(local) : null;", source)
        self.assertIn("Saved bridges — kept on this device until you sign in again.", source)


if __name__ == "__main__":
    unittest.main()
