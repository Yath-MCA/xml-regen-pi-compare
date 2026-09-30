"""Small, dependency-free string/HTML helpers used throughout the reports."""
from ..config import *  # noqa: F401,F403  (WS_RE, html, etc.)

# ----------------------------------------------------------------- rendering

def esc(s: str) -> str:
    return html.escape(s, quote=False)


def esc_attr(s: str) -> str:
    return html.escape(s, quote=True).replace("\n", "&#10;")


def chunk(s: str | None) -> str:
    """Collapse indentation whitespace; drop whitespace-only chunks between tags."""
    if not s or not s.strip(" \t\r\n"):
        return ""
    return esc(WS_RE.sub(" ", s))


def marker(tip: str) -> str:
    return f'<span class="pi miss" title="{esc_attr(tip)}">&#9888;</span>'

