from pydantic import BaseModel, Field


class ClaimDraft(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    clause_id: int = Field(gt=0)
    quote: str = Field(min_length=1, max_length=2000)


class AnswerDraft(BaseModel):
    claims: list[ClaimDraft] = Field(max_length=12)


class VerifiedClaim(BaseModel):
    text: str
    clause_id: int
    quote: str
    document_id: int
    document_title: str
    path: str
    page: int | None
    dom_locator: str | None
    source_url: str


class AnswerResponse(BaseModel):
    answer: str
    insufficient_evidence: bool
    claims: list[VerifiedClaim]

