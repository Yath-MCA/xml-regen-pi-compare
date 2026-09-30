"""Per-document PI consistency check: every "gap" between siblings inside a
<contrib> is compared with the same gap in other contribs of the same class
(last / last-before / other) and xref group; disagreements become issues
and, in the preview HTML, red highlighting.
"""
from ..config import *       # noqa: F401,F403
from ..helpers.xml import *  # noqa: F401,F403 (local, pi_value)

# ----------------------------------------------------------- consistency check

@dataclass
class Gap:
    # (path, prev sibling, next sibling, occurrence); gaps right after an <xref>
    # of a contrib use (path, "xref@<role>", "", 0) instead - see xref_role()
    key: tuple
    value: str                 # concatenated pistart text at this position
    pis: list = field(default_factory=list)   # the PI elements sitting here
    parent: ET.Element | None = None
    before: ET.Element | None = None          # real child that follows (None = end)
    xref_i: int | None = None  # index of the <xref> directly before this gap (contrib level)


@dataclass
class Ctx:
    """Where to draw red marks while rendering one document."""
    pi_bad: dict = field(default_factory=dict)        # id(pi element) -> tooltip
    miss_before: dict = field(default_factory=dict)   # id(child) -> [tooltip]
    miss_end: dict = field(default_factory=dict)      # id(parent) -> [tooltip]


def xref_role(i: int, n: int) -> str:
    """Role of xref number i (0-based) of n: same idea as the contrib columns."""
    if i == n - 1:
        return "last"
    if i == n - 2:
        return "last-before"
    if i == 0:
        return "first"
    return "middle"


def analyze(contrib: ET.Element) -> list[Gap]:
    gaps: list[Gap] = []
    occ: Counter = Counter()

    def walk(el: ET.Element, path: str):
        prev = "^"
        pis: list = []
        vals: list = []
        xi = -1  # index of the last <xref> seen at contrib level

        def close(nxt: str, before):
            base = (path, prev, nxt)
            key = base + (occ[base],)
            occ[base] += 1
            xr = xi if (path == "contrib" and prev == "xref") else None
            gaps.append(Gap(key, "".join(vals), list(pis), el, before, xr))

        for kid in el:
            if kid.tag is PI:
                v = pi_value(kid)
                if v is not None:
                    pis.append(kid)
                    vals.append(v)
                continue
            if not isinstance(kid.tag, str):
                continue
            tag = local(kid.tag)
            close(tag, kid)
            if path == "contrib" and tag == "xref":
                xi += 1
            pis, vals, prev = [], [], tag
            walk(kid, f"{path}/{tag}")
        close("$", None)

    walk(contrib, "contrib")
    n_x = sum(1 for k in contrib if isinstance(k.tag, str) and local(k.tag) == "xref")
    for g in gaps:
        if g.xref_i is not None:
            g.key = ("contrib", "xref@" + xref_role(g.xref_i, n_x), "", 0)
    return gaps


def xref_key(contrib: ET.Element) -> int:
    """xref group of a contrib: 0, 1, 2 or 3 (= three or more xrefs)."""
    n = sum(1 for k in contrib if isinstance(k.tag, str) and local(k.tag) == "xref")
    return min(n, 3)


def xref_label(key: int) -> str:
    return "xref 3+" if key >= 3 else f"xref {key}"


def contrib_class(i: int, n: int) -> str:
    """last / last before / other - same idea as the report columns."""
    if i == n - 1:
        return "last"
    if i == n - 2:
        return "before"
    return "other"


CLASS_LABEL = {"last": "last", "before": "last before", "other": "other"}


def expected_values(items) -> dict:
    """
    items: (class key, gaps of one contrib). Returns
    (class key, position) -> most common value, only where the values disagree.
    """
    counts: dict = defaultdict(Counter)
    for cls, gaps in items:
        for g in gaps:
            counts[(cls, g.key)][g.value] += 1
    return {k: c.most_common(1)[0][0] for k, c in counts.items() if len(c) > 1}


def vis(v: str) -> str:
    return v.replace("\xa0", "<nbsp>")


def pos_label(key: tuple) -> str:
    path, prev, nxt = key[0], key[1], key[2]
    if prev.startswith("xref@"):
        return f"after {prev[5:]} xref"
    a = "start" if prev == "^" else prev
    b = "end" if nxt == "$" else nxt
    return f"{path} [{a} -> {b}]"


def build_ctx(gap_lists, classes, expected: dict):
    """Return (Ctx for rendering, list of issue dicts) for one document."""
    ctx, issues = Ctx(), []
    for n, (gaps, cls) in enumerate(zip(gap_lists, classes), 1):
        for g in gaps:
            exp = expected.get((cls, g.key))
            if exp is None or g.value == exp:
                continue
            if g.value == "":
                kind, what = "missing", f'expected "{vis(exp)}", found nothing'
            elif exp == "":
                kind, what = "unexpected", f'expected nothing, found "{vis(g.value)}"'
            else:
                kind, what = "different", f'expected "{vis(exp)}", found "{vis(g.value)}"'
            text = f"{pos_label(g.key)} ({CLASS_LABEL[cls[0]]}, {xref_label(cls[1])}): {what}"
            issues.append({"n": n, "kind": kind, "text": text})
            if g.pis:
                for p in g.pis:
                    ctx.pi_bad[id(p)] = text
            elif g.before is not None:
                ctx.miss_before.setdefault(id(g.before), []).append(text)
            else:
                ctx.miss_end.setdefault(id(g.parent), []).append(text)
    return ctx, issues


