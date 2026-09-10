(() => {
  if (window.__e2eHud) {
    return;
  }
  const TEXT = {
    en: {
      step: "Step",
      setup: "Setup",
      running: "running",
      passed: "passed",
      failed: "FAILED",
      error: "ERROR",
      skipped: "skipped",
      verify: "Verify",
      reproduce: "Reproduce",
      result: "Result"
    },
    de: {
      step: "Schritt",
      setup: "Vorbereitung",
      running: "läuft",
      passed: "OK",
      failed: "FEHLGESCHLAGEN",
      error: "FEHLER",
      skipped: "übersprungen",
      verify: "Verifikation",
      reproduce: "Reproduktion",
      result: "Ergebnis"
    }
  };
  const TONES = {
    fixed: "good",
    not_reproduced: "good",
    passed: "good",
    reproduced: "warn",
    still_broken: "bad",
    failed: "bad",
    inconclusive: "neutral"
  };
  const STYLE = `
    :host { all: initial; pointer-events: none; }
    * { pointer-events: none; box-sizing: border-box; }
    .banner {
      position: fixed; left: 0; right: 0; top: 0; height: 48px;
      display: flex; align-items: center; gap: 12px; padding: 0 16px;
      font: 600 15px/1.2 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #ffffff; background: #1f2937; z-index: 2147483647;
      white-space: nowrap; overflow: hidden;
    }
    .banner[data-position="bottom"] { top: auto; bottom: 0; }
    .banner[data-status="running"] { background: #1d4ed8; }
    .banner[data-status="passed"] { background: #15803d; }
    .banner[data-status="failed"] { background: #b91c1c; }
    .banner[data-status="error"] { background: #4b5563; }
    .badge {
      background: rgba(255, 255, 255, 0.22); padding: 3px 8px; border-radius: 4px;
      font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase;
    }
    .step { opacity: 0.9; }
    .title { flex: 1; overflow: hidden; text-overflow: ellipsis; }
    .message { font-weight: 400; opacity: 0.95; overflow: hidden; text-overflow: ellipsis; max-width: 45%; }
    .status { font-size: 13px; text-transform: uppercase; letter-spacing: 0.04em; }
    .timer { font-variant-numeric: tabular-nums; opacity: 0.8; }
    .frame {
      position: fixed; display: none; border: 4px solid #dc2626; border-radius: 4px;
      box-shadow: 0 0 0 4px rgba(220, 38, 38, 0.35); z-index: 2147483646;
    }
    .callout {
      position: fixed; display: none; max-width: 440px; padding: 8px 12px;
      background: #dc2626; color: #ffffff; border-radius: 6px; z-index: 2147483646;
      font: 500 14px/1.35 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      white-space: normal; word-break: break-word;
    }
    .final {
      position: fixed; display: none; left: 0; right: 0; top: 48px; padding: 10px 16px;
      font: 600 16px/1.3 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #ffffff; background: #4b5563; z-index: 2147483647; white-space: normal;
    }
    .final[data-position="bottom"] { top: auto; bottom: 48px; }
    .final[data-tone="good"] { background: #15803d; }
    .final[data-tone="bad"] { background: #b91c1c; }
    .final[data-tone="warn"] { background: #c2410c; }
    .final[data-tone="neutral"] { background: #4b5563; }
    .note-frame {
      position: fixed; display: none; border: 4px solid #2563eb; border-radius: 6px;
      box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.3); z-index: 2147483646;
    }
    .note-callout {
      position: fixed; display: none; max-width: 460px; padding: 10px 14px;
      background: #2563eb; color: #ffffff; border-radius: 8px; z-index: 2147483647;
      font: 600 15px/1.35 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      white-space: normal; word-break: break-word; box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
    }
    .note-frame[data-tone="success"] { border-color: #15803d; box-shadow: 0 0 0 4px rgba(21, 128, 61, 0.3); }
    .note-callout[data-tone="success"] { background: #15803d; }
    .note-frame[data-tone="failure"] { border-color: #dc2626; box-shadow: 0 0 0 4px rgba(220, 38, 38, 0.3); }
    .note-callout[data-tone="failure"] { background: #dc2626; }
  `;
  const state = {
    enabled: true,
    ticket_id: "",
    mode: "verify",
    language: "en",
    position: "top",
    show_timer: true,
    show_ticket_id: true,
    started_at_ms: Date.now(),
    step: null,
    failure: null,
    final: null,
    annotation: null
  };
  let host = null;
  let parts = null;

  const build = () => {
    host = document.createElement("e2e-hud");
    host.setAttribute("data-e2e-hud", "1");
    host.setAttribute("aria-hidden", "true");
    const root = host.attachShadow({ mode: "closed" });
    root.innerHTML =
      `<style>${STYLE}</style>` +
      '<div class="banner" data-status="idle">' +
      '<span class="badge ticket"></span><span class="badge mode"></span>' +
      '<span class="step"></span><span class="title"></span><span class="message"></span>' +
      '<span class="status"></span><span class="timer"></span></div>' +
      '<div class="frame"></div><div class="callout"></div><div class="final"></div>' +
      '<div class="note-frame"></div><div class="note-callout"></div>';
    parts = {
      banner: root.querySelector(".banner"),
      ticket: root.querySelector(".ticket"),
      mode: root.querySelector(".mode"),
      step: root.querySelector(".step"),
      title: root.querySelector(".title"),
      message: root.querySelector(".message"),
      status: root.querySelector(".status"),
      timer: root.querySelector(".timer"),
      frame: root.querySelector(".frame"),
      callout: root.querySelector(".callout"),
      final: root.querySelector(".final"),
      noteFrame: root.querySelector(".note-frame"),
      noteCallout: root.querySelector(".note-callout")
    };
  };

  const placeCallout = (element, rect) => {
    const below = rect.y + rect.height + 14;
    const fitsBelow = below + 60 < window.innerHeight;
    element.style.left = `${Math.max(8, Math.min(rect.x, window.innerWidth - 480))}px`;
    element.style.top = fitsBelow ? `${below}px` : `${Math.max(56, rect.y - 70)}px`;
  };

  const renderAnnotation = () => {
    const note = state.annotation;
    if (!note) {
      parts.noteFrame.style.display = "none";
      parts.noteCallout.style.display = "none";
      return;
    }
    const tone = note.tone || "info";
    parts.noteFrame.dataset.tone = tone;
    parts.noteCallout.dataset.tone = tone;
    parts.noteCallout.textContent = note.message || "";
    parts.noteCallout.style.display = note.message ? "block" : "none";
    if (note.rect) {
      const rect = note.rect;
      parts.noteFrame.style.display = "block";
      parts.noteFrame.style.left = `${rect.x - 6}px`;
      parts.noteFrame.style.top = `${rect.y - 6}px`;
      parts.noteFrame.style.width = `${rect.width + 12}px`;
      parts.noteFrame.style.height = `${rect.height + 12}px`;
      placeCallout(parts.noteCallout, rect);
      return;
    }
    parts.noteFrame.style.display = "none";
    parts.noteCallout.style.left = "16px";
    parts.noteCallout.style.top = state.position === "bottom" ? "16px" : "64px";
  };

  const mount = () => {
    const parent = document.documentElement;
    if (!parent) {
      return false;
    }
    if (!host) {
      build();
    }
    if (!host.isConnected) {
      parent.appendChild(host);
    }
    return true;
  };

  const elapsed = () => {
    const total = Math.max(0, Date.now() - state.started_at_ms);
    const seconds = Math.floor(total / 1000);
    const minutes = Math.floor(seconds / 60);
    const rest = seconds % 60;
    const tenths = Math.floor((total % 1000) / 100);
    return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}.${tenths}`;
  };

  const renderFrame = () => {
    const failure = state.failure;
    if (!failure || !failure.rect) {
      parts.frame.style.display = "none";
      parts.callout.style.display = "none";
      return;
    }
    const rect = failure.rect;
    parts.frame.style.display = "block";
    parts.frame.style.left = `${rect.x - 6}px`;
    parts.frame.style.top = `${rect.y - 6}px`;
    parts.frame.style.width = `${rect.width + 12}px`;
    parts.frame.style.height = `${rect.height + 12}px`;
    parts.callout.textContent = failure.message || "";
    parts.callout.style.display = failure.message ? "block" : "none";
    placeCallout(parts.callout, rect);
  };

  const render = () => {
    if (!mount()) {
      return;
    }
    const text = TEXT[state.language] || TEXT.en;
    host.style.display = state.enabled ? "" : "none";
    parts.banner.dataset.position = state.position;
    parts.final.dataset.position = state.position;
    parts.ticket.textContent = state.show_ticket_id && state.ticket_id ? state.ticket_id : "";
    parts.ticket.style.display = parts.ticket.textContent ? "" : "none";
    parts.mode.textContent = state.mode === "reproduce" ? text.reproduce : text.verify;
    const step = state.step;
    if (step) {
      const label = step.phase === "preconditions" ? text.setup : text.step;
      parts.step.textContent =
        step.total > 0 ? `${label} ${step.index}/${step.total}` : `${label} ${step.index}`;
      parts.title.textContent = step.title || "";
      parts.status.textContent = text[step.status] || step.status;
      parts.banner.dataset.status = step.status;
    } else {
      parts.step.textContent = "";
      parts.title.textContent = "";
      parts.status.textContent = "";
      parts.banner.dataset.status = "idle";
    }
    parts.message.textContent = state.failure && state.failure.message ? state.failure.message : "";
    parts.timer.textContent = state.show_timer ? elapsed() : "";
    renderFrame();
    renderAnnotation();
    const final = state.final;
    if (final) {
      parts.final.style.display = "block";
      parts.final.dataset.tone = TONES[final.verdict] || "neutral";
      parts.final.textContent = `${text.result}: ${final.verdict} - ${final.message || ""}`;
    } else {
      parts.final.style.display = "none";
    }
  };

  const api = Object.freeze({
    setState(next) {
      Object.assign(state, next || {});
      render();
    },
    setStep(step) {
      state.step = Object.assign({ status: "running" }, step);
      state.failure = null;
      state.final = null;
      render();
    },
    markSuccess() {
      if (state.step) {
        state.step.status = "passed";
      }
      render();
    },
    markFailure(failure) {
      if (state.step) {
        state.step.status = "failed";
      }
      state.failure = failure || { rect: null, message: "" };
      render();
    },
    markError(message) {
      if (state.step) {
        state.step.status = "error";
      }
      state.failure = { rect: null, message: message || "" };
      render();
    },
    setFinal(final) {
      state.final = final;
      render();
    },
    annotate(note) {
      state.annotation = note || null;
      render();
    },
    clearAnnotation() {
      state.annotation = null;
      render();
    },
    getState() {
      return JSON.parse(JSON.stringify(state));
    }
  });

  Object.defineProperty(window, "__e2eHud", {
    value: api,
    enumerable: false,
    configurable: false,
    writable: false
  });

  const keepMounted = () => {
    const observer = new MutationObserver(() => {
      if (host && !host.isConnected) {
        mount();
      }
    });
    observer.observe(document.documentElement, { childList: true });
  };

  const start = () => {
    mount();
    keepMounted();
    render();
  };

  if (document.documentElement) {
    start();
  } else {
    const early = new MutationObserver(() => {
      if (document.documentElement) {
        early.disconnect();
        start();
      }
    });
    early.observe(document, { childList: true });
  }
  document.addEventListener("DOMContentLoaded", render);

  if (typeof window.__e2eHudState === "function") {
    Promise.resolve(window.__e2eHudState())
      .then((next) => {
        if (next) {
          api.setState(next);
        }
      })
      .catch(() => {});
  }

  setInterval(() => {
    if (state.enabled && state.show_timer && parts && host && host.isConnected) {
      parts.timer.textContent = elapsed();
    }
  }, 250);
})();
