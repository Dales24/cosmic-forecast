/**
 * Tests for updateLegend() — DOM output and filter behaviour.
 */

const app = global._app;

// The legend always appends 2 static items (Earth + Orbital paths) after the "All" row.
const STATIC_ROWS = 2;

function getLegendItems() {
  return Array.from(document.querySelectorAll('#legend-list li'));
}

function getDynamicItems() {
  return getLegendItems().filter(li => !li.classList.contains('earth') && !li.classList.contains('orbit'));
}

function resetScene(...kinds) {
  app.sceneObjects = kinds.map((k, i) => ({
    id: `obj${i}`, name: `Obj ${i}`, kind: k,
    x_norm: 0, y_norm: 0, vx_norm: 0, vy_norm: 0, source: 'test',
  }));
  app.filterKind = null;
}

describe('updateLegend()', () => {
  beforeEach(() => {
    document.getElementById('legend-list').innerHTML = '';
    app.filterKind = null;
  });

  // ── Structure ──────────────────────────────────────────────────────────────

  test('empty scene shows only "All Objects" dynamic row', () => {
    app.sceneObjects = [];
    app.updateLegend();
    const items = getDynamicItems();
    expect(items).toHaveLength(1);
    expect(items[0].className).toContain('filter-all');
  });

  test('one kind produces two dynamic rows (All + that kind)', () => {
    resetScene('satellite');
    app.updateLegend();
    expect(getDynamicItems()).toHaveLength(2);
  });

  test('deduplicates kinds — two satellites → one kind dynamic row', () => {
    resetScene('satellite', 'satellite');
    app.updateLegend();
    expect(getDynamicItems()).toHaveLength(2);  // All + satellite
  });

  test('each unique kind gets its own row', () => {
    resetScene('satellite', 'asteroid', 'ufo');
    app.updateLegend();
    expect(getDynamicItems()).toHaveLength(4);  // All + 3 kinds
  });

  test('each kind row has the data-kind attribute', () => {
    resetScene('satellite', 'ufo');
    app.updateLegend();
    const kinds = getDynamicItems()
      .filter(li => !li.classList.contains('filter-all'))
      .map(li => li.dataset.kind);
    expect(kinds).toContain('satellite');
    expect(kinds).toContain('ufo');
  });

  test('"All Objects" row has filter-all class', () => {
    resetScene('satellite');
    app.updateLegend();
    const allRow = getDynamicItems().find(li => li.classList.contains('filter-all'));
    expect(allRow).not.toBeUndefined();
  });

  test('kind row has kind-filter class', () => {
    resetScene('asteroid');
    app.updateLegend();
    const kindRows = getDynamicItems().filter(li => !li.classList.contains('filter-all'));
    kindRows.forEach(li => expect(li.classList.contains('kind-filter')).toBe(true));
  });

  test('kind row shows human-readable name from KIND_NAMES', () => {
    resetScene('ufo');
    app.updateLegend();
    const kindRow = getLegendItems().find(li => li.dataset && li.dataset.kind === 'ufo');
    expect(kindRow).not.toBeUndefined();
    expect(kindRow.textContent).toContain('Unidentified');
  });

  test('color dot uses KIND_STYLES color', () => {
    resetScene('satellite');
    app.updateLegend();
    const kindRow = getLegendItems().find(li => li.dataset && li.dataset.kind === 'satellite');
    // The colored element is a <span> with inline color style.
    // jsdom normalizes hex to rgb(), so check the style string contains the expected hex.
    const dot = kindRow.querySelector('span[style]');
    expect(dot).not.toBeNull();
    // Set the expected color on a dummy element and compare to jsdom's normalized form.
    const dummy = document.createElement('span');
    dummy.style.color = app.KIND_STYLES.satellite.color;
    expect(dot.style.color).toBe(dummy.style.color);
  });

  // ── Click — filter ON ──────────────────────────────────────────────────────

  test('clicking a kind row sets filterKind to that kind', () => {
    resetScene('satellite', 'asteroid');
    app.updateLegend();
    const kindRow = getLegendItems().find(li => li.dataset && li.dataset.kind === 'satellite');
    kindRow.click();
    expect(app.filterKind).toBe('satellite');
  });

  test('clicking the same kind twice toggles filterKind back to null', () => {
    resetScene('satellite');
    app.updateLegend();
    const kindRow = getLegendItems().find(li => li.dataset && li.dataset.kind === 'satellite');
    kindRow.click();
    expect(app.filterKind).toBe('satellite');
    kindRow.click();
    expect(app.filterKind).toBeNull();
  });

  // ── Click — "All Objects" resets ───────────────────────────────────────────

  test('clicking "All Objects" resets filterKind to null', () => {
    resetScene('satellite');
    app.filterKind = 'satellite';
    app.updateLegend();
    const allRow = getLegendItems().find(li => li.classList.contains('filter-all'));
    allRow.click();
    expect(app.filterKind).toBeNull();
  });

  test('clicking "All Objects" when already null keeps null', () => {
    resetScene('satellite');
    app.filterKind = null;
    app.updateLegend();
    const allRow = getLegendItems().find(li => li.classList.contains('filter-all'));
    allRow.click();
    expect(app.filterKind).toBeNull();
  });

  // ── Active state styling ───────────────────────────────────────────────────

  test('active filter row has "active" class', () => {
    resetScene('satellite', 'ufo');
    app.filterKind = 'satellite';
    app.updateLegend();
    const kindRow = getLegendItems().find(li => li.dataset && li.dataset.kind === 'satellite');
    expect(kindRow.classList.contains('active')).toBe(true);
  });

  test('inactive filter rows do not have "active" class', () => {
    resetScene('satellite', 'ufo');
    app.filterKind = 'satellite';
    app.updateLegend();
    const ufoRow = getLegendItems().find(li => li.dataset && li.dataset.kind === 'ufo');
    expect(ufoRow.classList.contains('active')).toBe(false);
  });

  test('"All Objects" row is active when filterKind is null', () => {
    resetScene('satellite');
    app.filterKind = null;
    app.updateLegend();
    const allRow = getLegendItems().find(li => li.classList.contains('filter-all'));
    expect(allRow.classList.contains('active')).toBe(true);
  });

  test('"All Objects" row is not active when a filter is set', () => {
    resetScene('satellite');
    app.filterKind = 'satellite';
    app.updateLegend();
    const allRow = getLegendItems().find(li => li.classList.contains('filter-all'));
    expect(allRow.classList.contains('active')).toBe(false);
  });
});

describe('map legend panel', () => {
  const panel = document.querySelector('.map-legend');

  test('uses an accessible native disclosure that starts expanded', () => {
    expect(panel.tagName).toBe('DETAILS');
    expect(panel.open).toBe(true);
    expect(panel.querySelector('summary').textContent).toMatch(/orbital map/i);
  });

  test('can be collapsed without removing the legend contents', () => {
    panel.open = false;
    expect(panel.open).toBe(false);
    expect(panel.querySelector('#legend-list')).not.toBeNull();
    panel.open = true;
  });
});
