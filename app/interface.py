import sys
import os

import numpy as np
from flask import Flask, render_template_string, request, jsonify

# Add project root so `app.*` imports work when run from app/ directory
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)

app = Flask(__name__)

# ── Lazy CNN state ────────────────────────────────────────────────────────────
_cnn_model = None


def _get_cnn():
    global _cnn_model
    if _cnn_model is None:
        from app.object_classifier import create_cnn_model
        _cnn_model = create_cnn_model()
    return _cnn_model


# ── API routes ────────────────────────────────────────────────────────────────
@app.route("/api/classify/<int:obj_id>")
def classify_object(obj_id):
    from app.object_classifier import predict_patch
    cnn = _get_cnn()
    rng = np.random.default_rng(seed=obj_id * 137 + 42)
    patch = rng.integers(0, 255, size=(64, 64, 3), dtype=np.uint8)
    result = predict_patch(cnn, patch)
    return jsonify(result)


@app.route("/api/forecast", methods=["POST"])
def api_forecast():
    from app.trajectory_transformer import linear_extrapolation
    data = request.get_json(force=True)
    objects = data.get("objects", [])
    predictions = []
    for obj in objects:
        positions = np.array(obj["positions"], dtype=np.float32)
        if len(positions) < 2:
            continue
        forecast = linear_extrapolation(positions, horizon=50)
        predictions.append({
            "id": obj["id"],
            "waypoints": forecast[:, :2].tolist(),
        })
    return jsonify({"predictions": predictions})


# ── Data parser (optional) ────────────────────────────────────────────────────
try:
    from data_parser import get_data
    _has_data_parser = True
except Exception:
    _has_data_parser = False


