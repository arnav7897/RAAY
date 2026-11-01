from dataclasses import replace

import pytest

from app.ingest.models import FetchResult, GoldDocument
from app.ingest.service import IngestService, InMemoryRepository


class StubFetcher:
    def __init__(self, result: FetchResult) -> None:
        self.result = result
        self.calls = 0

    async def fetch(self, url: str) -> FetchResult:
        self.calls += 1
        return self.result


@pytest.mark.asyncio
async def test_unchanged_content_does_not_create_duplicate_version() -> None:
    source = GoldDocument(
        key="microfinance-2025-44",
        title="Review of Qualifying Assets Criteria",
        source_url="https://example.test/rbi",
        expected_clauses=("8.1",),
    )
    fetched = FetchResult(
        url=source.source_url,
        content=b"<html><body><p>8.1 New text</p></body></html>",
        content_type="text/html",
        retrieved_at="2026-11-01T00:00:00Z",
    )
    repository = InMemoryRepository()
    service = IngestService(fetcher=StubFetcher(fetched), repository=repository)

    first = await service.ingest(source)
    second = await service.ingest(source)

    assert first.created is True
    assert second.created is False
    assert repository.version_count(source.key) == 1
    assert repository.metadata_refresh_count(source.key) == 1


@pytest.mark.asyncio
async def test_changed_content_creates_immutable_version() -> None:
    source = GoldDocument(
        key="microfinance-2025-44",
        title="Review of Qualifying Assets Criteria",
        source_url="https://example.test/rbi",
        expected_clauses=("8.1",),
    )
    first_fetch = FetchResult(
        url=source.source_url,
        content=b"<html><body><p>8.1 Old text</p></body></html>",
        content_type="text/html",
        retrieved_at="2026-11-01T00:00:00Z",
    )
    fetcher = StubFetcher(first_fetch)
    repository = InMemoryRepository()
    service = IngestService(fetcher=fetcher, repository=repository)
    await service.ingest(source)

    fetcher.result = replace(
        first_fetch,
        content=b"<html><body><p>8.1 Revised text</p></body></html>",
        retrieved_at="2026-11-02T00:00:00Z",
    )
    result = await service.ingest(source)

    assert result.created is True
    assert result.version_no == 2
    assert repository.version_count(source.key) == 2


@pytest.mark.asyncio
async def test_missing_expected_clause_fails_before_persistence() -> None:
    source = GoldDocument(
        key="microfinance-2025-44",
        title="Review of Qualifying Assets Criteria",
        source_url="https://example.test/rbi",
        expected_clauses=("8.1",),
    )
    fetched = FetchResult(
        url=source.source_url,
        content=b"<html><body><p>1. Different clause</p></body></html>",
        content_type="text/html",
        retrieved_at="2026-11-01T00:00:00Z",
    )
    repository = InMemoryRepository()
    service = IngestService(fetcher=StubFetcher(fetched), repository=repository)

    with pytest.raises(ValueError, match="missing expected clauses: 8.1"):
        await service.ingest(source)

    assert repository.version_count(source.key) == 0


@pytest.mark.asyncio
async def test_source_identity_mismatch_fails_before_persistence() -> None:
    source = GoldDocument(
        key="expected-document",
        title="Expected document",
        source_url="https://example.test/rbi",
        rbi_ref="RBI/2025-26/371",
    )
    fetched = FetchResult(
        url=source.source_url,
        content=b"<html><body><p>1. RBI/2025-26/143 is a different document.</p></body></html>",
        content_type="text/html",
        retrieved_at="2026-11-01T00:00:00Z",
    )
    repository = InMemoryRepository()
    service = IngestService(fetcher=StubFetcher(fetched), repository=repository)

    with pytest.raises(ValueError, match="source identity mismatch"):
        await service.ingest(source)

    assert repository.version_count(source.key) == 0
