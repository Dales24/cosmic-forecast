/*
 * Account UI: login / sign-up / logout, plus saving and reloading simulation
 * searches and image-classification uploads. Self-contained (its own DOM +
 * state) so it doesn't touch app.js. Talks to the /api/auth and /api/searches /
 * /api/uploads endpoints; the session token lives in localStorage.
 */
(() => {
  const TOKEN_KEY = window.COSMIC.TOKEN_KEY;
  let token = localStorage.getItem(TOKEN_KEY) || null;
  let me = null;
  let lastUploadName = "";

  const bar = document.getElementById("auth-bar");
  if (!bar) return;

  // Remember the most recent uploaded filename so we can save it with a result.
  const imgInput = document.getElementById("img-upload");
  if (imgInput) {
    imgInput.addEventListener("change", (e) => {
      if (e.target.files[0]) lastUploadName = e.target.files[0].name;
    });
  }

  // ── tiny DOM helpers ──────────────────────────────────────────────────────
  function el(tag, cls, html) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (html != null) node.innerHTML = html;
    return node;
  }
  function toast(msg) {
    const t = el("div", "auth-toast", msg);
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3000);
  }

  async function api(path, method = "GET", body = null) {
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = "Bearer " + token;
    const opts = { method, headers };
    if (body != null) opts.body = JSON.stringify(body);
    return fetch(path, opts);
  }

  // ── modal (login / register) ──────────────────────────────────────────────
  const modal = el("div", "auth-modal");
  modal.style.display = "none";
  modal.innerHTML = `
    <div class="auth-card">
      <button class="auth-x" data-close>&times;</button>
      <h2 id="auth-title">Log in</h2>
      <label>Username</label><input id="auth-username" type="text" autocomplete="username">
      <label>Password</label><input id="auth-password" type="password" autocomplete="current-password">
      <p id="auth-error" class="auth-error"></p>
      <button id="auth-submit" class="auth-btn primary">Log in</button>
      <p class="auth-switch">
        <span id="auth-switch-text">No account?</span>
        <a href="#" id="auth-switch">Sign up</a>
      </p>
    </div>`;
  document.body.appendChild(modal);

  let mode = "login";
  const $ = (id) => document.getElementById(id);

  function openModal(which) {
    mode = which;
    $("auth-title").textContent = which === "login" ? "Log in" : "Create account";
    $("auth-submit").textContent = which === "login" ? "Log in" : "Sign up";
    $("auth-switch-text").textContent = which === "login" ? "No account?" : "Have an account?";
    $("auth-switch").textContent = which === "login" ? "Sign up" : "Log in";
    $("auth-error").textContent = "";
    modal.style.display = "flex";
  }
  const closeModal = () => (modal.style.display = "none");

  modal.querySelector("[data-close]").onclick = closeModal;
  modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });
  $("auth-switch").onclick = (e) => { e.preventDefault(); openModal(mode === "login" ? "register" : "login"); };

  $("auth-submit").onclick = async () => {
    const username = $("auth-username").value.trim();
    const password = $("auth-password").value;
    const path = mode === "login" ? "/api/auth/login" : "/api/auth/register";
    const res = await api(path, "POST", { username, password });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      $("auth-error").textContent = data.detail || "Something went wrong";
      return;
    }
    if (mode === "register") {
      // Registered — now log in with the same credentials.
      const login = await api("/api/auth/login", "POST", { username, password });
      const ld = await login.json();
      token = ld.token;
    } else {
      token = data.token;
    }
    localStorage.setItem(TOKEN_KEY, token);
    closeModal();
    await refresh();
  };

  // ── saved panel ───────────────────────────────────────────────────────────
  const saved = el("div", "saved-panel");
  saved.style.display = "none";
  saved.innerHTML = `
    <div class="saved-head"><h2>My saved work</h2><button class="auth-x" data-close-saved>&times;</button></div>
    <h3>Searches</h3><div id="saved-searches" class="saved-list"></div>
    <h3>Uploads</h3><div id="saved-uploads" class="saved-list"></div>`;
  document.body.appendChild(saved);
  saved.querySelector("[data-close-saved]").onclick = () => (saved.style.display = "none");

  async function openSaved() {
    saved.style.display = "block";
    const s = await (await api("/api/searches")).json();
    const u = await (await api("/api/uploads")).json();
    renderList($("saved-searches"), s.searches, (item) => {
      const p = item.params;
      return `${item.name} <span class="saved-meta">RA ${p.ra ?? "?"}, Dec ${p.dec ?? "?"}</span>`;
    }, loadSearch, "/api/searches");
    renderList($("saved-uploads"), u.uploads, (item) => {
      return `${item.filename} <span class="saved-meta">${item.result.className || item.kind || ""}</span>`;
    }, null, "/api/uploads");
  }

  function renderList(container, items, label, onLoad, baseUrl) {
    container.innerHTML = "";
    if (!items || !items.length) {
      container.appendChild(el("p", "saved-empty", "Nothing saved yet."));
      return;
    }
    for (const item of items) {
      const row = el("div", "saved-item");
      row.appendChild(el("span", "saved-label", label(item)));
      const actions = el("span", "saved-actions");
      if (onLoad) {
        const load = el("button", "saved-mini", "Load");
        load.onclick = () => { onLoad(item.params); saved.style.display = "none"; };
        actions.appendChild(load);
      }
      const del = el("button", "saved-mini danger", "Delete");
      del.onclick = async () => {
        await api(`${baseUrl}/${item.id}`, "DELETE");
        openSaved();
      };
      actions.appendChild(del);
      row.appendChild(actions);
      container.appendChild(row);
    }
  }

  function loadSearch(params) {
    if (params.ra != null) $("ra").value = params.ra;
    if (params.dec != null) $("dec").value = params.dec;
    if (params.obs_datetime) $("obs_datetime").value = params.obs_datetime;
    document.getElementById("scene-form")?.requestSubmit();
  }

  // ── save buttons injected into the existing panel ─────────────────────────
  const saveSearchBtn = el("button", "auth-btn subtle save-search-btn", "★ Save this search");
  saveSearchBtn.style.display = "none";
  saveSearchBtn.onclick = async () => {
    const params = {
      ra: $("ra").value.trim(),
      dec: $("dec").value.trim(),
      obs_datetime: $("obs_datetime").value,
    };
    const name = prompt("Name this search:", `RA ${params.ra || "?"} / Dec ${params.dec || "?"}`);
    if (!name) return;
    const res = await api("/api/searches", "POST", { name, params });
    toast(res.ok ? "Search saved" : "Could not save");
  };
  document.getElementById("scene-form")?.after(saveSearchBtn);

  const saveUploadBtn = el("button", "auth-btn subtle save-upload-btn", "★ Save this result");
  saveUploadBtn.style.display = "none";
  saveUploadBtn.onclick = async () => {
    const result = {
      className: $("upload-class-name")?.textContent || "",
      confidence: $("upload-conf-pct")?.textContent || "",
    };
    const res = await api("/api/uploads", "POST", {
      filename: lastUploadName || "upload", kind: result.className, result,
    });
    toast(res.ok ? "Upload saved" : "Could not save");
  };
  document.getElementById("upload-result")?.appendChild(saveUploadBtn);

  // ── render the account bar ────────────────────────────────────────────────
  function renderBar() {
    if (me) {
      bar.innerHTML = `<span class="auth-user">@${me.username}</span>
        <button class="auth-btn" id="btn-saved">Saved</button>
        <button class="auth-btn ghost" id="btn-logout">Log out</button>`;
      $("btn-saved").onclick = openSaved;
      $("btn-logout").onclick = async () => {
        await api("/api/auth/logout", "POST");
        token = null; me = null;
        localStorage.removeItem(TOKEN_KEY);
        refresh();
      };
    } else {
      bar.innerHTML = `<button class="auth-btn" id="btn-login">Log in</button>`;
      $("btn-login").onclick = () => openModal("login");
    }
    const show = me ? "inline-block" : "none";
    saveSearchBtn.style.display = show;
    saveUploadBtn.style.display = show;
  }

  // ── theme preference ──────────────────────────────────────────────────────
  // Apply the theme saved on the profile, and persist the user's own changes.
  function applyProfileTheme() {
    if (me && me.theme && typeof window.cosmicSetTheme === "function") {
      window.cosmicSetTheme(me.theme);
    }
  }

  document.addEventListener("cosmic:themechange", (e) => {
    if (me) api("/api/preferences", "PUT", { theme: e.detail });
  });

  async function refresh() {
    if (token) {
      const res = await api("/api/auth/me");
      if (res.ok) me = await res.json();
      else { token = null; localStorage.removeItem(TOKEN_KEY); me = null; }
    }
    applyProfileTheme();
    renderBar();
  }

  refresh();
})();
