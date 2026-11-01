from dataclasses import dataclass
from datetime import date

import psycopg

from app.lifecycle.compute import LifecycleRelation, LifecycleState, RelationDirection
from app.relations.classify import RelationType


@dataclass(frozen=True, slots=True)
class LifecycleDocument:
    document_id: int
    draft: bool
    effective_at: date | None
    relations: tuple[LifecycleRelation, ...]


class LifecycleRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    async def load_documents(self) -> tuple[LifecycleDocument, ...]:
        async with (
            await psycopg.AsyncConnection.connect(self._database_url) as connection,
            connection.cursor() as cursor,
        ):
            await cursor.execute(
                """
                SELECT id, doc_type, COALESCE(effective_at, published_at)::text
                FROM documents
                ORDER BY id
                """
            )
            document_rows = await cursor.fetchall()
            await cursor.execute(
                """
                SELECT source_document_id, target_document_id, relation_type,
                       verification_status
                FROM document_relations
                WHERE verification_status = 'VERIFIED'
                """
            )
            relation_rows = await cursor.fetchall()

        relations: dict[int, list[LifecycleRelation]] = {}
        for row in relation_rows:
            relation_type = RelationType(_string(row[2]))
            verified = _string(row[3]) == "VERIFIED"
            source_id = _integer(row[0])
            relations.setdefault(source_id, []).append(
                LifecycleRelation(relation_type, RelationDirection.OUTGOING, verified)
            )
            target_id = _optional_integer(row[1])
            if target_id is not None:
                relations.setdefault(target_id, []).append(
                    LifecycleRelation(relation_type, RelationDirection.INCOMING, verified)
                )

        return tuple(
            LifecycleDocument(
                document_id=_integer(row[0]),
                draft=_optional_string(row[1]) == "DRAFT",
                effective_at=_optional_date(row[2]),
                relations=tuple(relations.get(_integer(row[0]), ())),
            )
            for row in document_rows
        )

    async def update_state(self, document_id: int, state: LifecycleState) -> None:
        async with await psycopg.AsyncConnection.connect(self._database_url) as connection:
            await connection.execute(
                """
                UPDATE documents
                SET lifecycle_state = %s, updated_at = now()
                WHERE id = %s
                """,
                (state.value, document_id),
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


def _optional_date(value: object) -> date | None:
    text = _optional_string(value)
    return date.fromisoformat(text) if text else None
