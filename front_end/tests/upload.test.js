/**
 * Tests for classifyUploadFile() and handleCSVUpload().
 */

const app = global._app;

// ── classifyUploadFile() ──────────────────────────────────────────────────────

describe('classifyUploadFile()', () => {
  let mockFileReader;

  beforeEach(() => {
    document.getElementById('upload-result').style.display = 'none';
    document.getElementById('upload-class-name').textContent = '';
    document.getElementById('upload-conf-pct').textContent   = '';
    document.getElementById('upload-conf-bar').style.width   = '0%';
    document.getElementById('upload-group-wrap').innerHTML   = '';

    // Mock FileReader so readAsDataURL triggers onload synchronously
    mockFileReader = {
      readAsDataURL: jest.fn(function () {
        if (this.onload) this.onload({ target: { result: 'data:image/png;base64,abc' } });
      }),
      onload: null,
    };
    jest.spyOn(global, 'FileReader').mockImplementation(() => mockFileReader);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('shows upload result block on success', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ class: 'Satellite', group: 'artificial', confidence: 0.9 }),
    }));

    const file = new File(['data'], 'img.png', { type: 'image/png' });
    await app.classifyUploadFile(file);

    expect(document.getElementById('upload-result').style.display).toBe('block');
  });

  test('fills class name from response', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ class: 'Galaxy', group: 'deep_space', confidence: 0.72 }),
    }));

    const file = new File(['data'], 'img.png', { type: 'image/png' });
    await app.classifyUploadFile(file);

    expect(document.getElementById('upload-class-name').textContent).toBe('Galaxy');
  });

  test('formats confidence as percentage', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ class: 'Asteroid', group: 'natural', confidence: 0.854 }),
    }));

    const file = new File(['data'], 'img.png', { type: 'image/png' });
    await app.classifyUploadFile(file);

    expect(document.getElementById('upload-conf-pct').textContent).toBe('85.4%');
    expect(document.getElementById('upload-conf-bar').style.width).toBe('85.4%');
  });

  test('renders group badge with correct class', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ class: 'ISS', group: 'artificial', confidence: 0.95 }),
    }));

    const file = new File(['data'], 'img.png', { type: 'image/png' });
    await app.classifyUploadFile(file);

    const wrap = document.getElementById('upload-group-wrap');
    expect(wrap.querySelector('.badge-artificial')).not.toBeNull();
  });

  test('shows "Classification failed" on fetch error', async () => {
    global.fetch = jest.fn(() => Promise.reject(new Error('net err')));

    const file = new File(['data'], 'img.png', { type: 'image/png' });
    await app.classifyUploadFile(file);

    expect(document.getElementById('upload-class-name').textContent).toBe('Classification failed');
  });

  test('POSTs to /api/classify/upload', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ class: 'Nebula', group: 'deep_space', confidence: 0.6 }),
    }));

    const file = new File(['data'], 'img.png', { type: 'image/png' });
    await app.classifyUploadFile(file);

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/classify/upload',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  test('sets preview src immediately', () => {
    global.fetch = jest.fn(() => new Promise(() => {}));  // never resolves
    const file = new File(['data'], 'img.png', { type: 'image/png' });
    app.classifyUploadFile(file);
    expect(document.getElementById('upload-preview').src).toContain('data:image');
  });
});

// ── handleCSVUpload() ─────────────────────────────────────────────────────────

const MOCK_CSV_RESPONSE = {
  objects: [
    { id: 'SAT1', name: 'My Sat', kind: 'satellite',
      x_norm: 0.12, y_norm: -0.05, vx_norm: 1e-5, vy_norm: -1e-5, source: 'upload' },
  ],
  predictions: [{ id: 0, waypoints: [[0.13, -0.06], [0.14, -0.07]] }],
};

describe('handleCSVUpload()', () => {
  const csvFile = () => new File(['id,x,y,timestamp\n'], 'data.csv', { type: 'text/csv' });

  beforeEach(() => {
    document.getElementById('csv-result').style.display = 'none';
    document.getElementById('csv-result').textContent   = '';
    document.getElementById('csv-result').className     = 'csv-status';
    app.sceneObjects  = [];
    app.forecastPaths = null;
    app.filterKind    = null;
  });

  test('replaces sceneObjects on success', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true, json: () => Promise.resolve(MOCK_CSV_RESPONSE),
    }));
    await app.handleCSVUpload(csvFile());
    expect(app.sceneObjects).toHaveLength(1);
    expect(app.sceneObjects[0].name).toBe('My Sat');
  });

  test('sets forecastPaths on success', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true, json: () => Promise.resolve(MOCK_CSV_RESPONSE),
    }));
    await app.handleCSVUpload(csvFile());
    expect(app.forecastPaths).toHaveLength(1);
    expect(app.forecastPaths[0].waypoints).toHaveLength(2);
  });

  test('shows success status with correct count', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true, json: () => Promise.resolve(MOCK_CSV_RESPONSE),
    }));
    await app.handleCSVUpload(csvFile());
    const el = document.getElementById('csv-result');
    expect(el.style.display).toBe('block');
    expect(el.className).toContain('success');
    expect(el.textContent).toContain('1 object');
  });

  test('shows plural text for multiple objects', async () => {
    const multi = {
      objects: [MOCK_CSV_RESPONSE.objects[0], { ...MOCK_CSV_RESPONSE.objects[0], id: 'SAT2' }],
      predictions: [],
    };
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true, json: () => Promise.resolve(multi),
    }));
    await app.handleCSVUpload(csvFile());
    expect(document.getElementById('csv-result').textContent).toContain('2 objects');
  });

  test('shows error when 0 objects returned', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true, json: () => Promise.resolve({ objects: [], predictions: [] }),
    }));
    await app.handleCSVUpload(csvFile());
    const el = document.getElementById('csv-result');
    expect(el.className).toContain('error');
    expect(el.textContent).toContain('No valid objects');
  });

  test('shows error on non-ok HTTP status', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: false,
      statusText: 'Unprocessable Entity',
      json: () => Promise.resolve({ detail: 'CSV must have columns: id, timestamp, x, y' }),
    }));
    await app.handleCSVUpload(csvFile());
    const el = document.getElementById('csv-result');
    expect(el.className).toContain('error');
    expect(el.textContent).toContain('CSV must have columns');
  });

  test('shows error on network failure', async () => {
    global.fetch = jest.fn(() => Promise.reject(new Error('network down')));
    await app.handleCSVUpload(csvFile());
    expect(document.getElementById('csv-result').className).toContain('error');
  });

  test('sets simMode=true and simPaused=true after load', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true, json: () => Promise.resolve(MOCK_CSV_RESPONSE),
    }));
    app.simMode   = false;
    app.simPaused = false;
    await app.handleCSVUpload(csvFile());
    expect(app.simMode).toBe(true);
    expect(app.simPaused).toBe(true);
  });

  test('resets filterKind to null', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true, json: () => Promise.resolve(MOCK_CSV_RESPONSE),
    }));
    app.filterKind = 'satellite';
    await app.handleCSVUpload(csvFile());
    expect(app.filterKind).toBeNull();
  });

  test('POSTs to /api/upload/csv', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true, json: () => Promise.resolve(MOCK_CSV_RESPONSE),
    }));
    await app.handleCSVUpload(csvFile());
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/upload/csv',
      expect.objectContaining({ method: 'POST' }),
    );
  });
});
