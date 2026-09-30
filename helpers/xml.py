"""Extracting and parsing <contrib-group> XML out of a source document."""
from ..config import *  # noqa: F401,F403
from .io import *       # noqa: F401,F403 (candidate_xml_files not needed here, kept for symmetry)

# ------------------------------------------------------------------- parsing

def _fix_entity(m: re.Match) -> str:
    name = m.group(1)
    if name in XML_ENTITIES:
        return m.group(0)
    cp = name2codepoint.get(name)
    # unknown named entity (DTD not loaded) -> keep it visible, but well-formed
    return chr(cp) if cp else f"&amp;{name};"


def parse_group(group_xml: str) -> ET.Element:
    """Parse the extracted <contrib-group> text; returns a synthetic <root> wrapper."""
    wrapped = f"<root {NS_DECLS}>{NAMED_ENTITY_RE.sub(_fix_entity, group_xml)}</root>"
    # insert_pis=True keeps <?pistart ...?> in the tree (ElementTree drops them otherwise)
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_pis=True))
    return ET.fromstring(wrapped, parser=parser)


def tidy_raw(raw: str) -> str:
    """Remove the source indentation so each raw <contrib> reads from column 0."""
    lines = raw.split("\n")
    rest = [l for l in lines[1:] if l.strip()]
    indent = min((len(l) - len(l.lstrip(" \t")) for l in rest), default=0)
    out = [lines[0]] + [l[indent:] if l.strip() else "" for l in lines[1:]]
    return "\n".join(out).replace("\t", "  ")


def raw_contribs(group_xml: str) -> list[str]:
    return [tidy_raw(m) for m in CONTRIB_RE.findall(group_xml)]


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def pi_value(pi: ET.Element) -> str | None:
    """Text carried by a <?pistart xml:space="..."?>, or None for any other PI."""
    data = (pi.text or "").strip()
    if not data or data.split(None, 1)[0] != "pistart":
        return None
    m = PI_VALUE_RE.search(data)
    if not m:
        return None
    raw = m.group(1) if m.group(1) is not None else m.group(2)
    return html.unescape(raw)  # &#x00A0; -> nbsp (parser does not decode PI data)


