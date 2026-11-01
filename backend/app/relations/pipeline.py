from app.parse.models import EvidenceBlock
from app.refs.extract import extract_references
from app.relations.classify import RelationType, classify_relationship
from app.relations.models import EvidenceType, RelationshipEvidence, VerificationStatus
from app.relations.resolve import DocumentRecord, ResolutionStatus, resolve_reference
from app.relations.verify import locate_normalized_quote


def build_evidence_windows(
    blocks: tuple[EvidenceBlock, ...],
) -> tuple[EvidenceBlock, ...]:
    windows: list[EvidenceBlock] = []
    for index, block in enumerate(blocks):
        if not extract_references(block.text):
            continue
        if classify_relationship(block.text) is not None or index + 1 >= len(blocks):
            windows.append(block)
            continue
        following = blocks[index + 1]
        if classify_relationship(following.text) is None:
            windows.append(block)
            continue
        windows.append(
            EvidenceBlock(
                text=f"{block.text}\n{following.text}",
                location=type(block.location)(
                    char_start=block.location.char_start,
                    char_end=following.location.char_end,
                    page=block.location.page,
                    dom_locator=block.location.dom_locator,
                ),
            )
        )
    return tuple(windows)


def _evidence_type(relation_type: RelationType, text: str) -> EvidenceType:
    if relation_type is RelationType.REPEALS and "list" in text.casefold():
        return EvidenceType.REPEAL_LIST
    if relation_type is RelationType.AMENDS:
        return EvidenceType.AMEND_INSTRUCTION
    return EvidenceType.EXPLICIT_REF


def analyze_evidence_block(
    *,
    source_document_id: int,
    source_url: str,
    source_text: str,
    block: EvidenceBlock,
    documents: tuple[DocumentRecord, ...],
) -> tuple[RelationshipEvidence, ...]:
    references = extract_references(block.text)
    if not references:
        return ()
    classification = classify_relationship(block.text)
    quote_span = locate_normalized_quote(source_text, block.text)
    relationships: list[RelationshipEvidence] = []

    for reference in references:
        resolution = resolve_reference(reference, documents)
        if resolution.document_id == source_document_id:
            continue
        relation_type = (
            classification.relation_type
            if classification is not None
            else RelationType.RELATED_TO
        )
        if classification is None:
            status = VerificationStatus.CANDIDATE
            evidence_type = EvidenceType.EXPLICIT_REF
        elif resolution.status is ResolutionStatus.UNRESOLVED:
            status = VerificationStatus.UNRESOLVED
            evidence_type = _evidence_type(relation_type, block.text)
        elif quote_span is None:
            status = VerificationStatus.CANDIDATE
            evidence_type = _evidence_type(relation_type, block.text)
        else:
            status = VerificationStatus.VERIFIED
            evidence_type = _evidence_type(relation_type, block.text)

        char_start = quote_span.char_start if quote_span else block.location.char_start
        char_end = quote_span.char_end if quote_span else block.location.char_end
        relationships.append(
            RelationshipEvidence(
                source_document_id=source_document_id,
                target_document_id=resolution.document_id,
                target_ref_raw=reference.raw,
                target_clause=reference.target_clause,
                relation_type=relation_type,
                evidence_text=block.text,
                evidence_page=block.location.page,
                evidence_dom_locator=block.location.dom_locator,
                char_start=char_start,
                char_end=char_end,
                source_url=source_url,
                evidence_type=evidence_type,
                status=status,
            )
        )
    return tuple(relationships)
