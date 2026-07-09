/**
 * Tests for pure utility constants and functions exported by app.js.
 */

const app = global._app;

// ── esc() ─────────────────────────────────────────────────────────────────────

describe('esc()', () => {
  test('escapes ampersand', () => {
    expect(app.esc('a & b')).toBe('a &amp; b');
  });
  test('escapes less-than', () => {
    expect(app.esc('<script>')).toBe('&lt;script&gt;');
  });
  test('escapes greater-than', () => {
    expect(app.esc('a > b')).toBe('a &gt; b');
  });
  test('escapes all three in one string', () => {
    expect(app.esc('<b>Hello & World</b>')).toBe('&lt;b&gt;Hello &amp; World&lt;/b&gt;');
  });
  test('returns unchanged string with no special chars', () => {
    expect(app.esc('Hello World 123')).toBe('Hello World 123');
  });
  test('handles empty string', () => {
    expect(app.esc('')).toBe('');
  });
});

// ── KIND_STYLES ───────────────────────────────────────────────────────────────

describe('KIND_STYLES', () => {
  const EXPECTED_KINDS = [
    'iss', 'satellite', 'space_debris', 'rocket_body',
    'asteroid', 'comet', 'near_earth_object', 'meteor', 'meteoroid',
    'galaxy', 'nebula', 'star_cluster', 'variable_star', 'ufo',
  ];

  test.each(EXPECTED_KINDS)('%s has a style entry', kind => {
    expect(app.KIND_STYLES[kind]).toBeDefined();
  });

  test('every style has a positive size', () => {
    Object.entries(app.KIND_STYLES).forEach(([kind, s]) => {
      expect(s.size).toBeGreaterThan(0);
    });
  });

  test('every style has a hex color', () => {
    Object.entries(app.KIND_STYLES).forEach(([, s]) => {
      expect(s.color).toMatch(/^#[0-9a-fA-F]{6}$/);
    });
  });

  test('ufo is neon green', () => {
    expect(app.KIND_STYLES.ufo.color.toLowerCase()).toBe('#00ff88');
  });

  test('iss is larger than satellite', () => {
    expect(app.KIND_STYLES.iss.size).toBeGreaterThan(app.KIND_STYLES.satellite.size);
  });
});

// ── KIND_NAMES ────────────────────────────────────────────────────────────────

describe('KIND_NAMES', () => {
  test('every KIND_STYLES key has a name', () => {
    Object.keys(app.KIND_STYLES).forEach(kind => {
      expect(app.KIND_NAMES[kind]).toBeDefined();
      expect(typeof app.KIND_NAMES[kind]).toBe('string');
      expect(app.KIND_NAMES[kind].length).toBeGreaterThan(0);
    });
  });

  test('ufo name contains alien emoji', () => {
    expect(app.KIND_NAMES.ufo).toContain('\u{1F47D}');
  });

  test('iss name is "ISS"', () => {
    expect(app.KIND_NAMES.iss).toBe('ISS');
  });
});

// ── SIM_SPEED ─────────────────────────────────────────────────────────────────

describe('SIM_SPEED', () => {
  test('is 200', () => {
    expect(app.SIM_SPEED).toBe(200);
  });
});

// ── HIT_RADIUS ────────────────────────────────────────────────────────────────

describe('HIT_RADIUS', () => {
  test('is a positive number', () => {
    expect(app.HIT_RADIUS).toBeGreaterThan(0);
  });
});

// ── CSV_TEMPLATE ──────────────────────────────────────────────────────────────

describe('CSV_TEMPLATE', () => {
  test('is a non-empty string', () => {
    expect(typeof app.CSV_TEMPLATE).toBe('string');
    expect(app.CSV_TEMPLATE.length).toBeGreaterThan(0);
  });

  test('first line is the header', () => {
    const header = app.CSV_TEMPLATE.split('\n')[0];
    expect(header).toBe('id,name,kind,x,y,timestamp');
  });

  test('contains required columns in header', () => {
    const header = app.CSV_TEMPLATE.split('\n')[0].split(',');
    ['id', 'x', 'y', 'timestamp'].forEach(col => {
      expect(header).toContain(col);
    });
  });

  test('each object id appears at least twice', () => {
    const lines = app.CSV_TEMPLATE.split('\n').filter(l => l && !l.startsWith('id'));
    const counts = {};
    lines.forEach(l => {
      const id = l.split(',')[0];
      if (id) counts[id] = (counts[id] || 0) + 1;
    });
    Object.values(counts).forEach(n => expect(n).toBeGreaterThanOrEqual(2));
  });

  test('x and y values are numeric', () => {
    const lines = app.CSV_TEMPLATE.split('\n').filter(l => l && !l.startsWith('id'));
    lines.forEach(l => {
      const parts = l.split(',');
      expect(Number.isFinite(parseFloat(parts[3]))).toBe(true); // x
      expect(Number.isFinite(parseFloat(parts[4]))).toBe(true); // y
    });
  });
});
