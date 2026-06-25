from __future__ import annotations

import base64
import hashlib
import json
import secrets
import urllib.parse
from typing import Any

import httpx

from discovery.config import get_settings
from discovery.models import BridgeSession, BridgeTrack

_oauth_states: dict[str, str] = {}

DEMO_TRACKS = [
    ("4cOdKETwRBC7tOlA0CdWr6", "Khruangbin", "Time (You and I)"),
    ("3bidbhpQGRsR7zRPHmjlF3", "Tame Impala", "The Less I Know The Better"),
    ("6habFtsirITryhBrJXrzoa", "Bon Iver", "Holocene"),
    ("2LawezPeJ4qb7b4K9KlzAk", "Khruangbin", "Maria También"),
    ("1NeQ9YStIb1K3JHWxSDMJo", "Unknown Mortal Orchestra", "Multi-Love"),
    ("0AqQUcf2XJdPhX1PvvdPD0", "Men I Trust", "Show Me How"),
    ("5TxXWhM2ypJ2G1kSqQy8Kf", "Mac DeMarco", "Chamber Of Reflection"),
    ("3bUuKaC4W8AcE9bQ4Bq9bK", "Crumb", "Balloon"),
]


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    return verifier, challenge


def get_auth_url() -> str:
    settings = get_settings()
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)
    _oauth_states[state] = verifier
    params = {
        "client_id": settings.spotify_client_id or "demo",
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "scope": "user-top-read user-read-private playlist-modify-public",
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    }
    return "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)


def handle_callback(code: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.spotify_client_id or settings.mock_mode:
        return {"access_token": "demo", "token_type": "Bearer"}
    verifier = next(iter(_oauth_states.values()), "")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.spotify_redirect_uri,
        "client_id": settings.spotify_client_id,
        "code_verifier": verifier,
    }
    auth = (settings.spotify_client_id, settings.spotify_client_secret)
    with httpx.Client(timeout=30) as client:
        r = client.post("https://accounts.spotify.com/api/token", data=data, auth=auth)
        r.raise_for_status()
        return r.json()


def _spotify_get(path: str, token: str, params: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(timeout=30, headers=headers) as client:
        r = client.get(f"https://api.spotify.com/v1{path}", params=params or {})
        if r.status_code == 401:
            return {}
        r.raise_for_status()
        return r.json()


def _demo_session(intent: str, anchor_track_id: str | None) -> BridgeSession:
    anchor = anchor_track_id or DEMO_TRACKS[0][0]
    anchor_name = next((t[2] for t in DEMO_TRACKS if t[0] == anchor), DEMO_TRACKS[0][2])
    tracks = []
    for i, (tid, artist, name) in enumerate(DEMO_TRACKS):
        novelty = round(0.15 + i * 0.1, 2)
        tracks.append(
            BridgeTrack(
                position=i + 1,
                track_id=tid,
                name=name,
                artist=artist,
                spotify_url=f"https://open.spotify.com/track/{tid}",
                explanation=(
                    f"Step {i + 1}: Gradual bridge from {anchor_name} — "
                    f"{'shared groove, slightly higher energy' if i < 3 else 'introduces new texture while keeping BPM within 8%'} "
                    f"for intent: {intent[:60]}"
                ),
                novelty_score=novelty,
            )
        )
    return BridgeSession(
        anchor_track=anchor_name,
        intent=intent,
        tracks=tracks,
        session_summary=(
            "8-track bridge session moving from your comfort anchor toward novel artists "
            "with explainable transitions. Demo mode — connect Spotify for live recommendations."
        ),
    )


def create_bridge_session(
    intent: str,
    anchor_track_id: str | None = None,
    access_token: str = "demo",
) -> BridgeSession:
    settings = get_settings()
    if access_token == "demo" or settings.mock_mode or not settings.spotify_client_id:
        return _demo_session(intent, anchor_track_id)

    top = _spotify_get("/me/top/tracks", access_token, {"limit": 5})
    items = top.get("items", [])
    anchor = anchor_track_id
    anchor_name = "your top track"
    if not anchor and items:
        anchor = items[0]["id"]
        anchor_name = items[0]["name"]
    elif anchor:
        meta = _spotify_get(f"/tracks/{anchor}", access_token)
        anchor_name = meta.get("name", anchor_name)

    seed = anchor or (items[0]["id"] if items else DEMO_TRACKS[0][0])
    recs = _spotify_get(
        "/recommendations",
        access_token,
        {
            "seed_tracks": seed,
            "limit": 8,
            "min_energy": 0.3,
            "max_energy": 0.85,
        },
    )
    rec_items = recs.get("tracks", [])
    if not rec_items:
        return _demo_session(intent, seed)

    tracks = []
    for i, t in enumerate(rec_items):
        tracks.append(
            BridgeTrack(
                position=i + 1,
                track_id=t["id"],
                name=t["name"],
                artist=", ".join(a["name"] for a in t["artists"]),
                spotify_url=t["external_urls"]["spotify"],
                explanation=(
                    f"Bridge step {i + 1} from {anchor_name}: selected for gradual novelty "
                    f"matching your intent — {intent[:80]}"
                ),
                novelty_score=round(0.2 + i * 0.09, 2),
            )
        )
    return BridgeSession(
        anchor_track=anchor_name,
        intent=intent,
        tracks=tracks,
        session_summary=f"Live 8-track bridge from {anchor_name} toward novel artists for: {intent}",
    )
