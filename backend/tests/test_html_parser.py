from app.parse.html import parse_html


def test_html_parser_builds_clause_paths_and_dom_locations() -> None:
    html = b"""
    <html><body><main id="content">
      <p>8. Qualifying Assets Criteria</p>
      <p>8.1 Qualifying assets shall constitute at least 60 percent.</p>
      <p>(a) This requirement applies on an ongoing basis.</p>
      <p>9. Effective Date</p>
    </main></body></html>
    """

    result = parse_html(html)

    by_number = {clause.clause_no: clause for clause in result.clauses}
    assert by_number["8"].path == "8"
    assert by_number["8.1"].path == "8.1"
    assert by_number["(a)"].path == "8.1.(a)"
    assert by_number["(a)"].parent_path == "8.1"
    assert by_number["8.1"].location.dom_locator
    assert by_number["8.1"].location.page is None
    location = by_number["8.1"].location
    assert result.normalized_text[location.char_start : location.char_end].startswith("8.1")


def test_html_parser_does_not_duplicate_nested_container_text() -> None:
    html = b"<html><body><div><p>1. First clause</p><p>2. Second clause</p></div></body></html>"

    result = parse_html(html)

    assert [clause.clause_no for clause in result.clauses] == ["1", "2"]


def test_html_parser_prefers_rbi_document_table_over_navigation() -> None:
    html = b"""
    <html><body>
      <p>1. Navigation item changes frequently</p>
      <table class="td"><tr><td><p>8.1 Regulatory clause</p></td></tr></table>
      <p>2. Footer item</p>
    </body></html>
    """

    result = parse_html(html)

    assert [clause.clause_no for clause in result.clauses] == ["8.1"]
    assert result.normalized_text == "8.1 Regulatory clause"
