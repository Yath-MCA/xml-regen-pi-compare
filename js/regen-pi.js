/**
 * regen-pi.js — ES2016 class module for contrib-group PI regeneration.
 *
 * Ported from contrib_script/regen_compare_v1.py (given-names, between-xrefs,
 * between-contribs). Canonical config is Option B:
 *
 *   <separator classname="given-names" value="..." pos="inner"/>
 *
 * Legacy tag-as-kind (<given-names .../>) is accepted and mapped to classname.
 * Missing/blank classname on <separator> is rejected.
 *
 * Browser: prefer the live journal config Document already on
 * LOADING_CONFIG.CLIENT_CONFIG[...].XML_DOC (no re-fetch). Fallbacks:
 * RegenPi.fromXmlDoc(doc), parsePiConfigXml + DOMParser for string XML.
 * Node/Vite tests can polyfill DOMParser (linkedom / jsdom) when using strings.
 *
 * @module regen-pi
 */

"use strict";

// ---------------------------------------------------------------------------
// Errors / model
// ---------------------------------------------------------------------------

export class RegenPiError extends Error {
  constructor(message) {
    super(message);
    this.name = "RegenPiError";
  }
}

/**
 * @param {string} classname required non-blank slot name
 * @param {object} [opts]
 * @param {string} [opts.pos="after"]
 * @param {string|null} [opts.contribs]
 * @param {string|null} [opts.when]
 */
export class RegenPiSelector {
  constructor(classname, opts) {
    opts = opts || {};
    var cn = classname == null ? "" : String(classname).trim();
    if (!cn) {
      throw new RegenPiError(
        'classname is required and must be non-blank ' +
          '(Option B: <separator classname="..." .../>)'
      );
    }
    this.classname = cn;
    this.pos =
      ((opts.pos == null ? "after" : String(opts.pos)).trim().toLowerCase()) ||
      "after";
    var contribs = opts.contribs;
    this.contribs =
      contribs == null || String(contribs).trim() === ""
        ? null
        : String(contribs);
    var when = opts.when;
    this.when =
      when == null || String(when).trim() === "" ? null : String(when);
  }
}

/**
 * @param {RegenPiSelector} selector
 * @param {string} value unescaped PI text
 */
export class RegenPiRule {
  constructor(selector, value) {
    if (!(selector instanceof RegenPiSelector)) {
      throw new RegenPiError("RegenPiRule requires a RegenPiSelector");
    }
    this.selector = selector;
    this.value = value == null ? "" : String(value);
  }

  get classname() {
    return this.selector.classname;
  }
  get kind() {
    return this.selector.classname;
  }
  get pos() {
    return this.selector.pos;
  }
  get contribs() {
    return this.selector.contribs;
  }
  get when() {
    return this.selector.when;
  }

  /**
   * @param {object} flat
   * @param {string} flat.classname
   * @param {string} [flat.value]
   * @param {string} [flat.pos]
   * @param {string|null} [flat.contribs]
   * @param {string|null} [flat.when]
   */
  static fromFlat(flat) {
    flat = flat || {};
    return new RegenPiRule(
      new RegenPiSelector(flat.classname, {
        pos: flat.pos,
        contribs: flat.contribs,
        when: flat.when,
      }),
      flat.value
    );
  }
}

/**
 * Parsed pi-config for one client/shortcode.
 */
export class RegenPiConfig {
  /**
   * @param {object} init
   */
  constructor(init) {
    init = init || {};
    this.client = init.client || "";
    this.shortcode = init.shortcode || "";
    this.dtd = init.dtd || "";
    this.version = init.version || "";
    this.status = init.status || "";
    this.elements = init.elements || {};
    this.ques = init.ques || {};
    this.rules = Array.isArray(init.rules) ? init.rules.slice() : [];
  }

  /** @returns {RegenPiRule[]} */
  get separators() {
    return this.rules;
  }

  /**
   * @param {string} classname
   * @returns {RegenPiRule[]}
   */
  select(classname) {
    var cn = classname == null ? "" : String(classname).trim();
    if (!cn) {
      throw new RegenPiError("select() requires a non-blank classname");
    }
    return this.rules.filter(function (r) {
      return r.classname === cn;
    });
  }

