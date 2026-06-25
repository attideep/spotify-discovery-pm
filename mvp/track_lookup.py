"""Resolve a Spotify track ID to metadata (demo catalog → oEmbed → live API)."""
from __future__ import annotations

from mvp.demo_tracks import DEMO_TRACKS
from mvp.oembed import lookup_track_oembed
from mvp.parse import track_url
from mvp.spotify_client import SpotifyClient, normalize_track


def _from_demo_catalog(track_id: str) -> dict | None:
    for d in DEMO_TRACKS:
        if d["id"] == track_id:
            return {
                **d,
                "spotify_url": track_url(track_id),
                "uri": f"spotify:track:{track_id}",
            }
    return None


def lookup_track(track_id: str, client: SpotifyClient | None = None) -> dict | None:
    hit = _from_demo_catalog(track_id)
    if hit:
        return hit

    if client:
        try:
            return normalize_track(client.get_track(track_id))
        except Exception:
            pass

    return lookup_track_oembed(track_id)
