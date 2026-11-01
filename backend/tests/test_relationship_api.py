from app.api.main import app


def test_openapi_exposes_document_relationship_evidence() -> None:
    operation = app.openapi()["paths"]["/documents/{document_id}/relations"]["get"]

    assert operation["responses"]["200"]["content"]["application/json"]["schema"]
    response_schema = app.openapi()["components"]["schemas"]["RelationshipResponse"]
    assert {
        "id",
        "direction",
        "relation_type",
        "verification_status",
        "evidence_text",
        "source_url",
        "char_start",
        "char_end",
    }.issubset(response_schema["properties"])
