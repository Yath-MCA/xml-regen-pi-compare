/**
 * TipTapManager
 * -------------
 * Single owner of TipTap HTML get/set for a module — mirrors SummernoteManager:
 *   - IMPACT ↔ editor TAG_MAP, format-id cache, transform/restore pipeline
 *   - getContent / setContent wrap editor.getHTML / setContent
 *   - regen-pi strip on load + regen on save
 *   - TrackChangesExtension wiring (peer: tiptap-track-changes)
 *   - ICE lite (CKEditor4+nytimes/ice) bridge via transform/iceBridge.js
 *
 * Formatting transform is HTML-skeleton (see transform/htmlSkeleton.js),
 * NOT custom TipTap FormattingHandler marks.
 *
 * One instance per editor-enabled module:
 *   this._tiptap = this._tiptap || new TipTapManager(this);
 *   const html = this._tiptap.getContent(editor);
 *
 * @module TipTapManager
 */

"use strict";

import { Mark, mergeAttributes } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { TrackChangesExtension } from "tiptap-track-changes";

import RegenPi, { stripPistart } from "../regen-pi.js";
import {
  TAG_MAP,
  DEFAULT_RESTORE,
  LIVE_CHECK,
  getEditorTagAllowed,
  transformToEditor,
  restoreFromEditor,
  unwrapParagraphs,
  reconcileAfterCommand,
  ensureBag,
} from "./transform/htmlSkeleton.js";
import {
  iceHtmlToEditor as bridgeIceHtmlToEditor,
  editorHtmlToIce as bridgeEditorHtmlToIce,
  ICE_ATTR,
  TIPTAP_ATTR,
  ICE_INS_CLASS,
  ICE_DEL_CLASS,
} from "./transform/iceBridge.js";

/**
 * Preserve data-format-id on a mark and optionally force the HTML tag.
 * Thin attribute passthrough — not a FormattingHandler redesign.
 *
 * @param {import('@tiptap/core').Mark} BaseMark
 * @param {object} opts
 * @param {string} [opts.tag] render/parse tag override (e.g. 'b', 'i')
 * @param {string[]} [opts.parseTags] extra parseHTML tags
 */
function withFormatIdAttr(BaseMark, opts) {
  opts = opts || {};
  return BaseMark.extend({
    addAttributes: function () {
      var parent =
        typeof this.parent === "function" ? this.parent() || {} : {};
      return Object.assign({}, parent, {
        "data-format-id": {
          default: null,
          parseHTML: function (element) {
            return element.getAttribute("data-format-id");
          },
          renderHTML: function (attributes) {
            if (!attributes["data-format-id"]) return {};
            return { "data-format-id": attributes["data-format-id"] };
          },
        },
      });
    },
    parseHTML: function () {
      var tags = opts.parseTags || (opts.tag ? [opts.tag] : null);
      if (tags) {
        return tags.map(function (tag) {
          return { tag: tag };
        });
      }
      return typeof this.parent === "function" ? this.parent() : [];
    },
    renderHTML: function (_ref) {
      var HTMLAttributes = _ref.HTMLAttributes;
      var tag = opts.tag;
      if (tag) {
        return [tag, mergeAttributes(HTMLAttributes), 0];
      }
      if (typeof this.parent === "function") {
        return this.parent.apply(this, arguments);
      }
      return ["span", mergeAttributes(HTMLAttributes), 0];
    },
  });
}

/**
 * Minimal marks for editor tags not in StarterKit (u, sup, sub, sc).
 * @param {string} name
 * @param {string} tag
 */
