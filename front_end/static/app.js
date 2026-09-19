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
  star:              { size: 3,  color: "#fde68a" },
  black_hole:        { size: 5,  color: "#7c3aed" },
  quasar:            { size: 4,  color: "#22d3ee" },
  pulsar:            { size: 3,  color: "#f472b6" },
  supernova_remnant: { size: 5,  color: "#fb7185" },
  planet:            { size: 8,  color: "#e8c89a" },
  sun:               { size: 10, color: "#ffcf5a" },
  earth:             { size: 9,  color: "#5aa9ff" },
  moon:              { size: 6,  color: "#cfd2dc" },
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
  star:              "Star",
  black_hole:        "Black Hole \u{1F573}",
  quasar:            "Quasar",
  pulsar:            "Pulsar",
  supernova_remnant: "Supernova Remnant",
  planet:            "Planet",
  sun:               "Sun \u{2600}",
  earth:             "Earth \u{1F30D}",
  moon:              "Moon \u{1F311}",
  ufo:               "Unidentified \u{1F47D}",
};

// One-line fact shown in the detail panel. Solar-system bodies (Sun/Earth/Moon
// and the named planets) carry their own per-object description from the scene,
// which takes precedence; this is the per-kind fallback for everything else.
const KIND_FACTS = {
  iss:               "A crewed space station orbiting ~400 km up, circling Earth roughly every 90 minutes.",
  satellite:         "An artificial object placed in orbit for communication, navigation, imaging, or research.",
  space_debris:      "Defunct human-made fragments — spent stages, dead satellites, collision shards — still in orbit.",
  rocket_body:       "A spent rocket stage left in orbit after delivering its payload.",
  asteroid:          "A rocky remnant of the early solar system, most orbiting between Mars and Jupiter.",
  comet:             "An icy body that grows a glowing coma and tail when the Sun's heat vaporizes its surface.",
  near_earth_object: "An asteroid or comet whose orbit brings it close to Earth's neighborhood.",
  meteor:            "The streak of light from a small particle burning up in Earth's atmosphere.",
  meteoroid:         "A small rock or metal fragment traveling through space, smaller than an asteroid.",
  galaxy:            "A gravitationally bound system of billions of stars, gas, dust, and dark matter.",
  nebula:            "A vast cloud of gas and dust — often a stellar nursery or the remains of a dying star.",
  star_cluster:      "A group of stars born from the same cloud and held together by gravity.",
  variable_star:     "A star whose brightness changes over time — from pulsation, eclipses, or eruptions.",
  star:              "A luminous sphere of plasma held together by gravity and powered by nuclear fusion.",
  black_hole:        "A region where gravity is so strong that not even light can escape.",
  quasar:            "The blazing core of a distant galaxy, powered by a supermassive black hole devouring matter.",
  pulsar:            "A rapidly spinning neutron star sweeping beams of radiation past Earth like a lighthouse.",
  supernova_remnant: "The expanding shell of gas and dust left behind by a stellar explosion.",
  planet:            "A world orbiting the Sun, round under its own gravity and clearing its orbital path.",
  sun:               "The star at the center of the solar system, powering light and life on Earth.",
  earth:             "Our home planet — the only known world with liquid-water oceans and life.",
  moon:              "Earth's only natural satellite, whose gravity drives the ocean tides.",
  ufo:               "An object with no catalogued match — origin unknown.",
};

// Per-kind "learn more" link, pointing at the authoritative NASA page for that
// class of object. Shown alongside the fact in the detail panel.
const KIND_LINKS = {
  iss:               "https://www.nasa.gov/international-space-station/",
  satellite:         "https://www.nasa.gov/learning-resources/for-kids-and-students/what-is-a-satellite-grades-5-8/",
  space_debris:      "https://orbitaldebris.jsc.nasa.gov/",
  rocket_body:       "https://orbitaldebris.jsc.nasa.gov/",
  asteroid:          "https://science.nasa.gov/solar-system/asteroids/",
  comet:             "https://science.nasa.gov/solar-system/comets/",
  near_earth_object: "https://science.nasa.gov/planetary-defense/",
  meteor:            "https://science.nasa.gov/solar-system/meteors-meteorites/",
  meteoroid:         "https://science.nasa.gov/solar-system/meteors-meteorites/",
  galaxy:            "https://science.nasa.gov/universe/galaxies/",
  nebula:            "https://science.nasa.gov/universe/",
  star_cluster:      "https://science.nasa.gov/universe/stars/",
  variable_star:     "https://science.nasa.gov/universe/stars/types/",
  star:              "https://science.nasa.gov/universe/stars/",
  black_hole:        "https://science.nasa.gov/universe/black-holes/",
  quasar:            "https://science.nasa.gov/universe/black-holes/",
  pulsar:            "https://science.nasa.gov/universe/stars/types/",
  supernova_remnant: "https://science.nasa.gov/universe/stars/",
  planet:            "https://science.nasa.gov/solar-system/planets/",
  sun:               "https://science.nasa.gov/sun/",
  earth:             "https://science.nasa.gov/earth/",
  moon:              "https://science.nasa.gov/moon/",
  ufo:               "https://science.nasa.gov/uap/",
};

const DEBRIS_FIELD_NAMES = {
  "cosmos-2251": "Cosmos 2251",
  "iridium-33": "Iridium 33",
  "fengyun-1c": "Fengyun 1C",
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
let objTrails = [];          // [[{x, y}, …]] recent positions per object (motion trails)
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

// Framing a position search: without this a 10° search leaves a handful of
// objects scattered across the full-sky map with no hint of where to look.
const FOCUS_MARGIN   = 0.25; // fraction of the viewport kept as padding
const FOCUS_MIN_SPAN = 0.08; // scene units; stops one object zooming to the max
const ZOOM_MIN = 0.15, ZOOM_MAX = 12; // same clamps the wheel handler uses

function resetView() {
  panX = 0; panY = 0; zoom = 1;
}

// Zoom and pan so `objects` fill the viewport. Returns false when there is
// nothing to frame, or before the first frame has sized the scene.
function focusOnObjects(objects) {
  if (!objects || !objects.length || !SCALE) return false;

  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const obj of objects) {
    minX = Math.min(minX, obj.x_norm); maxX = Math.max(maxX, obj.x_norm);
    minY = Math.min(minY, obj.y_norm); maxY = Math.max(maxY, obj.y_norm);
  }

  const w = window.innerWidth, h = window.innerHeight;
  const spanX = Math.max(maxX - minX, FOCUS_MIN_SPAN);
  const spanY = Math.max(maxY - minY, FOCUS_MIN_SPAN);
  const fit   = Math.min(w / (spanX * SCALE), h / (spanY * SCALE)) * (1 - FOCUS_MARGIN);

  zoom = Math.max(ZOOM_MIN, Math.min(fit, ZOOM_MAX));
  panX = w / 2 - (CX + ((minX + maxX) / 2) * SCALE) * zoom;
  panY = h / 2 - (CY + ((minY + maxY) / 2) * SCALE) * zoom;
  return true;
}

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
// ── User-added objects ──────────────────────────────────────────────────────
// Distance presets map to the scene's radial bands (Earth 0 → deep sky ~0.95).
const DISTANCE_BANDS = {
  "Low orbit (LEO)": 0.12,
  "Geostationary": 0.21,
  "Moon distance": 0.34,
  "Inner planets": 0.68,
  "Outer planets": 0.85,
  "Deep sky": 0.95,
};

// Scene x/y for a distance band + real right ascension (degrees).
function customObjectXY(bandLabel, raDeg) {
  const radius = DISTANCE_BANDS[bandLabel] ?? 0.5;
  const ra = (Number(raDeg) || 0) * Math.PI / 180;
  return { x: radius * Math.cos(ra), y: radius * Math.sin(ra) };
}

// Append an object to the live scene (and keep objPositions in step).
function addToScene(obj) {
  sceneObjects.push(obj);
  objPositions.push({ x: 0, y: 0 });
  updateLegend();
}

function _token() {
  try { return localStorage.getItem(window.COSMIC.TOKEN_KEY); } catch { return null; }
}

// Merge the signed-in user's saved custom objects into the scene.
async function mergeCustomObjects() {
  const token = _token();
  if (!token) return;
  try {
    const r = await fetch("/api/custom-objects", {
      headers: { Authorization: "Bearer " + token },
    });
    if (!r.ok) return;
    const data = await r.json();
    for (const o of (data.objects || [])) {
      sceneObjects.push({
        ...o, source: "custom", vx_norm: 0, vy_norm: 0, speed_kms: 0,
      });
    }
  } catch { /* offline — skip */ }
}

async function persistCustomObject(name, kind, x, y) {
  const token = _token();
  if (!token) return;
  try {
    await fetch("/api/custom-objects", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
      body: JSON.stringify({ name, kind, x_norm: x, y_norm: y }),
    });
  } catch { /* offline — object still shows this session */ }
}

