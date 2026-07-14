// ── Kind style map ────────────────────────────────────────────────────────────
const KIND_STYLES = {
  iss:               { size: 6,  color: "#4da3ff" },
  satellite:         { size: 3,  color: "#7ee787" },
  space_debris:      { size: 2,  color: "#ff6b6b" },
  rocket_body:       { size: 3,  color: "#ff9f43" },
  asteroid:          { size: 4,  color: "#ffd166" },
  comet:             { size: 4,  color: "#74b9ff" },
  near_earth_object: { size: 4,  color: "#ff7675" },
  meteor:            { size: 2,  color: "#fdcb6e" },
  meteoroid:         { size: 2,  color: "#e17055" },
  galaxy:            { size: 5,  color: "#a78bfa" },
  nebula:            { size: 5,  color: "#c084fc" },
  star_cluster:      { size: 4,  color: "#f0abfc" },
  variable_star:     { size: 3,  color: "#fbbf24" },
  ufo:               { size: 4,  color: "#00ff88" },
};

const KIND_NAMES = {
  iss:               "ISS",
  satellite:         "Satellite",
  space_debris:      "Space Debris",
  rocket_body:       "Rocket Body",
  asteroid:          "Asteroid",
  comet:             "Comet",
  near_earth_object: "Near-Earth Object",
  meteor:            "Meteor",
  meteoroid:         "Meteoroid",
  galaxy:            "Galaxy",
  nebula:            "Nebula",
  star_cluster:      "Star Cluster",
  variable_star:     "Variable Star",
  ufo:               "Unidentified \u{1F47D}",
};

// Decorative orbital guide rings (visual only, not tied to real orbits)
const orbits = [
  { radius: 0.14, tilt:  0.2  },
  { radius: 0.22, tilt: -0.15 },
  { radius: 0.31, tilt:  0.35 },
  { radius: 0.42, tilt: -0.25 },
];

// ── Canvas setup ──────────────────────────────────────────────────────────────
const canvas = document.getElementById("space-map");
const ctx    = canvas.getContext("2d");

const stars = [];
let CX = 0, CY = 0, SCALE = 1;

// ── Scene state ───────────────────────────────────────────────────────────────
let sceneObjects = [];       // [{id, name, kind, x_norm, y_norm, vx_norm, vy_norm, source}]
let objPositions = [];       // [{x, y}] world coords, updated each frame
let filterKind   = null;     // null = show all kinds
let hoveredIdx   = -1;
let selectedIdx  = null;
const classCache = {};

// ── Pan / zoom ────────────────────────────────────────────────────────────────
let panX = 0, panY = 0, zoom = 1;
let isDragging = false, dragMoved = false;
let dragAnchorX = 0, dragAnchorY = 0;

canvas.addEventListener("mousedown", e => {
  if (e.button !== 0) return;
  isDragging  = true;
  dragMoved   = false;
  dragAnchorX = e.clientX - panX;
  dragAnchorY = e.clientY - panY;
  canvas.style.cursor = "grabbing";
});

window.addEventListener("mousemove", e => {
  if (isDragging) {
    const nx = e.clientX - dragAnchorX;
    const ny = e.clientY - dragAnchorY;
    if (Math.abs(nx - panX) > 3 || Math.abs(ny - panY) > 3) dragMoved = true;
    panX = nx; panY = ny;
    return;
  }
  const r   = canvas.getBoundingClientRect();
  hoveredIdx = findObjectAt(e.clientX - r.left, e.clientY - r.top);
  canvas.style.cursor = hoveredIdx >= 0 ? "pointer" : "default";
});

window.addEventListener("mouseup", () => {
  isDragging = false;
  canvas.style.cursor = "default";
});

canvas.addEventListener("click", e => {
  if (dragMoved) return;
  const r   = canvas.getBoundingClientRect();
  const idx = findObjectAt(e.clientX - r.left, e.clientY - r.top);
  if (idx >= 0) showObjectInfo(idx);
  else hideObjectInfo();
});

