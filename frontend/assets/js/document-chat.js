/* ---------- document chat: answers restricted to the selected local documents ---------- */
function docStateLabel(sel) {
  if (S.docLoading) return ["", "Checking selection…"];
  if (!sel) return ["error", "Selection unavailable"];
  if (sel.ready) return ["ready", "Ready"];
  if ((sel.missing || []).length) return ["missing", "Missing documents"];
  if ((sel.not_indexed || []).length) return ["unindexed", "Not indexed"];
  return ["error", "Unavailable"];
}
function docStatusMarkup() {
  const sel = S.docSel;
  if (S.docLoading) {
    return `<section class="doc-panel is-loading" aria-live="polite" aria-busy="true">
   <div class="doc-panel-top"><h2>${ic("file")} Document chat</h2><span class="doc-state">Loading<i></i></span></div>
   <div class="doc-list"><div class="doc-item" style="flex:1 1 220px"><div class="doc-skeleton" style="width:60%"></div><div class="doc-skeleton" style="width:85%;margin-top:7px"></div></div></div>
   <p class="doc-panel-note">Checking the selected documents and their index status…</p></section>`;
  }
  if (!sel) return "";
  const [state, label] = docStateLabel(sel),
    docs = sel.documents || [];
  const rows = docs
    .map((d) => {
      const ok = !!d.indexed,
        chunks = Number(d.chunks || 0);
      return `<div class="doc-item ${ok ? "ok" : "warn"}">
   <b>${esc(d.title || "Untitled document")}</b>
   <div class="doc-meta"><code class="doc-id" title="Document database ID">${esc(d.id || "—")}</code>
    <span class="doc-tag">${esc(ok ? "indexed" : "not indexed")}</span>
    <span>${esc(String(d.type || "text").toUpperCase())} · ${chunks} passage${chunks === 1 ? "" : "s"}</span>
   </div></div>`;
    })
    .join("");
  const missing = (sel.missing || [])
    .map(
      (n) =>
        `<div class="doc-item warn"><b>${esc(n)}</b><div class="doc-meta"><span class="doc-tag">missing</span><span>No matching document in the Knowledge Base</span></div></div>`,
    )
    .join("");
  const notes = [];
  if (state === "missing")
    notes.push(
      `<strong>Not found:</strong> ${esc((sel.missing || []).join(", "))}. Add or rename the document in Knowledge, then reopen Document chat.`,
    );
  if (state === "unindexed")
    notes.push(
      `<strong>Not indexed:</strong> ${esc((sel.not_indexed || []).join(", "))}. Open Knowledge and use Re-index.`,
    );
  if (state === "error")
    notes.push(
      esc(
        sel.message ||
          "The selection could not be resolved. Check the local backend and retry.",
      ),
    );
  return `<section class="doc-panel" aria-live="polite">
  <div class="doc-panel-top"><h2>${ic("file")} Document chat</h2><span class="doc-state ${esc(state)}"><i></i>${esc(label)}</span><button type="button" class="btn doc-recheck" data-a="docrefresh" title="Recheck the selected documents">Recheck</button></div>
  <div class="doc-list">${rows}${missing}</div>
  <p class="doc-panel-note">${
    state === "ready"
      ? "Only these documents are searched. Web search and other collections are disabled; citations name the document and page."
      : notes.join(" ")
  }${state !== "ready" ? ' <button type="button" class="doc-link" data-a="nav:kb">Open Knowledge</button>' : ""}</p>
 </section>`;
}
async function loadDocSelection() {
  S.docLoading = true;
  S.docSel = null;
  if (S.page === "doc" || S.page === "chat") chatView();
  const sel = await refreshDocSelection();
  S.docLoading = false;
  if (S.page !== "doc" && S.page !== "chat") return sel;
  S.docSel = sel;
  if (S.page === "doc") {
    S.docMode = !!sel.ready;
    if (S.docMode) {
      S.webMode = "off";
      S.kb = [];
    }
  }
  chatView();
  side();
  if (S.page === "doc" && !sel.ready) {
    const b = $("#ban");
    if (b)
      b.textContent =
        (sel.message ||
          "Document chat is unavailable: the selected documents are not ready.") +
        " Fix the selection in Knowledge, then reopen Document chat.";
  }
  return sel;
}
async function docView() {
  S.page = "doc";
  chatView();
  side();
  return loadDocSelection();
}
