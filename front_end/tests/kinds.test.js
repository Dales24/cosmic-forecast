/**
 * Every rendered object kind needs both a style (size + colour) and a display
 * name, so the legend and canvas never fall back to a raw slug.
 */

const app = global._app;

const DEEP_SPACE_PACK = ["star", "black_hole", "quasar", "pulsar", "supernova_remnant"];

describe("object kinds", () => {
  test("the deep-space pack has styles with a colour and size", () => {
    for (const kind of DEEP_SPACE_PACK) {
      const style = app.KIND_STYLES[kind];
      expect(style).toBeDefined();
      expect(style.color).toMatch(/^#[0-9a-f]{3,6}$/i);
      expect(style.size).toBeGreaterThan(0);
    }
  });

  test("every styled kind also has a display name", () => {
    for (const kind of Object.keys(app.KIND_STYLES)) {
      expect(app.KIND_NAMES[kind]).toBeTruthy();
    }
  });
});
