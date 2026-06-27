"""Lightweight rate limiting — Postgres when DATABASE_URL is set, else in-process."""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request

from discovery.config import get_settings

_lock = Lock()
_memory_buckets: dict[str, list[float]] = defaultdict(list)


def client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _memory_check(key: str, *, limit: int, window_sec: int) -> None:
    now = time.time()
    with _lock:
        hits = [t for t in _memory_buckets[key] if now - t < window_sec]
        if len(hits) >= limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests — please wait a minute and try again.",
            )
        hits.append(now)
        _memory_buckets[key] = hits


def _db_check(key: str, *, limit: int, window_sec: int) -> bool:
    from mvp.persistence import get_connection

    conn = get_connection()
    if not conn:
        return False
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rate_buckets (bucket_key, window_start, count)
                VALUES (%s, NOW(), 1)
                ON CONFLICT (bucket_key) DO UPDATE SET
                  count = CASE
                    WHEN rate_buckets.window_start < NOW() - make_interval(secs => %s) THEN 1
                    ELSE rate_buckets.count + 1
                  END,
                  window_start = CASE
                    WHEN rate_buckets.window_start < NOW() - make_interval(secs => %s) THEN NOW()
                    ELSE rate_buckets.window_start
                  END
                RETURNING count
                """,
                (key, window_sec, window_sec),
            )
            count = cur.fetchone()[0]
            if count > limit:
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests — please wait a minute and try again.",
                )
        return True
    except HTTPException:
        raise
    except Exception:
        return False
    finally:
        conn.close()


def enforce_rate_limit(request: Request, *, scope: str = "api") -> None:
    settings = get_settings()
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return
    key = f"{scope}:{client_key(request)}"
    if not _db_check(key, limit=limit, window_sec=60):
        _memory_check(key, limit=limit, window_sec=60)
