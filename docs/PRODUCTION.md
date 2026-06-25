# Production setup (P0 + P1)

## Vercel environment variables

Set in Vercel → Project → Settings → Environment Variables:

| Variable | Required | Notes |
|----------|----------|-------|
| `SPOTIFY_CLIENT_ID` | Live mode | [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) |
| `SPOTIFY_CLIENT_SECRET` | Live mode | Same app |
| `SPOTIFY_REDIRECT_URI` | Yes | `https://spotify-discovery-pm.vercel.app/mvp/callback` |
| `SESSION_SECRET` | Yes | Random 64-char hex |
| `ANTHROPIC_API_KEY` | P1 AI | Bridge planning + RAG/classification |
| `ALLOW_DEMO_MODE` | Optional | `true` (default) — verified demo tracks without login |
| `MOCK_MODE` | Optional | `false` — set `true` only to skip live review ingest |

## Spotify Developer Dashboard

1. Create app → Web API
2. Redirect URI: `https://spotify-discovery-pm.vercel.app/mvp/callback`
3. Bundle IDs not needed (web app)

**Note:** Spotify blocked `/recommendations` and `/audio-features` for apps created after Nov 2024. This app uses **Search API + LLM planning** instead.

## User flows

### Demo (no login)
1. Click **Try demo**
2. Enter intent → Generate bridge
3. Tracks use **verified Spotify IDs** — links work on open.spotify.com

### Live (Spotify connected)
1. **Connect Spotify** → OAuth → HttpOnly cookie session
2. Optional: paste track URL as anchor
3. Generate bridge → Search API gathers candidates → Claude plans 8 tracks
4. **Save to Spotify** → creates private playlist in your account

## Architecture changes (P1)

- OAuth tokens in **signed HttpOnly cookies** (not URL params)
- PKCE verifier in short-lived cookie (serverless-safe)
- Token refresh on API calls
- Explicit errors (`auth_required`, `track_not_found`, etc.)
- No silent fallback to fake tracks on live errors
