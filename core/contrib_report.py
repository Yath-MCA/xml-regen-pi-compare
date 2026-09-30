"""Assembles the contrib report itself: per-document preview/raw-XML pages,
the tabbed (1 / 2 / 3+ contribs) HTML report, the issues.csv export, and the
console summary. Depends on core.patterns for the statistics/pattern cards.
"""
from ..config import *            # noqa: F401,F403
from ..helpers.text import *      # noqa: F401,F403
from ..helpers.io import *        # noqa: F401,F403
from ..helpers.template import *  # noqa: F401,F403
from .consistency import Ctx      # noqa: F401
from .render import render        # noqa: F401
from .patterns import *           # noqa: F401,F403

def write_doc_outputs(row: dict, client: str, shortcode: str, ctx: Ctx, issues: list):
    folder: Path = row["folder"]
    (folder / OUT_XML).write_text(row["raw_group"], encoding="utf-8")

    by_n: dict = defaultdict(list)
    for i in issues:
        by_n[i["n"]].append(i["text"])

    trs = []
    for n, c in enumerate(row["contribs"], 1):
        if by_n[n]:
            chk = "<ul>" + "".join(f"<li>{esc(t)}</li>" for t in by_n[n]) + "</ul>"
        else:
            chk = '<span class="ok">OK</span>'
        trs.append(f'<tr><td>{n}</td><td>{render(c, ctx)}</td><td class="chk">{chk}</td></tr>')

    body = (
        '<table class="files"><tr><th>#</th><th>Contrib</th><th>PI check (all contribs)</th></tr>'
        + "".join(trs)
        + "</table>"
    )
    chips = [
        ("Docid", row["docid"], ""),
        ("Client", client, ""),
        ("Shortcode", shortcode, ""),
        ("Contribs", len(row["contribs"]), ""),
        issue_chip(len(issues)),
        ("Script version", f"v{SCRIPT_VERSION}", ""),
        ("Generated", now(), ""),
    ]
    title = row["file_id"] or row["docid"]
    (folder / OUT_HTML).write_text(page(title, chips, body), encoding="utf-8")


def pick_cells(contribs, raws, ctx: Ctx) -> list:
    """
    first / last-before / last as (preview_html, raw_xml) pairs (see role_index),
    None where the document has no contrib for that column.
    """
    n = len(contribs)

    def cell(i):
        raw = raws[i] if i < len(raws) else "(raw xml not available)"
        return render(contribs[i], ctx), raw

    out = []
    for role, _ in ROLES:
        i = role_index(n, role)
        out.append(cell(i) if i is not None else None)
    return out


def has_issue(r: dict) -> bool:
    return bool(r["issues"]) or any(n not in (None, 1) for n in r["pat"].values())


def file_tr(r: dict, roles: list) -> str:
    fid = esc(fid_of(r))
    if r["preview_rel"]:
        fid = f'<a href="{esc(r["preview_rel"])}">{fid}</a>'
    if len(r["contribs"]) >= 3:
        fid += f' <span class="cb" title="number of contribs">{len(r["contribs"])} contribs</span>'
    if r["issues"]:
        tips = [i["text"] for i in r["issues"][:8]]
        if len(r["issues"]) > 8:
            tips.append(f"... +{len(r['issues']) - 8} more")
        fid += (
            f' <span class="badge" title="{esc_attr("PI check on all contribs:" + chr(10) + chr(10).join(tips))}">'
            f'&#9888; {len(r["issues"])}</span>'
        )
    role_idx = {role: k for k, (role, _) in enumerate(ROLES)}
    cells = "".join(
        (
            f'<td><div class="v-preview">{c[0]}</div>'
            f'<div class="v-raw"><pre class="raw">{esc(c[1])}</pre></div>'
            f"{cell_tags(r, role)}</td>"
        )
        if (c := r["cells"][role_idx[role]])
        else "<td class=\"na\">-</td>"
        for role in roles
    )
    flag = " data-issue" if has_issue(r) else ""
    s = esc_attr(f'{fid_of(r)} {r["docid"]}'.lower())
    return (
        f'<tr id="{esc(row_id(r["docid"]))}" data-row data-s="{s}"{flag}>'
        f'<td class="fid">{fid}</td><td class="docid">{esc(r["docid"])}</td>{cells}</tr>'
    )


