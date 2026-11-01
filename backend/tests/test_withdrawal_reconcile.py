from pathlib import Path

import pytest

from app.relations.models import EvidenceType, RelationshipEvidence, VerificationStatus
from app.relations.resolve import DocumentRecord
from app.relations.withdrawal import WithdrawalReconciler, WithdrawalSnapshot


class FakeWithdrawalRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.saved: list[RelationshipEvidence] = []

    async def load_documents(self) -> tuple[DocumentRecord, ...]:
        return (
            DocumentRecord(
                document_id=8,
                title="Review of Qualifying Assets Criteria",
                published_at="2025-06-06",
                aliases=("DoR.FIN.REC.25/03.10.038/2025-26",),
            ),
        )

    async def consolidation_document_id(self) -> int:
        return 9

    async def latest_withdrawal_snapshot(self) -> WithdrawalSnapshot | None:
        return WithdrawalSnapshot(
            cache_path=str(self.path),
            source_url="https://www.rbi.org.in/Scripts/NotificationUserWithdrawnCircular.aspx",
        )

    async def save_relationship(self, relationship: RelationshipEvidence) -> int:
        self.saved.append(relationship)
        return 1


@pytest.mark.asyncio
async def test_withdrawal_annex_creates_verified_repeal_for_known_alias(
    tmp_path: Path,
) -> None:
    path = tmp_path / "withdrawn.html"
    path.write_text(
        """
        <table><tr><td>41.</td><td>DoR.FIN.REC.25/03.10.038/2025-26</td>
        <td>Review of Qualifying Assets Criteria</td><td>June 6, 2025</td></tr>
        <tr><td>42.</td><td>DOR.UNKNOWN.REC.1/01.01.001/2025-26</td>
        <td>Unknown circular</td><td>June 7, 2025</td></tr></table>
        """,
        encoding="utf-8",
    )
    repository = FakeWithdrawalRepository(path)

    summary = await WithdrawalReconciler(repository, tmp_path).reconcile()

    assert summary.rows_seen == 2
    assert summary.relationships_saved == 1
    relationship = repository.saved[0]
    assert relationship.target_document_id == 8
    assert relationship.relation_type.value == "REPEALS"
    assert relationship.evidence_type is EvidenceType.REPEAL_LIST
    assert relationship.status is VerificationStatus.VERIFIED
