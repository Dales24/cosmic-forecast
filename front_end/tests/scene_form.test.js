/**
 * Tests for loading a scene at a chosen date/time: the load result the button
 * reports back, and loadScene()'s success/failure signal.
 */

const app = global._app;

// ── sceneResultHTML() ─────────────────────────────────────────────────────────

describe('sceneResultHTML()', () => {
  test('reports the time and object count on success', () => {
    const html = app.sceneResultHTML('', '', '2026-12-25 00:00', { ok: true, count: 42 });
    expect(html).toContain('Loaded Scene');
    expect(html).toContain('2026-12-25 00:00 UTC');
    expect(html).toContain('42 objects loaded');
  });

  test('renders without coordinates, which are optional', () => {
    const html = app.sceneResultHTML('', '', '2026-12-25 00:00', { ok: true, count: 1 });
    expect(html).not.toContain('RA:');
    expect(html).toContain('1 object loaded'); // singular
  });

  test('includes coordinates when both are given', () => {
    const html = app.sceneResultHTML('83.82', '-5.39', '2026-12-25 00:00', { ok: true, count: 2 });
    expect(html).toContain('83.82');
    expect(html).toContain('-5.39');
  });

  test('says so when the load failed instead of claiming a scene', () => {
    const html = app.sceneResultHTML('', '', '2026-12-25 00:00', { ok: false, count: 7 });
    expect(html).toContain('Scene Failed to Load');
    expect(html).not.toContain('Loaded Scene');
  });

  test('escapes coordinates rather than injecting markup', () => {
    const html = app.sceneResultHTML('<img>', '<b>', '2026-12-25 00:00', { ok: true, count: 0 });
    expect(html).not.toContain('<img>');
    expect(html).toContain('&lt;img&gt;');
  });
});

// ── loadScene() ───────────────────────────────────────────────────────────────

describe('loadScene()', () => {
  test('shows scene time and stale element metadata, clearing on recovery', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({
      objects: [], datetime: '2025-01-01T00:00:00Z', source_freshness: [{
        kind: 'satellite', stale: true, downloaded_at: 1735689600,
        oldest_epoch: '2024-01-01T00:00:00Z',
      }],
    }) });
    await app.loadScene('2025-01-01T00:00:00Z');
    const warning = document.getElementById('source-warning');
    expect(warning.hidden).toBe(false);
    expect(warning.textContent).toContain('Using cached orbital data');
    expect(warning.textContent).toContain('over 7 days old');
    expect(document.getElementById('scene-timestamp').textContent).toContain('2025-01-01');
    global.fetch.mockResolvedValue({ ok: true, json: async () => ({ objects: [] }) });
    await app.loadScene();
    expect(warning.hidden).toBe(true);
  });
  test('shows missing sources and clears the notice after recovery', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ objects: [], source_warnings: [
        { source: 'celestrak', kind: 'satellite' },
      ] }),
    });
    expect((await app.loadScene('2026-12-25T00:00:00Z')).ok).toBe(true);
    const notice = document.getElementById('source-warning');
    expect(notice.hidden).toBe(false);
    expect(notice.textContent).toContain('Map incomplete');
    expect(notice.textContent).toContain('Satellite (celestrak)');
    global.fetch.mockResolvedValue({
      ok: true, json: async () => ({ objects: [], source_warnings: [] }),
    });
    await app.loadScene('2026-12-26T00:00:00Z');
    expect(notice.hidden).toBe(true);
    expect(notice.textContent).toBe('');
  });
  test('sends the chosen datetime to the API and reports the count', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ objects: [{ id: 'a' }, { id: 'b' }] }),
    }));

    const result = await app.loadScene('2026-12-25T00:00:00Z');

    expect(global.fetch.mock.calls[0][0]).toContain('datetime_str=2026-12-25T00%3A00%3A00Z');
    expect(result.ok).toBe(true);
    expect(result.count).toBe(2);
    expect(result.search).toBeNull();
  });

  test('reports failure on a non-OK response, keeping the previous scene', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: false,
      status: 422,
      json: () => Promise.resolve({ detail: 'bad datetime' }),
    }));

    const result = await app.loadScene('not-a-date');
    expect(result.ok).toBe(false);
  });

  test('reports failure when the network throws', async () => {
    global.fetch = jest.fn(() => Promise.reject(new Error('offline')));

    const result = await app.loadScene('2026-12-25T00:00:00Z');
    expect(result.ok).toBe(false);
  });
});

