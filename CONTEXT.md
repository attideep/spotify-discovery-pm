<!--
  LIVING CONTEXT FILE — Spotify Growth PM assignment (Bridge Sessions MVP)
  Purpose: durable memory of decisions, URLs, env checklist, and verification
  status so nothing is lost between sessions. Update as the project evolves.
  Last updated: 2026-06-25
-->

# Spotify Discovery PM — Project Context

> **Assignment:** Spotify Growth PM take-home — Review Discovery Engine +
> user research + Bridge Sessions MVP + strategy deck.
>
> **Live app:** https://spotify-discovery-pm.vercel.app
>
> **GitHub:** https://github.com/attideep/spotify-discovery-pm (branch `main`)

## Owner
- **Attideep Raina** — building step-by-step with agent assistance; prefers one
  verification step at a time.

## What was built

| Area | Location | Notes |
|---|---|---|
| Review corpus + RAG | `ingest/`, `analysis/`, `data/corpus.json` | ~620 reviews; classify + embed + `/api/ask` |
| Research artifacts | `interviews/`, `PROBLEM.md` | 6 archetypes, quote bank, validation |
| Bridge Sessions MVP | `mvp/`, `api/main.py`, `web/` | Demo + live OAuth bridge, save playlist |
| Strategy deck | `deck/NL Spotify.pdf` | Final deliverable |
| Production guide | `docs/PRODUCTION.md` | Vercel + Spotify Developer setup |

## Key technical decisions
- **Spotify Recommendations API is deprecated** for new apps → bridge uses
  **Search + artist top tracks** + LLM/heuristic planner (`mvp/bridge.py`).
- **Demo mode** uses a static **chart catalog** (`data/chart_catalog.json`, ~10k
  popular tracks) plus curated picks in `mvp/demo_tracks.py` — no API keys.
  Regenerate: `python scripts/build_chart_catalog.py`. Demo IDs pass oEmbed check.
- **OAuth:** PKCE flow, tokens in **HttpOnly signed cookies** (`mvp/auth.py`,
  `mvp/session.py`), callback `/mvp/callback`.
- **Vercel routing:** all paths → `api/main.py` (`vercel.json`); earlier CSS 404
  was caused by broken `/static/*` rewrite.

## Environment variables (Vercel / local `.env`)

| Variable | Required for | Status (typical) |
|---|---|---|
| `SPOTIFY_CLIENT_ID` | Live bridge, OAuth, save playlist | User must set |
| `SPOTIFY_CLIENT_SECRET` | OAuth token exchange | User must set |
| `SPOTIFY_REDIRECT_URI` | OAuth callback | Default: `https://spotify-discovery-pm.vercel.app/mvp/callback` |
| `SESSION_SECRET` | Signed session cookies | User must set (random 32+ chars) |
| `ANTHROPIC_API_KEY` | Claude bridge planner | Optional — heuristic fallback |
| `MOCK_MODE` | — | `false` in production |
| `ALLOW_DEMO_MODE` | Demo without login | `true` |

Check `/health` → `spotify_configured: true` when Spotify keys are set.

## Product positioning (2026-06-25)

**Public launch model:** Unlimited free use via demo bridges — no login. Connect
Spotify is **private beta** (Spotify Dev Mode caps OAuth at 5 users until
Extended Quota is approved).

Features for unlimited public use:
- Bridge Sessions (8-track journeys, verified Spotify links, **album art**)
- Paste **any** public Spotify track URL as anchor (oEmbed lookup)
- **Search bar** — full Spotify catalog when API keys set; **10k chart hits**
  from static catalog otherwise (HuggingFace popularity dataset, no cost)
- **Share bridge** via copy-link (`/#bridge?intent=…&anchor=…`)
- Discovery Lab + Ask Corpus

## Verification walkthrough (user progress)

| Step | What | Status |
|---|---|---|
| 1 | UI loads styled | ✅ Passed |
| 2 | `/health` returns OK | ✅ Passed |
| 3 | Demo bridge → Spotify links open real tracks | ✅ Passed |
| 4 | Anchor URL paste resolves | ✅ Passed |
| 5 | Vercel env vars set | Partial (no Spotify keys — Premium gate) |
| 6 | Spotify Developer | Skipped — public demo-first launch |
| 7+ | Share links, oEmbed anchors, public UX | ✅ Shipped 2026-06-25 |

### Step 3 — root cause (2026-06-25)
Nine of eleven demo track IDs were **invalid on Spotify** (404 / wrong song).
Example: `6K4Q2czNsd9kqOeJ25XGQN` does not resolve; correct ID for *The Less I
Know The Better* is `6K4t31amVTZDgR3sKmwUJJ`. `Maria También` ID pointed at
*Time (You and I)*. *Eclipse* by Crumb does not exist — replaced with *Locket*.

**Fix:** Updated `mvp/demo_tracks.py` + added `scripts/verify_demo_tracks.py`
(run in CI/smoke test before deploy).

## How to re-test Step 3
1. Open https://spotify-discovery-pm.vercel.app → **Bridge Sessions**
2. Click **Try demo**
3. Click **Generate bridge session**
4. Click any track row link → should open Spotify track page (not “Page not found”)

## Spotify Developer — Premium requirement (2026)

As of **Feb–Mar 2026**, Spotify requires an active **Premium subscription** on
the developer account to create/use Development Mode apps. See
[Spotify's Feb 2026 update](https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security).

Implications for this project:
- **Demo mode** (Steps 1–4) works without any Spotify dev account ✅
- **Live OAuth, save playlist, arbitrary track lookup** need Client ID/Secret
- Dev Mode also caps **5 test users** per app and **1 Client ID** per developer

**Workaround for assignment review:** Demo mode is production-ready for the
MVP story; live path is documented in `docs/PRODUCTION.md` for when Premium
is available.

## Open items (post-P1)
- P2: Supabase persistence, rate limiting, monitoring, custom domain
- User: add Vercel env vars for live OAuth + save playlist
- Do **not** edit `.cursor/plans/spotify_discovery_pm_5640145e.plan.md`

## Session log (recent)
- **2026-06-25:** UX pass — removed duplicate sidebar shortcuts (nav tabs only);
  Ask Corpus answers tightened (prompt + post-process; citations in collapsible
  section); Discovery Lab themes/segments clickable with drill-down + bridge/ask.
- **2026-06-25:** Static **10k chart catalog** — `data/chart_catalog.json` from
  HuggingFace popularity dataset; search + bridge pool without Spotify API keys.
- **2026-06-25:** Public demo-first UX — share links, oEmbed anchors, Connect
  Spotify moved to private beta messaging.
- **2026-06-25:** Steps 5–6 blocked — Spotify Developer requires Premium;
  user chose unlimited public demo path instead.
- **2026-06-25:** Fixed invalid demo track IDs; added `CONTEXT.md` and oEmbed
  verification script; user reported Spotify “Page not found” on Step 3.
