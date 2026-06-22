// ── Scene parameters ──────────────────────────────────────────────────────────
const orbits = [
  { radius: 0.14, speed: 0.0008,  tilt:  0.2  },
  { radius: 0.22, speed: 0.0005,  tilt: -0.15 },
  { radius: 0.31, speed: 0.00035, tilt:  0.35 },
  { radius: 0.42, speed: 0.00025, tilt: -0.25 },
];

const OBJECTS = [
  { orbit: 0, angle: 0.4, size: 4, color: "#ffd166", kind: "object" },
  { orbit: 1, angle: 2.1, size: 3, color: "#7ee787", kind: "object" },
  { orbit: 1, angle: 4.8, size: 3, color: "#ff6b6b", kind: "debris" },
  { orbit: 2, angle: 1.2, size: 5, color: "#ffd166", kind: "object" },
  { orbit: 2, angle: 5.0, size: 3, color: "#ff6b6b", kind: "debris" },
  { orbit: 3, angle: 3.3, size: 4, color: "#a78bfa", kind: "object" },
  { orbit: 3, angle: 1.1, size: 4, color: "#00ff88", kind: "ufo" },
];

// ── Canvas setup ──────────────────────────────────────────────────────────────
const canvas = document.getElementById("space-map");
const ctx = canvas.getContext("2d");

const stars = [];
let CX = 0, CY = 0, SCALE = 1;

// ── Mutable scene state ───────────────────────────────────────────────────────
const objPositions = OBJECTS.map(() => ({ x: 0, y: 0 }));
let hoveredIdx = null;
let selectedIdx = null;
const classCache = {};

// ── Simulation state ──────────────────────────────────────────────────────────
const SIM_SPEED = 200;
let forecastPaths = null;
let forecasting = false;

let simMode    = false;
let simPaused  = false;
let simStartReal = performance.now();
let simStartEff  = performance.now();

function effectiveTime(real) {
  if (!simMode) return real;
  if (simPaused) return simStartEff;
  return simStartEff + (real - simStartReal) * SIM_SPEED;
}

// ── Form: load scene ──────────────────────────────────────────────────────────
document.getElementById("scene-form").addEventListener("submit", function (e) {
  e.preventDefault();

  const ra      = document.getElementById("ra").value.trim();
  const dec     = document.getElementById("dec").value.trim();
  const obsDate = document.getElementById("obs_date").value;

  if (!obsDate) return;

  const ts = new Date(obsDate + "T00:00:00Z").getTime();

  simMode      = true;
  simPaused    = true;
  simStartReal = performance.now();
  simStartEff  = ts;
  forecastPaths = null;

  playBtn.textContent = "▶ Play Simulation";
  playBtn.classList.remove("playing");
  simTimeEl.style.display = "block";
  simTimeEl.textContent   = "Paused — " + obsDate;

  const html = ra && dec
    ? '<div class="results">' +
        '<h3>Loaded Scene</h3>' +
        '<p>RA: ' + esc(ra) + ' &nbsp; Dec: ' + esc(dec) + '</p>' +
        '<p>Date: ' + esc(obsDate) + '</p>' +
        '<p style="margin-top:0.5rem;color:#7a9acc;font-size:0.82rem;">' +
          'Scene paused at this date. Press &#9654; Play to simulate forward.' +
        '</p>' +
      '</div>'
    : '';
  document.getElementById("scene-result").innerHTML = html;
});

function esc(s) {
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

// ── Stars ─────────────────────────────────────────────────────────────────────
function initStars(count) {
  stars.length = 0;
  for (let i = 0; i < count; i++) {
    stars.push({
      x: Math.random(), y: Math.random(),
      r: Math.random() * 1.4 + 0.3,
      twinkle: Math.random() * Math.PI * 2,
    });
  }
}

// ── Draw helpers ──────────────────────────────────────────────────────────────
function drawBackground() {
  const w = window.innerWidth, h = window.innerHeight;
  const g = ctx.createRadialGradient(w*.5, h*.45, 0, w*.5, h*.45, Math.max(w,h)*.75);
  g.addColorStop(0, "#0a1030");
  g.addColorStop(0.45, "#050818");
  g.addColorStop(1, "#010208");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
  for (const s of stars) {
    const alpha = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(s.twinkle));
    ctx.fillStyle = `rgba(220,230,255,${alpha})`;
    ctx.beginPath();
    ctx.arc(s.x * w, s.y * h, s.r, 0, Math.PI * 2);
    ctx.fill();
    s.twinkle += 0.015 + Math.random() * 0.01;
  }
}

function drawEarth(cx, cy, scale) {
  const r = scale * 0.045;
  const glow = ctx.createRadialGradient(cx, cy, r*.5, cx, cy, r*3);
  glow.addColorStop(0, "rgba(77,163,255,0.35)");
  glow.addColorStop(1, "rgba(77,163,255,0)");
  ctx.fillStyle = glow;
  ctx.beginPath(); ctx.arc(cx, cy, r*3, 0, Math.PI*2); ctx.fill();
  const eg = ctx.createRadialGradient(cx-r*.3, cy-r*.3, r*.2, cx, cy, r);
  eg.addColorStop(0, "#7ec8ff"); eg.addColorStop(0.55, "#2b6cb0"); eg.addColorStop(1, "#0a2240");
  ctx.fillStyle = eg;
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2); ctx.fill();
  ctx.strokeStyle = "rgba(140,200,255,0.5)"; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2); ctx.stroke();
}

