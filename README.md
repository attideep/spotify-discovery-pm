# Bridge Sessions

**Discover music gradually — one intentional step at a time.**

[**Try it live →**](https://spotify-discovery-pm.vercel.app)

Bridge Sessions helps you move from a song you already love toward something new. Pick an anchor track, describe the mood you want, and get an 8-song journey with explainable transitions — not a random shuffle, not a wall of recommendations.

Free to use. No login required.

---

## What it is

Most streaming apps optimize for **repeat listening**. Bridge Sessions is built for **discovery** — the moment you want to stretch your taste without jumping straight into the deep end.

| | |
|---|---|
| **Bridge Sessions** | Start from any song. Describe where you want to go. Receive an ordered 8-track path from familiar → novel, each step explained. |
| **Discovery Lab** | Explore what real listeners say about finding music — themes, frustrations, and patterns pulled from app store and community reviews. |
| **Ask Corpus** | Ask product and discovery questions and get concise answers grounded in real user feedback. |
| **Search** | Find anchor tracks by name or artist — paste a Spotify link or just type the song title. |
| **Share** | Send a link to a friend — they open the exact same bridge you built. |

---

## How it works

```
Your anchor song  +  your intent  →  8-track bridge session
Review corpus     →  themes + Q&A  →  Discovery Lab + Ask Corpus
```

1. **You set the starting point** — a track you trust and a direction (“warm indie folk”, “more energy for a run”).
2. **The planner sequences eight tracks** — each one a small hop, ordered from safe to surprising.
3. **Discovery Lab & Ask Corpus** — separate layer that turns listener feedback into insight for product thinkers and curious users.

Bridge Sessions uses search-based planning (not black-box recommendation feeds), so every track in a session is intentional and inspectable.

---

## Quick start (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

export PYTHONPATH=.
python ingest/seed_corpus.py
uvicorn api.main:app --reload --port 8000
# → http://localhost:8000
```

```bash
bash scripts/smoke_test.sh
```

---

## API

Interactive docs: https://spotify-discovery-pm.vercel.app/docs

---

## Deployment

See [`docs/PRODUCTION.md`](docs/PRODUCTION.md) for Vercel setup, environment variables, and optional Spotify OAuth.

---

## For reviewers

**5-minute walkthrough:** [`docs/REVIEWER_WALKTHROUGH.md`](docs/REVIEWER_WALKTHROUGH.md)

**Phase 1 rollout:** Comfort Loop Curators in commute context — see the rollout card on the Home tab.

---

## Environment

| Variable | Purpose |
|----------|---------|
| `ALLOW_DEMO_MODE` | Public free mode without login (default in production) |
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Gemini bridge planner (shows **AI planned** badge) + review embeddings |
| `ANTHROPIC_API_KEY` | Optional — richer Ask Corpus answers (RAG) |
| `DATABASE_URL` | Optional Supabase — bridge analytics + distributed rate limits |
| `RATE_LIMIT_PER_MINUTE` | Abuse protection (default 30) |
| `SPOTIFY_CLIENT_ID/SECRET` | Optional — full catalog search + save to playlist |
| `SESSION_SECRET` | Signed session cookies for OAuth |

---

## What's in this repo

The public repo contains the **app source** so the product is inspectable and self-hostable. That's normal for a demo product on GitHub.

**Not in the repo (and safe from copy-paste):**
- Production API keys (`SPOTIFY_*`, `GEMINI_*` / `GOOGLE_API_KEY`, `ANTHROPIC_*`, `SESSION_SECRET`) — these live only in Vercel env vars
- Your live deployment, domain, and users
- Any private strategy or internal notes

**What someone could fork:** the UI, bridge logic, and bundled track/review datasets needed to run the app locally. They'd still need their own hosting, keys, and brand to ship a competing product.

If you prefer a closed codebase, make the GitHub repo **private** and keep only the live URL public.

---

Built by [Attideep Raina](https://github.com/attideep).
