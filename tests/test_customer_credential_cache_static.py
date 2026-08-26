from pathlib import Path
import re
import unittest


CUSTOMER_JS = Path(__file__).resolve().parents[1] / "web" / "customer.js"


class CustomerCredentialCacheTests(unittest.TestCase):
    def test_postgres_server_auth_clears_local_password_verifier(self):
        source = CUSTOMER_JS.read_text()

        self.assertIn("function clearLocalAuth()", source)
        self.assertIn("localStorage.removeItem(LOCAL_AUTH_KEY)", source)

        server_auth_branch = re.search(
            r"if \(r\.ok && data\.user\) \{(?P<body>.*?)await finishAuth",
            source,
            re.S,
        )
        self.assertIsNotNone(server_auth_branch)
        body = server_auth_branch.group("body")
        self.assertIn('if (storageMode === "postgres")', body)
        self.assertIn("clearLocalAuth();", body)
        self.assertIn("saveLocalAuth(data.user, pwHash);", body)

    def test_local_device_account_still_stores_local_verifier(self):
        source = CUSTOMER_JS.read_text()
        local_account = re.search(
            r"async function createLocalAccount\(email, password, display_name\) \{(?P<body>.*?)\n  \}",
            source,
            re.S,
        )

        self.assertIsNotNone(local_account)
        self.assertIn("const pwHash = await hashCredentials(email, password);", local_account.group("body"))
        self.assertIn("saveLocalAuth(user, pwHash);", local_account.group("body"))


if __name__ == "__main__":
    unittest.main()
