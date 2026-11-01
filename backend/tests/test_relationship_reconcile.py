from pathlib import Path

import pytest

from app.relations.models import RelationshipEvidence
from app.relations.reconcile import RelationshipReconciler
from app.relations.repository import SourceDocument
from app.relations.resolve import DocumentRecord


class FakeRelationshipRepository:
    def __init__(self, source: SourceDocument, documents: tuple[DocumentRecord, ...]) -> None:
        self.source = source
        self.documents = documents
        self.saved: dict[tuple[int, str, int, int], RelationshipEvidence] = {}

    async def load_documents(self) -> tuple[DocumentRecord, ...]:
        return self.documents

    async def load_sources(self) -> tuple[SourceDocument, ...]:
        return (self.source,)

    async def save_relationship(self, relationship: RelationshipEvidence) -> int:
        key = (
            relationship.source_document_id,
            relationship.target_ref_raw,
            relationship.char_start,
            relationship.char_end,
        )
        self.saved[key] = relationship
        return 1


@pytest.mark.asyncio
async def test_reconciliation_parses_raw_source_and_is_idempotent(tmp_path: Path) -> None:
    html = b"""
    <html><body>
      <p>Please refer to paragraph 8.1 of RBI/DOR/2021-22/89.</p>
      <p>On review, paragraph 8.1 is amended as follows.</p>
    </body></html>
    """
    raw_path = tmp_path / "source.html"
    raw_path.write_bytes(html)
    normalized_text = (
        "Please refer to paragraph 8.1 of RBI/DOR/2021-22/89.\n"
        "On review, paragraph 8.1 is amended as follows."
    )
    source = SourceDocument(
        document_id=8,
        published_at="2025-06-06",
        source_url="https://www.rbi.org.in/source",
        version_id=11,
        raw_cache_path=str(raw_path),
        source_format="html",
        normalized_text=normalized_text,
    )
    repository = FakeRelationshipRepository(
        source,
        (
            DocumentRecord(
                document_id=7,
                title="Master Direction - Regulatory Framework for Microfinance Loans, 2022",
                published_at="2022-03-14",
                aliases=("RBI/DOR/2021-22/89",),
            ),
        ),
    )
    reconciler = RelationshipReconciler(repository=repository, raw_cache_dir=tmp_path)

    first = await reconciler.reconcile()
    second = await reconciler.reconcile()

    assert first.sources_processed == 1
    assert first.sources_skipped == 0
    assert first.relationships_seen == 1
    assert second.relationships_seen == 1
    assert len(repository.saved) == 1
    relationship = next(iter(repository.saved.values()))
    assert relationship.target_document_id == 7
    assert relationship.target_clause == "8.1"
    assert relationship.status.value == "VERIFIED"


@pytest.mark.asyncio
async def test_reconciliation_skips_sources_without_raw_cache(tmp_path: Path) -> None:
    source = SourceDocument(
        document_id=8,
        published_at=None,
        source_url="https://example.test/missing",
        version_id=12,
        raw_cache_path=None,
        source_format="html",
        normalized_text="missing",
    )
    repository = FakeRelationshipRepository(source, ())

    summary = await RelationshipReconciler(
        repository=repository,
        raw_cache_dir=tmp_path,
    ).reconcile()

    assert summary.sources_processed == 0
    assert summary.sources_skipped == 1
    assert summary.failures == (
        "document version 12 has no raw cache path",
    )
