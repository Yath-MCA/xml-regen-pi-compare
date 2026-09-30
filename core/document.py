"""Reads and parses ONE document into the `row` dict every report builder
consumes (never raises - problems are recorded in row["error"])."""
from ..config import *       # noqa: F401,F403
from ..helpers.io import *   # noqa: F401,F403
from ..helpers.xml import *  # noqa: F401,F403
from .consistency import *   # noqa: F401,F403
from .patterns import *      # noqa: F401,F403

# ------------------------------------------------------------- one document

def read_doc(base: Path, docid: str, item: dict, meta: dict) -> dict:
    """Read + parse one document. Never raises; problems go into row['error']."""
    row = {
        "docid": docid,
        "file_id": meta.get("file-id", ""),
        "folder": doc_folder(base, docid, item, meta),
        "preview_rel": "",
        "cells": None,
        "error": None,
        "contribs": None,
        "raws": [],
        "gaps": [],
        "raw_group": "",
        "group_root": None,
        "issues": [],
        "xkeys": [],
        "cmp_cls": [],
        "xk": {},
        "hits": [],
        "seqs": [],
        "pat": {},
    }
    folder = row["folder"]
    if not folder.is_dir():
        row["error"] = f"folder not found: {folder}"
        print(f"[MISSING] {docid} - {row['error']}")
        return row

    src, raw = extract_contrib_groups(folder, base, item)
    if not raw:
        row["error"] = "no <contrib-group> found in any xml in folder"
        # Skip this doc only; shortcode run continues with remaining docs
        print(f"[NO CONTRIB] {docid} - {row['error']} (skip doc; continue)")
        return row

    try:
        group_root = parse_group(raw)
        contribs = list(group_root.iter("contrib"))
    except ET.ParseError as e:
        row["error"] = f"contrib-group parse error: {e}"
        print(f"[FAILED] {docid} - {row['error']}")
        return row

    if not contribs:
        row["error"] = "<contrib-group> has no <contrib>"
        print(f"[EMPTY] {docid} - {row['error']}")
        return row

    raws = raw_contribs(raw)
    if len(raws) != len(contribs):
        print(f"[WARN] {docid} - raw/parsed contrib count differs ({len(raws)} vs {len(contribs)})")

    row["contribs"] = contribs
    row["raws"] = raws
    row["raw_group"] = raw
    row["group_root"] = group_root
    row["src"] = src.name
    row["gaps"] = [analyze(c) for c in contribs]
    n = len(contribs)
    row["xkeys"] = [xref_key(c) for c in contribs]
    row["cmp_cls"] = [(contrib_class(i, n), row["xkeys"][i]) for i in range(n)]
    row["hits"] = [pattern_hits(g) for g in row["gaps"]]
    row["seqs"] = [pi_sequences(h) for h in row["hits"]]
    return row