def files_table(rows: list, roles: list) -> str:
    rows = sorted(rows, key=lambda r: (0 if has_issue(r) else 1, fid_of(r).lower()))
    head = "".join(f"<th>{ROLE_LABEL[r]}</th>" for r in roles)
    return (
        '<div class="emptymsg" style="display:none">No files match the filter.</div>'
        f'<table class="files"><tr><th>File ID</th><th>Docid</th>{head}</tr>'
        + "".join(file_tr(r, roles) for r in rows)
        + "</table>"
    )


def failed_table(rows: list) -> str:
    trs = "".join(
        f'<tr id="{esc(row_id(r["docid"]))}" data-row data-issue data-s="{esc_attr((fid_of(r) + " " + r["docid"]).lower())}">'
        f'<td class="fid">{esc(fid_of(r))}</td><td class="docid">{esc(r["docid"])}</td>'
        f'<td class="err">{esc(r["error"] or "")}</td></tr>'
        for r in sorted(rows, key=lambda r: fid_of(r).lower())
    )
    return (
        '<div class="emptymsg" style="display:none">No files match the filter.</div>'
        '<table class="files"><tr><th>File ID</th><th>Docid</th><th>Error</th></tr>' + trs + "</table>"
    )


def pane_html(gid: str, label: str, on: bool, rows: list, roles: list, stats, entries: list) -> str:
    off = len(off_pattern_rows(rows))
    n_pi = sum(len(r["issues"]) for r in rows)
    small = (
        f' <span class="small" title="fewer than {SMALL_GROUP} files">small group (n&lt;{SMALL_GROUP})</span>'
        if len(rows) < SMALL_GROUP
        else ""
    )
    head = (
        f'<div class="ghead"><b>{esc(label)}</b> &middot; {len(rows)} files &middot; '
        f"{off} off-pattern &middot; {n_pi} PI issue(s) on all contribs{small}</div>"
    )
    body = (
        head
        + fix_html(entries, label)
        + stats_html(stats, label)
        + allcheck_html(rows)
        + files_table(rows, roles)
    )
    return (
        f'<section class="pane{" on" if on else ""}" id="pane-{gid}" data-pane="{gid}" data-xref="all" '
        f'role="tabpanel" aria-labelledby="tab-{gid}">{body}</section>'
    )


def build_report(client: str, shortcode: str, rows: list[dict], report_dir: Path, stats_by: dict,
                 entries: list, cross: list, elements_file=None):
    good = [r for r in rows if r["contribs"]]
    failed = [r for r in rows if not r["contribs"]]
    by_g = {gid: [r for r in good if group_of(len(r["contribs"])) == gid] for gid, _, _ in GROUPS}
    ent_g = {gid: [e for e in entries if e["group"] == gid] for gid, _, _ in GROUPS}

    def n_bad(rs):
        return sum(1 for r in rs if has_issue(r))

    # default tab: the first group that has findings, else the biggest one
    shown = [g for g, _, _ in GROUPS if by_g[g]]
    default = next((g for g in shown if n_bad(by_g[g])), None) or max(shown, key=lambda g: len(by_g[g]), default=None)
    if default is None and failed:
        default = "gf"

    tabs, panes = [], []
    for gid, label, roles in GROUPS:
        rs = by_g[gid]
        if not rs:
            continue
        w = n_bad(rs)
        tabs.append(
            f'<button type="button" role="tab" id="tab-{gid}" data-tab="{gid}" aria-controls="pane-{gid}" '
            f'aria-selected="{"true" if gid == default else "false"}">{esc(label)} '
            f'<span class="n">{len(rs)}</span>'
            + (f'<span class="w" title="files with findings">&#9888;{w}</span>' if w else "")
            + "</button>"
        )
        panes.append(pane_html(gid, label, gid == default, rs, roles, stats_by[gid], ent_g[gid]))
    if failed:
        tabs.append(
            f'<button type="button" role="tab" id="tab-gf" data-tab="gf" aria-controls="pane-gf" '
            f'aria-selected="{"true" if default == "gf" else "false"}">Failed '
            f'<span class="n">{len(failed)}</span></button>'
        )
        panes.append(
            f'<section class="pane{" on" if default == "gf" else ""}" id="pane-gf" data-pane="gf" '
            f'role="tabpanel" aria-labelledby="tab-gf"><div class="ghead"><b>Failed documents</b> &middot; '
            f"{len(failed)} without a usable contrib-group</div>{failed_table(failed)}</section>"
        )

    nav = (
        f'<nav class="tabs" role="tablist" data-default="{default or ""}" aria-label="Contribs per file">'
        + "".join(tabs)
        + '<span class="tools"><input type="search" id="q" placeholder="search file id / docid" '
        'aria-label="search files"> <label><input type="checkbox" id="onlyIssues"> '
        "Only files with issues</label></span></nav>"
        if tabs
        else ""
    )
    body = cross_html(cross) + nav + "".join(panes)

    off = off_pattern_rows(good)
    n_issues = sum(len(r["issues"]) for r in good)
    n_cross = sum(1 for c in cross if not c["same"])
    chips = [
        ("Client", client, ""),
        ("Project shortcode", shortcode, ""),
        ("Documents", len(rows), ""),
        ("Contribs checked", sum(len(r["contribs"]) for r in good), ""),
        ("Off-pattern files", f"{len(off)}/{len(good)}", "warn" if off else "good"),
        issue_chip(n_issues),
    ]
    if cross:
        chips.append(("Cross-group differences", n_cross, "warn" if n_cross else "good"))
    if failed:
        chips.append(("Failed docs", len(failed), "warn"))
    chips.append(("Script version", f"v{SCRIPT_VERSION}", ""))
    chips.append(("Generated", now(), ""))

    out = report_dir / f"{safe_name(client)}_{safe_name(shortcode)}_contrib_v{SCRIPT_VERSION}.html"
    ensure_dir(out.parent)  # recreate if missing at write time
    out.write_text(
        page(
            f"{client} / {shortcode} - contrib report",
            chips,
            body,
            toggle=True,
            links=[("Element list", elements_file)] if elements_file else None,
        ),
        encoding="utf-8",
    )
    return out, len(off)


