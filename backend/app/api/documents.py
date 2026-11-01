from typing import Annotated, Literal

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


class RelationshipDiffResponse(BaseModel):
    operation: str
    old_text: str
    new_text: str


class RelationshipResponse(BaseModel):
    id: int
    direction: Literal["OUTGOING", "INCOMING"]
    source_document_id: int
    source_rbi_ref: str | None
    source_title: str
    target_document_id: int | None
    target_rbi_ref: str | None
    target_title: str | None
    target_ref_raw: str
    target_clause: str | None
    relation_type: str
    evidence_text: str
    evidence_page: int | None
    evidence_dom_locator: str | None
    char_start: int
    char_end: int
    source_url: str
    evidence_type: str
    verification_status: str
    extractor: str
    extractor_version: str
    old_text: str | None
    new_text: str | None
    diff: list[RelationshipDiffResponse]


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


@router.get("/{document_id}/relations", response_model=list[RelationshipResponse])
async def list_relationships(
    document_id: int, settings: SettingsDependency
) -> list[RelationshipResponse]:
    async with (
        await psycopg.AsyncConnection.connect(settings.database_url) as connection,
        connection.cursor() as cursor,
    ):
        await cursor.execute("SELECT 1 FROM documents WHERE id = %s", (document_id,))
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="document not found")
        await cursor.execute(
            """
            SELECT relation.id,
                   CASE WHEN relation.source_document_id = %s
                        THEN 'OUTGOING' ELSE 'INCOMING' END,
                   source.id, source.rbi_ref, source.title,
                   target.id, target.rbi_ref, target.title,
                   relation.target_ref_raw, relation.target_clause,
                   relation.relation_type, relation.evidence_text,
                   relation.evidence_page, relation.evidence_dom_locator,
                   relation.char_start, relation.char_end, relation.source_url,
                   relation.evidence_type, relation.verification_status,
                   relation.extractor, relation.extractor_version,
                   version.old_text, version.new_text,
                   COALESCE(version.diff_json, '[]'::jsonb)
            FROM document_relations AS relation
            JOIN documents AS source ON source.id = relation.source_document_id
            LEFT JOIN documents AS target ON target.id = relation.target_document_id
            LEFT JOIN clause_versions AS version ON version.relation_id = relation.id
            WHERE relation.source_document_id = %s OR relation.target_document_id = %s
            ORDER BY relation.id
            """,
            (document_id, document_id, document_id),
        )
        rows = await cursor.fetchall()
    return [
        RelationshipResponse(
            id=_integer(row[0]),
            direction=_direction(row[1]),
            source_document_id=_integer(row[2]),
            source_rbi_ref=_optional_string(row[3]),
            source_title=_string(row[4]),
            target_document_id=_optional_integer(row[5]),
            target_rbi_ref=_optional_string(row[6]),
            target_title=_optional_string(row[7]),
            target_ref_raw=_string(row[8]),
            target_clause=_optional_string(row[9]),
            relation_type=_string(row[10]),
            evidence_text=_string(row[11]),
            evidence_page=_optional_integer(row[12]),
            evidence_dom_locator=_optional_string(row[13]),
            char_start=_integer(row[14]),
            char_end=_integer(row[15]),
            source_url=_string(row[16]),
            evidence_type=_string(row[17]),
            verification_status=_string(row[18]),
            extractor=_string(row[19]),
            extractor_version=_string(row[20]),
            old_text=_optional_string(row[21]),
            new_text=_optional_string(row[22]),
            diff=_diff(row[23]),
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


def _direction(value: object) -> Literal["OUTGOING", "INCOMING"]:
    text = _string(value)
    if text == "OUTGOING":
        return "OUTGOING"
    if text == "INCOMING":
        return "INCOMING"
    raise ValueError(f"unexpected relationship direction: {text}")


def _diff(value: object) -> list[RelationshipDiffResponse]:
    if not isinstance(value, list):
        raise TypeError(f"expected relationship diff list, got {type(value).__name__}")
    return [RelationshipDiffResponse.model_validate(item) for item in value]
