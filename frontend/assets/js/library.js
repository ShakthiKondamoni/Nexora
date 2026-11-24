let LIB_ITEMS = [],
  LIB_REQUEST = 0,
  LIB_TIMER = null;
function libEsc(v) {
  return String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
}
function libSafeUrl(v) {
  try {
    const u = new URL(String(v || ""));
    return ["http:", "https:"].includes(u.protocol) ? u.href : "";
  } catch {
    return "";
  }
}
function libDate(v) {
  if (v === null || v === undefined || v === "") return "";
  const d = new Date(typeof v === "number" && v < 1e12 ? v * 1000 : v);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString();
}
function libraryView() {
  const main = document.querySelector("#main");
  if (!main) return;
  main.innerHTML = `<section class="library-page"><header class="lib-head"><div><h1>Unified Library</h1><p>Saved Knowledge, web citations, and indexed GitHub projects in one view.</p></div><span class="lib-total" id="lib-total">Loading…</span></header><div class="lib-controls"><input id="lib-query" class="lib-input" type="search" autocomplete="off" placeholder="Search titles, URLs, collections, and repositories" aria-label="Search Library"><select id="lib-source" class="lib-select" aria-label="Filter by source"><option value="all">All sources</option><option value="knowledge">Knowledge Base</option><option value="github">GitHub</option></select><select id="lib-type" class="lib-select" aria-label="Filter by item type"><option value="all">All item types</option><option value="web_citation">Saved web citation</option><option value="pdf">PDF</option><option value="text">Text / Markdown</option><option value="notebook">Notebook</option><option value="github_project">GitHub project</option></select></div><div id="lib-source-status" class="lib-source-status" aria-live="polite"></div><div id="lib-results" class="lib-results"><div class="lib-loading">Loading persisted items…</div></div><p class="lib-source-note">Items point to their existing stored records; Library does not create duplicate document copies.</p><div class="lib-overlay" id="lib-overlay" hidden><section class="lib-dialog" role="dialog" aria-modal="true" aria-labelledby="lib-dialog-title"><div class="lib-dialog-head"><h2 id="lib-dialog-title">Library item</h2><button class="lib-button" type="button" data-library-close>Close</button></div><div id="lib-dialog-body" class="lib-dialog-body"></div></section></div></section>`;
  const q = document.querySelector("#lib-query"),
    source = document.querySelector("#lib-source"),
    type = document.querySelector("#lib-type"),
    reload = () => loadLibraryItems(q.value, source.value, type.value);
  q.addEventListener("input", () => {
    clearTimeout(LIB_TIMER);
    LIB_TIMER = setTimeout(reload, 180);
  });
  source.addEventListener("change", reload);
  type.addEventListener("change", reload);
  reload();
}
async function loadLibraryItems(q = "", source = "all", type = "all") {
  const req = ++LIB_REQUEST,
    results = document.querySelector("#lib-results");
  if (!results || S.page !== "lib") return;
  results.innerHTML = '<div class="lib-loading">Loading persisted items…</div>';
  try {
    const data = await api(
      "/api/library?" + new URLSearchParams({ q, source, type }).toString(),
    );
    if (req !== LIB_REQUEST || S.page !== "lib") return;
    LIB_ITEMS = Array.isArray(data.items) ? data.items : [];
    renderLibraryItems(data);
  } catch (error) {
    if (req !== LIB_REQUEST || S.page !== "lib") return;
    document.querySelector("#lib-total").textContent = "Unavailable";
    document.querySelector("#lib-source-status").innerHTML = "";
    results.innerHTML = `<div class="lib-error">Library could not be loaded: ${libEsc(error.message || error)}. Check the local backend and retry.</div>`;
  }
}
function renderLibraryItems(data) {
  const total = document.querySelector("#lib-total"),
    status = document.querySelector("#lib-source-status"),
    results = document.querySelector("#lib-results");
  if (!total || !status || !results) return;
  total.textContent = `${Number(data.total) || 0} item${Number(data.total) === 1 ? "" : "s"}`;
  status.innerHTML = Object.entries(data.source_status || {})
    .map(([key, v]) => {
      const state = String(v.state || "Unavailable"),
        cls =
          state === "Ready"
            ? "lib-ready"
            : state === "Unavailable"
              ? "lib-unavailable"
              : "lib-warning";
      return `<span class="${cls}">${libEsc(key === "knowledge" ? "Knowledge Base" : "GitHub")}: ${libEsc(state)} · ${Number(v.count) || 0} item${Number(v.count) === 1 ? "" : "s"}${v.message ? " — " + libEsc(v.message) : ""}</span>`;
    })
    .join("");
  if (!LIB_ITEMS.length) {
    const filtered = !!(
      document.querySelector("#lib-query")?.value ||
      document.querySelector("#lib-source")?.value !== "all" ||
      document.querySelector("#lib-type")?.value !== "all"
    );
    results.innerHTML = `<div class="lib-empty">${filtered ? "No persisted items match these filters. Try another search or source filter." : "No saved items yet. Add a Knowledge document, save a web citation, or index a GitHub project."}</div>`;
    return;
  }
  results.innerHTML = LIB_ITEMS.map((item) => {
    const m = item.metadata || {},
      source = String(item.source_label || item.source || "Source"),
      type = String(item.type || "item").replaceAll("_", " "),
      details = [],
      collections = (item.collections || []).join(", ");
    if (collections) details.push(collections);
    if (m.file_type) details.push(String(m.file_type).toUpperCase());
    if (m.page_count) details.push(`${m.page_count} pages`);
    if (m.file_count !== null && m.file_count !== undefined)
      details.push(`${m.file_count} indexed files`);
    if (m.branch) details.push(`branch ${m.branch}`);
    if (m.status) details.push(String(m.status));
    const desc = String(m.description || m.source_url || "");
    const date = libDate(m.updated || m.added || m.last_synced);
    return `<article class="lib-card"><div class="lib-card-top"><span class="lib-tag">${libEsc(source)}</span><span class="lib-tag">${libEsc(type)}</span></div><h2>${libEsc(item.title || "Untitled item")}</h2><p>${libEsc(desc || "Persisted item")}</p><div class="lib-card-meta">${details.map((x) => `<span class="lib-tag">${libEsc(x)}</span>`).join("")}${date ? `<span class="lib-tag">Updated ${libEsc(date)}</span>` : ""}</div><div class="lib-card-actions"><button class="lib-button" type="button" data-library-open="${libEsc(item.id)}">Open item</button>${m.source_url && libSafeUrl(m.source_url) ? `<a class="lib-external" href="${libEsc(libSafeUrl(m.source_url))}" target="_blank" rel="noopener noreferrer">Source page ↗</a>` : ""}</div></article>`;
  }).join("");
}
function libShow(title, html) {
  const overlay = document.querySelector("#lib-overlay"),
    heading = document.querySelector("#lib-dialog-title"),
    body = document.querySelector("#lib-dialog-body");
  if (!overlay || !heading || !body) return;
  heading.textContent = title || "Library item";
  body.innerHTML = html;
  overlay.hidden = false;
}
function libClose() {
  const overlay = document.querySelector("#lib-overlay");
  if (overlay) overlay.hidden = true;
}
async function openLibraryItem(id) {
  const item = LIB_ITEMS.find((x) => String(x.id) === String(id));
  if (!item) return;
  libShow(item.title, "<p>Loading the stored item…</p>");
  try {
    if (item.source === "knowledge") {
      const data = await api(
          "/api/kb/sources/" + encodeURIComponent(item.id) + "/text",
        ),
        pages = Array.isArray(data.pages) ? data.pages : [],
        shown = pages.slice(0, 12),
        url = libSafeUrl(item.metadata?.source_url);
      const html = `<div class="lib-dialog-meta">${(item.collections || []).map((x) => `<span class="lib-tag">${libEsc(x)}</span>`).join("")}<span class="lib-tag">${libEsc(item.type)}</span><span class="lib-tag">${pages.length} pages</span></div>${url ? `<p><a class="lib-external" href="${libEsc(url)}" target="_blank" rel="noopener noreferrer">Open original web source ↗</a></p>` : ""}${shown.length ? shown.map((p) => `<h3>${libEsc(p.kind || "Page")} ${libEsc(p.loc ?? "")}</h3><pre class="lib-page-text">${libEsc(p.text || p.error || "No extracted text is available.")}</pre>`).join("") : "<p>No extracted page text is available. The persisted source record remains in Knowledge.</p>"}${pages.length > shown.length ? `<p class="lib-source-note">Showing the first ${shown.length} of ${pages.length} pages.</p>` : ""}`;
      libShow(item.title, html);
    } else if (item.source === "github") {
      const p = await api(
          "/api/github/projects/" + encodeURIComponent(item.id),
        ),
        files = Array.isArray(p.files) ? p.files : [],
        url = libSafeUrl(p.html_url || item.metadata?.html_url),
        summary = [p.owner, p.name].filter(Boolean).join("/") || item.title;
      const html = `<div class="lib-dialog-meta"><span class="lib-tag">${libEsc(p.status || item.metadata.status || "Indexed")}</span><span class="lib-tag">${libEsc(p.branch || p.default_branch || "Branch not recorded")}</span><span class="lib-tag">${files.length} indexed files</span></div><p>${libEsc(p.description || item.metadata.description || "No repository description is stored.")}</p>${url ? `<p><a class="lib-external" href="${libEsc(url)}" target="_blank" rel="noopener noreferrer">Open ${libEsc(summary)} on GitHub ↗</a></p>` : ""}<h3>Indexed files</h3>${
        files.length
          ? `<div class="lib-files">${files
              .slice(0, 60)
              .map(
                (f) =>
                  `<div class="lib-file-row"><span>${libEsc(f.path || "Unnamed file")} <span class="lib-tag">${libEsc(f.language || "text")}</span></span><button class="lib-button" type="button" data-library-preview="${libEsc(item.id)}" data-library-path="${libEsc(f.path || "")}">Preview</button></div>`,
              )
              .join(
                "",
              )}</div>${files.length > 60 ? `<p class="lib-source-note">Showing 60 of ${files.length} files.</p>` : ""}`
          : "<p>No indexed files are available for this project.</p>"
      }`;
      libShow(item.title, html);
    }
  } catch (error) {
    libShow(
      item.title,
      `<div class="lib-error">Could not open stored item: ${libEsc(error.message || error)}. It may have been removed or unavailable.</div>`,
    );
  }
}
async function previewLibraryFile(id, path) {
  const body = document.querySelector("#lib-dialog-body");
  if (!body) return;
  body.innerHTML = "<p>Loading indexed file preview…</p>";
  try {
    const r = await api(
      "/api/github/projects/" +
        encodeURIComponent(id) +
        "/preview?path=" +
        encodeURIComponent(path),
    );
    body.innerHTML = `<p><button class="lib-button" type="button" data-library-open="${libEsc(id)}">← Back to project</button> <span class="lib-tag">${libEsc(r.language || "text")}</span></p><h3>${libEsc(r.path || path)}</h3><pre class="lib-page-text">${libEsc(r.content || "")}</pre>`;
  } catch (error) {
    body.innerHTML = `<div class="lib-error">File preview is unavailable: ${libEsc(error.message || error)}.</div>`;
  }
}
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-library-close]")) return libClose();
  if (e.target.id === "lib-overlay") return libClose();
  const open = e.target.closest("[data-library-open]");
  if (open) {
    e.preventDefault();
    return openLibraryItem(open.dataset.libraryOpen);
  }
  const preview = e.target.closest("[data-library-preview]");
  if (preview) {
    e.preventDefault();
    return previewLibraryFile(
      preview.dataset.libraryPreview,
      preview.dataset.libraryPath,
    );
  }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") libClose();
});
