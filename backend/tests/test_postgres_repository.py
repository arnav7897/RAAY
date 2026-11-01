import os
from uuid import uuid4

import psycopg
import pytest

from app.ingest.models import FetchResult, GoldDocument
from app.ingest.repository import PostgresRepository
from app.ingest.service import IngestService

DATABASE_URL = os.getenv("RAAY_TEST_DATABASE_URL")


class StubFetcher:
    def __init__(self, result: FetchResult) -> None:
        self.result = result

    async def fetch(self, url: str) -> FetchResult:
        return self.result


@pytest.mark.skipif(DATABASE_URL is None, reason="RAAY_TEST_DATABASE_URL is not configured")
@pytest.mark.asyncio
async def test_postgres_repository_is_idempotent() -> None:
    assert DATABASE_URL is not None
    key = f"phase1-integration-{uuid4()}"
    source = GoldDocument(
        key=key,
        title="Phase 1 integration fixture",
        source_url="https://example.test/phase1",
        expected_clauses=("8.1",),
    )
    fetched = FetchResult(
        url=source.source_url,
        content=b"<html><body><p>8.1 Integration clause</p></body></html>",
        content_type="text/html",
        retrieved_at="2026-11-01T00:00:00Z",
    )
    service = IngestService(
        fetcher=StubFetcher(fetched),
        repository=PostgresRepository(DATABASE_URL),
    )

    first = await service.ingest(source)
    second = await service.ingest(source)

    assert first.created is True
    assert first.version_no == 1
    assert second.created is False
    async with (
        await psycopg.AsyncConnection.connect(DATABASE_URL) as connection,
        connection.cursor() as cursor,
    ):
        await cursor.execute(
            """
            SELECT count(*)
            FROM document_versions AS version
            JOIN documents AS document ON document.id = version.document_id
            WHERE document.source_key = %s
            """,
            (key,),
        )
        row = await cursor.fetchone()
    assert row == (1,)
