import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
_NUMBERED = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(?=\S)")
_PARAGRAPH = re.compile(r"^Paragraph\s+(\d+(?:\.\d+)*):?\s*(?=\S)", re.IGNORECASE)
_PARENTHETICAL = re.compile(r"^(\([A-Za-zivxlcdmIVXLCDM]+\))\s*(?=\S)")


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).replace("\u00a0", " ")
    return _WHITESPACE.sub(" ", normalized).strip()


def detect_clause_number(text: str) -> str | None:
    for pattern in (_PARAGRAPH, _NUMBERED, _PARENTHETICAL):
        match = pattern.match(text)
        if match:
            return match.group(1)
    return None


def clause_path(clause_no: str, current_path: str | None) -> tuple[str, str | None]:
    if clause_no[0].isdigit():
        parent = clause_no.rpartition(".")[0] or None
        return clause_no, parent
    if current_path is None:
        return clause_no, None
    return f"{current_path}.{clause_no}", current_path
