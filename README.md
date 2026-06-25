# Bridge Sessions

**Gradual music discovery — AI-planned 8-track journeys from comfort to novelty.**

[**Try it live →**](https://spotify-discovery-pm.vercel.app)

No login required. Search 10,000 chart hits, build bridge sessions from any Spotify track link, explore review insights, and ask questions grounded in 620+ real user voices.

---

## Features

| | |
|---|---|
| **Bridge Sessions** | Describe your mood or paste a Spotify track URL. Get an 8-track journey with explainable transitions — each step a small hop, not a random shuffle. |
| **Discovery Lab** | Interactive theme dashboard from App Store, Play Store, Reddit, and HN reviews — see what users actually say about music discovery. |
| **Ask Corpus** | RAG-powered Q&A over the review corpus with citations. Ask custom questions or use built-in growth prompts. |
| **Global search** | 10k popular tracks (static catalog, no API keys) or full Spotify catalog when API credentials are configured. |
| **Share links** | Copy a URL to send a bridge session to anyone — intent and anchor preserved. |

**Optional:** Connect Spotify to save bridge sessions as private playlists (requires API credentials).

---

## How it works

```
Reviews (620+)  →  classify + embed  →  Discovery Lab + Ask Corpus
Spotify track   →  search + LLM plan  →  8-track Bridge Session
Chart catalog   →  10k static index   →  search without API keys
```

1. **Ingest & index** — Reviews from App Store, Play Store, Reddit, and HN are classified by theme, segment, and sentiment, then embedded for retrieval.
2. **Bridge planning** — Given an intent and optional anchor track, the planner gathers candidates via Search API (or chart catalog in demo mode) and sequences eight tracks with transition notes.
3. **Serve** — FastAPI backend on Vercel; static Spotify-inspired UI with single navigation across Home, Bridge Sessions, Discovery Lab, and Ask Corpus.

Spotify deprecated `/recommendations` for new developer apps (Nov 2024+). This product uses **Search API + LLM planning** instead — a deliberate constraint that keeps sessions explainable.

---

## Quick start (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # MOCK_MODE=true works without keys

export PYTHONPATH=.
python ingest/seed_corpus.py
uvicorn api.main:app --reload --port 8000
# → http://localhost:8000
```

```bash
bash scripts/smoke_test.sh
```

Verify: `curl http://localhost:8000/health` should return `chart_catalog_tracks: 10000` and `catalog_search: true`.

---

## Project structure

```
api/          FastAPI routes (bridge, search, RAG, insights)
web/          Static UI (Home, Bridge Sessions, Discovery Lab, Ask Corpus)
mvp/          Spotify OAuth, bridge planner, chart catalog search
analysis/     Classification, embeddings, clustering, RAG
ingest/       Review scrapers + seed corpus
data/         corpus.json, chart_catalog.json (10k tracks)
docs/         Production deployment guide
```

---

## API

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Status, review count, catalog size |
| `POST /api/bridge` | Generate 8-track bridge session |
| `GET /api/search?q=` | Track search (chart catalog or Spotify) |
| `GET /api/insights` | Theme dashboard data |
| `POST /api/ask` | Custom RAG question |
| `GET /api/ask/{key}` | Built-in growth questions |

Interactive docs: https://spotify-discovery-pm.vercel.app/docs

---

## Deployment

See [`docs/PRODUCTION.md`](docs/PRODUCTION.md) for Vercel environment variables, Spotify Developer Dashboard setup, and demo vs live mode.

**Demo mode (default):** Works without Spotify or LLM keys — verified track IDs, chart catalog search, heuristic bridge planning.

**Live mode:** Set `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SESSION_SECRET`, and optionally `ANTHROPIC_API_KEY` for OAuth, full catalog search, and Claude bridge planning.

---

## Chart catalog

The static catalog (`data/chart_catalog.json`) contains 10,000 unique tracks ranked by popularity — sourced from a public dataset, no Spotify API calls.

Regenerate after updating the source CSV:

```bash
python scripts/build_chart_catalog.py
```

---

## Environment

| Variable | Purpose |
|----------|---------|
| `MOCK_MODE` | `true` = seed corpus + demo bridge (default locally) |
| `ALLOW_DEMO_MODE` | `true` = public demo without login (default in production) |
| `ANTHROPIC_API_KEY` | Claude bridge planner + RAG answers |
| `SPOTIFY_CLIENT_ID/SECRET` | OAuth + full catalog search |
| `SESSION_SECRET` | Signed HttpOnly session cookies |
| `GEMINI_API_KEY` | Optional real embeddings (hash fallback otherwise) |

---

## Strategy deck

A product strategy presentation is included at `deck/NL Spotify.pdf` (source: `deck/index.html`).

---

Built by [Attideep Raina](https://github.com/attideep). MIT-style use for learning and extension welcome — open an issue if you deploy your own fork.
