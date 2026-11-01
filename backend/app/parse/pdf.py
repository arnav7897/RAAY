# mypy: disable-error-code="no-untyped-call,var-annotated,arg-type"

import pymupdf

from app.parse.models import EvidenceLocation, ParsedClause, ParseResult
from app.parse.text import clause_path, detect_clause_number, normalize_text


def parse_pdf(payload: bytes) -> ParseResult:
    document = pymupdf.open(stream=payload, filetype="pdf")
    clauses: list[ParsedClause] = []
    chunks: list[str] = []
    cursor = 0
    current_path: str | None = None
    try:
        for page_index, page in enumerate(document, start=1):
            blocks = sorted(page.get_text("blocks"), key=lambda block: (block[1], block[0]))
            for block in blocks:
                text = normalize_text(str(block[4]))
                if not text:
                    continue
                if chunks:
                    cursor += 1
                start = cursor
                chunks.append(text)
                cursor += len(text)
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
                        location=EvidenceLocation(
                            char_start=start,
                            char_end=cursor,
                            page=page_index,
                        ),
                    )
                )
                current_path = path
    finally:
        document.close()

    return ParseResult(
        normalized_text="\n".join(chunks),
        clauses=tuple(clauses),
        source_format="pdf",
    )
