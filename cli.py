"""Interactive command-line front end: prints the client/shortcode overview,
asks what to (re)generate, runs the pipeline for each pair, and prints the
final summary. `python -m extract_contrib` runs main()."""
import argparse
import subprocess
import sys

from .config import *           # noqa: F401,F403
from .helpers.io import *       # noqa: F401,F403
from .core.pipeline import *    # noqa: F401,F403

# ----------------------------------------------------------------- questions

def parse_choice(raw: str, options: list):
    """'1,3' or 'LWW plos' -> matching option names, None if anything is unknown."""
    lookup = {o.lower(): o for o in options}
    out = []
    for part in re.split(r"[,\s]+", raw.strip()):
        if not part:
            continue
        if part.isdigit() and 1 <= int(part) <= len(options):
            name = options[int(part) - 1]
        elif part.lower() in lookup:
            name = lookup[part.lower()]
        else:
            return None
        if name not in out:
            out.append(name)
    return out


def cnt(n: int, word: str = "doc") -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def status_note(done: dict, client: str, shortcode: str, docids: list) -> str:
    st, n = status_of(done, client, shortcode, docids)
    if st == "new":
        return "not filled"
    if st == "update":
        if n == 0:
            return "update (older script version, regenerate)"
        return f"update (+{n} new doc{'' if n == 1 else 's'})"
    e = done_entry(done, client, shortcode)
    bad = f", {e['failed']} failed" if e.get("failed") else ""
    return f"filled {e.get('generated_at', '')}{bad}"


def print_overview(docs: dict, metas: dict, index: dict, done: dict):
    """Unique counts Clients -> Shortcodes and whether each is already filled."""
    clients = sorted(index, key=str.lower)
    pairs = [(c, sc) for c in clients for sc in sorted(index[c], key=str.lower)]
    n_docs = sum(len(v) for scs in index.values() for v in scs.values())
    unique_sc = {sc for _, sc in pairs}
    states = Counter(status_of(done, c, sc, index[c][sc])[0] for c, sc in pairs)

    extra = "" if len(unique_sc) == len(pairs) else f"  ({len(unique_sc)} unique shortcode names)"
    print(f"\n{RUN_DTD} overview:  {len(clients)} clients | {len(pairs)} shortcodes | {n_docs} docs{extra}")
    print(
        f"  filled: {states['done']}  |  not filled: {states['new']}  |  "
        f"update (new docs): {states['update']}"
    )
    print()
    for c in clients:
        scs = index[c]
        filled = sum(status_of(done, c, sc, ids)[0] == "done" for sc, ids in scs.items())
        docs_c = sum(len(v) for v in scs.values())
        print(f"  {c}   {len(scs)} shortcodes, {docs_c} docs   ({filled}/{len(scs)} filled)")
        for sc in sorted(scs, key=str.lower):
            print(f"      {sc:<14}{len(scs[sc]):>6} docs   [{status_note(done, c, sc, scs[sc])}]")

    notes = []
    others = Counter(
        dtd_of(docs[d], m) or "?" for d, m in metas.items() if d in docs and dtd_of(docs[d], m) != RUN_DTD
    )
    if others:
        notes.append("not " + RUN_DTD + ": " + ", ".join(f"{k} {cnt(v)}" for k, v in sorted(others.items())))
    no_meta = sum(1 for d in docs if d not in metas)
    if no_meta:
        notes.append(f"{cnt(no_meta)} without a {META_NAME} entry")
    blank = sum(len(v) for sc_map in index.values() for sc, v in sc_map.items() if sc == "unknown")
    blank += sum(len(v) for c, sc_map in index.items() if c == "unknown" for v in sc_map.values())
    if blank:
        notes.append(f"{cnt(blank)} with a blank client or shortcode (grouped as 'unknown')")
    if notes:
        print("\n  ignored / check: " + "; ".join(notes))


