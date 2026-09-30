"""
extract_contrib
===============
Package form of the original extract_contrib.py, split into a `helpers`
layer (I/O, XML parsing, string/HTML utilities, the shared page template)
and a `core` layer (consistency checking, pattern statistics, the two
reports, the batch pipeline), plus `cli.py` (the interactive prompt) and
`api.py` (an optional FastAPI wrapper - see api.py's docstring).

Backward compatibility
-----------------------
Everything the original single-file script exposed at module level (RUN_DTD,
load_json, parse_group, page, build_report, process_group, main, ...) is
still available directly on this package, so existing code that does

    import extract_contrib as ec
    ec.page(...)
    ec.RUN_DTD

keeps working unchanged - `regen_compare.py` in particular relies on this.
"""
from .config import *         # noqa: F401,F403
from .helpers import *        # noqa: F401,F403
from .core import *           # noqa: F401,F403
from .cli import *            # noqa: F401,F403

__all__ = [n for n in dir() if not n.startswith("_")]
