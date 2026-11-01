from app.api.main import app


def test_openapi_exposes_scoped_question_contract() -> None:
    operation = app.openapi()["paths"]["/questions"]["post"]

    assert operation["requestBody"]["required"] is True
    response_schema = app.openapi()["components"]["schemas"]["AnswerResponse"]
    assert {"answer", "insufficient_evidence", "claims"}.issubset(
        response_schema["properties"]
    )

