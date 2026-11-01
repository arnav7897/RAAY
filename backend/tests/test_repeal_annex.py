from app.relations.repeal import parse_repeal_html, parse_repeal_rows


def test_parses_reference_date_and_title_from_repeal_rows() -> None:
    text = """
    1 RBI/2021-22/10 May 5, 2021 Earlier Microfinance Circular
    2 DOR.AML.REC.49/14.01.001/2024-25 November 6, 2024 KYC Amendment
    malformed row without a dated reference
    """

    rows = parse_repeal_rows(text)

    assert [(row.reference, row.published_at, row.title) for row in rows] == [
        ("RBI/2021-22/10", "2021-05-05", "Earlier Microfinance Circular"),
        (
            "DOR.AML.REC.49/14.01.001/2024-25",
            "2024-11-06",
            "KYC Amendment",
        ),
    ]


def test_parses_official_withdrawn_page_table_row_with_dom_location() -> None:
    html = b"""
    <html><body><table>
      <tr><th>No.</th><th>Circular No.</th><th>Subject</th><th>Date</th></tr>
      <tr><td>41.</td><td><a>DoR.FIN.REC.25/03.10.038/2025-26</a></td>
      <td>Review of Qualifying Assets Criteria</td><td>June 6, 2025</td></tr>
    </table></body></html>
    """

    rows = parse_repeal_html(html)

    assert len(rows) == 1
    assert rows[0].reference == "DoR.FIN.REC.25/03.10.038/2025-26"
    assert rows[0].published_at == "2025-06-06"
    assert rows[0].title == "Review of Qualifying Assets Criteria"
    assert rows[0].location.dom_locator == "tr:nth-of-type(2)"
    assert rows[0].evidence_text.startswith("41.")
