"""Pattern statistics: reduces every file to an ordered PI-attr-value / PI-
position sequence per column (first / last-before / last contrib), groups
files by xref count, and finds the most common pattern (pattern-1) plus
what every other pattern differs by. Also renders the statistics, the
files-to-fix table, the cross-group check and the all-contribs PI-check
tables used inside the contrib report.
"""
from ..config import *        # noqa: F401,F403
from ..helpers.text import *  # noqa: F401,F403
from ..helpers.io import *    # noqa: F401,F403 (safe_name)
from .consistency import *    # noqa: F401,F403
from .render import render    # noqa: F401

# ----------------------------------------------------- pattern statistics

ROLES = [("first", "First contrib"), ("before", "Last before"), ("last", "Last contrib")]
KINDS = [("attr", "PI attr value"), ("pos", "PI position")]


def role_index(n: int, role: str):
    """
    Index of the contrib shown in a report column (None = no contrib there).
        n == 1 : only "last"
        n == 2 : "before" (index 0) + "last" (index 1)
        n >= 3 : first (0), before (n-2), last (n-1)
    """
    if role == "first":
        return 0 if n >= 3 else None
    if role == "before":
        return n - 2 if n >= 2 else None
    return n - 1 if n >= 1 else None


def pos_short(key: tuple) -> str:
    path, prev, nxt = key[0], key[1], key[2]
    if prev.startswith("xref@"):
        return f"after {prev[5:]} xref"
    if path.startswith("contrib/"):
        path = path[len("contrib/"):]
    a = "start" if prev == "^" else prev
    b = "end" if nxt == "$" else nxt
    return f"{path} [{a} -> {b}]"


def pattern_hits(gaps: list) -> list:
    """Gaps that carry a pistart and take part in the patterns (middle xrefs are skipped)."""
    return [g for g in gaps if g.pis and g.key[1] != "xref@middle"]


def pi_sequences(hits: list) -> dict:
    return {
        "attr": tuple(g.value for g in hits),
        "pos": tuple(pos_short(g.key) for g in hits),
    }


def tok_val(v: str) -> str:
    return v.replace("\xa0", "[nbsp]").replace(" ", "\u00b7") or "(empty)"


def tok(kind: str, x: str) -> str:
    if kind == "attr":
        return f'<code class="tok">{esc(tok_val(x))}</code>'
    return f'<code class="tok pos">{esc(x)}</code>'


def tok_plain(kind: str, x: str) -> str:
    return f"'{tok_val(x)}'" if kind == "attr" else x


