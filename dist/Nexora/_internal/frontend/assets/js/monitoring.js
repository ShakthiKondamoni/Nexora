/* ---------- metrics & charts ---------- */
async function poll() {
  if (document.hidden || S.pause) return;
  try {
    const m = await api("/api/metrics"),
      g = m.gpu;
    S.last = m;
    S.hist.push({
      t: Date.now(),
      cpu: m.cpu,
      ram: m.ram.pct,
      gpu: g ? g.util : null,
      vram: g ? (g.used / g.total) * 100 : null,
      run: m.ollama.running.length,
    });
    if (S.hist.length > 1800) S.hist.shift();
    S.redraw && S.redraw();
  } catch {}
}
const arm = () => {
  clearInterval(tm);
  tm = setInterval(poll, S.poll);
};
function line(cv, key, color, why) {
  const D = cv.getContext("2d"),
    r = cv.getBoundingClientRect(),
    dp = devicePixelRatio || 1;
  if (cv.width !== Math.round(r.width * dp)) {
    cv.width = r.width * dp;
    cv.height = r.height * dp;
  }
  D.setTransform(dp, 0, 0, dp, 0, 0);
  const W = r.width,
    H = r.height,
    now = Date.now(),
    pts = S.hist.filter((s) => s.t > now - S.range * 1000 && s[key] != null);
  D.clearRect(0, 0, W, H);
  D.strokeStyle = "#2f2f2f";
  D.fillStyle = "#9b9b9b";
  D.font = "11px system-ui";
  for (const g of [0, 0.5, 1]) {
    const y = H - 18 - (H - 26) * g;
    D.beginPath();
    D.moveTo(32, y);
    D.lineTo(W, y);
    D.stroke();
    D.fillText(Math.round(100 * g) + "%", 0, y + 4);
  }
  D.fillText(
    "-" + (S.range >= 60 ? S.range / 60 + " min" : S.range + " s"),
    32,
    H - 3,
  );
  D.fillText("now", W - 22, H - 3);
  if (!pts.length) {
    D.fillText(
      "Unavailable — " + (why || "no samples collected yet"),
      44,
      H / 2,
    );
    cv._p = [];
    return null;
  }
  cv._p = pts.map((s) => ({
    x: 32 + (W - 32) * (1 - (now - s.t) / (S.range * 1000)),
    v: s[key],
    t: s.t,
  }));
  D.beginPath();
  cv._p.forEach((p, i) => {
    const y = H - 18 - ((H - 26) * p.v) / 100;
    i ? D.lineTo(p.x, y) : D.moveTo(p.x, y);
  });
  D.strokeStyle = color;
  D.lineWidth = 2;
  D.stroke();
  D.lineTo(cv._p.at(-1).x, H - 18);
  D.lineTo(cv._p[0].x, H - 18);
  D.fillStyle = color + "22";
  D.fill();
  if (!cv._h) {
    cv._h = 1;
    cv.onmousemove = (e) => {
      const x = e.offsetX,
        p = (cv._p || []).reduce(
          (b, c) => (Math.abs(c.x - x) < Math.abs(b.x - x) ? c : b),
          { x: 1e9 },
        );
      cv.title =
        p.v != null
          ? `${p.v.toFixed(1)}% · ${new Date(p.t).toLocaleTimeString()}`
          : "";
    };
  }
  const v = pts.map((s) => s[key]);
  return {
    cur: v.at(-1),
    avg: v.reduce((a, b) => a + b, 0) / v.length,
    max: Math.max(...v),
  };
}
function donut(cv, pct, color, label) {
  const D = cv.getContext("2d"),
    dp = devicePixelRatio || 1;
  cv.width = 150 * dp;
  cv.height = 150 * dp;
  D.setTransform(dp, 0, 0, dp, 0, 0);
  D.clearRect(0, 0, 150, 150);
  D.lineWidth = 16;
  D.strokeStyle = "#2a2a3a";
  D.beginPath();
  D.arc(75, 75, 58, 0, 7);
  D.stroke();
  if (pct != null) {
    D.strokeStyle = color;
    D.beginPath();
    D.arc(75, 75, 58, -Math.PI / 2, -Math.PI / 2 + (Math.PI * 2 * pct) / 100);
    D.stroke();
  }
  D.fillStyle = "#ececec";
  D.textAlign = "center";
  D.font = "600 22px system-ui";
  D.fillText(pct == null ? "N/A" : pct.toFixed(0) + "%", 75, 78);
  D.font = "11px system-ui";
  D.fillStyle = "#9b9b9b";
  D.fillText(label, 75, 95);
  cv.title =
    label + ": " + (pct == null ? "unavailable" : pct.toFixed(1) + "% used");
}
const st = (r) =>
  r
    ? `now <b>${r.cur.toFixed(1)}%</b> · avg ${r.avg.toFixed(1)}% · peak ${r.max.toFixed(1)}%`
    : "—";
