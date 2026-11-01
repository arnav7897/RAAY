import hashlib
import re
from collections import defaultdict
from typing import Protocol

from app.ingest.models import FetchResult, GoldDocument, IngestResult
from app.parse.html import parse_html
from app.parse.models import ParseResult
from app.parse.pdf import parse_pdf


class Fetcher(Protocol):
    async def fetch(self, url: str) -> FetchResult: ...


class Repository(Protocol):
    async def latest_hash(self, document_key: str) -> str | None: ...

    async def save_version(
        self,
        source: GoldDocument,
        fetched: FetchResult,
        parsed: ParseResult,
        content_hash: str,
    ) -> int: ...


class InMemoryRepository:
    def __init__(self) -> None:
        self._versions: dict[str, list[tuple[str, ParseResult]]] = defaultdict(list)

    async def latest_hash(self, document_key: str) -> str | None:
        versions = self._versions[document_key]
        return versions[-1][0] if versions else None

    async def save_version(
        self,
        source: GoldDocument,
        fetched: FetchResult,
        parsed: ParseResult,
        content_hash: str,
    ) -> int:
        del fetched
        self._versions[source.key].append((content_hash, parsed))
        return len(self._versions[source.key])

    def version_count(self, document_key: str) -> int:
        return len(self._versions[document_key])


def _parse(fetched: FetchResult) -> ParseResult:
    content_type = fetched.content_type.casefold()
    if "pdf" in content_type or fetched.content.startswith(b"%PDF"):
        return parse_pdf(fetched.content)
    if "html" in content_type or b"<html" in fetched.content[:1024].lower():
        return parse_html(fetched.content)
    raise ValueError(f"unsupported source content type: {fetched.content_type}")


class IngestService:
    def __init__(self, *, fetcher: Fetcher, repository: Repository) -> None:
        self._fetcher = fetcher
        self._repository = repository

    async def ingest(self, source: GoldDocument) -> IngestResult:
        fetched = await self._fetcher.fetch(source.source_url)
        parsed = _parse(fetched)
        compact_text = re.sub(r"\s+", "", parsed.normalized_text).casefold()
        expected_identifiers = (source.rbi_ref, source.dept_ref)
        missing_identifiers = [
            identifier
            for identifier in expected_identifiers
            if identifier and re.sub(r"\s+", "", identifier).casefold() not in compact_text
        ]
        if missing_identifiers:
            raise ValueError(
                "source identity mismatch; missing identifiers: "
                + ", ".join(missing_identifiers)
            )
        content_hash = hashlib.sha256(parsed.normalized_text.encode("utf-8")).hexdigest()
        latest_hash = await self._repository.latest_hash(source.key)
        if latest_hash == content_hash:
            return IngestResult(
                document_key=source.key,
                content_hash=content_hash,
                version_no=0,
                clause_count=0,
                created=False,
            )

        found = {clause.clause_no for clause in parsed.clauses}
        missing = sorted(set(source.expected_clauses) - found)
        if missing:
            raise ValueError(f"missing expected clauses: {', '.join(missing)}")
        version_no = await self._repository.save_version(
            source,
            fetched,
            parsed,
            content_hash,
        )
        return IngestResult(
            document_key=source.key,
            content_hash=content_hash,
            version_no=version_no,
            clause_count=len(parsed.clauses),
            created=True,
        )