// ── Position search ───────────────────────────────────────────────────────────

describe('position search', () => {
  const okScene = (body) => jest.fn(() => Promise.resolve({
    ok: true,
    json: () => Promise.resolve(body),
  }));

  test('sends ra and dec when both are given', async () => {
    global.fetch = okScene({ objects: [], search: { matched: 0, searched: 9, radius_deg: 30 } });

    await app.loadScene('2026-12-25T00:00:00Z', { ra: '83.82', dec: '-5.39' });

    const url = global.fetch.mock.calls[0][0];
    expect(url).toContain('ra=83.82');
    expect(url).toContain('dec=-5.39');
  });

  test('omits both when only one coordinate is given', async () => {
    global.fetch = okScene({ objects: [] });

    await app.loadScene('2026-12-25T00:00:00Z', { ra: '83.82', dec: '' });

    const url = global.fetch.mock.calls[0][0];
    expect(url).not.toContain('ra=');
    expect(url).not.toContain('dec=');
  });

  test('passes the search tally back to the caller', async () => {
    global.fetch = okScene({ objects: [{ id: 'a' }], search: { matched: 1, searched: 40, radius_deg: 30 } });

    const result = await app.loadScene('2026-12-25T00:00:00Z', { ra: '10', dec: '0' });
    expect(result.search).toEqual({ matched: 1, searched: 40, radius_deg: 30 });
  });

  test('result panel reports the searched patch, not a plain load', () => {
    const html = app.sceneResultHTML('10', '0', '2026-12-25 00:00', {
      ok: true, count: 1, search: { matched: 1, searched: 40, radius_deg: 30 },
    });
    expect(html).toContain('Position Search');
    expect(html).toContain('within 30');
    expect(html).toContain('1 of 40 objects');
  });

  test('an empty patch of sky reads as a result, not a failure', () => {
    const html = app.sceneResultHTML('10', '0', '2026-12-25 00:00', {
      ok: true, count: 0, search: { matched: 0, searched: 40, radius_deg: 5 },
    });
    expect(html).toContain('0 of 40 objects');
    expect(html).not.toContain('Failed');
  });
});

// ── Invalid input ─────────────────────────────────────────────────────────────

describe('invalid search input', () => {
  test('a 422 is reported as bad input, not an unreachable catalog', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: false,
      status: 422,
      json: () => Promise.resolve({ detail: "ra must be a number, got 'abc'" }),
    }));

    const result = await app.loadScene('2026-12-25T00:00:00Z', { ra: 'abc', dec: '0' });
    expect(result.ok).toBe(false);
    expect(result.invalid).toBe(true);
    expect(result.error).toContain('ra must be a number');

    const html = app.sceneResultHTML('abc', '0', '2026-12-25 00:00', result);
    expect(html).toContain('Check Your Search');
    expect(html).toContain('ra must be a number');
    expect(html).not.toContain('Could not reach the catalogs');
  });

  test('a 5xx is still reported as an unreachable catalog', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: false, status: 503, json: () => Promise.resolve({}),
    }));

    const result = await app.loadScene('2026-12-25T00:00:00Z');
    expect(result.invalid).toBe(false);

    const html = app.sceneResultHTML('', '', '2026-12-25 00:00', result);
    expect(html).toContain('Could not reach the catalogs');
  });

  test('escapes the server message rather than injecting it', () => {
    const html = app.sceneResultHTML('', '', '2026-12-25 00:00', {
      ok: false, invalid: true, error: '<img src=x>',
    });
    expect(html).not.toContain('<img src=x>');
    expect(html).toContain('&lt;img');
  });

  test('validationDetail falls back when the body is not the expected shape', async () => {
    expect(await app.validationDetail({
      status: 422, json: () => Promise.reject(new Error('not json')),
    })).toContain('422');

    expect(await app.validationDetail({
      status: 422, json: () => Promise.resolve({ detail: [{ msg: 'field required' }] }),
    })).toBe('field required');
  });
});

