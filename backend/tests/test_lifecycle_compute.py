from datetime import date

import pytest

from app.lifecycle.compute import (
    LifecycleRelation,
    LifecycleResult,
    LifecycleState,
    RelationDirection,
    compute_lifecycle,
)
from app.relations.classify import RelationType


@pytest.mark.parametrize(
    ("draft", "effective_at", "relations", "expected_state", "expected_label"),
    [
        (True, None, (), LifecycleState.DRAFT, "DRAFT"),
        (False, date(2026, 12, 1), (), LifecycleState.DRAFT, "PROPOSED"),
        (False, date(2025, 1, 1), (), LifecycleState.IN_FORCE, "IN FORCE"),
        (
            False,
            date(2025, 1, 1),
            (LifecycleRelation(RelationType.REPEALS, RelationDirection.INCOMING, True),),
            LifecycleState.REPEALED,
            "HISTORICAL — repealed",
        ),
        (
            False,
            date(2025, 1, 1),
            (
                LifecycleRelation(
                    RelationType.CONSOLIDATED_INTO,
                    RelationDirection.OUTGOING,
                    True,
                ),
            ),
            LifecycleState.SUPERSEDED,
            "HISTORICAL — consolidated",
        ),
    ],
)
def test_lifecycle_precedence(
    draft: bool,
    effective_at: date | None,
    relations: tuple[LifecycleRelation, ...],
    expected_state: LifecycleState,
    expected_label: str,
) -> None:
    result = compute_lifecycle(
        draft=draft,
        effective_at=effective_at,
        relations=relations,
        as_of=date(2026, 11, 1),
    )

    assert result.state is expected_state
    assert result.display_label == expected_label


def test_unverified_relation_does_not_change_lifecycle() -> None:
    result = compute_lifecycle(
        draft=False,
        effective_at=date(2025, 1, 1),
        relations=(
            LifecycleRelation(RelationType.REPEALS, RelationDirection.INCOMING, False),
        ),
        as_of=date(2026, 11, 1),
    )

    assert result == LifecycleResult(LifecycleState.IN_FORCE, "IN FORCE", ())


def test_verified_amendment_adds_label_without_changing_state() -> None:
    result = compute_lifecycle(
        draft=False,
        effective_at=date(2025, 1, 1),
        relations=(
            LifecycleRelation(RelationType.AMENDS, RelationDirection.INCOMING, True),
        ),
        as_of=date(2026, 11, 1),
    )

    assert result.state is LifecycleState.IN_FORCE
    assert result.labels == ("AMENDED",)
