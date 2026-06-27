# Reviewer walkthrough

**Live app:** https://spotify-discovery-pm.vercel.app  
**GitHub:** https://github.com/attideep/spotify-discovery-pm

5-minute path to see the full product story — no Spotify Premium or API keys required.

---

## 1. Bridge Sessions (core product)

1. Open the app → **Bridge Sessions** (sidebar or bottom nav on mobile)
2. **Anchor track:** type `Blinding Lights` or paste any Spotify track URL
3. **Intent:** tap **Commute** context chip or type your own mood
4. **Generate bridge session** — watch the loader, then review 8 tracks with transition notes
5. **Copy share link** → open in a new tab — same intent and same 8 tracks

**What to notice:** Each step explains the transition. Planner badge shows **AI planned** (with Gemini key) or **Smart match** (heuristic).

---

## 2. Discovery Lab (research layer)

1. **Discovery Lab** tab
2. Click a **theme** card → read sample user quotes
3. **Ask about this theme** or **Try bridge for this** — pre-fills intent

---

## 3. Ask Corpus (RAG)

1. **Ask Corpus** tab
2. Click a canonical question chip, or type your own
3. Answer appears with collapsible **Source quotes**

---

## 4. Phase 1 rollout (product strategy)

1. **Home** tab → **Phase 1 rollout** card
2. Target segment: **Comfort Loop Curators** in **commute context**
3. MVP success metrics: completion, save rate, repeat sessions

---

## Optional: live mode

Requires Spotify Developer app + Premium on developer account (2026 policy).

Set in Vercel: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SESSION_SECRET`  
Optional: `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) for Gemini bridge planning

---

## Health & metrics

```bash
curl -s https://spotify-discovery-pm.vercel.app/health
curl -s https://spotify-discovery-pm.vercel.app/api/metrics
```

With `DATABASE_URL` (Supabase Postgres): bridge events are logged for analytics.