canvas.addEventListener("wheel", e => {
  e.preventDefault();
  const r      = canvas.getBoundingClientRect();
  const mx     = e.clientX - r.left;
  const my     = e.clientY - r.top;
  const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
  const nz     = Math.max(0.15, Math.min(zoom * factor, 12));
  // zoom toward the mouse cursor
  panX = mx - (mx - panX) * (nz / zoom);
  panY = my - (my - panY) * (nz / zoom);
  zoom = nz;
}, { passive: false });

// ── Simulation state ──────────────────────────────────────────────────────────
const SIM_SPEED = 200;
let forecastPaths = null;
let forecasting   = false;
let simMode       = false;
let simPaused     = true;   // frozen by default
let simStartReal  = 0;
let simStartEff   = 0;

function effectiveTime(real) {
  if (!simMode || simPaused) return simStartEff;
  return simStartEff + (real - simStartReal) * SIM_SPEED;
}

// ── Load scene from API ───────────────────────────────────────────────────────
async function loadScene(datetimeISO) {
  updateLegendLoading(true);
  try {
    const qs   = datetimeISO ? "?datetime_str=" + encodeURIComponent(datetimeISO) : "";
    const resp = await fetch("/api/scene" + qs);
    const data = await resp.json();
    sceneObjects = data.objects || [];
  } catch {
    // keep whatever we had
  }
  objPositions = sceneObjects.map(() => ({ x: 0, y: 0 }));
  // clear stale caches
  for (const k in classCache) delete classCache[k];
  hoveredIdx  = -1;
  selectedIdx = null;
  hideObjectInfo();
  updateLegend();
}

// ── Legend (dynamic) ──────────────────────────────────────────────────────────
function updateLegendLoading(loading) {
  const ul = document.getElementById("legend-list");
  if (!loading) return;
  ul.innerHTML =
    '<li class="loading-note">Loading objects…</li>';
}

function updateLegend() {
  const ul = document.getElementById("legend-list");
  ul.innerHTML = "";

  // "All" filter
  const allLi = _legendItem(null, "◎", "#8eb4ff", "All Objects", sceneObjects.length);
  allLi.classList.add("filter-all");
  if (filterKind === null) allLi.classList.add("active");
  allLi.addEventListener("click", () => { filterKind = null; updateLegend(); });
  ul.appendChild(allLi);

  // Decorative separators
  ul.appendChild(_staticItem("earth", "Earth (center)"));
  ul.appendChild(_staticItem("orbit", "Orbital paths"));

  // Kind rows — only for kinds actually in the current scene
  const counts = {};
  for (const o of sceneObjects) counts[o.kind] = (counts[o.kind] || 0) + 1;

  for (const [kind, style] of Object.entries(KIND_STYLES)) {
    if (!counts[kind]) continue;
    const li = _legendItem(kind, "●", style.color, KIND_NAMES[kind] || kind, counts[kind]);
    li.classList.add("kind-filter");
    if (filterKind === kind) li.classList.add("active");
    li.addEventListener("click", () => {
      filterKind = filterKind === kind ? null : kind;
      // deselect if the selected object is now hidden
      if (selectedIdx !== null && filterKind !== null &&
          sceneObjects[selectedIdx]?.kind !== filterKind) {
        hideObjectInfo();
      }
      updateLegend();
    });
    ul.appendChild(li);
  }
}

function _legendItem(kind, bullet, color, label, count) {
  const li   = document.createElement("li");
  if (kind) li.dataset.kind = kind;
  const dot  = document.createElement("span");
  dot.textContent = bullet + " ";
  dot.style.color = color;
  li.appendChild(dot);
  li.appendChild(document.createTextNode(label + " "));
  const cnt  = document.createElement("span");
  cnt.className   = "count";
  cnt.textContent = "(" + count + ")";
  li.appendChild(cnt);
  return li;
}

function _staticItem(cls, text) {
  const li = document.createElement("li");
  li.className   = cls;
  li.textContent = text;
  return li;
}

// ── Stars & backdrop ──────────────────────────────────────────────────────────
// Star colours span the stellar temperature range (blue-white → yellow/orange)
// so the field reads as real starlight, not flat grey.
const STAR_COLORS = ["#ffffff", "#dbe6ff", "#cfe0ff", "#ffe6c0", "#ffcda0"];

// The static sky (gradient, nebulae, Milky Way, faint stars) is pre-rendered once
// per resize into an offscreen canvas and blitted each frame; only the brighter
// foreground stars twinkle live. Cheap, and smooth.
const backdrop = document.createElement("canvas");
const bctx = backdrop.getContext("2d");

