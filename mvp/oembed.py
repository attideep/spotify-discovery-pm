"""Public Spotify track metadata via oEmbed (no API keys required)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from mvp.parse import track_url


def lookup_track_oembed(track_id: str) -> dict | None:
    """Return normalized track dict or None if Spotify doesn't recognize the ID."""
    url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/track/{track_id}"
    try:
        with urllib.request.urlopen(url, timeout=12) as resp:
            data = json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None

    title = (data.get("title") or "").strip() or "Unknown track"
    return {
        "id": track_id,
        "name": title,
        "artist": "",
        "album_art": data.get("thumbnail_url") or "",
        "spotify_url": track_url(track_id),
        "uri": f"spotify:track:{track_id}",
    }