function createSimpleMark(name, tag) {
  return Mark.create({
    name: name,
    addAttributes: function () {
      return {
        "data-format-id": {
          default: null,
          parseHTML: function (element) {
            return element.getAttribute("data-format-id");
          },
          renderHTML: function (attributes) {
            if (!attributes["data-format-id"]) return {};
            return { "data-format-id": attributes["data-format-id"] };
          },
        },
      };
    },
    parseHTML: function () {
      return [{ tag: tag }];
    },
    renderHTML: function (_ref) {
      var HTMLAttributes = _ref.HTMLAttributes;
      return [tag, mergeAttributes(HTMLAttributes), 0];
    },
    addCommands: function () {
      var markName = name;
      var cap = markName.charAt(0).toUpperCase() + markName.slice(1);
      var cmds = {};
      cmds["toggle" + cap] = function () {
        return function (_ref) {
          var commands = _ref.commands;
          return commands.toggleMark(markName);
        };
      };
      return cmds;
    },
  });
}

export var UnderlineMark = createSimpleMark("underline", "u");
export var SuperscriptMark = createSimpleMark("superscript", "sup");
export var SubscriptMark = createSimpleMark("subscript", "sub");
export var SmallcapsMark = createSimpleMark("smallcaps", "sc");

/**
 * @typedef {object} TrackAuthor
 * @property {string} id
 * @property {string} name
 * @property {string} color
 */

class TipTapManager {
  /**
   * @param {object} [owner] host module (logError, _name, …)
   * @param {object} [options]
   * @param {TrackAuthor} [options.author]
   * @param {'edit'|'suggest'|'view'} [options.trackMode='suggest']
   */
  constructor(owner, options) {
    options = options || {};
    this.owner = owner || null;
    this._caches = typeof WeakMap !== "undefined" ? new WeakMap() : null;
    this._cacheFallback = { map: new Map(), seq: 0 };
    this._bypass = false;
    this._editor = null;

    this.author = options.author || {
      id: "user-1",
      name: "Editor",
      color: "#2d5fce",
    };
    this.trackMode = options.trackMode || "suggest";
    /** @type {Map<string, object>} ICE change meta keyed by cid / changeId */
    this._iceMeta = new Map();
    /** @type {boolean} when false, skip ICE ↔ TipTap bridge in get/set */
    this.iceBridge = options.iceBridge !== false;
  }

  // =========================================================================
  // Static config mirrors (delegate to htmlSkeleton)
  // =========================================================================

  static get TAG_MAP() {
    return TAG_MAP;
  }

  static get DEFAULT_RESTORE() {
    return DEFAULT_RESTORE;
  }

  static get EDITOR_TAG_ALLOWED() {
    return getEditorTagAllowed();
  }

  static get LIVE_CHECK() {
    return LIVE_CHECK;
  }

  // =========================================================================
  // Debug / errors
  // =========================================================================

  _ownerName() {
    return (this.owner && this.owner._name) || "unknown";
  }

  logError(context, err) {
    if (this.owner && typeof this.owner.logError === "function") {
      this.owner.logError(context, err);
    } else if (typeof console !== "undefined" && console.error) {
      console.error(
        "[TipTapManager:" + this._ownerName() + "] " + context,
        err
      );
    }
  }

  getDebugSnapshot() {
    var bag = this.ensureCache(this._editor);
    return {
      owner: this._ownerName(),
      hasEditor: !!this._editor,
      bypassActive: this._bypass,
      trackMode: this.trackMode,
      formatCacheSize: bag.map.size,
      formatCacheSeq: bag.seq,
      formatCacheEntries: Array.from(bag.map.entries()),
      iceBridge: this.iceBridge !== false,
      iceMetaSize: this._iceMeta ? this._iceMeta.size : 0,
    };
  }

  // =========================================================================
  // Cache
  // =========================================================================

  /**
   * @param {object} [editorOrKey] TipTap editor (WeakMap key) or null
   * @returns {{ map: Map, seq: number }}
   */
  ensureCache(editorOrKey) {
    var key = editorOrKey || null;
    if (!key) return this._cacheFallback;
    if (this._caches) {
      var bag = this._caches.get(key);
      if (!bag) {
        bag = { map: new Map(), seq: 0 };
        this._caches.set(key, bag);
      }
      return bag;
    }
    return this._cacheFallback;
  }

