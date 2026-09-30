/**
 * iceBridge.js — CKEditor4 + nytimes/ice (lite) ↔ TipTap track-changes HTML
 *
 * Load:  ICE ins/del (ice-ins / ice-del, data-cid, …) → TipTap marks HTML
 *        (<ins|del data-change-id data-author-id data-author-name data-timestamp>)
 * Save:  TipTap track marks HTML → ICE lite ins/del with ICE attrs + classes
 *
 * Formatting (em/strong/…) stays with htmlSkeleton; call ICE bridge around it:
 *   set: iceHtmlToEditor → transformToEditor
 *   get: restoreFromEditor → editorHtmlToIce
 *
 * @module transform/iceBridge
 */

"use strict";

/** ICE class / attribute conventions (nytimes/ice + common CKEditor lite). */
export var ICE_INS_CLASS = "ice-ins";
export var ICE_DEL_CLASS = "ice-del";
/** Vanilla ice alias classes (span.ins / span.del) when data-cid is present. */
export var ICE_ALIAS_INS = "ins";
export var ICE_ALIAS_DEL = "del";

export var ICE_ATTR = {
  cid: "data-cid",
  userid: "data-userid",
  username: "data-username",
  time: "data-time",
  changedata: "data-changedata",
};

/** tiptap-track-changes InsertionMark / DeletionMark HTML attrs. */
export var TIPTAP_ATTR = {
  changeId: "data-change-id",
  authorId: "data-author-id",
  authorName: "data-author-name",
  timestamp: "data-timestamp",
};

var CTS_CLASS_RE = /^(?:ice-)?cts-\d+$/i;
var ICE_INS_RE = /\b(?:ice-ins)\b/i;
var ICE_DEL_RE = /\b(?:ice-del)\b/i;

/**
 * @typedef {object} IceChangeMeta
 * @property {'ins'|'del'} type
 * @property {string} [cid]
 * @property {string} [userid]
 * @property {string} [username]
 * @property {string} [time]
 * @property {string} [changedata]
 * @property {string} [ctsClass] e.g. cts-1 / ice-cts-1
 * @property {string} [title]
 * @property {string} [tag] original tag (ins|del|span)
 */

/**
 * @param {string|null|undefined} html
 * @returns {string}
 */
function asString(html) {
  return html == null ? "" : String(html);
}

/**
 * @param {Element} el
 * @returns {string}
 */
function classNameOf(el) {
  if (!el) return "";
  if (typeof el.className === "string") return el.className;
  if (el.getAttribute) return el.getAttribute("class") || "";
  return "";
}

/**
 * @param {string} className
 * @returns {string[]}
 */
function classTokens(className) {
  return String(className || "")
    .split(/\s+/)
    .filter(Boolean);
}

/**
 * @param {Element} el
 * @returns {string|null}
 */
function findCtsClass(el) {
  var tokens = classTokens(classNameOf(el));
  var i;
  for (i = 0; i < tokens.length; i++) {
    if (CTS_CLASS_RE.test(tokens[i])) return tokens[i];
  }
  return null;
}

/**
 * @param {Element} el
 * @returns {boolean}
 */
function hasDataCid(el) {
  return !!(el && el.getAttribute && el.getAttribute(ICE_ATTR.cid));
}

/**
 * True when el is an ICE insert wrapper.
 * @param {Element} el
 * @returns {boolean}
 */
export function isIceInsert(el) {
  if (!el || !el.tagName) return false;
  var tag = el.tagName.toLowerCase();
  var cls = classNameOf(el);
  if (ICE_INS_RE.test(cls)) return true;
  if (tag === "ins" && hasDataCid(el)) return true;
  // Vanilla ice: <span class="ins cts-1" data-cid="…">
  if (
    (tag === "span" || tag === "ins") &&
    hasDataCid(el) &&
    classTokens(cls).indexOf(ICE_ALIAS_INS) !== -1
  ) {
    return true;
  }
  return false;
}

