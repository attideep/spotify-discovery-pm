/** Keyboard shortcuts + bridge extras */
(function () {
  const HISTORY_KEY = "bridge_history_v1";

  window.BridgeExtras = {
    saveHistory(session) {
      try {
        const list = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
        list.unshift({
          at: Date.now(),
          anchor: session.anchor_track,
          intent: session.intent,
          url: window.buildShareUrl?.(session),
        });
        localStorage.setItem(HISTORY_KEY, JSON.stringify(list.slice(0, 12)));
      } catch { /* ignore */ }
    },

    renderStats(session) {
      const el = document.getElementById("bridgeStats");
      if (!el || !session?.tracks?.length) return;
      const scores = session.tracks.map(t => t.novelty_score || 0);
      const min = Math.min(...scores);
      const max = Math.max(...scores);
      const artists = new Set(session.tracks.map(t => (t.artist || "").split(",")[0].trim()).filter(Boolean));
      el.classList.remove("hidden");
      el.innerHTML = `
        <div class="bridge-stats__grid">
          <div class="bridge-stats__item"><span class="bridge-stats__val">${artists.size}</span><span class="bridge-stats__label">artists</span></div>
          <div class="bridge-stats__item"><span class="bridge-stats__val">${Math.round(min * 100)}–${Math.round(max * 100)}%</span><span class="bridge-stats__label">novelty arc</span></div>
          <div class="bridge-stats__item"><span class="bridge-stats__val">~${session.tracks.length * 4}m</span><span class="bridge-stats__label">listen time</span></div>
        </div>`;
    },

    async surpriseMe() {
      const anchors = window.EXAMPLE_ANCHORS || [];
      const intents = window.CONTEXT_INTENTS || [];
      if (!anchors.length) return;
      const a = anchors[Math.floor(Math.random() * anchors.length)];
      const c = intents[Math.floor(Math.random() * intents.length)];
      document.getElementById("anchorInput").value = a.url;
      document.getElementById("intentInput").value = c.text;
      await window.previewAnchor?.();
      window.toast?.("Surprise bridge — hit Generate!");
    },

    toggleTheatre() {
      document.body.classList.toggle("theatre-mode");
    },

    bindShortcuts() {
      document.addEventListener("keydown", e => {
        if (e.target.matches("input, textarea")) return;
        if (e.key === " ") {
          e.preventDefault();
          window.BridgePlayer?.togglePlay();
        } else if (e.key === "ArrowRight") {
          document.getElementById("playerNext")?.click();
        } else if (e.key === "ArrowLeft") {
          document.getElementById("playerPrev")?.click();
        } else if (e.key === "?") {
          document.getElementById("shortcutsModal")?.classList.toggle("hidden");
        }
      });
    },
  };
})();
