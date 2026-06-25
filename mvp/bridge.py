from __future__ import annotations

import json
import re
from typing import Any

from discovery.config import get_settings
from discovery.models import BridgeSession, BridgeTrack
from mvp.chart_catalog import bridge_candidates, get_track, _stable_seed, _tokens, _token_in_blob, _track_key
from mvp.demo_tracks import DEMO_TRACKS
from mvp.oembed import lookup_track_oembed
from mvp.parse import track_url
from mvp.spotify_client import SpotifyAPIError, SpotifyClient, normalize_track
from mvp.track_lookup import enrich_track_meta, lookup_track


class BridgeError(Exception):
    def __init__(self, message: str, code: str = "bridge_error", status: int = 400):
        super().__init__(message)
        self.code = code
        self.status = status


def _dedupe_candidates(candidates: list[dict], exclude_ids: set[str], anchor: dict | None = None) -> list[dict]:
    seen: set[str] = set()
    seen_keys: set[str] = set()
    if anchor:
        seen_keys.add(_track_key(anchor))
    out = []
    for c in candidates:
        tid = c["id"]
        key = _track_key(c)
        if tid in seen or tid in exclude_ids or key in seen_keys:
            continue
        seen.add(tid)
        seen_keys.add(key)
        out.append(c)
    return out


def _catalog_client() -> SpotifyClient | None:
    try:
        return SpotifyClient.from_client_credentials()
    except SpotifyAPIError:
        return None


def _gather_candidates(client: SpotifyClient | None, anchor: dict, intent: str) -> list[dict]:
    """Search-based discovery — uses user token, else app catalog token, else demo pool."""
    pool: list[dict] = []
    search_client = client or _catalog_client()

    if search_client:
        artist_names = (anchor.get("artist") or anchor.get("name") or "").split(",")[0].strip()
        queries = [intent[:80], f"{artist_names} {intent[:40]}".strip(), f"{artist_names} similar"]
        if artist_names:
            queries.insert(0, f'artist:"{artist_names}"')
        seen_q: set[str] = set()
        for q in queries:
            q = q.strip()
            if not q or q in seen_q:
                continue
            seen_q.add(q)
            try:
                for t in search_client.search_tracks(q, limit=10):
                    pool.append(normalize_track(t))
            except SpotifyAPIError:
                continue

        if artist_names:
            try:
                for artist in search_client.search_artists(artist_names, limit=2):
                    for t in search_client.artist_top_tracks(artist["id"])[:5]:
                        pool.append(normalize_track(t))
            except SpotifyAPIError:
                pass

    for c in bridge_candidates(anchor, intent, limit=60):
        pool.append(enrich_track_meta(c))

    return _dedupe_candidates(pool, {anchor["id"]}, anchor)


def _plan_with_llm(
    anchor: dict,
    candidates: list[dict],
    intent: str,
) -> list[dict]:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return _plan_heuristic(anchor, candidates, intent)

    import anthropic

    catalog = [
        {
            "id": c["id"],
            "name": c["name"],
            "artist": c["artist"],
        }
        for c in candidates[:40]
    ]
    prompt = f"""You are Bridge Sessions — an AI music discovery agent for Spotify.

Build an 8-track listening bridge from ANCHOR toward novel music matching the user's intent.
Pick exactly 8 track IDs from CATALOG only (never invent IDs).
Order tracks by gradual novelty (low → high). Anchor is step 0 context, not in the 8.

ANCHOR: {anchor["name"]} by {anchor["artist"]} (id: {anchor["id"]})
INTENT: {intent}

CATALOG:
{json.dumps(catalog, indent=2)}

Return JSON only:
{{"tracks": [{{"id": "...", "explanation": "one sentence why this transition works", "novelty_score": 0.0-1.0}}]}}
Must be exactly 8 tracks, all IDs from catalog."""

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text
    try:
        data = json.loads(re.search(r"\{.*\}", raw, re.S).group())
        return data.get("tracks", [])
    except Exception:
        return _plan_heuristic(anchor, candidates, intent)


