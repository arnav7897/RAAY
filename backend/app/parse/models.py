from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvidenceLocation:
    char_start: int
    char_end: int
    page: int | None = None
    dom_locator: str | None = None

    def __post_init__(self) -> None:
        if self.char_start < 0 or self.char_end <= self.char_start:
            raise ValueError("evidence offsets must identify a non-empty span")
        if (self.page is None) == (self.dom_locator is None):
            raise ValueError("exactly one source-specific locator is required")


@dataclass(frozen=True, slots=True)
class ParsedClause:
    path: str
    clause_no: str
    parent_path: str | None
    text: str
    location: EvidenceLocation


@dataclass(frozen=True, slots=True)
class ParseResult:
    normalized_text: str
    clauses: tuple[ParsedClause, ...]
    source_format: str
