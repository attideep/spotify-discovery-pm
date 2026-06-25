# Spotify Discovery PM — AI Discovery Engine + Bridge Sessions MVP

Growth PM assignment: AI-powered review analysis, user research synthesis, problem definition, and production MVP for Spotify music discovery.

## Live links

| Artifact | URL |
|----------|-----|
| Review Discovery Engine | https://spotify-discovery-pm.vercel.app |
| Bridge Sessions MVP | https://spotify-discovery-pm.vercel.app/bridge.html |
| API docs | https://spotify-discovery-pm.vercel.app/docs |
| Deck (PDF) | `deck/NL Spotify.pdf` |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # MOCK_MODE=true works without keys

export PYTHONPATH=.
python ingest/seed_corpus.py
uvicorn api.main:app --reload --port 8000
# → http://localhost:8000 (Review Engine)
# → http://localhost:8000/bridge.html (MVP)
```

```bash
bash scripts/smoke_test.sh
```

## Project structure

```
ingest/       Scrapers + seed corpus
analysis/     Classify, embed, cluster, RAG
api/          FastAPI (Review Engine + Bridge Sessions)
web/          Static UI
mvp/          Spotify OAuth + bridge planner
interviews/   Quote bank, 6 archetypes, problem definition
deck/         10-slide HTML deck → NL Spotify.pdf
```

## Part 1 — Review Discovery Engine

1. **Ingest** App Store, Play Store, Reddit, HN
2. **Classify** themes, segments, sentiment (LLM or keyword fallback)
3. **Index** SQLite + hash embeddings (optional Gemini/Supabase)
4. **RAG Q&A** — six canonical growth questions with citations

API:
- `POST /api/ingest` — run ingest + index
- `GET /api/insights` — theme dashboard
- `POST /api/ask` — custom question
- `GET /api/ask/{key}` — canonical questions

## Part 2 — Research

Internet-grounded synthesis in `interviews/`:
- 6 archetype transcripts (grounded in verbatim quotes)
- `quote_bank.md`, `validation_table.md`, `screener.md`

## Part 3 — Problem

**Comfort Loop Curators** — see `interviews/PROBLEM.md`

## Part 4 — Bridge Sessions MVP

Conversational 8-track bridge from comfort anchor → novel artists with explainable transitions.

- `GET /mvp/login` — Spotify OAuth
- `POST /api/bridge` — generate session
- Demo mode works without Spotify keys

## Production (P0 + P1)

See [`docs/PRODUCTION.md`](docs/PRODUCTION.md) for Vercel + Spotify Dashboard setup.

**Demo mode:** verified Spotify track IDs — links work without login.  
**Live mode:** OAuth cookie session → Search API + Claude bridge planner → Save playlist.

Required Vercel env vars for live: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SESSION_SECRET`, `ANTHROPIC_API_KEY`.

## Deck

Open `deck/index.html` in Chrome → Print → Save as PDF as `NL Spotify.pdf`

Or: `python scripts/export_deck_pdf.py` (requires weasyprint)

## Environment

| Variable | Purpose |
|----------|---------|
| MOCK_MODE | true = seed corpus + demo bridge (default) |
| ANTHROPIC_API_KEY | Live LLM classification + RAG |
| SPOTIFY_CLIENT_ID/SECRET | Live Bridge Sessions |
| GEMINI_API_KEY | Optional real embeddings |
