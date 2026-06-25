const API = window.API_BASE || "";
let accessToken = new URLSearchParams(location.search).get("token") || "demo";

async function fetchJSON(path, opts) {
  const r = await fetch(`${API}${path}`, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

document.getElementById("demoBtn").addEventListener("click", async () => {
  const data = await fetchJSON("/mvp/demo-token");
  accessToken = data.access_token;
  alert("Demo mode enabled — generate a bridge session below.");
});

document.getElementById("buildBtn").addEventListener("click", async () => {
  const intent = document.getElementById("intentInput").value.trim();
  if (!intent) return alert("Enter your intent");
  const anchor = document.getElementById("anchorInput").value.trim() || null;

  const session = await fetchJSON("/api/bridge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ intent, anchor_track_id: anchor, access_token: accessToken }),
  });

  document.getElementById("session").classList.remove("hidden");
  document.getElementById("sessionTitle").textContent = `Bridge from: ${session.anchor_track}`;
  document.getElementById("sessionSummary").textContent = session.session_summary;

  document.getElementById("tracks").innerHTML = session.tracks.map(t => `
    <div class="track">
      <div class="track__num">${t.position}</div>
      <div>
        <strong>${t.name}</strong>
        <div class="track__meta">${t.artist} · novelty ${t.novelty_score}</div>
        <p>${t.explanation}</p>
      </div>
      <a href="${t.spotify_url}" target="_blank">Open</a>
    </div>
  `).join("");
});

if (accessToken && accessToken !== "demo") {
  document.getElementById("spotifyLogin").textContent = "Spotify connected";
}
