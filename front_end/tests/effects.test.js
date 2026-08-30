/**
 * Tests for the scene effects: per-theme animated motifs, collision detection,
 * and the explosion bursts collisions spawn.
 */

const app = global._app;

const moving = (x, y) => ({ kind: 'satellite', vx_norm: 0.01, vy_norm: 0, x_norm: x, y_norm: y });
const still  = (x, y) => ({ kind: 'galaxy', vx_norm: 0, vy_norm: 0, x_norm: x, y_norm: y });

// ── Theme motifs ──────────────────────────────────────────────────────────────

describe('theme motifs', () => {
  const themeNames = Object.keys(app.THEMES);

  test('every theme declares a motif and an explosion colour', () => {
    for (const name of themeNames) {
      const theme = app.THEMES[name];
      expect(theme).toHaveProperty('motif');
      expect(theme.explosionColor).toMatch(/^#[0-9a-f]{6}$/i);
    }
  });

  test('every named motif resolves to a real renderer', () => {
    for (const name of themeNames) {
      const motif = app.THEMES[name].motif;
      if (motif !== null) {
        expect(typeof app.THEME_MOTIFS[motif]).toBe('function');
      }
    }
  });

  test('each theme has a distinct look on the objects', () => {
    const motifs = themeNames.map((n) => app.THEMES[n].motif);
    expect(new Set(motifs).size).toBe(motifs.length);
  });

  test('pirate uses the ship-wheel motif', () => {
    expect(app.THEMES.pirate.motif).toBe('wheel');
  });

  test('only moving object kinds are decorated', () => {
    // Deep-sky objects would be cluttered by an ornament and never move.
    expect(app.MOTIF_KINDS.has('satellite')).toBe(true);
    expect(app.MOTIF_KINDS.has('iss')).toBe(true);
    expect(app.MOTIF_KINDS.has('galaxy')).toBe(false);
    expect(app.MOTIF_KINDS.has('planet')).toBe(false);
  });

  test('drawThemeMotif skips kinds that carry no ornament', () => {
    app.currentTheme = app.THEMES.pirate;
    expect(app.drawThemeMotif('galaxy', 10, 10, 3, 0, '#fff')).toBe(false);
  });

  test('drawThemeMotif draws for a decorated kind', () => {
    app.currentTheme = app.THEMES.pirate;
    expect(app.drawThemeMotif('satellite', 10, 10, 3, 0, '#fff')).toBe(true);
  });

  test('the default theme stays undecorated', () => {
    app.currentTheme = app.THEMES.default;
    expect(app.drawThemeMotif('satellite', 10, 10, 3, 0, '#fff')).toBe(false);
  });

  test('every motif renderer runs without throwing', () => {
    for (const render of Object.values(app.THEME_MOTIFS)) {
      expect(() => render(50, 50, 4, 1.23, '#ff8a3d')).not.toThrow();
    }
  });
});

// ── Collision detection ───────────────────────────────────────────────────────

describe('findApproaches()', () => {
  const apart = (...keys) => new Set(keys);

  test('fires when a pair that was apart comes together', () => {
    const objects = [moving(0, 0), moving(0, 0)];
    const positions = [{ x: 100, y: 100 }, { x: 102, y: 100 }];
    expect(app.findApproaches(objects, positions, 5, apart('0:1'))).toHaveLength(1);
  });

  test('does NOT fire for objects that were together all along', () => {
    // Docked ISS modules and formation-flying Starlinks sit on top of each
    // other from frame one — they never approach, so they must never explode.
    const objects = [moving(0, 0), moving(0, 0)];
    const positions = [{ x: 100, y: 100 }, { x: 100, y: 100 }];
    expect(app.findApproaches(objects, positions, 5, new Set())).toEqual([]);
  });

  test('marks a distant pair as separated so a later approach can fire', () => {
    const objects = [moving(0, 0), moving(0, 0)];
    const separated = new Set();
    app.findApproaches(objects, [{ x: 0, y: 0 }, { x: 500, y: 0 }], 5, separated);
    expect(separated.has('0:1')).toBe(true);

    const events = app.findApproaches(objects, [{ x: 0, y: 0 }, { x: 1, y: 0 }], 5, separated);
    expect(events).toHaveLength(1);
  });

  test('will not fire twice without drifting apart in between', () => {
    const objects = [moving(0, 0), moving(0, 0)];
    const positions = [{ x: 0, y: 0 }, { x: 1, y: 0 }];
    const separated = apart('0:1');
    expect(app.findApproaches(objects, positions, 5, separated)).toHaveLength(1);
    expect(app.findApproaches(objects, positions, 5, separated)).toEqual([]);
  });

  test('reports the midpoint, where the burst belongs', () => {
    const objects = [moving(0, 0), moving(0, 0)];
    const positions = [{ x: 100, y: 100 }, { x: 104, y: 108 }];
    const [hit] = app.findApproaches(objects, positions, 20, apart('0:1'));
    expect(hit.x).toBe(102);
    expect(hit.y).toBe(104);
  });

  test('static objects never collide', () => {
    // Two galaxies at the same spot are a projection artifact, not an event.
    const objects = [still(0, 0), still(0, 0)];
    const positions = [{ x: 100, y: 100 }, { x: 100, y: 100 }];
    expect(app.findApproaches(objects, positions, 5, apart('0:1'))).toEqual([]);
  });

  test('a moving object does not collide with a static one', () => {
    const objects = [moving(0, 0), still(0, 0)];
    const positions = [{ x: 100, y: 100 }, { x: 100, y: 100 }];
    expect(app.findApproaches(objects, positions, 5, apart('0:1'))).toEqual([]);
  });

  test('never pairs an object with itself, and reports each pair once', () => {
    const objects = [moving(0, 0), moving(0, 0), moving(0, 0)];
    const positions = [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 2, y: 0 }];
    const hits = app.findApproaches(objects, positions, 50, apart('0:1', '0:2', '1:2'));
    expect(hits).toHaveLength(3); // 0-1, 0-2, 1-2
    for (const hit of hits) expect(hit.i).toBeLessThan(hit.j);
  });

  test('tolerates missing positions', () => {
    const objects = [moving(0, 0), moving(0, 0)];
    const positions = [undefined, { x: 0, y: 0 }];
    expect(() => app.findApproaches(objects, positions, 5, new Set())).not.toThrow();
    expect(app.findApproaches(objects, positions, 5, new Set())).toEqual([]);
  });

  test('handles an empty scene', () => {
    expect(app.findApproaches([], [], 5, new Set())).toEqual([]);
  });
});

