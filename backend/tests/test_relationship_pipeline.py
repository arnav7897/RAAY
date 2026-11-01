from app.parse.models import EvidenceBlock, EvidenceLocation
from app.relations.classify import RelationType
from app.relations.models import EvidenceType, VerificationStatus
from app.relations.pipeline import analyze_evidence_block, build_evidence_windows
from app.relations.resolve import DocumentRecord

SOURCE_TEXT = (
    "Please refer to paragraph 8.1 of the Master Direction - Reserve Bank of India "
    "(Regulatory Framework for Microfinance Loans) Directions, 2022 dated March 14, "
    "2022 which prescribes the criteria. On a review, it has been decided to revise the "
    "criteria and the amended paragraph 8.1 may be read as follows."
)


def test_explicit_resolved_instruction_becomes_verified_relationship() -> None:
    block = EvidenceBlock(
        text=SOURCE_TEXT,
        location=EvidenceLocation(char_start=0, char_end=len(SOURCE_TEXT), dom_locator="#p1"),
    )
    documents = (
        DocumentRecord(
            document_id=7,
            title="Master Direction - Regulatory Framework for Microfinance Loans Directions, 2022",
            published_at="2022-03-14",
            aliases=("RBI/DOR/2021-22/89",),
        ),
    )

    relationships = analyze_evidence_block(
        source_document_id=8,
        source_url="https://www.rbi.org.in/source",
        source_text=SOURCE_TEXT,
        block=block,
        documents=documents,
    )

    assert len(relationships) == 1
    relationship = relationships[0]
    assert relationship.target_document_id == 7
    assert relationship.target_clause == "8.1"
    assert relationship.relation_type is RelationType.AMENDS
    assert relationship.status is VerificationStatus.VERIFIED
    assert relationship.evidence_type is EvidenceType.AMEND_INSTRUCTION
    assert relationship.evidence_text == SOURCE_TEXT


def test_unresolved_explicit_instruction_is_never_verified() -> None:
    text = "RBI/2099-2100/999 is hereby repealed."
    block = EvidenceBlock(
        text=text,
        location=EvidenceLocation(char_start=0, char_end=len(text), page=1),
    )

    relationships = analyze_evidence_block(
        source_document_id=8,
        source_url="https://www.rbi.org.in/source.pdf",
        source_text=text,
        block=block,
        documents=(),
    )

    assert relationships[0].status is VerificationStatus.UNRESOLVED
    assert relationships[0].target_document_id is None


def test_missing_quote_span_prevents_verified_relationship() -> None:
    block = EvidenceBlock(
        text=SOURCE_TEXT,
        location=EvidenceLocation(char_start=0, char_end=len(SOURCE_TEXT), dom_locator="#p1"),
    )
    documents = (
        DocumentRecord(
            document_id=7,
            title="Master Direction - Regulatory Framework for Microfinance Loans Directions, 2022",
            published_at="2022-03-14",
            aliases=(),
        ),
    )

    relationships = analyze_evidence_block(
        source_document_id=8,
        source_url="https://www.rbi.org.in/source",
        source_text="different source text",
        block=block,
        documents=documents,
    )

    assert relationships[0].status is VerificationStatus.CANDIDATE


def test_reference_and_amendment_instruction_can_span_adjacent_blocks() -> None:
    first = "Please refer to paragraph 8.1 of RBI/2021-22/89."
    second = "On review, paragraph 8.1 is amended as follows."
    blocks = (
        EvidenceBlock(
            text=first,
            location=EvidenceLocation(char_start=0, char_end=len(first), dom_locator="#p1"),
        ),
        EvidenceBlock(
            text=second,
            location=EvidenceLocation(
                char_start=len(first) + 1,
                char_end=len(first) + 1 + len(second),
                dom_locator="#p2",
            ),
        ),
    )

    windows = build_evidence_windows(blocks)

    assert len(windows) == 1
    assert windows[0].text == f"{first}\n{second}"
    assert windows[0].location.char_start == 0
    assert windows[0].location.char_end == len(first) + 1 + len(second)
    assert windows[0].location.dom_locator == "#p1"
