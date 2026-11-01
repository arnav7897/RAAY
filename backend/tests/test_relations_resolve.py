from app.refs.extract import ReferenceCandidate, ReferenceKind
from app.relations.resolve import DocumentRecord, ResolutionStatus, resolve_reference

DOCUMENTS = (
    DocumentRecord(
        document_id=7,
        title="Master Direction - Regulatory Framework for Microfinance Loans Directions, 2022",
        published_at="2022-03-14",
        aliases=(
            "RBI/DOR/2021-22/89",
            "DoR.FIN.REC.95/03.10.038/2021-22",
        ),
    ),
    DocumentRecord(
        document_id=9,
        title="Master Direction - Know Your Customer Direction, 2016",
        published_at="2016-02-25",
        aliases=("DBR.AML.BC.No.81/14.01.001/2015-16",),
    ),
)


def test_resolves_exact_alias_before_fuzzy_title() -> None:
    reference = ReferenceCandidate(
        raw="dor.fin.rec.95/03.10.038/2021-22",
        kind=ReferenceKind.DEPARTMENT,
        char_start=0,
        char_end=35,
    )

    result = resolve_reference(reference, DOCUMENTS)

    assert result.status is ResolutionStatus.RESOLVED
    assert result.document_id == 7
    assert result.method == "exact_alias"


def test_resolves_similar_title_only_when_date_matches() -> None:
    reference = ReferenceCandidate(
        raw="Master Direction RBI Regulatory Framework for Microfinance Loans Directions 2022",
        kind=ReferenceKind.TITLED,
        char_start=0,
        char_end=77,
        title="Master Direction RBI Regulatory Framework for Microfinance Loans Directions 2022",
        published_at="2022-03-14",
    )

    result = resolve_reference(reference, DOCUMENTS)

    assert result.status is ResolutionStatus.RESOLVED
    assert result.document_id == 7
    assert result.method == "title_and_date"
    assert result.score is not None and result.score >= 92


def test_does_not_guess_from_title_without_matching_date() -> None:
    reference = ReferenceCandidate(
        raw="Master Direction Regulatory Framework for Microfinance Loans",
        kind=ReferenceKind.TITLED,
        char_start=0,
        char_end=59,
        title="Master Direction Regulatory Framework for Microfinance Loans",
        published_at="2023-03-14",
    )

    result = resolve_reference(reference, DOCUMENTS)

    assert result.status is ResolutionStatus.UNRESOLVED
    assert result.document_id is None
