const API = window.API_BASE || "";
const FETCH_OPTS = { credentials: "include" };

const EXAMPLE_ANCHORS = [
  { label: "Holocene · Bon Iver", url: "https://open.spotify.com/track/35KiiILklye1JRRctaLUb4" },
  { label: "Tame Impala", url: "https://open.spotify.com/track/6K4t31amVTZDgR3sKmwUJJ" },
  { label: "Khruangbin", url: "https://open.spotify.com/track/0bOqusuuIBSYnIyVswZJPV" },
];

const EXAMPLE_INTENTS = [
  "Like Khruangbin but more energetic for a morning run",
  "Warm indie folk, slow build",
  "Psychedelic groove — safe steps toward something new",
];

const CONTEXT_INTENTS = [
  { label: "Commute", text: "Commute — steady energy, gradual novelty from my anchor" },
  { label: "Focus", text: "Focus work — smooth textures, low distraction" },
  { label: "Workout", text: "Workout — build energy as the bridge progresses" },
  { label: "Wind down", text: "Wind down — calmer tracks toward the end" },
];

const PLANNER_LABELS = {
  openai: "AI planned",
  gemini: "AI planned",
  claude: "AI planned",
  heuristic: "Smart match",
  shared: "Shared session",
};

let isConnected = false;
let lastSession = null;
let currentTracks = [];
let currentTrackIdx = 0;

function parseHashState() {
  const raw = location.hash.replace("#", "");
  const [tabPart, queryPart] = raw.split("?");
  const tab = tabPart || (location.pathname.includes("bridge") ? "bridge" : "home");
  const params = new URLSearchParams(queryPart || "");
  return { tab, params };
}

function parseTrackId(raw) {
  if (!raw) return "";
  const m = raw.match(/track\/([A-Za-z0-9]{22})/);
  if (m) return m[1];
  return /^[A-Za-z0-9]{22}$/.test(raw) ? raw : "";
}

function buildShareUrl(session) {
  const qs = new URLSearchParams();
  qs.set("intent", session.intent);
  const anchorId = session.anchor_id || session._shareAnchor || parseTrackId(document.getElementById("anchorInput")?.value || "");
  if (anchorId) qs.set("anchor", anchorId);
  const ids = (session.tracks || []).map(t => t.track_id).filter(Boolean);
  if (ids.length) qs.set("tracks", ids.join(","));
  return `${location.origin}/#bridge?${qs.toString()}`;
}

/** Legacy blob decode — kept for old links; prefer intent+anchor URLs. */
function decodeShare(encoded) {
  const toBytes = (b64) => {
    let norm = b64.replace(/-/g, "+").replace(/_/g, "/");
    while (norm.length % 4) norm += "=";
    const bin = atob(norm);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i);
    return new TextDecoder().decode(bytes);
  };
  let slim;
  try {
    slim = JSON.parse(toBytes(encoded));
  } catch {
    slim = JSON.parse(decodeURIComponent(escape(atob(encoded))));
  }
  return {
    anchor_track: slim.a,
    intent: slim.i,
    session_summary: slim.s,
    mode: slim.m || "demo",
    tracks: (slim.t || []).map(t => ({
      position: t.p,
      track_id: t.id,
      name: t.n,
      artist: t.ar,
      spotify_url: t.u,
      explanation: t.e,
      novelty_score: t.nv,
    })),
  };
}

async function tryLoadSharedBridge(shareParams) {
  const params = shareParams || parseHashState().params;
  const hasShare = params.get("share") || params.get("intent") || params.get("i");
  if (!hasShare) return;

  switchTab("bridge", { preserveQuery: true });
  clearBridgeError();
  setBridgeLoading(true, "Loading shared bridge…");

  if (params.get("share")) {
    try {
      displaySession(decodeShare(params.get("share")));
      setBridgeLoading(false);
      toast("Shared bridge session loaded");
      return;
    } catch {
      /* fall through to intent+anchor if present */
    }
  }

  const intent = params.get("intent") || params.get("i");
  if (!intent) {
    setBridgeLoading(false);
    showBridgeError("Could not load shared bridge — link may be truncated. Generate a new one and copy again.");
    return;
  }

  const anchorId = params.get("anchor") || params.get("a");
  const anchor = anchorId ? `https://open.spotify.com/track/${anchorId}` : null;
  const trackIds = (params.get("tracks") || "")
    .split(",")
    .map(s => s.trim())
    .filter(id => /^[A-Za-z0-9]{22}$/.test(id));

  try {
    let session;
    if (trackIds.length >= 8) {
      session = await fetchJSON("/api/bridge/restore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ intent, anchor: anchorId, track_ids: trackIds.slice(0, 8) }),
      });
    } else {
      session = await fetchJSON("/api/bridge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ intent, anchor, demo: !isConnected }),
      });
    }
    session._shareAnchor = anchorId || session.anchor_id || "";
    document.getElementById("intentInput").value = intent;
    if (anchor) {
      document.getElementById("anchorInput").value = anchor;
      previewAnchor();
    }
    displaySession(session);
    document.getElementById("sessionBlock")?.scrollIntoView({ behavior: "smooth", block: "start" });
    toast("Shared bridge session loaded");
  } catch (e) {
    showBridgeError(e.message || "Could not load shared bridge.");
  } finally {
    setBridgeLoading(false);
  }
}

