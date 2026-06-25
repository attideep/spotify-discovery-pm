from __future__ import annotations

import re
from typing import Any

SPOTIFY_TRACK_RE = re.compile(
    r"(?:spotify\.com/track/|spotify:track:)([A-Za-z0-9]{22})"
)


def parse_track_id(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    m = SPOTIFY_TRACK_RE.search(value)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9]{22}", value):
        return value
    return None


def resolve_track_query(value: str | None) -> str | None:
    """Spotify URL/ID, or best chart-catalog match for a song or artist name."""
    if not value or not value.strip():
        return None
    tid = parse_track_id(value)
    if tid:
        return tid
    from mvp.chart_catalog import search_tracks

    hits = search_tracks(value.strip(), limit=1)
    return hits[0]["id"] if hits else None


def track_url(track_id: str) -> str:
    return f"https://open.spotify.com/track/{track_id}"


def track_uri(track_id: str) -> str:
    return f"spotify:track:{track_id}"
