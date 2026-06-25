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
  const qs = new URLSearchParams({ intent: session.intent });
  const anchorId = session._shareAnchor || parseTrackId(document.getElementById("anchorInput")?.value || "");
  if (anchorId) qs.set("anchor", anchorId);
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

async function tryLoadSharedBridge() {
  const { tab, params } = parseHashState();
  const hasShare = params.get("share") || params.get("intent") || params.get("i");
  if (!hasShare) return;

  switchTab("bridge");
  clearBridgeError();
  toast("Loading shared bridge…");

  if (params.get("share")) {
    try {
      displaySession(decodeShare(params.get("share")));
      toast("Shared bridge session loaded");
      return;
    } catch {
      /* fall through to intent+anchor if present */
    }
  }

  const intent = params.get("intent") || params.get("i");
  if (!intent) {
    showBridgeError("Could not load shared bridge — link may be truncated. Generate a new one and copy again.");
    return;
  }

  const anchorId = params.get("anchor") || params.get("a");
  const anchor = anchorId ? `https://open.spotify.com/track/${anchorId}` : null;

  try {
    const session = await fetchJSON("/api/bridge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intent, anchor, demo: !isConnected }),
    });
    session._shareAnchor = anchorId || "";
    document.getElementById("intentInput").value = intent;
    if (anchor) {
      document.getElementById("anchorInput").value = anchor;
      previewAnchor();
    }
    displaySession(session);
    toast("Shared bridge session loaded");
  } catch (e) {
    showBridgeError(e.message || "Could not load shared bridge.");
  }
}