describe('isCollidable()', () => {
  test('needs real velocity', () => {
    expect(app.isCollidable({ vx_norm: 0.1, vy_norm: 0 })).toBe(true);
    expect(app.isCollidable({ vx_norm: 0, vy_norm: 0.1 })).toBe(true);
    expect(app.isCollidable({ vx_norm: 0, vy_norm: 0 })).toBe(false);
    expect(app.isCollidable({})).toBe(false);
    expect(app.isCollidable(null)).toBe(false);
  });
});

// ── Explosions ────────────────────────────────────────────────────────────────

describe('explosions', () => {
  beforeEach(() => app.clearExplosions());

  test('a collision spawns a burst', () => {
    app.spawnExplosions([{ i: 0, j: 1, x: 10, y: 20 }], 1000, '#ff8a3d');
    expect(app.explosions).toHaveLength(1);
    expect(app.explosions[0]).toMatchObject({ x: 10, y: 20, color: '#ff8a3d' });
  });

  test('the same pair does not spawn again during its cooldown', () => {
    const hit = [{ i: 0, j: 1, x: 10, y: 20 }];
    app.spawnExplosions(hit, 1000, '#fff');
    app.spawnExplosions(hit, 1000 + app.COLLISION_COOLDOWN_MS - 1, '#fff');
    expect(app.explosions).toHaveLength(1);
  });

  test('the same pair can explode again once the cooldown passes', () => {
    const hit = [{ i: 0, j: 1, x: 10, y: 20 }];
    app.spawnExplosions(hit, 1000, '#fff');
    app.spawnExplosions(hit, 1000 + app.COLLISION_COOLDOWN_MS + 1, '#fff');
    expect(app.explosions).toHaveLength(2);
  });

  test('different pairs each get their own burst', () => {
    app.spawnExplosions([
      { i: 0, j: 1, x: 0, y: 0 },
      { i: 2, j: 3, x: 5, y: 5 },
    ], 1000, '#fff');
    expect(app.explosions).toHaveLength(2);
  });

  test('a debris cascade cannot spawn unbounded bursts', () => {
    const many = Array.from({ length: 100 }, (_, n) => ({ i: n, j: n + 1, x: n, y: 0 }));
    app.spawnExplosions(many, 1000, '#fff');
    expect(app.explosions.length).toBeLessThanOrEqual(app.MAX_EXPLOSIONS);
  });

  test('a burst is removed once its lifetime is up', () => {
    app.spawnExplosions([{ i: 0, j: 1, x: 10, y: 20 }], 1000, '#fff');
    app.drawExplosions(1000 + app.EXPLOSION_LIFETIME_MS / 2, 600);
    expect(app.explosions).toHaveLength(1); // still burning

    app.drawExplosions(1000 + app.EXPLOSION_LIFETIME_MS + 1, 600);
    expect(app.explosions).toHaveLength(0);
  });

  test('drawing an empty set is a no-op', () => {
    expect(() => app.drawExplosions(1000, 600)).not.toThrow();
  });

  test('clearExplosions resets the separation state too', () => {
    app.separatedPairs.add('0:1');
    app.clearExplosions();
    expect(app.separatedPairs.size).toBe(0);
  });

  test('clearExplosions also clears the cooldown, so reused indices can fire', () => {
    const hit = [{ i: 0, j: 1, x: 10, y: 20 }];
    app.spawnExplosions(hit, 1000, '#fff');
    app.clearExplosions();
    app.spawnExplosions(hit, 1001, '#fff'); // inside the old cooldown window
    expect(app.explosions).toHaveLength(1);
  });

  test('loading a new scene clears in-flight bursts', async () => {
    app.spawnExplosions([{ i: 0, j: 1, x: 10, y: 20 }], 1000, '#fff');
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ objects: [] }),
    }));
    await app.loadScene('2026-12-25T00:00:00Z');
    expect(app.explosions).toHaveLength(0);
  });
});
