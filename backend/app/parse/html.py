from selectolax.parser import HTMLParser, Node

from app.parse.models import EvidenceBlock, EvidenceLocation, ParsedClause, ParseResult
from app.parse.text import clause_path, detect_clause_number, normalize_text

_LEAF_SELECTOR = "p, li, h1, h2, h3, h4, h5, h6"
_CONTENT_SELECTOR = f"{_LEAF_SELECTOR}, td"


def _dom_locator(node: Node, ordinal: int) -> str:
    node_id = node.attributes.get("id")
    if node_id:
        return f"#{node_id}"
    parent_id = node.parent.attributes.get("id") if node.parent is not None else None
    prefix = f"#{parent_id} > " if parent_id else ""
    return f"{prefix}{node.tag}:nth-of-type({ordinal})"


def _document_scope(tree: HTMLParser) -> Node:
    candidates = tree.css("table.td")
    if candidates:
        return max(candidates, key=lambda node: len(node.text(strip=True)))
    if tree.body is None:
        raise ValueError("HTML source has no body")
    return tree.body


def parse_html_blocks(payload: bytes) -> tuple[EvidenceBlock, ...]:
    tree = HTMLParser(payload)
    scope = _document_scope(tree)
    blocks: list[EvidenceBlock] = []
    cursor = 0

    for ordinal, node in enumerate(scope.css(_CONTENT_SELECTOR), start=1):
        if node.tag == "td" and node.css(_LEAF_SELECTOR):
            continue
        text = normalize_text(node.text(separator=" ", strip=True))
        if not text:
            continue
        if blocks:
            cursor += 1
        start = cursor
        cursor += len(text)
        blocks.append(
            EvidenceBlock(
                text=text,
                location=EvidenceLocation(
                    char_start=start,
                    char_end=cursor,
                    dom_locator=_dom_locator(node, ordinal),
                ),
            )
        )
    return tuple(blocks)


def parse_html(payload: bytes) -> ParseResult:
    blocks = parse_html_blocks(payload)
    clauses: list[ParsedClause] = []
    current_path: str | None = None

    for block in blocks:
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
        normalized_text="\n".join(block.text for block in blocks),
        clauses=tuple(clauses),
        source_format="html",
    )
