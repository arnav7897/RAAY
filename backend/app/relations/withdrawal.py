from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.refs.extract import ReferenceCandidate, ReferenceKind
from app.relations.classify import RelationType
from app.relations.models import EvidenceType, RelationshipEvidence, VerificationStatus
from app.relations.repeal import parse_repeal_html
from app.relations.resolve import DocumentRecord, ResolutionStatus, resolve_reference


@dataclass(frozen=True, slots=True)
class WithdrawalSnapshot:
    cache_path: str
    source_url: str


@dataclass(frozen=True, slots=True)
class WithdrawalSummary:
    rows_seen: int
    relationships_saved: int


class WithdrawalStore(Protocol):
    async def load_documents(self) -> tuple[DocumentRecord, ...]: ...

    async def consolidation_document_id(self) -> int: ...

    async def latest_withdrawal_snapshot(self) -> WithdrawalSnapshot | None: ...

    async def save_relationship(self, relationship: RelationshipEvidence) -> int: ...


class WithdrawalReconciler:
    def __init__(self, repository: WithdrawalStore, raw_cache_dir: Path) -> None:
        self._repository = repository
        self._raw_cache_dir = raw_cache_dir

    async def reconcile(self) -> WithdrawalSummary:
        snapshot = await self._repository.latest_withdrawal_snapshot()
        if snapshot is None:
            return WithdrawalSummary(0, 0)
        recorded = Path(snapshot.cache_path)
        path = next(
            (
                candidate
                for candidate in (recorded, self._raw_cache_dir / recorded.name)
                if candidate.is_file()
            ),
            None,
        )
        if path is None:
            return WithdrawalSummary(0, 0)
        rows = parse_repeal_html(path.read_bytes())
        documents = await self._repository.load_documents()
        source_document_id = await self._repository.consolidation_document_id()
        saved = 0
        for row in rows:
            kind = (
                ReferenceKind.RBI
                if row.reference.casefold().startswith("rbi/")
                else ReferenceKind.DEPARTMENT
            )
            reference = ReferenceCandidate(
                raw=row.reference,
                kind=kind,
                char_start=0,
                char_end=len(row.reference),
                published_at=row.published_at,
            )
            resolution = resolve_reference(reference, documents)
            if (
                resolution.status is not ResolutionStatus.RESOLVED
                or resolution.document_id is None
                or resolution.document_id == source_document_id
            ):
                continue
            await self._repository.save_relationship(
                RelationshipEvidence(
                    source_document_id=source_document_id,
                    target_document_id=resolution.document_id,
                    target_ref_raw=row.reference,
                    target_clause=None,
                    relation_type=RelationType.REPEALS,
                    evidence_text=row.evidence_text,
                    evidence_page=None,
                    evidence_dom_locator=row.location.dom_locator,
                    char_start=row.location.char_start,
                    char_end=row.location.char_end,
                    source_url=snapshot.source_url,
                    evidence_type=EvidenceType.REPEAL_LIST,
                    status=VerificationStatus.VERIFIED,
                    extractor="raay-withdrawal-annex",
                    extractor_version="1.0.0",
                )
            )
            saved += 1
        return WithdrawalSummary(len(rows), saved)
