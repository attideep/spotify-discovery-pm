const API = window.API_BASE || "";
let accessToken = new URLSearchParams(location.search).get("token") || "demo";
let currentTracks = [];
let currentTrackIdx = 0;

async function fetchJSON(path, opts) {
  const r = await fetch(`${API}${path}`, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function toast(msg) {
  const el = document.getElementById("statusToast");
  el.textContent = msg;
  el.classList.add("visible");
  setTimeout(() => el.classList.remove("visible"), 2800);
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

document.querySelectorAll(".nav-item, .sidebar__list-item, .media-card, [data-tab]").forEach(el => {
  el.addEventListener("click", e => {
    const tab = el.dataset.tab;
    if (tab) {
      e.preventDefault();
      switchTab(tab);
    }
  });
});

const hash = location.hash.replace("#", "") || (location.pathname.includes("bridge") ? "bridge" : "home");
if (["home", "bridge", "insights", "ask"].includes(hash)) switchTab(hash);

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
  toast("Loading insights…");
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
  toast(`${data.total_reviews} reviews indexed`);
}

document.getElementById("runIngest")?.addEventListener("click", async () => {
  toast("Running analysis…");
  const data = await fetchJSON("/api/ingest", { method: "POST" });
  toast(`Indexed ${data.indexed} reviews`);
  await loadInsights();
});

document.getElementById("loadInsights")?.addEventListener("click", loadInsights);

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
  "linear-gradient(135deg,#450af5,#c4efd9)",
  "linear-gradient(135deg,#1ed760,#509bf5)",
  "linear-gradient(135deg,#e91429,#f59b23)",
  "linear-gradient(135deg,#169c46,#121212)",
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
      <a class="track-row__link" href="${t.spotify_url}" target="_blank" aria-label="Open in Spotify">
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

document.getElementById("demoBtn")?.addEventListener("click", async () => {
  const data = await fetchJSON("/mvp/demo-token");
  accessToken = data.access_token;
  toast("Demo mode — generate a bridge below");
});

document.getElementById("buildBtn")?.addEventListener("click", async () => {
  const intent = document.getElementById("intentInput").value.trim();
  if (!intent) return toast("Enter your intent first");
  const anchor = document.getElementById("anchorInput").value.trim() || null;
  toast("Building your bridge…");

  const session = await fetchJSON("/api/bridge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ intent, anchor_track_id: anchor, access_token: accessToken }),
  });

  document.getElementById("sessionBlock").classList.remove("hidden");
  document.getElementById("sessionTitle").textContent = `Bridge from ${session.anchor_track}`;
  document.getElementById("sessionSummary").textContent = session.session_summary;
  renderTracks(session.tracks);
  toast("Bridge session ready — 8 tracks");
});

document.getElementById("playerPlay")?.addEventListener("click", () => {
  if (currentTracks.length && currentTracks[currentTrackIdx]?.spotify_url) {
    window.open(currentTracks[currentTrackIdx].spotify_url, "_blank");
  } else {
    switchTab("bridge");
    toast("Generate a bridge session to play");
  }
});

if (accessToken && accessToken !== "demo") {
  const login = document.getElementById("spotifyLogin");
  login.textContent = "Connected";
  login.classList.add("btn-spotify--ghost");
  login.removeAttribute("href");
}

loadInsights().catch(e => toast("Error: " + e.message));
