const API = window.API_BASE || "";

async function fetchJSON(path, opts) {
  const r = await fetch(`${API}${path}`, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function setStatus(msg) {
  document.getElementById("status").textContent = msg;
}

function renderThemes(themes) {
  const el = document.getElementById("themes");
  el.innerHTML = themes.slice(0, 8).map(t => `
    <div class="theme-bar">
      <div class="theme-bar__label"><span>${t.theme.replace(/_/g, " ")}</span><span>${t.pct}%</span></div>
      <div class="theme-bar__track"><div class="theme-bar__fill" style="width:${Math.min(t.pct * 2, 100)}%"></div></div>
      <p class="hint">${t.summary}</p>
    </div>
  `).join("");
}

function renderSegments(segments) {
  const el = document.getElementById("segments");
  const total = Object.values(segments).reduce((a, b) => a + b, 0) || 1;
  el.innerHTML = Object.entries(segments)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `
      <div class="segment-row">
        <span>${k.replace(/_/g, " ")}</span>
        <span>${v} (${Math.round(100 * v / total)}%)</span>
      </div>
    `).join("");
}

function renderAnswer(data) {
  const el = document.getElementById("answer");
  const cites = (data.citations || []).map(c =>
    `<div class="citation"><strong>[${c.id}]</strong> ${c.text}${c.url ? ` — <a href="${c.url}" target="_blank">source</a>` : ""}</div>`
  ).join("");
  el.innerHTML = `<p><strong>Q:</strong> ${data.question}</p><p>${data.answer}</p>${cites}`;
}

async function loadInsights() {
  setStatus("Loading insights...");
  const data = await fetchJSON("/api/insights");
  renderThemes(data.themes);
  renderSegments(data.segments);
  setStatus(`${data.total_reviews} reviews indexed`);

  const btns = document.getElementById("canonicalBtns");
  btns.innerHTML = Object.entries(data.canonical_questions).map(([k, q]) =>
    `<button class="chip" data-key="${k}">${q.slice(0, 48)}…</button>`
  ).join("");
  btns.querySelectorAll(".chip").forEach(btn => {
    btn.addEventListener("click", async () => {
      const resp = await fetchJSON(`/api/ask/${btn.dataset.key}`);
      renderAnswer(resp);
    });
  });
}

document.getElementById("runIngest").addEventListener("click", async () => {
  setStatus("Running ingest + classification...");
  const data = await fetchJSON("/api/ingest", { method: "POST" });
  setStatus(`Indexed ${data.indexed} reviews`);
  await loadInsights();
});

document.getElementById("loadInsights").addEventListener("click", loadInsights);

document.getElementById("askBtn").addEventListener("click", async () => {
  const q = document.getElementById("questionInput").value.trim();
  if (!q) return;
  const resp = await fetchJSON("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: q }),
  });
  renderAnswer(resp);
});

loadInsights().catch(e => setStatus("Error: " + e.message));