/**
 * True when el is an ICE delete wrapper.
 * @param {Element} el
 * @returns {boolean}
 */
export function isIceDelete(el) {
  if (!el || !el.tagName) return false;
  var tag = el.tagName.toLowerCase();
  var cls = classNameOf(el);
  if (ICE_DEL_RE.test(cls)) return true;
  if (tag === "del" && hasDataCid(el)) return true;
  if (
    (tag === "span" || tag === "del") &&
    hasDataCid(el) &&
    classTokens(cls).indexOf(ICE_ALIAS_DEL) !== -1
  ) {
    return true;
  }
  return false;
}

/**
 * TipTap track insertion (ins[data-change-id]).
 * @param {Element} el
 * @returns {boolean}
 */
export function isTipTapInsert(el) {
  if (!el || !el.tagName) return false;
  return (
    el.tagName.toLowerCase() === "ins" &&
    !!el.getAttribute(TIPTAP_ATTR.changeId)
  );
}

/**
 * TipTap track deletion (del[data-change-id]).
 * @param {Element} el
 * @returns {boolean}
 */
export function isTipTapDelete(el) {
  if (!el || !el.tagName) return false;
  return (
    el.tagName.toLowerCase() === "del" &&
    !!el.getAttribute(TIPTAP_ATTR.changeId)
  );
}

/**
 * @param {Element} el
 * @param {'ins'|'del'} type
 * @returns {IceChangeMeta}
 */
function readIceMeta(el, type) {
  return {
    type: type,
    cid: el.getAttribute(ICE_ATTR.cid) || "",
    userid: el.getAttribute(ICE_ATTR.userid) || "",
    username: el.getAttribute(ICE_ATTR.username) || "",
    time: el.getAttribute(ICE_ATTR.time) || "",
    changedata: el.getAttribute(ICE_ATTR.changedata) || "",
    ctsClass: findCtsClass(el) || "",
    title: el.getAttribute("title") || "",
    tag: el.tagName ? el.tagName.toLowerCase() : "",
  };
}

/**
 * @param {Map|object|null|undefined} metaBag
 * @returns {Map}
 */
function ensureMetaMap(metaBag) {
  if (metaBag && typeof metaBag.set === "function" && typeof metaBag.get === "function") {
    return metaBag;
  }
  return new Map();
}

/**
 * @param {Map} metaMap
 * @param {IceChangeMeta} meta
 */
function storeMeta(metaMap, meta) {
  if (!metaMap || !meta) return;
  var key = meta.cid ? String(meta.cid) : "";
  if (!key) return;
  metaMap.set(key, meta);
}

/**
 * Move children from oldEl into neu and replace in parent.
 * @param {Element} oldEl
 * @param {Element} neu
 * @returns {Element}
 */
function replaceKeepingChildren(oldEl, neu) {
  while (oldEl.firstChild) {
    neu.appendChild(oldEl.firstChild);
  }
  if (oldEl.parentNode) {
    oldEl.parentNode.replaceChild(neu, oldEl);
  }
  return neu;
}

/**
 * Strip ICE / TipTap tracking attrs and ice/cts classes from el (in place).
 * @param {Element} el
 */
function clearTrackAttrsAndClasses(el) {
  if (!el || !el.removeAttribute) return;
  [
    ICE_ATTR.cid,
    ICE_ATTR.userid,
    ICE_ATTR.username,
    ICE_ATTR.time,
    ICE_ATTR.changedata,
    TIPTAP_ATTR.changeId,
    TIPTAP_ATTR.authorId,
    TIPTAP_ATTR.authorName,
    TIPTAP_ATTR.timestamp,
    "title",
  ].forEach(function (name) {
    el.removeAttribute(name);
  });

  // Drop --author-color style TipTap injects; keep other inline styles.
  var style = el.getAttribute("style");
  if (style && /--author-color/i.test(style)) {
    var cleaned = style
      .split(";")
      .map(function (part) {
        return part.trim();
      })
      .filter(function (part) {
        return part && !/^--author-color\s*:/i.test(part);
      })
      .join("; ");
    if (cleaned) el.setAttribute("style", cleaned);
    else el.removeAttribute("style");
  }

  var kept = classTokens(classNameOf(el)).filter(function (tok) {
    if (ICE_INS_RE.test(tok) || ICE_DEL_RE.test(tok)) return false;
    if (tok === ICE_ALIAS_INS || tok === ICE_ALIAS_DEL) return false;
    if (CTS_CLASS_RE.test(tok)) return false;
    return true;
  });
  if (kept.length) el.setAttribute("class", kept.join(" "));
  else el.removeAttribute("class");
}