// ── Framing the search on the map ─────────────────────────────────────────────

describe('focusOnObjects()', () => {
  beforeEach(() => {
    app.resetView();
    app.SCALE = 600; app.CX = 400; app.CY = 300;
  });

  test('does nothing when there is nothing to frame', () => {
    expect(app.focusOnObjects([])).toBe(false);
    expect(app.zoom).toBe(1);
  });

  test('zooms in on a tight cluster', () => {
    const framed = app.focusOnObjects([
      { x_norm: 0.30, y_norm: 0.30 },
      { x_norm: 0.34, y_norm: 0.34 },
    ]);
    expect(framed).toBe(true);
    expect(app.zoom).toBeGreaterThan(1);
  });

  test('centres the cluster in the viewport', () => {
    app.focusOnObjects([
      { x_norm: 0.20, y_norm: 0.10 },
      { x_norm: 0.40, y_norm: 0.30 },
    ]);
    // Midpoint (0.30, 0.20) must land at the centre of the window.
    const screenX = app.panX + (app.CX + 0.30 * app.SCALE) * app.zoom;
    const screenY = app.panY + (app.CY + 0.20 * app.SCALE) * app.zoom;
    expect(screenX).toBeCloseTo(window.innerWidth / 2, 6);
    expect(screenY).toBeCloseTo(window.innerHeight / 2, 6);
  });

  test('never exceeds the zoom range the wheel allows', () => {
    app.focusOnObjects([{ x_norm: 0.5, y_norm: 0.5 }]); // single point
    expect(app.zoom).toBeLessThanOrEqual(12);
    expect(app.zoom).toBeGreaterThanOrEqual(0.15);
  });

  test('bails out before the first frame has sized the scene', () => {
    app.SCALE = 0;
    expect(app.focusOnObjects([{ x_norm: 0.1, y_norm: 0.1 }])).toBe(false);
  });
});

describe('view reset', () => {
  test('a search frames the map, a plain load restores the whole sky', async () => {
    app.SCALE = 600; app.CX = 400; app.CY = 300;

    global.fetch = jest.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        objects: [{ x_norm: 0.3, y_norm: 0.3 }, { x_norm: 0.32, y_norm: 0.32 }],
        search: { matched: 2, searched: 100, radius_deg: 10 },
      }),
    }));
    await app.loadScene('2026-12-25T00:00:00Z', { ra: '10', dec: '0' });
    expect(app.zoom).toBeGreaterThan(1);

    global.fetch = jest.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ objects: [{ x_norm: 0.3, y_norm: 0.3 }] }),
    }));
    await app.loadScene('2026-12-25T00:00:00Z');
    expect(app.zoom).toBe(1);
    expect(app.panX).toBe(0);
    expect(app.panY).toBe(0);
  });
});

// ── Clear button ──────────────────────────────────────────────────────────────

describe('clear button', () => {
  test('empties the coordinates, resets the view, and reloads the whole sky', async () => {
    document.getElementById('ra').value  = '83.82';
    document.getElementById('dec').value = '-5.39';
    app.SCALE = 600; app.CX = 400; app.CY = 300;
    app.zoom = 6; app.panX = 120; app.panY = 90;

    global.fetch = jest.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ objects: [{ x_norm: 0.1, y_norm: 0.1 }] }),
    }));

    document.getElementById('clear-search').click();
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(document.getElementById('ra').value).toBe('');
    expect(document.getElementById('dec').value).toBe('');
    expect(app.zoom).toBe(1);
    expect(app.panX).toBe(0);

    const url = global.fetch.mock.calls[0][0];
    expect(url).not.toContain('ra=');
    expect(document.getElementById('scene-result').innerHTML).toContain('Loaded Scene');
  });
});
