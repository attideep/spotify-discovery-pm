from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from pathlib import Path

from discovery.config import get_settings
from discovery.models import ReviewRecord


def _hash_embedding(text: str, dim: int = 384) -> list[float]:
    out = []
    for i in range(dim):
        h = hashlib.sha256(f"{text}:{i}".encode()).digest()
        out.append((h[0] / 127.5) - 1.0)
    return out


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(x * x for x in b)) or 1e-9
    return dot / (na * nb)


class ReviewStore:
    def __init__(self, db_path: str | None = None) -> None:
        settings = get_settings()
        self.db_path = db_path or str(Path(settings.data_dir) / "reviews.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY,
                    source TEXT,
                    platform TEXT,
                    text TEXT,
                    rating REAL,
                    url TEXT,
                    themes TEXT,
                    segment TEXT,
                    sentiment REAL,
                    embedding TEXT
                )
                """
            )
            conn.commit()

    def embed(self, text: str) -> list[float]:
        settings = get_settings()
        if settings.gemini_api_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=settings.gemini_api_key)
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text,
                    task_type="retrieval_document",
                )
                return list(result["embedding"])
            except Exception:
                pass
        return _hash_embedding(text)

    def upsert(self, record: ReviewRecord) -> None:
        emb = self.embed(record.text)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO reviews
                (id, source, platform, text, rating, url, themes, segment, sentiment, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.source,
                    record.platform,
                    record.text,
                    record.rating,
                    record.url,
                    json.dumps(record.themes),
                    record.segment,
                    record.sentiment,
                    json.dumps(emb),
                ),
            )
            conn.commit()

    def load_all(self) -> list[ReviewRecord]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM reviews").fetchall()
        out = []
        for r in rows:
            out.append(
                ReviewRecord(
                    id=r[0],
                    source=r[1],
                    platform=r[2],
                    text=r[3],
                    rating=r[4],
                    url=r[5],
                    themes=json.loads(r[6] or "[]"),
                    segment=r[7] or "general",
                    sentiment=r[8] or 0.0,
                )
            )
        return out

    def search(self, query: str, k: int = 8) -> list[tuple[ReviewRecord, float]]:
        qemb = self.embed(query)
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM reviews").fetchall()
        scored = []
        for r in rows:
            emb = json.loads(r[9] or "[]")
            if not emb:
                continue
            rec = ReviewRecord(
                id=r[0],
                source=r[1],
                platform=r[2],
                text=r[3],
                rating=r[4],
                url=r[5],
                themes=json.loads(r[6] or "[]"),
                segment=r[7] or "general",
                sentiment=r[8] or 0.0,
            )
            scored.append((rec, _cosine(qemb, emb)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
