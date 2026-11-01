from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.parse.html import parse_html_blocks
from app.parse.pdf import parse_pdf_blocks
from app.relations.models import RelationshipEvidence
from app.relations.pipeline import analyze_evidence_block, build_evidence_windows
from app.relations.repository import SourceDocument
from app.relations.resolve import DocumentRecord


class RelationshipStore(Protocol):
    async def load_documents(self) -> tuple[DocumentRecord, ...]: ...

    async def load_sources(self) -> tuple[SourceDocument, ...]: ...

    async def save_relationship(self, relationship: RelationshipEvidence) -> int: ...


@dataclass(frozen=True, slots=True)
class ReconcileSummary:
    sources_processed: int
    sources_skipped: int
    relationships_seen: int
    failures: tuple[str, ...]


class RelationshipReconciler:
    def __init__(self, *, repository: RelationshipStore, raw_cache_dir: Path) -> None:
        self._repository = repository
        self._raw_cache_dir = raw_cache_dir

    def _payload(self, source: SourceDocument) -> bytes:
        if source.raw_cache_path is None:
            raise FileNotFoundError(
                f"document version {source.version_id} has no raw cache path"
            )
        recorded_path = Path(source.raw_cache_path)
        candidates = (recorded_path, self._raw_cache_dir / recorded_path.name)
        for candidate in candidates:
            if candidate.is_file():
                return candidate.read_bytes()
        raise FileNotFoundError(
            f"raw cache file for document version {source.version_id} was not found"
        )

    async def reconcile(self) -> ReconcileSummary:
        documents = await self._repository.load_documents()
        sources = await self._repository.load_sources()
        sources_processed = 0
        relationships_seen = 0
        failures: list[str] = []

        for source in sources:
            try:
                payload = self._payload(source)
            except FileNotFoundError as error:
                failures.append(str(error))
                continue
            if source.source_format == "html":
                blocks = parse_html_blocks(payload)
            elif source.source_format == "pdf":
                blocks = parse_pdf_blocks(payload)
            else:
                raise ValueError(f"unsupported source format: {source.source_format}")

            for block in build_evidence_windows(blocks):
                relationships = analyze_evidence_block(
                    source_document_id=source.document_id,
                    source_url=source.source_url,
                    source_text=source.normalized_text,
                    block=block,
                    documents=documents,
                )
                for relationship in relationships:
                    await self._repository.save_relationship(relationship)
                    relationships_seen += 1
            sources_processed += 1

        return ReconcileSummary(
            sources_processed=sources_processed,
            sources_skipped=len(failures),
            relationships_seen=relationships_seen,
            failures=tuple(failures),
        )