function displaySession(session) {
  lastSession = session;
  document.getElementById("sessionBlock").classList.remove("hidden");
  document.getElementById("sessionTitle").textContent = `Bridge from ${session.anchor_track}`;
  document.getElementById("sessionSummary").textContent = session.session_summary;
  document.getElementById("sessionMode").textContent = session.mode === "live" ? "Live beta" : "Free";
  const plannerEl = document.getElementById("sessionPlanner");
  const plannerLabel = PLANNER_LABELS[session.planner] || "";
  if (plannerEl) {
    if (plannerLabel) {
      plannerEl.textContent = plannerLabel;
      plannerEl.classList.remove("hidden");
    } else {
      plannerEl.classList.add("hidden");
    }
  }
  renderTracks(session.tracks);

  const saveBtn = document.getElementById("savePlaylistBtn");
  const shareBtn = document.getElementById("shareBridgeBtn");
  if (isConnected && session.mode === "live") {
    saveBtn.classList.remove("hidden");
  } else {
    saveBtn.classList.add("hidden");
  }
  shareBtn.classList.remove("hidden");
}

async function fetchJSON(path, opts = {}) {
  const r = await fetch(`${API}${path}`, { ...FETCH_OPTS, ...opts });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    let msg = data.error || data.detail || r.statusText;
    if (r.status >= 500 && (!msg || msg === "Internal Server Error")) {
      msg = "Server error — try again in a moment. Bridges still work in Smart match mode.";
    }
    const err = new Error(msg);
    err.code = data.code;
    err.status = r.status;
    throw err;
  }
  return data;
}

function toast(msg) {
  const el = document.getElementById("statusToast");
  el.textContent = msg;
  el.classList.add("visible");
  setTimeout(() => el.classList.remove("visible"), 2800);
}

function showBridgeError(msg) {
  const el = document.getElementById("bridgeError");
  el.textContent = msg;
  el.classList.remove("hidden");
}

function clearBridgeError() {
  document.getElementById("bridgeError").classList.add("hidden");
}

function setBridgeLoading(loading, message = "Building your bridge…") {
  const overlay = document.getElementById("bridgeLoader");
  const title = document.getElementById("bridgeLoaderTitle");
  const btn = document.getElementById("buildBtn");
  if (title) title.textContent = message;
  overlay?.classList.toggle("hidden", !loading);
  if (btn) {
    btn.disabled = loading;
    btn.setAttribute("aria-busy", loading ? "true" : "false");
  }
}

/* ── Tab navigation ── */
const TAB_ACCENTS = { home: "home", bridge: "bridge", insights: "insights", ask: "insights" };

const THEME_BRIDGE_INTENTS = {
  discovery_fatigue: "Gradual discovery — low-effort steps from music I already love",
  recommendation_irrelevance: "Fresh recommendations that don't repeat my usual playlists",
  comfort_loop: "Help me expand beyond my comfort playlists without random jumps",
  algorithm_anxiety: "Explainable music suggestions I can trust",
  social_discovery: "Discovery paths inspired by what friends share",
  podcast_drift: "More music discovery, less podcast clutter in my feed",
  ui_friction: "Easy-to-find discovery features for new artists",
  positive_discovery: "Recreate that magical discovery moment more often",
};