def _plan_heuristic(anchor: dict, candidates: list[dict], intent: str) -> list[dict]:
    """Pick 8 tracks with increasing novelty — anchor/intent determine the pool, not a fixed demo list."""
    anchor_id = anchor["id"]
    anchor_artist = (anchor.get("artist") or "").lower()
    anchor_key = _track_key(anchor)
    intent_tokens = _tokens(intent)
    seed = _stable_seed(anchor_id, intent)

    scored: list[tuple[float, int, int, dict]] = []
    for c in candidates:
        if c["id"] == anchor_id or _track_key(c) == anchor_key:
            continue
        blob = f"{c.get('name', '')} {c.get('artist', '')}".lower()
        track_artist = (c.get("artist") or "").lower()
        same_artist = bool(anchor_artist) and anchor_artist.split(",")[0].strip() in track_artist
        intent_hits = sum(1 for t in intent_tokens if _token_in_blob(t, blob))
        anchor_overlap = sum(
            1 for t in _tokens(f"{anchor.get('name', '')} {anchor_artist}") if _token_in_blob(t, blob)
        )

        if same_artist:
            familiarity = 0.0
        elif intent_hits >= 2:
            familiarity = 0.35
        elif intent_hits == 1 or anchor_overlap >= 2:
            familiarity = 0.55
        else:
            familiarity = 0.78

        tie = (seed ^ hash(c["id"])) & 0xFFFF
        scored.append((familiarity, -intent_hits, tie, c))

    scored.sort(key=lambda x: (x[0], x[1], x[2]))

    if len(scored) < 8:
        return _plan_heuristic_fallback(anchor, candidates, intent, scored)

    n = len(scored)
    picks: list[dict] = []
    seen: set[str] = set()
    for step in range(8):
        idx = min(int(step * (n - 1) / 7), n - 1)
        for j in range(n):
            pos = (idx + j) % n
            c = scored[pos][3]
            if c["id"] not in seen:
                seen.add(c["id"])
                picks.append(c)
                break

    out = []
    for i, c in enumerate(picks[:8]):
        blob = f"{c.get('name', '')} {c.get('artist', '')}".lower()
        intent_hits = sum(1 for t in intent_tokens if _token_in_blob(t, blob))
        same_artist = bool(anchor_artist) and anchor_artist.split(",")[0].strip() in (c.get("artist") or "").lower()
        if same_artist:
            why = f"Stays close to {anchor['name']} while opening toward your intent."
        elif intent_hits:
            why = f"Matches “{' '.join(intent_tokens[:3])}” — step {i + 1} toward something new."
        else:
            why = f"A stretch pick that widens the path from {anchor['name']}."
        out.append(
            {
                "id": c["id"],
                "explanation": why,
                "novelty_score": round(0.12 + i * 0.11, 2),
            }
        )
    return out


def _plan_heuristic_fallback(
    anchor: dict,
    candidates: list[dict],
    intent: str,
    scored: list[tuple[float, int, int, dict]],
) -> list[dict]:
    picks = [s[3] for s in scored]
    for c in candidates:
        if c["id"] != anchor["id"] and c not in picks:
            picks.append(c)
        if len(picks) >= 8:
            break
    out = []
    for i, c in enumerate(picks[:8]):
        out.append(
            {
                "id": c["id"],
                "explanation": f"Step {i + 1} from {anchor['name']} toward {intent[:50]}",
                "novelty_score": round(0.15 + i * 0.1, 2),
            }
        )
    return out


def _build_session(
    anchor: dict,
    plan: list[dict],
    candidates: list[dict],
    intent: str,
    mode: str,
) -> BridgeSession:
    by_id = {c["id"]: c for c in candidates}
    by_id[anchor["id"]] = enrich_track_meta(anchor)
    tracks: list[BridgeTrack] = []

    for i, step in enumerate(plan[:8]):
        tid = step["id"]
        meta = enrich_track_meta(by_id.get(tid) or {"id": tid, "name": tid, "artist": ""})
        tracks.append(
            BridgeTrack(
                position=len(tracks) + 1,
                track_id=tid,
                name=meta["name"],
                artist=meta.get("artist", ""),
                spotify_url=meta.get("spotify_url") or track_url(tid),
                album_art=meta.get("album_art", ""),
                explanation=step.get("explanation", ""),
                novelty_score=float(step.get("novelty_score", 0.2 + i * 0.08)),
            )
        )

    if len(tracks) < 8:
        raise BridgeError("Could not build 8-track bridge — try a different anchor or intent.", "insufficient_tracks")

    summary = (
        f"Live bridge from {anchor['name']} — 8 tracks with AI-planned transitions."
        if mode == "live"
        else "Free bridge using verified Spotify tracks — paste any public track link as your anchor."
    )
    anchor_label = (
        f"{anchor['name']} — {anchor['artist']}"
        if anchor.get("artist")
        else anchor["name"]
    )
    return BridgeSession(
        anchor_track=anchor_label,
        anchor_id=anchor["id"],
        intent=intent,
        tracks=tracks,
        session_summary=summary,
    )