function hexA(hex, a) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

function buildBackdrop(w, h) {
  backdrop.width = w;
  backdrop.height = h;
  const b = bctx;

  // Deep-space gradient.
  const g = b.createRadialGradient(w * .5, h * .42, 0, w * .5, h * .42, Math.max(w, h) * .8);
  g.addColorStop(0, "#0b1230");
  g.addColorStop(0.5, "#050817");
  g.addColorStop(1, "#010208");
  b.fillStyle = g;
  b.fillRect(0, 0, w, h);

  // Faint diagonal Milky Way band.
  b.save();
  b.translate(w * .5, h * .5);
  b.rotate(-0.5);
  const mw = b.createLinearGradient(0, -h * .22, 0, h * .22);
  mw.addColorStop(0, "rgba(130,150,225,0)");
  mw.addColorStop(0.5, "rgba(150,165,235,0.10)");
  mw.addColorStop(1, "rgba(130,150,225,0)");
  b.fillStyle = mw;
  b.fillRect(-w, -h * .22, w * 2, h * .44);
  b.restore();

  // Coloured nebula clouds for depth.
  const clouds = [
    { x: .22, y: .30, r: .42, c: "rgba(80,60,165,0.18)" },
    { x: .78, y: .62, r: .50, c: "rgba(40,95,155,0.16)" },
    { x: .55, y: .18, r: .34, c: "rgba(150,55,120,0.10)" },
  ];
  for (const c of clouds) {
    const rg = b.createRadialGradient(c.x * w, c.y * h, 0, c.x * w, c.y * h, c.r * Math.max(w, h));
    rg.addColorStop(0, c.c);
    rg.addColorStop(1, "rgba(0,0,0,0)");
    b.fillStyle = rg;
    b.fillRect(0, 0, w, h);
  }

  // Dense field of faint background stars.
  const count = Math.floor(w * h / 1400);
  for (let i = 0; i < count; i++) {
    b.fillStyle = `rgba(210,224,255,${0.15 + Math.random() * 0.5})`;
    b.beginPath();
    b.arc(Math.random() * w, Math.random() * h, Math.random() * 0.9 + 0.2, 0, Math.PI * 2);
    b.fill();
  }
}

function initStars(n) {
  stars.length = 0;
  for (let i = 0; i < n; i++) {
    stars.push({
      x: Math.random(), y: Math.random(),
      r: Math.random() * 1.3 + 0.5,
      tw: Math.random() * Math.PI * 2,
      sp: 0.008 + Math.random() * 0.02,
      color: STAR_COLORS[(Math.random() * STAR_COLORS.length) | 0],
      glint: Math.random() < 0.1,
    });
  }
}

// ── Draw helpers ──────────────────────────────────────────────────────────────
function drawBackground() {
  const w = window.innerWidth, h = window.innerHeight;
  ctx.drawImage(backdrop, 0, 0, w, h);

  for (const s of stars) {
    const tw    = 0.5 + 0.5 * Math.sin(s.tw);
    const alpha = 0.45 + 0.55 * tw;
    const x = s.x * w, y = s.y * h, r = s.r * (0.8 + 0.4 * tw);

    // Brighter stars get a soft halo.
    if (s.r > 1.1) {
      const gr = ctx.createRadialGradient(x, y, 0, x, y, r * 4);
      gr.addColorStop(0, hexA(s.color, alpha * 0.5));
      gr.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = gr;
      ctx.beginPath(); ctx.arc(x, y, r * 4, 0, Math.PI * 2); ctx.fill();
    }

    ctx.fillStyle = hexA(s.color, alpha);
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();

    // A few stars get a subtle diffraction glint.
    if (s.glint) {
      ctx.strokeStyle = hexA(s.color, alpha * 0.5);
      ctx.lineWidth = 0.6;
      ctx.beginPath();
      ctx.moveTo(x - r * 3, y); ctx.lineTo(x + r * 3, y);
      ctx.moveTo(x, y - r * 3); ctx.lineTo(x, y + r * 3);
      ctx.stroke();
    }
    s.tw += s.sp;
  }
}

