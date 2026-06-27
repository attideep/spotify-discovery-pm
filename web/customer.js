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

  function $(id) {
    return document.getElementById(id);
  }

  function showSearchLoading(el, message = "Searching catalog…") {
    if (!el) return;
    el.innerHTML = `<div class="search-results__loading"><span class="search-results__spinner"></span>${message}</div>`;
    el.classList.remove("hidden");
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
        return data;
      } catch {
        this._renderAuthUI({ logged_in: false, user: null });
      }
    },

    _renderAuthUI(status) {
      const signedOut = $("authSignedOut");
      const signedIn = $("authSignedIn");
      const nameEl = $("authUserName");
      const saveBtn = $("saveBridgeBtn");
      if (!signedOut || !signedIn) return;

      if (status.logged_in && status.user) {
        signedOut.classList.add("hidden");
        signedIn.classList.remove("hidden");
        if (nameEl) nameEl.textContent = status.user.display_name || status.user.email;
        if (saveBtn) saveBtn.classList.remove("hidden");
      } else {
        signedOut.classList.remove("hidden");
        signedIn.classList.add("hidden");
        if (saveBtn) saveBtn.classList.add("hidden");
      }

      const googleBtn = $("authGoogleBtn");
      if (googleBtn) {
        googleBtn.disabled = !status.google_configured;
        googleBtn.title = status.google_configured ? "" : "Google sign-in coming soon — use email for now";
      }
    },

    openAuth(mode = "login") {
      $("authModal")?.classList.remove("hidden");
      $("authModalTitle").textContent = mode === "signup" ? "Create account" : "Sign in";
      $("authSubmitBtn").textContent = mode === "signup" ? "Sign up" : "Sign in";
      $("authSubmitBtn").dataset.mode = mode;
      $("authError").classList.add("hidden");
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
        errEl.textContent = "Email and password required.";
        errEl.classList.remove("hidden");
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
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || data.error || "Auth failed");
        this.closeAuth();
        await this.refreshAuth();
        window.toast?.(mode === "signup" ? "Welcome to Bridge!" : "Signed in");
      } catch (e) {
        errEl.textContent = e.message;
        errEl.classList.remove("hidden");
      }
    },

    async logout() {
      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
      authUser = null;
      await this.refreshAuth();
      window.toast?.("Signed out");
    },

    async saveCurrentBridge() {
      if (!window.lastSession) return window.toast?.("Generate a bridge first");
      if (!authUser) return this.openAuth("login");
      try {
        const r = await fetch("/api/bridges/save", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(window.lastSession),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || "Save failed");
        window.toast?.("Bridge saved to your library");
        await this.loadSavedBridges();
      } catch (e) {
        window.toast?.(e.message);
      }
    },

    async loadSavedBridges() {
      const el = $("savedBridges");
      if (!el || !authUser) {
        el?.classList.add("hidden");
        return;
      }
      try {
        const data = await fetch("/api/bridges/saved", { credentials: "include" }).then(r => r.json());
        const bridges = data.bridges || [];
        if (!bridges.length) {
          el.classList.add("hidden");
          return;
        }
        el.classList.remove("hidden");
        el.innerHTML = `
          <div class="saved-bridges__head">
            <h3>Your saved bridges</h3>
            <span class="saved-bridges__count">${bridges.length}</span>
          </div>
          <div class="saved-bridges__scroll">
            ${bridges.map(b => `
              <button type="button" class="saved-bridge-card" data-id="${b.id}">
                <span class="saved-bridge-card__title">${escapeHtml(b.title || b.anchor_track)}</span>
                <span class="saved-bridge-card__meta">${escapeHtml((b.intent || "").slice(0, 48))}${(b.intent || "").length > 48 ? "…" : ""}</span>
              </button>
            `).join("")}
          </div>`;
        el.querySelectorAll(".saved-bridge-card").forEach(btn => {
          btn.addEventListener("click", () => this.openSavedBridge(btn.dataset.id));
        });
      } catch {
        el.classList.add("hidden");
      }
    },

    async openSavedBridge(id) {
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
        window.toast?.("Saved bridge loaded");
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
          $("intentInput").value = btn.dataset.intent;
          $("intentInput").focus();
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
        const title = document.getElementById("continueBridgeTitle");
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
      $("authSubmitBtn")?.addEventListener("click", () => this.submitAuth());
      $("authLogoutBtn")?.addEventListener("click", () => this.logout());
      $("authGoogleBtn")?.addEventListener("click", () => {
        window.location.href = "/api/auth/google";
      });
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
