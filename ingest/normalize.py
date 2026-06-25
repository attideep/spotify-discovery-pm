from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from discovery.models import ReviewRecord


def _rid(source: str, text: str, idx: int) -> str:
    h = hashlib.sha256(f"{source}:{text[:80]}:{idx}".encode()).hexdigest()[:12]
    return f"{source}_{h}"


def normalize(
    source: str,
    platform: str,
    text: str,
    *,
    rating: Optional[float] = None,
    date: Optional[datetime] = None,
    url: Optional[str] = None,
    idx: int = 0,
) -> ReviewRecord:
    clean = re.sub(r"\s+", " ", text.strip())
    return ReviewRecord(
        id=_rid(source, clean, idx),
        source=source,
        platform=platform,
        text=clean,
        rating=rating,
        date=date or datetime.now(timezone.utc),
        url=url,
    )


def save_corpus(records: list[ReviewRecord], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = [r.model_dump(mode="json") for r in records]
    p.write_text(json.dumps(payload, indent=2, default=str))
    return p


def load_corpus(path: str | Path) -> list[ReviewRecord]:
    p = Path(path)
    if not p.exists():
        return []
    data = json.loads(p.read_text())
    return [ReviewRecord.model_validate(d) for d in data]