def choose_clients(index: dict, done: dict) -> list:
    clients = sorted(index, key=str.lower)
    print(f"\n{RUN_DTD} clients:")
    for i, c in enumerate(clients, 1):
        scs = index[c]
        pending = sum(status_of(done, c, sc, ids)[0] != "done" for sc, ids in scs.items())
        n_docs = sum(len(v) for v in scs.values())
        tail = f"{pending} to generate" if pending else "all filled"
        print(f"  {i}) {c:<14}{len(scs):>4} shortcodes{n_docs:>8} docs   {tail}")
    while True:
        raw = input("Client (number/name, comma for several, 'all'): ").strip()
        if raw.lower() == "all":
            return clients
        picked = parse_choice(raw, clients)
        if picked:
            return picked
        print("  not recognised, try again")


def choose_shortcodes(clients: list, index: dict, done: dict) -> list:
    """Return the (client, shortcode) pairs to generate."""
    scs = None
    if len(clients) == 1:
        c = clients[0]
        scs = sorted(index[c], key=str.lower)
        print(f"\n{RUN_DTD} / {c} shortcodes:")
        for i, sc in enumerate(scs, 1):
            note = status_note(done, c, sc, index[c][sc])
            print(f"  {i}) {sc:<14}{len(index[c][sc]):>6} docs   [{note}]")
        prompt = (
            "Shortcode (number/name, comma for several; Enter = all not filled/updated; "
            "'all' = regenerate everything): "
        )
    else:
        prompt = (
            f"Shortcodes for {', '.join(clients)} (Enter = all not filled/updated; "
            "'all' = regenerate everything): "
        )

    while True:
        raw = input(prompt).strip()
        low = raw.lower()
        if low in ("", "new", "all"):
            pairs = []
            for c in clients:
                for sc in sorted(index[c], key=str.lower):
                    st, _ = status_of(done, c, sc, index[c][sc])
                    if low == "all" or st != "done":
                        pairs.append((c, sc))
            return pairs
        picked = parse_choice(raw, scs) if scs else None
        if picked:
            pairs = []
            for sc in picked:
                st, _ = status_of(done, clients[0], sc, index[clients[0]][sc])
                if st == "done":
                    ans = input(f"  {sc} is already filled. Regenerate? [y/N]: ").strip().lower()
                    if ans != "y":
                        continue
                pairs.append((clients[0], sc))
            return pairs
        print("  not recognised, try again")



# ---------------------------------------------------------------------- main

def ask_delay(label: str, default: float) -> float:
    while True:
        raw = input(f"{label} in seconds [{default:g}]: ").strip()
        if not raw:
            return default
        try:
            v = float(raw)
            if v >= 0:
                return v
        except ValueError:
            pass
        print("  enter a number of seconds (0 = no pause)")


def pause(seconds: float, why: str):
    if seconds > 0:
        print(f"  ... pausing {seconds:g}s before {why} (Ctrl+C to stop)")
        time.sleep(seconds)


def normalize_workflow(value: str) -> str:
    lookup = {
        "1": "extract",
        "extract": "extract",
        "2": "regen-pi",
        "regen": "regen-pi",
        "regen-pi": "regen-pi",
    }
    try:
        return lookup[value.strip().lower()]
    except KeyError as exc:
        raise ValueError("workflow must be 'extract' or 'regen-pi'") from exc


def build_regen_command(base: Path, client: str, shortcode: str,
                        config_path: Path, harness: Path,
                        docid: str | None = None, one_doc: bool = False) -> list[str]:
    script = Path(__file__).resolve().parent.parent / "regen_compare_v1.py"
    cmd = [
        sys.executable,
        str(script),
        str(base),
        str(config_path),
        "--client", client,
        "--shortcode", shortcode,
        "--harness", str(harness),
    ]
    if docid:
        cmd.extend(["--docid", docid])
    elif one_doc:
        cmd.append("--one-doc")
    return cmd


