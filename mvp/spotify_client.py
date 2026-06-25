from __future__ import annotations

import time
from typing import Any

import httpx

from discovery.config import get_settings


class SpotifyAPIError(Exception):
    def __init__(self, message: str, status: int = 0, code: str = "spotify_error"):
        super().__init__(message)
        self.status = status
        self.code = code


class SpotifyClient:
    BASE = "https://api.spotify.com/v1"
    ACCOUNTS = "https://accounts.spotify.com/api/token"

    def __init__(self, access_token: str, refresh_token: str = "") -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> dict | list:
        url = path if path.startswith("http") else f"{self.BASE}{path}"
        with httpx.Client(timeout=30) as client:
            r = client.request(
                method,
                url,
                headers=self._headers(),
                params=params,
                json=json_body,
            )
        if r.status_code == 401:
            raise SpotifyAPIError("Spotify session expired — reconnect.", 401, "auth_expired")
        if r.status_code == 403:
            raise SpotifyAPIError(
                "Spotify API access denied. Your app may need Extended Quota.",
                403,
                "forbidden",
            )
        if r.status_code == 429:
            raise SpotifyAPIError("Spotify rate limit — try again in a moment.", 429, "rate_limit")
        if r.status_code >= 400:
            raise SpotifyAPIError(r.text[:200] or "Spotify API error", r.status_code)
        if not r.content:
            return {}
        return r.json()

    @classmethod
    def exchange_code(cls, code: str, verifier: str) -> dict[str, Any]:
        settings = get_settings()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.spotify_redirect_uri,
            "client_id": settings.spotify_client_id,
            "code_verifier": verifier,
        }
        auth = (settings.spotify_client_id, settings.spotify_client_secret)
        with httpx.Client(timeout=30) as client:
            r = client.post(cls.ACCOUNTS, data=data, auth=auth)
        if r.status_code >= 400:
            raise SpotifyAPIError(f"OAuth token exchange failed: {r.text[:200]}", r.status_code, "oauth_failed")
        payload = r.json()
        payload["expires_at"] = time.time() + payload.get("expires_in", 3600)
        return payload

    def refresh(self) -> dict[str, Any]:
        if not self.refresh_token:
            raise SpotifyAPIError("No refresh token", 401, "auth_expired")
        settings = get_settings()
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": settings.spotify_client_id,
        }
        auth = (settings.spotify_client_id, settings.spotify_client_secret)
        with httpx.Client(timeout=30) as client:
            r = client.post(self.ACCOUNTS, data=data, auth=auth)
        if r.status_code >= 400:
            raise SpotifyAPIError("Session expired — reconnect Spotify.", 401, "auth_expired")
        payload = r.json()
        payload["expires_at"] = time.time() + payload.get("expires_in", 3600)
        if "refresh_token" not in payload:
            payload["refresh_token"] = self.refresh_token
        self.access_token = payload["access_token"]
        return payload

    def ensure_fresh(self) -> None:
        # Caller should track expires_at externally; refresh if needed via session helper
        pass

    def me(self) -> dict:
        return self._request("GET", "/me")

    def get_track(self, track_id: str) -> dict:
        return self._request("GET", f"/tracks/{track_id}")

    def top_tracks(self, limit: int = 5) -> list[dict]:
        data = self._request("GET", "/me/top/tracks", params={"limit": limit, "time_range": "medium_term"})
        return data.get("items", [])

    def search_tracks(self, q: str, limit: int = 10) -> list[dict]:
        data = self._request("GET", "/search", params={"q": q, "type": "track", "limit": limit})
        return data.get("tracks", {}).get("items", [])

    def search_artists(self, q: str, limit: int = 3) -> list[dict]:
        data = self._request("GET", "/search", params={"q": q, "type": "artist", "limit": limit})
        return data.get("artists", {}).get("items", [])

    def artist_top_tracks(self, artist_id: str) -> list[dict]:
        data = self._request("GET", f"/artists/{artist_id}/top-tracks", params={"market": "US"})
        return data.get("tracks", [])

    def create_playlist(self, user_id: str, name: str, description: str) -> dict:
        return self._request(
            "POST",
            f"/users/{user_id}/playlists",
            json_body={"name": name, "description": description, "public": False},
        )

    def add_tracks_to_playlist(self, playlist_id: str, uris: list[str]) -> dict:
        return self._request(
            "POST",
            f"/playlists/{playlist_id}/tracks",
            json_body={"uris": uris},
        )


def normalize_track(item: dict) -> dict:
    artists = ", ".join(a["name"] for a in item.get("artists", []))
    images = item.get("album", {}).get("images", [])
    art = images[0]["url"] if images else ""
    tid = item["id"]
    return {
        "id": tid,
        "name": item.get("name", ""),
        "artist": artists,
        "album_art": art,
        "spotify_url": f"https://open.spotify.com/track/{tid}",
        "uri": f"spotify:track:{tid}",
    }
