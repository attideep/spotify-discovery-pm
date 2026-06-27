"""Resolve ~30s preview clip URLs via Apple iTunes Search (no API keys)."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _score_match(result: dict, name: str, artist: str) -> int:
    preview = result.get("previewUrl")
    if not preview or result.get("wrapperType") != "track":
        return -1
    want_title = _norm(name)
    want_artist = _norm((artist or "").split(",")[0])
    title = _norm(result.get("trackName", ""))
    art = _norm(result.get("artistName", ""))
    score = 0
    if want_title and (want_title in title or title in want_title):
        score += 4
    if want_artist and (want_artist in art or art in want_artist):
        score += 3
    if want_title and want_title.split()[0] in title.split():
        score += 1
    return score


def lookup_preview_url(name: str, artist: str = "") -> str | None:
    term = f"{artist} {name}".strip() if artist else (name or "").strip()
    if not term:
        return None

    qs = urllib.parse.urlencode({"term": term, "entity": "song", "limit": 10})
    url = f"https://itunes.apple.com/search?{qs}"
    try:
        with urllib.request.urlopen(url, timeout=12) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None

    results = data.get("results") or []
    best_url: str | None = None
    best_score = 0
    for hit in results:
        score = _score_match(hit, name, artist)
        if score > best_score:
            best_score = score
            best_url = hit.get("previewUrl")

    if best_url:
        return best_url

    for hit in results:
        preview = hit.get("previewUrl")
        if preview:
            return preview
    return None