function drawOrbitalPaths(cx, cy, scale) {
  for (const o of orbits) {
    const rx = scale * o.radius;
    const ry = scale * o.radius * (1 - Math.abs(o.tilt) * 0.35);
    ctx.strokeStyle = "rgba(120,170,255,0.22)"; ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx, ry, o.tilt, 0, Math.PI*2);
    ctx.stroke();
  }
}

function objectXY(obj, time, cx, cy, scale) {
  const o = orbits[obj.orbit];
  const angle = obj.angle + time * o.speed * 1000;
  const rx = scale * o.radius;
  const ry = scale * o.radius * (1 - Math.abs(o.tilt) * 0.35);
  return { x: cx + Math.cos(angle) * rx, y: cy + Math.sin(angle) * ry };
}

function drawForecastPaths(cx, cy, scale) {
  if (!forecastPaths) return;
  ctx.save();
  ctx.setLineDash([5, 8]);
  ctx.lineWidth = 1.5;
  for (const p of forecastPaths) {
    const obj = OBJECTS[p.id];
    ctx.globalAlpha = 0.45;
    ctx.strokeStyle = obj.color;
    ctx.beginPath();
    let first = true;
    for (const [xn, yn] of p.waypoints) {
      const px = cx + xn * scale;
      const py = cy + yn * scale;
      if (first) { ctx.moveTo(px, py); first = false; }
      else ctx.lineTo(px, py);
    }
    ctx.stroke();
    if (p.waypoints.length > 0) {
      const [xn, yn] = p.waypoints[p.waypoints.length - 1];
      ctx.globalAlpha = 0.7;
      ctx.fillStyle = obj.color;
      ctx.shadowColor = obj.color;
      ctx.shadowBlur = 6;
      ctx.beginPath();
      ctx.arc(cx + xn * scale, cy + yn * scale, 3, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    }
  }
  ctx.setLineDash([]);
  ctx.globalAlpha = 1;
  ctx.restore();
}

function drawObjects(cx, cy, scale, time) {
  for (let i = 0; i < OBJECTS.length; i++) {
    const obj = OBJECTS[i];
    const { x, y } = objectXY(obj, time, cx, cy, scale);
    objPositions[i].x = x;
    objPositions[i].y = y;

    if (i === selectedIdx) {
      ctx.strokeStyle = obj.color;
      ctx.lineWidth = 1.5;
      ctx.globalAlpha = 0.75;
      ctx.beginPath(); ctx.arc(x, y, obj.size + 7, 0, Math.PI * 2); ctx.stroke();
      ctx.globalAlpha = 1;
    }

    if (i === hoveredIdx && i !== selectedIdx) {
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1;
      ctx.globalAlpha = 0.35;
      ctx.beginPath(); ctx.arc(x, y, obj.size + 6, 0, Math.PI * 2); ctx.stroke();
      ctx.globalAlpha = 1;
    }

    ctx.fillStyle = obj.color;
    ctx.shadowColor = obj.color;
    ctx.shadowBlur = 8;
    ctx.beginPath(); ctx.arc(x, y, obj.size, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0;
  }
}

// ── Main loop ─────────────────────────────────────────────────────────────────
function frame(realTime) {
  const w = window.innerWidth, h = window.innerHeight;
  CX = w * 0.42; CY = h * 0.5; SCALE = Math.min(w, h) * 0.95;
  const t = effectiveTime(realTime);

  drawBackground();
  drawOrbitalPaths(CX, CY, SCALE);
  drawEarth(CX, CY, SCALE);
  drawForecastPaths(CX, CY, SCALE);
  drawObjects(CX, CY, SCALE, t);

  if (simMode && !simPaused) {
    const elapsed = (realTime - simStartReal) * SIM_SPEED / 1000;
    const h_ = Math.floor(elapsed / 3600);
    const m_ = Math.floor((elapsed % 3600) / 60);
    const s_ = Math.floor(elapsed % 60);
    simTimeEl.textContent =
      "T+" + h_ + "h " + String(m_).padStart(2,"0") + "m " + String(s_).padStart(2,"0") + "s";
  }

  requestAnimationFrame(frame);
}

// ── Resize ────────────────────────────────────────────────────────────────────
function resize() {
  canvas.width  = window.innerWidth  * devicePixelRatio;
  canvas.height = window.innerHeight * devicePixelRatio;
  canvas.style.width  = window.innerWidth  + "px";
  canvas.style.height = window.innerHeight + "px";
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
}

window.addEventListener("resize", () => { resize(); initStars(320); });
resize();
initStars(320);
requestAnimationFrame(frame);

// ── Hit testing ───────────────────────────────────────────────────────────────
const HIT_RADIUS = 20;

function findObjectAt(mx, my) {
  let closest = -1, minD = HIT_RADIUS;
  objPositions.forEach((p, i) => {
    const d = Math.hypot(mx - p.x, my - p.y);
    if (d < minD) { minD = d; closest = i; }
  });
  return closest;
}

canvas.addEventListener("mousemove", e => {
  const r = canvas.getBoundingClientRect();
  hoveredIdx = findObjectAt(e.clientX - r.left, e.clientY - r.top);
  canvas.style.cursor = hoveredIdx >= 0 ? "pointer" : "default";
});

canvas.addEventListener("click", e => {
  const r = canvas.getBoundingClientRect();
  const idx = findObjectAt(e.clientX - r.left, e.clientY - r.top);
  if (idx >= 0) showObjectInfo(idx);
  else hideObjectInfo();
});

// ── Object info panel ─────────────────────────────────────────────────────────
function showObjectInfo(idx) {
  selectedIdx = idx;
  const p = objPositions[idx];
  const obj = OBJECTS[idx];
  const o = orbits[obj.orbit];

  const xn   = (p.x - CX) / SCALE;
  const yn   = (p.y - CY) / SCALE;
  const dist = Math.hypot(xn, yn);
  const az   = (Math.atan2(yn, xn) * 180 / Math.PI).toFixed(1);

  document.getElementById("obj-title").textContent    = "Object #" + (idx + 1);
  document.getElementById("obj-x").textContent        = (xn >= 0 ? "+" : "") + xn.toFixed(4) + " u";
  document.getElementById("obj-y").textContent        = (yn >= 0 ? "+" : "") + yn.toFixed(4) + " u";
  document.getElementById("obj-dist").textContent     = dist.toFixed(4) + " u";
  document.getElementById("obj-az").textContent       = az + "°";
  document.getElementById("obj-orbit").textContent    = "#" + (obj.orbit + 1);
  document.getElementById("obj-radius").textContent   = o.radius.toFixed(2) + " u";
  document.getElementById("obj-kind").textContent     = obj.kind;
  document.getElementById("obj-class").textContent    = "Loading…";
  document.getElementById("obj-conf").textContent     = "—";
  document.getElementById("conf-bar").style.width     = "0%";
  document.getElementById("obj-group-wrap").innerHTML = "";

  document.getElementById("form-view").style.display = "none";
  document.getElementById("obj-view").style.display  = "block";

  if (classCache[idx]) {
    applyClassification(idx);
  } else {
    fetch("/api/classify/" + idx)
      .then(r => r.json())
      .then(data => {
        classCache[idx] = data;
        if (selectedIdx === idx) applyClassification(idx);
      })
      .catch(() => {
        document.getElementById("obj-class").textContent = "unavailable";
      });
  }
}

function applyClassification(idx) {
  const c = classCache[idx];
  if (!c) return;
  document.getElementById("obj-class").textContent = c.class;
  document.getElementById("obj-conf").textContent  = (c.confidence * 100).toFixed(1) + "%";
  document.getElementById("conf-bar").style.width  = (c.confidence * 100).toFixed(1) + "%";
  const badgeClass = "badge-" + c.group;
  document.getElementById("obj-group-wrap").innerHTML =
    '<span class="obj-class-badge ' + badgeClass + '">' + c.group.replace("_", " ") + "</span>";
}

function hideObjectInfo() {
  selectedIdx = null;
  document.getElementById("obj-view").style.display  = "none";
  document.getElementById("form-view").style.display = "block";
}

// ── Forecast / play ───────────────────────────────────────────────────────────
async function fetchForecast() {
  const effTime = effectiveTime(performance.now());
  const payload = OBJECTS.map((obj, idx) => {
    const o = orbits[obj.orbit];
    const positions = [];
    for (let step = 7; step >= 0; step--) {
      const t = effTime - step * 400;
      const angle = obj.angle + t * o.speed * 1000;
      const rx = o.radius;
      const ry = o.radius * (1 - Math.abs(o.tilt) * 0.35);
      positions.push([Math.cos(angle) * rx, Math.sin(angle) * ry, t / 1000]);
    }
    return { id: idx, positions };
  });

  const resp = await fetch("/api/forecast", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ objects: payload }),
  });
  return resp.json();
}

const playBtn   = document.getElementById("play-btn");
const simTimeEl = document.getElementById("sim-time");

playBtn.addEventListener("click", async () => {
  if (forecasting) return;

  if (simMode && !simPaused) {
    simMode = false;
    simPaused = false;
    forecastPaths = null;
    playBtn.textContent = "▶ Play Simulation";
    playBtn.classList.remove("playing");
    simTimeEl.style.display = "none";
    return;
  }

  forecasting = true;
  playBtn.textContent = "⏳ Computing…";

  try {
    const result = await fetchForecast();
    forecastPaths = result.predictions;
  } catch (e) {
    forecastPaths = null;
  }

  simMode      = true;
  simPaused    = false;
  simStartReal = performance.now();
  forecasting  = false;
  playBtn.textContent = "⏹ Stop Simulation";
  playBtn.classList.add("playing");
  simTimeEl.style.display = "block";
  simTimeEl.textContent   = "T+0h 00m 00s";
});
