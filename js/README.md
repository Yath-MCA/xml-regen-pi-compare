# regen-pi (ES2016)

Browser-friendly class module that regenerates `<?pistart xml:space="..."?>`
separator PIs inside JATS `<contrib-group>` XML.

Ported from `contrib_script/regen_compare_v1.py` (Phase 2 regen subset).
Canonical config is **Option B** (`classname` required on every `<separator>`),
matching the journal **split** config XML pattern used by the existing web app.

| Focus slot | Behavior in this module |
|---|---|
| `given-names` | Insert PI inside / before `</given-names>` when `pos="inner"` |
| `between-xrefs` | Insert PI after every non-last `<xref>` when `pos="after"` |
| `between-contribs` | Insert PI as last child before `</contrib>` using `when` / `contribs` |

Python also handles `surname` and `affixes`; those slots are **not** regenerated
here yet (see [DEV.md](./DEV.md#extending-slots)).

## Install / import

Unit tests use Vitest + happy-dom under this `js/` folder:

```bash
cd js
npm install
npm test            # one-shot
npm run test:watch  # watch mode
```

See [QA.md](./QA.md) for smoke cases covered by `__tests__/regen-pi.spec.js`.

For the host app, copy or import the file as an ES module (no runtime npm dependency):

```js
import RegenPi, {
  RegenPiError,
  RegenPiSelector,
  RegenPiRule,
  RegenPiConfig,
  parsePiConfigDoc,
  parsePiConfigFromClientConfig,
  parsePiConfigXml,
  getLoadingClientConfig,
  resolveClientConfigEntry,
  stripPistart,
  makePistart,
  formatPiAttrValue,
  roleOf,
  pickBetweenContribsRule,
} from './regen-pi.js';
```

## Preferred load: live `XML_DOC` (no re-fetch)

In the host web app, journal split configs are already loaded into a DOM
Document on the global:

```text
LOADING_CONFIG.CLIENT_CONFIG   // object / map of entries
  entry.FILE_NAME      e.g. "MD.xml"
  entry.IGNORE_TRACK   e.g. false
  entry.IS_LOADED      e.g. true
  entry.ORDER          e.g. 5
  entry.SEPARATE_FILE  e.g. true
  entry.TYPE           e.g. "SPLIT"
  entry.URL            e.g. "assets/v6.05.695/config/journals/lww/split/MD.xml"
  entry.XML_DOC        Document  (live DOM — use this)
```

```js
// Uses global LOADING_CONFIG.CLIENT_CONFIG (throws if missing / unloaded)
const engine = RegenPi.fromClientConfig(null, { fileName: 'MD.xml' });

// Or pass the map / a single entry explicitly
const engine2 = RegenPi.fromClientConfig(LOADING_CONFIG.CLIENT_CONFIG, {
  fileName: 'MD.xml',
});

// Or the Document directly
const engine3 = RegenPi.fromXmlDoc(
  LOADING_CONFIG.CLIENT_CONFIG[/* key */].XML_DOC
);
```

Safety (`RegenPiError` with a clear message) when:

- `LOADING_CONFIG` / `CLIENT_CONFIG` missing (and you relied on the global)
- `IS_LOADED` is false
- `XML_DOC` is null
- multi-entry map without `fileName` / `url` / `key`

String parse (`RegenPi.fromXml` / `parsePiConfigXml`) still works for Node tests
and needs `DOMParser`; prefer Document APIs in the browser.

## Option B config

Same pattern as journal split configs. Sample checked into this folder:
[`LWW_MD.separator-classname.xml`](./LWW_MD.separator-classname.xml)

```xml
<separator classname="given-names" value="&#x00A0;" pos="inner"/>
<separator classname="between-xrefs" value="," pos="after"/>
<separator classname="between-contribs" value="," pos="after" contribs="3+"/>
```

- Blank / missing `classname` on `<separator>` throws `RegenPiError`.
- Legacy tag-as-kind (`<given-names value="..." pos="inner"/>`) still parses;
  the tag name becomes `classname`.

Full schema: [CONFIG.md](./CONFIG.md).

## API (matches `regen-pi.js`)

### `RegenPi` (default export)

| Member | Description |
|---|---|
| `RegenPi.fromClientConfig(clientConfig?, opts?)` | **Preferred** — `LOADING_CONFIG.CLIENT_CONFIG` entry/map → engine |
| `RegenPi.fromXmlDoc(xmlDoc)` | **Preferred** — live `Document` / `XML_DOC` → engine |
| `RegenPi.fromXml(xmlText)` | Parse string (needs `DOMParser`) |
| `RegenPi.fromConfig(config)` | Wrap existing `RegenPiConfig` |
| `new RegenPi(config)` | Requires a `RegenPiConfig` instance |
| `engine.select(classname)` | Rules for one classname (`RegenPiRule[]`) |
| `engine.regen(stripXml)` | Insert separator PIs into already-stripped contrib XML |
| `RegenPi.makePistart(value)` | Build `<?pistart xml:space="..."?>` |

There is **no** `stripAndRegen` helper. Strip first with `stripPistart`, then
call `regen`.

### Model classes

- **`RegenPiError`** — blank classname, bad XML, missing global, unloaded `XML_DOC`, etc.
- **`RegenPiSelector(classname, { pos, contribs, when })`** — classname required non-blank; default `pos` is `"after"`.
- **`RegenPiRule(selector, value)`** — getters: `classname`, `kind` (alias), `pos`, `contribs`, `when`. Factory: `fromFlat(...)`.
- **`RegenPiConfig`** — `client`, `shortcode`, `dtd`, `version`, `status`, `elements`, `ques`, `rules`. Methods: `select`, `separatorsOf`; getter `separators`.

### Config helpers

| Function | Role |
|---|---|
| `parsePiConfigDoc(xmlDoc)` | Live Document → `RegenPiConfig` |
| `parsePiConfigFromClientConfig(mapOrEntry, opts?)` | CLIENT_CONFIG → config (checks `IS_LOADED` / `XML_DOC`) |
| `getLoadingClientConfig()` | Read `globalThis.LOADING_CONFIG.CLIENT_CONFIG` |
| `resolveClientConfigEntry(mapOrEntry, opts?)` | Pick one entry by `fileName` / `url` / `key` |
| `resolvePiConfigRoot(docOrRoot)` | Find `<pi-config>` element |
| `configFromPiConfigElement(root)` | Element → `RegenPiConfig` |
| `parsePiConfigXml(xmlText)` | String → config (DOMParser) |

### Other helpers

| Function | Role |
|---|---|
| `stripPistart(text)` | Remove only `<?pistart ...?>` PIs |
| `makePistart(value)` / `formatPiAttrValue(value)` | Escape + wrap PI attribute |
| `roleOf(i, n)` | `"first"` / `"last-before"` / `"last"` / `"other"` |
| `pickBetweenContribsRule(rules, index, n)` | Choose between-contribs rule |

## Smoke usage

```js
import { RegenPi, stripPistart } from './regen-pi.js';

const engine = RegenPi.fromClientConfig(LOADING_CONFIG.CLIENT_CONFIG, {
  fileName: 'MD.xml',
});

const stripped = stripPistart(cleanContribGroupXml);
const regenerated = engine.regen(stripped);

engine.select('given-names');
engine.select('between-contribs');
```

Standalone / Node (string path) and Vitest: see [QA.md](./QA.md) (`npm test` in this folder).

## Docs index

| Doc | Contents |
|---|---|
| [SKILL.md](./SKILL.md) / [skills/regen-pi.md](./skills/regen-pi.md) | When to use; extract vs regen-pi; CLIENT_CONFIG |
| [CONFIG.md](./CONFIG.md) | pi-config Option B schema |
| [DEV.md](./DEV.md) | Architecture vs Python; XML_DOC; extending slots |
| [QA.md](./QA.md) | Test plan, edge cases, Vite/vitest |
| [CHANGELOG.md](./CHANGELOG.md) | Release notes |

Package CLI workflows (Python extract / regen-pi): see
[`../REGEN_COMMAND.md`](../REGEN_COMMAND.md).
