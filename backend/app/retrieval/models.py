from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class ClauseEvidence:
    clause_id: int
    document_id: int
    document_title: str
    path: str
    text: str
    page: int | None
    dom_locator: str | None
    source_url: str
    score: float

    def with_score(self, score: float) -> "ClauseEvidence":
        return replace(self, score=score)

