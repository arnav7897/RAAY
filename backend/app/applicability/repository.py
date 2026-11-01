import psycopg
from psycopg.types.json import Jsonb

from app.applicability.extract import ExtractedApplicabilityFact
from app.relations.repository import SourceDocument


class ApplicabilityRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    async def load_sources(self) -> tuple[SourceDocument, ...]:
        async with (
            await psycopg.AsyncConnection.connect(self._database_url) as connection,
            connection.cursor() as cursor,
        ):
            await cursor.execute(
                """
                SELECT document.id, document.published_at::text, document.source_url,
                       version.id, version.raw_cache_path, version.source_format,
                       version.normalized_text
                FROM documents AS document
                JOIN LATERAL (
                    SELECT id, raw_cache_path, source_format, normalized_text
                    FROM document_versions
                    WHERE document_id = document.id
                    ORDER BY version_no DESC
                    LIMIT 1
                ) AS version ON true
                ORDER BY document.id
                """
            )
            rows = await cursor.fetchall()
        return tuple(
            SourceDocument(
                document_id=_integer(row[0]),
                published_at=_optional_string(row[1]),
                source_url=_string(row[2]),
                version_id=_integer(row[3]),
                raw_cache_path=_optional_string(row[4]),
                source_format=_string(row[5]),
                normalized_text=_string(row[6]),
            )
            for row in rows
        )

    async def save_fact(
        self,
        *,
        document_id: int,
        source_url: str,
        fact: ExtractedApplicabilityFact,
    ) -> int:
        async with (
            await psycopg.AsyncConnection.connect(self._database_url) as connection,
            connection.cursor() as cursor,
        ):
            await cursor.execute(
                """
                INSERT INTO applicability_facts (
                    document_id, entity_code, polarity, condition_json,
                    evidence_text, evidence_page, evidence_dom_locator,
                    char_start, char_end, source_url, extractor, extractor_version
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (
                    document_id, entity_code, polarity, char_start, char_end,
                    extractor, extractor_version
                ) DO UPDATE SET
                    evidence_text = EXCLUDED.evidence_text,
                    evidence_page = EXCLUDED.evidence_page,
                    evidence_dom_locator = EXCLUDED.evidence_dom_locator,
                    source_url = EXCLUDED.source_url,
                    updated_at = now()
                RETURNING id
                """,
                (
                    document_id,
                    fact.entity_code,
                    fact.polarity.value,
                    Jsonb({}),
                    fact.evidence_text,
                    fact.location.page,
                    fact.location.dom_locator,
                    fact.location.char_start,
                    fact.location.char_end,
                    source_url,
                    "raay-deterministic",
                    "1.0.0",
                ),
            )
            row = await cursor.fetchone()
        if row is None:
            raise RuntimeError("applicability fact upsert did not return an id")
        return _integer(row[0])


def _integer(value: object) -> int:
    if not isinstance(value, int):
        raise TypeError(f"expected integer, got {type(value).__name__}")
    return value


def _string(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"expected string, got {type(value).__name__}")
    return value


def _optional_string(value: object) -> str | None:
    return None if value is None else _string(value)
