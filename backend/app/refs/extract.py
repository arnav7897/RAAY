import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ReferenceKind(StrEnum):
    RBI = "RBI"
    DEPARTMENT = "DEPARTMENT"
    TITLED = "TITLED"
    DATED_CIRCULAR = "DATED_CIRCULAR"
    IBID = "IBID"


@dataclass(frozen=True, slots=True)
class ReferenceCandidate:
    raw: str
    kind: ReferenceKind
    char_start: int
    char_end: int
    title: str | None = None
    published_at: str | None = None
    target_clause: str | None = None


_RBI_REFERENCE = re.compile(
    r"\bRBI/(?:[A-Za-z]+/)?\d{4}(?:-\d{2,4})?/\d+\b",
    re.IGNORECASE,
)
_DEPARTMENT_REFERENCE = re.compile(
    r"\b[A-Za-z]{2,}(?:\.[A-Za-z][A-Za-z0-9-]*){2,}"
    r"(?:\.No)?\.?\d+/\d+(?:\.\d+)+/\d{4}-\d{2}\b",
    re.IGNORECASE,
)
_TITLE_REFERENCE = re.compile(
    r"\bMaster Directions?\s*[-–—]?\s*.+?Directions,\s*\d{4}",
    re.IGNORECASE,
)
_DATE_TEXT = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2},\s+\d{4}"
)
_DATED_CIRCULAR = re.compile(rf"\bthe circular dated\s+(?P<date>{_DATE_TEXT})", re.IGNORECASE)
_DATE_AFTER_TITLE = re.compile(rf"^\s*dated\s+(?P<date>{_DATE_TEXT})", re.IGNORECASE)
_CLAUSE_REFERENCE = re.compile(
    r"\b(?:paragraph|para(?:graph)?|clause)\s+"
    r"(?P<clause>\d+(?:\.\d+)*(?:\s*\([A-Za-z0-9ivxIVX]+\))*)",
    re.IGNORECASE,
)
_IBID = re.compile(r"\bibid\.?", re.IGNORECASE)


def _date(value: str) -> str | None:
    for pattern in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            continue
    return None


def _target_clause(text: str, title_start: int) -> str | None:
    prefix = text[max(0, title_start - 160) : title_start]
    matches = list(_CLAUSE_REFERENCE.finditer(prefix))
    if not matches:
        return None
    return re.sub(r"\s+", "", matches[-1].group("clause"))


def extract_references(text: str) -> tuple[ReferenceCandidate, ...]:
    references: list[ReferenceCandidate] = []
    occupied: list[tuple[int, int]] = []

    for pattern, kind in (
        (_RBI_REFERENCE, ReferenceKind.RBI),
        (_DEPARTMENT_REFERENCE, ReferenceKind.DEPARTMENT),
    ):
        for match in pattern.finditer(text):
            references.append(
                ReferenceCandidate(
                    raw=match.group(0),
                    kind=kind,
                    char_start=match.start(),
                    char_end=match.end(),
                    target_clause=_target_clause(text, match.start()),
                )
            )
            occupied.append(match.span())

    for match in _TITLE_REFERENCE.finditer(text):
        following = text[match.end() : match.end() + 80]
        date_match = _DATE_AFTER_TITLE.match(following)
        references.append(
            ReferenceCandidate(
                raw=match.group(0),
                kind=ReferenceKind.TITLED,
                char_start=match.start(),
                char_end=match.end(),
                title=match.group(0),
                published_at=_date(date_match.group("date")) if date_match else None,
                target_clause=_target_clause(text, match.start()),
            )
        )

    for match in _DATED_CIRCULAR.finditer(text):
        references.append(
            ReferenceCandidate(
                raw=match.group(0),
                kind=ReferenceKind.DATED_CIRCULAR,
                char_start=match.start(),
                char_end=match.end(),
                published_at=_date(match.group("date")),
            )
        )
    for match in _IBID.finditer(text):
        references.append(
            ReferenceCandidate(
                raw=match.group(0),
                kind=ReferenceKind.IBID,
                char_start=match.start(),
                char_end=match.end(),
            )
        )

    references.sort(key=lambda reference: (reference.char_start, reference.char_end))
    return tuple(references)
