import re
from dataclasses import dataclass
from enum import StrEnum


class RelationType(StrEnum):
    AMENDS = "AMENDS"
    REPLACES = "REPLACES"
    REPEALS = "REPEALS"
    CONSOLIDATED_INTO = "CONSOLIDATED_INTO"
    RELATED_TO = "RELATED_TO"


@dataclass(frozen=True, slots=True)
class Classification:
    relation_type: RelationType
    matched_text: str


_NEGATIVE_PATTERNS = (
    re.compile(r"\bas amended from time to time\b", re.IGNORECASE),
    re.compile(r"\bamendments? issued from time to time\b", re.IGNORECASE),
    re.compile(r"\bmay be amended\b", re.IGNORECASE),
    re.compile(r"\brefer to (?:the )?amended\b", re.IGNORECASE),
)
_PATTERNS: tuple[tuple[RelationType, re.Pattern[str]], ...] = (
    (
        RelationType.CONSOLIDATED_INTO,
        re.compile(r"\b(?:is|are|were|has been|have been) consolidated into\b", re.IGNORECASE),
    ),
    (
        RelationType.REPEALS,
        re.compile(r"\b(?:is|are|were|hereby|shall be) repealed\b", re.IGNORECASE),
    ),
    (
        RelationType.REPEALS,
        re.compile(r"\b(?:is|are|were|stand|stands|hereby) withdrawn\b", re.IGNORECASE),
    ),
    (
        RelationType.REPLACES,
        re.compile(r"\b(?:is|are|shall be|has been) replaced by\b", re.IGNORECASE),
    ),
    (
        RelationType.REPLACES,
        re.compile(r"\b(?:is|are|was|were|has been) superseded by\b", re.IGNORECASE),
    ),
    (
        RelationType.AMENDS,
        re.compile(
            r"\b(?:is|are|was|were|shall be|has been|have been) "
            r"(?:amended|substituted|inserted|deleted|omitted)\b",
            re.IGNORECASE,
        ),
    ),
    (RelationType.AMENDS, re.compile(r"\bdecided to revise\b", re.IGNORECASE)),
    (
        RelationType.AMENDS,
        re.compile(r"\bamended paragraph\b.+?\bmay be read as follows\b", re.IGNORECASE),
    ),
)


def classify_relationship(text: str) -> Classification | None:
    if any(pattern.search(text) for pattern in _NEGATIVE_PATTERNS):
        return None
    matches: list[tuple[int, RelationType, re.Match[str]]] = []
    for relation_type, pattern in _PATTERNS:
        match = pattern.search(text)
        if match is not None:
            matches.append((match.start(), relation_type, match))
    if not matches:
        return None
    _, relation_type, match = min(matches, key=lambda item: item[0])
    return Classification(relation_type=relation_type, matched_text=match.group(0))
