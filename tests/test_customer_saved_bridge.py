from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CustomerSavedBridgeTests(unittest.TestCase):
    def test_open_saved_bridge_guards_failed_api_payloads_before_display(self):
        source = (ROOT / "web" / "customer.js").read_text()
        match = re.search(
            r"async openSavedBridge\(id\) \{(?P<body>.*?)\n    renderMoodChips",
            source,
            re.S,
        )
        self.assertIsNotNone(match)
        body = match.group("body")

        guard_pos = body.index("if (!r.ok)")
        tracks_guard_pos = body.index("Array.isArray(bridge.tracks)")
        display_pos = body.index("window.displaySession?.(session)")

        self.assertLess(guard_pos, display_pos)
        self.assertLess(tracks_guard_pos, display_pos)
        self.assertIn("await r.json().catch(() => ({}))", body)


if __name__ == "__main__":
    unittest.main()