  resetCache(editorOrKey) {
    var bag = this.ensureCache(editorOrKey);
    bag.map.clear();
    bag.seq = 0;
    return bag;
  }

  // =========================================================================
  // Transform / restore (Summernote-equivalent names)
  // =========================================================================

  /**
   * IMPACT HTML → editor HTML (+ populate format cache).
   * @param {string} html
   * @param {{ map: Map, seq: number }} [cacheBag]
   * @returns {string}
   */
  transformForEditor(html, cacheBag) {
    try {
      return transformToEditor(html, cacheBag || this.ensureCache(this._editor));
    } catch (err) {
      this.logError("transformForEditor", err);
      return html == null ? "" : String(html);
    }
  }

  /**
   * Editor HTML → IMPACT HTML (restore cache + DEFAULT_RESTORE).
   * @param {string} html
   * @param {{ map: Map, seq: number }} [cacheBag]
   * @returns {string}
   */
  restoreFromEditor(html, cacheBag) {
    try {
      return restoreFromEditor(
        html,
        cacheBag || this.ensureCache(this._editor)
      );
    } catch (err) {
      this.logError("restoreFromEditor", err);
      return html == null ? "" : String(html);
    }
  }

  /** Alias matching htmlSkeleton export name. */
  transformToEditor(html, cacheBag) {
    return this.transformForEditor(html, cacheBag);
  }

  unwrapParagraphs(html) {
    return unwrapParagraphs(html);
  }

  reconcileAfterCommand(editableEl) {
    try {
      reconcileAfterCommand(editableEl);
    } catch (err) {
      this.logError("reconcileAfterCommand", err);
    }
  }

  withBypass(fn) {
    this._bypass = true;
    try {
      return fn();
    } finally {
      this._bypass = false;
    }
  }

  // =========================================================================
  // Bind editor + content API
  // =========================================================================

  /**
   * @param {import('@tiptap/core').Editor} editor
   * @returns {import('@tiptap/core').Editor}
   */
  bindEditor(editor) {
    this._editor = editor || null;
    return editor;
  }

  /**
   * Get IMPACT HTML from the live TipTap editor (restore + unwrap).
   * @param {import('@tiptap/core').Editor} [editor]
   * @returns {string}
   */
  getContent(editor) {
    var ed = editor || this._editor;
    if (!ed) return "";
    try {
      if (this._bypass) return ed.getHTML();
      var bag = this.ensureCache(ed);
      // Editor HTML → IMPACT formatting, then TipTap track marks → ICE lite.
      var restored = this.restoreFromEditor(ed.getHTML(), bag);
      if (this.iceBridge === false) return restored;
      return bridgeEditorHtmlToIce(restored, {
        meta: this._iceMeta,
        defaultUser: this.author,
      });
    } catch (err) {
      this.logError("getContent", err);
      return "";
    }
  }

  /**
   * Set IMPACT HTML into TipTap (strip pistart → transform → setContent).
   * @param {string} content IMPACT HTML (may contain <?pistart?>)
   * @param {import('@tiptap/core').Editor} [editor]
   * @param {object} [opts]
   * @param {boolean} [opts.stripPi=true]
   */
  setContent(content, editor, opts) {
    opts = opts || {};
    var ed = editor || this._editor;
    if (!ed) return;
    try {
      var raw = content == null ? "" : String(content);
      if (opts.stripPi !== false) {
        raw = stripPistart(raw);
      }
      if (this._bypass) {
        ed.commands.setContent(raw || "", false);
        return;
      }
      var bag = this.resetCache(ed);
      // ICE lite → TipTap track marks, then IMPACT → editor formatting.
      var useIce = opts.iceBridge !== false && this.iceBridge !== false;
      if (useIce) {
        if (opts.resetIceMeta !== false) {
          this._iceMeta = new Map();
        }
        raw = bridgeIceHtmlToEditor(raw, { meta: this._iceMeta });
      }
      var transformed = this.transformForEditor(raw, bag);
      ed.commands.setContent(transformed || "", false);
    } catch (err) {
      this.logError("setContent", err);
    }
  }