  /** Alias used by older Python callers. */
  separatorsOf(kind) {
    return this.select(kind);
  }
}

// ---------------------------------------------------------------------------
// PI helpers (mirror regen_compare_v1.esc_for_pi / pi_tag)
// ---------------------------------------------------------------------------

var PI_RE = /<\?pistart\b[^>]*\?>/g;
var CONTRIB_RE = /<contrib\b[^>]*>[\s\S]*?<\/contrib>/gi;
var XREF_RE = /<xref\b[^>]*\/>|<xref\b[^>]*>[\s\S]*?<\/xref>/gi;
var GIVEN_EMPTY_RE = /<given-names(\s[^>]*)?\s*\/>/gi;

/**
 * @param {string} value
 * @returns {string}
 */
export function formatPiAttrValue(value) {
  var v = value == null ? "" : String(value);
  if (v === "\u00a0") {
    return "&#x00A0;";
  }
  return v
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;");
}

/**
 * Build <?pistart xml:space="..."?> matching extractor / regen_compare conventions.
 * @param {string} value
 * @returns {string}
 */
export function makePistart(value) {
  return '<?pistart xml:space="' + formatPiAttrValue(value) + '"?>';
}

/**
 * Strip only pistart PIs (Phase 1 of regen_compare_v1).
 * @param {string} text
 * @returns {string}
 */
export function stripPistart(text) {
  return String(text || "").replace(PI_RE, "");
}

