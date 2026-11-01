import psycopg

from app.retrieval.models import ClauseEvidence
from app.retrieval.rank import reciprocal_rank_fusion


class PostgresRetriever:
    def __init__(self, database_url: str, *, limit: int = 8) -> None:
        self._database_url = database_url
        self._limit = limit

    async def search(
        self,
        question: str,
        document_ids: tuple[int, ...],
        *,
        max_hops: int,
    ) -> tuple[ClauseEvidence, ...]:
        if not document_ids:
            return ()
        if max_hops not in (0, 1, 2):
            raise ValueError("max_hops must be 0, 1, or 2")

        async with await psycopg.AsyncConnection.connect(self._database_url) as connection:
            scope = await self._expand_scope(connection, document_ids, max_hops)
            lexical = await self._lexical_search(connection, question, scope)

        # Semantic ranks plug into the same RRF seam when clause embeddings are evaluated.
        return reciprocal_rank_fusion(lexical, (), limit=self._limit)

    async def _expand_scope(
        self,
        connection: psycopg.AsyncConnection[tuple[object, ...]],
        document_ids: tuple[int, ...],
        max_hops: int,
    ) -> tuple[int, ...]:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                WITH RECURSIVE scope(document_id, depth) AS (
                    SELECT unnest(%s::bigint[]), 0
                    UNION
                    SELECT CASE
                               WHEN relation.source_document_id = scope.document_id
                               THEN relation.target_document_id
                               ELSE relation.source_document_id
                           END,
                           scope.depth + 1
                    FROM scope
                    JOIN document_relations AS relation
                      ON relation.source_document_id = scope.document_id
                      OR relation.target_document_id = scope.document_id
                    WHERE scope.depth < %s
                      AND relation.verification_status = 'VERIFIED'
                      AND relation.target_document_id IS NOT NULL
                )
                SELECT DISTINCT document_id
                FROM scope
                WHERE document_id IS NOT NULL
                ORDER BY document_id
                """,
                (list(document_ids), max_hops),
            )
            rows = await cursor.fetchall()
        return tuple(_integer(row[0]) for row in rows)

    async def _lexical_search(
        self,
        connection: psycopg.AsyncConnection[tuple[object, ...]],
        question: str,
        document_ids: tuple[int, ...],
    ) -> tuple[ClauseEvidence, ...]:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                WITH query AS (
                    SELECT replace(
                        websearch_to_tsquery('english', %s)::text,
                        ' & ',
                        ' | '
                    )::tsquery AS value
                )
                SELECT clause.id, version.document_id, document.title, clause.path,
                       clause.text, clause.page, clause.dom_locator, document.source_url,
                       ts_rank_cd(clause.tsv, query.value) AS score
                FROM clauses AS clause
                JOIN document_versions AS version ON version.id = clause.document_version_id
                JOIN documents AS document ON document.id = version.document_id
                CROSS JOIN query
                WHERE version.document_id = ANY(%s::bigint[])
                  AND version.version_no = (
                      SELECT max(latest.version_no)
                      FROM document_versions AS latest
                      WHERE latest.document_id = version.document_id
                  )
                  AND clause.tsv @@ query.value
                ORDER BY score DESC, clause.id
                LIMIT %s
                """,
                (question, list(document_ids), self._limit * 3),
            )
            rows = await cursor.fetchall()
        return tuple(
            ClauseEvidence(
                clause_id=_integer(row[0]),
                document_id=_integer(row[1]),
                document_title=_string(row[2]),
                path=_string(row[3]),
                text=_string(row[4]),
                page=_optional_integer(row[5]),
                dom_locator=_optional_string(row[6]),
                source_url=_string(row[7]),
                score=_float(row[8]),
            )
            for row in rows
        )


def _integer(value: object) -> int:
    if not isinstance(value, int):
        raise TypeError(f"expected integer, got {type(value).__name__}")
    return value


def _optional_integer(value: object) -> int | None:
    return None if value is None else _integer(value)


def _string(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"expected string, got {type(value).__name__}")
    return value


def _optional_string(value: object) -> str | None:
    return None if value is None else _string(value)


def _float(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)
    raise TypeError(f"expected float, got {type(value).__name__}")

