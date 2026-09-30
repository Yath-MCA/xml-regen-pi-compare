# QA — regen-pi test plan

## Goals

- Prove Option B config parse + regen for the three focus slots.
- Prefer the web-app path: live `XML_DOC` via `LOADING_CONFIG.CLIENT_CONFIG` (no re-fetch).
- Lock edge cases: blank classname, last contrib, NBSP, missing/unloaded global config.
- Stay ES2016-compatible; no invented facade methods beyond `regen-pi.js` exports.

## Preferred load path (web app)

```js
import { RegenPi } from './regen-pi.js';

// A) Global already populated by the host app
const engine = RegenPi.fromClientConfig(); // reads LOADING_CONFIG.CLIENT_CONFIG
// or narrow when the map has many journals:
const engine2 = RegenPi.fromClientConfig(null, { fileName: 'MD.xml' });
// B) Explicit entry / map
const engine3 = RegenPi.fromClientConfig(LOADING_CONFIG.CLIENT_CONFIG, {
  fileName: 'MD.xml',
});
// C) Direct Document
const engine4 = RegenPi.fromXmlDoc(entry.XML_DOC);
```

Entry fields used for safety:

| Field | Rule |
|---|---|
| `IS_LOADED` | must be truthy |
| `XML_DOC` | must be non-null Document (or Element with `<pi-config>`) |
| Global `LOADING_CONFIG` | required only when calling `fromClientConfig()` with no argument |

## Smoke cases (module contract / sample-validated)

These follow `regen-pi.js` behavior, the LWW/MD Option B sample
`LWW_MD.separator-classname.xml`, and the web-app `CLIENT_CONFIG` pattern.

| # | Case | Expect |
|---|---|---|
| S1 | `RegenPi.fromXml` on sample Option B file | Config loads; `select('given-names')` length ≥ 1 |
| S1b | `RegenPi.fromXmlDoc(doc)` after `DOMParser` parse of sample | Same rules as S1; no second string parse inside regen helpers |
| S1c | `fromClientConfig` with `{ IS_LOADED: true, XML_DOC: doc, FILE_NAME: 'MD.xml' }` | Engine builds; `select('between-contribs')` returns sample rules |
| S2 | `given-names` regen with `pos="inner"` | PI before `</given-names>`; empty `<given-names/>` wraps PI |
| S3 | `between-xrefs` with ≥2 xrefs | PI after each xref except the last |
| S4 | `between-xrefs` with 0–1 xref | No xref PI inserted |
| S5 | `between-contribs` `contribs="3+"` default `,` | Matching non-last roles get `,` when n ≥ 3 |
| S6 | `when="last-before"` + `contribs="3+"` / `"2"` | Second-to-last gets `and` per matching rule |
| S7 | `when="last"` | Last contrib gets PI only if an explicit last rule matches |
| S8 | `stripPistart` then `regen` | Only pistart PIs removed; separators match config |
| S9 | NBSP value `&#x00A0;` | Unescapes to `\u00a0`; `makePistart` emits `&#x00A0;` |
| S10 | Legacy `<given-names .../>` under `<separators>` | classname `given-names` |

## Edge cases

| Case | Expect |
|---|---|
| Blank classname on `<separator>` | `RegenPiError` |
| `new RegenPiSelector('')` / whitespace-only | `RegenPiError` |
| `config.select('')` | `RegenPiError` |
| Missing `DOMParser` when calling `parsePiConfigXml` | `RegenPiError` |
| Invalid XML / no `<pi-config>` | `RegenPiError` |
| `fromClientConfig()` with no `LOADING_CONFIG` | `RegenPiError` (clear message) |
| `IS_LOADED: false` | `RegenPiError` |
| `XML_DOC: null` | `RegenPiError` |
| Multi-entry `CLIENT_CONFIG` without `fileName`/`url`/`key` | `RegenPiError` |
| Last contrib with no `when="last"` rule | No between-contribs PI |
| Empty `value=""` on last rule | PI emitted with empty `xml:space=""` if selected |
| `contribs` mismatch (n=2 vs `3+`) | Rule skipped |
| Self-closing vs open `given-names` | Both handled by `insertGivenNamesPis` |

## Manual browser smoke (host app)

1. Open a journal that loads split config into `LOADING_CONFIG.CLIENT_CONFIG`.
2. Confirm an entry has `IS_LOADED === true` and `XML_DOC` is a Document.
3. In console / module:

   ```js
   import { RegenPi, stripPistart } from '/path/to/regen-pi.js';
   const engine = RegenPi.fromClientConfig(LOADING_CONFIG.CLIENT_CONFIG, {
     fileName: 'MD.xml',
   });
   engine.select('given-names');
   ```

4. Run S2–S7 against a small stripped contrib-group fixture.
5. Confirm no re-fetch of `URL` occurs (Document reuse only).

## Vite / Vitest (scaffolded)

Layout:

```text
js/
  package.json          # "test": "vitest run"
  vitest.config.js      # environment: happy-dom (DOMParser + Document)
  regen-pi.js
  LWW_MD.separator-classname.xml
  __tests__/
    regen-pi.spec.js    # QA smoke S1–S10 + CLIENT_CONFIG safety
```

### How to run

From this `js/` folder (npm preferred):

```bash
npm install
npm test            # vitest run (CI / one-shot)
npm run test:watch  # vitest watch mode
```

`happy-dom` supplies `DOMParser` and `Document` so `fromXml` / `fromXmlDoc` /
mocked `LOADING_CONFIG.CLIENT_CONFIG[].XML_DOC` work under Node.

### Spec coverage

| Area | Spec focus |
|---|---|
| S1 / S1b | `fromXml` / `fromXmlDoc` on Option B sample |
| S1c | `fromClientConfig` entry + mocked global map + `fileName` |
| Safety | missing `LOADING_CONFIG`, `IS_LOADED: false`, `XML_DOC: null`, multi-entry without selector |
| Blank classname | `fromXml`, `RegenPiSelector`, `select('')` |
| S2–S7 | given-names / between-xrefs / between-contribs regen |
| S8–S10 | `stripPistart`→`regen`, NBSP `&#x00A0;`, legacy tag-as-kind |

## Out of scope for JS QA (Python covered)

- Full harness compare HTML / match %
- Batch client/shortcode summary
- `surname` / affix insertion until ported

## Regression checklist before merge

- [ ] Docs API matches exports in `regen-pi.js` (includes `fromXmlDoc` / `fromClientConfig`)
- [ ] Preferred path uses `XML_DOC` without re-fetch
- [x] Missing global / `IS_LOADED` false / null `XML_DOC` throw clear `RegenPiError` (vitest)
- [x] Option B sample still parses (vitest)
- [x] Blank classname still throws (vitest)
- [ ] Last contrib still silent without `when="last"`
- [ ] NBSP round-trips as `&#x00A0;` in PI attribute
