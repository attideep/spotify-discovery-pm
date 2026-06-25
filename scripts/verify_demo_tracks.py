#!/usr/bin/env python3
"""Verify every demo track ID resolves on Spotify (oEmbed)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

from mvp.demo_tracks import DEMO_TRACKS


def verify_track(track_id: str) -> tuple[bool, str]:
    url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/track/{track_id}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
            return True, data.get("title", "")
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def main() -> int:
    failed = 0
    for track in DEMO_TRACKS:
        ok, info = verify_track(track["id"])
        status = "OK" if ok else "FAIL"
        print(f"{status:4} {track['id']}  {track['name']} — {track['artist']}  ({info})")
        if not ok:
            failed += 1

    if failed:
        print(f"\n{failed} invalid demo track(s). Fix mvp/demo_tracks.py before deploy.")
        return 1

    print(f"\nAll {len(DEMO_TRACKS)} demo tracks verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
