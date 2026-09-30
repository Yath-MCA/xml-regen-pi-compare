"""Filesystem, JSON and report-directory helpers (no XML/report logic)."""
from .. import config           # module object - see default_report_root() below
from ..config import *  # noqa: F401,F403

# ----------------------------------------------------------------- io helpers

def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_name(s: str) -> str:
    return re.sub(r"[^\w.-]+", "_", s.strip()) or "unknown"


def ensure_dir(path: Path) -> Path:
    """Create path (and parents) if missing; return path. Call immediately before report writes."""
    path.mkdir(parents=True, exist_ok=True)
    return path



def rel_or_abs(target: Path, start: Path, *, for_html: bool = True) -> str:
    """Path from start to target for links/meta.

    Same drive/mount -> posix relative path.
    Cross-drive (Windows ValueError from os.path.relpath) -> absolute path;
    when for_html=True return file:// URI so report hrefs work across C:/D:.
    """
    target = Path(target).resolve()
    start = Path(start).resolve()
    try:
        return Path(os.path.relpath(target, start)).as_posix()
    except (ValueError, OSError):
        return target.as_uri() if for_html else target.as_posix()


# Back-compat alias (same behavior, HTML file:// on cross-drive)
link_path = rel_or_abs


def default_report_root() -> Path:
    """Documents/impact-support-log (or REPORT_ROOT when tests override it).

    Reads config.REPORT_ROOT through the module object (not the star-imported
    copy) so `extract_contrib.config.REPORT_ROOT = ...` (or `ec.REPORT_ROOT =
    ...`, since __init__ re-exports it) is honoured even though this function
    lives in a different module than the assignment.
    """
    if config.REPORT_ROOT is not None:
        return Path(config.REPORT_ROOT)
    return Path.home() / "Documents" / SUPPORT_LOG_NAME


# Set for the duration of one extract batch (run_contrib_extract / main).
# process_group reuses this so all shortcodes in a session share one folder.
_SESSION_REPORT_DIR: Path | None = None


def reset_session_report_dir() -> None:
    """Clear the session folder so the next batch gets a new timestamp."""
    global _SESSION_REPORT_DIR
    _SESSION_REPORT_DIR = None


def make_contrib_report_dir(timestamp: str | None = None) -> Path:
    """One timestamped report folder per extract session: {ts}_contrib_reports/JATS/."""
    global _SESSION_REPORT_DIR
    if timestamp is not None:
        report_dir = default_report_root() / f"{timestamp}_{REPORT_DIR}" / RUN_DTD
        ensure_dir(report_dir)
        _SESSION_REPORT_DIR = report_dir
        return report_dir
    if _SESSION_REPORT_DIR is not None:
        ensure_dir(_SESSION_REPORT_DIR)
        return _SESSION_REPORT_DIR
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = default_report_root() / f"{ts}_{REPORT_DIR}" / RUN_DTD
    ensure_dir(report_dir)
    _SESSION_REPORT_DIR = report_dir
    return report_dir

def resolve_meta_path(base: Path, stored: str | None) -> Path | None:
    """Resolve a meta-contrib report path (absolute preferred; relative = under project base)."""
    if not stored:
        return None
    p = Path(stored)
    return p if p.is_absolute() else (base / p)


def path_for_meta(path: Path) -> str:
    """Store absolute path strings in meta-contrib.json (reports leave the project tree)."""
    return str(path.resolve())


# ------------------------------------------------------------ locating files

def doc_folder(base: Path, docid: str, item: dict, meta: dict) -> Path:
    folder = item.get("folder")
    if folder:
        return base / folder
    return base / meta.get("dtd", "") / docid


def candidate_xml_files(base: Path, folder: Path, item: dict) -> list[Path]:
    found: list[Path] = []

    def add(p: Path):
        if (
            p.suffix.lower() == ".xml"
            and p.name.lower() not in SKIP_XML
            and p.exists()
            and p not in found
        ):
            found.append(p)

    # 1) anything documents.json already knows about
    for rel in (item.get("files") or {}).values():
        if isinstance(rel, str):
            add(base / rel)

    # 2) any other xml sitting in the folder
    if folder.is_dir():
        for p in sorted(folder.glob("*.xml")):
            add(p)

    return found


def extract_contrib_groups(folder: Path, base: Path, item: dict):
    """Return (source_path, raw_contrib_group_xml) or (None, None)."""
    for p in candidate_xml_files(base, folder, item):
        text = p.read_text(encoding="utf-8-sig", errors="replace")
        groups = CONTRIB_GROUP_RE.findall(text)
        if groups:
            return p, "\n\n".join(groups)
    return None, None


