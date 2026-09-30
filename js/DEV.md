# DEV — regen-pi architecture

## Relationship to `regen_compare_v1.py`

Python script (sibling of this package):
`contrib_script/regen_compare_v1.py`

| Phase | Python | This JS module |
|---|---|---|
| 1 Strip | `strip_pi` → `contrib_group_strip_pi.xml` | `stripPistart(text)` |
| 2 Regen | `regen_group` / `regen_one_contrib` | `RegenPi.regen(stripXml)` |
| 3 Compare | slot-by-slot HTML | **not ported** |
| 4 Batch | harness summary | **not ported** |

### Slot coverage

| Slot | Python | JS `regen()` |
|---|---|---|
| `surname` (inner, conditional when) | yes | **no** (store via config only) |
| `given-names` (inner) | yes | yes (`pos="inner"`) |
| `affixes` / `alis="affix"` elements | yes | **no** |
| `between-xrefs` | yes | yes (`pos="after"`, skip last xref) |
| `between-contribs` | yes (`role` / `when`) | yes (`when` + optional `contribs`) |

Python `load_config` historically expects **legacy** separator tags.
This JS parser prefers **Option B** `<separator classname="..."/>` (same as
journal split configs) and still accepts legacy tags.

### PI escaping

| | Python `esc_for_pi` | JS `formatPiAttrValue` |
|---|---|---|
| NBSP | → `&#x00A0;` | → `&#x00A0;` |
| `&` `"` `<` | not escaped in esc_for_pi | escaped to XML entities |

## Web-app config Document (preferred)

The host app loads journal split XML once and keeps a live DOM on:

```text
LOADING_CONFIG.CLIENT_CONFIG[<key>].XML_DOC   // Document
LOADING_CONFIG.CLIENT_CONFIG[<key>].IS_LOADED // must be true
LOADING_CONFIG.CLIENT_CONFIG[<key>].FILE_NAME // e.g. "MD.xml"
LOADING_CONFIG.CLIENT_CONFIG[<key>].URL       // assets/.../split/MD.xml
LOADING_CONFIG.CLIENT_CONFIG[<key>].TYPE      // e.g. "SPLIT"
```

**Do not re-fetch `URL`.** Call:

```js
RegenPi.fromClientConfig(LOADING_CONFIG.CLIENT_CONFIG, { fileName: 'MD.xml' });
// or
RegenPi.fromXmlDoc(entry.XML_DOC);
```

Internals:

```text
getLoadingClientConfig()
  → resolveClientConfigEntry(map, opts)
    → parsePiConfigFromClientConfig  (IS_LOADED + XML_DOC checks)
      → parsePiConfigDoc(XML_DOC)
        → resolvePiConfigRoot → configFromPiConfigElement
```

String path (`fromXml` / `parsePiConfigXml`) is for Node/tests only; it uses
`DOMParser.parseFromString` then the same `parsePiConfigDoc` path.

## Class map

```text
RegenPiError
RegenPiSelector     classname + pos + contribs + when
RegenPiRule         selector + value  (kind === classname)
RegenPiConfig       metadata + elements + ques + rules[]
RegenPi             facade:
                      fromClientConfig / fromXmlDoc / fromXml / fromConfig
                      select / regen
```

Config helpers: `parsePiConfigDoc`, `parsePiConfigFromClientConfig`,
`getLoadingClientConfig`, `resolveClientConfigEntry`, `resolvePiConfigRoot`,
`configFromPiConfigElement`, `parsePiConfigXml`.

Other helpers: `stripPistart`, `makePistart`, `formatPiAttrValue`, `roleOf`,
`pickBetweenContribsRule`.

Internal: `insertGivenNamesPis`, `insertXrefPis`, `insertBetweenContribs`,
XML walkers, `unescapeXmlEntities`, `contribsMatch`.

## Role / between-contribs

`roleOf(i, n)` mirrors Python `role_of`: `last` / `last-before` / `first` / `other`.

`pickBetweenContribsRule`:

- `"last"` → only `when === "last"` (+ `contribs` match); else **no PI**
- `"last-before"` → prefer `when === "last-before"`, else unconditional
- other roles → unconditional rules with matching `contribs`
- `contribs`: exact (`"2"`) or min (`"3+"`); blank/null = any

## Legacy XML compatibility

1. **Option B** (required for new configs / web split files):

   ```xml
   <separator classname="between-contribs" value="," pos="after" contribs="3+"/>
   ```

2. **Legacy tag-as-kind** (accepted):

   ```xml
   <given-names value="&#x00A0;" pos="inner"/>
   ```

3. Rejected: `<separator>` with missing/blank `classname`.

Sample: `LWW_MD.separator-classname.xml`.

## DOMParser / jsdom notes

- **Browser host app:** prefer `XML_DOC` — no `DOMParser` needed for config load.
- `parsePiConfigXml` throws if `DOMParser` is undefined.
- Node / Vitest string tests: polyfill `globalThis.DOMParser` (`@xmldom/xmldom`,
  `linkedom`, or `jsdom`).
- `unescapeXmlEntities` prefers `DOMParser` when present; else a small entity map.
- Regex regen paths do not need DOMParser.

## Extending slots (surname / affixes)

`regen()` hard-codes three selects. To add slots:

1. Add Option B rules to the journal split pi-config.
2. Implement insert helpers (mirror Python `regen_one_contrib` / `insert_affix_pis`).
3. Call from `RegenPi.regen`.
4. If affixes need `alis="affix"`, extend `configFromPiConfigElement` (today only
   `allowed` is stored on `elements` / `ques`).
5. Add vitest cases in [QA.md](./QA.md).

Keep Option B classname required.