/**
 * Convert one ICE node into TipTap track mark HTML element.
 * @param {Element} el
 * @param {'ins'|'del'} type
 * @param {Map} metaMap
 * @returns {Element}
 */
function convertIceNodeToTipTap(el, type, metaMap) {
  var meta = readIceMeta(el, type);
  if (!meta.cid) {
    meta.cid = "ice-" + String(Date.now()) + "-" + String(Math.floor(Math.random() * 1e6));
  }
  storeMeta(metaMap, meta);

  var tag = type === "ins" ? "ins" : "del";
  var neu = document.createElement(tag);
  replaceKeepingChildren(el, neu);
  clearTrackAttrsAndClasses(neu);

  neu.setAttribute(TIPTAP_ATTR.changeId, meta.cid);
  if (meta.userid) neu.setAttribute(TIPTAP_ATTR.authorId, meta.userid);
  if (meta.username) neu.setAttribute(TIPTAP_ATTR.authorName, meta.username);
  if (meta.time) neu.setAttribute(TIPTAP_ATTR.timestamp, meta.time);

  return neu;
}

/**
 * ICE HTML → TipTap-loadable track HTML.
 * Recognizes:
 *   <ins class="ice-ins" data-cid …>, <del class="ice-del" …>
 *   <span class="ice-ins|ins" data-cid …> (vanilla ice default tag)
 *
 * TipTap InsertionMark / DeletionMark parse `ins|del[data-change-id]`.
 *
 * @param {string} html
 * @param {{ meta?: Map }} [opts] optional Map filled with IceChangeMeta by cid
 * @returns {string}
 */
