/**
 * Tests for drawGlyph() — every object kind renders as its own glyph without
 * throwing, and a few kinds paint their signature shapes.
 */

const app = global._app;
const ctx = document.getElementById("space-map").getContext("2d");
const STYLE = { size: 4, color: "#88aaff" };

const KINDS = [
  "star", "variable_star", "galaxy", "nebula", "black_hole",
  "comet", "pulsar", "quasar", "iss", "satellite", "asteroid", "ufo",
];

describe("drawGlyph()", () => {
  beforeEach(() => {
    for (const fn of Object.values(ctx)) {
      if (typeof fn === "function" && fn.mockClear) fn.mockClear();
    }
  });

  test("every kind renders without throwing and paints something", () => {
    for (const kind of KINDS) {
      expect(() => app.drawGlyph(kind, 100, 100, STYLE, 0, 500, 300)).not.toThrow();
    }
    expect(ctx.fill).toHaveBeenCalled();
  });

  test("black hole paints the shadow disc plus accretion rings", () => {
    app.drawGlyph("black_hole", 100, 100, STYLE, 0, 500, 300);
    // lensing bloom + event-horizon disc + two rings ⇒ several arcs
    expect(ctx.arc.mock.calls.length).toBeGreaterThanOrEqual(3);
  });

  test("comet builds a gradient tail", () => {
    app.drawGlyph("comet", 100, 100, STYLE, 0, 500, 300);
    expect(ctx.createLinearGradient).toHaveBeenCalled();
  });

  test("a star gets a soft bloom (radial gradient)", () => {
    app.drawGlyph("star", 100, 100, STYLE, 0, 500, 300);
    expect(ctx.createRadialGradient).toHaveBeenCalled();
  });
});

describe("drawVignette()", () => {
  test("darkens the frame with a radial gradient fill", () => {
    ctx.createRadialGradient.mockClear();
    ctx.fillRect.mockClear();
    expect(() => app.drawVignette()).not.toThrow();
    expect(ctx.createRadialGradient).toHaveBeenCalled();
    expect(ctx.fillRect).toHaveBeenCalled();
  });
});

describe("drawShootingStars()", () => {
  test("spawns a meteor and draws its fading streak", () => {
    const rnd = jest.spyOn(Math, "random").mockReturnValue(0); // force a spawn
    ctx.createLinearGradient.mockClear();
    app.drawShootingStars(); // spawn + draw
    app.drawShootingStars(); // move + draw
    expect(ctx.createLinearGradient).toHaveBeenCalled();
    rnd.mockRestore();
  });
});

describe("drawSunFlare()", () => {
  test("paints translucent flare artifacts without throwing", () => {
    ctx.createRadialGradient.mockClear();
    ctx.arc.mockClear();
    expect(() => app.drawSunFlare(120, 90)).not.toThrow();
    expect(ctx.createRadialGradient).toHaveBeenCalled();
    expect(ctx.arc.mock.calls.length).toBeGreaterThanOrEqual(5); // one per artifact
  });
});

describe("drawMoon()", () => {
  test("draws an orbit ring, a glow, and a lunar-phase shadow", () => {
    ctx.stroke.mockClear();
    ctx.createRadialGradient.mockClear();
    expect(() => app.drawMoon(400, 300, 500)).not.toThrow();
    expect(ctx.stroke).toHaveBeenCalled();            // orbit ring
    expect(ctx.createRadialGradient).toHaveBeenCalled(); // glow + phase shadow
  });
});
