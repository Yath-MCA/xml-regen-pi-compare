# Contributor CLI Commands

The unified CLI asks for the project folder, client, project code/shortcode, and then the workflow. The examples below process client `LWW` and shortcode `MD`.

## Interactive Workflow

```powershell
cd "D:\NEW_GEN\LIVE_SUPPORT_2026\FOOTNOTES\From-2026-1st-to-now\contrib_script\extract_contrib_package"
python .\run_cli.py
```

Prompt order:

```text
Project Folder:
Client:
Project code / shortcode:
Workflow:
  1) extract
  2) regen-pi
```

## Process 1: Extract Contributors and Generate Reports

```powershell
python .\run_cli.py `
  --root "D:\NEW_GEN\LIVE_SUPPORT_2026\FOOTNOTES\From-2026-1st-to-now" `
  --client LWW `
  --project-code MD `
  --workflow extract
```

This process reads `documents.json` and `meta.json`, extracts the contributor group, and generates the contributor reports.

## Process 2: Regenerate and Compare Only

Run this after Process 1 has created the extracted contributor XML:

```powershell
python .\run_cli.py `
  --root "D:\NEW_GEN\LIVE_SUPPORT_2026\FOOTNOTES\From-2026-1st-to-now" `
  --client LWW `
  --project-code MD `
  --workflow regen-pi
```

This process uses the existing `contrib_group_original_clean.xml` files and does not run extraction.

### One document only

Default regen-pi processes every docid for the client/project-code. To process a single document:

```powershell
python .\run_cli.py `
  --root "D:\NEW_GEN\LIVE_SUPPORT_2026\FOOTNOTES\From-2026-1st-to-now" `
  --client LWW `
  --project-code MD `
  --workflow regen-pi `
  --one-doc
```

`--one-doc` picks the first matching JATS docid (sorted) for that client/shortcode.

Or pass an explicit id:

```powershell
python .\run_cli.py `
  --root "D:\NEW_GEN\LIVE_SUPPORT_2026\FOOTNOTES\From-2026-1st-to-now" `
  --client LWW `
  --project-code MD `
  --workflow regen-pi `
  --docid N0032c01d-a8f4-444c-bdb9-23cd92f43e8e
```

Note: `contrib_group_original_clean.xml` still contains `<?pistart?>` (comments cleaned only). Strip output is `contrib_group_strip_pi.xml`. HTML `span.pistart` strip is handled by the impact_qa Node runner (see impact_qa `src/js/regen_pi/RUN.md`), not this Python workflow.

For a non-standard layout, add `--config "path\config.xml"` and `--harness "path\JATS"`.

It creates these files in each processed document directory:

- `contrib_group_strip_pi.xml`
- `contrib_group_regen.xml`
- `contrib_group_compare.html`

The batch summary is written to:

```text
JATS\regen_compare_reports\LWW_MD_regen_compare_v1.html
```

## JS module (regen-pi.js)

For in-browser reuse of the Option B separator model, see [`js/README.md`](./js/README.md) and [`js/SKILL.md`](./js/SKILL.md).

Preferred API against the host app global:

```js
RegenPi.fromClientConfig(LOADING_CONFIG.CLIENT_CONFIG, { fileName: 'MD.xml' });
// or RegenPi.fromXmlDoc(entry.XML_DOC)
```

JS regenerates `given-names`, `between-xrefs`, and `between-contribs` only; full strip/compare batching stays in this CLI and `regen_compare_v1.py`.