function drawEarth(cx, cy, scale) {
  const r = scale * 0.045;

  // Outer atmosphere glow.
  const glow = ctx.createRadialGradient(cx, cy, r * .9, cx, cy, r * 2.6);
  glow.addColorStop(0, "rgba(90,170,255,0.35)");
  glow.addColorStop(0.5, "rgba(70,140,255,0.12)");
  glow.addColorStop(1, "rgba(70,140,255,0)");
  ctx.fillStyle = glow;
  ctx.beginPath(); ctx.arc(cx, cy, r * 2.6, 0, Math.PI * 2); ctx.fill();

  // Ocean base, lit from the upper-left.
  const eg = ctx.createRadialGradient(cx - r * .35, cy - r * .35, r * .15, cx, cy, r);
  eg.addColorStop(0, "#8fd0ff"); eg.addColorStop(0.5, "#2f74c0"); eg.addColorStop(1, "#0a2038");
  ctx.fillStyle = eg;
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();

  // Surface detail, clipped to the globe.
  ctx.save();
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.clip();

  // Continent hints.
  ctx.fillStyle = "rgba(70,130,80,0.55)";
  for (const [dx, dy, rr] of [[-.3, -.2, .45], [.25, .05, .5], [-.05, .35, .4], [.4, -.35, .3]]) {
    ctx.beginPath();
    ctx.ellipse(cx + dx * r, cy + dy * r, rr * r, rr * r * 0.7, dx, 0, Math.PI * 2);
    ctx.fill();
  }

  // Day/night terminator — darken away from the sunlit side.
  const term = ctx.createRadialGradient(cx - r * .5, cy - r * .5, r * .2, cx + r * .6, cy + r * .6, r * 1.8);
  term.addColorStop(0, "rgba(2,6,16,0)");
  term.addColorStop(0.6, "rgba(2,6,16,0.15)");
  term.addColorStop(1, "rgba(2,6,16,0.8)");
  ctx.fillStyle = term;
  ctx.fillRect(cx - r, cy - r, r * 2, r * 2);

  // Specular highlight.
  const spec = ctx.createRadialGradient(cx - r * .4, cy - r * .45, 0, cx - r * .4, cy - r * .45, r * .5);
  spec.addColorStop(0, "rgba(255,255,255,0.5)");
  spec.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = spec;
  ctx.beginPath(); ctx.arc(cx - r * .4, cy - r * .45, r * .5, 0, Math.PI * 2); ctx.fill();
  ctx.restore();

  // Thin bright atmosphere rim.
  const rim = ctx.createRadialGradient(cx, cy, r * .92, cx, cy, r * 1.06);
  rim.addColorStop(0, "rgba(150,210,255,0)");
  rim.addColorStop(0.6, "rgba(150,210,255,0.35)");
  rim.addColorStop(1, "rgba(150,210,255,0)");
  ctx.fillStyle = rim;
  ctx.beginPath(); ctx.arc(cx, cy, r * 1.06, 0, Math.PI * 2); ctx.fill();
}

function drawOrbitalPaths(cx, cy, scale) {
  for (const o of orbits) {
    const rx = scale * o.radius;
    const ry = scale * o.radius * (1 - Math.abs(o.tilt) * 0.35);
    ctx.strokeStyle = "rgba(120,170,255,0.15)"; ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx, ry, o.tilt, 0, Math.PI*2);
    ctx.stroke();
  }
}

function drawForecastPaths(cx, cy, scale) {
  if (!forecastPaths) return;
  ctx.save();
  ctx.setLineDash([5, 8]);
  ctx.lineWidth = 1.5;
  for (const p of forecastPaths) {
    const obj = sceneObjects[p.id];
    if (!obj) continue;
    if (filterKind && obj.kind !== filterKind) continue;
    const style = KIND_STYLES[obj.kind] || { color: "#e2e8f0" };
    ctx.globalAlpha = 0.45;
    ctx.strokeStyle = style.color;
    ctx.beginPath();
    let first = true;
    for (const [xn, yn] of p.waypoints) {
      const px = cx + xn * scale, py = cy + yn * scale;
      if (first) { ctx.moveTo(px, py); first = false; }
      else ctx.lineTo(px, py);
    }
    ctx.stroke();
    if (p.waypoints.length > 0) {
      const [xn, yn] = p.waypoints[p.waypoints.length - 1];
      ctx.globalAlpha = 0.7;
      ctx.fillStyle = style.color;
      ctx.shadowColor = style.color; ctx.shadowBlur = 6;
      ctx.beginPath(); ctx.arc(cx + xn * scale, cy + yn * scale, 3, 0, Math.PI*2);
      ctx.fill(); ctx.shadowBlur = 0;
    }
  }
  ctx.setLineDash([]);
  ctx.globalAlpha = 1;
  ctx.restore();
}

