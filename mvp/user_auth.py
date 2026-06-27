"""Email/password + Google OAuth for customer app users."""
from __future__ import annotations

import hashlib
import secrets
import urllib.parse
from typing import Any

import httpx

from discovery.config import get_settings
from mvp.user_store import (
    create_user,
    ensure_user_schema,
    get_user_by_email,
    get_user_by_google_id,
    get_user_by_id,
    storage_mode,
)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    try:
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt.encode("utf-8"),
            n=2**14,
            r=8,
            p=1,
            dklen=32,
        )
    except (MemoryError, OverflowError, ValueError) as exc:
        raise RuntimeError("Password hashing unavailable in this environment.") from exc
    return f"scrypt${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if not stored or not stored.startswith("scrypt$"):
        return False
    try:
        _, salt, digest_hex = stored.split("$", 2)
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt.encode("utf-8"),
            n=2**14,
            r=8,
            p=1,
            dklen=32,
        )
        return secrets.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def register_user(email: str, password: str, display_name: str = "") -> tuple[dict[str, Any] | None, str | None]:
    if not ensure_user_schema():
        return None, "Account storage is not available right now."
    if len(password) < 8:
        return None, "Password must be at least 8 characters."
    if "@" not in email or "." not in email.split("@")[-1]:
        return None, "Enter a valid email address."
    if get_user_by_email(email):
        return None, "An account with this email already exists. Try signing in."
    try:
        password_hash = hash_password(password)
    except RuntimeError:
        return None, "Account sign-up is temporarily unavailable. Please try again later."
    user = create_user(
        email=email,
        password_hash=password_hash,
        display_name=display_name.strip(),
    )
    if not user:
        return None, "Could not create account."
    return user, None


def login_user(email: str, password: str) -> tuple[dict[str, Any] | None, str | None]:
    if not ensure_user_schema():
        return None, "Account storage is not available right now."
    row = get_user_by_email(email)
    if not row or not row.get("password_hash"):
        return None, "Invalid email or password."
    if not verify_password(password, row["password_hash"]):
        return None, "Invalid email or password."
    return {k: v for k, v in row.items() if k != "password_hash"}, None


def google_oauth_configured() -> bool:
    s = get_settings()
    return bool(s.google_client_id.strip() and s.google_client_secret.strip())


def google_login_redirect_uri() -> str:
    return f"{get_settings().api_base_url.rstrip('/')}/api/auth/google/callback"


def build_google_auth_url(state: str) -> str:
    params = {
        "client_id": get_settings().google_client_id,
        "redirect_uri": google_login_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_google_code(code: str) -> tuple[dict[str, Any] | None, str | None]:
    if not google_oauth_configured():
        return None, "Google sign-in is not configured."
    if not ensure_user_schema():
        return None, "Account storage is not available."

    data = {
        "code": code,
        "client_id": get_settings().google_client_id,
        "client_secret": get_settings().google_client_secret,
        "redirect_uri": google_login_redirect_uri(),
        "grant_type": "authorization_code",
    }
    try:
        with httpx.Client(timeout=15) as client:
            token_resp = client.post(GOOGLE_TOKEN_URL, data=data)
            if token_resp.status_code != 200:
                return None, "Google sign-in failed."
            access_token = token_resp.json().get("access_token")
            if not access_token:
                return None, "Google sign-in failed."
            user_resp = client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if user_resp.status_code != 200:
                return None, "Could not read Google profile."
            profile = user_resp.json()
    except httpx.HTTPError:
        return None, "Google sign-in timed out."

    google_id = profile.get("sub")
    email = (profile.get("email") or "").lower()
    if not google_id or not email:
        return None, "Google account missing email."

    existing = get_user_by_google_id(google_id)
    if existing:
        return {k: v for k, v in existing.items() if k != "password_hash"}, None

    by_email = get_user_by_email(email)
    if by_email:
        return {k: v for k, v in by_email.items() if k != "password_hash"}, None

    user = create_user(
        email=email,
        display_name=profile.get("name") or email.split("@")[0],
        google_id=google_id,
        avatar_url=profile.get("picture") or "",
    )
    if not user:
        return None, "Could not create account from Google."
    return user, None


def public_auth_status(user: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "storage": storage_mode(),
        "google_configured": google_oauth_configured(),
        "logged_in": bool(user),
        "user": user,
    }


def user_from_id(user_id: str | None) -> dict[str, Any] | None:
    if not user_id:
        return None
    return get_user_by_id(user_id)