def seq_diff(base: tuple, seq: tuple, kind: str):
    """Tokens of `seq` that differ from `base`, plus readable lines (html, plain)."""
    bad: set = set()
    html_l: list = []
    plain: list = []
    if len(base) == len(seq):  # same length: compare slot by slot (clearest for separators)
        for j, (x, y) in enumerate(zip(base, seq)):
            if x != y:
                bad.add(j)
                html_l.append(
                    f'<b class="k differs">differs</b> #{j + 1} expected {tok(kind, x)}, found {tok(kind, y)}'
                )
                plain.append(f"differs #{j + 1} expected {tok_plain(kind, x)}, found {tok_plain(kind, y)}")
        return bad, html_l, plain
    sm = difflib.SequenceMatcher(None, base, seq, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        exp = " ".join(tok(kind, x) for x in base[i1:i2])
        got = " ".join(tok(kind, x) for x in seq[j1:j2])
        pexp = " ".join(tok_plain(kind, x) for x in base[i1:i2])
        pgot = " ".join(tok_plain(kind, x) for x in seq[j1:j2])
        if tag == "replace":
            html_l.append(f'<b class="k differs">differs</b> expected {exp}, found {got}')
            plain.append(f"differs expected {pexp}, found {pgot}")
            bad.update(range(j1, j2))
        elif tag == "delete":
            html_l.append(f'<b class="k missing">missing</b> {exp}')
            plain.append(f"missing {pexp}")
        else:
            html_l.append(f'<b class="k extra">extra</b> {got}')
            plain.append(f"extra {pgot}")
            bad.update(range(j1, j2))
    return bad, html_l, plain


# contrib-count groups = the tabs of the contrib report
GROUPS = [
    ("g1", "1 contrib", ["last"]),
    ("g2", "2 contribs", ["before", "last"]),
    ("g3", "3+ contribs", ["first", "before", "last"]),
]
GROUP_LABEL = {g: label for g, label, _ in GROUPS}
ROLE_LABEL = dict(ROLES)


def group_of(n: int) -> str:
    return "g1" if n == 1 else "g2" if n == 2 else "g3"


def build_stats(rows: list[dict], roles: list) -> dict:
    """
    Statistics of ONE contrib-count group (all rows have the same kind of columns).
    Per column and kind: files split by xref group, then grouped by pattern.
    """
    total = len(rows)
    cards = {}
    for role in roles:
        for kind, _ in KINDS:
            by_x: dict = {}
            for r in rows:
                i = role_index(len(r["contribs"]), role)
                xk = r["xkeys"][i]
                r["xk"][role] = xk
                by_x.setdefault(xk, {}).setdefault(r["seqs"][i][kind], []).append(r)
            subgroups = []
            for xk in sorted(by_x):
                ordered = sorted(by_x[xk].items(), key=lambda kv: -len(kv[1]))  # stable on ties
                base = ordered[0][0]
                patterns = []
                for n, (seq, rs) in enumerate(ordered, 1):
                    for r in rs:
                        r["pat"][(role, kind)] = n
                    p = {"n": n, "seq": seq, "rows": rs, "bad": set(), "diff_html": [], "diff_plain": []}
                    if n > 1:
                        p["bad"], p["diff_html"], p["diff_plain"] = seq_diff(base, seq, kind)
                    patterns.append(p)
                subgroups.append(
                    {
                        "xk": xk,
                        "files": sum(len(p["rows"]) for p in patterns),
                        "patterns": patterns,
                        "base": base,
                    }
                )
            cards[(role, kind)] = {"subgroups": subgroups}
    return {"total": total, "roles": roles, "cards": cards}


def cross_group(stats_by: dict) -> list:
    """
    Is pattern-1 (the most common pattern) the same in every contrib-count group?
    One entry per column x kind x xref group that exists in at least two groups.
    """
    out = []
    for role, _ in ROLES:
        for kind, _ in KINDS:
            for xk in range(4):
                items = []
                for gid, _, _ in GROUPS:
                    st = stats_by.get(gid)
                    if not st or role not in st["roles"]:
                        continue
                    for sg in st["cards"][(role, kind)]["subgroups"]:
                        if sg["xk"] == xk:
                            items.append((gid, sg["base"], sg["files"]))
                if len(items) >= 2:
                    out.append(
                        {"role": role, "kind": kind, "xk": xk, "items": items,
                         "same": len({b for _, b, _ in items}) == 1}
                    )
    return out


def off_pattern_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if any(n not in (None, 1) for n in r["pat"].values())]


def row_id(docid: str) -> str:
    return "row-" + safe_name(docid)


def fid_of(r: dict) -> str:
    return r["file_id"] or r["docid"]


def copy_btn(rows: list, label: str = "Copy IDs") -> str:
    ids = "&#10;".join(esc_attr(fid_of(r)) for r in sorted(rows, key=lambda r: fid_of(r).lower()))
    return f'<button type="button" class="copy" data-ids="{ids}" title="copy the file ids to the clipboard">{label}</button>'


def file_rows(rows: list[dict]) -> str:
    return "".join(
        f'<div class="frow"><a href="#{esc(row_id(r["docid"]))}">{esc(fid_of(r))}</a>'
        f'<span class="did">{esc(r["docid"])}</span></div>'
        for r in sorted(rows, key=lambda r: fid_of(r).lower())
    )


