import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch, sentinel

from api import main


class SharedEndpointRateLimitTests(unittest.TestCase):
    def test_canonical_ask_uses_ask_rate_limit(self) -> None:
        fake_store = object()
        fake_response = SimpleNamespace(model_dump=lambda: {"answer": "ok"})

        with (
            patch.object(main, "enforce_rate_limit") as enforce_rate_limit,
            patch.object(main, "_ensure_indexed", return_value=fake_store),
            patch.object(main, "ask", return_value=fake_response) as ask,
        ):
            result = main.api_ask_canonical("why_struggle", sentinel.request)

        self.assertEqual(result, {"answer": "ok"})
        enforce_rate_limit.assert_called_once_with(sentinel.request, scope="ask")
        ask.assert_called_once_with("q:why_struggle", fake_store)

    def test_bridge_restore_uses_bridge_rate_limit(self) -> None:
        body = main.RestoreBridgeBody(
            intent="focus",
            anchor="3nqQXoyQOWXiESFLlDF1hG",
            track_ids=["4uLU6hMCjMI75M1A2tKUQC"] * 8,
        )
        fake_session = SimpleNamespace(model_dump=lambda: {"intent": "focus", "tracks": []})

        with (
            patch.object(main, "enforce_rate_limit") as enforce_rate_limit,
            patch.object(main, "resolve_track_query", return_value="anchor-id"),
            patch.object(main, "restore_bridge_session", return_value=fake_session) as restore_bridge_session,
        ):
            response = main.api_bridge_restore(body, sentinel.request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.body), {"intent": "focus", "tracks": [], "mode": "demo"})
        enforce_rate_limit.assert_called_once_with(sentinel.request, scope="bridge")
        restore_bridge_session.assert_called_once_with(
            intent="focus",
            anchor_track_id="anchor-id",
            track_ids=body.track_ids,
        )


if __name__ == "__main__":
    unittest.main()
