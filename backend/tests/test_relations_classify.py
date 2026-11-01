import pytest

from app.relations.classify import RelationType, classify_relationship


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("paragraph 8.1 is amended as follows", RelationType.AMENDS),
        ("the following paragraph shall be substituted", RelationType.AMENDS),
        ("a new paragraph is inserted after paragraph 4", RelationType.AMENDS),
        ("paragraph 6 is deleted", RelationType.AMENDS),
        ("the words shall be omitted", RelationType.AMENDS),
        ("the earlier Direction is replaced by this Direction", RelationType.REPLACES),
        ("the listed circulars are repealed", RelationType.REPEALS),
        ("the circulars stand withdrawn with immediate effect", RelationType.REPEALS),
        ("the former instruction is superseded by this Direction", RelationType.REPLACES),
        ("these circulars are consolidated into this Direction", RelationType.CONSOLIDATED_INTO),
    ],
)
def test_classifies_explicit_relationship_verbs(text: str, expected: RelationType) -> None:
    result = classify_relationship(text)

    assert result is not None
    assert result.relation_type is expected
    assert result.matched_text.casefold() in text.casefold()


@pytest.mark.parametrize(
    "text",
    [
        "the Direction, as amended from time to time, remains applicable",
        "including amendments issued from time to time",
        "the draft may be amended after public comments",
        "refer to the amended Direction for background",
    ],
)
def test_does_not_create_edges_from_non_instructional_amendment_mentions(text: str) -> None:
    assert classify_relationship(text) is None
