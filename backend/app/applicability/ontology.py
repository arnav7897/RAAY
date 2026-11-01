from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EntityOntology:
    parents: dict[str, str | None]

    def __post_init__(self) -> None:
        for entity in self.parents:
            visited: set[str] = set()
            current: str | None = entity
            while current is not None:
                if current in visited:
                    raise ValueError(f"entity ontology cycle at {current}")
                visited.add(current)
                current = self.parents.get(current)

    def is_a(self, entity_code: str, ancestor_code: str) -> bool:
        current: str | None = entity_code
        visited: set[str] = set()
        while current is not None and current not in visited:
            if current == ancestor_code:
                return True
            visited.add(current)
            current = self.parents.get(current)
        return False


def default_ontology() -> EntityOntology:
    return EntityOntology(
        {
            "REGULATED_ENTITY": None,
            "BANK": "REGULATED_ENTITY",
            "COMMERCIAL_BANK": "BANK",
            "SMALL_FINANCE_BANK": "COMMERCIAL_BANK",
            "LOCAL_AREA_BANK": "COMMERCIAL_BANK",
            "REGIONAL_RURAL_BANK": "COMMERCIAL_BANK",
            "PAYMENTS_BANK": "COMMERCIAL_BANK",
            "COOPERATIVE_BANK": "BANK",
            "PRIMARY_URBAN_COOPERATIVE_BANK": "COOPERATIVE_BANK",
            "STATE_COOPERATIVE_BANK": "COOPERATIVE_BANK",
            "DISTRICT_CENTRAL_COOPERATIVE_BANK": "COOPERATIVE_BANK",
            "NBFC": "REGULATED_ENTITY",
            "NBFC_ICC": "NBFC",
            "NBFC_MFI": "NBFC",
            "HFC": "NBFC",
        }
    )
