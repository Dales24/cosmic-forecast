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