def files_details(rows: list[dict], open_: bool) -> str:
    s = "" if len(rows) == 1 else "s"
    return (
        f'<details{" open" if open_ else ""}><summary>{len(rows)} file{s}</summary>'
        f'<div class="frow-tools">{copy_btn(rows)}</div>{file_rows(rows)}</details>'
    )


def _contrib_len(r: dict, role: str) -> int:
    i = role_index(len(r["contribs"]), role)
    return len(r["raws"][i]) if i is not None and i < len(r["raws"]) else 10**9


def sample_preview(role: str, p: dict) -> str:
    """
    Up to SAMPLES files of a pattern (shortest contrib first), differing pistarts in red.
    The first one is shown, a button cycles through the others.
    """
    picks = sorted(p["rows"], key=lambda r: (_contrib_len(r, role), fid_of(r).lower()))[:SAMPLES]
    parts = []
    for k, r in enumerate(picks):
        i = role_index(len(r["contribs"]), role)
        hits = r["hits"][i]
        ctx = Ctx()
        for j in p["bad"]:
            if j < len(hits):
                for pi in hits[j].pis:
                    ctx.pi_bad[id(pi)] = "differs from pattern-1"
        parts.append(
            f'<div class="pv"{"" if k == 0 else " hidden"}><span class="pv-l">preview - {esc(fid_of(r))}</span>'
            f'{render(r["contribs"][i], ctx)}</div>'
        )
    nxt = (
        f'<button type="button" class="pv-next">next sample (1/{len(picks)})</button>'
        if len(picks) > 1
        else ""
    )
    return f'<div class="pvs">{"".join(parts)}{nxt}</div>'


def render_card(role: str, kind: str, card: dict, total: int) -> str:
    out = []
    for sg in card["subgroups"]:
        size = sg["files"]
        body = []
        for p in sg["patterns"]:
            n, rs = p["n"], p["rows"]
            minor = n > 1
            items = "".join(
                f'<li class="{"bad" if i in p["bad"] else ""}">{tok(kind, x)}</li>'
                for i, x in enumerate(p["seq"])
            ) or '<li class="none">(no pistart)</li>'
            diff_html = "".join(f"<div>{d}</div>" for d in p["diff_html"])
            label = "differs from pattern-1" if minor else "most common"
            body.append(
                f'<div class="pat{" minor" if minor else ""}">'
                f'<div class="pat-h"><b>pattern-{n}</b><span class="cnt">{len(rs)}/{size}</span>'
                f'<span class="pct">{len(rs) / size * 100:.1f}%</span>'
                f'<span class="lbl">{label}</span></div>'
                f'<ol class="seq">{items}</ol>'
                + (f'<div class="diff">{diff_html}</div>' if diff_html else "")
                + sample_preview(role, p)
                + files_details(rs, open_=minor)
                + "</div>"
            )
        small = (
            f'<span class="small" title="fewer than {SMALL_GROUP} files: the percentages say little">'
            f"small group (n&lt;{SMALL_GROUP})</span>"
            if size < SMALL_GROUP
            else ""
        )
        out.append(
            f'<div class="xg" data-xk="{sg["xk"]}"><div class="xg-h">'
            f'<b>{esc(xref_label(sg["xk"]))}</b><span class="cnt">{size}/{total} files</span>{small}</div>'
            + "".join(body)
            + "</div>"
        )
    return "".join(out) or '<div class="none">-</div>'


KIND_SEG = (
    '<div class="seg kind" role="group" aria-label="Statistics kind">'
    '<button type="button" data-kind="both" class="on">Both</button>'
    '<button type="button" data-kind="attr">PI attr value</button>'
    '<button type="button" data-kind="pos">PI position</button></div>'
)