const SEGMENT_BRIDGE_INTENTS = {
  comfort_loop_curator: "Gradual bridges from my favorite playlists toward something new",
  algorithm_skeptic: "Transparent, explainable track suggestions — not black-box picks",
  context_switcher: "Discovery that fits my current mood and context",
  social_discoverer: "Novel artists through trusted social signals",
  time_poor_commuter: "Quick, low-effort discovery for my commute",
  genre_explorer_burned: "Controlled novelty — diverse but not random genre jumps",
  general: "Safe steps toward new music without leaving my taste zone",
};

let insightsCache = null;
let activeTheme = null;
let activeSegment = null;

function switchTab(tab, { preserveQuery = false } = {}) {
  document.querySelectorAll(".nav-item").forEach(n => {
    n.classList.toggle("active", n.dataset.tab === tab);
  });
  document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
  const panel = document.getElementById(`panel-${tab}`);
  if (panel) panel.classList.add("active");
  document.getElementById("mainArea").dataset.accent = TAB_ACCENTS[tab] || "home";

  if (tab === "home") {
    history.replaceState(null, "", "/");
    return;
  }

  const query = preserveQuery && location.hash.includes("?")
    ? location.hash.slice(location.hash.indexOf("?"))
    : "";
  history.replaceState(null, "", `/#${tab}${query}`);
}

function initExampleChips() {
  const anchorEl = document.getElementById("anchorChips");
  anchorEl.innerHTML = EXAMPLE_ANCHORS.map(a =>
    `<button type="button" class="chip" data-anchor="${a.url}">${a.label}</button>`
  ).join("");
  anchorEl.querySelectorAll(".chip").forEach(btn => {
    btn.addEventListener("click", () => {
      document.getElementById("anchorInput").value = btn.dataset.anchor;
      previewAnchor();
    });
  });

  const intentEl = document.getElementById("intentChips");
  intentEl.innerHTML = EXAMPLE_INTENTS.map(() => `<button type="button" class="chip"></button>`).join("");
  intentEl.querySelectorAll(".chip").forEach((btn, i) => {
    const text = EXAMPLE_INTENTS[i];
    btn.textContent = text.length > 36 ? text.slice(0, 36) + "…" : text;
    btn.addEventListener("click", () => {
      document.getElementById("intentInput").value = text;
    });
  });

  const contextEl = document.getElementById("contextChips");
  if (contextEl) {
    contextEl.innerHTML = CONTEXT_INTENTS.map(c =>
      `<button type="button" class="chip chip--context">${c.label}</button>`
    ).join("");
    contextEl.querySelectorAll(".chip").forEach((btn, i) => {
      btn.addEventListener("click", () => {
        document.getElementById("intentInput").value = CONTEXT_INTENTS[i].text;
      });
    });
  }
}

document.querySelectorAll(".nav-item, .media-card, [data-tab]").forEach(el => {
  el.addEventListener("click", e => {
    const tab = el.dataset.tab;
    if (tab) {
      e.preventDefault();
      switchTab(tab);
    }
  });
});

const INITIAL_HASH = parseHashState();
if (["home", "bridge", "insights", "ask"].includes(INITIAL_HASH.tab)) {
  const hasShareQuery = Boolean(
    INITIAL_HASH.params.get("share")
    || INITIAL_HASH.params.get("intent")
    || INITIAL_HASH.params.get("i")
    || INITIAL_HASH.params.get("tracks"),
  );
  switchTab(INITIAL_HASH.tab, { preserveQuery: hasShareQuery });
}

const urlError = INITIAL_HASH.params.get("error");
if (urlError) {
  switchTab("bridge");
  showBridgeError(`Spotify connection failed (${urlError}). Try again.`);
}

/* ── Auth ── */
async function refreshAuthUI() {
  const status = await fetchJSON("/api/auth/status");
  isConnected = status.connected;
  const login = document.getElementById("spotifyLogin");
  const logout = document.getElementById("logoutBtn");
  const authStatus = document.getElementById("authStatus");
  const connectBeta = document.getElementById("connectBeta");

  if (isConnected) {
    login.textContent = `Connected · ${status.display_name}`;
    login.classList.add("btn-spotify--disabled");
    login.removeAttribute("href");
    logout.classList.remove("hidden");
    authStatus.textContent = "Beta connected — personalized bridges and save playlist enabled.";
    connectBeta?.classList.add("connect-beta--connected");
  } else {
    login.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02z"/></svg> Request beta access`;
    logout.classList.add("hidden");
    connectBeta?.classList.remove("connect-beta--connected");
    authStatus.textContent = "Free mode — unlimited bridges for everyone. No Spotify login needed.";

    if (status.spotify_configured) {
      login.classList.remove("btn-spotify--disabled");
      login.href = "/mvp/login";
      login.onclick = null;
    } else {
      login.classList.add("btn-spotify--disabled");
      login.removeAttribute("href");
      login.onclick = (e) => {
        e.preventDefault();
        toast("Private beta invites opening soon — free bridges work without login.");
      };
    }
  }
}

