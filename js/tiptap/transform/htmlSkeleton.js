/**
 * htmlSkeleton.js — native editor HTML ↔ custom IMPACT HTML
 *
 * Port of SummernoteManager TAG_MAP / transform / restore (no Summernote coupling).
 * IMPACT tags (em, strong, cite, …) ↔ editor tags (i, b, …) with data-format-id cache.
 *
 * @module transform/htmlSkeleton
 */

"use strict";

/** IMPACT tag → editor rule. */
export var TAG_MAP = {
  em: { editorTag: "i" },
  strong: { editorTag: "b" },
  cite: { editorTag: "i" },
  i: { editorTag: "i", passthrough: true },
  b: { editorTag: "b", passthrough: true },
  sup: { editorTag: "sup", onlyWhenAttrs: true },
  sub: { editorTag: "sub", onlyWhenAttrs: true },
  u: { editorTag: "u", onlyWhenAttrs: true },
  sc: { editorTag: "sc", onlyWhenAttrs: true },
  span: { editorTag: "span", onlyWhenAttrs: true },
};

/** Bare editor tags created by the user (no cache) → IMPACT defaults. */
export var DEFAULT_RESTORE = {
  i: {
    tag: "em",
    attrs: { class: "italic", "data-name": "italic" },
  },
  b: {
    tag: "strong",
    attrs: { "data-name": "bold" },
  },
};

/**
 * editorTag → Set of IMPACT tags that may restore into it.
 * @returns {Object.<string, Set<string>>}
 */
export function getEditorTagAllowed() {
  var allowed = {};
  Object.keys(TAG_MAP).forEach(function (impactTag) {
    var rule = TAG_MAP[impactTag];
    if (!rule || !rule.editorTag) return;
    if (!allowed[rule.editorTag]) allowed[rule.editorTag] = new Set();
    allowed[rule.editorTag].add(impactTag);
  });
  return allowed;
}

/** Live computed-style checks for stale data-format-id cleanup. */
export var LIVE_CHECK = {
  i: function (computed) {
    return (
      computed.fontStyle === "italic" || computed.fontStyle === "oblique"
    );
  },
  b: function (computed) {
    return (
      computed.fontWeight === "bold" ||
      parseInt(computed.fontWeight, 10) >= 600
    );
  },
  u: function (computed) {
    var deco = computed.textDecorationLine || computed.textDecoration || "";
    return deco.indexOf("underline") !== -1;
  },
  sup: function (computed) {
    return computed.verticalAlign === "super";
  },
  sub: function (computed) {
    return computed.verticalAlign === "sub";
  },
  sc: null,
  span: null,
};

/**
 * @param {Element} el
 * @returns {Object.<string, string>}
 */
export function collectElementAttrs(el) {
  var attrs = {};
  if (!el || !el.attributes) return attrs;
  Array.from(el.attributes).forEach(function (attr) {
    if (!attr || !attr.name) return;
    if (attr.name === "data-format-id") return;
    attrs[attr.name] = attr.value;
  });
  return attrs;
}

/**
 * @param {Element} el
 * @param {Object.<string, string>} attrs
 */
export function applyAttrs(el, attrs) {
  if (!el || !attrs) return;
  Object.keys(attrs).forEach(function (name) {
    if (attrs[name] == null) return;
    el.setAttribute(name, attrs[name]);
  });
}

/**
 * @param {Element} oldEl
 * @param {string} newTag
 * @returns {Element}
 */
export function replaceElementKeepChildren(oldEl, newTag) {
  var neu = document.createElement(newTag);
  while (oldEl.firstChild) {
    neu.appendChild(oldEl.firstChild);
  }
  if (oldEl.parentNode) {
    oldEl.parentNode.replaceChild(neu, oldEl);
  }
  return neu;
}

/**
 * Create / normalize a format-id cache bag: { map: Map, seq: number }.
 * @param {object} [bag]
 * @returns {{ map: Map, seq: number }}
 */
export function ensureBag(bag) {
  if (bag && bag.map && typeof bag.seq === "number") return bag;
  return { map: new Map(), seq: 0 };
}

/**
 * IMPACT HTML → native editor HTML (i/b/… + data-format-id).
 *
 * @param {string} html
 * @param {{ map: Map, seq: number }} [cacheBag]
 * @returns {string}
 */
