/**
 * Tests for the planets. They are now scene objects (positions come from the
 * backend); PLANET_STYLES only carries how each body is drawn, and
 * drawPlanetBody paints one disc at a given screen position.
 */

const app = global._app;

const PLANET_NAMES = ['Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune'];

describe('PLANET_STYLES data', () => {
  test('every planet style has a radius and full colour ramp', () => {
    const names = Object.keys(app.PLANET_STYLES);
    expect(names.length).toBeGreaterThan(0);
    for (const name of names) {
      const p = app.PLANET_STYLES[name];
      expect(p.r).toBeGreaterThan(0);
      for (const c of [p.hi, p.mid, p.lo]) {
        expect(c).toMatch(/^#[0-9a-f]{6}$/i);
      }
    }
  });

  test('the seven planets are present, Mercury → Neptune', () => {
    for (const expected of PLANET_NAMES) {
      expect(app.PLANET_STYLES[expected]).toBeTruthy();
    }
  });

  test('Jupiter is the largest disc; Saturn and Uranus are ringed', () => {
    const maxR = Math.max(...Object.values(app.PLANET_STYLES).map((p) => p.r));
    expect(app.PLANET_STYLES.Jupiter.r).toBe(maxR);
    expect(app.PLANET_STYLES.Saturn.ring).toBeTruthy();
    expect(app.PLANET_STYLES.Uranus.ring).toBeTruthy();
  });

  test('planetRadius returns the disc radius, and 0 for an unknown name', () => {
    expect(app.planetRadius('Jupiter')).toBe(app.PLANET_STYLES.Jupiter.r);
    expect(app.planetRadius('Nibiru')).toBe(0);
  });
});

describe('drawPlanetBody()', () => {
  const ctx = document.getElementById('space-map').getContext('2d');

  beforeEach(() => {
    for (const fn of Object.values(ctx)) {
      if (typeof fn === 'function' && fn.mockClear) fn.mockClear();
    }
  });

  test('renders a known planet without throwing and paints its disc', () => {
    expect(() => app.drawPlanetBody('Jupiter', 400, 300, 500)).not.toThrow();
    expect(ctx.fill.mock.calls.length).toBeGreaterThanOrEqual(1);
  });

  test('an unknown planet name is a no-op', () => {
    expect(() => app.drawPlanetBody('Nibiru', 400, 300, 500)).not.toThrow();
    expect(ctx.fill.mock.calls.length).toBe(0);
  });

  test('is purely visual — does not add scene objects', () => {
    app.sceneObjects = [];
    app.drawPlanetBody('Mars', 400, 300, 500);
    expect(app.sceneObjects).toHaveLength(0);
  });

  test('a ringed planet clips a front pass via rect', () => {
    app.drawPlanetBody('Saturn', 400, 300, 500);
    expect(ctx.rect.mock.calls.length).toBeGreaterThanOrEqual(1);
  });
});

describe('planet hit-testing', () => {
  test('a planet is clickable across its whole disc, not just the centre', () => {
    app.sceneObjects = [{ name: 'Jupiter', kind: 'planet', x_norm: 0, y_norm: 0 }];
    // drawSceneObjects records a disc-sized hit radius for planets.
    app.objPositions = [{ x: 100, y: 100, hit: 40 }];
    // 30px from centre: inside the 40px disc, beyond the 20px default reach.
    expect(app.findObjectAt(130, 100)).toBe(0);
  });

  test('a click well outside the disc still misses', () => {
    app.sceneObjects = [{ name: 'Jupiter', kind: 'planet', x_norm: 0, y_norm: 0 }];
    app.objPositions = [{ x: 100, y: 100, hit: 40 }];
    expect(app.findObjectAt(200, 100)).toBe(-1);
  });
});

describe('local bodies (Sun / Earth / Moon)', () => {
  test('bodyDiscR gives disc radii for drawn bodies, 0 for glyph kinds', () => {
    expect(app.bodyDiscR({ kind: 'sun' })).toBe(app.SUN.r);
    expect(app.bodyDiscR({ kind: 'moon' })).toBe(app.MOON.r);
    expect(app.bodyDiscR({ kind: 'earth' })).toBeGreaterThan(0);
    expect(app.bodyDiscR({ kind: 'planet', name: 'Jupiter' }))
      .toBe(app.PLANET_STYLES.Jupiter.r);
    expect(app.bodyDiscR({ kind: 'satellite' })).toBe(0);
  });

  test('syncLocalBodies points the Sun/Moon artwork at their scene positions', () => {
    app.sceneObjects = [
      { kind: 'sun', name: 'Sun', x_norm: 0.5, y_norm: -0.3 },
      { kind: 'moon', name: 'Moon', x_norm: 0.2, y_norm: 0.1 },
    ];
    app.syncLocalBodies();
    expect([app.SUN.x, app.SUN.y]).toEqual([0.5, -0.3]);
    expect([app.MOON.x, app.MOON.y]).toEqual([0.2, 0.1]);
  });

  test('every local-body kind has a style and a display name', () => {
    for (const kind of ['sun', 'earth', 'moon']) {
      expect(app.KIND_STYLES[kind]).toBeDefined();
      expect(app.KIND_NAMES[kind]).toBeTruthy();
    }
  });

  test('a body is clickable across its disc, not just the centre', () => {
    app.sceneObjects = [{ name: 'Earth', kind: 'earth', x_norm: 0, y_norm: 0 }];
    app.objPositions = [{ x: 100, y: 100, hit: 30 }];
    expect(app.findObjectAt(120, 100)).toBe(0);   // 20px in — inside the disc
    expect(app.findObjectAt(200, 100)).toBe(-1);  // far away — miss
  });
});

describe('drawSun()', () => {
  const ctx = document.getElementById('space-map').getContext('2d');

  test('the Sun has a draw radius and numeric position', () => {
    // The Sun now sits at its real position (synced from the scene), not a
    // fixed spot, so only its draw radius is invariant.
    expect(app.SUN.r).toBeGreaterThan(0);
    expect(Number.isFinite(app.SUN.x)).toBe(true);
    expect(Number.isFinite(app.SUN.y)).toBe(true);
  });

  test('renders a corona and a disc without throwing', () => {
    ctx.fill.mockClear();
    expect(() => app.drawSun(400, 300, 500)).not.toThrow();
    expect(ctx.fill.mock.calls.length).toBeGreaterThanOrEqual(2); // corona + core
  });
});

describe('drawMoon()', () => {
  const ctx = document.getElementById('space-map').getContext('2d');

  test('the Moon has a draw radius and numeric position', () => {
    // The Moon is synced to its real scene position, so only its draw radius
    // is invariant.
    expect(app.MOON.r).toBeGreaterThan(0);
    expect(Number.isFinite(app.MOON.x)).toBe(true);
    expect(Number.isFinite(app.MOON.y)).toBe(true);
  });

  test('renders the disc plus craters without throwing', () => {
    ctx.fill.mockClear();
    expect(() => app.drawMoon(400, 300, 500)).not.toThrow();
    // Sphere fill + four crater fills at minimum.
    expect(ctx.fill.mock.calls.length).toBeGreaterThanOrEqual(5);
  });
});
