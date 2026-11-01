from collections.abc import Sequence

import psycopg
from psycopg.types.json import Jsonb

from app.ingest.models import FetchResult, GoldDocument
from app.parse.models import ParseResult


class PostgresRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    async def latest_hash(self, document_key: str) -> str | None:
        async with (
            await psycopg.AsyncConnection.connect(self._database_url) as connection,
            connection.cursor() as cursor,
        ):
            await cursor.execute(
                """
                SELECT version.content_hash
                FROM documents AS document
                JOIN document_versions AS version ON version.document_id = document.id
                WHERE document.source_key = %s
                ORDER BY version.version_no DESC
                LIMIT 1
                """,
                (document_key,),
            )
            row = await cursor.fetchone()
            return str(row[0]) if row else None

    async def start_run(self, source: str) -> int:
        async with (
            await psycopg.AsyncConnection.connect(self._database_url) as connection,
            connection.cursor() as cursor,
        ):
            await cursor.execute(
                """
                INSERT INTO ingest_runs (source, status)
                VALUES (%s, 'RUNNING')
                RETURNING id
                """,
                (source,),
            )
            row = await cursor.fetchone()
            if row is None:
                raise RuntimeError("ingest run insert did not return an id")
            return _integer(row[0])

    async def finish_run(
        self, run_id: int, *, succeeded: bool, details: dict[str, object]
    ) -> None:
        status = "SUCCEEDED" if succeeded else "FAILED"
        async with (
            await psycopg.AsyncConnection.connect(self._database_url) as connection,
            connection.cursor() as cursor,
        ):
            await cursor.execute(
                """
                UPDATE ingest_runs
                SET status = %s, finished_at = now(), details = %s
                WHERE id = %s AND status = 'RUNNING'
                """,
                (status, Jsonb(details), run_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"running ingest record {run_id} was not found")

    async def save_version(
        self,
        source: GoldDocument,
        fetched: FetchResult,
        parsed: ParseResult,
        content_hash: str,
    ) -> int:
        async with (
            await psycopg.AsyncConnection.connect(self._database_url) as connection,
            connection.transaction(),
            connection.cursor() as cursor,
        ):
            document_id = await self._upsert_document(cursor, source, fetched.url)
            await cursor.execute(
                "SELECT id FROM documents WHERE id = %s FOR UPDATE",
                (document_id,),
            )
            await cursor.execute(
                """
                SELECT COALESCE(MAX(version_no), 0)
                FROM document_versions
                WHERE document_id = %s
                """,
                (document_id,),
            )
            row = await cursor.fetchone()
            version_no = _integer(row[0]) + 1 if row else 1
            await cursor.execute(
                """
                INSERT INTO document_versions
                    (document_id, version_no, retrieved_at, content_hash, raw_cache_path,
                     source_format, normalized_text)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    document_id,
                    version_no,
                    fetched.retrieved_at,
                    content_hash,
                    fetched.cache_path,
                    parsed.source_format,
                    parsed.normalized_text,
                ),
            )
            version_row = await cursor.fetchone()
            if version_row is None:
                raise RuntimeError("document version insert did not return an id")
            await self._insert_clauses(cursor, _integer(version_row[0]), parsed)
            return version_no

    @staticmethod
    async def _upsert_document(
        cursor: psycopg.AsyncCursor[tuple[object, ...]],
        source: GoldDocument,
        resolved_url: str,
    ) -> int:
        await cursor.execute(
            """
            INSERT INTO documents
                (source_key, rbi_ref, dept_ref, title, published_at, source_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_key) DO UPDATE
            SET rbi_ref = EXCLUDED.rbi_ref,
                dept_ref = EXCLUDED.dept_ref,
                title = EXCLUDED.title,
                published_at = EXCLUDED.published_at,
                source_url = EXCLUDED.source_url
            RETURNING id
            """,
            (
                source.key,
                source.rbi_ref,
                source.dept_ref,
                source.title,
                source.published_at,
                resolved_url,
            ),
        )
        row = await cursor.fetchone()
        if row is None:
            raise RuntimeError("document upsert did not return an id")
        return _integer(row[0])

    @staticmethod
    async def _insert_clauses(
        cursor: psycopg.AsyncCursor[tuple[object, ...]],
        version_id: int,
        parsed: ParseResult,
    ) -> None:
        ids_by_path: dict[str, int] = {}
        for ordinal, clause in enumerate(parsed.clauses, start=1):
            parent_id = ids_by_path.get(clause.parent_path) if clause.parent_path else None
            await cursor.execute(
                """
                INSERT INTO clauses
                    (document_version_id, ordinal, parent_id, path, clause_no, page, dom_locator,
                     char_start, char_end, text)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    version_id,
                    ordinal,
                    parent_id,
                    clause.path,
                    clause.clause_no,
                    clause.location.page,
                    clause.location.dom_locator,
                    clause.location.char_start,
                    clause.location.char_end,
                    clause.text,
                ),
            )
            row = await cursor.fetchone()
            if row is None:
                raise RuntimeError("clause insert did not return an id")
            ids_by_path[clause.path] = _integer(row[0])


def rows_as_dicts(
    columns: Sequence[str], rows: Sequence[Sequence[object]]
) -> list[dict[str, object]]:
    return [dict(zip(columns, row, strict=True)) for row in rows]


def _integer(value: object) -> int:
    if not isinstance(value, int):
        raise TypeError(f"expected database integer, got {type(value).__name__}")
    return value
