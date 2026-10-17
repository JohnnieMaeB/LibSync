"""MARC 21 (MARCXML) to LibSync book dicts, shared by SRU and other drivers
that return MARC records."""

import re
import xml.etree.ElementTree as ET

MARC_NS = "{http://www.loc.gov/MARC21/slim}"
COVER_BY_ISBN = "https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg?default=false"


def _subfields(field: ET.Element, codes: str) -> list[str]:
    return [
        (sf.text or "").strip()
        for sf in field.findall(f"{MARC_NS}subfield")
        if sf.get("code") in codes and (sf.text or "").strip()
    ]


def _field(record: ET.Element, tag: str) -> ET.Element | None:
    return record.find(f"{MARC_NS}datafield[@tag='{tag}']")


def _fields(record: ET.Element, tag: str) -> list[ET.Element]:
    return record.findall(f"{MARC_NS}datafield[@tag='{tag}']")


def _clean(text: str) -> str:
    # ISBD punctuation MARC leaves at the end of subfields (" /", " :", ","),
    # keeping the period of a trailing initial ("Ursula K.").
    cleaned = re.sub(r"[\s/:;,=]+$", "", text).strip()
    if cleaned.endswith(".") and not re.search(r"[A-Z]\.$", cleaned):
        cleaned = cleaned[:-1].rstrip()
    return cleaned


def _year(record: ET.Element) -> int | None:
    control = record.find(f"{MARC_NS}controlfield[@tag='008']")
    if control is not None and control.text and len(control.text) >= 11:
        date1 = control.text[7:11]
        if date1.isdigit():
            return int(date1)
    for tag in ("264", "260"):
        field = _field(record, tag)
        if field is not None:
            match = re.search(r"\b(1[5-9]\d\d|20\d\d)\b", " ".join(_subfields(field, "c")))
            if match:
                return int(match.group(1))
    return None


def display_name(name: str) -> str:
    """MARC stores personal names inverted ("Weir, Andy", "Le Guin, Ursula
    K."); patrons read "Andy Weir". Leaves multi-comma forms alone."""
    parts = [p.strip() for p in name.split(",")]
    if len(parts) == 2 and all(parts):
        return f"{parts[1]} {parts[0]}"
    return name


def _koha_item_availability(record: ET.Element, items_tag: str | None) -> str | None:
    """Koha embeds its items in 952: $q = due date (checked out), $7 = not for
    loan, $1 = lost, $0 = withdrawn. Opt-in per server (`items_tag`), because
    952 is a local field other catalogs use differently — the Library of
    Congress's records carry one that has nothing to do with holdings. None
    when not enabled or the record carries no items."""
    if not items_tag:
        return None
    items = _fields(record, items_tag)
    if not items:
        return None
    for item in items:
        codes = {sf.get("code"): (sf.text or "").strip() for sf in item.findall(f"{MARC_NS}subfield")}
        if not codes.get("q") and codes.get("7", "0") in ("", "0") and codes.get("1", "0") in ("", "0") and codes.get("0", "0") in ("", "0"):
            return "available"
    return "checked out"


def record_to_book(record: ET.Element, url_template: str | None = None, items_tag: str | None = None) -> dict | None:
    title_field = _field(record, "245")
    if title_field is None:
        return None
    title = ": ".join(filter(None, (_clean(part) for part in _subfields(title_field, "ab"))))
    if not title:
        return None
    personal = _field(record, "100")
    corporate = _field(record, "110")
    if personal is not None:
        author = display_name(_clean(" ".join(_subfields(personal, "a"))))
    elif corporate is not None:
        author = _clean(" ".join(_subfields(corporate, "a")))
    else:
        author = _clean(" ".join(_subfields(title_field, "c"))) or "Unknown author"

    isbn = None
    for field in _fields(record, "020"):
        candidates = [re.sub(r"[^0-9Xx]", "", value) for value in _subfields(field, "a")]
        isbn = next((c for c in candidates if len(c) in (10, 13)), None)
        if isbn:
            break

    control_number = record.find(f"{MARC_NS}controlfield[@tag='001']")
    lccn_field = _field(record, "010")
    lccn = re.sub(r"\s+", "", " ".join(_subfields(lccn_field, "a"))) if lccn_field is not None else ""
    record_id = (control_number.text or "").strip() if control_number is not None else ""
    if url_template:
        url = url_template.format(id=record_id, lccn=lccn, isbn=isbn or "")
    elif lccn:
        url = f"https://lccn.loc.gov/{lccn}"
    else:
        url = None

    return {
        "title": title,
        "author": author,
        "first_publish_year": _year(record),
        "cover_url": COVER_BY_ISBN.format(isbn=isbn) if isbn else None,
        "url": url,
        "availability": _koha_item_availability(record, items_tag) or "in catalog",
    }


def parse_records(
    records: list[ET.Element], url_template: str | None = None, items_tag: str | None = None
) -> list[dict]:
    return [book for book in (record_to_book(r, url_template, items_tag) for r in records) if book]
