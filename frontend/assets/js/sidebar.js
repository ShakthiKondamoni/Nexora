/* ---------- sidebar ---------- */
function side() {
  const nav = $("#nav"),
    hist = $("#hist"),
    ns = nav ? nav.scrollTop : 0,
    hs = hist ? hist.scrollTop : 0;
  const A = S.chats.filter(
    (c) => !c.archived && c.title.toLowerCase().includes(S.q.toLowerCase()),
  );
  const row = (c) =>
    `<div class="ch ${c.id === S.cid && S.page === "chat" ? "on" : ""}" data-a="open:${c.id}"><span class="t" title="${esc(c.title)}">${esc(c.title)}</span><span class="act"><button class="ib" data-a="pin:${c.id}" title="${c.pinned ? "Unpin" : "Pin"}">${ic("pin")}</button><button class="ib" data-a="menu:${c.id}" title="More">${ic("more")}</button></span></div>`;
  const gh = (k, n, x = "") =>
    `<div class="gh" data-a="tog:${k}"><span>${S.open[k] ? "▾" : "▸"} ${n}</span>${x}</div>`;
  const pin = A.filter((c) => c.pinned),
    rec = A.filter((c) => !c.pinned && !c.project_id),
    dg = (t) => {
      const d = (Date.now() / 1000 - t) / 86400;
      return d < 1
        ? "Today"
        : d < 2
          ? "Yesterday"
          : d < 7
            ? "Previous 7 days"
            : "Older";
    };
  let rh = "",
    lg = "";
  for (const c of rec) {
    const g = dg(c.updated);
    if (g !== lg) {
      rh += `<div class="sub">${g}</div>`;
      lg = g;
    }
    rh += row(c);
  }
  const ph =
    S.projects
      .map((p) => {
        const l = A.filter((c) => c.project_id === p.id && !c.pinned);
        return (
          `<div class="sub">${esc(p.name)}</div>` +
          (l.map(row).join("") || '<div class="em">Empty</div>')
        );
      })
      .join("") || '<div class="em">No projects yet</div>';
  const ar = S.chats.filter((c) => c.archived);
  $("#side").className = S.col ? "c" : "";
  $("#side").innerHTML =
    `<div class="hd">${ic("box")}<b>Nexora</b><button class="ib" id="sbtn" data-a="search" title="Search chats">${ic("search")}</button><button class="ib" data-a="col" title="Collapse sidebar">${ic("panel")}</button></div>
 <nav id="nav">${NAV.map(([id, l, i]) => `<button class="ni ${S.page === id ? "on" : ""}" data-a="nav:${id}" title="${l}">${ic(i)}<span class="lb">${l}</span></button>`).join("")}</nav>
 <div id="hist">${S.sq ? `<input id="sq" placeholder="Search chats" value="${esc(S.q)}">` : ""}${gh("p", "Pinned")}${S.open.p ? pin.map(row).join("") || '<div class="em">No pinned chats</div>' : ""}
 ${gh("j", "Projects", `<span data-a="newproj" title="New project">+</span>`)}${S.open.j ? ph : ""}${gh("r", "Recents")}${S.open.r ? rh || '<div class="em">No chats yet</div>' : ""}
 ${ar.length ? `<div class="gh" data-a="arch"><span>${S.arch ? "▾" : "▸"} Archived (${ar.length})</span></div>${S.arch ? ar.map(row).join("") : ""}` : ""}</div>
 <div class="acct">${ic("sliders")}<span class="lb">Local · Ollama</span></div>`;
  const nav2 = $("#nav"),
    hist2 = $("#hist");
  if (nav2) {
    nav2.scrollTop = ns;
    if (side._page !== S.page) {
      const on = nav2.querySelector(".ni.on");
      if (on) on.scrollIntoView({ block: "nearest" });
    }
  }
  if (hist2) hist2.scrollTop = hs;
  side._page = S.page;
  const q = $("#sq");
  if (q) {
    q.focus();
    q.setSelectionRange(99, 99);
    q.oninput = () => {
      S.q = q.value;
      side();
    };
  }
}
async function loadChats() {
  const d = await api("/api/chats");
  S.chats = d.chats;
  S.projects = d.projects;
  side();
}
async function loadModels() {
  try {
    S.models = (await api("/api/models")).models;
    S.merr = null;
    S.model = S.cfg.chat_model || "";
  } catch (e) {
    S.merr = e.message;
  }
}
function go(p, keep) {
  S.page = p;
  clearInterval(pt);
  S.redraw = null;
  if ((p === "chat" || p === "doc") && !keep) {
    S.cid = null;
    S.msgs = [];
    S.att = [];
    S.kb = [];
    S.docMode = false;
    S.docSel = null;
  }
  side();
  if (!DONE[p]) {
    $("#main").innerHTML =
      `<div class="pg"><h1>${NAV.find((n) => n[0] === p)[1]}</h1><p class="mu">Not built yet — planned for stage ${STAGE[p]} of your build order. Nothing here is a mock-up.</p></div>`;
    return;
  }
  ({
    chat: chatView,
    dash: dashView,
    status: statusView,
    task: taskView,
    models: modelsView,
    set: setView,
    kb: kbView,
    github: githubView,
    lib: libraryView,
    code: codeView,
    doc: docView,
  })[p]();
}
function menu(x, y, h) {
  const m = $("#menu");
  m.innerHTML = h;
  m.style.left = Math.min(x, innerWidth - 190) + "px";
  m.style.top = Math.min(y, innerHeight - 260) + "px";
  m.style.display = "block";
}
document.addEventListener("click", async (e) => {
  const m = $("#menu");
  if (!m.contains(e.target)) m.style.display = "none";
  if (e.target === $("#modal")) closeModal();
  if (!e.target.closest('#amenu,[data-a="attach"]'))
    $("#amenu").style.display = "none";
  const t = e.target.closest("[data-a]");
  if (!t) return;
  const [k, v, w] = t.dataset.a.split(":");
  m.style.display = "none";
  $("#amenu").style.display = "none";
  try {
    if (k === "nav") return go(v);
    if (k === "col") {
      S.col = !S.col;
      return side();
    }
    if (k === "search") {
      S.sq = !S.sq;
      S.q = "";
      return side();
    }
    if (k === "tog") {
      S.open[v] = !S.open[v];
      return side();
    }
    if (k === "arch") {
      S.arch = !S.arch;
      return side();
    }
    if (k === "open") {
      S.cid = v;
      S.docMode = false;
      S.docSel = null;
      S.msgs = (await api(`/api/chats/${v}/messages`)).map((m) => ({
        ...m,
        webMode: m.webMode || m.web_mode,
        sources: m.sources ? JSON.parse(m.sources) : [],
      }));
      S.att = [];
      return go("chat", 1);
    }
    if (k === "pin") {
      const c = S.chats.find((c) => c.id === v);
      await api("/api/chats/" + v, "PATCH", { pinned: c.pinned ? 0 : 1 });
      return loadChats();
    }
    if (k === "newproj") {
      const n = prompt("Project name");
      if (n) {
        await api("/api/projects", "POST", { name: n });
        loadChats();
      }
      return;
    }
    if (k === "menu") {
      const c = S.chats.find((c) => c.id === v);
      return menu(
        e.clientX,
        e.clientY,
        `<button data-a="m_ren:${v}">Rename</button><button data-a="pin:${v}">${c.pinned ? "Unpin" : "Pin"}</button>${S.projects.map((p) => `<button data-a="m_mv:${v}:${p.id}">Move to ${esc(p.name)}</button>`).join("")}${c.project_id ? `<button data-a="m_mv:${v}:">Remove from project</button>` : ""}<button data-a="m_arc:${v}">${c.archived ? "Unarchive" : "Archive"}</button><button data-a="m_exp:${v}">Export (.md)</button><button data-a="m_del:${v}" style="color:#f87171">Delete</button>`,
      );
    }
    if (k === "m_ren") {
      const c = S.chats.find((c) => c.id === v),
        n = prompt("Rename chat", c.title);
      if (n) {
        await api("/api/chats/" + v, "PATCH", { title: n });
        loadChats();
      }
      return;
    }
    if (k === "m_mv") {
      await api("/api/chats/" + v, "PATCH", { project_id: w || null });
      return loadChats();
    }
    if (k === "m_arc") {
      const c = S.chats.find((c) => c.id === v);
      await api("/api/chats/" + v, "PATCH", { archived: c.archived ? 0 : 1 });
      return loadChats();
    }
    if (k === "m_exp") {
      const ms = await api(`/api/chats/${v}/messages`),
        c = S.chats.find((c) => c.id === v);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(
        new Blob(
          [
            `# ${c.title}\n\n` +
              ms
                .map((m) => `**${m.role}:**\n\n${m.content}`)
                .join("\n\n---\n\n"),
          ],
          { type: "text/markdown" },
        ),
      );
      a.download = c.title.replace(/\W+/g, "_") + ".md";
      a.click();
      return;
    }
    if (k === "m_del") {
      if (confirm("Delete this chat permanently?")) {
        await api("/api/chats/" + v, "DELETE");
        if (S.cid === v) go("chat");
        loadChats();
      }
      return;
    }
    if (await kact(k, v, w, t, e)) return;
    if (k === "rm") {
      S.att.splice(+v, 1);
      return chips();
    }
    if (k === "send") return S.gen ? S.gen.abort() : send();
    if (k === "copy") {
      navigator.clipboard.writeText(S.msgs[+v].content);
      return;
    }
    if (k === "regen") {
      await api(`/api/chats/${S.cid}/last`, "DELETE");
      S.msgs.pop();
      return send(true);
    }
    if (k === "rng") {
      S.range = +v;
      return S.redraw && S.redraw();
    }
    if (k === "pause") {
      S.pause = !S.pause;
      t.classList.toggle("on", S.pause);
      t.textContent = S.pause ? "Resume" : "Pause";
      return;
    }
    if (k === "useM") {
      applyCfg(await api("/api/settings", "PUT", { chat_model: v }));
      return go("chat");
    }
    if (k === "testM") {
      t.textContent = "Testing…";
      try {
        t.textContent =
          "✔ " +
          (await api("/api/test", "POST", { model: v })).reply.slice(0, 40);
      } catch (er) {
        t.textContent = "✖ " + er.message.slice(0, 120);
      }
      return;
    }
    if (k === "sort") {
      S.sort = v;
      return procRows();
    }
  } catch (er) {
    alert(er.message);
  }
});