def write_issues_csv(client: str, shortcode: str, entries: list, good: list, report_dir: Path) -> Path:
    """All findings of the contrib report, one line each (opens in Excel)."""
    out = report_dir / f"{safe_name(client)}_{safe_name(shortcode)}_issues_v{SCRIPT_VERSION}.csv"
    ensure_dir(out.parent)  # recreate if missing at write time
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["file_id", "docid", "contrib_group", "contribs", "check", "column", "xref_group",
                    "kind", "pattern", "detail"])
        for e in entries:
            r = e["row"]
            w.writerow(
                [r["file_id"], r["docid"], GROUP_LABEL[e["group"]], len(r["contribs"]), "pattern", e["role"],
                 e["xref"], e["kind"], f"pattern-{e['pattern']}", " | ".join(e["plain"])]
            )
        for r in sorted(good, key=lambda r: fid_of(r).lower()):
            for i in r["issues"]:
                w.writerow([r["file_id"], r["docid"], GROUP_LABEL[group_of(len(r["contribs"]))],
                            len(r["contribs"]), "all-contribs", f"contrib #{i['n']}", "", i["kind"], "",
                            i["text"]])
    return out


def group_summary(good: list) -> dict:
    """{group: {files, off_pattern, pi_issues}} for meta-contrib.json and the console."""
    out = {}
    for gid, _, _ in GROUPS:
        rs = [r for r in good if group_of(len(r["contribs"])) == gid]
        out[gid] = {
            "label": GROUP_LABEL[gid],
            "files": len(rs),
            "off_pattern": len(off_pattern_rows(rs)),
            "pi_issues": sum(len(r["issues"]) for r in rs),
        }
    return out


def print_top_issues(entries: list, good: list, cross: list, limit: int = 5):
    gs = group_summary(good)
    print("[GROUPS] " + " | ".join(
        f"{g['label']}: {g['files']} files, {g['off_pattern']} off-pattern" for g in gs.values() if g["files"]
    ))
    n_cross = sum(1 for c in cross if not c["same"])
    if n_cross:
        print(f"[CROSS-GROUP] {n_cross} of {len(cross)} pattern-1 comparisons differ between the tabs")
    n_all = sum(len(r["issues"]) for r in good)
    if not entries and not n_all:
        print("[ISSUES] none")
        return
    n_files = len({e["row"]["docid"] for e in entries})
    print(f"[ISSUES] {len(entries)} pattern finding(s) in {n_files} file(s); {n_all} PI issue(s) on all contribs")
    for e in entries[:limit]:
        r = e["row"]
        detail = e["plain"][0] if e["plain"] else ""
        print(f"    {fid_of(r)} ({GROUP_LABEL[e['group']]}): {e['role']} / {e['xref']} / {e['kind']} - {detail}")
    if len(entries) > limit:
        print(f"    ... +{len(entries) - limit} more (see the report / csv)")