  clearContent(editor) {
    var ed = editor || this._editor;
    if (!ed) return;
    this.resetCache(ed);
    this.withBypass(function () {
      ed.commands.clearContent(false);
    });
  }

  // =========================================================================
  // regen-pi on save path
  // =========================================================================

  /**
   * Resolve RegenPi engine from opts / LOADING_CONFIG.
   * @param {object} [opts]
   * @returns {import('../regen-pi.js').default|null}
   */
  resolveRegenEngine(opts) {
    opts = opts || {};
    if (opts.regen === false) return null;
    if (opts.engine) return opts.engine;
    if (opts.xmlDoc) return RegenPi.fromXmlDoc(opts.xmlDoc);
    if (opts.clientConfig) {
      return RegenPi.fromClientConfig(opts.clientConfig, {
        fileName: opts.fileName,
        url: opts.url,
        key: opts.key,
      });
    }
    return RegenPi.fromClientConfig(null, {
      fileName: opts.fileName,
      url: opts.url,
      key: opts.key,
    });
  }

  /**
   * Editor → IMPACT HTML → strip → optional regen (pistart re-apply).
   * @param {import('@tiptap/core').Editor} [editor]
   * @param {object} [opts] see resolveRegenEngine
   * @returns {string}
   */
  getXml(editor, opts) {
    opts = opts || {};
    var impactHtml = this.getContent(editor);
    var stripXml = stripPistart(impactHtml);
    var engine = this.resolveRegenEngine(opts);
    if (!engine) return stripXml;
    return engine.regen(stripXml);
  }

  /**
   * Load XML/HTML into editor (strip pistart + transform).
   * @param {string} xml
   * @param {import('@tiptap/core').Editor} [editor]
   * @param {object} [opts]
   */
  setXml(xml, editor, opts) {
    this.setContent(xml, editor, opts);
  }


  // =========================================================================
  // ICE ↔ TipTap track bridge
  // =========================================================================

  /**
   * ICE lite HTML → TipTap track-changes HTML (does not touch IMPACT formatting).
   * @param {string} html
   * @param {{ meta?: Map }} [opts]
   * @returns {string}
   */
  iceHtmlToEditor(html, opts) {
    opts = opts || {};
    try {
      return bridgeIceHtmlToEditor(html, {
        meta: opts.meta || this._iceMeta,
      });
    } catch (err) {
      this.logError("iceHtmlToEditor", err);
      return html == null ? "" : String(html);
    }
  }

  /**
   * TipTap track-changes HTML → ICE lite (ins/del + ice-ins/ice-del + data-*).
   * @param {string} html
   * @param {object} [opts]
   * @returns {string}
   */
  editorHtmlToIce(html, opts) {
    opts = opts || {};
    try {
      return bridgeEditorHtmlToIce(
        html,
        Object.assign(
          {
            meta: this._iceMeta,
            defaultUser: this.author,
          },
          opts
        )
      );
    } catch (err) {
      this.logError("editorHtmlToIce", err);
      return html == null ? "" : String(html);
    }
  }

  /** Snapshot of cached ICE change metadata (cid → meta). */
  getIceMetaSnapshot() {
    return Array.from(this._iceMeta.entries());
  }

  resetIceMeta() {
    this._iceMeta = new Map();
    return this._iceMeta;
  }
  // =========================================================================
  // Extensions (StarterKit + format-id marks + TrackChanges)
  // =========================================================================