document.getElementById("logoutBtn")?.addEventListener("click", async () => {
  await fetchJSON("/mvp/logout", { method: "POST" });
  isConnected = false;
  await refreshAuthUI();
  toast("Logged out");
});

/* ── Anchor preview + song search ── */
let anchorSearchTimer = null;

function looksLikeSpotifyRef(raw) {
  return /spotify\.com\/track\/|spotify:track:/.test(raw) || /^[A-Za-z0-9]{22}$/.test(raw);
}

function bindSearchResultClicks(container, onPick) {
  container.querySelectorAll(".search-result").forEach(btn => {
    btn.addEventListener("click", () => onPick(btn));
  });
}

function renderSearchResultsHtml(tracks, hint) {
  if (!tracks.length) {
    return `<div class="search-results__hint">No tracks found — try the song title or artist name.</div>`;
  }
  return tracks.map(t => `
    <button type="button" class="search-result" data-url="${t.spotify_url}" data-id="${t.id}">
      ${t.album_art ? `<img class="search-result__art" src="${t.album_art}" alt="" loading="lazy" />` : `<div class="search-result__art"></div>`}
      <div class="search-result__meta">
        <div class="search-result__title">${t.name}</div>
        <div class="search-result__artist">${t.artist || "Spotify"}</div>
      </div>
    </button>
  `).join("") + (hint ? `<div class="search-results__hint">${hint}</div>` : "");
}

async function previewAnchor() {
  const raw = document.getElementById("anchorInput").value.trim();
  const preview = document.getElementById("anchorPreview");
  if (!raw) {
    preview.classList.add("hidden");
    return;
  }
  try {
    const track = await fetchJSON("/api/track/lookup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ anchor: raw }),
    });
    preview.classList.remove("hidden");
    preview.innerHTML = `
      ${track.album_art ? `<img src="${track.album_art}" alt="" />` : ""}
      <div><strong>${track.name}</strong><br/><span style="color:var(--text-subdued)">${track.artist || "Spotify track"}</span></div>`;
  } catch (e) {
    preview.classList.add("hidden");
  }
}

async function searchAnchorTracks(q) {
  const el = document.getElementById("anchorSearchResults");
  if (!el || !q || looksLikeSpotifyRef(q)) {
    el?.classList.add("hidden");
    if (q && looksLikeSpotifyRef(q)) previewAnchor();
    return;
  }
  try {
    const data = await fetchJSON(`/api/search/tracks?q=${encodeURIComponent(q)}`);
    el.innerHTML = renderSearchResultsHtml(data.tracks || [], "");
    el.classList.remove("hidden");
    bindSearchResultClicks(el, btn => {
      document.getElementById("anchorInput").value = btn.dataset.url;
      el.classList.add("hidden");
      previewAnchor();
    });
  } catch {
    el.classList.add("hidden");
  }
}

document.getElementById("anchorInput")?.addEventListener("input", e => {
  const q = e.target.value.trim();
  clearTimeout(anchorSearchTimer);
  if (!q) {
    document.getElementById("anchorSearchResults")?.classList.add("hidden");
    document.getElementById("anchorPreview")?.classList.add("hidden");
    return;
  }
  anchorSearchTimer = setTimeout(() => searchAnchorTracks(q), 280);
});

document.getElementById("anchorInput")?.addEventListener("change", previewAnchor);
document.getElementById("anchorInput")?.addEventListener("blur", () => {
  setTimeout(() => document.getElementById("anchorSearchResults")?.classList.add("hidden"), 180);
  previewAnchor();
});

/* ── Insights ── */
function themeLabel(theme) {
  return theme.replace(/_/g, " ");
}

function themeAskQuestion(theme, summary) {
  return `What do users say about ${themeLabel(theme)}? ${summary}`;
}

