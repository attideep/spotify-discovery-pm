#!/usr/bin/env python3
"""Build a static top-chart catalog (~10k tracks) without Spotify API keys.

Source: HuggingFace maharshipandya/spotify-tracks-dataset (114k tracks with IDs).
We keep the top N unique tracks by Spotify popularity as a chart proxy.

Usage:
    python scripts/build_chart_catalog.py
    python scripts/build_chart_catalog.py --limit 10000 --verify-sample 20
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mvp.demo_tracks import DEMO_TRACKS  # noqa: E402
from mvp.oembed import lookup_track_oembed  # noqa: E402

DATASET_URL = (
    "https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset/"
    "resolve/main/dataset.csv"
)
DEFAULT_OUT = ROOT / "data" / "chart_catalog.json"
DEFAULT_CACHE = ROOT / "data" / ".spotify_tracks_dataset.csv"


def download_dataset(cache_path: Path) -> None:
    if cache_path.exists() and cache_path.stat().st_size > 1_000_000:
        print(f"Using cached dataset: {cache_path}")
        return
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {DATASET_URL} …")
    urllib.request.urlretrieve(DATASET_URL, cache_path)
    print(f"Saved {cache_path.stat().st_size // 1024} KB")


def _artist_label(raw: str) -> str:
    return raw.replace(";", ", ").strip()


def load_top_tracks(csv_path: Path, limit: int) -> list[dict]:
    best: dict[str, dict] = {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tid = (row.get("track_id") or "").strip()
            if not tid or len(tid) != 22:
                continue
            try:
                pop = int(row.get("popularity") or 0)
            except ValueError:
                pop = 0
            name = (row.get("track_name") or "").strip()
            artist = _artist_label(row.get("artists") or "")
            if not name:
                continue
            prev = best.get(tid)
            if prev is None or pop > prev["popularity"]:
                best[tid] = {"id": tid, "name": name, "artist": artist, "popularity": pop}

    ranked = sorted(best.values(), key=lambda t: t["popularity"], reverse=True)
    top = ranked[:limit]

    demo_ids = {d["id"] for d in DEMO_TRACKS}
    top_ids = {t["id"] for t in top}
    missing_demo = [d for d in DEMO_TRACKS if d["id"] not in top_ids]
    if missing_demo:
        for d in missing_demo:
            top.append(
                {
                    "id": d["id"],
                    "name": d["name"],
                    "artist": d["artist"],
                    "popularity": 100,
                }
            )
        top.sort(key=lambda t: t["popularity"], reverse=True)
        top = top[:limit]

    return top


def verify_sample(tracks: list[dict], n: int) -> None:
    import random

    sample = tracks if len(tracks) <= n else random.sample(tracks, n)
    ok = 0
    for t in sample:
        hit = lookup_track_oembed(t["id"])
        if hit and hit.get("name"):
            ok += 1
            print(f"  OK  {t['name'][:40]} — {t['artist'][:30]}")
        else:
            print(f"  FAIL {t['id']} {t['name']}")
    print(f"oEmbed spot-check: {ok}/{len(sample)} valid")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build static chart catalog JSON")
    parser.add_argument("--limit", type=int, default=10_000)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--verify-sample", type=int, default=0)
    args = parser.parse_args()

    download_dataset(args.cache)
    tracks = load_top_tracks(args.cache, args.limit)

    payload = {
        "version": 1,
        "source": "maharshipandya/spotify-tracks-dataset",
        "description": f"Top {args.limit} unique Spotify tracks by popularity (chart proxy, no API keys)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(tracks),
        "tracks": tracks,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    size_kb = args.out.stat().st_size // 1024
    print(f"Wrote {len(tracks)} tracks → {args.out} ({size_kb} KB)")

    if args.verify_sample > 0:
        verify_sample(tracks, args.verify_sample)


if __name__ == "__main__":
    main()
