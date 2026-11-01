from app.relations.repeal import parse_repeal_rows


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
