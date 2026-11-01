from dataclasses import dataclass

import psycopg
from psycopg.types.json import Jsonb

from app.relations.diff import DiffChunk
from app.relations.models import RelationshipEvidence
from app.relations.resolve import DocumentRecord
from app.relations.withdrawal import WithdrawalSnapshot


@dataclass(frozen=True, slots=True)
class SourceDocument:
    document_id: int
    published_at: str | None
    source_url: str
    version_id: int
    raw_cache_path: str | None
    source_format: str
    normalized_text: str


@dataclass(frozen=True, slots=True)
class ClauseRecord:
    clause_id: int
    text: str


class RelationshipRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    async def load_documents(self) -> tuple[DocumentRecord, ...]:
        async with (
            await psycopg.AsyncConnection.connect(self._database_url) as connection,
            connection.cursor() as cursor,
        ):
            await cursor.execute(
                """
                SELECT document.id, document.title, document.published_at::text,
                       array_remove(array_agg(alias.alias ORDER BY alias.alias), NULL)
                FROM documents AS document
                LEFT JOIN document_aliases AS alias ON alias.document_id = document.id
                GROUP BY document.id
                ORDER BY document.id
                """
            )
            rows = await cursor.fetchall()
        return tuple(
            DocumentRecord(
                document_id=_integer(row[0]),
                title=_string(row[1]),
                published_at=_optional_string(row[2]),
                aliases=tuple(_string(value) for value in _list(row[3])),
            )
            for row in rows
        )

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

    async def consolidation_document_id(self) -> int:
        async with (
            await psycopg.AsyncConnection.connect(self._database_url) as connection,
            connection.cursor() as cursor,
        ):
            await cursor.execute(
                "SELECT id FROM documents WHERE source_key = %s",
                ("consolidation-withdrawal-2025",),
            )
            row = await cursor.fetchone()
        if row is None:
            raise RuntimeError("consolidation withdrawal document is not ingested")
        return _integer(row[0])

    async def latest_withdrawal_snapshot(self) -> WithdrawalSnapshot | None:
        async with (
            await psycopg.AsyncConnection.connect(self._database_url) as connection,
            connection.cursor() as cursor,
        ):
            await cursor.execute(
                """
                SELECT details #>> '{documents,discovery,cache_path}'
                FROM ingest_runs
                WHERE source = 'withdrawn' AND status = 'SUCCEEDED'
                  AND details #>> '{documents,discovery,cache_path}' IS NOT NULL
                ORDER BY id DESC
                LIMIT 1
                """
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return WithdrawalSnapshot(
            cache_path=_string(row[0]),
            source_url="https://www.rbi.org.in/Scripts/NotificationUserWithdrawnCircular.aspx",
        )

    async def save_relationship(self, relationship: RelationshipEvidence) -> int:
        async with (
            await psycopg.AsyncConnection.connect(self._database_url) as connection,
            connection.cursor() as cursor,
        ):
            await cursor.execute(
                """
                INSERT INTO document_relations (
                    source_document_id, target_document_id, target_ref_raw, target_clause,
                    relation_type, evidence_text, evidence_page, evidence_dom_locator,
                    char_start, char_end, source_url, evidence_type, verification_status,
                    extractor, extractor_version
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (
                    source_document_id, target_ref_raw, relation_type, char_start, char_end,
                    extractor, extractor_version
                ) DO UPDATE SET
                    target_document_id = EXCLUDED.target_document_id,
                    target_clause = EXCLUDED.target_clause,
                    evidence_text = EXCLUDED.evidence_text,
                    evidence_page = EXCLUDED.evidence_page,
                    evidence_dom_locator = EXCLUDED.evidence_dom_locator,
                    source_url = EXCLUDED.source_url,
                    evidence_type = EXCLUDED.evidence_type,
                    verification_status = EXCLUDED.verification_status,
                    updated_at = now()
                RETURNING id
                """,
                (
                    relationship.source_document_id,
                    relationship.target_document_id,
                    relationship.target_ref_raw,
                    relationship.target_clause,
                    relationship.relation_type.value,
                    relationship.evidence_text,
                    relationship.evidence_page,
                    relationship.evidence_dom_locator,
                    relationship.char_start,
                    relationship.char_end,
                    relationship.source_url,
                    relationship.evidence_type.value,
                    relationship.status.value,
                    relationship.extractor,
                    relationship.extractor_version,
                ),
            )
            row = await cursor.fetchone()
        if row is None:
            raise RuntimeError("relationship upsert did not return an id")
        return _integer(row[0])

    async def latest_clause(self, document_id: int, clause_no: str) -> ClauseRecord | None:
        async with (
            await psycopg.AsyncConnection.connect(self._database_url) as connection,
            connection.cursor() as cursor,
        ):
            await cursor.execute(
                """
                SELECT clause.id, clause.text
                FROM clauses AS clause
                JOIN document_versions AS version ON version.id = clause.document_version_id
                WHERE version.document_id = %s AND clause.clause_no = %s
                ORDER BY version.version_no DESC, clause.ordinal
                LIMIT 1
                """,
                (document_id, clause_no),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return ClauseRecord(clause_id=_integer(row[0]), text=_string(row[1]))

    async def save_clause_version(
        self,
        *,
        relation_id: int,
        target_clause: ClauseRecord | None,
        source_clause: ClauseRecord | None,
        old_text: str | None,
        new_text: str | None,
        diff: tuple[DiffChunk, ...],
    ) -> None:
        if old_text is None and new_text is None:
            return
        payload = [
            {
                "operation": chunk.operation.value,
                "old_text": chunk.old_text,
                "new_text": chunk.new_text,
            }
            for chunk in diff
        ]
        async with (
            await psycopg.AsyncConnection.connect(self._database_url) as connection,
            connection.cursor() as cursor,
        ):
            await cursor.execute(
                """
                INSERT INTO clause_versions (
                    relation_id, target_clause_id, source_clause_id,
                    old_text, new_text, diff_json
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (relation_id) DO UPDATE SET
                    target_clause_id = EXCLUDED.target_clause_id,
                    source_clause_id = EXCLUDED.source_clause_id,
                    old_text = EXCLUDED.old_text,
                    new_text = EXCLUDED.new_text,
                    diff_json = EXCLUDED.diff_json
                """,
                (
                    relation_id,
                    target_clause.clause_id if target_clause else None,
                    source_clause.clause_id if source_clause else None,
                    old_text,
                    new_text,
                    Jsonb(payload),
                ),
            )


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


def _list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"expected list, got {type(value).__name__}")
    return value