const rng = () =>
  `<span style="margin-left:auto;display:flex;gap:6px">${[
    [60, "60 s"],
    [300, "5 min"],
    [900, "15 min"],
    [3600, "1 hr"],
  ]
    .map(
      ([v, l]) =>
        `<button class="btn ${S.range === v ? "on" : ""}" data-a="rng:${v}">${l}</button>`,
    )
    .join(
      "",
    )}<button class="btn ${S.pause ? "on" : ""}" data-a="pause">${S.pause ? "Resume" : "Pause"}</button></span>`;
const hdr = (t) =>
  `<div style="display:flex;align-items:center;gap:10px"><div><h1>${t}</h1><div class="mu">Real samples only · polled every ${S.poll / 1000}s · history is kept in memory while this tab is open (max 1 hr)</div></div>${rng()}</div>`;

function dashView() {
  $("#main").innerHTML =
    `<div class="pg">${hdr("Dashboard")}<div class="grid" id="cards"></div>
 <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn" data-a="nav:chat">Open AI Chat</button><button class="btn" data-a="nav:models">Open Model Library</button><button class="btn" data-a="nav:ocr">Open PDF OCR</button><button class="btn" data-a="nav:task">Open Task Manager</button></div>
 <div class="grid">${["ram", "vram", "disk"].map((k) => `<div class="card pcard"><div class="l">${{ ram: "Memory (used vs free)", vram: "Dedicated GPU memory (used vs free)", disk: "Disk (used vs free)" }[k]}</div><canvas class="dn" id="d_${k}"></canvas></div>`).join("")}</div>
 <div class="row">${[
   ["cpu", "CPU utilization", "#a855f7"],
   ["ram", "Memory utilization", "#3b82f6"],
   ["gpu", "GPU utilization", "#22c55e"],
   ["vram", "GPU memory utilization", "#f59e0b"],
 ]
   .map(
     ([k, t, c]) =>
       `<div class="card"><div class="l">${t} <span id="s_${k}" style="margin-left:auto"></span></div><canvas id="c_${k}" data-k="${k}" data-c="${c}"></canvas></div>`,
   )
   .join("")}</div></div>`;
  S.redraw = () => {
    const m = S.last;
    if (!m) return;
    const g = m.gpu,
      u = m.ollama,
      C = (i, l, v, s) =>
        `<div class="card"><div class="l">${ic(i)} ${l}</div><div class="v">${v}</div><div class="mu">${s || ""}</div></div>`;
    $("#cards").innerHTML =
      C("box", "Ollama", u.up ? "Online" : "Offline", OLLAMA_NOTE) +
      C("library", "Installed models", S.models.length) +
      C(
        "activity",
        "Running models",
        u.running.length,
        u.running.map((r) => r.name).join(", "),
      ) +
      C(
        "dash",
        "CPU",
        m.cpu.toFixed(0) + "%",
        m.cores + " logical processors",
      ) +
      C(
        "dash",
        "RAM",
        m.ram.pct.toFixed(0) + "%",
        fb(m.ram.used) + " / " + fb(m.ram.total),
      ) +
      C("dash", "GPU", g ? g.util + "%" : "N/A", g ? g.name : m.gpu_err) +
      C(
        "dash",
        "GPU memory",
        g ? fb(g.used) : "N/A",
        g ? "of " + fb(g.total) + " dedicated" : m.gpu_err,
      ) +
      C(
        "dash",
        "Disk",
        m.disk.pct.toFixed(0) + "%",
        fb(m.disk.used) + " / " + fb(m.disk.total),
      );
    donut($("#d_ram"), m.ram.pct, "#a855f7", "RAM");
    donut($("#d_vram"), g ? (g.used / g.total) * 100 : null, "#3b82f6", "VRAM");
    donut($("#d_disk"), m.disk.pct, "#f59e0b", "Disk");
    document.querySelectorAll("canvas[data-k]").forEach((cv) => {
      $("#s_" + cv.dataset.k).innerHTML = st(
        line(
          cv,
          cv.dataset.k,
          cv.dataset.c,
          m.gpu_err && cv.dataset.k.match(/gpu|vram/) ? m.gpu_err : "",
        ),
      );
    });
  };
  poll().then(() => S.redraw && S.redraw());
  arm();
  S.last && S.redraw();
}
const OLLAMA_NOTE = "Ollama-reported";

