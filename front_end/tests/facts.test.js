/**
 * Object facts + the "Further info" placeholder link shown in the detail panel.
 */

const app = global._app;

describe('KIND_FACTS', () => {
  test('every rendered kind has a fact', () => {
    for (const kind of Object.keys(app.KIND_NAMES)) {
      expect(typeof app.KIND_FACTS[kind]).toBe('string');
      expect(app.KIND_FACTS[kind].length).toBeGreaterThan(0);
    }
  });
});

describe('detail panel facts', () => {
  test('shows the per-kind fact for a catalog object', () => {
    app.sceneObjects = [{ name: 'ISS (ZARYA)', kind: 'iss', x_norm: 0.1, y_norm: 0.1 }];
    app.objPositions = [{ x: 0, y: 0 }];
    app.showObjectInfo(0);
    expect(document.getElementById('obj-desc').textContent).toBe(app.KIND_FACTS.iss);
  });

  test("an object's own description wins over the per-kind fact", () => {
    app.sceneObjects = [{
      name: 'Mars', kind: 'planet', x_norm: 0.2, y_norm: 0.2,
      description: 'The red planet.',
    }];
    app.objPositions = [{ x: 0, y: 0 }];
    app.showObjectInfo(0);
    expect(document.getElementById('obj-desc').textContent).toBe('The red planet.');
  });

  test('the "Further info" placeholder link is present', () => {
    const link = document.getElementById('obj-info-link');
    expect(link).not.toBeNull();
    expect(link.textContent).toMatch(/further info/i);
    expect(link.getAttribute('href')).toBe('#'); // placeholder for later
  });
});
