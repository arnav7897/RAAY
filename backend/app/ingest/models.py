from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GoldDocument:
    key: str
    title: str
    source_url: str
    expected_clauses: tuple[str, ...] = ()
    rbi_ref: str | None = None
    dept_ref: str | None = None
    published_at: str | None = None


@dataclass(frozen=True, slots=True)
class FetchResult:
    url: str
    content: bytes
    content_type: str
    retrieved_at: str
    cache_path: str | None = None


@dataclass(frozen=True, slots=True)
class IngestResult:
    document_key: str
    content_hash: str
    version_no: int
    clause_count: int
    created: bool
