# Chrome "Dangerous site" warning

If Chrome shows **Dangerous** or **Deceptive site ahead** on `spotify-discovery-pm.vercel.app`, it is usually a **false positive**: Google Safe Browsing flags sites that collect passwords on domains that look related to a major brand (our URL contains "spotify" and the UI is Spotify-inspired).

Bridge Sessions is **not** Spotify. It does not collect Spotify credentials.

## What we did in the product

- Top bar: **Not affiliated with Spotify**
- Sign-in modal shows the real hostname and states it is **not** Spotify’s login
- Terms / privacy modals clarify independent demo status

## How to clear the warning (site owner)

1. Open [Google Search Console](https://search.google.com/search-console) and add the property `https://spotify-discovery-pm.vercel.app`
2. Go to **Security & Manual Actions → Security issues**
3. Fix any listed issues (often none — false positive)
4. Click **Request review** and explain:
   - Independent music discovery demo
   - Email/password is for Bridge Sessions accounts only, not Spotify
   - No phishing; disclaimers visible in UI
5. Review often completes in 1–3 business days

Check status: [Google Safe Browsing transparency report](https://transparencyreport.google.com/safe-browsing/search)

## Long-term

Use a custom domain **without** "spotify" in the name (e.g. `bridgesessions.app`) to reduce false positives.
