"""Static chart catalog — up to 50k popular tracks, no Spotify API keys."""
from __future__ import annotations

import hashlib
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


def _token_in_blob(token: str, blob: str) -> bool:
    if token in blob:
        return True
    stem = re.sub(r"['']?s$", "", token)
    return len(stem) >= 3 and stem in blob


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
        return any(_token_in_blob(t, blob) for t in tokens)
    return all(_token_in_blob(t, blob) for t in tokens)


def search_tracks(query: str, *, limit: int = 12, any_token: bool = False) -> list[dict]:
    hits = [t for t in _load() if _match(query, t, any_token=any_token)]
    if not hits and not any_token:
        hits = [t for t in _load() if _match(query, t, any_token=True)]
    hits.sort(key=lambda t: t.get("popularity", 0), reverse=True)
    return [_normalize(t) for t in hits[:limit]]


def _track_key(t: dict) -> str:
    return f"{(t.get('name') or '').lower()}|{(t.get('artist') or '').split(',')[0].strip().lower()}"


def bridge_candidates(anchor: dict, intent: str, *, limit: int = 60) -> list[dict]:
    """Intent/artist-aware pool for demo bridges (no live Search API)."""
    anchor_key = _track_key(anchor)
    seen: set[str] = {anchor["id"]}
    seen_keys: set[str] = {anchor_key}
    pool: list[dict] = []

    def add(tracks: list[dict]) -> None:
        for t in tracks:
            key = _track_key(t)
            if t["id"] in seen or key in seen_keys:
                continue
            seen.add(t["id"])
            seen_keys.add(key)
            pool.append(t)

    artist = (anchor.get("artist") or "").split(",")[0].strip()
    anchor_name = (anchor.get("name") or "").strip()

    if artist:
        add(search_tracks(artist, limit=16, any_token=True))
    if anchor_name:
        add(search_tracks(anchor_name, limit=8, any_token=True))

    add(search_tracks(intent, limit=20))
    for token in _tokens(intent)[:6]:
        add(search_tracks(token, limit=10, any_token=False))

    if artist:
        add(search_tracks(f"{artist} {intent[:50]}".strip(), limit=12, any_token=True))

    for d in DEMO_TRACKS:
        if d["id"] in seen:
            continue
        if _match(intent, d, any_token=True) or (artist and _token_in_blob(artist.lower(), d.get("artist", "").lower())):
            add([_normalize({**d, "popularity": max(d.get("popularity", 0), 85)})])

    anchor_pop = anchor.get("popularity") or 70
    catalog = sorted(_load(), key=lambda x: x.get("popularity", 0), reverse=True)
    band = [t for t in catalog if abs(t.get("popularity", 0) - anchor_pop) <= 12 and t["id"] not in seen]
    add([_normalize(t) for t in band[:12]])

    seed = _stable_seed(anchor["id"], intent)
    remaining = [t for t in catalog if t["id"] not in seen]
    for i, t in enumerate(remaining):
        if len(pool) >= limit:
            break
        if (seed + i * 7919) % 17 == 0 or i < 8:
            add([_normalize(t)])

    if len(pool) < 16:
        for t in catalog:
            if t["id"] not in seen:
                add([_normalize(t)])
            if len(pool) >= limit:
                break

    return pool[:limit]


def _stable_seed(anchor_id: str, intent: str) -> int:
    import hashlib

    h = hashlib.sha256(f"{anchor_id}|{intent.strip().lower()}".encode()).hexdigest()
    return int(h[:8], 16)