function showThemeDetail(theme) {
  activeTheme = theme.theme;
  activeSegment = null;
  document.querySelectorAll(".theme-card").forEach(c => {
    c.classList.toggle("theme-card--active", c.dataset.theme === theme.theme);
  });
  document.querySelectorAll(".segment-chip").forEach(c => c.classList.remove("segment-chip--active"));

  const detail = document.getElementById("themeDetail");
  detail.classList.remove("hidden");
  const quotes = (theme.exemplars || []).slice(0, 3).map(ex => `
    <blockquote class="theme-detail__quote">"${ex.text}"${ex.url ? ` — <a href="${ex.url}" target="_blank" rel="noopener">source</a>` : ""}</blockquote>
  `).join("") || `<p class="theme-detail__empty">No sample quotes loaded for this theme.</p>`;

  detail.innerHTML = `
    <div class="theme-detail__head">
      <div>
        <h3 class="theme-detail__title">${themeLabel(theme.theme)}</h3>
        <p class="theme-detail__meta">${theme.pct}% of reviews · ${theme.count} mentions</p>
      </div>
      <button type="button" class="theme-detail__close" aria-label="Close">&times;</button>
    </div>
    <p class="theme-detail__summary">${theme.summary}</p>
    <div class="theme-detail__quotes">${quotes}</div>
    <div class="chip-row chip-row--compact">
      <button type="button" class="chip" data-action="ask-theme">Ask about this theme</button>
      <button type="button" class="chip" data-action="bridge-theme">Try bridge for this</button>
    </div>`;

  detail.querySelector(".theme-detail__close")?.addEventListener("click", clearThemeDetail);
  detail.querySelector('[data-action="ask-theme"]')?.addEventListener("click", () => {
    document.getElementById("questionInput").value = themeAskQuestion(theme.theme, theme.summary);
    switchTab("ask");
    askAboutQuestion(themeAskQuestion(theme.theme, theme.summary));
  });
  detail.querySelector('[data-action="bridge-theme"]')?.addEventListener("click", () => {
    document.getElementById("intentInput").value = THEME_BRIDGE_INTENTS[theme.theme] || theme.summary;
    switchTab("bridge");
    document.getElementById("intentInput")?.focus();
    toast("Intent set — add an anchor track and generate");
  });
}

function showSegmentDetail(key, count, total) {
  activeSegment = key;
  activeTheme = null;
  document.querySelectorAll(".segment-chip").forEach(c => {
    c.classList.toggle("segment-chip--active", c.dataset.segment === key);
  });
  document.querySelectorAll(".theme-card").forEach(c => c.classList.remove("theme-card--active"));

  const pct = Math.round(100 * count / total);
  const label = themeLabel(key);
  const intent = SEGMENT_BRIDGE_INTENTS[key] || SEGMENT_BRIDGE_INTENTS.general;
  const detail = document.getElementById("themeDetail");
  detail.classList.remove("hidden");
  detail.innerHTML = `
    <div class="theme-detail__head">
      <div>
        <h3 class="theme-detail__title">${label}</h3>
        <p class="theme-detail__meta">${pct}% of corpus · ${count} reviews</p>
      </div>
      <button type="button" class="theme-detail__close" aria-label="Close">&times;</button>
    </div>
    <p class="theme-detail__summary">Users in this segment describe discovery differently — bridge sessions can target their specific friction.</p>
    <div class="chip-row chip-row--compact">
      <button type="button" class="chip" data-action="ask-segment">Ask about ${label}</button>
      <button type="button" class="chip" data-action="bridge-segment">Bridge for this segment</button>
    </div>`;

  detail.querySelector(".theme-detail__close")?.addEventListener("click", clearThemeDetail);
  detail.querySelector('[data-action="ask-segment"]')?.addEventListener("click", () => {
    const q = `What discovery challenges do ${label} users face?`;
    document.getElementById("questionInput").value = q;
    switchTab("ask");
    askAboutQuestion(q);
  });
  detail.querySelector('[data-action="bridge-segment"]')?.addEventListener("click", () => {
    document.getElementById("intentInput").value = intent;
    switchTab("bridge");
    document.getElementById("intentInput")?.focus();
    toast("Intent set for this segment — generate when ready");
  });
}

function clearThemeDetail() {
  activeTheme = null;
  activeSegment = null;
  document.getElementById("themeDetail")?.classList.add("hidden");
  document.querySelectorAll(".theme-card, .segment-chip").forEach(c => {
    c.classList.remove("theme-card--active", "segment-chip--active");
  });
}

