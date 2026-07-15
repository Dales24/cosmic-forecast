/**
 * Tests for the decorative planets: data integrity and that drawing them is a
 * pure visual pass (no throw, touches the canvas, never mutates scene state).
 */

const app = global._app;

describe('PLANETS data', () => {
  test('every planet has a position, radius, and full colour ramp', () => {
    expect(app.PLANETS.length).toBeGreaterThan(0);
    for (const p of app.PLANETS) {
      expect(typeof p.x).toBe('number');
      expect(typeof p.y).toBe('number');
      expect(p.r).toBeGreaterThan(0);
      for (const c of [p.hi, p.mid, p.lo]) {
        expect(c).toMatch(/^#[0-9a-f]{6}$/i);
      }
    }
  });

  test('planets sit off-centre so they never overlap Earth at the origin', () => {
    for (const p of app.PLANETS) {
      expect(Math.hypot(p.x, p.y)).toBeGreaterThan(0.05);
    }
  });

  test('the real solar-system planets are present, Mercury → Pluto', () => {
    const names = app.PLANETS.map((p) => p.name);
    for (const expected of [
      'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto',
    ]) {
      expect(names).toContain(expected);
    }
  });

  test('Jupiter is the largest disc; Saturn and Uranus are ringed', () => {
    const byName = Object.fromEntries(app.PLANETS.map((p) => [p.name, p]));
    const maxR = Math.max(...app.PLANETS.map((p) => p.r));
    expect(byName.Jupiter.r).toBe(maxR);
    expect(byName.Saturn.ring).toBeTruthy();
    expect(byName.Uranus.ring).toBeTruthy();
  });
});

describe('drawPlanets()', () => {
  const ctx = document.getElementById('space-map').getContext('2d');

  beforeEach(() => {
    for (const fn of Object.values(ctx)) {
      if (typeof fn === 'function' && fn.mockClear) fn.mockClear();
    }
  });

  test('renders without throwing and paints each planet disc', () => {
    expect(() => app.drawPlanets(400, 300, 500)).not.toThrow();
    // Each planet fills at least its sphere; expect one fill per planet minimum.
    expect(ctx.fill.mock.calls.length).toBeGreaterThanOrEqual(app.PLANETS.length);
  });

  test('is purely decorative — does not add scene objects', () => {
    app.sceneObjects = [];
    app.drawPlanets(400, 300, 500);
    expect(app.sceneObjects).toHaveLength(0);
  });

  test('ringed planets clip a front pass via rect', () => {
    const ringed = app.PLANETS.filter((p) => p.ring).length;
    app.drawPlanets(400, 300, 500);
    // One clipped rect per ringed planet's front ring pass.
    expect(ctx.rect.mock.calls.length).toBeGreaterThanOrEqual(ringed);
  });
});

describe('drawSun()', () => {
  const ctx = document.getElementById('space-map').getContext('2d');

  test('the Sun is upper-left, matching the scene light direction', () => {
    // Every body is lit from the upper-left, so the Sun must live there too.
    expect(app.SUN.x).toBeLessThan(0);
    expect(app.SUN.y).toBeLessThan(0);
    expect(app.SUN.r).toBeGreaterThan(0);
  });

  test('renders a corona and a disc without throwing', () => {
    ctx.fill.mockClear();
    expect(() => app.drawSun(400, 300, 500)).not.toThrow();
    expect(ctx.fill.mock.calls.length).toBeGreaterThanOrEqual(2); // corona + core
  });
});

describe('drawMoon()', () => {
  const ctx = document.getElementById('space-map').getContext('2d');

  test('the Moon sits close beside Earth at the origin', () => {
    expect(Math.hypot(app.MOON.x, app.MOON.y)).toBeLessThan(0.2);
    expect(app.MOON.r).toBeGreaterThan(0);
  });

  test('renders the disc plus craters without throwing', () => {
    ctx.fill.mockClear();
    expect(() => app.drawMoon(400, 300, 500)).not.toThrow();
    // Sphere fill + four crater fills at minimum.
    expect(ctx.fill.mock.calls.length).toBeGreaterThanOrEqual(5);
  });
});