function unescapeXmlEntities(raw) {
  if (raw == null) return "";
  var s = String(raw);
  if (typeof DOMParser !== "undefined") {
    try {
      var doc = new DOMParser().parseFromString(
        "<!DOCTYPE x><t>" + s + "</t>",
        "text/xml"
      );
      var t = doc.getElementsByTagName("t")[0];
      if (t && t.textContent != null) return t.textContent;
    } catch (e) {
      /* fall through */
    }
  }
  return s
    .replace(/&#x00A0;/gi, "\u00a0")
    .replace(/&#160;/g, "\u00a0")
    .replace(/&nbsp;/gi, "\u00a0")
    .replace(/&quot;/g, '"')
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&");
}

function allowedFlag(raw) {
  var v = (raw == null ? "" : String(raw)).trim().toLowerCase();
  return v === "yes" || v === "true" || v === "1";
}

// ---------------------------------------------------------------------------
// Config parse (Option B + legacy)
// ---------------------------------------------------------------------------

/**
 * Resolve pi-config root element from a live DOM Document (or DocumentFragment /
 * Element). Prefer this over re-parsing strings when the web app already loaded
 * the journal split config into XML_DOC.
 * @param {Document|Element} docOrRoot
 * @returns {Element} <pi-config> element
 */
export function resolvePiConfigRoot(docOrRoot) {
  if (docOrRoot == null) {
    throw new RegenPiError(
      "resolvePiConfigRoot: Document / XML_DOC is null or undefined"
    );
  }
  var node = docOrRoot;
  // Document or DocumentFragment
  if (node.nodeType === 9 || node.nodeType === 11) {
    var fromDoc = node.getElementsByTagName
      ? node.getElementsByTagName("pi-config")[0]
      : null;
    if (!fromDoc && node.documentElement && localName(node.documentElement) === "pi-config") {
      fromDoc = node.documentElement;
    }
    if (!fromDoc) {
      throw new RegenPiError("expected <pi-config> root in XML_DOC Document");
    }
    return fromDoc;
  }
  // Element
  if (node.nodeType === 1) {
    if (localName(node) === "pi-config") return node;
    var nested = node.getElementsByTagName
      ? node.getElementsByTagName("pi-config")[0]
      : null;
    if (nested) return nested;
    throw new RegenPiError("expected <pi-config> element");
  }
  throw new RegenPiError(
    "resolvePiConfigRoot: expected Document or Element, got nodeType=" +
      node.nodeType
  );
}

/**
 * Build RegenPiConfig from an already-parsed <pi-config> root Element.
 * @param {Element} root
 * @returns {RegenPiConfig}
 */
export function configFromPiConfigElement(root) {
  if (!root || root.nodeType !== 1 || localName(root) !== "pi-config") {
    throw new RegenPiError("configFromPiConfigElement expects a <pi-config> Element");
  }
  var cfg = new RegenPiConfig({
    client: root.getAttribute("client") || "",
    shortcode: root.getAttribute("shortcode") || "",
    dtd: root.getAttribute("dtd") || "",
    version: root.getAttribute("version") || "",
    status: root.getAttribute("status") || "",
  });

  var contrib = firstChildByLocalName(root, "contrib");
  if (!contrib) return cfg;

  var elems = firstChildByLocalName(contrib, "elements");
  if (elems) {
    forEachElementChild(elems, function (child) {
      cfg.elements[localName(child)] = allowedFlag(child.getAttribute("allowed"));
    });
  }
  var ques = firstChildByLocalName(contrib, "ques");
  if (ques) {
    forEachElementChild(ques, function (child) {
      cfg.ques[localName(child)] = allowedFlag(child.getAttribute("allowed"));
    });
  }
  var seps = firstChildByLocalName(contrib, "separators");
  if (seps) {
    forEachElementChild(seps, function (child) {
      cfg.rules.push(parseSeparatorChild(child));
    });
  }
  return cfg;
}

/**
 * Parse pi-config from a live DOM Document (web-app XML_DOC pattern).
 * Does not re-fetch or re-parse string XML.
 * @param {Document|Element} xmlDoc
 * @returns {RegenPiConfig}
 */
export function parsePiConfigDoc(xmlDoc) {
  return configFromPiConfigElement(resolvePiConfigRoot(xmlDoc));
}

/**
 * Pick a CLIENT_CONFIG entry object from LOADING_CONFIG.CLIENT_CONFIG.
 * Accepts the map itself, or a single entry already resolved.
 *
 * Entry shape (web app):
 *   { FILE_NAME, IGNORE_TRACK, IS_LOADED, ORDER, SEPARATE_FILE, TYPE, URL, XML_DOC }
 *
 * @param {object} clientConfigMapOrEntry LOADING_CONFIG.CLIENT_CONFIG or one entry
 * @param {object} [opts]
 * @param {string} [opts.fileName] match FILE_NAME (e.g. "MD.xml")
 * @param {string} [opts.url] match URL substring / exact
 * @param {string} [opts.key] exact object key if map is keyed that way
 * @returns {object} single CLIENT_CONFIG entry
 */
export function resolveClientConfigEntry(clientConfigMapOrEntry, opts) {
  opts = opts || {};
  if (clientConfigMapOrEntry == null || typeof clientConfigMapOrEntry !== "object") {
    throw new RegenPiError(
      "resolveClientConfigEntry: CLIENT_CONFIG is missing or not an object " +
        "(expected LOADING_CONFIG.CLIENT_CONFIG)"
    );
  }
  // Already a single entry with XML_DOC / IS_LOADED fields
  if (
    Object.prototype.hasOwnProperty.call(clientConfigMapOrEntry, "XML_DOC") ||
    Object.prototype.hasOwnProperty.call(clientConfigMapOrEntry, "IS_LOADED") ||
    Object.prototype.hasOwnProperty.call(clientConfigMapOrEntry, "FILE_NAME")
  ) {
    return clientConfigMapOrEntry;
  }

  var map = clientConfigMapOrEntry;
  var key = opts.key;
  if (key != null && key !== "") {
    if (!Object.prototype.hasOwnProperty.call(map, key)) {
      throw new RegenPiError(
        'resolveClientConfigEntry: no CLIENT_CONFIG entry for key "' + key + '"'
      );
    }
    return map[key];
  }

  var fileName = opts.fileName != null ? String(opts.fileName) : "";
  var urlOpt = opts.url != null ? String(opts.url) : "";
  var keys = Object.keys(map);
  var matches = [];
  for (var i = 0; i < keys.length; i++) {
    var entry = map[keys[i]];
    if (!entry || typeof entry !== "object") continue;
    if (fileName && String(entry.FILE_NAME || "") === fileName) {
      matches.push(entry);
      continue;
    }
    if (urlOpt) {
      var u = String(entry.URL || "");
      if (u === urlOpt || u.indexOf(urlOpt) !== -1) matches.push(entry);
    }
  }
  if (!fileName && !urlOpt) {
    // If exactly one entry, use it; else require a selector.
    if (keys.length === 1 && map[keys[0]] && typeof map[keys[0]] === "object") {
      return map[keys[0]];
    }
    throw new RegenPiError(
      "resolveClientConfigEntry: pass opts.fileName, opts.url, or opts.key " +
        "when CLIENT_CONFIG has multiple entries (count=" +
        keys.length +
        ")"
    );
  }
  if (matches.length === 0) {
    throw new RegenPiError(
      "resolveClientConfigEntry: no CLIENT_CONFIG entry matched " +
        (fileName ? 'FILE_NAME="' + fileName + '"' : 'URL~"' + urlOpt + '"')
    );
  }
  if (matches.length > 1) {
    throw new RegenPiError(
      "resolveClientConfigEntry: multiple CLIENT_CONFIG entries matched; " +
        "narrow with opts.key or a more specific opts.url"
    );
  }
  return matches[0];
}

/**
 * Build RegenPiConfig from a web-app CLIENT_CONFIG entry (or the whole map + opts).
 * Safety checks: entry present, IS_LOADED truthy, XML_DOC non-null Document.
 *
 * @param {object} clientConfigMapOrEntry
 * @param {object} [opts] see resolveClientConfigEntry
 * @returns {RegenPiConfig}
 */
export function parsePiConfigFromClientConfig(clientConfigMapOrEntry, opts) {
  var entry = resolveClientConfigEntry(clientConfigMapOrEntry, opts);
  if (!entry.IS_LOADED) {
    throw new RegenPiError(
      "CLIENT_CONFIG entry IS_LOADED is false " +
        '(FILE_NAME="' +
        (entry.FILE_NAME || "") +
        '"; load journal config before regen-pi)'
    );
  }
  if (entry.XML_DOC == null) {
    throw new RegenPiError(
      "CLIENT_CONFIG entry XML_DOC is null " +
        '(FILE_NAME="' +
        (entry.FILE_NAME || "") +
        '"; expected live DOM Document)'
    );
  }
  return parsePiConfigDoc(entry.XML_DOC);
}

/**
 * Read LOADING_CONFIG.CLIENT_CONFIG from globalThis / window when present.
 * @returns {object}
 */
export function getLoadingClientConfig() {
  var g =
    typeof globalThis !== "undefined"
      ? globalThis
      : typeof window !== "undefined"
        ? window
        : null;
  if (!g || g.LOADING_CONFIG == null) {
    throw new RegenPiError(
      "LOADING_CONFIG global is missing; pass CLIENT_CONFIG explicitly to " +
        "RegenPi.fromClientConfig(clientConfig, opts) or use fromXmlDoc(XML_DOC)"
    );
  }
  var cc = g.LOADING_CONFIG.CLIENT_CONFIG;
  if (cc == null || typeof cc !== "object") {
    throw new RegenPiError(
      "LOADING_CONFIG.CLIENT_CONFIG is missing or not an object"
    );
  }
  return cc;
}

/**
 * Parse a <pi-config> XML string into RegenPiConfig.
 * Requires DOMParser (browser native, or polyfill under Node).
 * Prefer parsePiConfigDoc / fromClientConfig when XML_DOC already exists.
 * @param {string} xmlText
 * @returns {RegenPiConfig}
 */
export function parsePiConfigXml(xmlText) {
  if (typeof DOMParser === "undefined") {
    throw new RegenPiError(
      "parsePiConfigXml requires DOMParser (browser or polyfill)"
    );
  }
  var doc = new DOMParser().parseFromString(String(xmlText || ""), "text/xml");
  var parseErr = doc.getElementsByTagName("parsererror")[0];
  if (parseErr) {
    throw new RegenPiError(
      "Invalid pi-config XML: " + (parseErr.textContent || "parse error")
    );
  }
  return parsePiConfigDoc(doc);
}

function localName(el) {
  if (!el) return "";
  if (el.localName) return el.localName;
  var t = el.tagName || "";
  var i = t.indexOf(":");
  return i >= 0 ? t.slice(i + 1) : t;
}

function firstChildByLocalName(parent, name) {
  var kids = parent.childNodes;
  for (var i = 0; i < kids.length; i++) {
    var n = kids[i];
    if (n.nodeType === 1 && localName(n) === name) return n;
  }
  return null;
}

function forEachElementChild(parent, fn) {
  var kids = parent.childNodes;
  for (var i = 0; i < kids.length; i++) {
    if (kids[i].nodeType === 1) fn(kids[i]);
  }
}

function parseSeparatorChild(child) {
  var tag = localName(child);
  var rawVal = child.getAttribute("value");
  if (rawVal == null) rawVal = "";
  var whenRaw = child.getAttribute("when");
  var pos = child.getAttribute("pos") || "after";
  var contribs = child.getAttribute("contribs");
  var classname;

  if (tag === "separator") {
    classname = child.getAttribute("classname");
    if (classname == null || !String(classname).trim()) {
      throw new RegenPiError(
        '<separator> requires a non-blank classname attribute ' +
          '(Option B: <separator classname="..." value="..."/>)'
      );
    }
    classname = String(classname).trim();
  } else {
    // Legacy tag-as-kind
    classname = tag;
  }

  return RegenPiRule.fromFlat({
    classname: classname,
    value: unescapeXmlEntities(rawVal),
    pos: pos,
    contribs: contribs,
    when: whenRaw,
  });
}

// ---------------------------------------------------------------------------
// Role / between-contribs (mirror regen_compare_v1 + optional contribs=)
// ---------------------------------------------------------------------------

/**
 * @param {number} i 0-based index
 * @param {number} n total contribs
 * @returns {string} first | last-before | last | other
 */
export function roleOf(i, n) {
  if (i === n - 1) return "last";
  if (i === n - 2) return "last-before";
  if (i === 0) return "first";
  return "other";
}

function contribsMatch(ruleContribs, n) {
  if (ruleContribs == null || ruleContribs === "") return true;
  var rc = String(ruleContribs).trim();
  if (rc.charAt(rc.length - 1) === "+") {
    var min = parseInt(rc.slice(0, -1), 10);
    if (isNaN(min)) return false;
    return n >= min;
  }
  var exact = parseInt(rc, 10);
  if (isNaN(exact)) return false;
  return n === exact;
}

/**
 * Pick between-contribs rule for contrib at index (0-based) among n.
 * @param {RegenPiRule[]} rules
 * @param {number} index
 * @param {number} n
 * @returns {RegenPiRule|null}
 */
export function pickBetweenContribsRule(rules, index, n) {
  if (n <= 0 || !rules || !rules.length) return null;
  var role = roleOf(index, n);
  var i;
  var r;

  if (role === "last") {
    for (i = 0; i < rules.length; i++) {
      r = rules[i];
      if (r.when === "last" && contribsMatch(r.contribs, n)) return r;
    }
    // Reference: no PI for last unless explicitly configured.
    return null;
  }

  if (role === "last-before") {
    for (i = 0; i < rules.length; i++) {
      r = rules[i];
      if (r.when === "last-before" && contribsMatch(r.contribs, n)) return r;
    }
  }

  if (role !== "last") {
    for (i = 0; i < rules.length; i++) {
      r = rules[i];
      if (!r.when && contribsMatch(r.contribs, n)) return r;
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// Insert helpers
// ---------------------------------------------------------------------------

function insertGivenNamesPis(text, rule) {
  if (!rule || rule.pos !== "inner") return text;
  var pi = makePistart(rule.value);
  // Expand self-closing to empty element first; one pass then inserts a
  // single PI before every </given-names> (avoids double PI on empties).
  var out = String(text).replace(GIVEN_EMPTY_RE, function (_m, attrs) {
    return "<given-names" + (attrs || "") + "></given-names>";
  });
  out = out.replace(/<\/given-names>/gi, pi + "</given-names>");
  return out;
}

function insertXrefPis(contribXml, rule) {
  if (!rule) return contribXml;
  if (rule.pos && rule.pos !== "after") return contribXml;
  var matches = [];
  var re = new RegExp(XREF_RE.source, "gi");
  var m;
  while ((m = re.exec(contribXml)) !== null) {
    matches.push({ end: m.index + m[0].length });
  }
  if (matches.length < 2) return contribXml;
  var pi = makePistart(rule.value);
  var parts = [];
  var last = 0;
  for (var i = 0; i < matches.length; i++) {
    parts.push(contribXml.slice(last, matches[i].end));
    if (i < matches.length - 1) parts.push(pi);
    last = matches[i].end;
  }
  parts.push(contribXml.slice(last));
  return parts.join("");
}

function insertBetweenContribs(text, rules) {
  var matches = [];
  var re = new RegExp(CONTRIB_RE.source, "gi");
  var m;
  while ((m = re.exec(text)) !== null) {
    matches.push({
      start: m.index,
      end: m.index + m[0].length,
      text: m[0],
    });
  }
  var n = matches.length;
  if (n === 0 || !rules || !rules.length) return text;

  // Reference inserts PI as last child before </contrib>.
  var out = text;
  for (var i = n - 1; i >= 0; i--) {
    var rule = pickBetweenContribsRule(rules, i, n);
    if (!rule) continue;
    var pi = makePistart(rule.value);
    var block = matches[i].text;
    var replaced = block.replace(/<\/contrib>\s*$/i, pi + "</contrib>");
    out = out.slice(0, matches[i].start) + replaced + out.slice(matches[i].end);
  }
  return out;
}

// ---------------------------------------------------------------------------
// RegenPi facade
// ---------------------------------------------------------------------------

/**
 * Load pi-config and regenerate separator PIs into strip_xml.
 *
 * Focus slots (regen_compare_v1 Phase 2 subset):
 *   - given-names (pos=inner)
 *   - between-xrefs (pos=after, between non-last xrefs)
 *   - between-contribs (role / when + optional contribs filter)
 */
export class RegenPi {
  /**
   * @param {RegenPiConfig} config
   */
  constructor(config) {
    if (!(config instanceof RegenPiConfig)) {
      throw new RegenPiError("RegenPi requires a RegenPiConfig");
    }
    this.config = config;
  }

  /**
   * Preferred in the web app: build from a live XML Document (CLIENT_CONFIG.XML_DOC).
   * @param {Document|Element} xmlDoc
   * @returns {RegenPi}
   */
  static fromXmlDoc(xmlDoc) {
    return new RegenPi(parsePiConfigDoc(xmlDoc));
  }

  /**
   * Preferred in the web app: LOADING_CONFIG.CLIENT_CONFIG entry or map.
   * If clientConfigMapOrEntry is omitted, reads global LOADING_CONFIG.CLIENT_CONFIG.
   * @param {object} [clientConfigMapOrEntry]
   * @param {object} [opts] fileName / url / key selectors when map has many entries
   * @returns {RegenPi}
   */
  static fromClientConfig(clientConfigMapOrEntry, opts) {
    var src =
      clientConfigMapOrEntry == null
        ? getLoadingClientConfig()
        : clientConfigMapOrEntry;
    return new RegenPi(parsePiConfigFromClientConfig(src, opts));
  }

  /**
   * Parse from an XML string (needs DOMParser). Prefer fromXmlDoc / fromClientConfig
   * when the journal config Document is already loaded.
   * @param {string} xmlText
   * @returns {RegenPi}
   */
  static fromXml(xmlText) {
    return new RegenPi(parsePiConfigXml(xmlText));
  }

  /**
   * @param {RegenPiConfig} config
   * @returns {RegenPi}
   */
  static fromConfig(config) {
    return new RegenPi(config);
  }

  /**
   * @param {string} classname
   * @returns {RegenPiRule[]}
   */
  select(classname) {
    return this.config.select(classname);
  }

  /**
   * Rebuild contrib-group XML from strip_pi by inserting separator PIs.
   * @param {string} stripXml
   * @returns {string}
   */
  regen(stripXml) {
    var text = String(stripXml == null ? "" : stripXml);
    var cfg = this.config;

    var gn = cfg.select("given-names");
    if (gn.length) {
      text = insertGivenNamesPis(text, gn[0]);
    }

    var xref = cfg.select("between-xrefs");
    if (xref.length) {
      var rule = xref[0];
      text = text.replace(new RegExp(CONTRIB_RE.source, "gi"), function (block) {
        return insertXrefPis(block, rule);
      });
    }

    var bc = cfg.select("between-contribs");
    if (bc.length) {
      text = insertBetweenContribs(text, bc);
    }

    return text;
  }

  /**
   * @param {string} value
   * @returns {string}
   */
  static makePistart(value) {
    return makePistart(value);
  }
}

export default RegenPi;