function displaySession(session) {
  lastSession = session;
  document.getElementById("sessionBlock").classList.remove("hidden");
  document.getElementById("sessionTitle").textContent = `Bridge from ${session.anchor_track}`;
  document.getElementById("sessionSummary").textContent = session.session_summary;
  document.getElementById("sessionMode").textContent = session.mode === "live" ? "Live beta" : "Free";
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
    const msg = data.error || data.detail || r.statusText;
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

/* ── Tab navigation ── */
const TAB_ACCENTS = { home: "home", bridge: "bridge", insights: "insights", ask: "insights" };

function switchTab(tab) {
  document.querySelectorAll(".nav-item").forEach(n => {
    n.classList.toggle("active", n.dataset.tab === tab);
  });
  document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
  const panel = document.getElementById(`panel-${tab}`);
  if (panel) panel.classList.add("active");
  document.getElementById("mainArea").dataset.accent = TAB_ACCENTS[tab] || "home";
  history.replaceState(null, "", tab === "home" ? "/" : `/#${tab}`);
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
}

document.querySelectorAll(".nav-item, .sidebar__list-item, .media-card, [data-tab]").forEach(el => {
  el.addEventListener("click", e => {
    const tab = el.dataset.tab;
    if (tab) {
      e.preventDefault();
      switchTab(tab);
    }
  });
});

const { tab: initialTab, params: hashParams } = parseHashState();
if (["home", "bridge", "insights", "ask"].includes(initialTab)) switchTab(initialTab);

const urlError = hashParams.get("error");
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

/* ── Anchor preview ── */
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

document.getElementById("anchorInput")?.addEventListener("change", previewAnchor);
document.getElementById("anchorInput")?.addEventListener("blur", previewAnchor);

/* ── Insights ── */
function renderThemes(themes, targetId = "themes") {
  const el = document.getElementById(targetId);
  if (!el) return;
  el.innerHTML = themes.slice(0, 8).map(t => `
    <div class="theme-card">
      <div class="theme-card__head">
        <span class="theme-card__name">${t.theme.replace(/_/g, " ")}</span>
        <span class="theme-card__pct">${t.pct}%</span>
      </div>
      <div class="theme-card__bar"><div class="theme-card__fill" style="width:${Math.min(t.pct * 2.5, 100)}%"></div></div>
      <p class="theme-card__summary">${t.summary}</p>
    </div>
  `).join("");
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
        <div class="segment-chip">
          <span style="min-width:140px;text-transform:capitalize">${k.replace(/_/g, " ")}</span>
          <div class="segment-chip__bar-wrap"><div class="segment-chip__bar" style="width:${pct}%"></div></div>
          <span style="color:var(--text-subdued);font-size:13px">${pct}%</span>
        </div>`;
    }).join("");
}

function renderAnswer(data) {
  const el = document.getElementById("answer");
  el.classList.remove("hidden");
  const cites = (data.citations || []).map(c =>
    `<div class="citation"><strong>[${c.id}]</strong> ${c.text}${c.url ? ` — <a href="${c.url}" target="_blank" style="color:var(--green)">source</a>` : ""}</div>`
  ).join("");
  el.innerHTML = `<div class="answer-box__q">${data.question}</div><p>${data.answer}</p>${cites}`;
}

async function loadInsights() {
  const data = await fetchJSON("/api/insights");
  renderThemes(data.themes);
  renderHomeThemes(data.themes);
  renderSegments(data.segments);
  document.getElementById("statReviews").textContent = data.total_reviews;
  document.getElementById("statThemes").textContent = data.themes.length;

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

document.getElementById("runIngest")?.addEventListener("click", async () => {
  toast("Running analysis…");
  const data = await fetchJSON("/api/ingest", { method: "POST" });
  toast(`Indexed ${data.indexed} reviews`);
  await loadInsights();
});

document.getElementById("loadInsights")?.addEventListener("click", () => loadInsights().then(() => toast("Refreshed")));

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

document.getElementById("globalSearch")?.addEventListener("keydown", async e => {
  if (e.key !== "Enter") return;
  const q = e.target.value.trim();
  if (!q) return;
  switchTab("ask");
  document.getElementById("questionInput").value = q;
  const resp = await fetchJSON("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: q }),
  });
  renderAnswer(resp);
});

/* ── Bridge Sessions ── */
const GRADIENTS = [
  "linear-gradient(135deg,#1ed760,#169c46)",
  "linear-gradient(135deg,#509bf5,#1ed760)",
  "linear-gradient(135deg,#8c67ab,#509bf5)",
  "linear-gradient(135deg,#f59b23,#e91429)",
];

function updatePlayer(track, idx) {
  if (!track) return;
  document.getElementById("playerTitle").textContent = track.name;
  document.getElementById("playerArtist").textContent = track.artist;
  document.getElementById("playerArt").style.background = GRADIENTS[idx % GRADIENTS.length];
  const mins = Math.floor((idx + 1) * 3.75);
  document.getElementById("playerTime").textContent = `0:${String(mins).padStart(2, "0")}`;
  document.getElementById("playerProgress").style.width = `${((idx + 1) / 8) * 100}%`;
}

function renderTracks(tracks) {
  currentTracks = tracks;
  document.getElementById("tracks").innerHTML = tracks.map((t, i) => `
    <div class="track-row" data-idx="${i}" role="button" tabindex="0">
      <span class="track-row__idx">${t.position}</span>
      <span class="track-row__play-sm">▶</span>
      <div class="track-row__main">
        <div class="track-row__thumb" style="background:${GRADIENTS[i % GRADIENTS.length]}">♪</div>
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

document.getElementById("startBridgeBtn")?.addEventListener("click", () => {
  switchTab("bridge");
  document.getElementById("intentInput")?.focus();
});

document.getElementById("buildBtn")?.addEventListener("click", async () => {
  clearBridgeError();
  const intent = document.getElementById("intentInput").value.trim();
  if (!intent) return toast("Enter your intent first");
  const anchor = document.getElementById("anchorInput").value.trim() || null;
  toast("Building your bridge…");

  try {
    const session = await fetchJSON("/api/bridge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intent, anchor, demo: !isConnected }),
    });

    session._shareAnchor = parseTrackId(anchor || "");
    displaySession(session);
    toast(`Bridge ready — ${session.tracks.length} tracks`);
  } catch (e) {
    showBridgeError(e.message);
    if (e.code === "auth_required") switchTab("bridge");
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

document.getElementById("playerPlay")?.addEventListener("click", () => {
  if (currentTracks.length && currentTracks[currentTrackIdx]?.spotify_url) {
    window.open(currentTracks[currentTrackIdx].spotify_url, "_blank");
  } else {
    switchTab("bridge");
    toast("Generate a bridge session first");
  }
});

async function boot() {
  initExampleChips();
  await refreshAuthUI();
  await loadInsights();
  await tryLoadSharedBridge();
}

boot().catch(e => toast("Error: " + e.message));
