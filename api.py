"""
Optional FastAPI wrapper around extract_contrib's pipeline.

Not imported by __init__.py (so `import extract_contrib` never requires
fastapi installed) - use it explicitly:

    pip install fastapi uvicorn
    uvicorn extract_contrib.api:app --reload

Endpoints
---------
GET  /overview?root=...                       client -> shortcode -> status
GET  /clients?root=...
GET  /shortcodes?root=...&client=...
POST /generate     {root, client, shortcode}   runs the pipeline, returns
                                                the meta-contrib.json entry
GET  /report        ?root=...&client=...&shortcode=...&kind=contrib|elements|issues
                                                serves the generated file

`root` is always the project folder (holding documents.json / meta.json),
exactly as typed at the "Project Folder:" prompt of the CLI. Generation is
run synchronously in a threadpool per request - fine for the batch sizes
this tool targets (a few seconds even for hundreds of documents); a very
large multi-client run is still better done with the CLI, which has the
between-shortcode pauses this API intentionally skips.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import config
from .helpers.io import load_json, resolve_meta_path
from .core.pipeline import build_index, dtd_of, load_done, process_group, status_of

app = FastAPI(title="extract_contrib API", version=str(config.SCRIPT_VERSION))


def _load(root: Path):
    if not (root / config.DOCS_NAME).exists() or not (root / config.META_NAME).exists():
        raise HTTPException(404, f"{config.DOCS_NAME} or {config.META_NAME} not found in {root}")
    docs = load_json(root / config.DOCS_NAME)
    metas = load_json(root / config.META_NAME)
    index = build_index(docs, metas)
    done = load_done(root)
    return docs, metas, index, done


@app.get("/overview")
def overview(root: str):
    """{client: {shortcode: {docs, status, pending}}} for every JATS shortcode."""
    _, _, index, done = _load(Path(root))
    out = {}
    for client, scs in index.items():
        out[client] = {}
        for sc, ids in scs.items():
            st, pending = status_of(done, client, sc, ids)
            out[client][sc] = {"docs": len(ids), "status": st, "pending_docs": pending}
    return out


@app.get("/clients")
def clients(root: str):
    _, _, index, _ = _load(Path(root))
    return sorted(index, key=str.lower)


@app.get("/shortcodes")
def shortcodes(root: str, client: str):
    _, _, index, _ = _load(Path(root))
    if client not in index:
        raise HTTPException(404, f"no {config.RUN_DTD} documents for client {client!r}")
    return sorted(index[client], key=str.lower)


class GenerateRequest(BaseModel):
    root: str
    client: str
    shortcode: str


@app.post("/generate")
async def generate(req: GenerateRequest):
    """Runs the pipeline for one client + shortcode and records it in meta-contrib.json."""
    root = Path(req.root)
    docs, metas, index, done = _load(root)
    ids = index.get(req.client, {}).get(req.shortcode)
    if not ids:
        raise HTTPException(404, f"no {config.RUN_DTD} documents for {req.client}/{req.shortcode}")

    entry = await run_in_threadpool(process_group, root, docs, metas, req.client, req.shortcode, ids)
    if entry["failed"] != entry["documents"]:
        from .core.pipeline import save_done  # local import: keeps the top-level import list short

        done.setdefault(config.RUN_DTD, {}).setdefault(req.client, {})[req.shortcode] = entry
        await run_in_threadpool(save_done, root, done)
    return entry


_KIND_KEY = {"contrib": "report", "elements": "elements_report", "issues": "issues_csv"}


@app.get("/report")
def report(root: str, client: str, shortcode: str, kind: str = "contrib"):
    """Serves a previously generated report file (kind: contrib | elements | issues)."""
    if kind not in _KIND_KEY:
        raise HTTPException(400, f"kind must be one of {sorted(_KIND_KEY)}")
    _, _, _, done = _load(Path(root))
    entry = done.get(config.RUN_DTD, {}).get(client, {}).get(shortcode)
    if not entry:
        raise HTTPException(404, f"{client}/{shortcode} has not been generated yet")
    stored = entry.get(_KIND_KEY[kind])
    if not stored:
        raise HTTPException(404, f"{client}/{shortcode} has no {kind} report")
    path = resolve_meta_path(Path(root), stored)
    if not path or not path.exists():
        raise HTTPException(404, f"recorded report file is missing on disk: {path}")
    return FileResponse(path)