function drawSceneObjects(cx, cy, scale, realTime) {
  // How far has simulation advanced (in real seconds of object physics)?
  const simElapsedS = (simMode && !simPaused)
    ? (effectiveTime(realTime) - simStartEff) / 1000
    : 0;

  for (let i = 0; i < sceneObjects.length; i++) {
    const obj   = sceneObjects[i];
    const style = KIND_STYLES[obj.kind] || { size: 3, color: "#e2e8f0" };

    if (filterKind && obj.kind !== filterKind) {
      objPositions[i] = { x: -9999, y: -9999 }; // off-screen so hit test skips
      continue;
    }

    const wx = cx + (obj.x_norm + (obj.vx_norm || 0) * simElapsedS) * scale;
    const wy = cy + (obj.y_norm + (obj.vy_norm || 0) * simElapsedS) * scale;
    objPositions[i] = { x: wx, y: wy };

    if (i === selectedIdx) {
      ctx.strokeStyle = style.color; ctx.lineWidth = 1.5; ctx.globalAlpha = 0.75;
      ctx.beginPath(); ctx.arc(wx, wy, style.size + 7, 0, Math.PI*2); ctx.stroke();
      ctx.globalAlpha = 1;
    }
    if (i === hoveredIdx && i !== selectedIdx) {
      ctx.strokeStyle = "#fff"; ctx.lineWidth = 1; ctx.globalAlpha = 0.35;
      ctx.beginPath(); ctx.arc(wx, wy, style.size + 6, 0, Math.PI*2); ctx.stroke();
      ctx.globalAlpha = 1;
    }

    ctx.fillStyle   = style.color;
    ctx.shadowColor = style.color; ctx.shadowBlur = 8;
    ctx.beginPath(); ctx.arc(wx, wy, style.size, 0, Math.PI*2); ctx.fill();
    ctx.shadowBlur  = 0;
  }
}

