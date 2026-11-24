const $ = (s, e = document) => e.querySelector(s),
  esc = (s) =>
    String(s ?? "").replace(
      /[&<>"]/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c],
    );
const P = {
  book: '<path d="M12 7v14M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
  globe:
    '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/>',
  edit: '<path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.4 2.6a2.1 2.1 0 0 1 3 3L12 15l-4 1 1-4Z"/>',
  image:
    '<rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  library: '<path d="m16 6 4 14M12 6v14M8 8v12M4 4v16"/>',
  plug: '<path d="M12 22v-5M9 8V2M15 8V2M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z"/>',
  code: '<path d="m16 18 6-6-6-6M8 6l-6 6 6 6"/>',
  compass:
    '<circle cx="12" cy="12" r="10"/><path d="m16.2 7.8-2 6.3-6.4 2.1 2-6.3Z"/>',
  dash: '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
  activity: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  box: '<path d="M21 8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5M12 22V12"/>',
  file: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4M10 9H8M16 13H8M16 17H8"/>',
  scan: '<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><circle cx="12" cy="12" r="3"/>',
  msgs: '<path d="M14 9a2 2 0 0 1-2 2H6l-4 4V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2Z"/><path d="M18 9h2a2 2 0 0 1 2 2v11l-4-4h-6a2 2 0 0 1-2-2v-1"/>',
  sliders:
    '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  panel: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/>',
  pin: '<path d="M12 17v5M9 10.8a2 2 0 0 1-1.1 1.8l-1.8.9A2 2 0 0 0 5 15.2V17h14v-1.8a2 2 0 0 0-1.1-1.8l-1.8-.9a2 2 0 0 1-1.1-1.8V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1Z"/>',
  more: '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
  plus: '<path d="M5 12h14M12 5v14"/>',
  up: '<path d="m5 12 7-7 7 7M12 19V5"/>',
  stop: '<rect width="12" height="12" x="6" y="6" rx="1"/>',
  copy: '<rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2"/>',
  redo: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8M21 3v5h-5M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16M8 16H3v5"/>',
};
const ic = (n) => `<svg class="i" viewBox="0 0 24 24">${P[n]}</svg>`;
const fb = (n) => {
  if (n == null) return "—";
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < 4) {
    n /= 1024;
    i++;
  }
  return n.toFixed(1) + " " + u[i];
};
function csrfCookie() {
  const m = document.cookie.match(/(?:^|; )studio_csrf=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}
async function api(u, m = "GET", b) {
  const method = (m || "GET").toUpperCase(),
    headers = {};
  if (b !== undefined && b !== null)
    headers["Content-Type"] = "application/json";
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const c = csrfCookie();
    if (c) headers["X-CSRF-Token"] = c;
  }
  const r = await fetch(u, {
    method,
    headers,
    body: b !== undefined && b !== null ? JSON.stringify(b) : undefined,
    credentials: "same-origin",
  });
  let d = {};
  try {
    d = await r.json();
  } catch {}
  if (!r.ok) {
    const e = new Error(d.error || d.detail || r.status);
    e.status = r.status;
    throw e;
  }
  return d;
}
const NAV = [
  ["chat", "New Chat", "edit"],
  ["img", "Images", "image"],
  ["sched", "Scheduled Tasks", "clock"],
  ["lib", "Library", "library"],
  ["kb", "Knowledge", "book"],
  ["github", "GitHub Projects", "code"],
  ["plug", "Plugins / Integrations", "plug"],
  ["code", "Code Assistant", "code"],
  ["explore", "Explore Tools", "compass"],
  ["dash", "Dashboard", "dash"],
  ["status", "System Status", "activity"],
  ["task", "Task Manager", "activity"],
  ["models", "Model Library", "box"],
  ["ocr", "PDF OCR", "file"],
  ["reader", "Image Reader", "scan"],
  ["doc", "Document Chat", "msgs"],
  ["set", "Settings", "sliders"],
];
const DONE = {
    kb: 1,
    chat: 1,
    dash: 1,
    status: 1,
    task: 1,
    models: 1,
    set: 1,
    github: 1,
    lib: 1,
    doc: 1,
  },
  STAGE = {
    img: 8,
    sched: 9,
    lib: 8,
    plug: 9,
    code: 9,
    explore: 9,
    ocr: 6,
    reader: 7,
  };
const S = {
  page: "chat",
  cid: null,
  chats: [],
  projects: [],
  models: [],
  model: "",
  msgs: [],
  att: [],
  gen: null,
  hist: [],
  range: 60,
  pause: false,
  col: false,
  q: "",
  sq: false,
  open: { p: 1, r: 1, j: 1 },
  arch: false,
  poll: 2000,
  ctx: 4096,
  webMode: "off",
  cfg: {},
  sys: "",
  proc: [],
  ps: "",
  sort: "cpu",
};
S.kb = [];
let pt, tm;
async function loadCfg() {
  let c = await api("/api/settings");
  const mig = {};
  /* migration rule: server value wins. Legacy browser values only seed settings still at defaults, once, then are deleted. */
  if (!c.chat_model && localStorage.model) mig.chat_model = localStorage.model;
  if (!c.ocr_model && localStorage.ocr) mig.ocr_model = localStorage.ocr;
  if (
    c.ctx === 4096 &&
    localStorage.ctx &&
    [1024, 2048, 8192, 16384, 32768].includes(+localStorage.ctx)
  )
    mig.ctx = +localStorage.ctx;
  if (
    c.poll_ms === 2000 &&
    localStorage.poll &&
    [1000, 5000].includes(+localStorage.poll)
  )
    mig.poll_ms = +localStorage.poll;
  if (Object.keys(mig).length) {
    try {
      c = await api("/api/settings", "PUT", mig);
    } catch {}
  }
  ["model", "ocr", "ctx", "poll"].forEach((k) => localStorage.removeItem(k));
  applyCfg(c);
}
function applyTheme(mode) {
  const root = document.documentElement;
  const m = ["system", "light", "dark"].includes(mode) ? mode : "dark";
  root.dataset.theme = m;
  const prefersDark = !!(
    window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  );
  root.dataset.resolvedTheme =
    m === "system" ? (prefersDark ? "dark" : "light") : m;
}
if (window.matchMedia) {
  const studioThemeMedia = window.matchMedia("(prefers-color-scheme: dark)");
  const studioThemeChanged = () => {
    if (document.documentElement.dataset.theme === "system")
      applyTheme("system");
  };
  if (studioThemeMedia.addEventListener)
    studioThemeMedia.addEventListener("change", studioThemeChanged);
  else if (studioThemeMedia.addListener)
    studioThemeMedia.addListener(studioThemeChanged);
}
function applyCfg(c) {
  S.cfg = c;
  S.ctx = c.ctx;
  S.poll = c.poll_ms;
  S.model = c.chat_model || S.model;
  S.webMode = ["off", "search_first", "automatic"].includes(c.web_mode_default)
    ? c.web_mode_default
    : localStorage.getItem("nexora.web_mode_default") || "off";
  applyTheme(c.theme_mode || "dark");
  arm();
}
