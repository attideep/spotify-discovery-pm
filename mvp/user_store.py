"""User accounts and saved bridges — Postgres (prod) or SQLite (local dev)."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from discovery.config import get_settings

_USER_SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS app_users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    display_name TEXT NOT NULL DEFAULT '',
    google_id TEXT UNIQUE,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS saved_bridges (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    intent TEXT NOT NULL,
    anchor_track TEXT NOT NULL DEFAULT '',
    anchor_id TEXT,
    session_summary TEXT NOT NULL DEFAULT '',
    tracks_json JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_saved_bridges_user ON saved_bridges(user_id, created_at DESC);
"""

_user_schema_ready = False


def _sqlite_path() -> Path:
    """Vercel serverless has a read-only project dir; only /tmp is writable."""
    if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
        return Path("/tmp") / "spotify-discovery-users.db"
    return Path(__file__).resolve().parent.parent / "data" / "users.db"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pg_conn():
    url = get_settings().database_url.strip()
    if not url:
        return None
    import psycopg

    return psycopg.connect(url)


def _sqlite_conn() -> sqlite3.Connection:
    path = _sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def storage_mode() -> str:
    if get_settings().database_url.strip():
        return "postgres"
    if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
        return "sqlite-ephemeral"
    return "sqlite"


def ensure_user_schema() -> bool:
    global _user_schema_ready
    if _user_schema_ready:
        return True

    pg = _pg_conn()
    if pg:
        try:
            with pg, pg.cursor() as cur:
                cur.execute(_USER_SCHEMA_PG)
            _user_schema_ready = True
            return True
        except Exception:
            return False
        finally:
            pg.close()

    try:
        conn = _sqlite_conn()
        with conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS app_users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    display_name TEXT NOT NULL DEFAULT '',
                    google_id TEXT UNIQUE,
                    avatar_url TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS saved_bridges (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    anchor_track TEXT NOT NULL DEFAULT '',
                    anchor_id TEXT,
                    session_summary TEXT NOT NULL DEFAULT '',
                    tracks_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES app_users(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_saved_bridges_user ON saved_bridges(user_id, created_at);
                """
            )
        conn.close()
        _user_schema_ready = True
        return True
    except Exception:
        return False


def create_user(
    *,
    email: str,
    password_hash: str | None = None,
    display_name: str = "",
    google_id: str | None = None,
    avatar_url: str = "",
) -> dict[str, Any] | None:
    if not ensure_user_schema():
        return None
    uid = str(uuid.uuid4())
    email_norm = email.strip().lower()
    display = display_name or email_norm.split("@")[0]
    row = {
        "id": uid,
        "email": email_norm,
        "password_hash": password_hash,
        "display_name": display,
        "google_id": google_id,
        "avatar_url": avatar_url or "",
        "created_at": _now_iso(),
    }

    pg = _pg_conn()
    if pg:
        try:
            with pg, pg.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO app_users (id, email, password_hash, display_name, google_id, avatar_url)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, email, display_name, google_id, avatar_url, created_at
                    """,
                    (uid, email_norm, password_hash, display, google_id, avatar_url or None),
                )
                r = cur.fetchone()
            return _public_user(r)
        except Exception:
            return None
        finally:
            pg.close()

    try:
        conn = _sqlite_conn()
        with conn:
            conn.execute(
                """
                INSERT INTO app_users (id, email, password_hash, display_name, google_id, avatar_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (uid, email_norm, password_hash, display, google_id, avatar_url or "", row["created_at"]),
            )
        conn.close()
        return {k: v for k, v in row.items() if k != "password_hash"}
    except sqlite3.IntegrityError:
        return None
    except Exception:
        return None


def get_user_by_email(email: str) -> dict[str, Any] | None:
    if not ensure_user_schema():
        return None
    email_norm = email.strip().lower()
    pg = _pg_conn()
    if pg:
        try:
            with pg, pg.cursor() as cur:
                cur.execute(
                    "SELECT id, email, password_hash, display_name, google_id, avatar_url, created_at FROM app_users WHERE email = %s",
                    (email_norm,),
                )
                r = cur.fetchone()
            return _user_row(r, include_hash=True) if r else None
        finally:
            pg.close()
    conn = _sqlite_conn()
    r = conn.execute(
        "SELECT id, email, password_hash, display_name, google_id, avatar_url, created_at FROM app_users WHERE email = ?",
        (email_norm,),
    ).fetchone()
    conn.close()
    return dict(r) if r else None


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    if not ensure_user_schema():
        return None
    pg = _pg_conn()
    if pg:
        try:
            with pg, pg.cursor() as cur:
                cur.execute(
                    "SELECT id, email, display_name, google_id, avatar_url, created_at FROM app_users WHERE id = %s",
                    (user_id,),
                )
                r = cur.fetchone()
            return _public_user(r) if r else None
        finally:
            pg.close()
    conn = _sqlite_conn()
    r = conn.execute(
        "SELECT id, email, display_name, google_id, avatar_url, created_at FROM app_users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(r) if r else None


def get_user_by_google_id(google_id: str) -> dict[str, Any] | None:
    if not ensure_user_schema():
        return None
    pg = _pg_conn()
    if pg:
        try:
            with pg, pg.cursor() as cur:
                cur.execute(
                    "SELECT id, email, password_hash, display_name, google_id, avatar_url, created_at FROM app_users WHERE google_id = %s",
                    (google_id,),
                )
                r = cur.fetchone()
            return _user_row(r, include_hash=True) if r else None
        finally:
            pg.close()
    conn = _sqlite_conn()
    r = conn.execute(
        "SELECT id, email, password_hash, display_name, google_id, avatar_url, created_at FROM app_users WHERE google_id = ?",
        (google_id,),
    ).fetchone()
    conn.close()
    return dict(r) if r else None


def save_bridge(user_id: str, session: dict[str, Any]) -> dict[str, Any] | None:
    if not ensure_user_schema():
        return None
    bid = str(uuid.uuid4())
    tracks = session.get("tracks") or []
    title = f"Bridge from {session.get('anchor_track', 'your anchor')}"[:120]
    payload = json.dumps(tracks)
    anchor_id = session.get("anchor_id") or ""

    pg = _pg_conn()
    if pg:
        try:
            with pg, pg.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO saved_bridges (id, user_id, title, intent, anchor_track, anchor_id, session_summary, tracks_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    RETURNING id, title, intent, anchor_track, anchor_id, session_summary, created_at
                    """,
                    (
                        bid,
                        user_id,
                        title,
                        session.get("intent", "")[:500],
                        session.get("anchor_track", "")[:200],
                        anchor_id,
                        session.get("session_summary", "")[:1000],
                        payload,
                    ),
                )
                r = cur.fetchone()
            return {"id": r[0], "title": r[1], "intent": r[2], "anchor_track": r[3], "anchor_id": r[4], "session_summary": r[5], "created_at": str(r[6])}
        except Exception:
            return None
        finally:
            pg.close()

    try:
        conn = _sqlite_conn()
        with conn:
            conn.execute(
                """
                INSERT INTO saved_bridges (id, user_id, title, intent, anchor_track, anchor_id, session_summary, tracks_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bid,
                    user_id,
                    title,
                    session.get("intent", "")[:500],
                    session.get("anchor_track", "")[:200],
                    anchor_id,
                    session.get("session_summary", "")[:1000],
                    payload,
                    _now_iso(),
                ),
            )
        conn.close()
        return {"id": bid, "title": title, "intent": session.get("intent", ""), "anchor_track": session.get("anchor_track", ""), "anchor_id": anchor_id, "session_summary": session.get("session_summary", ""), "created_at": _now_iso()}
    except Exception:
        return None


def list_saved_bridges(user_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    if not ensure_user_schema():
        return []
    pg = _pg_conn()
    if pg:
        try:
            with pg, pg.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, intent, anchor_track, anchor_id, session_summary, tracks_json, created_at
                    FROM saved_bridges WHERE user_id = %s ORDER BY created_at DESC LIMIT %s
                    """,
                    (user_id, limit),
                )
                rows = cur.fetchall()
            return [_saved_row(r) for r in rows]
        finally:
            pg.close()
    conn = _sqlite_conn()
    rows = conn.execute(
        """
        SELECT id, title, intent, anchor_track, anchor_id, session_summary, tracks_json, created_at
        FROM saved_bridges WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [_saved_row_sqlite(r) for r in rows]


def get_saved_bridge(user_id: str, bridge_id: str) -> dict[str, Any] | None:
    if not ensure_user_schema():
        return None
    pg = _pg_conn()
    if pg:
        try:
            with pg, pg.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, intent, anchor_track, anchor_id, session_summary, tracks_json, created_at
                    FROM saved_bridges WHERE user_id = %s AND id = %s
                    """,
                    (user_id, bridge_id),
                )
                r = cur.fetchone()
            return _saved_row(r) if r else None
        finally:
            pg.close()
    conn = _sqlite_conn()
    r = conn.execute(
        """
        SELECT id, title, intent, anchor_track, anchor_id, session_summary, tracks_json, created_at
        FROM saved_bridges WHERE user_id = ? AND id = ?
        """,
        (user_id, bridge_id),
    ).fetchone()
    conn.close()
    return _saved_row_sqlite(r) if r else None


def delete_saved_bridge(user_id: str, bridge_id: str) -> bool:
    if not ensure_user_schema():
        return False
    pg = _pg_conn()
    if pg:
        try:
            with pg, pg.cursor() as cur:
                cur.execute("DELETE FROM saved_bridges WHERE user_id = %s AND id = %s", (user_id, bridge_id))
                return cur.rowcount > 0
        finally:
            pg.close()
    conn = _sqlite_conn()
    with conn:
        cur = conn.execute("DELETE FROM saved_bridges WHERE user_id = ? AND id = ?", (user_id, bridge_id))
        ok = cur.rowcount > 0
    conn.close()
    return ok


def _public_user(row) -> dict[str, Any]:
    return {
        "id": row[0],
        "email": row[1],
        "display_name": row[2],
        "google_id": row[3],
        "avatar_url": row[4] or "",
        "created_at": str(row[5]) if row[5] else "",
    }


def _user_row(row, *, include_hash: bool = False) -> dict[str, Any]:
    out = {
        "id": row[0],
        "email": row[1],
        "display_name": row[3],
        "google_id": row[4],
        "avatar_url": row[5] or "",
        "created_at": str(row[6]) if row[6] else "",
    }
    if include_hash:
        out["password_hash"] = row[2]
    return out


def _saved_row(row) -> dict[str, Any]:
    tracks = row[6] if isinstance(row[6], list) else json.loads(row[6] or "[]")
    return {
        "id": row[0],
        "title": row[1],
        "intent": row[2],
        "anchor_track": row[3],
        "anchor_id": row[4],
        "session_summary": row[5],
        "tracks": tracks,
        "created_at": str(row[7]) if row[7] else "",
    }


def _saved_row_sqlite(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "intent": row["intent"],
        "anchor_track": row["anchor_track"],
        "anchor_id": row["anchor_id"],
        "session_summary": row["session_summary"],
        "tracks": json.loads(row["tracks_json"] or "[]"),
        "created_at": row["created_at"],
    }
