import re
from dataclasses import dataclass
from datetime import datetime

from selectolax.parser import HTMLParser

from app.parse.models import EvidenceLocation
from app.parse.text import normalize_text


@dataclass(frozen=True, slots=True)
class RepealRow:
    reference: str
    published_at: str
    title: str


@dataclass(frozen=True, slots=True)
class RepealEvidenceRow(RepealRow):
    evidence_text: str
    location: EvidenceLocation


_REFERENCE = (
    r"(?:RBI/(?:[A-Za-z]+/)?\d{4}(?:-\d{2,4})?/\d+|"
    r"[A-Za-z]{2,}(?:\.[A-Za-z][A-Za-z0-9-]*){2,}(?:\.No)?\.?\d+/"
    r"\d+(?:\.\d+)+/\d{4}-\d{2})"
)
_DATE = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2},\s+\d{4}"
)
_ROW = re.compile(
    rf"^\s*\d+[.)]?\s+(?P<reference>{_REFERENCE})\s+"
    rf"(?P<date>{_DATE})\s+(?P<title>.+?)\s*$",
    re.IGNORECASE,
)


def _date(value: str) -> str:
    for pattern in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"unsupported RBI date: {value}")


def parse_repeal_rows(text: str) -> tuple[RepealRow, ...]:
    rows: list[RepealRow] = []
    for line in text.splitlines():
        match = _ROW.match(line)
        if match is None:
            continue
        rows.append(
            RepealRow(
                reference=match.group("reference"),
                published_at=_date(match.group("date")),
                title=match.group("title"),
            )
        )
    return tuple(rows)


def parse_repeal_html(payload: bytes) -> tuple[RepealEvidenceRow, ...]:
    tree = HTMLParser(payload)
    rows: list[RepealEvidenceRow] = []
    cursor = 0
    for ordinal, row in enumerate(tree.css("tr"), start=1):
        row_text = normalize_text(row.text(separator=" ", strip=True))
        if not row_text:
            continue
        if cursor:
            cursor += 1
        start = cursor
        cursor += len(row_text)
        cells = [normalize_text(cell.text(separator=" ", strip=True)) for cell in row.css("td")]
        reference_index: int | None = None
        reference_match: re.Match[str] | None = None
        for index, cell in enumerate(cells):
            match = re.search(_REFERENCE, cell, re.IGNORECASE)
            if match is not None:
                reference_index = index
                reference_match = match
                break
        if reference_index is None or reference_match is None:
            continue
        following = cells[reference_index + 1 :]
        date_value = next(
            (
                match.group(0)
                for cell in following
                if (match := re.search(_DATE, cell, re.IGNORECASE))
            ),
            None,
        )
        if date_value is None or not following:
            continue
        title = next(
            (cell for cell in following if re.search(_DATE, cell, re.IGNORECASE) is None),
            "",
        )
        if not title:
            continue
        rows.append(
            RepealEvidenceRow(
                reference=reference_match.group(0),
                published_at=_date(date_value),
                title=title,
                evidence_text=row_text,
                location=EvidenceLocation(
                    char_start=start,
                    char_end=cursor,
                    dom_locator=f"tr:nth-of-type({ordinal})",
                ),
            )
        )
    return tuple(rows)