export function transformToEditor(html, cacheBag) {
  if (html == null || html === "") return "";
  var bag = ensureBag(cacheBag);
  var root = document.createElement("div");
  root.innerHTML = String(html);
  var els = Array.from(root.querySelectorAll("*"));
  var i;
  for (i = els.length - 1; i >= 0; i--) {
    var el = els[i];
    if (!el || !el.tagName) continue;
    if (el.hasAttribute("data-format-id")) continue;

    var tag = el.tagName.toLowerCase();
    var rule = TAG_MAP[tag];
    if (!rule || rule.passthrough) continue;

    var attrs = collectElementAttrs(el);
    var attrKeys = Object.keys(attrs);
    if (rule.onlyWhenAttrs && attrKeys.length === 0) continue;

    bag.seq += 1;
    var id = String(bag.seq);
    bag.map.set(id, { tag: tag, attrs: attrs });

    var editorTag = rule.editorTag || tag;
    var target = el;
    if (editorTag !== tag) {
      target = replaceElementKeepChildren(el, editorTag);
    } else {
      Array.from(target.attributes)
        .map(function (a) {
          return a.name;
        })
        .forEach(function (name) {
          target.removeAttribute(name);
        });
    }
    target.setAttribute("data-format-id", id);
  }
  return root.innerHTML;
}

/**
 * Native editor HTML → IMPACT HTML (restore cached tags + DEFAULT_RESTORE).
 *
 * @param {string} html
 * @param {{ map: Map, seq: number }} [cacheBag]
 * @returns {string}
 */
export function restoreFromEditor(html, cacheBag) {
  if (html == null || html === "") return "";
  var bag = ensureBag(cacheBag);
  var allowedByEditorTag = getEditorTagAllowed();
  var root = document.createElement("div");
  root.innerHTML = String(html);

  var withIds = Array.from(root.querySelectorAll("[data-format-id]"));
  var i;
  for (i = withIds.length - 1; i >= 0; i--) {
    var el = withIds[i];
    var id = el.getAttribute("data-format-id");
    var cached = id && bag.map.get(String(id));
    var currentTag = el.tagName ? el.tagName.toLowerCase() : "";
    var allowedTags = allowedByEditorTag[currentTag];
    var cacheStillValid = !!(
      cached &&
      allowedTags &&
      allowedTags.has(cached.tag)
    );

    if (!cacheStillValid) {
      el.removeAttribute("data-format-id");
      continue;
    }

    var neu = replaceElementKeepChildren(el, cached.tag);
    applyAttrs(neu, cached.attrs || {});
  }

  var bare = Array.from(root.querySelectorAll("i, b"));
  for (i = bare.length - 1; i >= 0; i--) {
    var bareEl = bare[i];
    if (!bareEl || !bareEl.parentNode) continue;
    if (bareEl.hasAttribute("data-format-id")) continue;
    var bareTag = bareEl.tagName.toLowerCase();
    var def = DEFAULT_RESTORE[bareTag];
    if (!def) continue;
    var restored = replaceElementKeepChildren(bareEl, def.tag);
    applyAttrs(restored, def.attrs || {});
  }

  return unwrapParagraphs(root.innerHTML);
}

/**
 * Strip wrapping <p> tags (Summernote-compatible).
 * @param {string} html
 * @returns {string}
 */
export function unwrapParagraphs(html) {
  var doc = document.createElement("span");
  doc.innerHTML = html == null ? "" : String(html);
  Array.from(doc.querySelectorAll("p")).forEach(function (el) {
    el.after.apply(el, Array.from(el.childNodes));
    if (el.parentNode) el.parentNode.removeChild(el);
  });
  return doc.innerHTML;
}

/**
 * Drop stale data-format-id when live style no longer matches the editor tag.
 * @param {Element} editableEl
 */
export function reconcileAfterCommand(editableEl) {
  if (!editableEl) return;
  var candidates = Array.from(
    editableEl.querySelectorAll("[data-format-id]")
  );
  if (!candidates.length) return;

  candidates.forEach(function (el) {
    var tag = el.tagName ? el.tagName.toLowerCase() : "";
    var check = LIVE_CHECK[tag];
    if (typeof check !== "function") return;
    var computed = window.getComputedStyle(el);
    if (!check(computed)) {
      el.removeAttribute("data-format-id");
    }
  });
}

export default {
  TAG_MAP: TAG_MAP,
  DEFAULT_RESTORE: DEFAULT_RESTORE,
  LIVE_CHECK: LIVE_CHECK,
  getEditorTagAllowed: getEditorTagAllowed,
  transformToEditor: transformToEditor,
  restoreFromEditor: restoreFromEditor,
  unwrapParagraphs: unwrapParagraphs,
  reconcileAfterCommand: reconcileAfterCommand,
  ensureBag: ensureBag,
  collectElementAttrs: collectElementAttrs,
  applyAttrs: applyAttrs,
  replaceElementKeepChildren: replaceElementKeepChildren,
};
