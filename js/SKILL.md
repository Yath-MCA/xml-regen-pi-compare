# Skill: regen-pi (JS)

ES2016 module for regenerating contrib-group separator PIs from an Option B
`pi-config` XML (same pattern as journal **split** configs in the web app).

## When to use

- Browser app already loaded journal config into
  `LOADING_CONFIG.CLIENT_CONFIG[*].XML_DOC` and you must **not** re-fetch.
- You need to rebuild `<?pistart xml:space="..."?>` separators for
  `given-names` / `between-xrefs` / `between-contribs`.
- Role-aware `between-contribs` (`when` / `contribs`) without the Python batch harness.

## When not to use

- Full batch extract + report generation → Python CLI (`extract` workflow).
- Full strip → regen → HTML compare across a harness → Python `regen-pi` /
  `regen_compare_v1.py` (Phases 1–4).
- Slots not yet ported: `surname`, `affixes` (see DEV.md).

## Inputs

| Input | Notes |
|---|---|
| `LOADING_CONFIG.CLIENT_CONFIG` entry | Preferred: `IS_LOADED` + live `XML_DOC` |
| `Document` (`XML_DOC`) | `RegenPi.fromXmlDoc(doc)` |
| `pi-config` XML string | Fallback for tests; needs `DOMParser` |
| Strip XML | Contrib-group with pistart removed (or `stripPistart` first) |

## Outputs

| Output | Notes |
|---|---|
| Regenerated XML string | `engine.regen(stripXml)` |
| Rule lists | `engine.select(classname)` |

## Classname rules (Option B)

1. Every `<separator>` **must** have a non-blank `classname`.
2. Blank / missing classname → `RegenPiError`.
3. Legacy non-`separator` children map `tagName → classname`.
4. Regen focus classnames: `given-names`, `between-xrefs`, `between-contribs`.

## CLIENT_CONFIG safety

```js
RegenPi.fromClientConfig(LOADING_CONFIG.CLIENT_CONFIG, { fileName: 'MD.xml' });
// or
RegenPi.fromXmlDoc(entry.XML_DOC);
```

Throws `RegenPiError` if global missing, `IS_LOADED` false, or `XML_DOC` null.

## Workflows: extract vs regen-pi

| Workflow | Layer | Purpose |
|---|---|---|
| **extract** | Python CLI | Pull `<contrib-group>`; write reports |
| **regen-pi** (Python) | CLI / `regen_compare_v1.py` | Strip → regen → compare HTML |
| **regen-pi** (this JS) | `js/regen-pi.js` | Phase-2 regen in browser using live `XML_DOC` |

## Quick API reminder

```js
import { RegenPi, stripPistart } from './regen-pi.js';
const engine = RegenPi.fromClientConfig(null, { fileName: 'MD.xml' });
const out = engine.regen(stripPistart(cleanXml));
```

Details: [README.md](./README.md) · [CONFIG.md](./CONFIG.md) · [QA.md](./QA.md)