function renderThemes(themes, targetId = "themes") {
  const el = document.getElementById(targetId);
  if (!el) return;
  el.innerHTML = themes.slice(0, 8).map(t => `
    <button type="button" class="theme-card" data-theme="${t.theme}" aria-pressed="false">
      <div class="theme-card__head">
        <span class="theme-card__name">${themeLabel(t.theme)}</span>
        <span class="theme-card__pct">${t.pct}%</span>
      </div>
      <div class="theme-card__bar"><div class="theme-card__fill" style="width:${Math.min(t.pct * 2.5, 100)}%"></div></div>
      <p class="theme-card__summary">${t.summary}</p>
    </button>
  `).join("");

  el.querySelectorAll(".theme-card").forEach(card => {
    card.addEventListener("click", () => {
      const theme = themes.find(t => t.theme === card.dataset.theme);
      if (!theme) return;
      if (activeTheme === theme.theme) {
        clearThemeDetail();
        return;
      }
      showThemeDetail(theme);
      document.getElementById("themeDetail")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  });
}

function renderHomeThemes(themes) {
  const el = document.getElementById("homeThemes");
  if (!el) return;
  const colors = [
    "linear-gradient(135deg,#1ed760,#169c46)",
    "linear-gradient(135deg,#509bf5,#8c67ab)",
    "linear-gradient(135deg,#f59b23,#e91429)",
    "linear-gradient(135deg,#450af5,#c4efd9)",
  ];
  el.innerHTML = themes.slice(0, 6).map((t, i) => `
    <article class="media-card" data-tab="insights">
      <div class="media-card__cover">
        <div class="cover-gradient" style="background:${colors[i % colors.length]}">${Math.round(t.pct)}%</div>
      </div>
      <p class="media-card__title">${t.theme.replace(/_/g, " ")}</p>
      <p class="media-card__desc">${t.summary.slice(0, 56)}…</p>
    </article>
  `).join("");
  el.querySelectorAll(".media-card").forEach(c => {
    c.addEventListener("click", () => switchTab("insights"));
  });
}

function renderSegments(segments) {
  const el = document.getElementById("segments");
  const total = Object.values(segments).reduce((a, b) => a + b, 0) || 1;
  el.innerHTML = Object.entries(segments)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([k, v]) => {
      const pct = Math.round(100 * v / total);
      return `
        <button type="button" class="segment-chip" data-segment="${k}" aria-pressed="false">
          <span style="min-width:140px;text-transform:capitalize">${themeLabel(k)}</span>
          <div class="segment-chip__bar-wrap"><div class="segment-chip__bar" style="width:${pct}%"></div></div>
          <span style="color:var(--text-subdued);font-size:13px">${pct}%</span>
        </button>`;
    }).join("");

  el.querySelectorAll(".segment-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const key = chip.dataset.segment;
      const count = segments[key] || 0;
      if (activeSegment === key) {
        clearThemeDetail();
        return;
      }
      showSegmentDetail(key, count, total);
      document.getElementById("themeDetail")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  });
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderAnswer(data) {
  const el = document.getElementById("answer");
  el.classList.remove("hidden");
  const answer = escapeHtml(data.answer || "").replace(/\n/g, "<br/>");
  const cites = (data.citations || []).filter(c => c.text);
  const citeHtml = cites.length
    ? `<details class="answer-box__sources">
        <summary>Source quotes (${cites.length})</summary>
        ${cites.map(c =>
          `<div class="citation"><span class="citation__text">"${escapeHtml(c.text)}"</span>${c.url ? ` <a href="${escapeHtml(c.url)}" target="_blank" rel="noopener">source</a>` : ""}</div>`
        ).join("")}
      </details>`
    : "";
  el.innerHTML = `
    <div class="answer-box__q">${escapeHtml(data.question)}</div>
    <p class="answer-box__body">${answer}</p>
    ${citeHtml}`;
}

async function askAboutQuestion(q) {
  const resp = await fetchJSON("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: q }),
  });
  renderAnswer(resp);
}