// Returns {ok, count, search, invalid, error}. On failure the previous scene
// stays on screen, which would otherwise look like a successful load of the
// wrong moment. `invalid` marks rejected input (bad coordinates) as opposed to
// a source being unreachable — the two need different messages.
async function loadScene(datetimeISO, search) {
  updateLegendLoading(true);
  let ok = false;
  let matched = null;
  let debrisCoverage = null;
  let satelliteCoverage = null;
  let rocketBodyCoverage = null;
  let invalid = false;
  let error = null;
  try {
    const params = new URLSearchParams();
    if (datetimeISO) params.set("datetime_str", datetimeISO);
    const debrisField = document.getElementById("debris-field");
    if (debrisField) params.set("debris_field", debrisField.value);
    // Both coordinates or neither — the API rejects half a position search.
    if (search && search.ra && search.dec) {
      params.set("ra", search.ra);
      params.set("dec", search.dec);
    }
    const qs   = params.toString();
    const resp = await fetch("/api/scene" + (qs ? "?" + qs : ""));
    if (!resp.ok) {
      // 4xx is the server rejecting what was typed; report what it said.
      invalid = resp.status >= 400 && resp.status < 500;
      error   = invalid ? await validationDetail(resp) : "scene request failed (" + resp.status + ")";
      throw new Error(error);
    }
    const data = await resp.json();
    sceneObjects = data.objects || [];
    const timestamp = document.getElementById("scene-timestamp");
    if (timestamp) timestamp.textContent = data.datetime
      ? "Scene time: " + new Date(data.datetime).toISOString() : "";
    satelliteCoverage = data.satellite_coverage || null;
    const coverage = document.getElementById("satellite-coverage");
    if (coverage) {
      if (!satelliteCoverage) {
        coverage.textContent = "";
      } else {
        const failed = satelliteCoverage.failed_attempts || [];
        coverage.textContent = (satelliteCoverage.fallback ? "Fallback" : "Satellite") +
          " coverage: " + satelliteCoverage.selected_label +
          " (CelesTrak subset)" +
          (failed.length ? "; unavailable: " + failed.map(row => row.query).join(", ") : "") + ".";
      }
    }
    rocketBodyCoverage = data.rocket_body_coverage || null;
    const rocketCoverage = document.getElementById("rocket-body-coverage");
    if (rocketCoverage) {
      rocketCoverage.textContent = rocketBodyCoverage
        ? "Rocket-body coverage: " + rocketBodyCoverage.selected_label +
          " (CelesTrak name selection)."
        : "";
    }
    const warning = document.getElementById("source-warning");
    if (warning) {
      const missing = (data.source_warnings || []).map(item =>
        (item.detail || (KIND_NAMES[item.kind] || item.kind)) +
        " (" + item.source + ")"
      );
      const stale = (data.source_freshness || []).filter(item => item.stale);
      const oldElements = (data.source_freshness || []).filter(item =>
        Date.now() - Date.parse(item.oldest_epoch) > 7 * 86400000
      );
      warning.hidden = missing.length === 0 && stale.length === 0 && oldElements.length === 0;
      const messages = [];
      if (missing.length) messages.push(
        "Map incomplete: data unavailable for " + missing.join(", ") + ". Try again later."
      );
      if (stale.length) messages.push("Using cached orbital data for " + stale.map(item =>
        (KIND_NAMES[item.kind] || item.kind) + " (downloaded " +
        new Date(item.downloaded_at * 1000).toISOString() + ")"
      ).join(", ") + ". Refresh failed; download age is limited to 24 hours.");
      if (oldElements.length) messages.push("Some orbital elements are over 7 days old; positions may be less accurate.");
      warning.textContent = messages.join(" ");
    }
    matched = data.search || null;
    debrisCoverage = data.debris_coverage || null;
    await mergeCustomObjects(); // the user's own saved objects
    syncLocalBodies(); // point the Sun/Moon artwork at their real positions
    ok = true;
  } catch (err) {
    if (!error) error = err.message;
  }
  objPositions = sceneObjects.map(() => ({ x: 0, y: 0 }));
  // Object indices change with the new scene, so in-flight bursts and the
  // per-pair collision cooldown no longer refer to anything real.
  clearExplosions();
  // clear stale caches
  for (const k in classCache) delete classCache[k];
  hoveredIdx  = -1;
  selectedIdx = null;
  hideObjectInfo();
  updateLegend();
  // Frame a successful search; a plain load goes back to the whole sky.
  if (ok && matched) focusOnObjects(sceneObjects);
  else if (ok) resetView();
  return {
    ok, count: sceneObjects.length, search: matched,
    debrisCoverage, satelliteCoverage, rocketBodyCoverage, invalid, error,
  };
}

