/* Customer app (/app) — auth, saved bridges, search polish, extras */

(function () {
  if (window.APP_VARIANT !== "bridge-only") return;

  const MOODS = [
    { emoji: "☀️", label: "Morning energy", intent: "Morning energy — gradual lift from my anchor" },
    { emoji: "🚇", label: "Commute", intent: "Commute — steady energy, gradual novelty from my anchor" },
    { emoji: "🎯", label: "Focus", intent: "Focus work — smooth textures, low distraction" },
    { emoji: "🌙", label: "Wind down", intent: "Wind down — calmer tracks toward the end" },
    { emoji: "✨", label: "Surprise me", intent: "Controlled surprise — safe steps toward something new" },
  ];

  let authUser = null;
  let sessionSaved = false;

  function $(id) {
    return document.getElementById(id);
  }

  function showSearchLoading(el, message = "Searching catalog…") {
    if (!el) return;
    el.innerHTML = `<div class="search-results__loading"><span class="search-results__spinner"></span>${message}</div>`;
    el.classList.remove("hidden");
  }

  function formatBridgeDate(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return "";
      return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    } catch {
      return "";
    }
  }

  let bound = false;

  window.CustomerApp = {
    showSearchLoading,

    async refreshAuth() {
      try {
        const data = await fetch("/api/auth/user/status", { credentials: "include" }).then(r => r.json());
        authUser = data.user || null;
        this._renderAuthUI(data);
        if (authUser) await this.loadSavedBridges();
        else this._renderLibraryHint();
        return data;
      } catch {
        authUser = null;
        this._renderAuthUI({ logged_in: false, user: null });
        this._renderLibraryHint();
      }
    },

    _renderAuthUI(status) {
      const signedOut = $("authSignedOut");
      const signedIn = $("authSignedIn");
      const nameEl = $("authUserName");
      const saveBtn = $("saveBridgeBtn");
      const libraryPanel = $("libraryPanel");
      const libraryHint = $("libraryHint");
      const libraryNav = $("libraryNavBtn");
      if (!signedOut || !signedIn) return;

      if (status.logged_in && status.user) {
        signedOut.classList.add("hidden");
        signedIn.classList.remove("hidden");
        libraryHint?.classList.add("hidden");
        libraryPanel?.classList.remove("hidden");
        libraryNav?.classList.remove("hidden");
        if (nameEl) nameEl.textContent = status.user.display_name || status.user.email;
        if (saveBtn) saveBtn.classList.remove("hidden");
      } else {
        signedOut.classList.remove("hidden");
        signedIn.classList.add("hidden");
        libraryPanel?.classList.add("hidden");
        libraryHint?.classList.remove("hidden");
        libraryNav?.classList.add("hidden");
        if (saveBtn) saveBtn.classList.add("hidden");
        $("savedBridges")?.replaceChildren();
      }
    },

    _renderLibraryHint() {
      const hint = $("libraryHint");
      if (!hint || authUser) return;
      hint.classList.remove("hidden");
    },

    scrollToLibrary() {
      $("libraryPanel")?.scrollIntoView({ behavior: "smooth", block: "start" });
    },

    resetSaveButton() {
      sessionSaved = false;
      const saveBtn = $("saveBridgeBtn");
      if (!saveBtn) return;
      saveBtn.textContent = "Save bridge";
      saveBtn.classList.remove("btn-spotify--saved");
      saveBtn.disabled = false;
    },

    markSessionSaved() {
      sessionSaved = true;
      const saveBtn = $("saveBridgeBtn");
      if (!saveBtn) return;
      saveBtn.textContent = "Saved ✓";
      saveBtn.classList.add("btn-spotify--saved");
      saveBtn.disabled = true;
    },

    onSessionDisplay() {
      this.resetSaveButton();
    },

    openAuth(mode = "login") {
      $("authModal")?.classList.remove("hidden");
      $("authModalTitle").textContent = mode === "signup" ? "Create account" : "Sign in";
      $("authSubmitBtn").textContent = mode === "signup" ? "Sign up" : "Sign in";
      $("authSubmitBtn").dataset.mode = mode;
      $("authError")?.classList.add("hidden");
      $("authNameField")?.classList.toggle("hidden", mode !== "signup");
    },

    closeAuth() {
      $("authModal")?.classList.add("hidden");
    },

    async submitAuth() {
      const mode = $("authSubmitBtn")?.dataset.mode || "login";
      const email = $("authEmail")?.value.trim();
      const password = $("authPassword")?.value;
      const display_name = $("authName")?.value.trim() || "";
      const errEl = $("authError");
      if (!email || !password) {
        if (errEl) {
          errEl.textContent = "Email and password required.";
          errEl.classList.remove("hidden");
        }
        return;
      }
      const path = mode === "signup" ? "/api/auth/signup" : "/api/auth/login";
      try {
        const r = await fetch(path, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password, display_name }),
        });
        const raw = await r.text();
        let data = {};
        try {
          data = raw ? JSON.parse(raw) : {};
        } catch {
          const snippet = raw.replace(/\s+/g, " ").trim().slice(0, 80);
          throw new Error(
            r.ok
              ? "Unexpected server response."
              : snippet || `Sign-in failed (${r.status}). Please try again.`
          );
        }
        if (!r.ok) throw new Error(data.detail || data.error || "Auth failed");
        this.closeAuth();
        await this.refreshAuth();
        window.toast?.(mode === "signup" ? "Welcome! Your library is ready." : "Signed in — your library is below.");
        if (authUser) setTimeout(() => this.scrollToLibrary(), 400);
      } catch (e) {
        if (errEl) {
          errEl.textContent = e.message;
          errEl.classList.remove("hidden");
        }
      }
    },

    async logout() {
      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
      authUser = null;
      sessionSaved = false;
      await this.refreshAuth();
      window.toast?.("Signed out");
    },

    async saveCurrentBridge() {
      if (!window.lastSession) return window.toast?.("Generate a bridge first");
      if (!authUser) return this.openAuth("login");
      if (sessionSaved) return window.toast?.("Already in your library");
      const saveBtn = $("saveBridgeBtn");
      if (saveBtn) saveBtn.disabled = true;
      try {
        const r = await fetch("/api/bridges/save", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(window.lastSession),
        });
        const raw = await r.text();
        let data = {};
        try {
          data = raw ? JSON.parse(raw) : {};
        } catch {
          throw new Error("Could not save bridge — try again.");
        }
        if (!r.ok) throw new Error(data.detail || data.error || "Save failed");
        this.markSessionSaved();
        window.toast?.("Saved to your library");
        await this.loadSavedBridges();
        setTimeout(() => this.scrollToLibrary(), 300);
      } catch (e) {
        if (saveBtn) saveBtn.disabled = false;
        window.toast?.(e.message);
      }
    },

    async deleteSavedBridge(id, cardEl) {
      if (!authUser || !id) return;
      cardEl?.classList.add("saved-bridge-card--deleting");
      try {
        const r = await fetch(`/api/bridges/saved/${id}`, {
          method: "DELETE",
          credentials: "include",
        });
        if (!r.ok) {
          const data = await r.json().catch(() => ({}));
          throw new Error(data.detail || "Could not delete");
        }
        window.toast?.("Removed from library");
        await this.loadSavedBridges();
      } catch (e) {
        cardEl?.classList.remove("saved-bridge-card--deleting");
        window.toast?.(e.message);
      }
    },

    async loadSavedBridges() {
      const el = $("savedBridges");
      const panel = $("libraryPanel");
      const countEl = $("libraryCount");
      if (!el || !authUser) {
        panel?.classList.add("hidden");
        return;
      }
      panel?.classList.remove("hidden");
      el.innerHTML = `<div class="saved-bridges__loading"><span class="search-results__spinner"></span>Loading library…</div>`;
      try {
        const data = await fetch("/api/bridges/saved", { credentials: "include" }).then(r => r.json());
        const bridges = data.bridges || [];
        if (countEl) countEl.textContent = bridges.length ? String(bridges.length) : "";
        if (!bridges.length) {
          el.innerHTML = `
            <div class="library-empty">
              <p class="library-empty__title">No saved bridges yet</p>
              <p class="library-empty__sub">Generate a bridge, then tap <strong>Save bridge</strong> to keep it here.</p>
            </div>`;
          return;
        }
        el.innerHTML = `
          <div class="saved-bridges__scroll">
            ${bridges.map(b => {
              const trackCount = (b.tracks || []).length;
              const date = formatBridgeDate(b.created_at);
              return `
              <div class="saved-bridge-card" data-id="${escapeHtml(b.id)}">
                <button type="button" class="saved-bridge-card__open" data-id="${escapeHtml(b.id)}">
                  <span class="saved-bridge-card__title">${escapeHtml(b.title || b.anchor_track)}</span>
                  <span class="saved-bridge-card__meta">${escapeHtml((b.intent || "").slice(0, 56))}${(b.intent || "").length > 56 ? "…" : ""}</span>
                  <span class="saved-bridge-card__foot">${trackCount ? `${trackCount} tracks` : "8 tracks"}${date ? ` · ${date}` : ""}</span>
                </button>
                <button type="button" class="saved-bridge-card__delete" data-delete="${escapeHtml(b.id)}" aria-label="Delete saved bridge">×</button>
              </div>`;
            }).join("")}
          </div>`;
        el.querySelectorAll(".saved-bridge-card__open").forEach(btn => {
          btn.addEventListener("click", () => this.openSavedBridge(btn.dataset.id));
        });
        el.querySelectorAll("[data-delete]").forEach(btn => {
          btn.addEventListener("click", e => {
            e.stopPropagation();
            this.deleteSavedBridge(btn.dataset.delete, btn.closest(".saved-bridge-card"));
          });
        });
      } catch {
        el.innerHTML = `
          <div class="library-empty">
            <p class="library-empty__title">Could not load library</p>
            <p class="library-empty__sub">Check your connection and try again.</p>
          </div>`;
      }
    },

    async openSavedBridge(id) {
      if (!id) return;
      try {
        const bridge = await fetch(`/api/bridges/saved/${id}`, { credentials: "include" }).then(r => r.json());
        const session = {
          anchor_track: bridge.anchor_track,
          anchor_id: bridge.anchor_id,
          intent: bridge.intent,
          session_summary: bridge.session_summary,
          mode: "demo",
          tracks: bridge.tracks,
        };
        window.displaySession?.(session);
        this.markSessionSaved();
        window.toast?.("Bridge loaded from library");
        $("sessionBlock")?.scrollIntoView({ behavior: "smooth", block: "start" });
      } catch {
        window.toast?.("Could not open saved bridge");
      }
    },

    renderMoodChips() {
      const el = $("moodChips");
      if (!el) return;
      el.innerHTML = MOODS.map(m =>
        `<button type="button" class="chip chip--mood" data-intent="${escapeHtml(m.intent)}">${m.emoji} ${m.label}</button>`
      ).join("");
      el.querySelectorAll(".chip--mood").forEach(btn => {
        btn.addEventListener("click", () => {
          const input = $("intentInput");
          if (input) input.value = btn.dataset.intent;
          input?.focus();
        });
      });
    },

    renderContinueCard() {
      const raw = localStorage.getItem("bridge_last_session");
      if (!raw) return;
      try {
        const session = JSON.parse(raw);
        const el = $("continueBridge");
        if (!el || !session.tracks?.length) return;
        el.classList.remove("hidden");
        el.querySelector("[data-continue]")?.addEventListener("click", () => {
          window.displaySession?.(session);
          window.toast?.("Picked up where you left off");
        });
        const title = $("continueBridgeTitle");
        if (title) title.textContent = `Continue: ${session.anchor_track}`;
      } catch { /* ignore */ }
    },

    persistLastSession(session) {
      try {
        localStorage.setItem("bridge_last_session", JSON.stringify({
          anchor_track: session.anchor_track,
          anchor_id: session.anchor_id,
          intent: session.intent,
          session_summary: session.session_summary,
          mode: session.mode,
          tracks: session.tracks,
        }));
      } catch { /* ignore */ }
    },

    bind() {
      if (bound) return;
      bound = true;
      $("authLoginBtn")?.addEventListener("click", () => this.openAuth("login"));
      $("authSignupBtn")?.addEventListener("click", () => this.openAuth("signup"));
      $("libraryHintSignIn")?.addEventListener("click", () => this.openAuth("login"));
      $("libraryNavBtn")?.addEventListener("click", () => this.scrollToLibrary());
      $("authSubmitBtn")?.addEventListener("click", () => this.submitAuth());
      $("authLogoutBtn")?.addEventListener("click", () => this.logout());
      $("saveBridgeBtn")?.addEventListener("click", () => this.saveCurrentBridge());
      document.querySelectorAll("[data-close-auth]").forEach(btn => {
        btn.addEventListener("click", () => this.closeAuth());
      });

      const params = new URLSearchParams(location.search);
      const authErr = params.get("auth_error");
      if (authErr) {
        window.toast?.(decodeURIComponent(authErr));
        history.replaceState(null, "", "/app");
      }

      this.renderMoodChips();
      this.renderContinueCard();
      this.refreshAuth();

      const origDisplay = window.displaySession;
      if (origDisplay) {
        window.displaySession = session => {
          origDisplay(session);
          this.persistLastSession(session);
          this.onSessionDisplay(session);
          if (authUser) this.loadSavedBridges();
        };
      }
    },
  };

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  document.addEventListener("DOMContentLoaded", () => window.CustomerApp?.bind());
  if (document.readyState !== "loading") window.CustomerApp?.bind();
})();
