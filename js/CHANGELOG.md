# Changelog — regen-pi (JS)

## 0.1.0 — 2026-09-29

### Fixed

- `insertGivenNamesPis`: self-closing `<given-names/>` expands to an empty
  element before the shared close-tag pass so only one PI is inserted.

### Added

- ES2016 module `regen-pi.js` with class API:
  `RegenPi`, `RegenPiConfig`, `RegenPiRule`, `RegenPiSelector`, `RegenPiError`.
- **Preferred web-app load path:** `RegenPi.fromClientConfig` /
  `RegenPi.fromXmlDoc` using live `LOADING_CONFIG.CLIENT_CONFIG[*].XML_DOC`
  (no re-fetch). Safety errors when global missing, `IS_LOADED` false, or
  `XML_DOC` null.
- Helpers: `parsePiConfigDoc`, `parsePiConfigFromClientConfig`,
  `getLoadingClientConfig`, `resolveClientConfigEntry`, `resolvePiConfigRoot`,
  `configFromPiConfigElement`, plus string `parsePiConfigXml`.
- Option B config parsing: `<separator classname="..." .../>` required
  non-blank classname; legacy tag-as-kind still accepted.
- Regen focus slots: `given-names`, `between-xrefs`, `between-contribs`
  (role / `when` / optional `contribs`).
- Helpers: `stripPistart`, `makePistart`, `formatPiAttrValue`, `roleOf`,
  `pickBetweenContribsRule`.
- Sample config `LWW_MD.separator-classname.xml`.
- Docs: README, SKILL, CONFIG, DEV, QA, CHANGELOG.

### Not yet

- `surname` / `affixes` slot insertion (Python-only for now).
- Compare HTML / batch harness (Python Phases 3–4).
- Published npm package / Vitest scaffold.