def resolve_anchor(
    client: SpotifyClient | None,
    anchor_track_id: str | None,
) -> dict:
    if anchor_track_id:
        if client:
            try:
                return normalize_track(client.get_track(anchor_track_id))
            except SpotifyAPIError as e:
                raise BridgeError(str(e), e.code, e.status) from e
        hit = get_track(anchor_track_id)
        if hit:
            return enrich_track_meta(hit)
        oembed = lookup_track_oembed(anchor_track_id)
        if oembed:
            return enrich_track_meta(oembed)
        raise BridgeError(
            f"Track not found — check the Spotify link and try again.",
            "track_not_found",
            404,
        )

    if client:
        tops = client.top_tracks(limit=1)
        if tops:
            return normalize_track(tops[0])
        raise BridgeError("No top tracks on your account — paste a Spotify track link.", "no_top_tracks")

    anchor = DEMO_TRACKS[0]
    return {**anchor, "spotify_url": track_url(anchor["id"]), "uri": f"spotify:track:{anchor['id']}"}


def create_bridge_session(
    intent: str,
    anchor_track_id: str | None = None,
    client: SpotifyClient | None = None,
    *,
    force_demo: bool = False,
) -> BridgeSession:
    if not intent.strip():
        raise BridgeError("Describe your listening intent.", "missing_intent")

    settings = get_settings()
    mode = "demo"
    if client and not force_demo:
        mode = "live"
    elif not settings.allow_demo_mode and not client:
        raise BridgeError(
            "Connect Spotify to generate a bridge session.",
            "auth_required",
            401,
        )

    anchor = resolve_anchor(client if mode == "live" else None, anchor_track_id)
    candidates = _gather_candidates(client if mode == "live" else None, anchor, intent)
    plan = _plan_with_llm(anchor, candidates, intent)
    session = _build_session(anchor, plan, candidates, intent, mode)
    return session


def restore_bridge_session(
    intent: str,
    anchor_track_id: str | None,
    track_ids: list[str],
) -> BridgeSession:
    """Rebuild an exact shared session from saved track IDs — no re-planning."""
    if not intent.strip():
        raise BridgeError("Describe your listening intent.", "missing_intent")
    ids = [t.strip() for t in track_ids if t and t.strip()][:8]
    if len(ids) < 8:
        raise BridgeError(
            "Shared link is incomplete — generate a new bridge and copy the link again.",
            "invalid_share",
            400,
        )

    anchor = resolve_anchor(None, anchor_track_id)
    tracks: list[BridgeTrack] = []
    for i, tid in enumerate(ids):
        meta = lookup_track(tid) or {"id": tid, "name": "Unknown track", "artist": ""}
        meta = enrich_track_meta(meta)
        tracks.append(
            BridgeTrack(
                position=i + 1,
                track_id=tid,
                name=meta["name"],
                artist=meta.get("artist", ""),
                spotify_url=meta.get("spotify_url") or track_url(tid),
                album_art=meta.get("album_art", ""),
                explanation=f"Step {i + 1} in this shared bridge toward “{intent[:60]}”.",
                novelty_score=round(0.12 + i * 0.11, 2),
            )
        )

    anchor_label = (
        f"{anchor['name']} — {anchor['artist']}"
        if anchor.get("artist")
        else anchor["name"]
    )
    return BridgeSession(
        anchor_track=anchor_label,
        anchor_id=anchor["id"],
        intent=intent.strip(),
        tracks=tracks,
        session_summary="Shared bridge session — same track order as the link you opened.",
    )


def save_bridge_to_playlist(
    client: SpotifyClient,
    session: BridgeSession,
) -> dict[str, Any]:
    me = client.me()
    user_id = me["id"]
    name = f"Bridge Session — {session.anchor_track[:40]}"
    desc = f"AI bridge session. Intent: {session.intent[:200]}"
    playlist = client.create_playlist(user_id, name, desc)
    uris = [f"spotify:track:{t.track_id}" for t in session.tracks]
    client.add_tracks_to_playlist(playlist["id"], uris)
    return {
        "playlist_id": playlist["id"],
        "playlist_url": playlist.get("external_urls", {}).get("spotify", ""),
        "name": name,
    }
