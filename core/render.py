"""Turns a <contrib> element (+ an optional Ctx of what to flag) into the
preview HTML shown in the contrib report and the per-document preview page.
"""
from ..config import *         # noqa: F401,F403
from ..helpers.text import *   # noqa: F401,F403
from ..helpers.xml import *    # noqa: F401,F403
from .consistency import Ctx   # noqa: F401


def render_pi(pi: ET.Element, ctx: Ctx | None) -> str:
    value = pi_value(pi)
    if value is None:
        return ""
    out = esc(value)
    tip = ctx.pi_bad.get(id(pi)) if ctx else None
    if tip:
        return f'<span class="pi bad" title="{esc_attr(tip)}">{out or "&#9888;"}</span>'
    return f'<span class="pi">{out}</span>' if HIGHLIGHT_PI else out


def render(el: ET.Element, ctx: Ctx | None = None) -> str:
    out = [chunk(el.text)]
    for child in el:
        if child.tag is PI:
            out.append(render_pi(child, ctx))
        elif isinstance(child.tag, str):
            if ctx:
                out += [marker(t) for t in ctx.miss_before.get(id(child), [])]
            inner = render(child, ctx)
            wrap = INLINE_TAGS.get(local(child.tag))
            out.append(f"<{wrap}>{inner}</{wrap}>" if wrap else inner)
        out.append(chunk(child.tail))
    if ctx:
        out += [marker(t) for t in ctx.miss_end.get(id(el), [])]
    return "".join(out)