// ── Main loop ─────────────────────────────────────────────────────────────────
function frame(realTime) {
  const w = window.innerWidth, h = window.innerHeight;
  CX = w * 0.42; CY = h * 0.5; SCALE = Math.min(w, h) * 0.95;

  // Background — no transform (stars are screen-fixed)
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  drawBackground();

  // Scene — pan/zoom applied on top of DPR
  ctx.save();
  ctx.translate(panX, panY);
  ctx.scale(zoom, zoom);
  drawOrbitalPaths(CX, CY, SCALE);
  drawEarth(CX, CY, SCALE);
  drawForecastPaths(CX, CY, SCALE);
  drawSceneObjects(CX, CY, SCALE, realTime);
  ctx.restore();

  // Time HUD
  if (simMode && !simPaused) {
    const elapsed = (realTime - simStartReal) * SIM_SPEED / 1000;
    const hh = Math.floor(elapsed / 3600);
    const mm = Math.floor((elapsed % 3600) / 60);
    const ss = Math.floor(elapsed % 60);
    simTimeEl.textContent =
      "T+" + hh + "h " + String(mm).padStart(2, "0") + "m " + String(ss).padStart(2, "0") + "s";
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
  buildBackdrop(window.innerWidth, window.innerHeight);
}

window.addEventListener("resize", () => { resize(); initStars(320); });
resize();
initStars(320);
requestAnimationFrame(frame);

// ── Hit testing ───────────────────────────────────────────────────────────────
const HIT_RADIUS = 20;

function findObjectAt(sx, sy) {
  // Convert screen coords → world coords (inverse pan/zoom)
  const wx   = (sx - panX) / zoom;
  const wy   = (sy - panY) / zoom;
  const hitR = HIT_RADIUS / zoom;
  let closest = -1, minD = hitR;
  for (let i = 0; i < sceneObjects.length; i++) {
    if (filterKind && sceneObjects[i].kind !== filterKind) continue;
    const p = objPositions[i];
    if (!p) continue;
    const d = Math.hypot(wx - p.x, wy - p.y);
    if (d < minD) { minD = d; closest = i; }
  }
  return closest;
}

// ── Object info panel ─────────────────────────────────────────────────────────
function showObjectInfo(idx) {
  selectedIdx = idx;
  const obj   = sceneObjects[idx];
  if (!obj) return;

  const xn   = obj.x_norm;
  const yn   = obj.y_norm;
  const dist = Math.hypot(xn, yn);
  const az   = (Math.atan2(yn, xn) * 180 / Math.PI).toFixed(1);
  const speed = Math.hypot(obj.vx_norm || 0, obj.vy_norm || 0);

  document.getElementById("obj-title").textContent  = obj.name || ("Object #" + (idx + 1));
  document.getElementById("obj-x").textContent      = (xn >= 0 ? "+" : "") + xn.toFixed(4) + " u";
  document.getElementById("obj-y").textContent      = (yn >= 0 ? "+" : "") + yn.toFixed(4) + " u";
  document.getElementById("obj-dist").textContent   = dist.toFixed(4) + " u";
  document.getElementById("obj-az").textContent     = az + "°";
  document.getElementById("obj-orbit").textContent  = obj.source || "—";
  document.getElementById("obj-radius").textContent = speed > 0
    ? (speed * 42164).toFixed(2) + " km/s" : "—";
  document.getElementById("obj-kind").textContent   = KIND_NAMES[obj.kind] || obj.kind;
  document.getElementById("obj-class").textContent  = "Loading…";
  document.getElementById("obj-conf").textContent   = "—";
  document.getElementById("conf-bar").style.width   = "0%";
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
  const badgeClass = "badge-" + (c.group || "unknown");
  document.getElementById("obj-group-wrap").innerHTML =
    '<span class="obj-class-badge ' + badgeClass + '">' +
    (c.group || "unknown").replace("_", " ") + "</span>";
}

function hideObjectInfo() {
  selectedIdx = null;
  document.getElementById("obj-view").style.display  = "none";
  document.getElementById("form-view").style.display = "block";
}

// ── Forecast / play ───────────────────────────────────────────────────────────
async function fetchForecast() {
  const payload = sceneObjects
    .map((obj, idx) => {
      if (filterKind && obj.kind !== filterKind) return null;
      const positions = Array.from({ length: 8 }, (_, step) => {
        const dtS = -(7 - step) * 400 / 1000; // seconds before base
        return [
          obj.x_norm + (obj.vx_norm || 0) * dtS,
          obj.y_norm + (obj.vy_norm || 0) * dtS,
          simStartEff / 1000 + dtS,
        ];
      });
      return { id: idx, positions };
    })
    .filter(Boolean);

  const resp = await fetch("/api/forecast", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ objects: payload }),
  });
  return resp.json();
}

const playBtn   = document.getElementById("play-btn");
const simTimeEl = document.getElementById("sim-time");

