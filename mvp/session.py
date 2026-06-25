from __future__ import annotations

import json
import time
from typing import Any

from itsdangerous import BadSignature, URLSafeTimedSerializer

from discovery.config import get_settings

COOKIE_SESSION = "bridge_session"
COOKIE_OAUTH = "bridge_oauth"
MAX_AGE = 60 * 60 * 24 * 7  # 7 days
OAUTH_MAX_AGE = 600  # 10 min


def _ser() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt="bridge-v1")


def _oauth_ser() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt="oauth-v1")


def pack_session(access_token: str, refresh_token: str = "", expires_at: float = 0) -> str:
    return _ser().dumps(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at or (time.time() + 3600),
        }
    )


def unpack_session(cookie: str | None) -> dict[str, Any] | None:
    if not cookie:
        return None
    try:
        return _ser().loads(cookie, max_age=MAX_AGE)
    except BadSignature:
        return None


def pack_oauth(state: str, verifier: str) -> str:
    return _oauth_ser().dumps({"state": state, "verifier": verifier})


def unpack_oauth(cookie: str | None) -> dict[str, str] | None:
    if not cookie:
        return None
    try:
        return _oauth_ser().loads(cookie, max_age=OAUTH_MAX_AGE)
    except BadSignature:
        return None


def session_cookie_kwargs(token: str) -> dict:
    secure = get_settings().api_base_url.startswith("https")
    return {
        "key": COOKIE_SESSION,
        "value": token,
        "httponly": True,
        "secure": secure,
        "samesite": "lax",
        "max_age": MAX_AGE,
        "path": "/",
    }


def oauth_cookie_kwargs(token: str) -> dict:
    secure = get_settings().api_base_url.startswith("https")
    return {
        "key": COOKIE_OAUTH,
        "value": token,
        "httponly": True,
        "secure": secure,
        "samesite": "lax",
        "max_age": OAUTH_MAX_AGE,
        "path": "/",
    }


def clear_cookie(key: str) -> dict:
    secure = get_settings().api_base_url.startswith("https")
    return {
        "key": key,
        "value": "",
        "httponly": True,
        "secure": secure,
        "samesite": "lax",
        "max_age": 0,
        "path": "/",
    }
