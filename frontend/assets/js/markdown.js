(function () {
  function outside(s, fn) {
    return s
      .split(/(```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]*`)/g)
      .map((x, i) => (i % 2 ? x : fn(x)))
      .join("");
  }
  function normalize(raw) {
    let s = String(raw ?? "");
    const sig = (
      s.match(
        /(?:^|\n)\s*\\{1,}#{1,6}\s|\\{1,}\*\*[^\n]+?\\{1,}\*\*|\\{1,}\d+\\\.\s|(?:^|\n)\s*\\{1,}[*+-]\s/gm,
      ) || []
    ).length;
    const n = (s.match(/\\n/g) || []).length;
    const structure = /\\{1,}(?:#{1,6}\s|\*\*|\*\s|\d+\\?\.\s)/.test(s);
    if (sig >= 2 || (sig >= 1 && structure))
      s = outside(s, (x) =>
        x
          .replace(/(^|\n)([ \t]*)\\{1,}(#{1,6}\s)/g, "$1$2$3")
          .replace(/(^|\n)([ \t]*)\\{1,}([*+-])\s/g, "$1$2$3 ")
          .replace(/(^|\n)([ \t]*\d+)\\{1,}(\.\s)/g, "$1$2$3")
          .replace(/\\{1,}(\*\*[^\n]*?\*\*)/g, "$1")
          .replace(/\\{1,}(\*[^*\n]+\*)/g, "$1"),
      );
    if (
      !s.includes("\n") &&
      n >= 2 &&
      /\\n\\n|\\n\s*(?:#{1,6}\s|[-*+]\s|\d+\.\s)/.test(s)
    )
      s = outside(s, (x) => x.replace(/\\n/g, "\n"));
    return s;
  }
  window.normalizeStudioMarkdown = normalize;
  window.renderStudioMarkdown = function (raw) {
    const text = normalize(raw);
    if (!window.marked || !window.DOMPurify)
      return String(text)
        .replace(
          /[&<>"']/g,
          (c) =>
            ({
              "&": "&amp;",
              "<": "&lt;",
              ">": "&gt;",
              '"': "&quot;",
              "'": "&#39;",
            })[c],
        )
        .replace(/\n/g, "<br>");
    const html = window.marked.parse(text, { gfm: true, breaks: false });
    const safe = window.DOMPurify.sanitize(html, {
      USE_PROFILES: { html: true },
      ALLOWED_TAGS: [
        "p",
        "br",
        "hr",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "strong",
        "em",
        "del",
        "blockquote",
        "ul",
        "ol",
        "li",
        "pre",
        "code",
        "span",
        "a",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "sup",
        "sub",
      ],
      ALLOWED_ATTR: ["href", "title", "target", "rel", "class", "align"],
      ALLOW_DATA_ATTR: false,
      ALLOW_UNKNOWN_PROTOCOLS: false,
      FORBID_TAGS: [
        "script",
        "style",
        "iframe",
        "object",
        "embed",
        "form",
        "input",
        "button",
        "svg",
        "math",
      ],
      FORBID_ATTR: ["style", "onerror", "onclick", "onload"],
    });
    const box = document.createElement("div");
    box.innerHTML = safe;
    box.querySelectorAll("a[href]").forEach((a) => {
      try {
        const u = new URL(a.getAttribute("href"), location.href);
        if (
          ["http:", "https:"].includes(u.protocol) &&
          u.origin !== location.origin
        ) {
          a.target = "_blank";
          a.rel = "noopener noreferrer nofollow";
        } else if (!["http:", "https:", "mailto:", "tel:"].includes(u.protocol))
          a.removeAttribute("href");
      } catch (_) {
        a.removeAttribute("href");
      }
    });
    return box.innerHTML;
  };
})();
