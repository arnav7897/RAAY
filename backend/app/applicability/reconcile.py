from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.applicability.extract import ExtractedApplicabilityFact, extract_applicability_facts
from app.parse.html import parse_html_blocks
from app.parse.pdf import parse_pdf_blocks
from app.relations.repository import SourceDocument


class ApplicabilityStore(Protocol):
    async def load_sources(self) -> tuple[SourceDocument, ...]: ...

    async def save_fact(
        self,
        *,
        document_id: int,
        source_url: str,
        fact: ExtractedApplicabilityFact,
    ) -> int: ...


@dataclass(frozen=True, slots=True)
class ApplicabilitySummary:
    sources_processed: int
    sources_skipped: int
    facts_seen: int


class ApplicabilityReconciler:
    def __init__(self, *, repository: ApplicabilityStore, raw_cache_dir: Path) -> None:
        self._repository = repository
        self._raw_cache_dir = raw_cache_dir

    def _payload(self, source: SourceDocument) -> bytes | None:
        if source.raw_cache_path is None:
            return None
        recorded = Path(source.raw_cache_path)
        for candidate in (recorded, self._raw_cache_dir / recorded.name):
            if candidate.is_file():
                return candidate.read_bytes()
        return None

    async def reconcile(self) -> ApplicabilitySummary:
        sources = await self._repository.load_sources()
        processed = 0
        skipped = 0
        facts_seen = 0
        for source in sources:
            payload = self._payload(source)
            if payload is None:
                skipped += 1
                continue
            if source.source_format == "html":
                blocks = parse_html_blocks(payload)
            elif source.source_format == "pdf":
                blocks = parse_pdf_blocks(payload)
            else:
                raise ValueError(f"unsupported source format: {source.source_format}")
            for fact in extract_applicability_facts(blocks):
                await self._repository.save_fact(
                    document_id=source.document_id,
                    source_url=source.source_url,
                    fact=fact,
                )
                facts_seen += 1
            processed += 1
        return ApplicabilitySummary(processed, skipped, facts_seen)
