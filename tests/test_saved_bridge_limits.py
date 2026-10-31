from __future__ import annotations

import itertools
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

from api import main as api_main
from api.main import SavedBridgeBody
from mvp import user_store
from mvp.session import COOKIE_APP_USER


def _track(track_id: str = "track-1") -> dict:
    return {
        "position": 1,
        "track_id": track_id,
        "name": "Song",
        "artist": "Artist",
        "spotify_url": f"https://open.spotify.com/track/{track_id}",
        "album_art": "",
        "explanation": "A useful next step.",
        "novelty_score": 0.2,
    }


class SavedBridgeLimitsTest(unittest.TestCase):
    def test_saved_bridge_body_limits_tracks(self) -> None:
        body = {
            "anchor_track": "Anchor",
            "intent": "Focus",
            "tracks": [_track(f"track-{i}") for i in range(user_store.MAX_SAVED_BRIDGE_TRACKS + 1)],
        }

        with self.assertRaises(ValidationError):
            SavedBridgeBody.model_validate(body)

    def test_save_bridge_prunes_old_rows_per_user(self) -> None:
        counter = itertools.count()

        def fake_now() -> str:
            return f"2026-10-31T00:00:{next(counter):02d}+00:00"

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "users.db"
            user_store._user_schema_ready = False
            with (
                patch.object(user_store, "_pg_conn", return_value=None),
                patch.object(user_store, "_sqlite_path", return_value=db_path),
                patch.object(user_store, "_now_iso", side_effect=fake_now),
            ):
                user = user_store.create_user(email="save@example.com", password_hash="hash")
                self.assertIsNotNone(user)

                for i in range(user_store.MAX_SAVED_BRIDGES_PER_USER + 5):
                    saved = user_store.save_bridge(
                        user["id"],
                        {
                            "anchor_track": f"Anchor {i}",
                            "intent": "Focus",
                            "tracks": [_track(f"track-{i}")],
                        },
                    )
                    self.assertIsNotNone(saved)

                bridges = user_store.list_saved_bridges(user["id"], limit=100)

            user_store._user_schema_ready = False

        self.assertEqual(user_store.MAX_SAVED_BRIDGES_PER_USER, len(bridges))
        self.assertEqual("Anchor 44", bridges[0]["anchor_track"])
        self.assertNotIn("Anchor 0", {bridge["anchor_track"] for bridge in bridges})

    def test_api_save_bridge_rejects_oversized_request_before_persistence(self) -> None:
        client = TestClient(api_main.app)
        client.cookies.set(COOKIE_APP_USER, "session")
        oversized_body = b'{"tracks":[' + (b'"x",' * api_main.MAX_SAVED_BRIDGE_REQUEST_BYTES) + b'"x"]}'

        with (
            patch.object(api_main, "_current_app_user", return_value={"id": "user-1"}),
            patch.object(api_main, "enforce_rate_limit"),
            patch.object(api_main, "save_bridge") as save_bridge,
        ):
            response = client.post(
                "/api/bridges/save",
                content=oversized_body,
            )

        self.assertEqual(413, response.status_code)
        save_bridge.assert_not_called()

    def test_api_save_bridge_persists_valid_normalized_body(self) -> None:
        client = TestClient(api_main.app)
        client.cookies.set(COOKIE_APP_USER, "session")
        body = {
            "anchor_track": "Anchor",
            "intent": "Focus",
            "mode": "demo",
            "tracks": [{**_track("track-1"), "ignored": "not persisted"}],
        }
        saved = {"id": "bridge-1", "title": "Bridge from Anchor"}

        with (
            patch.object(api_main, "_current_app_user", return_value={"id": "user-1"}),
            patch.object(api_main, "enforce_rate_limit"),
            patch.object(api_main, "save_bridge", return_value=saved) as save_bridge,
        ):
            response = client.post(
                "/api/bridges/save",
                json=body,
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual(saved, response.json())
        save_bridge.assert_called_once()
        self.assertEqual("user-1", save_bridge.call_args.args[0])
        stored_body = save_bridge.call_args.args[1]
        self.assertNotIn("mode", stored_body)
        self.assertNotIn("ignored", stored_body["tracks"][0])


if __name__ == "__main__":
    unittest.main()
