from __future__ import annotations

import base64
import hashlib
import secrets
import time
import urllib.parse

from discovery.config import get_settings
from mvp.session import pack_oauth, pack_session, unpack_session
from mvp.spotify_client import SpotifyAPIError, SpotifyClient


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    return verifier, challenge


def get_login_redirect() -> tuple[str, str]:
    """Returns (spotify_auth_url, signed_oauth_cookie_value)."""
    settings = get_settings()
    if not settings.spotify_configured:
        raise SpotifyAPIError("Spotify not configured on server.", 503, "not_configured")

    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)
    oauth_cookie = pack_oauth(state, verifier)

    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "scope": " ".join(
            [
                "user-top-read",
                "user-read-private",
                "user-read-email",
                "playlist-modify-private",
                "playlist-modify-public",
            ]
        ),
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    }
    url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)
    return url, oauth_cookie


def exchange_callback(code: str, state: str, oauth_cookie: str | None) -> str:
    """Returns signed session cookie value."""
    from mvp.session import unpack_oauth

    oauth = unpack_oauth(oauth_cookie)
    if not oauth or oauth.get("state") != state:
        raise SpotifyAPIError("OAuth state mismatch — try connecting again.", 400, "oauth_state")

    payload = SpotifyClient.exchange_code(code, oauth["verifier"])
    return pack_session(
        payload["access_token"],
        payload.get("refresh_token", ""),
        payload.get("expires_at", time.time() + 3600),
    )


def client_from_session(session_cookie: str | None) -> SpotifyClient | None:
    data = unpack_session(session_cookie)
    if not data:
        return None

    client = SpotifyClient(data["access_token"], data.get("refresh_token", ""))
    if data.get("expires_at", 0) < time.time() + 60:
        try:
            refreshed = client.refresh()
            data["access_token"] = refreshed["access_token"]
            data["refresh_token"] = refreshed.get("refresh_token", data.get("refresh_token", ""))
            data["expires_at"] = refreshed.get("expires_at", time.time() + 3600)
            # Caller should re-pack cookie if refreshed
            client.access_token = data["access_token"]
        except SpotifyAPIError:
            return None
    return client


def refreshed_session_cookie(session_cookie: str | None) -> str | None:
    data = unpack_session(session_cookie)
    if not data:
        return None
    client = SpotifyClient(data["access_token"], data.get("refresh_token", ""))
    if data.get("expires_at", 0) < time.time() + 60:
        refreshed = client.refresh()
        data["access_token"] = refreshed["access_token"]
        data["refresh_token"] = refreshed.get("refresh_token", data.get("refresh_token", ""))
        data["expires_at"] = refreshed.get("expires_at", time.time() + 3600)
    return pack_session(data["access_token"], data.get("refresh_token", ""), data.get("expires_at", 0))