def choose_one(label: str, options: list[str], supplied: str | None = None) -> str:
    raw = supplied if supplied is not None else input(label).strip()
    picked = parse_choice(raw, options)
    if not picked or len(picked) != 1:
        raise ValueError(f"{label.rstrip(': ')} not recognised: {raw}")
    return picked[0]


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Extract contributors or regenerate contributor PIs.")
    ap.add_argument("--root", help="project folder containing documents.json and meta.json")
    ap.add_argument("--client")
    ap.add_argument("--shortcode", "--project-code", dest="shortcode")
    ap.add_argument("--workflow", help="extract or regen-pi")
    ap.add_argument("--config", help="PI config XML (regen-pi only)")
    ap.add_argument("--harness", help="folder holding extracted document directories (regen-pi only)")
    ap.add_argument("--docid", help="regen-pi: process only this document id")
    ap.add_argument("--one-doc", action="store_true",
                    help="regen-pi: process only the first matching docid for client+shortcode")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    base = Path(args.root or input("Project Folder: ").strip().strip('"'))
    if not (base / DOCS_NAME).exists() or not (base / META_NAME).exists():
        print(f"Missing {DOCS_NAME} or {META_NAME} in {base}")
        return 2

    docs = load_json(base / DOCS_NAME)
    metas = load_json(base / META_NAME)
    index = build_index(docs, metas)
    if not index:
        print(f"No {RUN_DTD} documents found in {META_NAME} (is the 'dtd' field filled in?)")
        return 2

    done = load_done(base)
    print_overview(docs, metas, index, done)

    clients = sorted(index, key=str.lower)
    try:
        client = choose_one("Client (number/name): ", clients, args.client)
        shortcodes = sorted(index[client], key=str.lower)
        shortcode = choose_one("Project code / shortcode (number/name): ", shortcodes, args.shortcode)
        if args.workflow is None:
            print("\nWorkflow:\n  1) extract\n  2) regen-pi")
        workflow = normalize_workflow(args.workflow or input("Workflow (number/name): "))
    except ValueError as exc:
        print(exc)
        return 2

    if workflow == "regen-pi":
        config_path = Path(args.config) if args.config else base / RUN_DTD / f"{client}_CONTRIB_PI_CONFIG.xml"
        harness = Path(args.harness) if args.harness else base / RUN_DTD
        if not config_path.exists():
            print(f"PI config not found: {config_path}")
            return 2
        script = Path(__file__).resolve().parent.parent / "regen_compare_v1.py"
        if not script.exists():
            print(f"Regeneration script not found: {script}")
            return 2
        return subprocess.run(
            build_regen_command(
                base, client, shortcode, config_path, harness,
                docid=args.docid, one_doc=bool(args.one_doc),
            ),
            check=False,
        ).returncode

    ids = index[client][shortcode]
    print(f"\n=== {RUN_DTD} / {client} / {shortcode} ({cnt(len(ids))}) ===")
    reset_session_report_dir()
    try:
        entry = process_group(base, docs, metas, client, shortcode, ids)
    except KeyboardInterrupt:
        print("\nStopped by user")
        return 130
    except Exception as exc:
        print(f"[ERROR] {client}/{shortcode}: {exc}")
        traceback.print_exc()
        return 1

    if entry["failed"] == entry["documents"]:
        print(f"[SKIP RECORD] every document failed, {shortcode} not marked as filled")
    else:
        done.setdefault(RUN_DTD, {}).setdefault(client, {})[shortcode] = entry
        save_done(base, done)

    print("\nSummary:")
    print(
        f"  {client} / {shortcode:<12} {entry.get('documents', 0):>5} docs  "
        f"{entry.get('failed', 0):>3} failed  {entry.get('off_pattern_files', 0):>3} off-pattern  "
        f"-> {entry.get('report', '')}"
    )
    print(f"Progress saved in {DONE_NAME}")
    return 0


if __name__ == "__main__":
    main()