async function loadInsights() {
  const data = await fetchJSON("/api/insights");
  insightsCache = data;
  renderThemes(data.themes);
  renderHomeThemes(data.themes);
  renderSegments(data.segments);
  document.getElementById("statReviews").textContent = data.total_reviews;
  document.getElementById("statThemes").textContent = data.themes.length;
  const subtitle = document.getElementById("insightSubtitle");
  if (subtitle) {
    subtitle.textContent = `${data.total_reviews} reviews analyzed — click a theme or segment to explore`;
  }

  const btns = document.getElementById("canonicalBtns");
  btns.innerHTML = Object.entries(data.canonical_questions).map(([k, q]) =>
    `<button class="chip" data-key="${k}">${q.length > 42 ? q.slice(0, 42) + "…" : q}</button>`
  ).join("");
  btns.querySelectorAll(".chip").forEach(btn => {
    btn.addEventListener("click", async () => {
      const resp = await fetchJSON(`/api/ask/${btn.dataset.key}`);
      renderAnswer(resp);
      switchTab("ask");
    });
  });
}

document.getElementById("askBtn")?.addEventListener("click", async () => {
  const q = document.getElementById("questionInput").value.trim();
  if (!q) return;
  const resp = await fetchJSON("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: q }),
  });
  renderAnswer(resp);
});

function hideSearchResults() {
  document.getElementById("searchResults")?.classList.add("hidden");
}

function renderSearchResults(data) {
  const el = document.getElementById("searchResults");
  if (!el) return;
  const tracks = data.tracks || [];
  el.innerHTML = renderSearchResultsHtml(tracks, data.hint);
  el.classList.remove("hidden");
  bindSearchResultClicks(el, btn => {
    switchTab("bridge");
    document.getElementById("anchorInput").value = btn.dataset.url;
    previewAnchor();
    hideSearchResults();
    document.getElementById("globalSearch").value = "";
    toast("Anchor track set — add intent and generate bridge");
  });
}

async function searchTracks(q) {
  const data = await fetchJSON(`/api/search/tracks?q=${encodeURIComponent(q)}`);
  renderSearchResults(data);
}

let globalSearchTimer = null;

function runGlobalSearch(q) {
  if (!q) {
    hideSearchResults();
    return;
  }
  searchTracks(q).catch(err => toast("Search failed: " + err.message));
}

document.getElementById("globalSearch")?.addEventListener("input", e => {
  const q = e.target.value.trim();
  clearTimeout(globalSearchTimer);
  if (!q) {
    hideSearchResults();
    return;
  }
  globalSearchTimer = setTimeout(() => runGlobalSearch(q), 300);
});

document.getElementById("globalSearch")?.addEventListener("keydown", async e => {
  if (e.key !== "Enter") return;
  e.preventDefault();
  clearTimeout(globalSearchTimer);
  const q = e.target.value.trim();
  if (!q) return;
  if (q.startsWith("?")) {
    switchTab("ask");
    document.getElementById("questionInput").value = q.slice(1).trim();
    const resp = await fetchJSON("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q.slice(1).trim() }),
    });
    renderAnswer(resp);
    hideSearchResults();
    return;
  }
  runGlobalSearch(q);
});

document.addEventListener("click", e => {
  if (!e.target.closest(".topbar__search")) hideSearchResults();
  if (!e.target.closest(".anchor-search")) document.getElementById("anchorSearchResults")?.classList.add("hidden");
});

/* ── Bridge Sessions ── */
const GRADIENTS = [
  "linear-gradient(135deg,#1ed760,#169c46)",
  "linear-gradient(135deg,#509bf5,#1ed760)",
  "linear-gradient(135deg,#8c67ab,#509bf5)",
  "linear-gradient(135deg,#f59b23,#e91429)",
];

function trackThumbHtml(t, i) {
  const grad = GRADIENTS[i % GRADIENTS.length];
  if (t.album_art) {
    return `<div class="track-row__thumb"><img src="${t.album_art}" alt="" loading="lazy" onerror="this.parentElement.classList.add('track-row__thumb--fallback');this.parentElement.style.background='${grad}';this.replaceWith(document.createTextNode('♪'));" /></div>`;
  }
  return `<div class="track-row__thumb track-row__thumb--fallback" style="background:${grad}">♪</div>`;
}

