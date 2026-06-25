# Production deployment

Bridge Sessions runs on [Vercel](https://vercel.com) as a Python serverless function (`api/main.py`) with static assets from `web/`.

**Live:** https://spotify-discovery-pm.vercel.app  
**Health check:** https://spotify-discovery-pm.vercel.app/health

Expected healthy response:

```json
{
  "status": "ok",
  "reviews_indexed": 620,
  "spotify_configured": false,
  "catalog_search": true,
  "chart_catalog_tracks": 10000,
  "allow_demo_mode": true
}
```

`catalog_search: true` when either Spotify API keys are set **or** the static chart catalog is present (committed in `data/chart_catalog.json`).

---

## Vercel environment variables

Set in Vercel → Project → Settings → Environment Variables:

| Variable | Required | Notes |
|----------|----------|-------|
| `SPOTIFY_CLIENT_ID` | Live mode | [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) |
| `SPOTIFY_CLIENT_SECRET` | Live mode | Same app |
| `SPOTIFY_REDIRECT_URI` | Live OAuth | `https://spotify-discovery-pm.vercel.app/mvp/callback` |
| `SESSION_SECRET` | Live OAuth | Random 64-char hex |
| `ANTHROPIC_API_KEY` | Optional | Claude bridge planner + RAG; heuristic fallback without it |
| `ALLOW_DEMO_MODE` | Optional | `true` (default) — public demo without login |
| `MOCK_MODE` | Optional | `false` in production; `true` skips live review ingest |

No env vars are required for the public demo — chart catalog search and demo bridges work out of the box.

---

## Spotify Developer Dashboard

1. Create app → Web API
2. Redirect URI: `https://spotify-discovery-pm.vercel.app/mvp/callback`
3. Bundle IDs not needed (web app)

**API constraint:** Spotify blocked `/recommendations` and `/audio-features` for apps created after Nov 2024. Bridge Sessions uses **Search API + LLM planning** instead.

OAuth is capped at 5 users in Spotify Dev Mode until Extended Quota is approved — demo mode is the primary public experience.

---

## User flows

### Demo (no login — default public experience)

1. Open the app → **Bridge Sessions** → enter intent → **Generate bridge session**
2. Optional: paste any public Spotify track URL as anchor
3. Search bar queries 10k chart hits (or full catalog if API keys set)
4. Tracks use verified IDs — links open on open.spotify.com
5. **Copy share link** to send the session to anyone

### Live (Spotify connected)

1. **Connect Spotify** → OAuth → HttpOnly cookie session
2. Optional: paste track URL as anchor
3. Generate bridge → Search API gathers candidates → Claude plans 8 tracks
4. **Save to Spotify** → creates private playlist in your account

---

## Architecture

- **Routing:** `vercel.json` routes all paths to `api/main.py`; static files served from `web/`
- **Auth:** OAuth tokens in signed HttpOnly cookies (not URL params); PKCE verifier in short-lived cookie (serverless-safe)
- **Search:** Spotify Search API when configured; falls back to static `data/chart_catalog.json` (10k tracks, no API cost)
- **Bridge planner:** Claude when `ANTHROPIC_API_KEY` set; heuristic fallback otherwise
- **Errors:** Explicit codes (`auth_required`, `track_not_found`, etc.) — no silent fallback to fake tracks on live errors

---

## Deploy

Push to `main` triggers Vercel if the project is linked. Manual redeploy: Vercel dashboard → Deployments → Redeploy.

Post-deploy verification:

```bash
curl -s https://spotify-discovery-pm.vercel.app/health | python3 -m json.tool
bash scripts/smoke_test.sh   # against localhost; adapt BASE_URL for production
```

---

## Regenerating the chart catalog

The catalog ships committed in the repo. To rebuild from source data:

```bash
python scripts/build_chart_catalog.py
git add data/chart_catalog.json
```

Source CSV (`data/.spotify_tracks_dataset.csv`) is gitignored; download separately or use the HuggingFace dataset referenced in the build script.
