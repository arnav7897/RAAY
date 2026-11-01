# mypy: disable-error-code="no-untyped-call,var-annotated,arg-type"

import pymupdf

from app.parse.models import EvidenceBlock, EvidenceLocation, ParsedClause, ParseResult
from app.parse.text import clause_path, detect_clause_number, normalize_text


def parse_pdf_blocks(payload: bytes) -> tuple[EvidenceBlock, ...]:
    document = pymupdf.open(stream=payload, filetype="pdf")
    evidence_blocks: list[EvidenceBlock] = []
    cursor = 0
    try:
        for page_index, page in enumerate(document, start=1):
            blocks = sorted(page.get_text("blocks"), key=lambda block: (block[1], block[0]))
            for block in blocks:
                text = normalize_text(str(block[4]))
                if not text:
                    continue
                if evidence_blocks:
                    cursor += 1
                start = cursor
                cursor += len(text)
                evidence_blocks.append(
                    EvidenceBlock(
                        text=text,
                        location=EvidenceLocation(
                            char_start=start,
                            char_end=cursor,
                            page=page_index,
                        ),
                    )
                )
    finally:
        document.close()
    return tuple(evidence_blocks)


def parse_pdf(payload: bytes) -> ParseResult:
    evidence_blocks = parse_pdf_blocks(payload)
    clauses: list[ParsedClause] = []
    current_path: str | None = None

    for block in evidence_blocks:
        text = block.text
        clause_no = detect_clause_number(text)
        if clause_no is None:
            continue
        path, parent_path = clause_path(clause_no, current_path)
        clauses.append(
            ParsedClause(
                path=path,
                clause_no=clause_no,
                parent_path=parent_path,
                text=text,
                location=block.location,
            )
        )
        current_path = path

    return ParseResult(
        normalized_text="\n".join(block.text for block in evidence_blocks),
        clauses=tuple(clauses),
        source_format="pdf",
    )
