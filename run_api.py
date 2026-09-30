from __future__ import annotations

import sys
from pathlib import Path

import uvicorn


PACKAGE_DIR = Path(__file__).resolve().parent
PARENT_DIR = PACKAGE_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))


if __name__ == "__main__":
    uvicorn.run("extract_contrib_package.api:app", host="127.0.0.1", port=8000, reload=True)
