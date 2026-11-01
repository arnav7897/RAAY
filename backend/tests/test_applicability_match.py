import pytest

from app.applicability.match import (
    ApplicabilityFact,
    ApplicabilityResult,
    Outcome,
    Polarity,
    StakeholderProfile,
    evaluate_applicability,
)
from app.applicability.ontology import EntityOntology, default_ontology

MFI_ONLY = (
    ApplicabilityFact(
        entity_code="NBFC_MFI",
        polarity=Polarity.INCLUDES,
        evidence_text="All Non-Banking Financial Companies - Microfinance Institutions",
    ),
)
NBFC_ALL = (
    ApplicabilityFact(
        entity_code="NBFC",
        polarity=Polarity.INCLUDES,
        evidence_text="All Non-Banking Financial Companies",
    ),
)
BANKS_EXCEPT_PAYMENTS = (
    ApplicabilityFact(
        entity_code="BANK",
        polarity=Polarity.INCLUDES,
        evidence_text="All Commercial Banks",
    ),
    ApplicabilityFact(
        entity_code="PAYMENTS_BANK",
        polarity=Polarity.EXCLUDES,
        evidence_text="excluding Payments Banks",
    ),
)
MIDDLE_LAYER = (
    ApplicabilityFact(
        entity_code="NBFC",
        polarity=Polarity.INCLUDES,
        evidence_text="NBFCs in the Middle Layer",
        conditions={"layer": "MIDDLE"},
    ),
)
NBFC_EXCEPT_MFI = (
    ApplicabilityFact("NBFC", Polarity.INCLUDES, "All NBFCs"),
    ApplicabilityFact("NBFC_MFI", Polarity.EXCLUDES, "excluding NBFC-MFIs"),
)


@pytest.mark.parametrize(
    ("entity", "attributes", "facts", "expected"),
    [
        ("NBFC_MFI", {}, MFI_ONLY, Outcome.DIRECT),
        ("NBFC_ICC", {}, MFI_ONLY, Outcome.NOT_ESTABLISHED),
        ("NBFC", {}, MFI_ONLY, Outcome.NOT_ESTABLISHED),
        ("COMMERCIAL_BANK", {}, MFI_ONLY, Outcome.NOT_ESTABLISHED),
        ("HFC", {}, MFI_ONLY, Outcome.NOT_ESTABLISHED),
        ("NBFC_MFI", {}, NBFC_ALL, Outcome.DIRECT),
        ("NBFC_ICC", {}, NBFC_ALL, Outcome.DIRECT),
        ("HFC", {}, NBFC_ALL, Outcome.DIRECT),
        ("COMMERCIAL_BANK", {}, BANKS_EXCEPT_PAYMENTS, Outcome.DIRECT),
        ("SMALL_FINANCE_BANK", {}, BANKS_EXCEPT_PAYMENTS, Outcome.DIRECT),
        ("PAYMENTS_BANK", {}, BANKS_EXCEPT_PAYMENTS, Outcome.NOT_ESTABLISHED),
        ("NBFC_ICC", {"layer": "MIDDLE"}, MIDDLE_LAYER, Outcome.DIRECT),
        ("NBFC_ICC", {"layer": "UPPER"}, MIDDLE_LAYER, Outcome.POTENTIAL),
        ("NBFC_ICC", {}, MIDDLE_LAYER, Outcome.POTENTIAL),
        ("NBFC_MFI", {}, NBFC_EXCEPT_MFI, Outcome.NOT_ESTABLISHED),
        ("NBFC_ICC", {}, NBFC_EXCEPT_MFI, Outcome.DIRECT),
    ],
)
def test_table_driven_applicability(
    entity: str,
    attributes: dict[str, str],
    facts: tuple[ApplicabilityFact, ...],
    expected: Outcome,
) -> None:
    result = evaluate_applicability(
        StakeholderProfile(entity_code=entity, attributes=attributes),
        facts,
        default_ontology(),
    )

    assert result.outcome is expected


def test_mfi_acceptance_reason_uses_official_addressee() -> None:
    result = evaluate_applicability(
        StakeholderProfile(entity_code="NBFC_MFI"),
        MFI_ONLY,
        default_ontology(),
    )

    assert result == ApplicabilityResult(
        outcome=Outcome.DIRECT,
        reasons=("All Non-Banking Financial Companies - Microfinance Institutions",),
    )


def test_ontology_rejects_cycles() -> None:
    with pytest.raises(ValueError, match="cycle"):
        EntityOntology({"NBFC": "NBFC_MFI", "NBFC_MFI": "NBFC"})
