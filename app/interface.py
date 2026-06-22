from flask import Flask, render_template_string, request
from data_parser import get_data

app = Flask(__name__)

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

    .map-legend,
    .panel {
      pointer-events: auto;
    }

    .map-legend {
      align-self: end;
      padding: 1rem 1.25rem;
      border-radius: 12px;
      background: rgba(8, 14, 32, 0.55);
      border: 1px solid rgba(120, 160, 255, 0.25);
      backdrop-filter: blur(8px);
      max-width: 320px;
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

    .map-legend li::before {
      content: "●";
      margin-right: 0.5rem;
    }

    .map-legend li.earth::before { color: #4da3ff; }
    .map-legend li.orbit::before { color: rgba(140, 180, 255, 0.6); }
    .map-legend li.object::before { color: #ffd166; }
    .map-legend li.debris::before { color: #ff6b6b; }

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
    }

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

    input[type="submit"]:hover {
      filter: brightness(1.08);
    }

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

    .results p,
    .results pre {
      font-size: 0.9rem;
      line-height: 1.5;
      color: #c8d8f8;
      white-space: pre-wrap;
      word-break: break-word;
    }

    @media (max-width: 900px) {
      body { overflow: auto; }
      .overlay {
        grid-template-columns: 1fr;
        padding: 1rem;
      }
      .map-legend { order: 2; }
      .panel { order: 1; justify-self: stretch; }
    }
  </style>
</head>
<body>
  <canvas id="space-map" aria-label="Space orbital map"></canvas>

  <div class="overlay">
    <div class="map-legend">
      <h2>Orbital Map</h2>
      <ul>
        <li class="earth">Earth (center)</li>
        <li class="orbit">Orbital paths</li>
        <li class="object">Tracked objects</li>
        <li class="debris">Debris &amp; NEOs</li>
      </ul>
    </div>

    <div class="panel">
      <h1>Cosmic Forecast</h1>
      <p class="subtitle">Predict object paths across the space map</p>

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
  </div>

  <script>
    const canvas = document.getElementById("space-map");
    const ctx = canvas.getContext("2d");

    const stars = [];
    const orbits = [
      { radius: 0.14, speed: 0.0008, tilt: 0.2 },
      { radius: 0.22, speed: 0.0005, tilt: -0.15 },
      { radius: 0.31, speed: 0.00035, tilt: 0.35 },
      { radius: 0.42, speed: 0.00025, tilt: -0.25 },
    ];
    const objects = [
      { orbit: 0, angle: 0.4, size: 4, color: "#ffd166", kind: "object" },
      { orbit: 1, angle: 2.1, size: 3, color: "#7ee787", kind: "object" },
      { orbit: 1, angle: 4.8, size: 3, color: "#ff6b6b", kind: "debris" },
      { orbit: 2, angle: 1.2, size: 5, color: "#ffd166", kind: "object" },
      { orbit: 2, angle: 5.0, size: 3, color: "#ff6b6b", kind: "debris" },
      { orbit: 3, angle: 3.3, size: 4, color: "#a78bfa", kind: "object" },
    ];

    function resize() {
      canvas.width = window.innerWidth * devicePixelRatio;
      canvas.height = window.innerHeight * devicePixelRatio;
      canvas.style.width = window.innerWidth + "px";
      canvas.style.height = window.innerHeight + "px";
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    }

    function initStars(count) {
      stars.length = 0;
      for (let i = 0; i < count; i++) {
        stars.push({
          x: Math.random(),
          y: Math.random(),
          r: Math.random() * 1.4 + 0.3,
          twinkle: Math.random() * Math.PI * 2,
        });
      }
    }

    function drawBackground() {
      const w = window.innerWidth;
      const h = window.innerHeight;
      const gradient = ctx.createRadialGradient(w * 0.5, h * 0.45, 0, w * 0.5, h * 0.45, Math.max(w, h) * 0.75);
      gradient.addColorStop(0, "#0a1030");
      gradient.addColorStop(0.45, "#050818");
      gradient.addColorStop(1, "#010208");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, w, h);

      for (const star of stars) {
        const alpha = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(star.twinkle));
        ctx.fillStyle = `rgba(220, 230, 255, ${alpha})`;
        ctx.beginPath();
        ctx.arc(star.x * w, star.y * h, star.r, 0, Math.PI * 2);
        ctx.fill();
        star.twinkle += 0.015 + Math.random() * 0.01;
      }
    }

    function drawEarth(cx, cy, scale) {
      const earthRadius = scale * 0.045;

      const glow = ctx.createRadialGradient(cx, cy, earthRadius * 0.5, cx, cy, earthRadius * 3);
      glow.addColorStop(0, "rgba(77, 163, 255, 0.35)");
      glow.addColorStop(1, "rgba(77, 163, 255, 0)");
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(cx, cy, earthRadius * 3, 0, Math.PI * 2);
      ctx.fill();

      const earthGrad = ctx.createRadialGradient(cx - earthRadius * 0.3, cy - earthRadius * 0.3, earthRadius * 0.2, cx, cy, earthRadius);
      earthGrad.addColorStop(0, "#7ec8ff");
      earthGrad.addColorStop(0.55, "#2b6cb0");
      earthGrad.addColorStop(1, "#0a2240");
      ctx.fillStyle = earthGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, earthRadius, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = "rgba(140, 200, 255, 0.5)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(cx, cy, earthRadius, 0, Math.PI * 2);
      ctx.stroke();
    }

    function drawOrbits(cx, cy, scale) {
      for (const orbit of orbits) {
        const rx = scale * orbit.radius;
        const ry = scale * orbit.radius * (1 - Math.abs(orbit.tilt) * 0.35);

        ctx.strokeStyle = "rgba(120, 170, 255, 0.22)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.ellipse(cx, cy, rx, ry, orbit.tilt, 0, Math.PI * 2);
        ctx.stroke();
      }
    }

    function drawObjects(cx, cy, scale, time) {
      for (const obj of objects) {
        const orbit = orbits[obj.orbit];
        const angle = obj.angle + time * orbit.speed * 1000;
        const rx = scale * orbit.radius;
        const ry = scale * orbit.radius * (1 - Math.abs(orbit.tilt) * 0.35);
        const x = cx + Math.cos(angle) * rx;
        const y = cy + Math.sin(angle) * ry;

        ctx.fillStyle = obj.color;
        ctx.shadowColor = obj.color;
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(x, y, obj.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      }
    }

    function frame(time) {
      const w = window.innerWidth;
      const h = window.innerHeight;
      const cx = w * 0.42;
      const cy = h * 0.5;
      const scale = Math.min(w, h) * 0.95;

      drawBackground();
      drawOrbits(cx, cy, scale);
      drawEarth(cx, cy, scale);
      drawObjects(cx, cy, scale, time);
      requestAnimationFrame(frame);
    }

    window.addEventListener("resize", () => {
      resize();
      initStars(320);
    });

    resize();
    initStars(320);
    requestAnimationFrame(frame);
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
        try:
            data_result = get_data(location, prediction)
        except Exception as e:
            data_result = f"Error: {e}"
    return render_template_string(
        HTML_FORM, location=location, prediction=prediction, data_result=data_result
    )


if __name__ == "__main__":
    app.run(debug=True)
