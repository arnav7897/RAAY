from app.refs.extract import ReferenceKind, extract_references


def test_extracts_rbi_and_department_reference_numbers_with_spans() -> None:
    text = (
        "Refer RBI/2025-26/44 and "
        "DoR.FIN.REC.25/03.10.038/2025-26 for the revised criteria."
    )

    references = extract_references(text)

    assert [(reference.kind, reference.raw) for reference in references] == [
        (ReferenceKind.RBI, "RBI/2025-26/44"),
        (ReferenceKind.DEPARTMENT, "DoR.FIN.REC.25/03.10.038/2025-26"),
    ]
    for reference in references:
        assert text[reference.char_start : reference.char_end] == reference.raw


def test_extracts_master_direction_title_date_and_target_clause() -> None:
    text = (
        "Please refer to paragraph 8.1 of the Master Direction - Reserve Bank of India "
        "(Regulatory Framework for Microfinance Loans) Directions, 2022 dated March 14, "
        "2022 which prescribes the criteria."
    )

    references = extract_references(text)

    assert len(references) == 1
    reference = references[0]
    assert reference.kind is ReferenceKind.TITLED
    assert reference.title == (
        "Master Direction - Reserve Bank of India "
        "(Regulatory Framework for Microfinance Loans) Directions, 2022"
    )
    assert reference.published_at == "2022-03-14"
    assert reference.target_clause == "8.1"


def test_extracts_contextual_references_without_guessing_a_target() -> None:
    references = extract_references(
        "The circular dated November 6, 2024 supersedes the instruction ibid."
    )

    assert [reference.kind for reference in references] == [
        ReferenceKind.DATED_CIRCULAR,
        ReferenceKind.IBID,
    ]
    assert references[0].published_at == "2024-11-06"
