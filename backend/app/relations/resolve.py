import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from rapidfuzz import fuzz

from app.refs.extract import ReferenceCandidate


class ResolutionStatus(StrEnum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    document_id: int
    title: str
    published_at: str | None
    aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Resolution:
    status: ResolutionStatus
    document_id: int | None
    method: str | None = None
    score: float | None = None


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", "", normalized).casefold()


def _title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def resolve_reference(
    reference: ReferenceCandidate,
    documents: tuple[DocumentRecord, ...],
    *,
    title_threshold: float = 92.0,
) -> Resolution:
    raw = _normalize(reference.raw)
    for document in documents:
        if any(_normalize(alias) == raw for alias in document.aliases):
            return Resolution(
                status=ResolutionStatus.RESOLVED,
                document_id=document.document_id,
                method="exact_alias",
                score=100.0,
            )

    if reference.title is not None and reference.published_at is not None:
        best_document: DocumentRecord | None = None
        best_score = 0.0
        query = _title(reference.title)
        for document in documents:
            if document.published_at != reference.published_at:
                continue
            score = float(fuzz.token_set_ratio(query, _title(document.title)))
            if score > best_score:
                best_document = document
                best_score = score
        if best_document is not None and best_score >= title_threshold:
            return Resolution(
                status=ResolutionStatus.RESOLVED,
                document_id=best_document.document_id,
                method="title_and_date",
                score=best_score,
            )

    return Resolution(status=ResolutionStatus.UNRESOLVED, document_id=None)
