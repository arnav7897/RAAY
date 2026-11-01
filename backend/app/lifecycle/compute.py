from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.relations.classify import RelationType


class LifecycleState(StrEnum):
    DRAFT = "DRAFT"
    IN_FORCE = "IN_FORCE"
    REPEALED = "REPEALED"
    SUPERSEDED = "SUPERSEDED"


class RelationDirection(StrEnum):
    OUTGOING = "OUTGOING"
    INCOMING = "INCOMING"


@dataclass(frozen=True, slots=True)
class LifecycleRelation:
    relation_type: RelationType
    direction: RelationDirection
    verified: bool


@dataclass(frozen=True, slots=True)
class LifecycleResult:
    state: LifecycleState
    display_label: str
    labels: tuple[str, ...]


def compute_lifecycle(
    *,
    draft: bool,
    effective_at: date | None,
    relations: tuple[LifecycleRelation, ...],
    as_of: date,
) -> LifecycleResult:
    verified = tuple(relation for relation in relations if relation.verified)
    if any(
        relation.relation_type is RelationType.REPEALS
        and relation.direction is RelationDirection.INCOMING
        for relation in verified
    ):
        return LifecycleResult(
            LifecycleState.REPEALED,
            "HISTORICAL — repealed",
            (),
        )
    if any(
        (
            relation.relation_type is RelationType.REPLACES
            and relation.direction is RelationDirection.INCOMING
        )
        or (
            relation.relation_type is RelationType.CONSOLIDATED_INTO
            and relation.direction is RelationDirection.OUTGOING
        )
        for relation in verified
    ):
        return LifecycleResult(
            LifecycleState.SUPERSEDED,
            "HISTORICAL — consolidated",
            (),
        )
    if draft:
        return LifecycleResult(LifecycleState.DRAFT, "DRAFT", ())
    if effective_at is not None and effective_at > as_of:
        return LifecycleResult(LifecycleState.DRAFT, "PROPOSED", ())

    labels = tuple(
        {"AMENDED"}
        if any(
            relation.relation_type is RelationType.AMENDS
            and relation.direction is RelationDirection.INCOMING
            for relation in verified
        )
        else ()
    )
    return LifecycleResult(LifecycleState.IN_FORCE, "IN FORCE", labels)
