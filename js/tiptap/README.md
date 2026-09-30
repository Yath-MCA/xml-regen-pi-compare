# contrib-tiptap

TipTap React editor for IMPACT / contrib HTML, with a **Summernote-style**
native ↔ custom HTML skeleton transform, an **ICE lite bridge** for
CKEditor 4 + [nytimes/ice](https://github.com/nytimes/ice) track-change markup,
and track changes from
[`tiptap-track-changes`](https://github.com/sungkhum/tiptap-track-changes).

Sibling [`../regen-pi.js`](../regen-pi.js) strips `<?pistart …?>` on load and
re-applies separators on save.

## Layout

```text
tiptap/
  TipTapManager.js           # owner: TAG_MAP, format cache, ICE bridge wiring,
                             #   transformForEditor / restoreFromEditor, get/set,
                             #   regen-pi, extensions
  ContribEditor.jsx          # TipTap React UI + TrackChangesExtension
  transform/htmlSkeleton.js  # pure IMPACT ↔ editor HTML (Summernote-equivalent)
  transform/iceBridge.js     # pure ICE lite ↔ TipTap track-changes HTML
  index.js                   # public exports
  package.json               # peerDeps: @tiptap/*, tiptap-track-changes, react
  README.md
```

**Removed** (do not revive): `formatting/FormattingHandler.jsx`,
`tracking/TrackingHandler.jsx`, JSON `xmlToDoc` / `docToXml` mark serializers.
Formatting is HTML-skeleton at get/set; tracking is the peer package + ICE bridge.

## Pipeline

| Step | Module | Behavior |
|---|---|---|
| Load | `TipTapManager.setContent` / `setXml` | `stripPistart` → **`iceHtmlToEditor`** (ICE → TipTap `ins`/`del[data-change-id]`) → `transformForEditor` (IMPACT → `i`/`b`/… + `data-format-id` cache) → TipTap `setContent` |
| Edit | `ContribEditor` | StarterKit-style marks (`b`/`i`/…) + `TrackChangesExtension` (`mode: 'suggest'`) |
| Save | `TipTapManager.getContent` / `getXml` | TipTap `getHTML` → `restoreFromEditor` (editor → IMPACT) → **`editorHtmlToIce`** (TipTap track → ICE lite) → optional `RegenPi.regen` |

Dialog content from the major editor (CKEditor 4 + ICE) often looks like:
whole old text in a `del` / `ice-del` wrapper, new text in an `ins` / `ice-ins`
wrapper. That markup may also have already passed through the Summernote-style
formatting transform (`em`/`strong`/…). Both layers are handled on the TipTap
side so CKEditor4+ICE can accept the result on the way back.

## CKEditor4 + ICE ↔ TipTap round-trip

### ICE conventions recognized (verified against nytimes/ice)

| Piece | Values |
|---|---|
| Insert wrapper | `<ins class="ice-ins">`, `<span class="ice-ins">`, or vanilla ice `<span class="ins" data-cid>` |
| Delete wrapper | `<del class="ice-del">`, `<span class="ice-del">`, or vanilla ice `<span class="del" data-cid>` |
| Change id | `data-cid` |
| User | `data-userid`, `data-username` |
| Time | `data-time` (epoch ms string) |
| Optional | `data-changedata`, `title`, user style class `cts-N` / `ice-cts-N` |

### TipTap track-changes HTML (peer `tiptap-track-changes`)

| Mark | Tag | Attrs |
|---|---|---|
| Insertion | `<ins data-change-id>` | `data-author-id`, `data-author-name`, `data-timestamp` |
| Deletion | `<del data-change-id>` | same |

### Attribute map

| ICE | TipTap |
|---|---|
| `data-cid` | `data-change-id` |
| `data-userid` | `data-author-id` |
| `data-username` | `data-author-name` |
| `data-time` | `data-timestamp` (also cached in `TipTapManager._iceMeta` because the peer’s `renderHTML` may omit timestamp) |

### Example — before / after

**Incoming from CKEditor4+ICE (dialog):**

```html
<del class="ice-del cts-1" data-cid="42" data-userid="u1"
     data-username="Alice" data-time="1710000000000">old phrase</del>
<ins class="ice-ins cts-1" data-cid="43" data-userid="u1"
     data-username="Alice" data-time="1710000000000">new <em class="italic">phrase</em></ins>
```

**After `iceHtmlToEditor` (TipTap-loadable track HTML):**

```html
<del data-change-id="42" data-author-id="u1" data-author-name="Alice"
     data-timestamp="1710000000000">old phrase</del>
<ins data-change-id="43" data-author-id="u1" data-author-name="Alice"
     data-timestamp="1710000000000">new <em class="italic">phrase</em></ins>
```

**After full `setContent` (ICE bridge + IMPACT format transform):**

```html
<del data-change-id="42" data-author-id="u1" data-author-name="Alice"
     data-timestamp="1710000000000">old phrase</del>
<ins data-change-id="43" data-author-id="u1" data-author-name="Alice"
     data-timestamp="1710000000000">new <i data-format-id="1">phrase</i></ins>
```

**On `getContent` (restore IMPACT + `editorHtmlToIce`):**

```html
<del class="ice-del cts-1" data-cid="42" data-userid="u1"
     data-username="Alice" data-time="1710000000000">old phrase</del>
<ins class="ice-ins cts-1" data-cid="43" data-userid="u1"
     data-username="Alice" data-time="1710000000000">new <em class="italic" data-name="italic">phrase</em></ins>
```

(`cts-1` / `data-time` are restored from `_iceMeta` when TipTap’s HTML omit them.)

## TAG_MAP (IMPACT ↔ editor)

| IMPACT | Editor | Notes |
|---|---|---|
| `em` | `i` | cached attrs |
| `strong` | `b` | cached attrs |
| `cite` | `i` | cached attrs |
| `i` / `b` | passthrough | |
| `sup` / `sub` / `u` / `sc` / `span` | same | only when element has attrs |

Bare `i` / `b` (no cache) restore via `DEFAULT_RESTORE` → `em` / `strong`.

## Install (peers only)

```bash
npm install @tiptap/react @tiptap/starter-kit @tiptap/core @tiptap/pm tiptap-track-changes
```

## API

```js
import ContribEditor, {
  TipTapManager,
  transformToEditor,
  restoreFromEditor,
  iceHtmlToEditor,
  editorHtmlToIce,
  TAG_MAP,
  DEFAULT_RESTORE,
  ICE_ATTR,
  TIPTAP_ATTR,
} from './tiptap/index.js';
import RegenPi from '../regen-pi.js';

// Imperative manager (SummernoteManager twin)
const mgr = new TipTapManager(moduleInstance, {
  author: { id: 'u1', name: 'Alice', color: '#2d5fce' },
  trackMode: 'suggest',
  // iceBridge: false,  // set false to skip ICE ↔ TipTap conversion
});
mgr.bindEditor(editor);
mgr.setXml(impactHtmlWithIce, editor);   // strip + ICE bridge + format + setContent
const impactIce = mgr.getContent(editor); // getHTML + restore + ICE bridge
const withPi = mgr.getXml(editor, {       // restore + ICE + regen
  clientConfig: LOADING_CONFIG.CLIENT_CONFIG,
  fileName: 'MD.xml',
});

// Pure bridge helpers (no TipTap / format coupling)
iceHtmlToEditor(iceHtml, { meta: new Map() });
editorHtmlToIce(tipTapTrackHtml, {
  meta: new Map(),
  defaultUser: { id: 'u1', name: 'Alice' },
});

// React
<ContribEditor
  xml={contribXml}
  author={{ id: 'u1', name: 'Alice', color: '#2d5fce' }}
  trackMode="suggest"
  regenOpts={{ fileName: 'MD.xml' }}
  autoExportXml
  onXmlChange={(xml) => { /* persist — ICE lite shape for CKEditor4 */ }}
/>

// Track-changes commands (from peer)
editor.commands.setSuggestMode();
editor.commands.setEditMode();
editor.commands.acceptAll();
editor.commands.rejectAll();

// Helpers on live editor
editor.contrib.setXml(xml);
editor.contrib.getXml({ fileName: 'MD.xml' });
editor.contrib.getHTML();   // restored IMPACT + ICE HTML
editor.contrib.manager;     // TipTapManager instance
```

### `transform/htmlSkeleton.js`

Pure functions (no TipTap / regen / ICE coupling):

- `transformToEditor(html, cacheBag)`
- `restoreFromEditor(html, cacheBag)`
- `unwrapParagraphs`, `reconcileAfterCommand`, `ensureBag`
- `TAG_MAP`, `DEFAULT_RESTORE`, `LIVE_CHECK`

### `transform/iceBridge.js`

Pure functions (no TipTap / format / regen coupling):

- `iceHtmlToEditor(html, { meta })` — ICE → TipTap track HTML; fills optional `meta` Map by cid
- `editorHtmlToIce(html, { meta, defaultUser, now, ctsClass })` — TipTap track → ICE lite
- `isIceInsert` / `isIceDelete` / `isTipTapInsert` / `isTipTapDelete`
- `ICE_ATTR`, `TIPTAP_ATTR`, `ICE_INS_CLASS`, `ICE_DEL_CLASS`

`TipTapManager.setContent` / `getContent` call these around the format skeleton.
Disable with `{ iceBridge: false }` on the manager or per `setContent` call.

## Round-trip note

1. Incoming HTML/XML may contain `<?pistart …?>` from a previous regen **and**
   ICE lite `ins`/`del` (or `span.ins` / `span.del`) wrappers from CKEditor4.
2. `setXml` always strips PI (unless `{ stripPi: false }`), then bridges ICE →
   TipTap track marks, then runs the IMPACT format transform.
3. Edits happen on native editor tags + TipTap track marks; format cache keeps
   IMPACT tag + attrs; `_iceMeta` keeps ICE userid/time/cts for attrs the peer
   may not re-render.
4. `getContent` restores IMPACT HTML, then TipTap track → ICE lite so the major
   editor can load it. `getXml` then runs `RegenPi.regen`.

See [`../CONFIG.md`](../CONFIG.md) and [`../DEV.md`](../DEV.md).