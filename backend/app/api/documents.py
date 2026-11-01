from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import Settings, get_settings

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentSummary(BaseModel):
    id: int
    source_key: str
    rbi_ref: str | None
    title: str
    published_at: str | None
    source_url: str
    version_no: int
    content_hash: str


class ClauseResponse(BaseModel):
    id: int
    parent_id: int | None
    path: str
    clause_no: str
    page: int | None
    dom_locator: str | None
    char_start: int
    char_end: int
    text: str


SettingsDependency = Annotated[Settings, Depends(get_settings)]


@router.get("", response_model=list[DocumentSummary])
async def list_documents(settings: SettingsDependency) -> list[DocumentSummary]:
    async with (
        await psycopg.AsyncConnection.connect(settings.database_url) as connection,
        connection.cursor() as cursor,
    ):
        await cursor.execute(
            """
            SELECT document.id, document.source_key, document.rbi_ref, document.title,
                   document.published_at::text, document.source_url,
                   version.version_no, version.content_hash
            FROM documents AS document
            JOIN LATERAL (
                SELECT version_no, content_hash
                FROM document_versions
                WHERE document_id = document.id
                ORDER BY version_no DESC
                LIMIT 1
            ) AS version ON true
            ORDER BY document.published_at DESC NULLS LAST, document.id
            """
        )
        rows = await cursor.fetchall()
    return [
        DocumentSummary(
            id=_integer(row[0]),
            source_key=_string(row[1]),
            rbi_ref=_optional_string(row[2]),
            title=_string(row[3]),
            published_at=_optional_string(row[4]),
            source_url=_string(row[5]),
            version_no=_integer(row[6]),
            content_hash=_string(row[7]),
        )
        for row in rows
    ]


@router.get("/{document_id}/clauses", response_model=list[ClauseResponse])
async def list_clauses(
    document_id: int, settings: SettingsDependency
) -> list[ClauseResponse]:
    async with (
        await psycopg.AsyncConnection.connect(settings.database_url) as connection,
        connection.cursor() as cursor,
    ):
        await cursor.execute(
            """
            SELECT clause.id, clause.parent_id, clause.path, clause.clause_no,
                   clause.page, clause.dom_locator, clause.char_start, clause.char_end,
                   clause.text
            FROM clauses AS clause
            JOIN document_versions AS version ON version.id = clause.document_version_id
            WHERE version.document_id = %s
              AND version.version_no = (
                  SELECT max(latest.version_no)
                  FROM document_versions AS latest
                  WHERE latest.document_id = %s
              )
            ORDER BY clause.ordinal
            """,
            (document_id, document_id),
        )
        rows = await cursor.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="document or clauses not found")
    return [
        ClauseResponse(
            id=_integer(row[0]),
            parent_id=_optional_integer(row[1]),
            path=_string(row[2]),
            clause_no=_string(row[3]),
            page=_optional_integer(row[4]),
            dom_locator=_optional_string(row[5]),
            char_start=_integer(row[6]),
            char_end=_integer(row[7]),
            text=_string(row[8]),
        )
        for row in rows
    ]


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
