# Problem Definition — Comfort Loop Curators

## Target segment

**Comfort Loop Curators** — Spotify Premium users aged 22–34 who listen 5+ hours/week, with >60% of sessions from saved playlists and Liked Songs. They rate Spotify's discovery experience 1–3/5 despite knowing the catalog is vast.

## Root cause

Spotify's collaborative-filtering stack optimizes for **session continuity and retention**, not **meaningful novelty with explainability**. Users repeat familiar content because:

1. **Opaque recommendations** — no "why this song" erodes trust after bad suggestions
2. **Batch-oriented discovery** — Discover Weekly is Monday-batch, not moment-aware (commute vs focus vs gym)
3. **Abrupt familiar→novel jump** — one weird track → skip → retreat to comfort playlists

## Evidence (triangulated)

| Theme | Corpus signal | Interview echo |
|-------|---------------|----------------|
| comfort_loop | 34% of indexed reviews | "70% from Liked Songs, discovery 2/10" |
| discovery_fatigue | 28% | "Discovery feels like work" |
| algorithm_anxiety | 19% | "I skip anything that says recommended" |
| recommendation_irrelevance | 31% | "Discover Weekly same vibe every week" |

## Business case

| Metric | Impact |
|--------|--------|
| Engaged listening minutes | Bridge sessions extend session depth with intentional novelty |
| Save rate / library growth | Explainable picks increase saves → stronger taste model |
| Premium retention | Stagnation drives cancellation; discovery restores perceived value |
| Strategic alignment | Directly supports Growth goal: increase meaningful discovery |

## Success metrics (MVP)

- Bridge session completion rate >40%
- Save rate per bridge track >15% (vs ~5% Discover Weekly baseline industry est.)
- Return usage: 2+ bridge sessions within 14 days
- Qualitative: users report "understood why" in post-session feedback

## Out of scope (v1)

- In-app playback (deep links only)
- Full playlist persistence to Spotify account
- Free-tier ad optimization