function updatePlayer(track, idx) {
  const bar = document.getElementById("previewBar");
  if (!track) {
    bar?.classList.add("hidden");
    return;
  }
  bar?.classList.remove("hidden");
  document.getElementById("playerTitle").textContent = track.name;
  document.getElementById("playerArtist").textContent = track.artist;
  document.getElementById("playerStep").textContent = `Track ${idx + 1} of ${currentTracks.length}`;
  const artEl = document.getElementById("playerArt");
  if (track.album_art) {
    artEl.style.background = "";
    artEl.style.backgroundImage = `url("${track.album_art}")`;
    artEl.style.backgroundSize = "cover";
    artEl.style.backgroundPosition = "center";
  } else {
    artEl.style.backgroundImage = "";
    artEl.style.background = GRADIENTS[idx % GRADIENTS.length];
  }
}

function renderTracks(tracks) {
  currentTracks = tracks;
  document.getElementById("tracks").innerHTML = tracks.map((t, i) => `
    <div class="track-row" data-idx="${i}" role="button" tabindex="0">
      <span class="track-row__idx">${t.position}</span>
      <span class="track-row__play-sm">▶</span>
      <div class="track-row__main">
        ${trackThumbHtml(t, i)}
        <div>
          <div class="track-row__title">${t.name}</div>
          <div class="track-row__artist">${t.artist}</div>
        </div>
      </div>
      <span class="track-row__novelty">${Math.round(t.novelty_score * 100)}% new</span>
      <span></span>
      <a class="track-row__link" href="${t.spotify_url}" target="_blank" rel="noopener" aria-label="Open in Spotify">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02z"/></svg>
      </a>
    </div>
    <p class="track-row__bridge-note">${t.explanation}</p>
  `).join("");

  document.querySelectorAll(".track-row").forEach(row => {
    row.addEventListener("click", e => {
      if (e.target.closest("a")) return;
      const idx = parseInt(row.dataset.idx, 10);
      currentTrackIdx = idx;
      updatePlayer(currentTracks[idx], idx);
    });
  });

  if (tracks.length) updatePlayer(tracks[0], 0);
}

document.getElementById("comfortLoopCta")?.addEventListener("click", () => {
  switchTab("bridge");
  document.getElementById("intentInput").value = CONTEXT_INTENTS[0].text;
  document.getElementById("anchorInput")?.focus();
});

document.getElementById("startBridgeBtn")?.addEventListener("click", () => {
  switchTab("bridge");
  document.getElementById("intentInput")?.focus();
});

document.getElementById("buildBtn")?.addEventListener("click", async () => {
  clearBridgeError();
  const intent = document.getElementById("intentInput").value.trim();
  if (!intent) return toast("Enter your intent first");
  const anchor = document.getElementById("anchorInput").value.trim() || null;
  setBridgeLoading(true);

  try {
    const session = await fetchJSON("/api/bridge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intent, anchor, demo: !isConnected }),
    });

    session._shareAnchor = session.anchor_id || parseTrackId(anchor || "");
    displaySession(session);
    toast(`Bridge ready — ${session.tracks.length} tracks`);
  } catch (e) {
    showBridgeError(e.message);
    if (e.code === "auth_required") switchTab("bridge");
  } finally {
    setBridgeLoading(false);
  }
});

document.getElementById("shareBridgeBtn")?.addEventListener("click", async () => {
  if (!lastSession) return;
  const url = buildShareUrl(lastSession);
  try {
    await navigator.clipboard.writeText(url);
    toast("Share link copied!");
  } catch {
    prompt("Copy this link:", url);
  }
});

document.getElementById("savePlaylistBtn")?.addEventListener("click", async () => {
  if (!lastSession) return;
  clearBridgeError();
  toast("Saving playlist to Spotify…");
  try {
    const result = await fetchJSON("/api/bridge/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        track_ids: lastSession.tracks.map(t => t.track_id),
        anchor_track: lastSession.anchor_track,
        intent: lastSession.intent,
      }),
    });
    toast("Playlist saved!");
    if (result.playlist_url) window.open(result.playlist_url, "_blank");
  } catch (e) {
    showBridgeError(e.message);
  }
});

document.getElementById("playerOpen")?.addEventListener("click", () => {
  if (currentTracks.length && currentTracks[currentTrackIdx]?.spotify_url) {
    window.open(currentTracks[currentTrackIdx].spotify_url, "_blank");
  } else {
    switchTab("bridge");
    toast("Generate a bridge session first");
  }
});

async function boot() {
  initExampleChips();
  await refreshAuthUI().catch(() => {});
  await tryLoadSharedBridge(INITIAL_HASH.params);
  await loadInsights().catch(() => {});
}

boot().catch(e => toast("Error: " + e.message));
