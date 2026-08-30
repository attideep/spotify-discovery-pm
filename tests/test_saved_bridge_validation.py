from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException

from api import main


class SavedBridgeValidationTests(TestCase):
    def test_save_bridge_rejects_missing_or_empty_tracks(self) -> None:
        for body in ({}, {"tracks": []}, {"tracks": None}):
            with self.subTest(body=body):
                with (
                    patch.object(main, "_current_app_user", return_value={"id": "user-1"}),
                    patch.object(main, "save_bridge") as save_bridge,
                ):
                    with self.assertRaises(HTTPException) as raised:
                        main.api_save_bridge(body, app_user="cookie")

                    self.assertEqual(400, raised.exception.status_code)
                    save_bridge.assert_not_called()

    def test_save_bridge_persists_payload_with_tracks(self) -> None:
        body = {
            "intent": "safe steps toward novelty",
            "anchor_track": "Anchor",
            "tracks": [{"track_id": "track-1", "name": "Track 1"}],
        }
        saved = {"id": "bridge-1", "title": "Bridge from Anchor"}
        with (
            patch.object(main, "_current_app_user", return_value={"id": "user-1"}),
            patch.object(main, "save_bridge", return_value=saved) as save_bridge,
        ):
            result = main.api_save_bridge(body, app_user="cookie")

        self.assertEqual(saved, result)
        save_bridge.assert_called_once_with("user-1", body)
