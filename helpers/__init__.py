"""Helper layer: text/HTML-escaping utilities, filesystem + JSON I/O, XML
parsing, and the shared HTML page template. No document/report logic lives
here - see extract_contrib.core for that.
"""
from .text import *      # noqa: F401,F403
from .io import *        # noqa: F401,F403
from .xml import *       # noqa: F401,F403
from .template import *  # noqa: F401,F403
