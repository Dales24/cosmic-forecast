/*
 * Admin API-health monitor. Polls /api/admin/health (admin-only) and renders
 * uptime, request volume, status breakdown, error rate, recent errors, the last
 * scene's object caps, and — on demand — a live reachability probe of the
 * external data sources.
 */
(() => {
  const TOKEN_KEY = "cf_token";
  const token = localStorage.getItem(TOKEN_KEY);
  const body = document.getElementById("admin-body");
  let checkSources = false;
  let timer = null;

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

  function card(title, inner) {
    return `<div class="page-card"><h2>${esc(title)}</h2>${inner}</div>`;
  }

  function field(k, v) {
    return `<div class="profile-field"><span class="k">${esc(k)}</span>` +
           `<span class="v">${esc(v)}</span></div>`;
  }

  function fmtUptime(seconds) {
    const s = Math.floor(seconds);
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return `${h}h ${String(m).padStart(2, "0")}m ${String(s % 60).padStart(2, "0")}s`;
  }

  function renderOverview(d) {
    const sc = d.status_classes || {};
    const rows =
      field("Uptime", fmtUptime(d.uptime_seconds)) +
      field("Total requests", d.total_requests) +
      field("2xx / 4xx / 5xx", `${sc["2xx"] || 0} / ${sc["4xx"] || 0} / ${sc["5xx"] || 0}`) +
      field("Error rate", (d.error_rate * 100).toFixed(2) + "%");
    return card("Overview", rows);
  }

  // Hidden counts from SIMBAD/JPL are a "there are more" floor (the API applies
  // the cap in the query), so they render as "1+" rather than an exact total.
  function fmtHidden(n, exact) {
    return n.toLocaleString() + (exact ? "" : "+");
  }

  function renderCaps(d) {
    const caps = d.scene_caps || {};
    const kinds = caps.kinds || [];
    if (!kinds.length) {
      return card("Scene object caps", '<p class="profile-empty">No scene built yet.</p>');
    }
    const rows = kinds.map((k) =>
      field(k.kind, `${k.shown} shown · ${fmtHidden(k.hidden, k.hidden_exact)} hidden · cap ${k.cap}`)
    ).join("");
    const total =
      field("Total shown", caps.total_shown) +
      field("Total hidden by caps", fmtHidden(caps.total_hidden, caps.total_hidden_exact));
    return card("Scene object caps", total + rows);
  }

  function renderPaths(d) {
    const items = (d.top_paths || []);
    if (!items.length) return card("Busiest paths", '<p class="profile-empty">No traffic yet.</p>');
    const rows = items.map((p) => field(p.path, p.count)).join("");
    return card("Busiest paths", rows);
  }

  function renderErrors(d) {
    const items = (d.recent_errors || []);
    if (!items.length) return card("Recent errors", '<p class="profile-empty">None 🎉</p>');
    const rows = items.map((e) =>
      `<div class="profile-list-item">${esc(e.method)} ${esc(e.path)} ` +
      `<span class="meta">${esc(e.status)} · ${esc(e.duration_ms)}ms · ${esc(e.at)}</span></div>`
    ).join("");
    return card("Recent errors", rows);
  }

  function renderSources(d) {
    const toggle =
      `<label style="display:flex;align-items:center;gap:0.5rem;font-size:0.85rem;text-transform:none;letter-spacing:0;color:var(--text-dim)">` +
      `<input type="checkbox" id="chk-sources" ${checkSources ? "checked" : ""}> ` +
      `Live-probe data sources (slower)</label>`;
    if (!d.sources) return card("Data sources", toggle + '<p class="profile-empty" style="margin-top:0.6rem">Enable the check above to probe CelesTrak / JPL / SIMBAD.</p>');
    const rows = Object.entries(d.sources).map(([name, s]) => {
      const dot = s.ok ? "🟢" : "🔴";
      const detail = s.ok ? `${s.status} · ${s.latency_ms}ms` : `${s.error || s.status || "unreachable"} · ${s.latency_ms}ms`;
      return field(`${dot} ${name}`, detail);
    }).join("");
    return card("Data sources", toggle + rows);
  }

  async function refresh() {
    const res = await api("/api/admin/health" + (checkSources ? "?check_sources=true" : ""));
    if (res.status === 401 || res.status === 403) {
      body.innerHTML = card("Access", '<p class="profile-empty">Admin access required. ' +
        '<a href="/">Log in as an admin on the map.</a></p>');
      if (timer) clearInterval(timer);
      return;
    }
    if (!res.ok) return;
    const d = await res.json();
    body.innerHTML =
      renderOverview(d) + renderCaps(d) + renderSources(d) +
      renderPaths(d) + renderErrors(d);
    const chk = document.getElementById("chk-sources");
    if (chk) chk.addEventListener("change", () => { checkSources = chk.checked; refresh(); });
  }

  refresh();
  timer = setInterval(refresh, 5000); // auto-refresh
})();