playBtn.addEventListener("click", async () => {
  if (forecasting) return;

  if (simMode && !simPaused) {
    // Stop
    simMode   = false;
    simPaused = true;
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
  } catch {
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

// ── Form: load scene ──────────────────────────────────────────────────────────
document.getElementById("scene-form").addEventListener("submit", function (e) {
  e.preventDefault();

  const ra          = document.getElementById("ra").value.trim();
  const dec         = document.getElementById("dec").value.trim();
  const obsDatetime = document.getElementById("obs_datetime").value; // YYYY-MM-DDTHH:MM

  const dtISO = obsDatetime ? obsDatetime + ":00Z" : new Date().toISOString();
  const ts    = new Date(dtISO).getTime();

  // Reset simulation to frozen at this moment
  simMode      = true;
  simPaused    = true;
  simStartReal = performance.now();
  simStartEff  = ts;
  forecastPaths = null;

  playBtn.textContent = "▶ Play Simulation";
  playBtn.classList.remove("playing");
  simTimeEl.style.display = "block";
  simTimeEl.textContent   = "Paused — " + (obsDatetime || dtISO.slice(0, 16)).replace("T", " ");

  const html = ra && dec
    ? '<div class="results">' +
        '<h3>Loaded Scene</h3>' +
        '<p>RA: ' + esc(ra) + ' &nbsp; Dec: ' + esc(dec) + '</p>' +
        '<p>Time: ' + esc(obsDatetime || "") + ' UTC</p>' +
        '<p style="margin-top:0.5rem;color:#7a9acc;font-size:0.82rem;">' +
          'Scene paused. Press &#9654; Play to simulate forward.' +
        '</p>' +
      '</div>'
    : '';
  document.getElementById("scene-result").innerHTML = html;

  loadScene(dtISO);
});

function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ── Image upload classifier ───────────────────────────────────────────────────
const uploadZone    = document.getElementById("upload-zone");
const imgUploadEl   = document.getElementById("img-upload");
const uploadResult  = document.getElementById("upload-result");
const uploadPreview = document.getElementById("upload-preview");

uploadZone.addEventListener("click", () => imgUploadEl.click());

uploadZone.addEventListener("dragover", e => {
  e.preventDefault();
  uploadZone.classList.add("drag-over");
});
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("drag-over"));
uploadZone.addEventListener("drop", e => {
  e.preventDefault();
  uploadZone.classList.remove("drag-over");
  const file = e.dataTransfer?.files?.[0];
  if (file && file.type.startsWith("image/")) classifyUploadFile(file);
});

imgUploadEl.addEventListener("change", () => {
  const file = imgUploadEl.files?.[0];
  if (file) classifyUploadFile(file);
});

async function classifyUploadFile(file) {
  // Show preview immediately
  const reader = new FileReader();
  reader.onload = e => { uploadPreview.src = e.target.result; };
  reader.readAsDataURL(file);

  uploadResult.style.display = "block";
  document.getElementById("upload-class-name").textContent = "Classifying…";
  document.getElementById("upload-group-wrap").innerHTML   = "";
  document.getElementById("upload-conf-pct").textContent   = "—";
  document.getElementById("upload-conf-bar").style.width   = "0%";

  try {
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch("/api/classify/upload", { method: "POST", body: form });
    const data = await resp.json();

    document.getElementById("upload-class-name").textContent = data.class || "Unknown";
    document.getElementById("upload-conf-pct").textContent   =
      (data.confidence * 100).toFixed(1) + "%";
    document.getElementById("upload-conf-bar").style.width   =
      (data.confidence * 100).toFixed(1) + "%";
    const badgeClass = "badge-" + (data.group || "unknown");
    document.getElementById("upload-group-wrap").innerHTML =
      '<span class="obj-class-badge ' + badgeClass + '">' +
      (data.group || "unknown").replace("_", " ") + "</span>";
  } catch {
    document.getElementById("upload-class-name").textContent = "Classification failed";
  }
}

// ── CSV upload ────────────────────────────────────────────────────────────────
const CSV_TEMPLATE = [
  "id,name,kind,x,y,timestamp",
  "OBJ001,My Satellite,satellite,0.120,-0.050,1704067200",
  "OBJ001,My Satellite,satellite,0.130,-0.060,1704068200",
  "OBJ001,My Satellite,satellite,0.140,-0.070,1704069200",
  "OBJ002,Unknown Object,ufo,0.280,-0.200,1704067200",
  "OBJ002,Unknown Object,ufo,0.285,-0.205,1704068200",
  "OBJ002,Unknown Object,ufo,0.290,-0.210,1704069200",
].join("\n");

document.getElementById("csv-template-link").addEventListener("click", e => {
  e.preventDefault();
  const blob = new Blob([CSV_TEMPLATE], { type: "text/csv" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href = url; a.download = "cosmic_forecast_template.csv";
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
});

const csvZone    = document.getElementById("csv-zone");
const csvUpload  = document.getElementById("csv-upload");
const csvResult  = document.getElementById("csv-result");

csvZone.addEventListener("click", () => csvUpload.click());
csvZone.addEventListener("dragover", e => { e.preventDefault(); csvZone.classList.add("drag-over"); });
csvZone.addEventListener("dragleave", () => csvZone.classList.remove("drag-over"));
csvZone.addEventListener("drop", e => {
  e.preventDefault(); csvZone.classList.remove("drag-over");
  const f = e.dataTransfer?.files?.[0];
  if (f) handleCSVUpload(f);
});
csvUpload.addEventListener("change", () => {
  const f = csvUpload.files?.[0];
  if (f) handleCSVUpload(f);
});

async function handleCSVUpload(file) {
  csvResult.className    = "csv-status";
  csvResult.style.display = "block";
  csvResult.textContent  = "Parsing…";

  try {
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch("/api/upload/csv", { method: "POST", body: form });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || resp.statusText);
    }

    const data = await resp.json();
    const n    = data.objects?.length ?? 0;
    const p    = data.predictions?.length ?? 0;

    if (n === 0) throw new Error("No valid objects found — check that each id has ≥ 2 rows.");

    // Replace scene with uploaded objects
    sceneObjects  = data.objects;
    objPositions  = sceneObjects.map(() => ({ x: 0, y: 0 }));
    forecastPaths = data.predictions;
    for (const k in classCache) delete classCache[k];
    hoveredIdx  = -1;
    selectedIdx = null;
    hideObjectInfo();
    filterKind = null;
    updateLegend();

    // Freeze at latest timestamp from the data
    simMode      = true;
    simPaused    = true;
    simStartReal = performance.now();
    simStartEff  = Date.now();
    playBtn.textContent = "▶ Play Simulation";
    playBtn.classList.remove("playing");
    simTimeEl.style.display = "block";
    simTimeEl.textContent   = "Paused — " + n + " objects loaded";

    csvResult.className   = "csv-status success";
    csvResult.textContent = `✓ ${n} object${n === 1 ? "" : "s"} loaded, ${p} path${p === 1 ? "" : "s"} predicted. Press ▶ to simulate.`;
  } catch (err) {
    csvResult.className   = "csv-status error";
    csvResult.textContent = "✗ " + err.message;
  }
}

// ── Auto-load on page start ───────────────────────────────────────────────────
(function init() {
  const now   = new Date();
  // Format local time as YYYY-MM-DDTHH:MM for the input field
  const local = new Date(now - now.getTimezoneOffset() * 60000);
  document.getElementById("obs_datetime").value = local.toISOString().slice(0, 16);

  simMode      = true;
  simPaused    = true;
  simStartReal = performance.now();
  simStartEff  = now.getTime();
  simTimeEl.style.display = "block";
  simTimeEl.textContent   = "Paused — " + local.toISOString().slice(0, 16).replace("T", " ");

  loadScene(now.toISOString());
})();

// ── Testing interface (no-op in browser where `module` is undefined) ──────────
if (typeof module !== "undefined") {
  module.exports = {
    // Constants
    KIND_STYLES, KIND_NAMES, CSV_TEMPLATE, SIM_SPEED, HIT_RADIUS,
    // Stateless pure functions
    esc,
    effectiveTime,
    findObjectAt,
    // Async handlers
    loadScene, handleCSVUpload, classifyUploadFile,
    updateLegend, hideObjectInfo, showObjectInfo,
    // Mutable state (getters/setters so tests can read and write the closure vars)
    get filterKind()    { return filterKind; },
    set filterKind(v)   { filterKind = v; },
    get sceneObjects()  { return sceneObjects; },
    set sceneObjects(v) { sceneObjects = v; objPositions = v.map(() => ({ x: 0, y: 0 })); },
    get objPositions()  { return objPositions; },
    set objPositions(v) { objPositions = v; },
    get panX()          { return panX; },
    set panX(v)         { panX = v; },
    get panY()          { return panY; },
    set panY(v)         { panY = v; },
    get zoom()          { return zoom; },
    set zoom(v)         { zoom = v; },
    get simMode()       { return simMode; },
    set simMode(v)      { simMode = v; },
    get simPaused()     { return simPaused; },
    set simPaused(v)    { simPaused = v; },
    get simStartReal()  { return simStartReal; },
    set simStartReal(v) { simStartReal = v; },
    get simStartEff()   { return simStartEff; },
    set simStartEff(v)  { simStartEff = v; },
    get forecastPaths() { return forecastPaths; },
    set forecastPaths(v){ forecastPaths = v; },
  };
}
