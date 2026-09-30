/**
 * ContribEditor.jsx — TipTap React editor with Summernote-style HTML skeleton
 * transform (via TipTapManager) and track changes (tiptap-track-changes).
 *
 * Load:  IMPACT HTML → stripPistart → transformForEditor → setContent
 * Save:  getHTML → restoreFromEditor → regen-pi.regen (pistart re-apply)
 *
 * Peer imports: @tiptap/react, @tiptap/starter-kit, @tiptap/core,
 *               tiptap-track-changes, react
 *
 * @module ContribEditor
 */

import React, { useCallback, useEffect, useMemo, useRef } from "react";
import { useEditor, EditorContent } from "@tiptap/react";

import TipTapManager from "./TipTapManager.js";

/**
 * @typedef {object} TrackAuthor
 * @property {string} id
 * @property {string} name
 * @property {string} color
 */

/**
 * @typedef {object} ContribEditorProps
 * @property {string} [xml] initial IMPACT HTML / contrib XML (pistart stripped on load)
 * @property {string} [content] raw editor HTML (skips IMPACT transform when set with bypass)
 * @property {boolean} [editable=true]
 * @property {boolean} [showToolbar=true]
 * @property {string} [className]
 * @property {TrackAuthor} [author] track-changes author
 * @property {'edit'|'suggest'|'view'} [trackMode='suggest']
 * @property {(json: object) => void} [onUpdate]
 * @property {(xml: string) => void} [onXmlChange]
 * @property {object} [regenOpts] passed to TipTapManager.getXml
 * @property {boolean} [autoExportXml=false]
 * @property {(changeId: string, status: string) => void} [onTrackStatusChange]
 */

/**
 * Main TipTap React editor for contrib / IMPACT HTML content.
 * @param {ContribEditorProps} props
 */