// FastAPI puts the reason in `detail`; fall back to the status if the body
// isn't the shape we expect.
async function validationDetail(resp) {
  try {
    const body = await resp.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail.length) {
      return body.detail[0].msg || "invalid input";
    }
  } catch { /* not JSON */ }
  return "invalid input (" + resp.status + ")";
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

  for (const kind of Object.keys(KIND_STYLES)) {
    if (!counts[kind]) continue;
    const color = kindStyle(kind).color;
    const li = _legendItem(kind, "●", color, KIND_NAMES[kind] || kind, counts[kind]);
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

// ── UI themes ─────────────────────────────────────────────────────────────────
// Each theme recolours the canvas backdrop (gradient, Milky Way, nebulae) and
// the star field; the DOM chrome is themed by CSS variables (see style.css).
// setTheme() swaps both at once. Default = the classic blue.
const THEMES = {
  default: {
    label: "Default",
    motif: null, // animated ornament drawn on moving objects
    explosionColor: "#ff8a3d",
    objectTint: null, // objects keep their natural per-kind colours
    stars: ["#ffffff", "#dbe6ff", "#cfe0ff", "#ffe6c0", "#ffcda0"],
    grad: ["#0b1230", "#050817", "#010208"],
    milkyWay: "150, 165, 235",
    clouds: [
      { x: .22, y: .30, r: .42, c: "rgba(80, 60, 165, 0.18)" },
      { x: .78, y: .62, r: .50, c: "rgba(40, 95, 155, 0.16)" },
      { x: .55, y: .18, r: .34, c: "rgba(150, 55, 120, 0.10)" },
    ],
  },
  cosmic: {
    label: "Purple Cosmic",
    motif: "sparks", // animated ornament drawn on moving objects
    explosionColor: "#d38bff",
    objectTint: { color: "#b794f6", amount: 0.15 },
    stars: ["#ffffff", "#e8d9ff", "#d6bcff", "#c9a2ff", "#ffcdf2"],
    grad: ["#1c1046", "#0d0622", "#04010e"],
    milkyWay: "170, 130, 240",
    clouds: [
      { x: .22, y: .30, r: .42, c: "rgba(140, 70, 220, 0.20)" },
      { x: .78, y: .62, r: .50, c: "rgba(95, 45, 190, 0.18)" },
      { x: .55, y: .18, r: .34, c: "rgba(205, 60, 180, 0.12)" },
    ],
  },
  vangogh: {
    label: "Van Gogh",
    motif: "swirl", // animated ornament drawn on moving objects
    explosionColor: "#f4c430",
    objectTint: { color: "#f4c430", amount: 0.32 },
    stars: ["#ffe9a8", "#ffd76b", "#fff3cf", "#bcd4ff", "#8fb8f0"],
    grad: ["#13457f", "#0d2a58", "#07162f"],
    milkyWay: "245, 205, 90",
    clouds: [
      { x: .24, y: .32, r: .46, c: "rgba(70, 130, 210, 0.24)" },
      { x: .76, y: .60, r: .50, c: "rgba(240, 195, 80, 0.16)" },
      { x: .55, y: .20, r: .36, c: "rgba(120, 170, 235, 0.18)" },
    ],
  },
  burton: {
    label: "Tim Burton",
    motif: "bats", // animated ornament drawn on moving objects
    explosionColor: "#9ae66e",
    objectTint: { color: "#b8a9d9", amount: 0.42 },
    stars: ["#eae7d6", "#c7f0a0", "#ffffff", "#b8a9d9", "#9ae66e"],
    grad: ["#16151d", "#0b0a11", "#030305"],
    milkyWay: "150, 140, 175",
    clouds: [
      { x: .22, y: .30, r: .42, c: "rgba(120, 90, 165, 0.16)" },
      { x: .78, y: .62, r: .50, c: "rgba(95, 125, 60, 0.14)" },
      { x: .55, y: .18, r: .34, c: "rgba(60, 60, 72, 0.22)" },
    ],
  },
  pirate: {
    label: "Pirate",
    motif: "wheel", // animated ornament drawn on moving objects
    explosionColor: "#ff6b2b",
    objectTint: { color: "#d9a441", amount: 0.42 },
    stars: ["#fff4d0", "#f5d98a", "#ffe9a8", "#d9b36a", "#bfa878"],
    grad: ["#2a1d0c", "#150d04", "#070401"],
    milkyWay: "210, 175, 95",
    clouds: [
      { x: .22, y: .30, r: .42, c: "rgba(150, 110, 45, 0.20)" },
      { x: .78, y: .62, r: .50, c: "rgba(70, 130, 120, 0.16)" },
      { x: .55, y: .18, r: .34, c: "rgba(185, 140, 60, 0.12)" },
    ],
  },
};

const DEFAULT_THEME = "default";
let currentTheme = THEMES[DEFAULT_THEME];

// Blend two "#rrggbb" colours; t=0 → a, t=1 → b.
function mixHex(a, b, t) {
  const pa = parseInt(a.slice(1), 16), pb = parseInt(b.slice(1), 16);
  const mix = (sh) => {
    const ca = (pa >> sh) & 255, cb = (pb >> sh) & 255;
    return Math.round(ca + (cb - ca) * t);
  };
  const r = mix(16), g = mix(8), bl = mix(0);
  return "#" + ((1 << 24) | (r << 16) | (g << 8) | bl).toString(16).slice(1);
}

// A kind's glyph style, tinted toward the active theme so on-canvas objects
// match the palette. Kinds stay distinguishable (each keeps its own base hue,
// nudged toward the theme's tint); the default theme applies no tint.
function kindStyle(kind) {
  const base = KIND_STYLES[kind] || { size: 3, color: "#e2e8f0" };
  const tint = currentTheme.objectTint;
  if (!tint || !tint.amount) return base;
  return { size: base.size, color: mixHex(base.color, tint.color, tint.amount) };
}

// ── Stars & backdrop ──────────────────────────────────────────────────────────

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

  const t = currentTheme;

  // Deep-space gradient.
  const g = b.createRadialGradient(w * .5, h * .42, 0, w * .5, h * .42, Math.max(w, h) * .8);
  g.addColorStop(0, t.grad[0]);
  g.addColorStop(0.5, t.grad[1]);
  g.addColorStop(1, t.grad[2]);
  b.fillStyle = g;
  b.fillRect(0, 0, w, h);

  // Faint diagonal Milky Way band.
  b.save();
  b.translate(w * .5, h * .5);
  b.rotate(-0.5);
  const mw = b.createLinearGradient(0, -h * .22, 0, h * .22);
  mw.addColorStop(0, `rgba(${t.milkyWay}, 0)`);
  mw.addColorStop(0.5, `rgba(${t.milkyWay}, 0.10)`);
  mw.addColorStop(1, `rgba(${t.milkyWay}, 0)`);
  b.fillStyle = mw;
  b.fillRect(-w, -h * .22, w * 2, h * .44);
  b.restore();

  // Coloured nebula clouds for depth.
  for (const c of t.clouds) {
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
  const palette = currentTheme.stars;
  for (let i = 0; i < n; i++) {
    // Magnitude 0..1 skewed toward the dim end (power law), so most stars are
    // faint pinpoints and only a few are bright — like a real sky. Size and
    // brightness both scale with it; only the brightest sparkle.
    const mag = Math.pow(Math.random(), 2.6);
    stars.push({
      x: Math.random(), y: Math.random(),
      mag,
      r: 0.4 + mag * 1.9,
      tw: Math.random() * Math.PI * 2,
      sp: 0.008 + Math.random() * 0.02,
      color: palette[(Math.random() * palette.length) | 0],
      glint: mag > 0.85,
    });
  }
}

// ── Draw helpers ──────────────────────────────────────────────────────────────
function drawBackground() {
  const w = window.innerWidth, h = window.innerHeight;
  ctx.drawImage(backdrop, 0, 0, w, h);

  for (const s of stars) {
    const tw    = 0.5 + 0.5 * Math.sin(s.tw);
    // Dim stars are genuinely faint; brightness tracks magnitude and twinkle.
    const alpha = (0.25 + 0.75 * (s.mag ?? 1)) * (0.5 + 0.5 * tw);
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

// Occasional meteors streaking across the sky — a few live at a time, spawned
// at random from the upper-left, fading as they fall. Screen-space, additive.
const meteors = [];
function drawShootingStars() {
  const w = window.innerWidth, h = window.innerHeight;
  if (meteors.length < 3 && Math.random() < 0.01) {
    const fromLeft = Math.random() < 0.5;
    meteors.push({
      x: fromLeft ? -20 : Math.random() * w,
      y: fromLeft ? Math.random() * h * 0.5 : -20,
      vx: 6 + Math.random() * 5,
      vy: 3 + Math.random() * 4,
      life: 1,
    });
  }

  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  ctx.lineWidth = 1.6;
  for (let i = meteors.length - 1; i >= 0; i--) {
    const m = meteors[i];
    m.x += m.vx; m.y += m.vy; m.life -= 0.012;
    if (m.life <= 0 || m.x > w + 40 || m.y > h + 40) { meteors.splice(i, 1); continue; }
    const tailX = m.x - m.vx * 3.2, tailY = m.y - m.vy * 3.2;
    const g = ctx.createLinearGradient(m.x, m.y, tailX, tailY);
    g.addColorStop(0, hexA("#ffffff", m.life));
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.strokeStyle = g;
    ctx.beginPath(); ctx.moveTo(m.x, m.y); ctx.lineTo(tailX, tailY); ctx.stroke();
  }
  ctx.restore();
}

// Lens flare: translucent artifacts strung along the axis from the Sun through
// the screen centre, like light bouncing inside a lens. Screen-space, additive.
function drawSunFlare(sx, sy) {
  const w = window.innerWidth, h = window.innerHeight;
  const dx = w * 0.5 - sx, dy = h * 0.5 - sy;
  const flares = [
    [0.0, 26, "rgba(255,220,150,0.10)"],
    [0.35, 10, "rgba(120,180,255,0.10)"],
    [0.6, 18, "rgba(255,140,180,0.08)"],
    [0.85, 7, "rgba(180,255,200,0.11)"],
    [1.25, 30, "rgba(255,200,120,0.07)"],
  ];
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  for (const [t, r, color] of flares) {
    const x = sx + dx * t, y = sy + dy * t;
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, color);
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}

// A soft darkening toward the frame edges — the eyepiece/sensor falloff that
// makes the view feel observed rather than flat. Drawn in screen space.
function drawVignette() {
  const w = window.innerWidth, h = window.innerHeight;
  const g = ctx.createRadialGradient(
    w * 0.5, h * 0.5, Math.min(w, h) * 0.34,
    w * 0.5, h * 0.5, Math.max(w, h) * 0.72
  );
  g.addColorStop(0, "rgba(0,0,0,0)");
  g.addColorStop(1, "rgba(0,0,0,0.5)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
}

const EARTH_DISC_R = 0.045; // Earth's disc radius in scene-scale units

function _lightUnit(bodyX, bodyY, sunX, sunY) {
  const dx = sunX - bodyX, dy = sunY - bodyY;
  const length = Math.hypot(dx, dy) || 1;
  return { x: dx / length, y: dy / length };
}

function drawEarth(cx, cy, scale) {
  const r = scale * EARTH_DISC_R;
  const light = _lightUnit(cx, cy, cx + SUN.x * scale, cy + SUN.y * scale);

  // Outer atmosphere glow.
  const glow = ctx.createRadialGradient(cx, cy, r * .9, cx, cy, r * 2.6);
  glow.addColorStop(0, "rgba(90,170,255,0.35)");
  glow.addColorStop(0.5, "rgba(70,140,255,0.12)");
  glow.addColorStop(1, "rgba(70,140,255,0)");
  ctx.fillStyle = glow;
  ctx.beginPath(); ctx.arc(cx, cy, r * 2.6, 0, Math.PI * 2); ctx.fill();

  // Ocean base, lit from the scene Sun.
  const eg = ctx.createRadialGradient(cx + light.x * r * .35, cy + light.y * r * .35, r * .15, cx, cy, r);
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
  const term = ctx.createRadialGradient(
    cx + light.x * r * .5, cy + light.y * r * .5, r * .2,
    cx - light.x * r * .6, cy - light.y * r * .6, r * 1.8
  );
  term.addColorStop(0, "rgba(2,6,16,0)");
  term.addColorStop(0.6, "rgba(2,6,16,0.15)");
  term.addColorStop(1, "rgba(2,6,16,0.8)");
  ctx.fillStyle = term;
  ctx.fillRect(cx - r, cy - r, r * 2, r * 2);

  // City lights rotate with the night side.
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  ctx.fillStyle = "rgba(255,214,140,0.9)";
  const awayX = -light.x, awayY = -light.y;
  const acrossX = -awayY, acrossY = awayX;
  for (const [along, across] of [[.35, .1], [.5, -.12], [.25, .22], [.6, .08], [.45, -.24], [.3, -.05], [.68, .2], [.2, -.2]]) {
    ctx.beginPath();
    ctx.arc(cx + (awayX * along + acrossX * across) * r,
      cy + (awayY * along + acrossY * across) * r,
      r * 0.03, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();

  // Specular highlight.
  const specX = cx + light.x * r * .42, specY = cy + light.y * r * .42;
  const spec = ctx.createRadialGradient(specX, specY, 0, specX, specY, r * .5);
  spec.addColorStop(0, "rgba(255,255,255,0.5)");
  spec.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = spec;
  ctx.beginPath(); ctx.arc(specX, specY, r * .5, 0, Math.PI * 2); ctx.fill();
  ctx.restore();

  // Thin bright atmosphere rim.
  const rim = ctx.createRadialGradient(cx, cy, r * .92, cx, cy, r * 1.06);
  rim.addColorStop(0, "rgba(150,210,255,0)");
  rim.addColorStop(0.6, "rgba(150,210,255,0.35)");
  rim.addColorStop(1, "rgba(150,210,255,0)");
  ctx.fillStyle = rim;
  ctx.beginPath(); ctx.arc(cx, cy, r * 1.06, 0, Math.PI * 2); ctx.fill();
}

// ── Decorative planets ─────────────────────────────────────────────────────────
// Distant worlds scattered behind Earth for depth. Purely visual — not scene
// objects, so they never enter hit-testing, forecasting, or the legend.
// Positions are normalized scale-units from the scene centre.
// Per-planet appearance, keyed by name. Positions now come from the scene
// (kind === "planet"); this only carries how each body is drawn. `r` is the
// disc radius in scene-scale units.
const PLANET_STYLES = {
  Mercury: { r: .013, hi: "#cdc6ba", mid: "#7d7367", lo: "#2e2a24", craters: true },
  Venus:   { r: .020, hi: "#f6ead0", mid: "#d9b978", lo: "#8a6d3a" },
  Mars:    { r: .016, hi: "#f0a878", mid: "#c65f38", lo: "#5c2415" },
  Jupiter: { r: .046, hi: "#f2d9b0", mid: "#c79a63", lo: "#6d4626", bands: true, spot: true },
  Saturn:  { r: .034, hi: "#efe0b0", mid: "#c9ac6b", lo: "#7a6034", bands: true, ring: "#d8c48f" },
  Uranus:  { r: .026, hi: "#cdeefb", mid: "#8fd0e6", lo: "#3f8fae", ring: "#a9d9e6" },
  Neptune: { r: .025, hi: "#bfe0ff", mid: "#5f92d8", lo: "#213f7a" },
};

// A lit sphere with its highlight facing the scene Sun.
function _shadedSphere(cx, cy, r, hi, mid, lo, light = { x: -.707, y: -.707 }) {
  const g = ctx.createRadialGradient(cx + light.x * r * .4, cy + light.y * r * .4, r * .1, cx, cy, r);
  g.addColorStop(0, hi); g.addColorStop(0.55, mid); g.addColorStop(1, lo);
  ctx.fillStyle = g;
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();
}

// Day/night shading, matching Earth's terminator so the lighting reads as one sun.
function _planetShadow(cx, cy, r, light) {
  const t = ctx.createRadialGradient(
    cx + light.x * r * .5, cy + light.y * r * .5, r * .2,
    cx - light.x * r * .6, cy - light.y * r * .6, r * 1.7
  );
  t.addColorStop(0, "rgba(2,4,10,0)");
  t.addColorStop(0.65, "rgba(2,4,10,0.12)");
  t.addColorStop(1, "rgba(2,4,10,0.72)");
  ctx.fillStyle = t;
  ctx.fillRect(cx - r, cy - r, r * 2, r * 2);
}

// Horizontal cloud belts for a gas giant.
function _planetBands(cx, cy, r) {
  ctx.fillStyle = "rgba(90,55,25,0.20)";
  for (const [oy, hh] of [[-.45, .11], [-.08, .16], [.28, .13], [.55, .09]]) {
    ctx.beginPath();
    ctx.ellipse(cx, cy + oy * r, r * 0.99, hh * r, 0, 0, Math.PI * 2);
    ctx.fill();
  }
}

// Impact craters for rocky bodies (Mercury, Pluto, the Moon).
function _craters(cx, cy, r, color) {
  ctx.fillStyle = color;
  for (const [dx, dy, rr] of [[-.3, -.2, .22], [.25, .1, .28], [.05, .4, .18], [.4, -.3, .15], [-.35, .28, .16]]) {
    ctx.beginPath(); ctx.arc(cx + dx * r, cy + dy * r, rr * r, 0, Math.PI * 2); ctx.fill();
  }
}

// Jupiter's Great Red Spot.
function _redSpot(cx, cy, r) {
  ctx.fillStyle = "rgba(200,90,60,0.55)";
  ctx.beginPath(); ctx.ellipse(cx + r * .28, cy + r * .18, r * .22, r * .14, 0, 0, Math.PI * 2); ctx.fill();
}

// A tilted ring; drawn once behind the planet and again (clipped low) in front.
function _planetRing(cx, cy, r, color, front) {
  ctx.save();
  if (front) {
    ctx.beginPath(); ctx.rect(cx - r * 3, cy, r * 6, r * 3); ctx.clip();
  }
  ctx.strokeStyle = hexA(color, front ? 0.9 : 0.5);
  ctx.lineWidth = r * 0.3;
  ctx.beginPath();
  ctx.ellipse(cx, cy, r * 2.05, r * 0.62, -0.5, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
}

// Draw one planet's disc at a screen position, from its PLANET_STYLES entry.
// Positions come from the scene object, so planets are hit-testable like any
// other object and drawn here only for their look.
function drawPlanetBody(name, px, py, scale, sunX = px - 1, sunY = py - 1) {
  const p = PLANET_STYLES[name];
  if (!p) return;
  const r = p.r * scale;
  const light = _lightUnit(px, py, sunX, sunY);

  if (p.ring) _planetRing(px, py, r, p.ring, false);
  _shadedSphere(px, py, r, p.hi, p.mid, p.lo, light);

  // Belts and shading stay inside the disc.
  ctx.save();
  ctx.beginPath(); ctx.arc(px, py, r, 0, Math.PI * 2); ctx.clip();
  if (p.bands) _planetBands(px, py, r);
  if (p.spot) _redSpot(px, py, r);
  if (p.craters) _craters(px, py, r, "rgba(50,44,38,0.35)");
  _planetShadow(px, py, r, light);
  ctx.restore();

  if (p.ring) _planetRing(px, py, r, p.ring, true);
}

// A planet's disc radius in scene-scale units (0 if unknown), for hit-testing
// and selection halos.
function planetRadius(name) {
  const p = PLANET_STYLES[name];
  return p ? p.r : 0;
}

// Defaults are replaced with scene positions after every load.
const SUN = { x: -.52, y: -.40, r: .05 };

function drawSun(cx, cy, scale) {
  const x = cx + SUN.x * scale, y = cy + SUN.y * scale, r = SUN.r * scale;

  const corona = ctx.createRadialGradient(x, y, r * .4, x, y, r * 4);
  corona.addColorStop(0, "rgba(255,240,190,0.55)");
  corona.addColorStop(0.3, "rgba(255,200,110,0.28)");
  corona.addColorStop(1, "rgba(255,180,80,0)");
  ctx.fillStyle = corona;
  ctx.beginPath(); ctx.arc(x, y, r * 4, 0, Math.PI * 2); ctx.fill();

  const core = ctx.createRadialGradient(x - r * .2, y - r * .2, r * .1, x, y, r);
  core.addColorStop(0, "#fff7e0"); core.addColorStop(0.6, "#ffd873"); core.addColorStop(1, "#ff9d3c");
  ctx.fillStyle = core;
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
}

// Our Moon, orbiting Earth, lit by the Sun with a real phase.
const MOON = { x: .14, y: -.075, r: .016 };

function drawMoon(cx, cy, scale) {
  const x = cx + MOON.x * scale, y = cy + MOON.y * scale, r = MOON.r * scale;

  // Faint orbit ring around Earth, passing through the Moon.
  const dist = Math.hypot(MOON.x, MOON.y) * scale;
  ctx.strokeStyle = "rgba(180,200,255,0.12)"; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.arc(cx, cy, dist, 0, Math.PI * 2); ctx.stroke();

  // Soft glow so it's easy to spot next to Earth.
  _additive(() => _bloom(x, y, r * 2.4, "#dfe3ee", 0.22));

  const light = _lightUnit(x, y, cx + SUN.x * scale, cy + SUN.y * scale);
  _shadedSphere(x, y, r, "#e8e8ee", "#9a9aa6", "#3a3a44", light);

  ctx.save();
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.clip();
  _craters(x, y, r, "rgba(60,60,72,0.35)");

  // Lunar phase: the night side faces away from the Sun.
  const sx = x - light.x * r * 1.1, sy = y - light.y * r * 1.1; // shadow centre, anti-Sun
  const shade = ctx.createRadialGradient(sx, sy, r * 0.2, sx, sy, r * 1.9);
  shade.addColorStop(0, "rgba(5,6,12,0.92)");
  shade.addColorStop(0.6, "rgba(5,6,12,0.5)");
  shade.addColorStop(1, "rgba(5,6,12,0)");
  ctx.fillStyle = shade;
  ctx.fillRect(x - r, y - r, r * 2, r * 2);
  ctx.restore();
}

// The Sun, Earth, and Moon come from the scene at their real positions but are
// drawn by their own artwork (drawSun/drawEarth/drawMoon). Point the render
// constants at the scene's Sun/Moon so the drawing — and the Sun-based lighting
// (Moon phase, sun flare) — follows their true positions. Earth stays centred.
function syncLocalBodies() {
  const sun = sceneObjects.find((o) => o.kind === "sun");
  const moon = sceneObjects.find((o) => o.kind === "moon");
  if (sun)  { SUN.x = sun.x_norm; SUN.y = sun.y_norm; }
  if (moon) { MOON.x = moon.x_norm; MOON.y = moon.y_norm; }
}

// A body's disc radius in scene-scale units (0 for glyph objects), for
// hit-testing and selection halos.
function bodyDiscR(obj) {
  switch (obj.kind) {
    case "planet": return planetRadius(obj.name);
    case "sun":    return SUN.r;
    case "earth":  return EARTH_DISC_R;
    case "moon":   return MOON.r;
    default:       return 0;
  }
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
    const style = kindStyle(obj.kind);
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

// ── Realistic per-kind glyphs ──────────────────────────────────────────────────
// A soft radial glow fading to transparent.
function _bloom(x, y, r, color, alpha) {
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, hexA(color, alpha));
  g.addColorStop(1, hexA(color, 0));
  ctx.fillStyle = g;
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
}

// The 4-point diffraction spike real optics give bright point sources.
function _spikes(x, y, len, color, alpha, width) {
  ctx.strokeStyle = hexA(color, alpha);
  ctx.lineWidth = width;
  ctx.beginPath();
  ctx.moveTo(x - len, y); ctx.lineTo(x + len, y);
  ctx.moveTo(x, y - len); ctx.lineTo(x, y + len);
  ctx.stroke();
}

function _core(x, y, r, color) {
  ctx.fillStyle = color;
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
}

// Run a draw with additive blending so overlapping light adds up, then restore.
function _additive(draw) {
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  draw();
  ctx.restore();
}

// A fading streak behind a moving object.
function _drawTrail(trail, color) {
  if (!trail || trail.length < 2) return;
  ctx.lineWidth = 1.5;
  for (let i = 1; i < trail.length; i++) {
    ctx.strokeStyle = hexA(color, (i / trail.length) * 0.5);
    ctx.beginPath();
    ctx.moveTo(trail[i - 1].x, trail[i - 1].y);
    ctx.lineTo(trail[i].x, trail[i].y);
    ctx.stroke();
  }
}

// Draw one object as a glyph that reads as its kind, not a flat dot.
// ── Theme motifs ──────────────────────────────────────────────────────────────
// Each theme can decorate moving objects with a small animated ornament, so the
// chosen look reads on the objects themselves and not just the backdrop. Only
// the objects that actually move are decorated — ornamenting all ~109 would
// clutter the deep sky and hide the real data.
const MOTIF_KINDS = new Set([
  "satellite", "iss", "space_debris", "rocket_body", "ufo",
]);

const THEME_MOTIFS = {
  // Two sparks orbiting the object.
  sparks(x, y, s, phase, color) {
    _additive(() => {
      for (const offset of [0, Math.PI]) {
        const a = phase * 2 + offset;
        _core(x + Math.cos(a) * s * 2.4, y + Math.sin(a) * s * 2.4, s * 0.4, color);
      }
    });
  },

  // A rotating brush-stroke arc, echoing Starry Night's swirls.
  swirl(x, y, s, phase, color) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(phase * 1.5);
    _additive(() => {
      ctx.strokeStyle = hexA(color, 0.7);
      ctx.lineWidth = Math.max(1, s * 0.35);
      ctx.beginPath();
      ctx.arc(0, 0, s * 2.2, 0, Math.PI * 1.4);
      ctx.stroke();
    });
    ctx.restore();
  },

  // Flapping bat wings — two arcs whose span pulses.
  bats(x, y, s, phase, color) {
    const flap = 0.6 + 0.4 * Math.sin(phase * 6);
    ctx.save();
    ctx.translate(x, y);
    ctx.strokeStyle = hexA(color, 0.8);
    ctx.lineWidth = Math.max(1, s * 0.3);
    for (const dir of [-1, 1]) {
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.quadraticCurveTo(dir * s * 1.6, -s * 1.6 * flap, dir * s * 2.8, 0);
      ctx.stroke();
    }
    ctx.restore();
  },

  // A turning ship's wheel: rim plus spokes that overhang it as handles.
  wheel(x, y, s, phase, color) {
    const r = s * 1.9;
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(phase * 1.2);
    ctx.strokeStyle = hexA(color, 0.85);
    ctx.lineWidth = Math.max(1, s * 0.28);
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    for (let spoke = 0; spoke < 6; spoke++) {
      const a = (spoke / 6) * Math.PI * 2;
      ctx.moveTo(0, 0);
      ctx.lineTo(Math.cos(a) * r * 1.45, Math.sin(a) * r * 1.45);
    }
    ctx.stroke();
    ctx.restore();
  },
};

// Draw the active theme's ornament on one object, if it has one.
function drawThemeMotif(kind, x, y, size, phase, color) {
  if (!MOTIF_KINDS.has(kind)) return false;
  const motif = THEME_MOTIFS[currentTheme.motif];
  if (!motif) return false;
  motif(x, y, size, phase, color);
  return true;
}

function drawGlyph(kind, x, y, style, phase, sunX, sunY) {
  const c = style.color;
  const s = style.size;

  switch (kind) {
    case "star":
    case "variable_star":
      _additive(() => { _bloom(x, y, s * 4, c, 0.6); _spikes(x, y, s * 3.5, "#ffffff", 0.5, 1); });
      _core(x, y, s * 0.7, "#ffffff");
      break;

    case "galaxy": {
      const tilt = (x * 0.7 + y * 0.3) % Math.PI; // deterministic per position
      ctx.save();
      ctx.translate(x, y); ctx.rotate(tilt);
      _additive(() => {
        for (const [rx, ry, a] of [[s * 3, s * 1.4, 0.18], [s * 2, s * 0.9, 0.28], [s, s * 0.5, 0.5]]) {
          const g = ctx.createRadialGradient(0, 0, 0, 0, 0, rx);
          g.addColorStop(0, hexA(c, a)); g.addColorStop(1, hexA(c, 0));
          ctx.fillStyle = g;
          ctx.beginPath(); ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2); ctx.fill();
        }
      });
      ctx.restore();
      _core(x, y, s * 0.5, "#ffffff");
      break;
    }

    case "nebula":
      _additive(() => {
        for (const [dx, dy, r, a] of [[0, 0, s * 3, 0.28], [s, -s * 0.6, s * 2, 0.2], [-s, s * 0.5, s * 2.2, 0.18]]) {
          _bloom(x + dx, y + dy, r, c, a);
        }
      });
      break;

    case "black_hole":
      _additive(() => _bloom(x, y, s * 3.5, "#ffa24a", 0.35)); // lensing glow
      ctx.fillStyle = "#05060a"; // event-horizon shadow
      ctx.beginPath(); ctx.arc(x, y, s, 0, Math.PI * 2); ctx.fill();
      _additive(() => {
        ctx.strokeStyle = hexA("#ffd27a", 0.9); ctx.lineWidth = 1.6;
        ctx.beginPath(); ctx.arc(x, y, s * 1.5, 0, Math.PI * 2); ctx.stroke();
        ctx.strokeStyle = hexA(c, 0.5); ctx.lineWidth = 1;
        ctx.beginPath(); ctx.arc(x, y, s * 2.1, 0, Math.PI * 2); ctx.stroke();
      });
      break;

    case "comet": {
      let tx = x - sunX, ty = y - sunY; // tail streams away from the Sun
      const d = Math.hypot(tx, ty) || 1;
      tx /= d; ty /= d;
      const tail = s * 8;
      _additive(() => {
        const g = ctx.createLinearGradient(x, y, x + tx * tail, y + ty * tail);
        g.addColorStop(0, hexA(c, 0.6)); g.addColorStop(1, hexA(c, 0));
        ctx.strokeStyle = g; ctx.lineWidth = s * 1.4;
        ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + tx * tail, y + ty * tail); ctx.stroke();
        _bloom(x, y, s * 2.5, c, 0.6);
      });
      _core(x, y, s * 0.6, "#ddffff");
      break;
    }

    case "pulsar": {
      const pulse = 0.4 + 0.6 * (0.5 + 0.5 * Math.sin(phase * 3));
      _additive(() => { _bloom(x, y, s * 4 * pulse, c, 0.7 * pulse); _spikes(x, y, s * 5, c, 0.35 * pulse, 1); });
      _core(x, y, s * 0.6, "#ffffff");
      break;
    }

    case "quasar":
      _additive(() => {
        _bloom(x, y, s * 4, c, 0.7);
        ctx.strokeStyle = hexA(c, 0.5); ctx.lineWidth = 1.4; // relativistic jet
        ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, y - s * 7); ctx.stroke();
      });
      _core(x, y, s * 0.7, "#ffffff");
      break;

    case "iss":
    case "satellite":
    case "space_debris":
    case "rocket_body":
      _additive(() => { _bloom(x, y, s * 2, c, 0.6); _spikes(x, y, s * 2.2, "#ffffff", 0.7, 1); });
      _core(x, y, Math.max(1.2, s * 0.5), "#ffffff");
      break;

    default: // asteroids, near-Earth objects, meteors, ufo — a glowing point
      _additive(() => _bloom(x, y, s * 2.4, c, 0.5));
      _core(x, y, s, c);
  }
}

// ── Collisions and explosions ─────────────────────────────────────────────────
// Only objects with real velocity can collide — the satellites, debris and
// rocket bodies that the simulation actually moves. Static catalogue entries
// (deep sky, planets, Earth) are drawn at a fixed spot, so a "collision"
// between them would be an artifact of the projection, not an event.
const COLLISION_DIST_SCENE = 0.006; // scene units, so it is zoom-independent
const COLLISION_COOLDOWN_MS = 4000; // per pair, so contact doesn't spam bursts
const EXPLOSION_LIFETIME_MS = 900;
const MAX_EXPLOSIONS = 12;

let explosions = [];
let lastCollisionAt = {};        // "i:j" -> timestamp of that pair's last burst
let separatedPairs = new Set();  // pair keys currently known to be apart

function isCollidable(obj) {
  return Boolean(obj && (obj.vx_norm || obj.vy_norm));
}

// Pairs of collidable objects that have just come together.
//
// Proximity alone is the wrong test: plenty of real objects are permanently
// co-located on this map — ISS modules docked to the same station, Starlink
// satellites flying in formation — and on a log-radius projection they sit on
// top of each other from the first frame. Those never *approach*; they arrive
// together. So a pair only counts once it has been seen apart, and must
// separate again before it can count a second time.
//
// `separated` is the set of pair keys currently known to be apart; this reads
// and updates it. Positions are canvas units at zoom 1, so the threshold is
// zoom-independent.
function findApproaches(objects, positions, threshold, separated) {
  const events = [];
  for (let i = 0; i < objects.length; i++) {
    if (!isCollidable(objects[i]) || !positions[i]) continue;
    for (let j = i + 1; j < objects.length; j++) {
      if (!isCollidable(objects[j]) || !positions[j]) continue;
      const key = i + ":" + j;
      const dx = positions[i].x - positions[j].x;
      const dy = positions[i].y - positions[j].y;

      if (Math.hypot(dx, dy) > threshold) {
        separated.add(key);
        continue;
      }
      if (!separated.has(key)) continue; // together since we started watching
      separated.delete(key);             // must drift apart before firing again
      events.push({
        i, j,
        x: (positions[i].x + positions[j].x) / 2,
        y: (positions[i].y + positions[j].y) / 2,
      });
    }
  }
  return events;
}

// Turn collisions into bursts, ignoring any pair that just exploded.
function spawnExplosions(hits, now, color) {
  for (const hit of hits) {
    if (explosions.length >= MAX_EXPLOSIONS) break;
    const key = hit.i + ":" + hit.j;
    if (now - (lastCollisionAt[key] || -Infinity) < COLLISION_COOLDOWN_MS) continue;
    lastCollisionAt[key] = now;
    explosions.push({
      x: hit.x,
      y: hit.y,
      born: now,
      color,
      // Fixed spread per burst so a replay of the same frame looks the same.
      shards: Array.from({ length: 10 }, (_, n) => {
        const a = (n / 10) * Math.PI * 2;
        return { dx: Math.cos(a), dy: Math.sin(a), len: 0.6 + (n % 3) * 0.25 };
      }),
    });
  }
}

function drawExplosions(now, scale) {
  for (let i = explosions.length - 1; i >= 0; i--) {
    const burst = explosions[i];
    const age = (now - burst.born) / EXPLOSION_LIFETIME_MS;
    if (age >= 1) { explosions.splice(i, 1); continue; }

    const fade = 1 - age;
    const radius = scale * 0.012 * (0.3 + age * 2.2);
    _additive(() => {
      _bloom(burst.x, burst.y, radius * 2.2, burst.color, 0.5 * fade);
      _bloom(burst.x, burst.y, radius, "#fff3c4", 0.7 * fade);

      ctx.strokeStyle = hexA(burst.color, 0.8 * fade);
      ctx.lineWidth = Math.max(1, scale * 0.002 * fade);
      ctx.beginPath();
      for (const shard of burst.shards) {
        const inner = radius * 0.6, outer = radius * (1.1 + shard.len);
        ctx.moveTo(burst.x + shard.dx * inner, burst.y + shard.dy * inner);
        ctx.lineTo(burst.x + shard.dx * outer, burst.y + shard.dy * outer);
      }
      ctx.stroke();

      ctx.strokeStyle = hexA("#ffffff", 0.5 * fade);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(burst.x, burst.y, radius * 1.6, 0, Math.PI * 2);
      ctx.stroke();
    });
  }
}

function clearExplosions() {
  explosions = [];
  lastCollisionAt = {};
  separatedPairs = new Set();
}

function drawSceneObjects(cx, cy, scale, realTime) {
  // How far has simulation advanced (in real seconds of object physics)?
  const simElapsedS = (simMode && !simPaused)
    ? (effectiveTime(realTime) - simStartEff) / 1000
    : 0;
  const moving = simMode && !simPaused;
  const phase = realTime * 0.004;
  const sunX = cx + SUN.x * scale, sunY = cy + SUN.y * scale;

  if (objTrails.length !== sceneObjects.length) objTrails = sceneObjects.map(() => []);

  for (let i = 0; i < sceneObjects.length; i++) {
    const obj   = sceneObjects[i];
    const style = kindStyle(obj.kind);

    if (filterKind && obj.kind !== filterKind) {
      objPositions[i] = { x: -9999, y: -9999 }; // off-screen so hit test skips
      objTrails[i].length = 0;
      continue;
    }

    const wx = cx + (obj.x_norm + (obj.vx_norm || 0) * simElapsedS) * scale;
    const wy = cy + (obj.y_norm + (obj.vy_norm || 0) * simElapsedS) * scale;

    // Planets and the Sun/Earth/Moon are drawn as sized discs, so their
    // clickable/halo radius is the disc itself; small glyphs use their size.
    const discR = bodyDiscR(obj); // scale-units, 0 for glyph objects
    const isBody = discR > 0;
    const vr = isBody ? discR * scale : style.size;
    objPositions[i] = { x: wx, y: wy, hit: isBody ? vr : 0 };

    // Motion trail for objects that actually move, only while the sim runs.
    if (moving && (obj.vx_norm || obj.vy_norm)) {
      objTrails[i].push({ x: wx, y: wy });
      if (objTrails[i].length > 14) objTrails[i].shift();
    } else if (!moving && objTrails[i].length) {
      objTrails[i].length = 0;
    }
    _drawTrail(objTrails[i], style.color);

    if (i === selectedIdx) {
      ctx.strokeStyle = style.color; ctx.lineWidth = 1.5; ctx.globalAlpha = 0.75;
      ctx.beginPath(); ctx.arc(wx, wy, vr + 7, 0, Math.PI*2); ctx.stroke();
      ctx.globalAlpha = 1;
    }
    if (i === hoveredIdx && i !== selectedIdx) {
      ctx.strokeStyle = "#fff"; ctx.lineWidth = 1; ctx.globalAlpha = 0.35;
      ctx.beginPath(); ctx.arc(wx, wy, vr + 6, 0, Math.PI*2); ctx.stroke();
      ctx.globalAlpha = 1;
    }

    if (obj.kind === "planet") {
      drawPlanetBody(obj.name, wx, wy, scale, sunX, sunY);
    } else if (!isBody) {
      // Sun/Earth/Moon are painted by their own draw functions in frame().
      drawGlyph(obj.kind, wx, wy, style, phase, sunX, sunY);
      drawThemeMotif(obj.kind, wx, wy, style.size, phase, style.color);
    }
  }

  // Projected near-pass flashes are optional and only run during simulation.
  if (moving && nearPassEffectsEnabled) {
    const approaches = findApproaches(
      sceneObjects, objPositions, COLLISION_DIST_SCENE * scale, separatedPairs
    );
    spawnExplosions(approaches, realTime, currentTheme.explosionColor);
  }
  if (nearPassEffectsEnabled) drawExplosions(realTime, scale);
}

// ── Main loop ─────────────────────────────────────────────────────────────────
function frame(realTime) {
  const w = window.innerWidth, h = window.innerHeight;
  CX = w * 0.42; CY = h * 0.5; SCALE = Math.min(w, h) * 0.95;

  // Background — no transform (stars are screen-fixed)
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  drawBackground();
  drawShootingStars();

  // Scene — pan/zoom applied on top of DPR
  ctx.save();
  ctx.translate(panX, panY);
  ctx.scale(zoom, zoom);
  drawSun(CX, CY, SCALE);
  drawOrbitalPaths(CX, CY, SCALE);
  drawEarth(CX, CY, SCALE);
  drawMoon(CX, CY, SCALE);
  drawForecastPaths(CX, CY, SCALE);
  drawSceneObjects(CX, CY, SCALE, realTime);
  ctx.restore();

  // Screen-space light effects over the scene, then edge falloff on top.
  drawSunFlare(panX + (CX + SUN.x * SCALE) * zoom, panY + (CY + SUN.y * SCALE) * zoom);
  drawVignette();

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

// ── Theme switching ─────────────────────────────────────────────────────────────
// Swaps the CSS chrome (via a body class) and the canvas palette together, then
// remembers the choice. Unknown names fall back to the default.
function setTheme(name) {
  const key = THEMES[name] ? name : DEFAULT_THEME;
  currentTheme = THEMES[key];
  for (const t of Object.keys(THEMES)) document.body.classList.remove("theme-" + t);
  document.body.classList.add("theme-" + key);
  const select = document.getElementById("theme-select");
  if (select && select.value !== key) select.value = key;
  buildBackdrop(window.innerWidth, window.innerHeight);
  initStars(320);
  updateLegend(); // recolour legend swatches for the new palette
  try { localStorage.setItem(window.COSMIC.THEME_KEY, key); } catch { /* storage disabled */ }
  return key;
}

// Bridge for auth.js: apply a theme saved on the user's profile.
window.cosmicSetTheme = setTheme;

const _themeSelect = document.getElementById("theme-select");
if (_themeSelect) {
  _themeSelect.addEventListener("change", () => {
    const key = setTheme(_themeSelect.value);
    // A user-initiated change — let auth.js persist it to the profile.
    document.dispatchEvent(new CustomEvent("cosmic:themechange", { detail: key }));
  });
}

// ── Add-object form ──────────────────────────────────────────────────────────
function initAddObjectForm() {
  const form = document.getElementById("add-object-form");
  const kindSel = document.getElementById("add-kind");
  const bandSel = document.getElementById("add-band");
  if (!form || !kindSel || !bandSel) return;

  const SINGLETONS = new Set(["sun", "earth", "moon"]);
  for (const [kind, label] of Object.entries(KIND_NAMES)) {
    if (SINGLETONS.has(kind)) continue; // one-of-a-kind bodies aren't user-addable
    kindSel.appendChild(new Option(label, kind));
  }
  kindSel.value = "satellite";
  for (const band of Object.keys(DISTANCE_BANDS)) {
    bandSel.appendChild(new Option(band, band));
  }
  bandSel.value = "Low orbit (LEO)";

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("add-name").value.trim();
    if (!name) return;
    const kind = kindSel.value;
    const { x, y } = customObjectXY(bandSel.value, document.getElementById("add-ra").value);
    addToScene({
      name, kind, x_norm: x, y_norm: y,
      vx_norm: 0, vy_norm: 0, speed_kms: 0, source: "custom",
    });
    await persistCustomObject(name, kind, x, y);
    document.getElementById("add-name").value = "";
    const note = document.getElementById("add-object-note");
    if (note) {
      note.textContent = _token()
        ? `Added “${name}” — saved to your profile.`
        : `Added “${name}” — log in to keep it across reloads.`;
    }
  });
}

resize(); // size the canvas first
let _savedTheme = null;
try { _savedTheme = localStorage.getItem(window.COSMIC.THEME_KEY); } catch { /* ignore */ }
setTheme(_savedTheme || DEFAULT_THEME); // paints the themed backdrop + star field
initAddObjectForm();
requestAnimationFrame(frame);

// ── Hit testing ───────────────────────────────────────────────────────────────
const HIT_RADIUS = 20;

function findObjectAt(sx, sy) {
  // Convert screen coords → world coords (inverse pan/zoom)
  const wx   = (sx - panX) / zoom;
  const wy   = (sy - panY) / zoom;
  const hitR = HIT_RADIUS / zoom;
  let closest = -1, minD = Infinity;
  for (let i = 0; i < sceneObjects.length; i++) {
    if (filterKind && sceneObjects[i].kind !== filterKind) continue;
    const p = objPositions[i];
    if (!p) continue;
    const d = Math.hypot(wx - p.x, wy - p.y);
    // A planet is clickable across its whole disc; small glyphs use hitR.
    const reach = Math.max(hitR, p.hit || 0);
    if (d <= reach && d < minD) { minD = d; closest = i; }
  }
  return closest;
}

// ── Object info panel ─────────────────────────────────────────────────────────
function showObjectInfo(idx) {
  selectedIdx = idx;
  const obj   = sceneObjects[idx];
  if (!obj) return;

  for (const [id, note] of [
    ["obj-position-note", obj.position_note],
    ["obj-motion-note", obj.motion_note],
  ]) {
    const element = document.getElementById(id);
    if (element) {
      element.textContent = note || "";
      element.hidden = !note;
    }
  }

  const xn   = obj.x_norm;
  const yn   = obj.y_norm;
  const dist = Math.hypot(xn, yn);
  const az   = (Math.atan2(yn, xn) * 180 / Math.PI).toFixed(1);

  document.getElementById("obj-title").textContent  = obj.name || ("Object #" + (idx + 1));
  document.getElementById("obj-x").textContent      = (xn >= 0 ? "+" : "") + xn.toFixed(4) + " u";
  document.getElementById("obj-y").textContent      = (yn >= 0 ? "+" : "") + yn.toFixed(4) + " u";
  document.getElementById("obj-dist").textContent   = dist.toFixed(4) + " u";
  document.getElementById("obj-az").textContent     = az + "°";
  document.getElementById("obj-orbit").textContent = obj.debris_field
    ? (obj.source || "celestrak") + " · " +
      (DEBRIS_FIELD_NAMES[obj.debris_field] || obj.debris_field)
    : (obj.source || "—");
  document.getElementById("obj-radius").textContent = obj.speed_kms
    ? obj.speed_kms.toFixed(2) + " km/s" : "—";
  document.getElementById("obj-kind").textContent   = KIND_NAMES[obj.kind] || obj.kind;

  // A fact for the object: its own description (solar-system bodies) if present,
  // otherwise the per-kind fallback.
  const fact = obj.description || KIND_FACTS[obj.kind] || "";
  const link = KIND_LINKS[obj.kind] || "";
  const descEl = document.getElementById("obj-desc");
  const aboutEl = document.getElementById("obj-about");
  const linkEl = document.getElementById("obj-info-link");
  if (descEl) descEl.textContent = fact;
  if (linkEl) {
    if (link) {
      linkEl.href = link;
      linkEl.target = "_blank";
      linkEl.textContent = "Learn more at NASA →";
      linkEl.style.display = "";
    } else {
      linkEl.removeAttribute("href");
      linkEl.style.display = "none";
    }
  }
  // The panel is worth showing if there's either a fact or a link.
  if (aboutEl) aboutEl.style.display = fact || link ? "block" : "none";

  document.getElementById("obj-class").textContent  = "Loading…";
  document.getElementById("obj-conf").textContent   = "—";
  document.getElementById("conf-bar").style.width   = "0%";
  document.getElementById("obj-group-wrap").innerHTML = "";

  document.getElementById("form-view").style.display = "none";
  document.getElementById("obj-view").style.display  = "block";

  if (classCache[idx]) {
    applyClassification(idx);
  } else {
    fetch("/api/classify/" + idx + "?kind=" + encodeURIComponent(obj.kind))
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
const nearPassEffects = document.getElementById("near-pass-effects");
let nearPassEffectsEnabled = Boolean(nearPassEffects && nearPassEffects.checked);

if (nearPassEffects) {
  nearPassEffects.addEventListener("change", () => {
    nearPassEffectsEnabled = nearPassEffects.checked;
    if (!nearPassEffectsEnabled) clearExplosions();
  });
}

// Freeze the simulation at a moment and put the controls in the paused state.
// Four flows land here — load scene, clear search, CSV upload, page init — so
// they share one definition instead of four copies of the same eight lines.
// Callers that invalidate predicted paths clear `forecastPaths` themselves; the
// CSV flow deliberately keeps the paths it just computed.
function pauseSimulationAt(timestampMs, label) {
  simMode      = true;
  simPaused    = true;
  simStartReal = performance.now();
  simStartEff  = timestampMs;

  playBtn.textContent = "▶ Play Simulation";
  playBtn.classList.remove("playing");
  simTimeEl.style.display = "block";
  simTimeEl.textContent   = "Paused — " + label;
}

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
// The date/time field is UTC (so is the label), matching what /api/scene expects.
function sceneResultHTML(ra, dec, utcMinutes, result) {
  // Rejected input and an unreachable catalog are different problems: one the
  // user can fix by retyping, the other they can only retry.
  if (!result.ok && result.invalid) {
    return '<div class="results">' +
      '<h3>Check Your Search</h3>' +
      '<p>' + esc(result.error || "invalid input") + '</p>' +
      '<p style="margin-top:0.5rem;color:#7a9acc;font-size:0.82rem;">' +
        'RA is 0–360&deg;, Dec is -90–90&deg;. Give both, or neither for the whole sky.' +
      '</p>' +
    '</div>';
  }
  if (!result.ok) {
    return '<div class="results">' +
      '<h3>Scene Failed to Load</h3>' +
      '<p>Could not reach the catalogs for ' + esc(utcMinutes) + ' UTC. ' +
        'The previous scene is still shown.</p>' +
    '</div>';
  }
  // A position search reports what it searched, so an empty patch of sky reads
  // as an empty result rather than a broken load.
  const search = result.search;
  const coords = search
    ? '<p>RA: ' + esc(ra) + ' &nbsp; Dec: ' + esc(dec) +
      ' &nbsp; within ' + search.radius_deg + '&deg;</p>'
    : (ra && dec ? '<p>RA: ' + esc(ra) + ' &nbsp; Dec: ' + esc(dec) + '</p>' : '');
  const tally = search
    ? '<p>' + search.matched + ' of ' + search.searched + ' objects in this patch of sky</p>'
    : '<p>' + result.count + ' object' + (result.count === 1 ? '' : 's') + ' loaded</p>';
  const excluded = search && search.excluded_count
    ? '<p>Excluded without sky coordinates: ' +
      Object.entries(search.excluded_without_coordinates || {}).map(([kind, count]) =>
        esc(KIND_NAMES[kind] || kind) + ': ' + esc(String(count))).join(', ') + '.</p>'
    : '';
  const observer = search && search.observer_count
    ? '<p>Earth is retained as the observer and is not counted as a search match.</p>' : '';
  const debris = result.debrisCoverage
    ? '<p>Debris coverage: ' + esc(result.debrisCoverage.label) +
      (result.debrisCoverage.duplicates_removed
        ? ' (' + result.debrisCoverage.duplicates_removed + ' duplicate' +
          (result.debrisCoverage.duplicates_removed === 1 ? '' : 's') + ' removed)'
        : '') + '</p>'
    : '';
  const satellite = result.satelliteCoverage
    ? '<p>Satellite coverage: ' + esc(result.satelliteCoverage.selected_label) +
      ' (CelesTrak subset' + (result.satelliteCoverage.fallback ? ', fallback' : '') + ')</p>'
    : '';
  const rocketBody = result.rocketBodyCoverage
    ? '<p>Rocket-body coverage: ' + esc(result.rocketBodyCoverage.selected_label) +
      ' (CelesTrak name selection)</p>'
    : '';
  return '<div class="results">' +
      '<h3>' + (search ? 'Position Search' : 'Loaded Scene') + '</h3>' +
      coords +
      '<p>Time: ' + esc(utcMinutes) + ' UTC</p>' +
      tally +
      excluded + observer +
      satellite +
      rocketBody +
      debris +
      '<p style="margin-top:0.5rem;color:#7a9acc;font-size:0.82rem;">' +
        'Scene paused. Press &#9654; Play to simulate forward.' +
      '</p>' +
    '</div>';
}

document.getElementById("scene-form").addEventListener("submit", async function (e) {
  e.preventDefault();

  const ra          = document.getElementById("ra").value.trim();
  const dec         = document.getElementById("dec").value.trim();
  const obsDatetime = document.getElementById("obs_datetime").value; // YYYY-MM-DDTHH:MM UTC

  const dtISO = obsDatetime ? obsDatetime + ":00Z" : new Date().toISOString();
  const ts    = new Date(dtISO).getTime();
  const stamp = dtISO.slice(0, 16).replace("T", " ");

  // A new scene invalidates any predicted paths drawn for the old one.
  forecastPaths = null;
  pauseSimulationAt(ts, stamp);

  // Every load reports back, so the button is never a no-op on screen.
  const resultEl = document.getElementById("scene-result");
  resultEl.innerHTML = '<div class="results"><p>Loading ' + esc(stamp) + ' UTC…</p></div>';
  const result = await loadScene(dtISO, { ra, dec });
  resultEl.innerHTML = sceneResultHTML(ra, dec, stamp, result);
});

// Clear the position search and go back to the whole sky at the current time.
// The date/time is reset too, so Clear always lands on a known-good state.
document.getElementById("clear-search").addEventListener("click", async function () {
  document.getElementById("ra").value  = "";
  document.getElementById("dec").value = "";

  const now = new Date();
  const utcMinutes = now.toISOString().slice(0, 16);
  document.getElementById("obs_datetime").value = utcMinutes;

  forecastPaths = null;
  pauseSimulationAt(now.getTime(), utcMinutes.replace("T", " "));

  const resultEl = document.getElementById("scene-result");
  resultEl.innerHTML = '<div class="results"><p>Clearing search…</p></div>';
  const result = await loadScene(utcMinutes + ":00Z");
  resultEl.innerHTML = sceneResultHTML("", "", utcMinutes.replace("T", " "), result);
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

    // Freeze at the latest timestamp in the data, keeping the paths just predicted.
    pauseSimulationAt(Date.now(), `${n} objects loaded`);

    csvResult.className   = "csv-status success";
    csvResult.textContent = `✓ ${n} object${n === 1 ? "" : "s"} loaded, ${p} path${p === 1 ? "" : "s"} predicted. Press ▶ to simulate.`;
  } catch (err) {
    csvResult.className   = "csv-status error";
    csvResult.textContent = "✗ " + err.message;
  }
}

// ── Auto-load on page start ───────────────────────────────────────────────────
(function init() {
  const now = new Date();
  // The field is UTC, like its label and the API — seeding it with local time
  // made an untouched form reload a different moment than the one just shown.
  const utcMinutes = now.toISOString().slice(0, 16);
  document.getElementById("obs_datetime").value = utcMinutes;

  pauseSimulationAt(now.getTime(), utcMinutes.replace("T", " "));

  // Minute precision, like the form sends. A millisecond-precision stamp is a
  // unique cache key on every load, so the server's scene cache never hit.
  loadScene(utcMinutes + ":00Z");
})();

// ── Testing interface (no-op in browser where `module` is undefined) ──────────
if (typeof module !== "undefined") {
  module.exports = {
    // Constants
    KIND_STYLES, KIND_NAMES, KIND_FACTS, KIND_LINKS, CSV_TEMPLATE, SIM_SPEED, HIT_RADIUS, PLANET_STYLES, SUN, MOON,
    THEMES, DEFAULT_THEME,
    // Stateless pure functions
    esc, sceneResultHTML, focusOnObjects, resetView, validationDetail, pauseSimulationAt,
    MOTIF_KINDS, THEME_MOTIFS, drawThemeMotif,
    isCollidable, findApproaches, spawnExplosions, drawExplosions, clearExplosions,
    COLLISION_DIST_SCENE, COLLISION_COOLDOWN_MS, EXPLOSION_LIFETIME_MS, MAX_EXPLOSIONS,
    effectiveTime,
    findObjectAt,
    setTheme, kindStyle, mixHex, DISTANCE_BANDS, customObjectXY, addToScene,
    drawEarth, drawPlanetBody, planetRadius, bodyDiscR, syncLocalBodies, drawSun, drawMoon, drawGlyph, drawVignette, drawShootingStars, drawSunFlare,
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
    get CX()            { return CX; },
    set CX(v)           { CX = v; },
    get CY()            { return CY; },
    set CY(v)           { CY = v; },
    get SCALE()         { return SCALE; },
    set SCALE(v)        { SCALE = v; },
    get simMode()       { return simMode; },
    set simMode(v)      { simMode = v; },
    get simPaused()     { return simPaused; },
    set simPaused(v)    { simPaused = v; },
    get simStartReal()  { return simStartReal; },
    set simStartReal(v) { simStartReal = v; },
    get simStartEff()   { return simStartEff; },
    set simStartEff(v)  { simStartEff = v; },
    get nearPassEffectsEnabled() { return nearPassEffectsEnabled; },
    get forecastPaths() { return forecastPaths; },
    set forecastPaths(v){ forecastPaths = v; },
    get currentTheme()  { return currentTheme; },
    set currentTheme(v) { currentTheme = v; },
    get explosions()    { return explosions; },
    get separatedPairs(){ return separatedPairs; },
  };
}