function taskView() {
  const blk = (k, t, c, extra) =>
    `<div class="card" style="margin-bottom:12px"><div class="l">${t} <span id="s_${k}" style="margin-left:auto"></span></div><div class="mu" id="x_${k}">${extra || ""}</div><canvas class="big" id="c_${k}" data-k="${k}" data-c="${c}"></canvas></div>`;
  $("#main").innerHTML =
    `<div class="pg">${hdr("Task Manager")}<div style="height:12px"></div>${blk("cpu", "CPU", "#a855f7")}${blk("ram", "Memory", "#3b82f6")}${blk("gpu", "GPU", "#22c55e")}${blk("vram", "GPU memory (dedicated VRAM)", "#f59e0b")}
 <div class="card" style="margin-bottom:12px"><div class="l">Ollama model activity <span class="mu">(reported by Ollama, not the OS)</span></div><div id="oll" class="mu"></div></div>
 <div class="card"><div class="l">Processes <input type="search" id="ps" placeholder="Search processes" style="margin-left:auto"> <button class="btn" id="pr">Refresh</button></div><table><thead><tr><th data-a="sort:name">Name</th><th>PID</th><th data-a="sort:cpu">CPU %</th><th data-a="sort:mem">Memory</th><th>Status</th><th>GPU</th></tr></thead><tbody id="pb"></tbody></table><div class="mu" style="margin-top:6px">Read-only. Per-process GPU usage isn’t collected (shown as “—”). Ollama processes are highlighted.</div></div></div>`;
  $("#ps").oninput = (e) => {
    S.ps = e.target.value;
    procRows();
  };
  $("#pr").onclick = loadProc;
  S.redraw = () => {
    const m = S.last;
    if (!m) return;
    const g = m.gpu,
      e = (why) => why || "";
    $("#x_cpu").textContent = m.cores + " logical processors";
    $("#x_ram").textContent =
      `Used ${fb(m.ram.used)} · Available ${fb(m.ram.avail)} · Total ${fb(m.ram.total)}`;
    $("#x_gpu").textContent = g
      ? `${g.name} · ${g.temp ?? "—"} °C · ${g.power ?? "—"} W · shared GPU memory not exposed by nvidia-smi`
      : m.gpu_err;
    $("#x_vram").textContent = g
      ? `Used ${fb(g.used)} of ${fb(g.total)} dedicated`
      : m.gpu_err;
    document.querySelectorAll("canvas[data-k]").forEach((cv) => {
      $("#s_" + cv.dataset.k).innerHTML = st(
        line(
          cv,
          cv.dataset.k,
          cv.dataset.c,
          cv.dataset.k.match(/gpu|vram/) ? m.gpu_err : "",
        ),
      );
    });
    $("#oll").innerHTML = !m.ollama.up
      ? "Ollama unreachable."
      : m.ollama.running.length
        ? `<table>${m.ollama.running.map((r) => `<tr><td>${esc(r.name)}</td><td>${fb(r.size)}</td><td>VRAM ${fb(r.vram)} (${r.size ? Math.round((100 * r.vram) / r.size) : 0}% on GPU)</td><td>ctx ${r.ctx ?? "—"}</td></tr>`).join("")}</table>`
        : "No models loaded.";
  };
  S.last && S.redraw();
  poll();
  arm();
  loadProc();
  pt = setInterval(loadProc, 3000);
}
async function loadProc() {
  if (S.pause || document.hidden) return;
  try {
    S.proc = await api("/api/processes");
    procRows();
  } catch {}
}
function procRows() {
  const b = $("#pb");
  if (!b) return;
  const f = S.ps.toLowerCase();
  b.innerHTML = S.proc
    .filter((p) => p.name.toLowerCase().includes(f))
    .sort((a, c) =>
      S.sort === "name" ? a.name.localeCompare(c.name) : c[S.sort] - a[S.sort],
    )
    .slice(0, 60)
    .map(
      (p) =>
        `<tr class="${p.ai ? "ai" : ""}"><td>${esc(p.name)}</td><td>${p.pid}</td><td>${p.cpu.toFixed(1)}</td><td>${fb(p.mem)}</td><td>${p.status}</td><td>—</td></tr>`,
    )
    .join("");
}
/* ---------- system diagnostics ---------- */
function diagnosticReportText(d) {
  const a = (d && d.components) || [];
  return [
    "Nexora diagnostic report",
    `Generated: ${(d && d.generated_at) || "unknown"}`,
    ...a.map((x) => `${x.name}: ${x.state} — ${x.message}`),
    "",
    "Component states only; no credentials or document contents.",
  ].join("\n");
}
function diagnosticCard(x) {
  const c = String(x.state || "")
    .toLowerCase()
    .replace(/\s+/g, "-");
  return `<article class="card diag-card"><div class="diag-card-head"><strong>${esc(x.name || "Status")}</strong><span class="diag-state ${esc(c)}">${esc(x.state || "Unknown")}</span></div><p class="mu">${esc(x.message || "No details available.")}</p></article>`;
}
async function refreshDiagnostics() {
  const g = $("#diag-grid"),
    r = $("#diag-report"),
    s = $("#diag-stamp");
  if (g)
    g.innerHTML =
      '<div class="card diag-card"><span class="mu">Checking local services…</span></div>';
  try {
    const d = await api("/api/diagnostics");
    S.diagnostics = d;
    if (g) g.innerHTML = (d.components || []).map(diagnosticCard).join("");
    if (r) r.textContent = diagnosticReportText(d);
    if (s)
      s.textContent =
        "Updated " + new Date(d.generated_at).toLocaleTimeString();
  } catch (e) {
    if (g)
      g.innerHTML = `<div class="card diag-card"><strong>Diagnostics unavailable</strong><p class="mu">${esc(e.message || "Could not load system status.")}</p></div>`;
    if (r)
      r.textContent =
        "Diagnostics unavailable. Check sign-in and the local backend.";
  }
}
async function copyDiagnostics() {
  const t = $("#diag-report")?.textContent || "",
    s = $("#diag-copy-status");
  try {
    await navigator.clipboard.writeText(t);
    if (s) s.textContent = "Copied.";
  } catch (e) {
    const b = document.createElement("textarea");
    b.value = t;
    b.style.position = "fixed";
    b.style.opacity = "0";
    document.body.appendChild(b);
    b.select();
    const ok = document.execCommand("copy");
    b.remove();
    if (s) s.textContent = ok ? "Copied." : "Copy was blocked by the browser.";
  }
}
async function statusView() {
  $("#main").innerHTML =
    `<div class="pg diag-page"><div class="diag-title"><div><h1>System status</h1><p class="mu">Live checks for Nexora, Ollama, web search, GitHub configuration, and local storage.</p></div><div class="diag-actions"><button class="btn" id="diag-refresh" type="button">Retry checks</button><button class="btn" id="diag-copy" type="button">Copy diagnostic report</button></div></div><div id="diag-stamp" class="mu diag-stamp">Checking…</div><section id="diag-grid" class="diag-grid" aria-live="polite"></section><section class="card diag-report-card"><h2>Diagnostic report</h2><pre id="diag-report">Checking…</pre><p class="mu">Copied report excludes tokens, passwords, private document contents, and service URLs.</p><span id="diag-copy-status" class="mu" role="status"></span></section></div>`;
  $("#diag-refresh").onclick = refreshDiagnostics;
  $("#diag-copy").onclick = copyDiagnostics;
  await refreshDiagnostics();
}
