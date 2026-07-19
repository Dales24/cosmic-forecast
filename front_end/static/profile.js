/*
 * Profile page: shows the signed-in user's account, theme, and saved work.
 * Reads the session token from localStorage (shared with auth.js) and calls the
 * same /api/auth and /api/searches / /api/uploads endpoints. Read-only.
 */
(() => {
  const TOKEN_KEY = "cf_token";
  const token = localStorage.getItem(TOKEN_KEY);
  const $ = (id) => document.getElementById(id);

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function api(path) {
    const headers = {};
    if (token) headers["Authorization"] = "Bearer " + token;
    return fetch(path, { headers });
  }

  function field(key, value) {
    return `<div class="profile-field"><span class="k">${esc(key)}</span>` +
           `<span class="v">${esc(value)}</span></div>`;
  }

  function showLoggedOut() {
    $("account").innerHTML =
      `<p class="profile-empty">You're not logged in. ` +
      `<a href="/">Go to the map</a> and log in to see your profile.</p>`;
    for (const el of document.querySelectorAll(".saved-section")) {
      el.style.display = "none";
    }
  }

  async function loadList(path, dataKey, elId, render) {
    const res = await api(path);
    if (!res.ok) return;
    const items = (await res.json())[dataKey] || [];
    $(elId).innerHTML = items.length
      ? items.map((it) => `<div class="profile-list-item">${render(it)}</div>`).join("")
      : `<p class="profile-empty">Nothing saved yet.</p>`;
  }

  async function load() {
    if (!token) return showLoggedOut();
    const res = await api("/api/auth/me");
    if (!res.ok) return showLoggedOut();

    const me = await res.json();
    $("account").innerHTML =
      field("Username", "@" + me.username) +
      field("Email", me.email || "—") +
      field("Theme", me.theme || "default");

    loadList("/api/searches", "searches", "searches", (s) => {
      const p = s.params || {};
      return `${esc(s.name)} <span class="meta">RA ${p.ra ?? "?"}, Dec ${p.dec ?? "?"}</span>`;
    });
    loadList("/api/uploads", "uploads", "uploads", (u) => {
      const r = u.result || {};
      return `${esc(u.filename)} <span class="meta">${esc(r.className || u.kind || "")}</span>`;
    });
  }

  load();
})();
