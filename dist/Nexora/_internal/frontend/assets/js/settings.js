/* ---------- models & settings ---------- */
async function modelsView() {
  await loadModels();
  $("#main").innerHTML =
    `<div class="pg"><h1>Model Library</h1><div class="mu">Installed in Ollama — nothing is downloaded from here. ${esc(S.merr || "")}</div><div class="card" style="margin-top:14px"><table><tr><th>Model</th><th>Size</th><th>Params</th><th>Capabilities</th><th>Status</th><th></th></tr>${S.models.map((m) => `<tr><td>${esc(m.name)}</td><td>${fb(m.size)}</td><td>${m.params || "—"}</td><td>${m.caps.join(", ") || "—"}</td><td>${m.running ? "Running · VRAM " + fb(m.vram) : "Idle"}</td><td><button class="btn" data-a="testM:${esc(m.name)}">Test</button> <button class="btn" data-a="useM:${esc(m.name)}">Set as default</button></td></tr>`).join("")}</table></div></div>`;
}
const CTX = [1024, 2048, 4096, 8192, 16384, 32768];
async function generalSettingsView() {
  await loadModels();
  const c = S.cfg,
    ms = S.models,
    chatMs = ms.filter((m) => !/embed/.test(m.name)),
    vis = ms.filter((m) => m.caps.includes("vision") || /ocr/i.test(m.name));
  const opt = (l, cur, ph) =>
    `<option value="">${ph}</option>` +
    l
      .map(
        (m) =>
          `<option value="${esc(m.name)}" title="${esc(m.name)}" ${m.name === cur ? "selected" : ""}>${esc(m.name)}</option>`,
      )
      .join("") +
    (cur && !l.find((m) => m.name === cur)
      ? `<option value="${esc(cur)}" selected>${esc(cur)} (not installed)</option>`
      : "");
  const cur = ms.find((m) => m.name === c.chat_model),
    big = c.ctx >= 16384;
  $("#main").innerHTML =
    `<div class="pg"><h1>Settings</h1><p class="mu">Saved on this PC in the Studio database, so they survive restarts.</p><p><a class="btn" href="/setup">Account &amp; Integrations</a> <span class="hint">Sign-in, GitHub, Google, and email recovery settings</span></p><div class="set">
 <div class="card"><h2>Model Configuration</h2><p class="sd">Used by chat and document chat. Models are read live from Ollama.</p>
  <div class="fld"><label for="s_url">Ollama URL</label><div class="fr"><input type="url" id="s_url" value="${esc(c.ollama_url)}" style="flex:1 1 220px"><button class="btn" id="s_test">Test Connection</button><button class="btn" id="s_ref">Refresh Models</button></div><div class="hint stat" id="s_stat">${S.merr ? '<span style="color:#fca5a5">' + esc(S.merr) + "</span>" : `<span style="color:#22c55e">● Connected</span> · ${ms.length} model(s) installed`}</div></div>
  <div class="fld"><label for="s_model">Default chat model</label><div style="min-width:0"><select id="s_model">${opt(chatMs, c.chat_model, "— choose a model —")}</select></div><div class="hint">${cur ? (cur.caps.length ? "Capabilities: " + esc(cur.caps.join(", ")) : "Capabilities not reported by Ollama") : "Chat is disabled until a model is chosen."}</div></div>
  <div class="fld"><label for="s_ctx">Default context length</label><div style="min-width:0"><select id="s_ctx">${CTX.map((v) => `<option ${v === c.ctx ? "selected" : ""}>${v}</option>`).join("")}</select></div><div class="hint">Recommended for ~6 GB VRAM: 4096 (8192 for small models). ${big ? '<span style="color:#fbbf24">Large contexts can run out of VRAM and fall back to slow CPU/RAM.</span>' : ""}</div></div>
  <div class="fld"><label for="s_ocr">Vision / OCR model</label><div style="min-width:0"><select id="s_ocr">${opt(vis, c.ocr_model, "Auto-detect")}</select></div><div class="hint">Used for scanned PDF pages. Only vision-capable or OCR models are listed.</div></div>
  <div class="fr" style="margin-top:8px"><button class="btn on" id="s_save">Save</button><span class="stat" id="s_msg"></span></div></div>
 <div class="card"><h2>Performance and Monitoring</h2><p class="sd">How often the Dashboard and Task Manager sample the system.</p>
  <div class="fld"><label for="s_poll">Metrics polling interval</label><div style="min-width:0"><select id="s_poll">${[1000, 2000, 5000].map((v) => `<option value="${v}" ${v === c.poll_ms ? "selected" : ""}>${v / 1000} s</option>`).join("")}</select></div></div></div>
 <div class="card"><h2>Storage and Privacy</h2><p class="sd">Upload limit: 50 MB per chat attachment, 100 MB per Knowledge document. Nothing leaves this PC except requests to your Ollama URL.</p></div>
 <div class="card dim"><h2>Connected Apps</h2><p class="sd">Manage Google sign-in, GitHub repository access, and email configuration in the Connected Apps section.</p><button class="btn" type="button" onclick="setView('connected-apps')">Open Connected Apps</button></div></div></div>`;
  const msg = (t, bad) => {
    $("#s_msg").innerHTML =
      `<span style="color:${bad ? "#fca5a5" : "#22c55e"}">${esc(t)}</span>`;
  };
  $("#s_test").onclick = async () => {
    $("#s_stat").textContent = "Testing…";
    try {
      const r = await api("/api/settings/test-connection", "POST", {
        ollama_url: $("#s_url").value.trim(),
      });
      $("#s_stat").innerHTML =
        `<span style="color:#22c55e">● Connected</span> to ${esc(r.url)} · ${r.models} model(s)`;
    } catch (e) {
      $("#s_stat").innerHTML =
        `<span style="color:#fca5a5">✖ ${esc(e.message)}</span>`;
    }
  };
  $("#s_ref").onclick = () => setView();
  $("#s_poll").onchange = async (e) => {
    try {
      applyCfg(await api("/api/settings", "PUT", { poll_ms: +e.target.value }));
    } catch (er) {
      alert(er.message);
    }
  };
  $("#s_save").onclick = async () => {
    const url = $("#s_url").value.trim();
    $("#s_url").classList.toggle("bad", !/^https?:\/\//.test(url));
    if (!/^https?:\/\//.test(url))
      return msg("Ollama URL must start with http:// or https://", 1);
    try {
      applyCfg(
        await api("/api/settings", "PUT", {
          ollama_url: url,
          chat_model: $("#s_model").value,
          ctx: +$("#s_ctx").value,
          ocr_model: $("#s_ocr").value,
        }),
      );
      msg("Saved");
      await loadModels();
    } catch (e) {
      msg(e.message, 1);
    }
  };
}

function settingsTabs(active) {
  return `<nav class="settings-tabs" aria-label="Settings sections"><button type="button" data-settings-section="general" class="${active === "general" ? "active" : ""}">General</button><button type="button" data-settings-section="connected-apps" class="${active === "connected-apps" ? "active" : ""}">Connected Apps</button><button type="button" data-settings-section="appearance" class="${active === "appearance" ? "active" : ""}">Appearance</button><button type="button" data-settings-section="web-research" class="${active === "web-research" ? "active" : ""}">Web &amp; Research</button></nav>`;
}
function wireSettingsTabs() {
  document
    .querySelectorAll("[data-settings-section]")
    .forEach((b) => (b.onclick = () => setView(b.dataset.settingsSection)));
}
function mountSettingsTabs(active) {
  const pg = $("#main .pg");
  if (!pg) return;
  const h = pg.querySelector(":scope > h1");
  if (!h) return;
  h.insertAdjacentHTML("afterend", settingsTabs(active));
  wireSettingsTabs();
}
function settingsFrame(active, description, content) {
  $("#main").innerHTML =
    `<div class="pg"><h1>Settings</h1>${settingsTabs(active)}<p class="mu">${description}</p>${content}</div>`;
  wireSettingsTabs();
}
async function appearanceView() {
  const current = ["system", "light", "dark"].includes(S.cfg?.theme_mode)
    ? S.cfg.theme_mode
    : "dark";
  settingsFrame(
    "appearance",
    "Choose how Nexora looks. Your choice is saved in this Studio profile and applies immediately.",
    `<section class="card appearance-card"><h2>Appearance</h2><p class="sd">System follows your operating system preference. Light and Dark stay fixed.</p><fieldset class="theme-picker"><legend class="sr-only">Theme</legend><label class="theme-choice"><input type="radio" name="theme_mode" value="system" ${current === "system" ? "checked" : ""}><span class="theme-preview system-preview" aria-hidden="true"><i></i><i></i></span><span class="theme-copy"><strong>System</strong><small>Follow device preference</small></span></label><label class="theme-choice"><input type="radio" name="theme_mode" value="light" ${current === "light" ? "checked" : ""}><span class="theme-preview light-preview" aria-hidden="true"><i></i><i></i></span><span class="theme-copy"><strong>Light</strong><small>Bright, low-contrast workspace</small></span></label><label class="theme-choice"><input type="radio" name="theme_mode" value="dark" ${current === "dark" ? "checked" : ""}><span class="theme-preview dark-preview" aria-hidden="true"><i></i><i></i></span><span class="theme-copy"><strong>Dark</strong><small>Charcoal workspace · default</small></span></label></fieldset><div class="hint" id="theme-status" role="status" aria-live="polite">${current[0].toUpperCase() + current.slice(1)} theme selected.</div></section>`,
  );
  const status = $("#theme-status");
  document.querySelectorAll('input[name="theme_mode"]').forEach(
    (input) =>
      (input.onchange = async () => {
        const next = input.value,
          previous = S.cfg?.theme_mode || "dark";
        applyTheme(next);
        status.textContent = "Applying and saving…";
        try {
          applyCfg(await api("/api/settings", "PUT", { theme_mode: next }));
          status.textContent = `${next[0].toUpperCase() + next.slice(1)} theme saved.`;
        } catch (e) {
          applyTheme(previous);
          document.querySelector(
            `input[name="theme_mode"][value="${previous}"]`,
          ).checked = true;
          status.textContent = `Could not save theme: ${e.message}`;
        }
      }),
  );
}
function connectedNotice() {
  const p = new URLSearchParams(location.search),
    success = p.get("github_connected"),
    error = p.get("github_error");
  if (!success && !error) return "";
  let message = success
    ? "GitHub connected successfully."
    : error === "authorization_denied"
      ? "GitHub authorization was denied. No account was connected."
      : error === "session_expired"
        ? "The GitHub sign-in session expired. Reconnect to try again."
        : "GitHub could not complete authorization. Check administrator setup and try again.";
  history.replaceState({}, "", location.pathname);
  return `<div class="settings-notice ${success ? "success" : "error"}" role="status">${esc(message)}</div>`;
}
async function connectedAppsView() {
  const notice = connectedNotice();
  settingsFrame(
    "connected-apps",
    "Review provider availability and manage repository access.",
    `${notice}<div class="app-grid"><div class="app-card loading-card">Checking connected apps…</div></div>`,
  );
  const [ar, gr] = await Promise.allSettled([
    api("/api/auth/status"),
    api("/api/github/status"),
  ]);
  const auth = ar.status === "fulfilled" ? ar.value : null,
    gh = gr.status === "fulfilled" ? gr.value : null;
  const provider = (auth && auth.google) || {},
    email = (auth && auth.email) || {};
  const googleReady = !!(provider.ready || provider.configured),
    emailReady = !!(email.ready || email.configured);
  const googleText =
    ar.status === "rejected"
      ? "Status unavailable"
      : googleReady
        ? "Sign-in enabled"
        : "Not configured";
  const emailText =
    ar.status === "rejected"
      ? "Status unavailable"
      : emailReady
        ? "Configured"
        : "Not configured";
  const githubReady = !!(gh && (gh.configured || gh.connected)),
    githubOn = !!(gh && gh.connected);
  const login = (gh && (gh.login || gh.username || gh.account)) || "";
  let githubStatus =
    gr.status === "rejected"
      ? "Status unavailable"
      : githubOn
        ? "Connected"
        : githubReady
          ? "Disconnected"
          : "Admin setup required";
  let githubDetail =
    gr.status === "rejected"
      ? "Could not check GitHub right now. Reload to retry."
      : githubOn
        ? login
          ? `Signed in as @${esc(login)}. Read-only repository access.`
          : "GitHub account connected. Read-only repository access."
        : githubReady
          ? "Connect a GitHub account to browse repositories and import code."
          : "An administrator must configure the GitHub App once in Account & Integrations.";
  let githubActions = "";
  if (gr.status === "rejected")
    githubActions =
      '<button class="btn" type="button" id="github-retry">Retry status</button>';
  else if (githubOn)
    githubActions =
      '<button class="btn primary" type="button" id="github-manage">Manage</button><button class="btn" type="button" id="github-reconnect">Reconnect</button><button class="btn danger" type="button" id="github-disconnect">Disconnect</button>';
  else if (githubReady)
    githubActions =
      '<button class="btn primary" type="button" id="github-connect">Connect GitHub</button>';
  else
    githubActions =
      '<a class="btn primary" href="/setup">Administrator setup</a><button class="btn" type="button" disabled aria-disabled="true">Connect GitHub</button>';
  const googleDescription =
    ar.status === "rejected"
      ? "Unable to read provider status."
      : googleReady
        ? "Uses the existing Google OAuth sign-in. This status reflects provider readiness, not a separate linked-account record."
        : "Google OAuth sign-in has not been configured for this Studio.";
  const emailDescription =
    ar.status === "rejected"
      ? "Unable to read provider status."
      : emailReady
        ? "Existing email/recovery settings are configured."
        : "Email is optional and is not configured.";
  settingsFrame(
    "connected-apps",
    "Review provider availability and manage repository access.",
    `${notice}<div class="app-grid"><article class="app-card"><div class="app-card-head"><span class="app-icon github-icon" aria-hidden="true">${ic("code")}</span><div class="app-title"><h2>GitHub</h2><span class="app-status ${gr.status === "rejected" ? "unknown" : githubOn ? "connected" : githubReady ? "off" : "setup"}"><i></i>${githubStatus}</span></div></div><p>Connect your repositories to search, analyze, and work with your code.</p><p class="app-detail">${githubDetail}</p><div class="app-actions">${githubActions}</div></article><article class="app-card"><div class="app-card-head"><span class="app-icon google-icon" aria-hidden="true">G</span><div class="app-title"><h2>Google</h2><span class="app-status ${ar.status === "rejected" ? "unknown" : googleReady ? "connected" : "off"}"><i></i>${googleText}</span></div></div><p class="app-detail">${googleDescription}</p><div class="app-actions"><a class="btn" href="/setup">Administrator setup</a></div></article><article class="app-card"><div class="app-card-head"><span class="app-icon email-icon" aria-hidden="true">@</span><div class="app-title"><h2>Email</h2><span class="app-status ${ar.status === "rejected" ? "unknown" : emailReady ? "connected" : "off"}"><i></i>${emailText}</span></div></div><p class="app-detail">${emailDescription}</p><div class="app-actions"><a class="btn" href="/setup">Administrator setup</a></div></article></div><section class="card app-security"><h2>Access and privacy</h2><p class="sd">GitHub repository browsing and import are read-only. Imported code is indexed in its own project and can be queried with your configured local Ollama model. Provider credentials are configured by an administrator and are not shown here.</p></section>`,
  );
  const btn = (id, fn) => {
    const el = $("#" + id);
    if (el) el.onclick = fn;
  };
  btn("github-retry", () => connectedAppsView());
  btn("github-manage", () => githubView());
  btn("github-connect", () => location.assign("/api/github/connect"));
  btn("github-reconnect", () => location.assign("/api/github/connect"));
  btn("github-disconnect", async () => {
    if (
      !confirm(
        "Disconnect GitHub? Imported project files remain in this Studio.",
      )
    )
      return;
    const el = $("#github-disconnect");
    el.disabled = true;
    el.textContent = "Disconnecting…";
    try {
      await api("/api/github/connection", "DELETE");
      await connectedAppsView();
    } catch (e) {
      el.disabled = false;
      el.textContent = "Disconnect";
      alert(`Could not disconnect GitHub: ${e.message}`);
    }
  });
}
async function setView(section = "general") {
  if (section === "appearance") return appearanceView();
  if (section === "connected-apps") return connectedAppsView();
  if (section === "web-research") return webResearchView();
  await generalSettingsView();
  mountSettingsTabs("general");
}

async function webResearchView() {
  await loadCfg();
  const c = S.cfg || {};
  settingsFrame(
    "web-research",
    "Configure the local search provider used by Nexora chat. Web Search Off remains local-only.",
    `<section class="web-settings card"><div class="web-settings-grid"><label>Search provider<select id="wr-provider" class="in"><option value="searxng" selected>SearXNG · self-hosted · no paid key</option></select></label><label>SearXNG instance URL<input id="wr-url" class="in" type="url" inputmode="url" autocomplete="off" placeholder="http://localhost:8080" value="${esc(c.web_instance_url || "")}"><small>Enter the base URL; the API appends <code>/search?format=json</code>. Enable JSON format in the SearXNG instance.</small></label><label>Default result count<select id="wr-count" class="in">${[3, 5, 8].map((n) => `<option value="${n}" ${+(c.web_result_count || 5) === n ? "selected" : ""}>${n} results</option>`).join("")}</select></label><label>Timeout<select id="wr-timeout" class="in">${[8, 12, 20, 30].map((n) => `<option value="${n}" ${+(c.web_timeout || 12) === n ? "selected" : ""}>${n} seconds</option>`).join("")}</select></label></div><div id="wr-status" class="web-settings-status" role="status" aria-live="polite">${c.web_instance_url ? "Provider configured. Test the connection before using search." : "No provider configured. Local chat is still available."}</div><div class="web-settings-actions"><button type="button" id="wr-test" class="btn">Test connection</button><button type="button" id="wr-save" class="btn primary">Save settings</button></div><p class="mu">Nexora sends search requests only to this configured provider. Credentials are not required for SearXNG; do not place secrets in the instance URL.</p></section>`,
  );
  const status = $("#wr-status");
  $("#wr-test").onclick = async (e) => {
    const b = e.currentTarget;
    b.disabled = true;
    b.textContent = "Testing…";
    status.className = "web-settings-status";
    status.textContent = "Contacting SearXNG…";
    try {
      const r = await api("/api/settings/test-web-search", "POST", {
        instance_url: $("#wr-url").value.trim(),
        timeout: +$("#wr-timeout").value,
      });
      status.className = "web-settings-status success";
      status.textContent = `Connection successful · ${r.results} result(s)${r.sample_title ? " · " + r.sample_title : ""}`;
    } catch (err) {
      status.className = "web-settings-status error";
      status.textContent =
        "Connection failed: " +
        err.message +
        " Check the URL, JSON output, network access, and timeout.";
    } finally {
      b.disabled = false;
      b.textContent = "Test connection";
    }
  };
  $("#wr-save").onclick = async (e) => {
    const b = e.currentTarget;
    b.disabled = true;
    try {
      S.cfg = await api("/api/settings", "PUT", {
        web_provider: $("#wr-provider").value,
        web_instance_url: $("#wr-url").value.trim(),
        web_result_count: +$("#wr-count").value,
        web_timeout: +$("#wr-timeout").value,
      });
      status.className = "web-settings-status success";
      status.textContent = "Web & Research settings saved.";
    } catch (err) {
      status.className = "web-settings-status error";
      status.textContent = "Could not save settings: " + err.message;
    } finally {
      b.disabled = false;
    }
  };
}
