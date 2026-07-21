/**
 * User-added scene objects: distance-band → position math, appending to the
 * scene, and that the form is wired up.
 */

const app = global._app;

describe('customObjectXY', () => {
  test('distance bands run from near Earth to the deep sky', () => {
    const bands = Object.values(app.DISTANCE_BANDS);
    expect(Math.min(...bands)).toBeLessThan(0.2);   // LEO
    expect(Math.max(...bands)).toBeGreaterThan(0.9); // deep sky
  });

  test('band + right ascension map to the right point', () => {
    const r = app.DISTANCE_BANDS['Low orbit (LEO)'];
    const east = app.customObjectXY('Low orbit (LEO)', 0);
    expect(east.x).toBeCloseTo(r);
    expect(east.y).toBeCloseTo(0);
    const north = app.customObjectXY('Low orbit (LEO)', 90);
    expect(north.x).toBeCloseTo(0);
    expect(north.y).toBeCloseTo(r);
  });
});

describe('addToScene', () => {
  test('appends the object and keeps objPositions in step', () => {
    app.sceneObjects = [];
    app.objPositions = [];
    app.addToScene({ name: 'My Probe', kind: 'satellite', x_norm: 0.1, y_norm: 0.1 });
    expect(app.sceneObjects).toHaveLength(1);
    expect(app.sceneObjects[0].name).toBe('My Probe');
    expect(app.objPositions).toHaveLength(1);
  });
});

describe('add-object form', () => {
  test('populates the type and distance dropdowns on init', () => {
    const kinds = document.getElementById('add-kind');
    const bands = document.getElementById('add-band');
    expect(kinds.options.length).toBeGreaterThan(0);
    expect(bands.options.length).toBe(Object.keys(app.DISTANCE_BANDS).length);
    // Singleton bodies are not offered as addable types.
    const values = [...kinds.options].map((o) => o.value);
    expect(values).not.toContain('sun');
    expect(values).toContain('satellite');
  });
});
