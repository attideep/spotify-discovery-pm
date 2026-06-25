from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx

from discovery.config import get_settings
from ingest.normalize import normalize, save_corpus


SPOTIFY_IOS_ID = "324684580"
SPOTIFY_ANDROID_ID = "com.spotify.music"

REDDIT_SUBS = ["truespotify", "spotify", "spotifyplaylists"]
HN_QUERIES = ["spotify discover", "spotify recommendations", "spotify algorithm"]


def fetch_play_store(limit: int = 500) -> list:
    from google_play_scraper import Sort, reviews

    out = []
    token = None
    while len(out) < limit:
        batch, token = reviews(
            SPOTIFY_ANDROID_ID,
            lang="en",
            country="us",
            sort=Sort.NEWEST,
            count=min(200, limit - len(out)),
            continuation_token=token,
        )
        out.extend(batch)
        if not token:
            break
    return out[:limit]


def fetch_app_store(limit: int = 500) -> list:
    from app_store_scraper import AppStore

    app = AppStore(country="us", app_name="spotify", app_id=int(SPOTIFY_IOS_ID))
    app.review(how_many=limit)
    return app.reviews


def fetch_reddit(limit_per_sub: int = 100) -> list[dict]:
    records = []
    headers = {"User-Agent": "spotify-discovery-pm/1.0"}
    with httpx.Client(timeout=30, headers=headers) as client:
        for sub in REDDIT_SUBS:
            url = f"https://www.reddit.com/r/{sub}/search.json?q=recommendation+OR+discover+OR+playlist&restrict_sr=1&sort=relevance&limit={limit_per_sub}"
            try:
                r = client.get(url)
                if r.status_code != 200:
                    continue
                for child in r.json().get("data", {}).get("children", []):
                    d = child.get("data", {})
                    text = d.get("selftext") or d.get("title", "")
                    if len(text) < 40:
                        continue
                    records.append(
                        {
                            "text": text,
                            "url": f"https://reddit.com{d.get('permalink', '')}",
                            "score": d.get("score", 0),
                            "sub": sub,
                        }
                    )
            except Exception:
                continue
    return records


def fetch_hn(limit: int = 100) -> list[dict]:
    records = []
    headers = {"User-Agent": "spotify-discovery-pm/1.0"}
    with httpx.Client(timeout=30, headers=headers) as client:
        for q in HN_QUERIES:
            url = f"https://hn.algolia.com/api/v1/search?query={q}&tags=story,comment&hitsPerPage={limit // len(HN_QUERIES)}"
            try:
                r = client.get(url)
                for hit in r.json().get("hits", []):
                    text = hit.get("comment_text") or hit.get("story_text") or hit.get("title", "")
                    if len(text) < 40:
                        continue
                    records.append(
                        {
                            "text": text,
                            "url": f"https://news.ycombinator.com/item?id={hit.get('objectID', hit.get('story_id', ''))}",
                            "points": hit.get("points", 0),
                        }
                    )
            except Exception:
                continue
    return records


def run_ingest(output_path: str | None = None) -> str:
    settings = get_settings()
    path = output_path or settings.corpus_path
    records = []
    idx = 0

    try:
        for rev in fetch_play_store(500):
            records.append(
                normalize(
                    "play_store",
                    "android",
                    rev.get("content", ""),
                    rating=rev.get("score"),
                    date=rev.get("at"),
                    url=None,
                    idx=idx,
                )
            )
            idx += 1
    except Exception as e:
        print(f"Play Store skip: {e}")

    try:
        for rev in fetch_app_store(500):
            records.append(
                normalize(
                    "app_store",
                    "ios",
                    rev.get("review", ""),
                    rating=rev.get("rating"),
                    date=datetime.fromisoformat(rev["date"]) if rev.get("date") else None,
                    url=None,
                    idx=idx,
                )
            )
            idx += 1
    except Exception as e:
        print(f"App Store skip: {e}")

    for item in fetch_reddit(100):
        records.append(
            normalize(
                f"reddit_{item['sub']}",
                "reddit",
                item["text"],
                url=item.get("url"),
                idx=idx,
            )
        )
        idx += 1

    for item in fetch_hn(100):
        records.append(
            normalize("hackernews", "forum", item["text"], url=item.get("url"), idx=idx)
        )
        idx += 1

    save_corpus(records, path)
    return path


if __name__ == "__main__":
    p = run_ingest()
    data = json.loads(open(p).read())
    print(f"Ingested {len(data)} records -> {p}")
