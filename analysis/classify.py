from __future__ import annotations

import json
import re
from collections import Counter

from discovery.config import get_settings
from discovery.models import ReviewRecord, Segment, Theme

THEME_KEYWORDS = {
    Theme.COMFORT_LOOP.value: ["comfort", "same playlist", "replay", "loop", "stuck", "repeat", "familiar", "same song", "same artist", "over and over"],
    Theme.RECOMMENDATION_IRRELEVANCE.value: ["recommend", "discover weekly", "daily mix", "release radar", "same vibe", "identical", "shuffle", "radio"],
    Theme.DISCOVERY_FATIGUE.value: ["discovery", "discover new", "find new", "new music", "new artist", "explore"],
    Theme.ALGORITHM_ANXIETY.value: ["algorithm", "distrust", "anxiety", "black box", "pigeonhole", "bubble"],
    Theme.SOCIAL_DISCOVERY.value: ["friend", "social", "share", "blend"],
    Theme.PODCAST_DRIFT.value: ["podcast"],
    Theme.UI_FRICTION.value: ["ads", "premium", "ui", "update", "crash", "bug"],
    Theme.POSITIVE_DISCOVERY.value: ["magical", "love discover", "great discover", "fresh artist"],
}

SEGMENT_KEYWORDS = {
    Segment.COMFORT_LOOP_CURATOR.value: ["comfort", "replay", "same playlist", "liked songs", "curator"],
    Segment.ALGORITHM_SKEPTIC.value: ["distrust", "skip", "manual", "black box", "anxiety"],
    Segment.CONTEXT_SWITCHER.value: ["mood", "context", "focus", "gym", "commute", "work"],
    Segment.SOCIAL_DISCOVERER.value: ["friend", "social", "share", "blend"],
    Segment.TIME_POOR_COMMUTER.value: ["commute", "time", "low-effort", "quick", "minutes"],
    Segment.GENRE_EXPLORER_BURNED.value: ["discover weekly", "burnout", "same-sounding", "saved maybe"],
}


def _keyword_themes(text: str) -> list[str]:
    lower = text.lower()
    hits = []
    for theme, kws in THEME_KEYWORDS.items():
        if any(k in lower for k in kws):
            hits.append(theme)
    if not hits:
        if any(w in lower for w in ["playlist", "listen", "music", "song"]):
            hits.append(Theme.COMFORT_LOOP.value)
        else:
            hits.append(Theme.UI_FRICTION.value)
    return hits[:3]


def _keyword_segment(text: str) -> str:
    lower = text.lower()
    scores = {seg: sum(1 for k in kws if k in lower) for seg, kws in SEGMENT_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else Segment.GENERAL.value


def _sentiment(text: str, rating: float | None) -> float:
    pos = len(re.findall(r"\b(love|great|magical|fresh|enjoy)\b", text.lower()))
    neg = len(re.findall(r"\b(hate|terrible|broken|stuck|bad|awful|same)\b", text.lower()))
    base = (pos - neg) / max(pos + neg, 1)
    if rating is not None:
        base = base * 0.5 + ((rating - 3) / 2) * 0.5
    return round(max(-1.0, min(1.0, base)), 2)


def classify_record(record: ReviewRecord) -> ReviewRecord:
    settings = get_settings()
    if settings.mock_mode or not settings.anthropic_api_key:
        record.themes = _keyword_themes(record.text)
        record.segment = _keyword_segment(record.text)
        record.sentiment = _sentiment(record.text, record.rating)
        return record

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = f"""Classify this Spotify user feedback. Return JSON only:
{{"themes": ["..."], "segment": "...", "sentiment": -1 to 1}}

Themes (pick 1-3): discovery_fatigue, recommendation_irrelevance, comfort_loop, algorithm_anxiety, social_discovery, podcast_drift, ui_friction, positive_discovery
Segments: comfort_loop_curator, algorithm_skeptic, context_switcher, social_discoverer, time_poor_commuter, genre_explorer_burned, general

Text: {record.text[:800]}"""
    msg = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text
    try:
        data = json.loads(re.search(r"\{.*\}", raw, re.S).group())
        record.themes = data.get("themes", _keyword_themes(record.text))
        record.segment = data.get("segment", _keyword_segment(record.text))
        record.sentiment = float(data.get("sentiment", 0))
    except Exception:
        record.themes = _keyword_themes(record.text)
        record.segment = _keyword_segment(record.text)
        record.sentiment = _sentiment(record.text, record.rating)
    return record


def classify_batch(records: list[ReviewRecord]) -> list[ReviewRecord]:
    return [classify_record(r) for r in records]
