"""Optional Postgres persistence (Supabase-compatible) for bridge analytics."""
from __future__ import annotations

from discovery.config import get_settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bridge_events (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    intent TEXT NOT NULL,
    anchor_id TEXT,
    track_ids TEXT[] NOT NULL,
    planner TEXT NOT NULL,
    mode TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rate_buckets (
    bucket_key TEXT PRIMARY KEY,
    window_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    count INT NOT NULL DEFAULT 0
);
"""

_schema_ready = False


def get_connection():
    url = get_settings().database_url.strip()
    if not url:
        return None
    import psycopg

    try:
        return psycopg.connect(url, connect_timeout=10)
    except Exception:
        return None


def ensure_schema() -> bool:
    global _schema_ready
    if _schema_ready:
        return True
    conn = get_connection()
    if not conn:
        return False
    try:
        with conn, conn.cursor() as cur:
            cur.execute(_SCHEMA)
        _schema_ready = True
        return True
    except Exception:
        return False
    finally:
        conn.close()


def log_bridge_event(
    *,
    intent: str,
    anchor_id: str,
    track_ids: list[str],
    planner: str,
    mode: str,
) -> None:
    if not ensure_schema():
        return
    conn = get_connection()
    if not conn:
        return
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO bridge_events (intent, anchor_id, track_ids, planner, mode)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (intent[:500], anchor_id or "", track_ids[:8], planner, mode),
            )
    except Exception:
        pass
    finally:
        conn.close()


def metrics_summary() -> dict:
    if not get_settings().database_url:
        return {"persistence_enabled": False}
    if not ensure_schema():
        return {"persistence_enabled": False, "error": "schema_init_failed"}
    conn = get_connection()
    if not conn:
        return {"persistence_enabled": False}
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM bridge_events")
            total = cur.fetchone()[0]
            cur.execute(
                """
                SELECT COUNT(*) FROM bridge_events
                WHERE created_at > NOW() - INTERVAL '24 hours'
                """
            )
            last_24h = cur.fetchone()[0]
            cur.execute(
                """
                SELECT planner, COUNT(*) FROM bridge_events
                GROUP BY planner ORDER BY COUNT(*) DESC LIMIT 5
                """
            )
            by_planner = {row[0]: row[1] for row in cur.fetchall()}
        return {
            "persistence_enabled": True,
            "bridges_total": total,
            "bridges_24h": last_24h,
            "by_planner": by_planner,
        }
    except Exception as exc:
        return {"persistence_enabled": True, "error": str(exc)}
    finally:
        conn.close()
