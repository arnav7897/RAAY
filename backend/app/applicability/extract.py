from dataclasses import dataclass

from app.applicability.match import Polarity
from app.parse.models import EvidenceBlock, EvidenceLocation


@dataclass(frozen=True, slots=True)
class ExtractedApplicabilityFact:
    entity_code: str
    polarity: Polarity
    evidence_text: str
    location: EvidenceLocation


def extract_applicability_facts(
    blocks: tuple[EvidenceBlock, ...],
) -> tuple[ExtractedApplicabilityFact, ...]:
    facts: list[ExtractedApplicabilityFact] = []
    for block in blocks:
        text = block.text.casefold()
        if (
            text.startswith("all non-banking financial companies - microfinance institutions")
            or "shall be applicable to every non-banking financial company"
            in text
            and "microfinance institution" in text
        ):
            facts.append(_fact("NBFC_MFI", Polarity.INCLUDES, block))
            continue
        if text.startswith("all commercial banks"):
            facts.append(_fact("COMMERCIAL_BANK", Polarity.INCLUDES, block))
            if "excluding payments banks" in text:
                facts.append(_fact("PAYMENTS_BANK", Polarity.EXCLUDES, block))
            continue
        if text.startswith("all primary") and "co-operative banks" in text:
            facts.append(_fact("COOPERATIVE_BANK", Polarity.INCLUDES, block))
            continue
        if text.startswith("all non-banking financial companies"):
            facts.append(_fact("NBFC", Polarity.INCLUDES, block))
    return tuple(facts)


def _fact(
    entity_code: str,
    polarity: Polarity,
    block: EvidenceBlock,
) -> ExtractedApplicabilityFact:
    return ExtractedApplicabilityFact(
        entity_code=entity_code,
        polarity=polarity,
        evidence_text=block.text,
        location=block.location,
    )
