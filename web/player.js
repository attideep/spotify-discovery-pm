/** Bridge player — HTML5 preview + Web Audio (volume; optional EQ). */
(function () {
  const STORAGE_VOL = "bridge_player_volume";
  const STORAGE_EQ = "bridge_player_eq";
  const minimal = () => Boolean(window.PLAYER_MINIMAL);
  const previewCache = new Map();

  let audio = null;
  let source = null;
  let ctx = null;
  let gain = null;
  let bass = null;
  let mid = null;
  let treble = null;
  let analyser = null;
  let eqAnim = null;
  let isPlaying = false;
  let loadGen = 0;
  let tourTimer = null;
  let seekDragging = false;
  let progressTimer = null;

  function fmtTime(sec) {
    if (!Number.isFinite(sec) || sec < 0) return "0:00";
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  }

  function readEq() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_EQ) || '{"bass":0,"mid":0,"treble":0}');
    } catch {
      return { bass: 0, mid: 0, treble: 0 };
    }
  }

  function saveEq(values) {
    localStorage.setItem(STORAGE_EQ, JSON.stringify(values));
  }

  async function fetchPreviewUrl(track) {
    const key = track.track_id || `${track.name}|${track.artist}`;
    if (previewCache.has(key)) return previewCache.get(key);

    const params = new URLSearchParams();
    if (track.track_id) params.set("track_id", track.track_id);
    if (track.name) params.set("name", track.name);
    if (track.artist) params.set("artist", track.artist);
    if (!params.toString()) return null;

    try {
      const r = await fetch(`/api/preview?${params}`);
      if (!r.ok) return null;
      const data = await r.json();
      const url = data.preview_url || null;
      if (url) previewCache.set(key, url);
      return url;
    } catch {
      return null;
    }
  }

  window.BridgePlayer = {
    init() {
      this._bindControls();
      this._loadVolume();
      if (!minimal()) {
        this._loadEqSliders();
        this._initEqCanvas();
      }
    },

    _bindControls() {
      document.getElementById("playerPlayBtn")?.addEventListener("click", () => this.togglePlay());
      document.getElementById("playerVolume")?.addEventListener("input", e => {
        const v = parseInt(e.target.value, 10) / 100;
        localStorage.setItem(STORAGE_VOL, String(v));
        this._setVolumeLabel(v);
        if (gain) gain.gain.value = v;
      });
      if (!minimal()) {
        ["eqBass", "eqMid", "eqTreble"].forEach(id => {
          document.getElementById(id)?.addEventListener("input", () => this._applyEqFromSliders());
        });
      }
      const seek = document.getElementById("playerSeek");
      seek?.addEventListener("input", () => {
        seekDragging = true;
        if (!audio) return;
        const pct = parseInt(seek.value, 10) / 1000;
        const t = pct * (audio.duration || 30);
        document.getElementById("playerTimeCurrent").textContent = fmtTime(t);
      });
      seek?.addEventListener("change", () => {
        if (!audio) return;
        const pct = parseInt(seek.value, 10) / 1000;
        audio.currentTime = pct * (audio.duration || 30);
        seekDragging = false;
      });
      document.getElementById("playerMenuBtn")?.addEventListener("click", () => {
        document.getElementById("playerMenu")?.classList.toggle("hidden");
      });
      document.querySelectorAll("[data-legal]").forEach(btn => {
        btn.addEventListener("click", () => {
          document.getElementById("playerMenu")?.classList.add("hidden");
          document.getElementById(btn.dataset.legal)?.classList.remove("hidden");
        });
      });
      document.querySelectorAll("[data-close-modal]").forEach(btn => {
        btn.addEventListener("click", () => {
          document.getElementById(btn.dataset.closeModal)?.classList.add("hidden");
        });
      });
      document.getElementById("playerTourBtn")?.addEventListener("click", () => this.toggleTour());
    },

    _loadVolume() {
      const v = parseFloat(localStorage.getItem(STORAGE_VOL) || "0.85");
      const slider = document.getElementById("playerVolume");
      if (slider) slider.value = Math.round(v * 100);
      this._setVolumeLabel(v);
    },

    _loadEqSliders() {
      const eq = readEq();
      const map = { eqBass: "bass", eqMid: "mid", eqTreble: "treble" };
      Object.entries(map).forEach(([id, k]) => {
        const el = document.getElementById(id);
        if (el) el.value = eq[k] ?? 0;
      });
    },

    _setVolumeLabel(v) {
      const el = document.getElementById("playerVolumeLabel");
      if (el) el.textContent = v === 0 ? "Muted" : `${Math.round(v * 100)}%`;
    },

    _applyEqFromSliders() {
      const values = {
        bass: parseInt(document.getElementById("eqBass")?.value || "0", 10),
        mid: parseInt(document.getElementById("eqMid")?.value || "0", 10),
        treble: parseInt(document.getElementById("eqTreble")?.value || "0", 10),
      };
      saveEq(values);
      if (bass) bass.gain.value = values.bass;
      if (mid) mid.gain.value = values.mid;
      if (treble) treble.gain.value = values.treble;
    },

    async _ensureContext() {
      if (!ctx) {
        ctx = new AudioContext();
        gain = ctx.createGain();
        if (!minimal()) {
          bass = ctx.createBiquadFilter();
          bass.type = "lowshelf";
          bass.frequency.value = 150;
          mid = ctx.createBiquadFilter();
          mid.type = "peaking";
          mid.frequency.value = 1000;
          mid.Q.value = 0.9;
          treble = ctx.createBiquadFilter();
          treble.type = "highshelf";
          treble.frequency.value = 4500;
          analyser = ctx.createAnalyser();
          analyser.fftSize = 64;
          bass.connect(mid);
          mid.connect(treble);
          treble.connect(gain);
          gain.connect(analyser);
          analyser.connect(ctx.destination);
          this._applyEqFromSliders();
        }
      }
      if (ctx.state === "suspended") await ctx.resume();
      const v = parseFloat(localStorage.getItem(STORAGE_VOL) || "0.85");
      gain.gain.value = v;
    },

    _connectSource() {
      if (!source || !gain) return;
      if (minimal()) {
        source.connect(gain);
        gain.connect(ctx.destination);
      } else {
        source.connect(bass);
      }
    },

    _startProgress() {
      clearInterval(progressTimer);
      progressTimer = setInterval(() => this._updateProgress(), 250);
    },

    _stopProgress() {
      clearInterval(progressTimer);
      progressTimer = null;
    },

    _updateProgress() {
      if (!audio || seekDragging) return;
      const dur = audio.duration || 30;
      const cur = audio.currentTime || 0;
      const seek = document.getElementById("playerSeek");
      const curEl = document.getElementById("playerTimeCurrent");
      const durEl = document.getElementById("playerTimeDur");
      if (seek) seek.value = String(Math.round((cur / dur) * 1000));
      if (curEl) curEl.textContent = fmtTime(cur);
      if (durEl) durEl.textContent = fmtTime(dur);
    },

    _clearPlayback() {
      if (audio) {
        audio.pause();
        audio.removeAttribute("src");
        audio.load();
        audio = null;
      }
      if (source) {
        try { source.disconnect(); } catch { /* ignore */ }
        source = null;
      }
      isPlaying = false;
      this._syncPlayBtn();
      this._stopEq();
      this._stopProgress();
    },

    async stop() {
      loadGen += 1;
      this._clearPlayback();
    },

    async loadTrack(track) {
      if (!track?.track_id && !track?.name) return;
      const gen = ++loadGen;
      this._clearPlayback();

      const previewUrl = await fetchPreviewUrl(track);
      if (gen !== loadGen) return;

      if (!previewUrl) {
        window.toast?.("No preview clip found — open in Spotify for full track");
        return;
      }

      await this._ensureContext();
      if (gen !== loadGen) return;

      audio = new Audio();
      audio.crossOrigin = "anonymous";
      audio.preload = "auto";
      audio.src = previewUrl;

      await new Promise((resolve, reject) => {
        const done = () => {
          audio.removeEventListener("canplay", done);
          audio.removeEventListener("error", err);
          resolve();
        };
        const err = () => {
          audio.removeEventListener("canplay", done);
          audio.removeEventListener("error", err);
          reject(new Error("preview load failed"));
        };
        audio.addEventListener("canplay", done);
        audio.addEventListener("error", err);
      }).catch(() => {
        window.toast?.("Preview unavailable");
        return;
      });

      if (gen !== loadGen || !audio) return;

      source = ctx.createMediaElementSource(audio);
      this._connectSource();

      audio.addEventListener("ended", () => {
        isPlaying = false;
        this._syncPlayBtn();
        this._stopEq();
        this._stopProgress();
      });

      const vol = parseFloat(localStorage.getItem(STORAGE_VOL) || "0.85");
      if (vol > 0) {
        try {
          await audio.play();
          isPlaying = true;
          this._syncPlayBtn();
          if (minimal()) this._startProgress();
          else this._startEq();
        } catch {
          window.toast?.("Tap play to start preview");
        }
      }
    },

    async play() {
      if (!audio) return;
      await this._ensureContext();
      const v = parseFloat(localStorage.getItem(STORAGE_VOL) || "0.85");
      if (gain) gain.gain.value = v;
      if (v === 0) return;
      await audio.play();
      isPlaying = true;
      this._syncPlayBtn();
      if (minimal()) this._startProgress();
      else this._startEq();
    },

    async pause() {
      if (audio) audio.pause();
      isPlaying = false;
      this._syncPlayBtn();
      this._stopEq();
      this._stopProgress();
    },

    togglePlay() {
      if (isPlaying) this.pause();
      else this.play();
    },

    _syncPlayBtn() {
      const btn = document.getElementById("playerPlayBtn");
      if (btn) btn.textContent = isPlaying ? "⏸" : "▶";
    },

    _initEqCanvas() {
      const canvas = document.getElementById("eqCanvas");
      if (!canvas) return;
      const resize = () => {
        canvas.width = canvas.offsetWidth * (window.devicePixelRatio || 1);
        canvas.height = canvas.offsetHeight * (window.devicePixelRatio || 1);
      };
      resize();
      window.addEventListener("resize", resize);
      this._eqCanvas = canvas;
      this._eqCtx = canvas.getContext("2d");
    },

    _startEq() {
      if (eqAnim || !this._eqCtx || !analyser) return;
      const canvas = this._eqCanvas;
      const ctx2d = this._eqCtx;
      const data = new Uint8Array(analyser.frequencyBinCount);
      const draw = () => {
        analyser.getByteFrequencyData(data);
        const w = canvas.width;
        const h = canvas.height;
        ctx2d.clearRect(0, 0, w, h);
        const bars = 24;
        const step = Math.floor(data.length / bars);
        for (let i = 0; i < bars; i += 1) {
          const v = data[i * step] / 255;
          const bh = v * h * 0.95;
          const g = ctx2d.createLinearGradient(0, h - bh, 0, h);
          g.addColorStop(0, "#1ed760");
          g.addColorStop(1, "#509bf5");
          ctx2d.fillStyle = g;
          ctx2d.fillRect((i * w) / bars + 1, h - bh, w / bars - 2, bh);
        }
        eqAnim = requestAnimationFrame(draw);
      };
      draw();
    },

    _stopEq() {
      if (eqAnim) cancelAnimationFrame(eqAnim);
      eqAnim = null;
      if (this._eqCtx && this._eqCanvas) {
        this._eqCtx.clearRect(0, 0, this._eqCanvas.width, this._eqCanvas.height);
      }
    },

    toggleTour() {
      const btn = document.getElementById("playerTourBtn");
      if (tourTimer) {
        clearInterval(tourTimer);
        tourTimer = null;
        btn?.classList.remove("chip--active");
        window.toast?.("Bridge tour paused");
        return;
      }
      btn?.classList.add("chip--active");
      window.toast?.("Auto tour — next track every 30s");
      tourTimer = setInterval(() => {
        document.getElementById("playerNext")?.click();
      }, 30000);
    },
  };
})();
