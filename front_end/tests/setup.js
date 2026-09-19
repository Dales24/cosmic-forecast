/**
 * Jest setup — runs after the test framework is ready (setupFilesAfterEnv).
 * Scaffolds the DOM that app.js expects at load time, then loads the module.
 */

// ── DOM scaffold ──────────────────────────────────────────────────────────────
document.body.innerHTML = `
  <canvas id="space-map" width="800" height="600"></canvas>
  <button id="play-btn">&#9654; Play Simulation</button>
  <div id="sim-time" style="display:none"></div>
  <label for="near-pass-effects">
    <input id="near-pass-effects" type="checkbox">
    Cosmetic projected near-pass flashes
  </label>
  <details class="map-legend" open>
    <summary>Orbital Map</summary>
    <div class="map-legend-content">
      <ul id="legend-list"></ul>
    </div>
  </details>
  <div id="theme-switch">
    <select id="theme-select">
      <option value="default">Default</option>
      <option value="cosmic">Purple Cosmic</option>
      <option value="vangogh">Van Gogh</option>
      <option value="burton">Tim Burton</option>
      <option value="pirate">Pirate</option>
    </select>
  </div>
  <div id="form-view" style="display:block"></div>
  <div id="obj-view"  style="display:none"></div>
  <form id="scene-form">
    <input id="ra"           type="text">
    <input id="dec"          type="text">
    <input id="obs_datetime" type="datetime-local">
    <select id="debris-field">
      <option value="all">All supported fields</option>
      <option value="cosmos-2251">Cosmos 2251 debris</option>
      <option value="iridium-33">Iridium 33 debris</option>
      <option value="fengyun-1c">Fengyun 1C debris</option>
    </select>
    <input type="submit">
    <button type="button" id="clear-search">Clear</button>
  </form>
  <form id="add-object-form">
    <input id="add-name" type="text">
    <select id="add-kind"></select>
    <select id="add-band"></select>
    <input id="add-ra" type="number" value="90">
    <input type="submit">
  </form>
  <p id="add-object-note"></p>
  <div id="scene-result"></div>
  <p id="source-warning" role="status" hidden></p>
  <p id="scene-timestamp"></p>
  <p id="satellite-coverage"></p>
  <p id="rocket-body-coverage"></p>
  <div id="obj-title"></div>
  <div id="obj-class"></div>
  <div id="obj-conf"></div>
  <div id="conf-bar"       style="width:0%"></div>
  <div id="obj-group-wrap"></div>
  <div id="obj-x"></div>
  <div id="obj-y"></div>
  <div id="obj-dist"></div>
  <div id="obj-az"></div>
  <div id="obj-orbit"></div>
  <div id="obj-radius"></div>
  <div id="obj-kind"></div>
  <p id="obj-position-note" hidden></p>
  <p id="obj-motion-note" hidden></p>
  <div id="obj-about">
    <p id="obj-desc"></p>
    <a id="obj-info-link" href="#">Further info &rarr;</a>
  </div>
  <div id="upload-zone"></div>
  <input id="img-upload" type="file">
  <div id="upload-result" style="display:none"></div>
  <img  id="upload-preview">
  <div id="upload-class-name"></div>
  <div id="upload-group-wrap"></div>
  <span id="upload-conf-pct"></span>
  <div id="upload-conf-bar" style="width:0%"></div>
  <div id="csv-zone"></div>
  <input id="csv-upload" type="file">
  <div id="csv-result" class="csv-status" style="display:none"></div>
  <a id="csv-template-link" href="#"></a>
`;

// ── Mock browser APIs ─────────────────────────────────────────────────────────
Object.defineProperty(window, 'innerWidth',       { value: 800, writable: true });
Object.defineProperty(window, 'innerHeight',      { value: 600, writable: true });
Object.defineProperty(window, 'devicePixelRatio', { value: 1,   writable: true });

const _mockCtx = {
  setTransform: jest.fn(), fillRect: jest.fn(), beginPath: jest.fn(),
  arc: jest.fn(), fill: jest.fn(), stroke: jest.fn(),
  translate: jest.fn(), scale: jest.fn(), save: jest.fn(), restore: jest.fn(),
  ellipse: jest.fn(), moveTo: jest.fn(), lineTo: jest.fn(), setLineDash: jest.fn(),
  quadraticCurveTo: jest.fn(), bezierCurveTo: jest.fn(), closePath: jest.fn(),
  rotate: jest.fn(), clip: jest.fn(), drawImage: jest.fn(), rect: jest.fn(),
  createRadialGradient: jest.fn(() => ({ addColorStop: jest.fn() })),
  createLinearGradient: jest.fn(() => ({ addColorStop: jest.fn() })),
  fillStyle: '', strokeStyle: '', lineWidth: 1,
  globalAlpha: 1, shadowColor: '', shadowBlur: 0,
};
HTMLCanvasElement.prototype.getContext = jest.fn(() => _mockCtx);

global.requestAnimationFrame = jest.fn();
global.performance = { now: jest.fn(() => 0) };

// Default fetch mock (returns empty scene — prevents real network calls from init IIFE)
global.fetch = jest.fn(() => Promise.resolve({
  ok: true,
  json: () => Promise.resolve({ objects: [], predictions: [] }),
}));

// ── Shared browser constants (loaded first in every page, so first here too) ──
require('../static/config.js');

// ── Load app module ───────────────────────────────────────────────────────────
// jest.resetModules() is called between files, so the require is fresh each run.
const app = require('../static/app.js');
global._app = app;

// Reset the fetch mock after module load (the IIFE called it once)
beforeEach(() => {
  global.fetch = jest.fn(() => Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ objects: [], predictions: [] }),
  }));
});
