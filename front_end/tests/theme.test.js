/**
 * Theme switching: the three UI themes recolour both the canvas palette
 * (THEMES) and the DOM chrome (a body class), and remember the choice.
 */

const app = global._app;

describe('THEMES data', () => {
  test('the named themes exist with a palette', () => {
    for (const key of ['default', 'cosmic', 'vangogh', 'burton', 'pirate']) {
      const t = app.THEMES[key];
      expect(t).toBeDefined();
      expect(t.label).toBeTruthy();
      expect(t.stars.length).toBeGreaterThan(0);
      expect(t.grad).toHaveLength(3);
      expect(t.clouds.length).toBeGreaterThan(0);
    }
  });

  test('the app default is the classic "default" theme', () => {
    expect(app.DEFAULT_THEME).toBe('default');
    expect(app.THEMES.default).toBeDefined();
  });
});

describe('object theming (kindStyle)', () => {
  test('the default theme leaves object colours untouched', () => {
    app.setTheme('default');
    expect(app.kindStyle('satellite').color).toBe(app.KIND_STYLES.satellite.color);
  });

  test('a tinted theme shifts object colours toward the theme', () => {
    app.setTheme('pirate');
    const themed = app.kindStyle('satellite').color;
    expect(themed).not.toBe(app.KIND_STYLES.satellite.color);
    // The tinted colour is the base blended toward the theme's tint colour.
    const tint = app.THEMES.pirate.objectTint;
    const expected = app.mixHex(
      app.KIND_STYLES.satellite.color, tint.color, tint.amount,
    );
    expect(themed).toBe(expected);
    expect(themed).toMatch(/^#[0-9a-f]{6}$/i);
  });

  test('kindStyle keeps the base size', () => {
    app.setTheme('vangogh');
    expect(app.kindStyle('satellite').size).toBe(app.KIND_STYLES.satellite.size);
  });
});

describe('profile bridge', () => {
  test('exposes window.cosmicSetTheme for auth.js to apply a saved theme', () => {
    expect(typeof window.cosmicSetTheme).toBe('function');
    window.cosmicSetTheme('burton');
    expect(app.currentTheme).toBe(app.THEMES.burton);
  });

  test('a user dropdown change emits cosmic:themechange for persistence', () => {
    const select = document.getElementById('theme-select');
    let captured = null;
    document.addEventListener(
      'cosmic:themechange', (e) => { captured = e.detail; }, { once: true },
    );
    select.value = 'pirate';
    select.dispatchEvent(new Event('change'));
    expect(captured).toBe('pirate');
  });
});

describe('setTheme()', () => {
  test('switches the canvas palette and the body class', () => {
    app.setTheme('vangogh');
    expect(app.currentTheme).toBe(app.THEMES.vangogh);
    expect(document.body.classList.contains('theme-vangogh')).toBe(true);
    expect(document.body.classList.contains('theme-cosmic')).toBe(false);

    app.setTheme('burton');
    expect(app.currentTheme).toBe(app.THEMES.burton);
    expect(document.body.classList.contains('theme-burton')).toBe(true);
    expect(document.body.classList.contains('theme-vangogh')).toBe(false);
  });

  test('syncs the dropdown to the chosen theme', () => {
    app.setTheme('cosmic');
    expect(document.getElementById('theme-select').value).toBe('cosmic');
    app.setTheme('burton');
    expect(document.getElementById('theme-select').value).toBe('burton');
  });

  test('changing the dropdown applies the theme', () => {
    const select = document.getElementById('theme-select');
    select.value = 'vangogh';
    select.dispatchEvent(new Event('change'));
    expect(app.currentTheme).toBe(app.THEMES.vangogh);
    expect(document.body.classList.contains('theme-vangogh')).toBe(true);
  });

  test('remembers the choice in localStorage', () => {
    app.setTheme('vangogh');
    expect(localStorage.getItem('cosmicTheme')).toBe('vangogh');
  });

  test('pirate mode applies and replaces the previous theme class', () => {
    app.setTheme('cosmic');
    app.setTheme('pirate');
    expect(app.currentTheme).toBe(app.THEMES.pirate);
    expect(document.body.classList.contains('theme-pirate')).toBe(true);
    expect(document.body.classList.contains('theme-cosmic')).toBe(false);
  });

  test('an unknown theme name falls back to the default', () => {
    const key = app.setTheme('nonsense');
    expect(key).toBe(app.DEFAULT_THEME);
    expect(app.currentTheme).toBe(app.THEMES[app.DEFAULT_THEME]);
  });
});