# ── HTML ──────────────────────────────────────────────────────────────────────
HTML_FORM = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cosmic Forecast</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      min-height: 100vh;
      background: #02040a;
      color: #dce6ff;
      font-family: "Segoe UI", system-ui, sans-serif;
      overflow: hidden;
    }

    #space-map {
      position: fixed;
      inset: 0;
      width: 100%;
      height: 100%;
      z-index: 0;
    }

    .overlay {
      position: relative;
      z-index: 1;
      min-height: 100vh;
      display: grid;
      grid-template-columns: 1fr min(420px, 92vw);
      gap: 2rem;
      padding: 2rem;
      pointer-events: none;
    }

    .left-col {
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
      gap: 1rem;
      align-self: end;
      max-width: 320px;
      pointer-events: auto;
    }

    .panel {
      align-self: center;
      justify-self: end;
      width: 100%;
      padding: 1.75rem;
      border-radius: 16px;
      background: rgba(6, 10, 24, 0.72);
      border: 1px solid rgba(120, 160, 255, 0.3);
      box-shadow: 0 0 40px rgba(40, 80, 180, 0.15);
      backdrop-filter: blur(12px);
      pointer-events: auto;
    }

    .map-legend {
      padding: 1rem 1.25rem;
      border-radius: 12px;
      background: rgba(8, 14, 32, 0.55);
      border: 1px solid rgba(120, 160, 255, 0.25);
      backdrop-filter: blur(8px);
    }

    .map-legend h2 {
      font-size: 0.85rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #8eb4ff;
      margin-bottom: 0.75rem;
    }

    .map-legend ul {
      list-style: none;
      font-size: 0.9rem;
      line-height: 1.8;
    }

    .map-legend li::before { content: "●"; margin-right: 0.5rem; }
    .map-legend li.earth::before  { color: #4da3ff; }
    .map-legend li.orbit::before  { color: rgba(140, 180, 255, 0.6); }
    .map-legend li.object::before { color: #ffd166; }
    .map-legend li.debris::before { color: #ff6b6b; }

    /* Play controls */
    .controls {
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
    }

    #play-btn {
      width: 100%;
      padding: 0.75rem 1rem;
      border: 1px solid rgba(120, 160, 255, 0.45);
      border-radius: 10px;
      background: rgba(8, 14, 40, 0.75);
      color: #dce6ff;
      font-size: 0.95rem;
      font-weight: 600;
      letter-spacing: 0.04em;
      cursor: pointer;
      backdrop-filter: blur(8px);
      transition: background 0.2s, border-color 0.2s;
    }

    #play-btn:hover { background: rgba(50, 80, 160, 0.55); border-color: #6ea0ff; }
    #play-btn.playing { background: rgba(60, 20, 80, 0.65); border-color: #c084fc; color: #e9d5ff; }

    #sim-time {
      display: none;
      text-align: center;
      font-size: 0.85rem;
      color: #c084fc;
      letter-spacing: 0.08em;
      padding: 0.4rem 0.8rem;
      border-radius: 8px;
      background: rgba(80, 20, 100, 0.35);
      border: 1px solid rgba(192, 132, 252, 0.3);
    }

    /* Panel header */
    h1 {
      font-size: 1.5rem;
      font-weight: 600;
      letter-spacing: 0.04em;
      margin-bottom: 0.35rem;
    }

    .subtitle {
      font-size: 0.9rem;
      color: #8ea8d8;
      margin-bottom: 1.5rem;
    }

    label {
      display: block;
      font-size: 0.8rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: #8eb4ff;
      margin-bottom: 0.35rem;
    }

    input[type="text"] {
      width: 100%;
      padding: 0.65rem 0.85rem;
      margin-bottom: 1rem;
      border-radius: 8px;
      border: 1px solid rgba(120, 160, 255, 0.35);
      background: rgba(2, 6, 18, 0.85);
      color: #eef3ff;
      font-size: 0.95rem;
    }

    input[type="text"]:focus {
      outline: none;
      border-color: #6ea0ff;
      box-shadow: 0 0 0 3px rgba(110, 160, 255, 0.2);
    }

    input[type="submit"] {
      width: 100%;
      padding: 0.75rem;
      border: none;
      border-radius: 8px;
      background: linear-gradient(135deg, #3d6bff, #6b4dff);
      color: #fff;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      letter-spacing: 0.04em;
    }

    input[type="submit"]:hover { filter: brightness(1.08); }

    .results {
      margin-top: 1.5rem;
      padding-top: 1.25rem;
      border-top: 1px solid rgba(120, 160, 255, 0.2);
    }

    .results h3 {
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #8eb4ff;
      margin-bottom: 0.75rem;
    }

    .results p, .results pre {
      font-size: 0.9rem;
      line-height: 1.5;
      color: #c8d8f8;
      white-space: pre-wrap;
      word-break: break-word;
    }

    /* Object info view */
    #obj-view { display: none; }

    .obj-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1.25rem;
    }

    .obj-title {
      font-size: 1.3rem;
      font-weight: 700;
      letter-spacing: 0.06em;
    }

    .back-btn {
      background: none;
      border: 1px solid rgba(120, 160, 255, 0.35);
      color: #8eb4ff;
      font-size: 0.8rem;
      padding: 0.3rem 0.7rem;
      border-radius: 6px;
      cursor: pointer;
    }
    .back-btn:hover { background: rgba(60, 100, 200, 0.2); }

    .obj-section {
      margin-bottom: 1.2rem;
    }

    .obj-section-title {
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: #8eb4ff;
      margin-bottom: 0.5rem;
      padding-bottom: 0.3rem;
      border-bottom: 1px solid rgba(120, 160, 255, 0.15);
    }

    .obj-row {
      display: flex;
      justify-content: space-between;
      font-size: 0.88rem;
      line-height: 1.9;
      color: #c8d8f8;
    }

    .obj-row .key { color: #7a9acc; }
    .obj-row .val { font-family: "SF Mono", "Fira Code", monospace; color: #e4eeff; }

    .obj-class-badge {
      display: inline-block;
      margin-top: 0.25rem;
      padding: 0.2rem 0.6rem;
      border-radius: 12px;
      font-size: 0.78rem;
      font-weight: 600;
      letter-spacing: 0.05em;
    }

    .badge-natural   { background: rgba(100,200,100,0.15); color: #7ee787; border: 1px solid rgba(100,200,100,0.3); }
    .badge-artificial{ background: rgba(100,150,255,0.15); color: #93c5fd; border: 1px solid rgba(100,150,255,0.3); }
    .badge-deep_space{ background: rgba(167,139,250,0.15); color: #c4b5fd; border: 1px solid rgba(167,139,250,0.3); }

    .hint {
      margin-top: 1.2rem;
      font-size: 0.78rem;
      color: #5a7099;
      line-height: 1.5;
    }

    .conf-bar-wrap {
      height: 4px;
      background: rgba(120,160,255,0.12);
      border-radius: 2px;
      margin-top: 0.4rem;
      overflow: hidden;
    }

    .conf-bar {
      height: 100%;
      border-radius: 2px;
      background: linear-gradient(90deg, #3d6bff, #a78bfa);
      transition: width 0.4s ease;
    }

    @media (max-width: 900px) {
      body { overflow: auto; }
      .overlay { grid-template-columns: 1fr; padding: 1rem; }
      .left-col { order: 2; max-width: 100%; }
      .panel { order: 1; justify-self: stretch; }
    }
  </style>
</head>
<body>
  <canvas id="space-map" aria-label="Space orbital map"></canvas>

  <div class="overlay">

    <!-- Left column: legend + play controls -->
    <div class="left-col">
      <div class="map-legend">
        <h2>Orbital Map</h2>
        <ul>
          <li class="earth">Earth (center)</li>
          <li class="orbit">Orbital paths</li>
          <li class="object">Tracked objects</li>
          <li class="debris">Debris &amp; NEOs</li>
        </ul>
      </div>

      <div class="controls">
        <button id="play-btn">&#9654; Play Simulation</button>
        <div id="sim-time">T+0h 00m 00s</div>
      </div>
    </div>

    <!-- Right column: form / object detail panel -->
    <div class="panel">

      <!-- Default: forecast form -->
      <div id="form-view">
        <h1>Cosmic Forecast</h1>
        <p class="subtitle">Click any object on the map to inspect it, or run a forecast below.</p>

        <form method="post">
          <label for="location">Observation Location</label>
          <input id="location" type="text" name="location" placeholder="e.g. Houston, TX">

          <label for="prediction">Prediction Window</label>
          <input id="prediction" type="text" name="prediction" placeholder="e.g. 2025-08-14">

          <input type="submit" value="Run Forecast">
        </form>

        {% if location and prediction %}
        <div class="results">
          <h3>Submitted Values</h3>
          <p>Location: {{ location }}</p>
          <p>Prediction: {{ prediction }}</p>
        </div>
        {% endif %}

        {% if data_result %}
        <div class="results">
          <h3>Forecast Result</h3>
          <pre>{{ data_result }}</pre>
        </div>
        {% endif %}
      </div>

      <!-- Object detail view (shown on click) -->
      <div id="obj-view">
        <div class="obj-header">
          <div class="obj-title" id="obj-title">Object #1</div>
          <button class="back-btn" onclick="hideObjectInfo()">&#8592; Back</button>
        </div>

        <div class="obj-section">
          <div class="obj-section-title">Classification</div>
          <div class="obj-row">
            <span class="key">Class</span>
            <span class="val" id="obj-class">&#8212;</span>
          </div>
          <div id="obj-group-wrap" style="margin-top:0.35rem"></div>
          <div class="obj-row" style="margin-top:0.5rem">
            <span class="key">Confidence</span>
            <span class="val" id="obj-conf">&#8212;</span>
          </div>
          <div class="conf-bar-wrap">
            <div class="conf-bar" id="conf-bar" style="width:0%"></div>
          </div>
        </div>

        <div class="obj-section">
          <div class="obj-section-title">Coordinates</div>
          <div class="obj-row">
            <span class="key">X offset</span>
            <span class="val" id="obj-x">&#8212;</span>
          </div>
          <div class="obj-row">
            <span class="key">Y offset</span>
            <span class="val" id="obj-y">&#8212;</span>
          </div>
          <div class="obj-row">
            <span class="key">Distance</span>
            <span class="val" id="obj-dist">&#8212;</span>
          </div>
          <div class="obj-row">
            <span class="key">Azimuth</span>
            <span class="val" id="obj-az">&#8212;</span>
          </div>
        </div>

        <div class="obj-section">
          <div class="obj-section-title">Orbit</div>
          <div class="obj-row">
            <span class="key">Orbit index</span>
            <span class="val" id="obj-orbit">&#8212;</span>
          </div>
          <div class="obj-row">
            <span class="key">Radius</span>
            <span class="val" id="obj-radius">&#8212;</span>
          </div>
          <div class="obj-row">
            <span class="key">Kind</span>
            <span class="val" id="obj-kind">&#8212;</span>
          </div>
        </div>

        <p class="hint">Press <strong>&#9654; Play Simulation</strong> to fast-forward paths and see ML-predicted trajectories.</p>
      </div>

    </div>
  </div>

  <script>
    // ── Scene parameters (must match draw functions below) ──────────────────
    const orbits = [
      { radius: 0.14, speed: 0.0008, tilt:  0.2  },
      { radius: 0.22, speed: 0.0005, tilt: -0.15 },
      { radius: 0.31, speed: 0.00035,tilt:  0.35 },
      { radius: 0.42, speed: 0.00025,tilt: -0.25 },
    ];

    const OBJECTS = [
      { orbit: 0, angle: 0.4, size: 4, color: "#ffd166", kind: "object" },
      { orbit: 1, angle: 2.1, size: 3, color: "#7ee787", kind: "object" },
      { orbit: 1, angle: 4.8, size: 3, color: "#ff6b6b", kind: "debris" },
      { orbit: 2, angle: 1.2, size: 5, color: "#ffd166", kind: "object" },
      { orbit: 2, angle: 5.0, size: 3, color: "#ff6b6b", kind: "debris" },
      { orbit: 3, angle: 3.3, size: 4, color: "#a78bfa", kind: "object" },
    ];

    // ── Canvas setup ─────────────────────────────────────────────────────────
    const canvas = document.getElementById("space-map");
    const ctx = canvas.getContext("2d");

    const stars = [];
    let CX = 0, CY = 0, SCALE = 1;   // updated each frame, read by click handler

    // ── Mutable scene state ──────────────────────────────────────────────────
    const objPositions = OBJECTS.map(() => ({ x: 0, y: 0 }));
    let hoveredIdx = null;
    let selectedIdx = null;
    const classCache = {};

    // ── Simulation state ─────────────────────────────────────────────────────
    let simMode = false;
    let simStartReal = 0;
    let simStartEff = 0;
    const SIM_SPEED = 200;          // 200× real time
    let forecastPaths = null;       // [{id, waypoints: [[xn,yn], ...]}]
    let forecasting = false;

    function effectiveTime(real) {
      if (!simMode) return real;
      return simStartEff + (real - simStartReal) * SIM_SPEED;
    }

    // ── Stars ────────────────────────────────────────────────────────────────
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

    // ── Draw helpers ──────────────────────────────────────────────────────────
    function drawBackground() {
      const w = window.innerWidth, h = window.innerHeight;
      const g = ctx.createRadialGradient(w*.5,h*.45,0,w*.5,h*.45,Math.max(w,h)*.75);
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

    function objectAngle(obj, time) {
      return obj.angle + time * orbits[obj.orbit].speed * 1000;
    }

    function objectXY(obj, time, cx, cy, scale) {
      const o = orbits[obj.orbit];
      const angle = objectAngle(obj, time);
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
        // draw endpoint dot
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

        // selection ring
        if (i === selectedIdx) {
          ctx.strokeStyle = obj.color;
          ctx.lineWidth = 1.5;
          ctx.globalAlpha = 0.75;
          ctx.beginPath(); ctx.arc(x, y, obj.size + 7, 0, Math.PI * 2); ctx.stroke();
          ctx.globalAlpha = 1;
        }

        // hover ring
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

    // ── Main loop ─────────────────────────────────────────────────────────────
    function frame(realTime) {
      const w = window.innerWidth, h = window.innerHeight;
      CX = w * 0.42; CY = h * 0.5; SCALE = Math.min(w, h) * 0.95;
      const t = effectiveTime(realTime);

      drawBackground();
      drawOrbitalPaths(CX, CY, SCALE);
      drawEarth(CX, CY, SCALE);
      drawForecastPaths(CX, CY, SCALE);
      drawObjects(CX, CY, SCALE, t);

      if (simMode) {
        const elapsed = (realTime - simStartReal) * SIM_SPEED / 1000;
        const h_ = Math.floor(elapsed / 3600);
        const m_ = Math.floor((elapsed % 3600) / 60);
        const s_ = Math.floor(elapsed % 60);
        const timeEl = document.getElementById("sim-time");
        timeEl.textContent =
          "T+" + h_ + "h " + String(m_).padStart(2,"0") + "m " + String(s_).padStart(2,"0") + "s";
      }

      requestAnimationFrame(frame);
    }

    // ── Resize ────────────────────────────────────────────────────────────────
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

    // ── Hit testing ───────────────────────────────────────────────────────────
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

    // ── Object info panel ────────────────────────────────────────────────────
    function showObjectInfo(idx) {
      selectedIdx = idx;
      const p = objPositions[idx];
      const obj = OBJECTS[idx];
      const o = orbits[obj.orbit];

      const xn = (p.x - CX) / SCALE;
      const yn = (p.y - CY) / SCALE;
      const dist = Math.hypot(xn, yn);
      const az = (Math.atan2(yn, xn) * 180 / Math.PI).toFixed(1);

      document.getElementById("obj-title").textContent = "Object #" + (idx + 1);
      document.getElementById("obj-x").textContent    = (xn >= 0 ? "+" : "") + xn.toFixed(4) + " u";
      document.getElementById("obj-y").textContent    = (yn >= 0 ? "+" : "") + yn.toFixed(4) + " u";
      document.getElementById("obj-dist").textContent = dist.toFixed(4) + " u";
      document.getElementById("obj-az").textContent   = az + "°";
      document.getElementById("obj-orbit").textContent = "#" + (obj.orbit + 1);
      document.getElementById("obj-radius").textContent = o.radius.toFixed(2) + " u";
      document.getElementById("obj-kind").textContent  = obj.kind;
      document.getElementById("obj-class").textContent = "Loading…";
      document.getElementById("obj-conf").textContent  = "—";
      document.getElementById("conf-bar").style.width  = "0%";
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
        '<span class="obj-class-badge ' + badgeClass + '">' + c.group.replace("_", " ") + '</span>';
    }

    function hideObjectInfo() {
      selectedIdx = null;
      document.getElementById("obj-view").style.display  = "none";
      document.getElementById("form-view").style.display = "block";
    }

    // ── Forecast / play ───────────────────────────────────────────────────────
    async function fetchForecast(realTime) {
      const effTime = effectiveTime(realTime);
      const payload = OBJECTS.map((obj, idx) => {
        const o = orbits[obj.orbit];
        const positions = [];
        for (let step = 7; step >= 0; step--) {
          const t = effTime - step * 400;
          const angle = obj.angle + t * o.speed * 1000;
          const rx = o.radius;
          const ry = o.radius * (1 - Math.abs(o.tilt) * 0.35);
          positions.push([
            Math.cos(angle) * rx,
            Math.sin(angle) * ry,
            t / 1000,
          ]);
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

    const playBtn = document.getElementById("play-btn");
    const simTimeEl = document.getElementById("sim-time");

    playBtn.addEventListener("click", async () => {
      if (forecasting) return;

      if (simMode) {
        simMode = false;
        forecastPaths = null;
        playBtn.textContent = "▶ Play Simulation";
        playBtn.classList.remove("playing");
        simTimeEl.style.display = "none";
        return;
      }

      forecasting = true;
      playBtn.textContent = "⏳ Computing…";

      const realNow = performance.now();
      try {
        const result = await fetchForecast(realNow);
        forecastPaths = result.predictions;
      } catch (e) {
        forecastPaths = null;
      }

      simMode = true;
      simStartReal = performance.now();
      simStartEff  = performance.now();
      forecasting  = false;
      playBtn.textContent = "⏹ Stop Simulation";
      playBtn.classList.add("playing");
      simTimeEl.style.display = "block";
      simTimeEl.textContent = "T+0h 00m 00s";
    });
  </script>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    location = prediction = data_result = None
    if request.method == "POST":
        location = request.form.get("location")
        prediction = request.form.get("prediction")
        if _has_data_parser:
            try:
                data_result = get_data(location, prediction)
            except Exception as e:
                data_result = f"Error: {e}"
        else:
            data_result = "Data parser not configured (settings.ini missing)."
    return render_template_string(
        HTML_FORM, location=location, prediction=prediction, data_result=data_result
    )


if __name__ == "__main__":
    app.run(debug=True)
