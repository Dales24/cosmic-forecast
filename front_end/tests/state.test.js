/**
 * Tests for simulation state logic: effectiveTime() and findObjectAt().
 */

const app = global._app;

// ── effectiveTime() ───────────────────────────────────────────────────────────

describe('effectiveTime()', () => {
  beforeEach(() => {
    app.simStartEff  = 5000;
    app.simStartReal = 0;
  });

  test('returns simStartEff when simMode is false', () => {
    app.simMode   = false;
    app.simPaused = false;
    expect(app.effectiveTime(9999)).toBe(5000);
  });

  test('returns simStartEff when paused regardless of real time', () => {
    app.simMode   = true;
    app.simPaused = true;
    expect(app.effectiveTime(1000)).toBe(5000);
    expect(app.effectiveTime(99999)).toBe(5000);
  });

  test('advances at SIM_SPEED when playing', () => {
    app.simMode      = true;
    app.simPaused    = false;
    app.simStartReal = 0;
    app.simStartEff  = 0;
    // 1000ms real × 200 = 200 000ms sim
    expect(app.effectiveTime(1000)).toBe(200000);
  });

  test('simulation time is linear', () => {
    app.simMode      = true;
    app.simPaused    = false;
    app.simStartReal = 0;
    app.simStartEff  = 0;
    const t1 = app.effectiveTime(100);
    const t2 = app.effectiveTime(200);
    expect(t2 - t1).toBe(t1 - app.effectiveTime(0));
  });

  test('pausing freezes the clock', () => {
    app.simMode      = true;
    app.simPaused    = false;
    app.simStartReal = 0;
    app.simStartEff  = 0;
    const playing = app.effectiveTime(500);
    app.simPaused = true;
    expect(app.effectiveTime(1000)).toBe(0); // frozen at simStartEff
    expect(app.effectiveTime(9999)).toBe(0);
    // played value was > 0
    expect(playing).toBeGreaterThan(0);
  });
});

// ── findObjectAt() ────────────────────────────────────────────────────────────

describe('findObjectAt()', () => {
  beforeEach(() => {
    app.panX = 0;
    app.panY = 0;
    app.zoom = 1;
    app.filterKind = null;
    app.sceneObjects = [
      { kind: 'satellite', x_norm: 0, y_norm: 0, vx_norm: 0, vy_norm: 0 },
      { kind: 'ufo',       x_norm: 0, y_norm: 0, vx_norm: 0, vy_norm: 0 },
    ];
    // Set known pixel positions directly
    app.objPositions = [
      { x: 100, y: 100 },
      { x: 300, y: 300 },
    ];
  });

  test('returns -1 when no objects are nearby', () => {
    expect(app.findObjectAt(500, 500)).toBe(-1);
  });

  test('returns index 0 for the first object', () => {
    expect(app.findObjectAt(100, 100)).toBe(0);
  });

  test('returns index 1 for the second object', () => {
    expect(app.findObjectAt(300, 300)).toBe(1);
  });

  test('returns closest object when both are nearby', () => {
    app.objPositions = [{ x: 100, y: 100 }, { x: 105, y: 100 }];
    // Click at 100,100 — should be obj 0
    expect(app.findObjectAt(100, 100)).toBe(0);
    // Click at 105,100 — should be obj 1
    expect(app.findObjectAt(105, 100)).toBe(1);
  });

  test('respects filterKind — hidden objects are not hit', () => {
    app.filterKind = 'satellite';
    expect(app.findObjectAt(300, 300)).toBe(-1);   // ufo filtered out
    expect(app.findObjectAt(100, 100)).toBe(0);    // satellite still hit
  });

  test('filterKind null shows all objects', () => {
    app.filterKind = null;
    expect(app.findObjectAt(300, 300)).toBe(1);
    expect(app.findObjectAt(100, 100)).toBe(0);
  });

  test('accounts for positive panX offset', () => {
    app.panX = 50;
    // Object world pos (100,100); screen = (100+50, 100) = (150, 100)
    expect(app.findObjectAt(150, 100)).toBe(0);
    expect(app.findObjectAt(100, 100)).toBe(-1);
  });

  test('accounts for negative panX offset', () => {
    app.panX = -50;
    // Screen = (100-50, 100) = (50, 100)
    expect(app.findObjectAt(50, 100)).toBe(0);
  });

  test('accounts for zoom > 1', () => {
    app.zoom = 2;
    // Screen = (100*2, 100*2) = (200, 200) with panX=panY=0
    expect(app.findObjectAt(200, 200)).toBe(0);
    expect(app.findObjectAt(100, 100)).toBe(-1);
  });

  test('accounts for zoom < 1', () => {
    app.zoom = 0.5;
    // Screen = (50, 50)
    expect(app.findObjectAt(50, 50)).toBe(0);
    expect(app.findObjectAt(100, 100)).toBe(-1);
  });

  test('hit radius scales inversely with zoom', () => {
    // At zoom=2, hitR = HIT_RADIUS(20)/zoom(2) = 10 world units
    // Object at world (100,100) → screen (200, 200).
    // Click screen (215,200) → wx=107.5, wy=100 → d=7.5 < hitR=10 → hit
    app.zoom = 2;
    app.objPositions = [{ x: 100, y: 100 }, { x: 999, y: 999 }];
    expect(app.findObjectAt(215, 200)).toBe(0);
    // Click screen (222,200) → wx=111, d=11 > hitR=10 → miss
    expect(app.findObjectAt(222, 200)).toBe(-1);
  });

  test('empty scene returns -1', () => {
    app.sceneObjects = [];
    app.objPositions = [];
    expect(app.findObjectAt(0, 0)).toBe(-1);
  });
});
