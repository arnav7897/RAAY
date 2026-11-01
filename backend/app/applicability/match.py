from dataclasses import dataclass, field
from enum import StrEnum

from app.applicability.ontology import EntityOntology


class Polarity(StrEnum):
    INCLUDES = "INCLUDES"
    EXCLUDES = "EXCLUDES"


class Outcome(StrEnum):
    DIRECT = "DIRECT"
    POTENTIAL = "POTENTIAL"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"


@dataclass(frozen=True, slots=True)
class ApplicabilityFact:
    entity_code: str
    polarity: Polarity
    evidence_text: str
    conditions: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StakeholderProfile:
    entity_code: str
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ApplicabilityResult:
    outcome: Outcome
    reasons: tuple[str, ...]


def _conditions_match(
    profile: StakeholderProfile,
    conditions: dict[str, str],
) -> bool:
    return all(profile.attributes.get(key) == expected for key, expected in conditions.items())


def evaluate_applicability(
    profile: StakeholderProfile,
    facts: tuple[ApplicabilityFact, ...],
    ontology: EntityOntology,
) -> ApplicabilityResult:
    exclusions = tuple(
        fact
        for fact in facts
        if fact.polarity is Polarity.EXCLUDES
        and ontology.is_a(profile.entity_code, fact.entity_code)
    )
    if exclusions:
        return ApplicabilityResult(
            outcome=Outcome.NOT_ESTABLISHED,
            reasons=tuple(fact.evidence_text for fact in exclusions),
        )

    inclusions = tuple(
        fact
        for fact in facts
        if fact.polarity is Polarity.INCLUDES
        and ontology.is_a(profile.entity_code, fact.entity_code)
    )
    if not inclusions:
        return ApplicabilityResult(
            outcome=Outcome.NOT_ESTABLISHED,
            reasons=("No applicable official addressee or clause was established",),
        )

    direct = tuple(fact for fact in inclusions if _conditions_match(profile, fact.conditions))
    if direct:
        return ApplicabilityResult(
            outcome=Outcome.DIRECT,
            reasons=tuple(fact.evidence_text for fact in direct),
        )
    return ApplicabilityResult(
        outcome=Outcome.POTENTIAL,
        reasons=tuple(
            f"{fact.evidence_text} (conditions not established)" for fact in inclusions
        ),
    )
