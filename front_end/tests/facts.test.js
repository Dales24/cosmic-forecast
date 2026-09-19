/**
 * Object facts + the per-kind "Learn more at NASA" link shown in the detail panel.
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

describe('KIND_LINKS', () => {
  test('every rendered kind links to an official NASA page', () => {
    for (const kind of Object.keys(app.KIND_NAMES)) {
      const url = app.KIND_LINKS[kind];
      expect(typeof url).toBe('string');
      expect(url).toMatch(/^https:\/\/[a-z.]*nasa\.gov\//);
    }
  });
});

describe('detail panel facts', () => {
  test('shows provenance notes and clears them on the next object', () => {
    app.sceneObjects = [
      { kind: 'near_earth_object', x_norm: 0.1, y_norm: 0.1,
        position_note: 'Illustrative placement', motion_note: 'Static in simulation' },
      { kind: 'satellite', x_norm: 0.1, y_norm: 0.1 },
    ];
    app.showObjectInfo(0);
    expect(document.getElementById('obj-position-note').textContent).toBe('Illustrative placement');
    expect(document.getElementById('obj-motion-note').hidden).toBe(false);
    app.showObjectInfo(1);
    expect(document.getElementById('obj-position-note').textContent).toBe('');
    expect(document.getElementById('obj-motion-note').hidden).toBe(true);
  });
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

  test('points the info link at the kind\'s NASA page, opening in a new tab', () => {
    app.sceneObjects = [{ name: '433 Eros', kind: 'asteroid', x_norm: 0.3, y_norm: 0.1 }];
    app.objPositions = [{ x: 0, y: 0 }];
    app.showObjectInfo(0);
    const link = document.getElementById('obj-info-link');
    expect(link.getAttribute('href')).toBe(app.KIND_LINKS.asteroid);
    expect(link.getAttribute('target')).toBe('_blank');
    expect(link.textContent).toMatch(/nasa/i);
    expect(link.style.display).not.toBe('none');
  });

  test('hides the info link when the kind has no NASA page', () => {
    app.sceneObjects = [{ name: 'Mystery', kind: 'made_up_kind', x_norm: 0.1, y_norm: 0.1 }];
    app.objPositions = [{ x: 0, y: 0 }];
    app.showObjectInfo(0);
    const link = document.getElementById('obj-info-link');
    expect(link.style.display).toBe('none');
    expect(link.hasAttribute('href')).toBe(false);
  });
});