export function ContribEditor(props) {
  var xml = props.xml;
  var contentProp = props.content;
  var editable = props.editable !== false;
  var showToolbar = props.showToolbar !== false;
  var className = props.className || "contrib-editor";
  var onUpdate = props.onUpdate;
  var onXmlChange = props.onXmlChange;
  var regenOpts = props.regenOpts;
  var autoExportXml = !!props.autoExportXml;
  var author = props.author;
  var trackMode = props.trackMode || "suggest";
  var onTrackStatusChange = props.onTrackStatusChange;

  var managerRef = useRef(null);
  if (!managerRef.current) {
    managerRef.current = new TipTapManager(null, {
      author: author,
      trackMode: trackMode,
    });
  }
  var manager = managerRef.current;

  var extensions = useMemo(
    function () {
      return manager.buildExtensions({
        author: author,
        trackMode: trackMode,
        onStatusChange: onTrackStatusChange,
      });
    },
    [manager, author, trackMode, onTrackStatusChange]
  );

  var handleUpdate = useCallback(
    function (_ref) {
      var editor = _ref.editor;
      if (!editor) return;
      var json = editor.getJSON();
      if (typeof onUpdate === "function") onUpdate(json);
      if (autoExportXml && typeof onXmlChange === "function") {
        try {
          onXmlChange(manager.getXml(editor, regenOpts || {}));
        } catch (err) {
          if (typeof console !== "undefined" && console.warn) {
            console.warn("[ContribEditor] getXml/regen failed:", err);
          }
        }
      }
    },
    [onUpdate, onXmlChange, autoExportXml, regenOpts, manager]
  );

  var editor = useEditor({
    extensions: extensions,
    content: "",
    editable: editable,
    onUpdate: handleUpdate,
  });

  // Bind manager ↔ editor; seed content once editor is ready.
  useEffect(
    function () {
      if (!editor) return;
      manager.bindEditor(editor);
      if (contentProp != null && contentProp !== "") {
        manager.withBypass(function () {
          editor.commands.setContent(contentProp, false);
        });
      } else if (xml != null) {
        manager.setXml(xml, editor);
      } else {
        manager.setXml("", editor);
      }
    },
    // Seed on mount / editor create only; xml prop reload handled below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [editor]
  );

  useEffect(
    function () {
      if (editor) editor.setEditable(editable);
    },
    [editor, editable]
  );

  // Reload from xml prop when parent passes new IMPACT HTML.
  useEffect(
    function () {
      if (!editor || contentProp != null) return;
      if (xml == null) return;
      manager.setXml(xml, editor);
    },
    [editor, xml, contentProp, manager]
  );

  var setXml = useCallback(
    function (nextXml) {
      if (!editor) return;
      manager.setXml(nextXml || "", editor);
    },
    [editor, manager]
  );

  var getXml = useCallback(
    function (opts) {
      if (!editor) return "";
      return manager.getXml(editor, Object.assign({}, regenOpts || {}, opts || {}));
    },
    [editor, manager, regenOpts]
  );

  var getHTML = useCallback(
    function () {
      return manager.getContent(editor);
    },
    [editor, manager]
  );

  var getJSON = useCallback(
    function () {
      return editor ? editor.getJSON() : null;
    },
    [editor]
  );

  useEffect(
    function () {
      if (!editor) return;
      editor.contrib = {
        manager: manager,
        setXml: setXml,
        getXml: getXml,
        getHTML: getHTML,
        getJSON: getJSON,
        setSuggestMode: function () {
          return editor.commands.setSuggestMode();
        },
        setEditMode: function () {
          return editor.commands.setEditMode();
        },
        acceptAll: function () {
          return editor.commands.acceptAll();
        },
        rejectAll: function () {
          return editor.commands.rejectAll();
        },
      };
    },
    [editor, manager, setXml, getXml, getHTML, getJSON]
  );

  var runCmd = useCallback(
    function (fn) {
      if (!editor || !editable) return;
      fn();
    },
    [editor, editable]
  );

  return (
    <div className={className}>
      {showToolbar ? (
        <div className="contrib-editor-toolbar" role="toolbar">
          <button
            type="button"
            className="contrib-btn"
            disabled={!editable}
            onClick={function () {
              runCmd(function () {
                editor.chain().focus().toggleBold().run();
              });
            }}
          >
            Bold
          </button>
          <button
            type="button"
            className="contrib-btn"
            disabled={!editable}
            onClick={function () {
              runCmd(function () {
                editor.chain().focus().toggleItalic().run();
              });
            }}
          >
            Italic
          </button>
          <button
            type="button"
            className="contrib-btn"
            disabled={!editable}
            onClick={function () {
              runCmd(function () {
                editor.chain().focus().toggleUnderline().run();
              });
            }}
          >
            Underline
          </button>
          <button
            type="button"
            className="contrib-btn"
            disabled={!editable}
            onClick={function () {
              runCmd(function () {
                editor.chain().focus().toggleSuperscript().run();
              });
            }}
          >
            Sup
          </button>
          <button
            type="button"
            className="contrib-btn"
            disabled={!editable}
            onClick={function () {
              runCmd(function () {
                editor.chain().focus().toggleSubscript().run();
              });
            }}
          >
            Sub
          </button>
          <span className="contrib-toolbar-sep" />
          <button
            type="button"
            className="contrib-btn"
            disabled={!editable}
            onClick={function () {
              runCmd(function () {
                editor.commands.setSuggestMode();
              });
            }}
          >
            Suggest
          </button>
          <button
            type="button"
            className="contrib-btn"
            disabled={!editable}
            onClick={function () {
              runCmd(function () {
                editor.commands.setEditMode();
              });
            }}
          >
            Edit
          </button>
          <button
            type="button"
            className="contrib-btn"
            disabled={!editable}
            onClick={function () {
              runCmd(function () {
                editor.commands.acceptAll();
              });
            }}
          >
            Accept all
          </button>
          <button
            type="button"
            className="contrib-btn"
            disabled={!editable}
            onClick={function () {
              runCmd(function () {
                editor.commands.rejectAll();
              });
            }}
          >
            Reject all
          </button>
        </div>
      ) : null}
      <EditorContent editor={editor} className="contrib-editor-content" />
    </div>
  );
}

ContribEditor.buildExtensions = function (options) {
  return TipTapManager.buildExtensions(options);
};

export { TipTapManager };
export default ContribEditor;
