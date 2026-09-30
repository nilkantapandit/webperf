(() => {
  const canvas = document.getElementById("matrixCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d", { alpha: true });
  if (!ctx) return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const state = {
    fps: 24,
    bgOpacity: 0.075,
    size: 18,
    color: "#5b8cff",
    charset: "01"
  };
  const speeds = { slow: 12, normal: 24, fast: 42 };
  let width = 0, height = 0, columns = [];
  let lastFrame = 0;

  function isDarkLanding() {
    return document.body?.classList.contains("landing-page") &&
      document.body?.dataset.theme !== "light" &&
      !document.body?.classList.contains("diagnostic-view") &&
      !reducedMotion.matches;
  }

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = Math.max(1, window.innerWidth);
    height = Math.max(1, window.innerHeight);
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.ceil(width / state.size);
    columns = Array.from({ length: count }, (_, i) => ({
      y: Math.random() * -height,
      speed: state.size * (0.65 + Math.random() * 0.8),
      x: i * state.size
    }));
    ctx.clearRect(0, 0, width, height);
  }

  function draw(now) {
    if (!isDarkLanding()) {
      ctx.clearRect(0, 0, width, height);
      return;
    }
    if (now - lastFrame < 1000 / state.fps) return;
    lastFrame = now;

    ctx.fillStyle = `rgba(5,9,20,${state.bgOpacity})`;
    ctx.fillRect(0, 0, width, height);
    ctx.font = `${state.size}px monospace`;
    ctx.textBaseline = "top";

    for (const column of columns) {
      const char = state.charset[Math.floor(Math.random() * state.charset.length)];
      ctx.fillStyle = `rgba(91,140,255,${0.58 + Math.random() * 0.24})`;
      ctx.fillText(char, column.x, column.y);
      column.y += column.speed;
      if (column.y > height + 30 || (column.y > 80 && Math.random() < 0.006)) {
        column.y = -Math.random() * height * 0.45;
        column.speed = state.size * (0.65 + Math.random() * 0.8);
      }
    }
  }

  function setSpeed(name) {
    if (!speeds[name]) return;
    state.fps = speeds[name];
    localStorage.setItem("webperf-matrix-speed", name);
    document.querySelectorAll("[data-matrix-speed]").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.matrixSpeed === name);
      btn.setAttribute("aria-pressed", btn.dataset.matrixSpeed === name ? "true" : "false");
    });
  }

  document.querySelectorAll("[data-matrix-speed]").forEach(btn => {
    btn.addEventListener("click", () => setSpeed(btn.dataset.matrixSpeed));
  });
  setSpeed(localStorage.getItem("webperf-matrix-speed") || "normal");

  function loop(now) {
    draw(now);
    requestAnimationFrame(loop);
  }

  resize();
  window.addEventListener("resize", resize, { passive: true });
  reducedMotion.addEventListener?.("change", resize);
  window.addEventListener("webperf-theme-change", () => { if (!isDarkLanding()) ctx.clearRect(0, 0, width, height); });
  requestAnimationFrame(loop);
})();
