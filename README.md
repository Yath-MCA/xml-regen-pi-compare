# Extract Contrib Project

Interactive CLI and optional FastAPI service for generating contributor reports from a project folder that contains `documents.json` and `meta.json`.

## What The Tool Does

This package has two related workflows.

### 1. Extract contrib XML and build reports

For each selected JATS client and shortcode, the tool:

1. Reads `documents.json` and `meta.json`.
2. Finds each document XML file from the document folder or file list.
3. Extracts the `<contrib-group>...</contrib-group>` XML.
4. Writes the extracted XML into each document folder as:

```text
contrib_group.xml
```

5. Builds shortcode-level reports under:

```text
%USERPROFILE%\Documents\impact-support-log\<timestamp>_contrib_reports\JATS\
```

The generated report files are:

```text
<client>_<shortcode>_contrib_v<N>.html
<client>_<shortcode>_elements_v<N>.html
<client>_<shortcode>_issues_v<N>.csv
```

Progress and report paths are saved in:

```text
meta-contrib.json
```

### 2. Extract XML, restore PI text, and check PI position/value

The XML workflow preserves processing instructions such as:

```xml
<?pistart xml:space=",&#x00A0;"?>
```

ElementTree normally drops processing instructions, so the parser is configured with `insert_pis=True`. The tool then reads the `xml:space` value from each `pistart` PI and uses it in the preview/report.

For preview only, the PI value is inserted back as visible text at the same position. Example:

```xml
<?pistart xml:space=",&#x00A0;"?>
```

is shown in the report as the comma/non-breaking-space text at that point in the contributor XML. This makes it easy to see where separator text was carried by PI instead of normal XML text.

The contrib report checks two PI details:

- `PI attr value`: the ordered `xml:space` values from `pistart`
- `PI position`: where each `pistart` appears inside the `<contrib>`

The report flags files where the PI value or PI position differs from the common pattern for that client/shortcode group. Other PI targets and comments are listed in the elements report as flags only.

## Requirements

- Python 3.14 or newer, based on `pyproject.toml`
- Dependencies from `requirements.txt`

Install dependencies from this folder:

```powershell
python -m pip install -r requirements.txt
```

Installing requirements only installs FastAPI/Uvicorn/Pydantic. It does not install this local package into Python. For module commands, either run from the parent folder shown below or set `PYTHONPATH` to the parent folder.

## Expected Input Folder

When the tool asks for `Project Folder`, provide the path to the folder that contains:

```text
documents.json
meta.json
```

Generated progress is saved to `meta-contrib.json` inside that same project folder.

Each document folder should contain the source XML, or `documents.json` should point to it. The tool skips `impact_config.xml` and generated `contrib_group.xml` files when looking for the source XML.

## Run the CLI

From this folder, use the local runner:

```powershell
python run_cli.py
```

The package-module form also works, but it must be run from the parent directory.

Because this directory is a Python package, run it from the parent directory:

```powershell
cd D:\NEW_GEN\LIVE_SUPPORT_2026\FOOTNOTES\From-2026-1st-to-now\contrib_script
python -m extract_contrib_porject
```

If you are already inside the package folder, go one level up first:

```powershell
cd ..
python -m extract_contrib_porject
```

The CLI will:

1. Ask for the project folder path.
2. Show available clients and shortcodes.
3. Ask which clients and shortcodes to generate.
4. Extract each `<contrib-group>`.
5. Write per-document `contrib_group.xml` and `contrib_preview.html`.
6. Write shortcode-level HTML/CSV reports and save progress in `meta-contrib.json`.

## Run the API

From this folder, use the local runner:

```powershell
python run_api.py
```

Then open:

```text
http://127.0.0.1:8000/docs
```

The package-module form also works, but it must be run from the parent directory.

Start the FastAPI app from the parent directory:

```powershell
cd D:\NEW_GEN\LIVE_SUPPORT_2026\FOOTNOTES\From-2026-1st-to-now\contrib_script
python -m uvicorn extract_contrib_porject.api:app --reload
```

If you are already inside the package folder, go one level up first:

```powershell
cd ..
python -m uvicorn extract_contrib_porject.api:app --reload
```

Open the interactive API docs:

```text
http://127.0.0.1:8000/docs
```

## API Endpoints

```text
GET  /overview?root=...
GET  /clients?root=...
GET  /shortcodes?root=...&client=...
POST /generate
GET  /report?root=...&client=...&shortcode=...&kind=contrib
```

Example API root value:

```text
D:\path\to\folder-containing-documents-json-and-meta-json
```

Example generate request body:

```json
{
  "root": "D:\\path\\to\\folder-containing-documents-json-and-meta-json",
  "client": "CLIENT_NAME",
  "shortcode": "SHORTCODE"
}
```

Report `kind` can be one of:

```text
contrib
elements
issues
```

## Notes

- Do not run `python api.py` directly; it uses package-relative imports.
- If you see `ModuleNotFoundError: No module named 'extract_contrib_porject'`, run `python run_cli.py` or `python run_api.py` from this folder, or run the `python -m ...` commands from the parent `contrib_script` folder.
- Use the CLI for large multi-client runs because it supports pauses between shortcodes and clients.
- Use the API for checking status, generating one client/shortcode at a time, and downloading generated reports.

## JS regen-pi module

Browser/ES2016 port of the regen Phase-2 idea lives under [`js/`](./js/). Start with [`js/README.md`](./js/README.md).

In the host web app, prefer `RegenPi.fromClientConfig(LOADING_CONFIG.CLIENT_CONFIG, { fileName })` or `RegenPi.fromXmlDoc(entry.XML_DOC)` so the already-loaded journal split config Document is reused (no re-fetch). Option B sample: [`js/LWW_MD.separator-classname.xml`](./js/LWW_MD.separator-classname.xml).

CLI extract / regen-pi workflows remain in [`REGEN_COMMAND.md`](./REGEN_COMMAND.md).
