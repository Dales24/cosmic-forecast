/*
 * Browser-side constants shared by every page and script.
 *
 * Loaded first (before the theme-flash block and any other script) so each
 * consumer reads one definition instead of declaring its own copy — changing a
 * storage key here changes it everywhere.
 */
window.COSMIC = Object.freeze({
  TOKEN_KEY: "cf_token",      // localStorage key holding the session token
  THEME_KEY: "cosmicTheme",   // localStorage key holding the chosen theme
  DEFAULT_THEME_CLASS: "theme-default",
});
