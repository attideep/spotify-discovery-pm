/** Custom bridge player — Spotify audio via hidden embed API + our UI chrome. */
(function () {
  const STORAGE_VOL = "bridge_player_volume";
  let embedController = null;
  let spotifyApi = null;
  let eqAnim = null;
  let isPlaying = false;

  window.BridgePlayer = {
    init() {
      this._bindControls();
      this._loadVolume();
      this._initEq();
    },

    _bindControls() {
      document.getElementById("playerPlayBtn")?.addEventListener("click", () => this.togglePlay());
      document.getElementById("playerVolume")?.addEventListener("input", e => {
        const v = parseInt(e.target.value, 10) / 100;
        localStorage.setItem(STORAGE_VOL, String(v));
        this._setVolumeLabel(v);
        if (v === 0) this.pause();
        else if (!isPlaying && embedController) this.play();
      });
      document.getElementById("playerMenuBtn")?.addEventListener("click", () => {
        document.getElementById("playerMenu")?.classList.toggle("hidden");
      });
      document.querySelectorAll("[data-legal]").forEach(btn => {
        btn.addEventListener("click", () => {
          document.getElementById("playerMenu")?.classList.add("hidden");
          const id = btn.dataset.legal;
          document.getElementById(id)?.classList.remove("hidden");
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

    _setVolumeLabel(v) {
      const el = document.getElementById("playerVolumeLabel");
      if (el) el.textContent = v === 0 ? "Muted" : `${Math.round(v * 100)}%`;
    },

    loadTrack(track) {
      if (!track?.track_id) return;
      const host = document.getElementById("spotifyEmbedHost");
      if (!host) return;
      host.innerHTML = "";
      embedController = null;
      const uri = `spotify:track:${track.track_id}`;

      const fallbackIframe = () => {
        host.innerHTML = `<iframe src="https://open.spotify.com/embed/track/${track.track_id}?utm_source=generator&theme=0" width="1" height="1" style="opacity:0;position:absolute;pointer-events:none" allow="autoplay; clipboard-write; encrypted-media" title="Spotify preview"></iframe>`;
        isPlaying = true;
        this._syncPlayBtn();
        this._startEq();
      };

      if (!spotifyApi) {
        fallbackIframe();
        return;
      }

      spotifyApi.createController(host, { uri, width: 1, height: 1 }, controller => {
        embedController = controller;
        controller.addListener("ready", () => {
          const vol = parseFloat(localStorage.getItem(STORAGE_VOL) || "0.85");
          if (vol > 0) controller.play();
          isPlaying = vol > 0;
          this._syncPlayBtn();
          if (isPlaying) this._startEq();
        });
        controller.addListener("playback_update", e => {
          isPlaying = !e.data.isPaused;
          this._syncPlayBtn();
          if (isPlaying) this._startEq();
          else this._stopEq();
        });
      });
    },

    stopEq() {
      this._stopEq();
    },

    play() {
      embedController?.play?.();
      isPlaying = true;
      this._syncPlayBtn();
      this._startEq();
    },

    pause() {
      embedController?.pause?.();
      isPlaying = false;
      this._syncPlayBtn();
      this._stopEq();
    },

    togglePlay() {
      if (isPlaying) this.pause();
      else this.play();
    },

    _syncPlayBtn() {
      const btn = document.getElementById("playerPlayBtn");
      if (btn) btn.textContent = isPlaying ? "⏸" : "▶";
    },

    _initEq() {
      const canvas = document.getElementById("eqCanvas");
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      const resize = () => {
        canvas.width = canvas.offsetWidth * (window.devicePixelRatio || 1);
        canvas.height = canvas.offsetHeight * (window.devicePixelRatio || 1);
      };
      resize();
      window.addEventListener("resize", resize);
      this._eqCtx = ctx;
      this._eqCanvas = canvas;
    },

    _startEq() {
      if (eqAnim || !this._eqCtx) return;
      const ctx = this._eqCtx;
      const canvas = this._eqCanvas;
      const bars = 24;
      const phases = Array.from({ length: bars }, () => Math.random() * Math.PI * 2);
      const draw = () => {
        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);
        const bw = w / bars;
        for (let i = 0; i < bars; i += 1) {
          phases[i] += 0.08 + i * 0.004;
          const amp = (Math.sin(phases[i]) * 0.35 + 0.55) * (0.4 + (i % 5) * 0.08);
          const bh = amp * h * 0.9;
          const g = ctx.createLinearGradient(0, h - bh, 0, h);
          g.addColorStop(0, "#1ed760");
          g.addColorStop(1, "#509bf5");
          ctx.fillStyle = g;
          ctx.fillRect(i * bw + 1, h - bh, bw - 2, bh);
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

    tourTimer: null,
    toggleTour() {
      const btn = document.getElementById("playerTourBtn");
      if (this.tourTimer) {
        clearInterval(this.tourTimer);
        this.tourTimer = null;
        if (btn) btn.classList.remove("chip--active");
        window.toast?.("Bridge tour paused");
        return;
      }
      if (btn) btn.classList.add("chip--active");
      window.toast?.("Bridge tour — auto-advancing every 30s");
      this.tourTimer = setInterval(() => {
        document.getElementById("playerNext")?.click();
      }, 30000);
    },
  };

  window.onSpotifyIframeApiReady = IFrameAPI => {
    spotifyApi = IFrameAPI;
  };
})();
