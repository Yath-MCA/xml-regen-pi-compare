/**
 * contrib-tiptap public exports.
 *
 * Sibling: ../regen-pi.js (PI regen via LOADING_CONFIG.CLIENT_CONFIG / XML_DOC).
 *
 * Design: Summernote-style IMPACT ↔ editor HTML skeleton (TipTapManager /
 * htmlSkeleton), ICE lite (CKEditor4+nytimes/ice) ↔ TipTap track marks
 * (iceBridge), TipTap get/set HTML, track changes via tiptap-track-changes.
 * No FormattingHandler / TrackingHandler custom marks.
 *
 * @module contrib-tiptap
 */

"use strict";

export { ContribEditor, default } from "./ContribEditor.jsx";
export {
  TipTapManager,
  UnderlineMark,
  SuperscriptMark,
  SubscriptMark,
  SmallcapsMark,
} from "./TipTapManager.js";
export { default as TipTapManagerDefault } from "./TipTapManager.js";

export {
  TAG_MAP,
  DEFAULT_RESTORE,
  LIVE_CHECK,
  getEditorTagAllowed,
  transformToEditor,
  restoreFromEditor,
  unwrapParagraphs,
  reconcileAfterCommand,
  ensureBag,
  collectElementAttrs,
  applyAttrs,
  replaceElementKeepChildren,
} from "./transform/htmlSkeleton.js";

export { default as htmlSkeleton } from "./transform/htmlSkeleton.js";

export {
  iceHtmlToEditor,
  editorHtmlToIce,
  isIceInsert,
  isIceDelete,
  isTipTapInsert,
  isTipTapDelete,
  ICE_INS_CLASS,
  ICE_DEL_CLASS,
  ICE_ATTR,
  TIPTAP_ATTR,
} from "./transform/iceBridge.js";

export { default as iceBridge } from "./transform/iceBridge.js";