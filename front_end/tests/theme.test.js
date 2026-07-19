/**
 * Theme switching: the three UI themes recolour both the canvas palette
 * (THEMES) and the DOM chrome (a body class), and remember the choice.
 */

const app = global._app;

describe('THEMES data', () => {
  test('the three named themes exist with a palette', () => {
    for (const key of ['cosmic', 'vangogh', 'burton']) {
      const t = app.THEMES[key];
      expect(t).toBeDefined();
      expect(t.label).toBeTruthy();
      expect(t.stars.length).toBeGreaterThan(0);
      expect(t.grad).toHaveLength(3);
      expect(t.clouds.length).toBeGreaterThan(0);
    }
  });

  test('the default theme is one of the three', () => {
    expect(app.THEMES[app.DEFAULT_THEME]).toBeDefined();
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

  test('an unknown theme name falls back to the default', () => {
    const key = app.setTheme('nonsense');
    expect(key).toBe(app.DEFAULT_THEME);
    expect(app.currentTheme).toBe(app.THEMES[app.DEFAULT_THEME]);
  });
});
