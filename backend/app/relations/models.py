from dataclasses import dataclass
from enum import StrEnum

from app.relations.classify import RelationType


class EvidenceType(StrEnum):
    EXPLICIT_REF = "EXPLICIT_REF"
    AMEND_INSTRUCTION = "AMEND_INSTRUCTION"
    REPEAL_LIST = "REPEAL_LIST"
    SEMANTIC = "SEMANTIC"


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNRESOLVED = "UNRESOLVED"
    CANDIDATE = "CANDIDATE"


@dataclass(frozen=True, slots=True)
class RelationshipEvidence:
    source_document_id: int
    target_document_id: int | None
    target_ref_raw: str
    target_clause: str | None
    relation_type: RelationType
    evidence_text: str
    evidence_page: int | None
    evidence_dom_locator: str | None
    char_start: int
    char_end: int
    source_url: str
    evidence_type: EvidenceType
    status: VerificationStatus
    extractor: str = "raay-deterministic"
    extractor_version: str = "1.0.0"