def stats_html(stats: dict, label: str) -> str:
    total, roles = stats["total"], stats["roles"]
    head = "".join(f"<th>{ROLE_LABEL[r]}</th>" for r in roles)
    rows = ""
    for kind, klabel in KINDS:
        tds = "".join(f'<td>{render_card(role, kind, stats["cards"][(role, kind)], total)}</td>' for role in roles)
        rows += f'<tr class="kr kr-{kind}"><th class="rl">{klabel}</th>{tds}</tr>'
    xks = sorted({sg["xk"] for c in stats["cards"].values() for sg in c["subgroups"]})
    chips = '<button type="button" data-x="all" class="on">All</button>' + "".join(
        f'<button type="button" data-x="{k}">{esc(xref_label(k))}</button>' for k in xks
    )
    cols = " + ".join(ROLE_LABEL[r] for r in roles)
    return (
        f'<details class="stats" open><summary>Statistics - {esc(label)} '
        '<span class="sub">pattern-N &nbsp;files with it / files in its xref group &nbsp;&middot;&nbsp; '
        '<code class="tok">\u00b7</code> = space, <code class="tok">[nbsp]</code> = non-breaking space'
        "</span></summary>"
        f'<div class="ctl">{KIND_SEG}<div class="seg xref" role="group" aria-label="xref group">'
        f'<span class="seg-l">xref</span>{chips}</div></div>'
        '<div class="legend" style="margin:8px 12px 0">'
        f"Only files with {esc(label)} are counted here. Columns: {cols}. "
        "Files are split by xref count (xref 0, 1, 2, 3+); only the first, last-before and last xref are "
        "looked at (\u201cafter first xref\u201d, \u201cafter last-before xref\u201d, \u201cafter last xref\u201d); "
        "middle xrefs are covered by the check on all contribs. "
        f"A pattern is compared only inside its xref group (group header = files in group / {total} in this tab). "
        "The preview is a sample file (shortest contrib first), differing pistarts in red."
        "</div>"
        f'<table class="stat"><tr><th></th>{head}</tr>{rows}</table></details>'
    )


def cross_html(cross: list) -> str:
    """Is the most common pattern the same in the 1 / 2 / 3+ tabs?"""
    if not cross:
        return ""
    diff = [c for c in cross if not c["same"]]
    same = [c for c in cross if c["same"]]

    def toks(kind, seq):
        return " ".join(tok(kind, x) for x in seq) or '<span class="none">(no pistart)</span>'

    trs = []
    for c in diff + same:
        head = (
            f'<td>{esc(ROLE_LABEL[c["role"]])}</td><td>{esc(dict(KINDS)[c["kind"]])}</td>'
            f'<td>{esc(xref_label(c["xk"]))}</td>'
        )
        if c["same"]:
            names = ", ".join(GROUP_LABEL[g] for g, _, _ in c["items"])
            trs.append(
                f'<tr class="cg-ok">{head}<td><span class="okmark">&#10003; same</span></td>'
                f'<td>{toks(c["kind"], c["items"][0][1])}<div class="cg-n">in {esc(names)}</div></td></tr>'
            )
        else:
            lines = "".join(
                f'<div class="cg-l"><a href="#tab={g}">{esc(GROUP_LABEL[g])}</a> '
                f'<span class="cg-n">({n} file{"" if n == 1 else "s"}'
                f'{", small group" if n < SMALL_GROUP else ""})</span> {toks(c["kind"], b)}</div>'
                for g, b, n in c["items"]
            )
            trs.append(f'<tr class="cg-bad">{head}<td><b class="k differs">differs</b></td><td>{lines}</td></tr>')
    return (
        f'<details class="stats"{" open" if diff else ""}><summary>Cross-group check - '
        f"{len(diff)} of {len(cross)} comparisons differ "
        '<span class="sub">is pattern-1 the same in the 1 / 2 / 3+ contribs tabs?</span></summary>'
        '<table class="fix"><tr><th>Column</th><th>Kind</th><th>xref group</th><th>Result</th>'
        "<th>Pattern-1 per tab</th></tr>" + "".join(trs) + "</table></details>"
    )


