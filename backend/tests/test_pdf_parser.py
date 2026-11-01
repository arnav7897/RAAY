import pymupdf

from app.parse.pdf import parse_pdf


def test_pdf_parser_keeps_page_and_offsets() -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "8.1 Qualifying assets shall constitute at least 60 percent.")
    payload = document.tobytes()
    document.close()

    result = parse_pdf(payload)

    clause = next(item for item in result.clauses if item.clause_no == "8.1")
    assert clause.location.page == 1
    assert clause.location.dom_locator is None
    location = clause.location
    assert result.normalized_text[location.char_start : location.char_end].startswith("8.1")
