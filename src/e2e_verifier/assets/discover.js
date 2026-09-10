([query, maxResults]) => {
  const IMPLICIT_ROLES = {
    a: "link",
    button: "button",
    select: "combobox",
    textarea: "textbox",
    summary: "button",
    nav: "navigation",
    main: "main",
    header: "banner",
    footer: "contentinfo",
    form: "form",
    table: "table",
    img: "img",
    h1: "heading",
    h2: "heading",
    h3: "heading",
    h4: "heading",
    h5: "heading",
    h6: "heading",
    li: "listitem",
    ul: "list",
    ol: "list",
    dialog: "dialog",
    output: "status",
    progress: "progressbar"
  };
  const INPUT_ROLES = {
    button: "button",
    submit: "button",
    reset: "button",
    image: "button",
    checkbox: "checkbox",
    radio: "radio",
    range: "slider",
    number: "spinbutton",
    search: "searchbox",
    email: "textbox",
    text: "textbox",
    password: "textbox",
    url: "textbox",
    tel: "textbox"
  };
  const clean = (value) => (value || "").replace(/\s+/g, " ").trim();
  const roleOf = (el) => {
    const explicit = el.getAttribute("role");
    if (explicit) {
      return explicit.split(/\s+/)[0];
    }
    const tag = el.tagName.toLowerCase();
    if (tag === "input") {
      const type = (el.getAttribute("type") || "text").toLowerCase();
      return INPUT_ROLES[type] || null;
    }
    if (tag === "a") {
      return el.hasAttribute("href") ? "link" : null;
    }
    return IMPLICIT_ROLES[tag] || null;
  };
  const labelOf = (el) => {
    if (el.labels && el.labels.length) {
      return clean(el.labels[0].textContent) || null;
    }
    const labelledBy = el.getAttribute("aria-labelledby");
    if (labelledBy) {
      const node = document.getElementById(labelledBy.split(/\s+/)[0]);
      if (node) {
        return clean(node.textContent) || null;
      }
    }
    return null;
  };
  const buttonValue = (el) => {
    const tag = el.tagName.toLowerCase();
    if (tag !== "input") {
      return "";
    }
    const type = (el.getAttribute("type") || "text").toLowerCase();
    return ["button", "submit", "reset"].includes(type) ? el.value : "";
  };
  const nameOf = (el) =>
    clean(el.getAttribute("aria-label")) ||
    labelOf(el) ||
    clean(el.innerText || el.textContent) ||
    clean(el.getAttribute("title")) ||
    clean(el.getAttribute("alt")) ||
    clean(buttonValue(el)) ||
    null;
  const cssPath = (el) => {
    const segments = [];
    let node = el;
    while (node && node.nodeType === 1 && node !== document.documentElement) {
      if (node.id) {
        segments.unshift(`#${CSS.escape(node.id)}`);
        break;
      }
      let segment = node.tagName.toLowerCase();
      const parent = node.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter((s) => s.tagName === node.tagName);
        if (siblings.length > 1) {
          segment += `:nth-of-type(${siblings.indexOf(node) + 1})`;
        }
      }
      segments.unshift(segment);
      node = parent;
    }
    return segments.join(" > ");
  };
  const isVisible = (el) => {
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  };
  const needle = clean(query).toLowerCase();
  const selector = "a, button, input, select, textarea, summary, label, [role], [data-testid], [tabindex], [onclick]";
  const results = [];
  for (const el of document.querySelectorAll(selector)) {
    if (el.closest("e2e-hud")) {
      continue;
    }
    const name = nameOf(el);
    const testId = el.getAttribute("data-testid");
    const placeholder = clean(el.getAttribute("placeholder")) || null;
    const label = labelOf(el);
    const haystack = [name, testId, el.id, placeholder, label, el.getAttribute("name")]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    if (needle && !haystack.includes(needle)) {
      continue;
    }
    const rect = el.getBoundingClientRect();
    results.push({
      tag: el.tagName.toLowerCase(),
      role: roleOf(el),
      name: name ? name.slice(0, 120) : null,
      label,
      placeholder,
      test_id: testId,
      element_id: el.id || null,
      css: cssPath(el),
      visible: isVisible(el),
      disabled: el.disabled === true || el.getAttribute("aria-disabled") === "true",
      rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
    });
    if (results.length >= maxResults) {
      break;
    }
  }
  return results;
}
