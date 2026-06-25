"""Resolve a Spotify track ID to metadata (demo catalog → oEmbed → live API)."""
from __future__ import annotations

from mvp.chart_catalog import get_track
from mvp.demo_tracks import DEMO_TRACKS
from mvp.oembed import lookup_track_oembed
from mvp.parse import track_url
from mvp.spotify_client import SpotifyClient, normalize_track


def _from_static_catalog(track_id: str) -> dict | None:
    hit = get_track(track_id)
    if hit:
        return hit
    for d in DEMO_TRACKS:
        if d["id"] == track_id:
            return {
                **d,
                "spotify_url": track_url(track_id),
                "uri": f"spotify:track:{track_id}",
            }
    return None


def enrich_track_meta(meta: dict) -> dict:
    """Fill missing album art (and artist) via Spotify oEmbed — no API keys."""
    if meta.get("album_art"):
        return meta
    hit = lookup_track_oembed(meta["id"])
    if not hit:
        return meta
    out = {**meta}
    if hit.get("album_art"):
        out["album_art"] = hit["album_art"]
    if not out.get("artist") and hit.get("artist"):
        out["artist"] = hit["artist"]
    return out


def lookup_track(track_id: str, client: SpotifyClient | None = None) -> dict | None:
    hit = _from_static_catalog(track_id)
    if hit:
        return enrich_track_meta(hit)

    if client:
        try:
            return normalize_track(client.get_track(track_id))
        except Exception:
            pass

    hit = lookup_track_oembed(track_id)
    return enrich_track_meta(hit) if hit else None
