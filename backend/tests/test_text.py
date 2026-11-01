from app.parse.text import detect_clause_number, normalize_text


def test_normalize_text_preserves_offsetable_single_spaces() -> None:
    assert normalize_text("  Paragraph\u00a0  8.1\nnext  ") == "Paragraph 8.1 next"


def test_detect_clause_number() -> None:
    assert detect_clause_number("8.1 Qualifying Assets") == "8.1"
    assert detect_clause_number("Paragraph 8.1: Revised text") == "8.1"
    assert detect_clause_number("(a) first condition") == "(a)"
    assert detect_clause_number("Introduction") is None