  /**
   * Build TipTap extension list for contrib editing.
   * @param {object} [overrides]
   * @param {TrackAuthor} [overrides.author]
   * @param {'edit'|'suggest'|'view'} [overrides.trackMode]
   * @param {function} [overrides.onStatusChange]
   * @param {Array} [overrides.extraExtensions]
   * @returns {Array}
   */
  buildExtensions(overrides) {
    overrides = overrides || {};
    var author = overrides.author || this.author;
    var mode = overrides.trackMode || this.trackMode;

    // StarterKit with bold/italic/strike off — replaced by b/i/s marks that
    // preserve data-format-id and match Summernote editor tags.
    // Keep paragraph — TipTap needs a block; unwrapParagraphs on restore.
    var starterNoMarks = StarterKit.configure({
      heading: false,
      blockquote: false,
      codeBlock: false,
      horizontalRule: false,
      bold: false,
      italic: false,
      strike: false,
    });

    // Import Bold/Italic from starter-kit internals via Mark + known tags.
    // Use lightweight marks that match Summernote editor tags (b/i).
    var BoldMark = withFormatIdAttr(
      Mark.create({
        name: "bold",
        parseHTML: function () {
          return [{ tag: "strong" }, { tag: "b" }];
        },
        renderHTML: function (_ref) {
          var HTMLAttributes = _ref.HTMLAttributes;
          return ["b", mergeAttributes(HTMLAttributes), 0];
        },
        addCommands: function () {
          return {
            toggleBold: function () {
              return function (_ref) {
                var commands = _ref.commands;
                return commands.toggleMark("bold");
              };
            },
          };
        },
      }),
      { tag: "b", parseTags: ["b", "strong"] }
    );

    var ItalicMark = withFormatIdAttr(
      Mark.create({
        name: "italic",
        parseHTML: function () {
          return [{ tag: "em" }, { tag: "i" }];
        },
        renderHTML: function (_ref) {
          var HTMLAttributes = _ref.HTMLAttributes;
          return ["i", mergeAttributes(HTMLAttributes), 0];
        },
        addCommands: function () {
          return {
            toggleItalic: function () {
              return function (_ref) {
                var commands = _ref.commands;
                return commands.toggleMark("italic");
              };
            },
          };
        },
      }),
      { tag: "i", parseTags: ["i", "em"] }
    );

    var StrikeMark = withFormatIdAttr(
      Mark.create({
        name: "strike",
        parseHTML: function () {
          return [
            { tag: "s" },
            {
              tag: "del",
              getAttrs: function (node) {
                var el = node;
                if (!el || !el.getAttribute) return false;
                // TipTap track-changes / ICE lite own <del> — do not treat as strike.
                if (el.getAttribute("data-change-id") || el.getAttribute("data-cid")) {
                  return false;
                }
                var cls = (el.getAttribute("class") || "").toLowerCase();
                if (
                  cls.indexOf("ice-del") !== -1 ||
                  cls.indexOf("ice-ins") !== -1
                ) {
                  return false;
                }
                return null;
              },
            },
            { tag: "strike" },
          ];
        },
        renderHTML: function (_ref) {
          var HTMLAttributes = _ref.HTMLAttributes;
          return ["s", mergeAttributes(HTMLAttributes), 0];
        },
        addCommands: function () {
          return {
            toggleStrike: function () {
              return function (_ref) {
                var commands = _ref.commands;
                return commands.toggleMark("strike");
              };
            },
          };
        },
      }),
      { tag: "s", parseTags: ["s", "del", "strike"] }
    );


    var track = TrackChangesExtension.configure({
      author: author,
      mode: mode,
      onStatusChange: overrides.onStatusChange,
    });

    var list = [
      starterNoMarks,
      BoldMark,
      ItalicMark,
      StrikeMark,
      UnderlineMark,
      SuperscriptMark,
      SubscriptMark,
      SmallcapsMark,
      track,
    ];

    if (overrides.extraExtensions && overrides.extraExtensions.length) {
      list = list.concat(overrides.extraExtensions);
    }
    return list;
  }

  /**
   * Static helper — build extensions without an instance.
   * @param {object} [options]
   * @returns {Array}
   */
  static buildExtensions(options) {
    return new TipTapManager(null, options).buildExtensions(options);
  }
}

export { TipTapManager };
export default TipTapManager;