export function iceHtmlToEditor(html, opts) {
  opts = opts || {};
  var raw = asString(html);
  if (!raw) return "";
  if (typeof document === "undefined") {
    throw new Error("iceHtmlToEditor requires a DOM document");
  }

  var metaMap = ensureMetaMap(opts.meta);
  if (opts.meta !== metaMap && opts.meta == null) {
    // caller did not pass meta; local map is fine (ephemeral)
  }

  var root = document.createElement("div");
  root.innerHTML = raw;

  var els = Array.from(root.querySelectorAll("*"));
  var i;
  // Deepest-first so nested ice wrappers convert inward-out.
  for (i = els.length - 1; i >= 0; i--) {
    var el = els[i];
    if (!el || !el.parentNode) continue;
    // Already TipTap-shaped — still harvest meta if ICE attrs linger.
    if (isTipTapInsert(el) || isTipTapDelete(el)) {
      var existingType = isTipTapInsert(el) ? "ins" : "del";
      var cid =
        el.getAttribute(TIPTAP_ATTR.changeId) ||
        el.getAttribute(ICE_ATTR.cid) ||
        "";
      if (cid) {
        storeMeta(metaMap, {
          type: existingType,
          cid: cid,
          userid:
            el.getAttribute(TIPTAP_ATTR.authorId) ||
            el.getAttribute(ICE_ATTR.userid) ||
            "",
          username:
            el.getAttribute(TIPTAP_ATTR.authorName) ||
            el.getAttribute(ICE_ATTR.username) ||
            "",
          time:
            el.getAttribute(TIPTAP_ATTR.timestamp) ||
            el.getAttribute(ICE_ATTR.time) ||
            "",
          changedata: el.getAttribute(ICE_ATTR.changedata) || "",
          ctsClass: findCtsClass(el) || "",
          title: el.getAttribute("title") || "",
          tag: el.tagName.toLowerCase(),
        });
      }
      // Normalize: ensure TipTap attrs, drop ICE classes.
      if (el.getAttribute(ICE_ATTR.cid) && !el.getAttribute(TIPTAP_ATTR.changeId)) {
        el.setAttribute(TIPTAP_ATTR.changeId, el.getAttribute(ICE_ATTR.cid));
      }
      if (el.getAttribute(ICE_ATTR.userid) && !el.getAttribute(TIPTAP_ATTR.authorId)) {
        el.setAttribute(TIPTAP_ATTR.authorId, el.getAttribute(ICE_ATTR.userid));
      }
      if (el.getAttribute(ICE_ATTR.username) && !el.getAttribute(TIPTAP_ATTR.authorName)) {
        el.setAttribute(
          TIPTAP_ATTR.authorName,
          el.getAttribute(ICE_ATTR.username)
        );
      }
      if (el.getAttribute(ICE_ATTR.time) && !el.getAttribute(TIPTAP_ATTR.timestamp)) {
        el.setAttribute(TIPTAP_ATTR.timestamp, el.getAttribute(ICE_ATTR.time));
      }
      // Remove ICE-only attrs/classes; keep TipTap attrs.
      el.removeAttribute(ICE_ATTR.cid);
      el.removeAttribute(ICE_ATTR.userid);
      el.removeAttribute(ICE_ATTR.username);
      el.removeAttribute(ICE_ATTR.time);
      el.removeAttribute(ICE_ATTR.changedata);
      var keptTt = classTokens(classNameOf(el)).filter(function (tok) {
        if (ICE_INS_RE.test(tok) || ICE_DEL_RE.test(tok)) return false;
        if (tok === ICE_ALIAS_INS || tok === ICE_ALIAS_DEL) return false;
        if (CTS_CLASS_RE.test(tok)) return false;
        return true;
      });
      if (keptTt.length) el.setAttribute("class", keptTt.join(" "));
      else el.removeAttribute("class");
      continue;
    }

    if (isIceInsert(el)) {
      convertIceNodeToTipTap(el, "ins", metaMap);
    } else if (isIceDelete(el)) {
      convertIceNodeToTipTap(el, "del", metaMap);
    }
  }

  // Expose map to caller when they passed a bag-like object without Map API.
  if (opts.meta && opts.meta !== metaMap && typeof opts.meta === "object") {
    metaMap.forEach(function (v, k) {
      opts.meta[k] = v;
    });
  }

  return root.innerHTML;
}

/**
 * @param {Element} el
 * @param {'ins'|'del'} type
 * @param {Map} metaMap
 * @param {object} opts
 * @returns {Element}
 */