def fix_entries(stats: dict, gid: str) -> list:
    """Every off-pattern finding of one group: one entry per file x column x kind."""
    out: list = []
    role_order = [label for _, label in ROLES]
    for role in stats["roles"]:
        rlabel = ROLE_LABEL[role]
        for kind, klabel in KINDS:
            for sg in stats["cards"][(role, kind)]["subgroups"]:
                for p in sg["patterns"]:
                    if p["n"] == 1:
                        continue
                    for r in p["rows"]:
                        out.append(
                            {
                                "row": r,
                                "group": gid,
                                "role": rlabel,
                                "xref": xref_label(sg["xk"]),
                                "kind": klabel,
                                "pattern": p["n"],
                                "html": p["diff_html"],
                                "plain": p["diff_plain"],
                            }
                        )
    out.sort(key=lambda e: (fid_of(e["row"]).lower(), role_order.index(e["role"]), e["kind"]))
    return out


def fix_html(entries: list, label: str) -> str:
    if not entries:
        return (
            f'<div class="okbox">Files to fix ({esc(label)}): none - every file follows the most common '
            "PI attr value and PI position pattern of its xref group.</div>"
        )
    files = {e["row"]["docid"]: e["row"] for e in entries}
    rows = "".join(
        f'<tr><td class="fid"><a href="#{esc(row_id(e["row"]["docid"]))}">{esc(fid_of(e["row"]))}</a></td>'
        f'<td class="docid">{esc(e["row"]["docid"])}</td>'
        f'<td>{esc(e["role"])}</td><td>{esc(e["xref"])}</td><td>{esc(e["kind"])}</td>'
        f'<td>pattern-{e["pattern"]}</td><td class="det">{"<br>".join(e["html"])}</td></tr>'
        for e in entries
    )
    return (
        f'<details class="stats" open><summary>Files to fix - {len(entries)} finding(s) in {len(files)} file(s) '
        '<span class="sub">off-pattern PI attr value / PI position, by column</span></summary>'
        f'<div class="frow-tools" style="margin:8px 12px 0">{copy_btn(list(files.values()), f"Copy {len(files)} file IDs")}</div>'
        '<table class="fix"><tr><th>File ID</th><th>Docid</th><th>Column</th><th>xref group</th>'
        "<th>Kind</th><th>Pattern</th><th>What differs (vs pattern-1)</th></tr>"
        f"{rows}</table></details>"
    )


def allcheck_html(rows: list[dict]) -> str:
    """The 'same value, same position' check over EVERY contrib (middle contribs too)."""
    items = [(r, i) for r in rows for i in r["issues"]]
    if not items:
        return (
            '<details class="stats"><summary>PI check on all contribs '
            '<span class="sub">no inconsistencies</span></summary></details>'
        )
    shown = items[:300]
    trs = "".join(
        f'<tr><td class="fid"><a href="#{esc(row_id(r["docid"]))}">{esc(fid_of(r))}</a></td>'
        f'<td>#{i["n"]} of {len(r["contribs"])}</td><td class="det">{esc(i["text"])}</td></tr>'
        for r, i in shown
    )
    more = (
        f"<div class='legend' style='margin:0 12px 12px'>... +{len(items) - 300} more (see the csv)</div>"
        if len(items) > 300
        else ""
    )
    return (
        f'<details class="stats" open><summary>PI check on all contribs - {len(items)} issue(s) '
        '<span class="sub">same value, same position, compared with contribs of the same class and xref group '
        "over ALL files (middle contribs and middle xrefs included)</span></summary>"
        '<table class="fix"><tr><th>File ID</th><th>Contrib</th><th>Issue</th></tr>'
        f"{trs}</table>{more}</details>"
    )


def cell_tags(r: dict, role: str) -> str:
    out = []
    xk = r["xk"].get(role)
    if xk is not None:
        out.append(f'<span class="tag xref" title="xref group">{esc(xref_label(xk))}</span>')
    for kind, label in (("attr", "attr"), ("pos", "pos")):
        n = r["pat"].get((role, kind))
        if n is None:
            continue
        cls = "tag" if n == 1 else "tag bad"
        full = dict(KINDS)[kind]
        out.append(
            f'<span class="{cls}" title="{full} pattern (inside the xref group of this tab)">{label}: pattern-{n}</span>'
        )
    return f'<div class="tags">{"".join(out)}</div>' if out else ""



