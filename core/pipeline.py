"""Runs one client+shortcode end to end (process_group), and the
meta-contrib.json bookkeeping (build_index / load_done / save_done /
status_of) that decides what still needs generating.
"""
from ..config import *              # noqa: F401,F403
from ..helpers.io import *          # noqa: F401,F403
from .consistency import *          # noqa: F401,F403
from .patterns import *             # noqa: F401,F403
from .elements_report import *      # noqa: F401,F403
from .contrib_report import *       # noqa: F401,F403
from .document import read_doc      # noqa: F401

# ------------------------------------------------------ one client + shortcode

def process_group(base: Path, docs: dict, metas: dict, client: str, shortcode: str, docids: list) -> dict:
    """Build per-doc outputs, the contrib report, the element list and the issues csv."""
    # Also recreated immediately before each report write via ensure_dir(out.parent).
    report_dir = make_contrib_report_dir()
    ensure_dir(report_dir)
    print(f"[PATHS] report_dir={report_dir}")

    rows = []
    n_docs = len(docids)
    for di, d in enumerate(docids, 1):
        pending_docs = n_docs - di
        print(
            f"[DOC] {client}/{shortcode}  {di}/{n_docs}  "
            f"current={d}  pending_docs={pending_docs}",
            flush=True,
        )
        rows.append(read_doc(base, d, docs[d], metas[d]))
    good = [r for r in rows if r["contribs"]]

    expected = expected_values(
        (cls, gl) for r in good for cls, gl in zip(r["cmp_cls"], r["gaps"])
    )
    # one statistics set per contrib-count group (= one tab of the report)
    stats_by: dict = {}
    entries: list = []
    for gid, _, roles in GROUPS:
        rs = [r for r in good if group_of(len(r["contribs"])) == gid]
        if rs:
            stats_by[gid] = build_stats(rs, roles)
            entries += fix_entries(stats_by[gid], gid)
    cross = cross_group(stats_by)

    inv = build_inventory(good) if good else None
    elements_out = None
    if inv:
        elements_out = build_elements_report(client, shortcode, inv, report_dir)
        print(f"[ELEMENTS] {elements_out} ({len(inv['elems'])} elements, "
              f"{flagged_count(inv)} flagged)")

    total_issues = 0
    for r in good:
        ctx, issues = build_ctx(r["gaps"], r["cmp_cls"], expected)
        r["issues"] = issues
        write_doc_outputs(r, client, shortcode, ctx, issues)
        r["cells"] = pick_cells(r["contribs"], r["raws"], ctx)
        r["preview_rel"] = rel_or_abs(r["folder"] / OUT_HTML, report_dir, for_html=True)
        total_issues += len(issues)
        tag = f", {len(issues)} PI issue(s)" if issues else ""
        print(f"[OK] {r['docid']} ({r['src']}) - {len(r['contribs'])} contribs{tag}")

    out, n_off = build_report(
        client, shortcode, rows, report_dir, stats_by, entries, cross,
        elements_out.name if elements_out else None,
    )
    print(f"[REPORT] {out} ({len(rows)} docs, {n_off} off-pattern)")
    csv_out = write_issues_csv(client, shortcode, entries, good, report_dir)
    print(f"[ISSUES CSV] {csv_out}")
    print_top_issues(entries, good, cross)

    return {
        "generated_at": now(),
        "version": SCRIPT_VERSION,
        "report": path_for_meta(out),
        "elements_report": path_for_meta(elements_out) if elements_out else None,
        "issues_csv": path_for_meta(csv_out),
        "unique_elements": len(inv["elems"]) if inv else 0,
        "flagged_elements": flagged_count(inv) if inv else 0,
        "documents": len(rows),
        "failed": len(rows) - len(good),
        "off_pattern_files": n_off,
        "pattern_findings": len(entries),
        "cross_group_differences": sum(1 for c in cross if not c["same"]),
        "groups": group_summary(good),
        "consistency_issues": total_issues,
        "docids": {
            r["docid"]: {
                "file-id": r["file_id"],
                "contribs": len(r["contribs"]) if r["contribs"] else 0,
                "status": "ok" if r["contribs"] else f"error: {r['error']}",
            }
            for r in rows
        },
    }



# ------------------------------------------------ what is in meta / what is done

def dtd_of(item: dict, meta: dict) -> str:
    return meta.get("dtd") or item.get("folder", "").split("/", 1)[0]


def build_index(docs: dict, metas: dict) -> dict:
    """{client: {shortcode: [docid, ...]}} for RUN_DTD documents only."""
    index: dict = {}
    for docid, meta in metas.items():
        item = docs.get(docid)
        if item is None or dtd_of(item, meta) != RUN_DTD:
            continue
        client = meta.get("client") or "unknown"
        shortcode = meta.get("project-shortcode") or "unknown"
        index.setdefault(client, {}).setdefault(shortcode, []).append(docid)
    return index


def load_done(base: Path) -> dict:
    p = base / DONE_NAME
    return load_json(p) if p.exists() else {}


def save_done(base: Path, data: dict):
    p = base / DONE_NAME
    tmp = p.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, p)  # never leaves a half written file behind


def done_entry(done: dict, client: str, shortcode: str):
    return done.get(RUN_DTD, {}).get(client, {}).get(shortcode)


def status_of(done: dict, client: str, shortcode: str, docids: list):
    """('new'|'update'|'done', number of docids not recorded yet)"""
    e = done_entry(done, client, shortcode)
    if not e:
        return "new", 0
    seen = e.get("docids", {})
    fresh = [d for d in docids if d not in seen]
    if fresh:
        return "update", len(fresh)
    if e.get("version") != SCRIPT_VERSION:  # generated by an older script version
        return "update", 0
    return "done", 0