function convertTipTapNodeToIce(el, type, metaMap, opts) {
  var cid =
    el.getAttribute(TIPTAP_ATTR.changeId) ||
    el.getAttribute(ICE_ATTR.cid) ||
    "";
  var cached = cid && metaMap ? metaMap.get(String(cid)) : null;

  var userid =
    el.getAttribute(TIPTAP_ATTR.authorId) ||
    el.getAttribute(ICE_ATTR.userid) ||
    (cached && cached.userid) ||
    (opts.defaultUser && opts.defaultUser.id) ||
    "";
  var username =
    el.getAttribute(TIPTAP_ATTR.authorName) ||
    el.getAttribute(ICE_ATTR.username) ||
    (cached && cached.username) ||
    (opts.defaultUser && opts.defaultUser.name) ||
    "";
  var time =
    el.getAttribute(TIPTAP_ATTR.timestamp) ||
    el.getAttribute(ICE_ATTR.time) ||
    (cached && cached.time) ||
    "";
  if (!time) {
    time = String(
      typeof opts.now === "number" ? opts.now : Date.now()
    );
  }
  var changedata =
    el.getAttribute(ICE_ATTR.changedata) ||
    (cached && cached.changedata) ||
    "";
  var ctsClass =
    findCtsClass(el) ||
    (cached && cached.ctsClass) ||
    opts.ctsClass ||
    "";
  var title =
    el.getAttribute("title") || (cached && cached.title) || "";

  if (!cid) {
    cid =
      "tt-" + String(Date.now()) + "-" + String(Math.floor(Math.random() * 1e6));
  }

  var tag = type === "ins" ? "ins" : "del";
  // Prefer semantic ins/del for CKEditor4 + ICE lite round-trip.
  var neu = document.createElement(tag);
  replaceKeepingChildren(el, neu);
  clearTrackAttrsAndClasses(neu);

  var iceClass = type === "ins" ? ICE_INS_CLASS : ICE_DEL_CLASS;
  var classes = [iceClass];
  if (ctsClass) classes.push(ctsClass);
  neu.setAttribute("class", classes.join(" "));

  neu.setAttribute(ICE_ATTR.cid, String(cid));
  if (userid !== "" && userid != null) {
    neu.setAttribute(ICE_ATTR.userid, String(userid));
  }
  if (username !== "" && username != null) {
    neu.setAttribute(ICE_ATTR.username, String(username));
  }
  if (time !== "" && time != null) {
    neu.setAttribute(ICE_ATTR.time, String(time));
  }
  if (changedata) {
    neu.setAttribute(ICE_ATTR.changedata, String(changedata));
  }
  if (title) {
    neu.setAttribute("title", title);
  }

  storeMeta(metaMap, {
    type: type,
    cid: String(cid),
    userid: String(userid || ""),
    username: String(username || ""),
    time: String(time || ""),
    changedata: String(changedata || ""),
    ctsClass: ctsClass || "",
    title: title || "",
    tag: tag,
  });

  return neu;
}

/**
 * TipTap track HTML → ICE lite (ins/del + ice-ins/ice-del + data-cid/…).
 *
 * @param {string} html
 * @param {{
 *   meta?: Map,
 *   defaultUser?: { id?: string, name?: string },
 *   now?: number,
 *   ctsClass?: string
 * }} [opts]
 * @returns {string}
 */
export function editorHtmlToIce(html, opts) {
  opts = opts || {};
  var raw = asString(html);
  if (!raw) return "";
  if (typeof document === "undefined") {
    throw new Error("editorHtmlToIce requires a DOM document");
  }

  var metaMap = ensureMetaMap(opts.meta);
  var root = document.createElement("div");
  root.innerHTML = raw;

  var els = Array.from(root.querySelectorAll("*"));
  var i;
  for (i = els.length - 1; i >= 0; i--) {
    var el = els[i];
    if (!el || !el.parentNode) continue;

    // Already ICE-shaped TipTap-less: leave alone (idempotent).
    if (
      (isIceInsert(el) || isIceDelete(el)) &&
      !isTipTapInsert(el) &&
      !isTipTapDelete(el)
    ) {
      continue;
    }

    if (isTipTapInsert(el) || (isIceInsert(el) && el.getAttribute(TIPTAP_ATTR.changeId))) {
      convertTipTapNodeToIce(el, "ins", metaMap, opts);
    } else if (
      isTipTapDelete(el) ||
      (isIceDelete(el) && el.getAttribute(TIPTAP_ATTR.changeId))
    ) {
      convertTipTapNodeToIce(el, "del", metaMap, opts);
    }
  }

  return root.innerHTML;
}

export default {
  ICE_INS_CLASS: ICE_INS_CLASS,
  ICE_DEL_CLASS: ICE_DEL_CLASS,
  ICE_ATTR: ICE_ATTR,
  TIPTAP_ATTR: TIPTAP_ATTR,
  isIceInsert: isIceInsert,
  isIceDelete: isIceDelete,
  isTipTapInsert: isTipTapInsert,
  isTipTapDelete: isTipTapDelete,
  iceHtmlToEditor: iceHtmlToEditor,
  editorHtmlToIce: editorHtmlToIce,
};
