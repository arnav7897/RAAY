from app.applicability.extract import extract_applicability_facts
from app.applicability.match import Polarity
from app.parse.models import EvidenceBlock, EvidenceLocation


def _block(text: str, ordinal: int) -> EvidenceBlock:
    return EvidenceBlock(
        text=text,
        location=EvidenceLocation(
            char_start=ordinal * 100,
            char_end=ordinal * 100 + len(text),
            dom_locator=f"#p{ordinal}",
        ),
    )


def test_extracts_mfi_only_addressee() -> None:
    facts = extract_applicability_facts(
        (_block("All Non-Banking Financial Companies - Microfinance Institutions", 1),)
    )

    assert [(fact.entity_code, fact.polarity) for fact in facts] == [
        ("NBFC_MFI", Polarity.INCLUDES)
    ]


def test_extracts_broad_entities_and_explicit_payment_bank_exclusion() -> None:
    facts = extract_applicability_facts(
        (
            _block(
                "All Commercial Banks including Small Finance Banks excluding Payments Banks",
                1,
            ),
            _block("All Primary Urban Co-operative Banks and State Co-operative Banks", 2),
            _block("All Non-Banking Financial Companies including Housing Finance Companies", 3),
        )
    )

    assert [(fact.entity_code, fact.polarity) for fact in facts] == [
        ("COMMERCIAL_BANK", Polarity.INCLUDES),
        ("PAYMENTS_BANK", Polarity.EXCLUDES),
        ("COOPERATIVE_BANK", Polarity.INCLUDES),
        ("NBFC", Polarity.INCLUDES),
    ]


def test_does_not_infer_applicability_from_incidental_entity_mention() -> None:
    facts = extract_applicability_facts(
        (_block("The Reserve Bank reviewed lending by an NBFC-MFI.", 1),)
    )

    assert facts == ()
