import re
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RepealRow:
    reference: str
    published_at: str
    title: str


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
