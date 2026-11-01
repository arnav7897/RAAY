from app.relations.verify import locate_normalized_quote


def test_quote_validator_accepts_unicode_and_whitespace_normalization() -> None:
    source = "The amended paragraph says: Qualifying assets shall constitute 60\u00a0percent."
    quote = "Qualifying assets shall constitute 60 percent."

    span = locate_normalized_quote(source, quote)

    assert span is not None
    assert "Qualifying assets" in source[span.char_start : span.char_end]


def test_quote_validator_rejects_text_absent_from_source() -> None:
    assert locate_normalized_quote("Official source text", "fabricated quote") is None
