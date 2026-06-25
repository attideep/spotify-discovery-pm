"""Static chart catalog — ~10k popular tracks, no Spotify API keys."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from mvp.demo_tracks import DEMO_TRACKS
from mvp.parse import track_url

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "chart_catalog.json"


@lru_cache(maxsize=1)
def _load() -> tuple[dict, ...]:
    if not CATALOG_PATH.exists():
        return tuple({**d, "popularity": 100} for d in DEMO_TRACKS)
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    tracks = data.get("tracks") or []
    by_id: dict[str, dict] = {}
    for d in DEMO_TRACKS:
        by_id[d["id"]] = {**d, "popularity": 100}
    for t in tracks:
        tid = t.get("id")
        if tid and tid not in by_id:
            by_id[tid] = t
    return tuple(by_id.values())


def catalog_count() -> int:
    return len(_load())


def get_track(track_id: str) -> dict | None:
    for t in _load():
        if t["id"] == track_id:
            return _normalize(t)
    return None


def _normalize(t: dict) -> dict:
    return {
        "id": t["id"],
        "name": t["name"],
        "artist": t.get("artist", ""),
        "album_art": t.get("album_art", ""),
        "popularity": t.get("popularity", 0),
        "spotify_url": track_url(t["id"]),
        "uri": f"spotify:track:{t['id']}",
    }


def _tokens(text: str) -> list[str]:
    stop = {"the", "and", "for", "with", "like", "but", "more", "your", "from", "that", "this"}
    return [w for w in re.split(r"\W+", text.lower()) if len(w) >= 3 and w not in stop]


def _match(query: str, track: dict, *, any_token: bool = False) -> bool:
    needle = query.lower().strip()
    if not needle:
        return False
    blob = f"{track['name']} {track.get('artist', '')}".lower()
    if needle in blob:
        return True
    tokens = _tokens(needle)
    if not tokens:
        return False
    if any_token:
        return any(t in blob for t in tokens)
    return all(t in blob for t in tokens)


def search_tracks(query: str, *, limit: int = 12, any_token: bool = False) -> list[dict]:
    hits = [t for t in _load() if _match(query, t, any_token=any_token)]
    if not hits and not any_token:
        hits = [t for t in _load() if _match(query, t, any_token=True)]
    hits.sort(key=lambda t: t.get("popularity", 0), reverse=True)
    return [_normalize(t) for t in hits[:limit]]


def bridge_candidates(anchor: dict, intent: str, *, limit: int = 40) -> list[dict]:
    """Intent/artist-aware pool for demo bridges (no live Search API)."""
    seen: set[str] = {anchor["id"]}
    pool: list[dict] = []

    for d in DEMO_TRACKS:
        if d["id"] not in seen:
            seen.add(d["id"])
            pool.append(_normalize({**d, "popularity": 100}))

    queries = [
        intent[:80],
        (anchor.get("artist") or "").split(",")[0].strip(),
        f"{anchor.get('artist', '')} {intent[:40]}".strip(),
    ]
    for q in queries:
        if not q:
            continue
        for t in search_tracks(q, limit=limit, any_token=True):
            if t["id"] in seen:
                continue
            seen.add(t["id"])
            pool.append(t)
        if len(pool) >= limit:
            break

    if len(pool) < 8:
        for t in sorted(_load(), key=lambda x: x.get("popularity", 0), reverse=True):
            if t["id"] in seen:
                continue
            seen.add(t["id"])
            pool.append(_normalize(t))
            if len(pool) >= limit:
                break

    return pool[:limit]
