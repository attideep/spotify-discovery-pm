from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Theme(str, Enum):
    DISCOVERY_FATIGUE = "discovery_fatigue"
    RECOMMENDATION_IRRELEVANCE = "recommendation_irrelevance"
    COMFORT_LOOP = "comfort_loop"
    ALGORITHM_ANXIETY = "algorithm_anxiety"
    SOCIAL_DISCOVERY = "social_discovery"
    PODCAST_DRIFT = "podcast_drift"
    UI_FRICTION = "ui_friction"
    POSITIVE_DISCOVERY = "positive_discovery"


class Segment(str, Enum):
    COMFORT_LOOP_CURATOR = "comfort_loop_curator"
    ALGORITHM_SKEPTIC = "algorithm_skeptic"
    CONTEXT_SWITCHER = "context_switcher"
    SOCIAL_DISCOVERER = "social_discoverer"
    TIME_POOR_COMMUTER = "time_poor_commuter"
    GENRE_EXPLORER_BURNED = "genre_explorer_burned"
    GENERAL = "general"


class ReviewRecord(BaseModel):
    id: str
    source: str
    platform: str
    text: str
    rating: Optional[float] = None
    date: Optional[datetime] = None
    url: Optional[str] = None
    themes: list[str] = Field(default_factory=list)
    segment: str = Segment.GENERAL.value
    sentiment: float = 0.0


class ThemeInsight(BaseModel):
    theme: str
    count: int
    pct: float
    summary: str
    exemplars: list[dict]


class AskResponse(BaseModel):
    question: str
    answer: str
    citations: list[dict]


class BridgeTrack(BaseModel):
    position: int
    track_id: str
    name: str
    artist: str
    spotify_url: str
    album_art: str = ""
    explanation: str
    novelty_score: float


class BridgeSession(BaseModel):
    anchor_track: str
    anchor_id: str = ""
    intent: str
    tracks: list[BridgeTrack]
    session_summary: str
    planner: str = "heuristic"
