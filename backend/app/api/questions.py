from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.answer.llm import (
    LLMInvalidOutputError,
    LLMProviderError,
    LLMQuotaError,
    LLMTimeoutError,
)
from app.answer.models import AnswerResponse
from app.answer.service import AnswerService
from app.config import Settings, get_settings
from app.retrieval.repository import PostgresRetriever

router = APIRouter(prefix="/questions", tags=["questions"])


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    document_ids: list[int] = Field(min_length=1, max_length=20)


SettingsDependency = Annotated[Settings, Depends(get_settings)]


@router.post("", response_model=AnswerResponse)
async def ask_question(
    request: QuestionRequest,
    settings: SettingsDependency,
    app_request: Request,
) -> AnswerResponse:
    llm = app_request.app.state.answer_llm
    if llm is None:
        raise HTTPException(status_code=503, detail="Answer model is not available")
    service = AnswerService(PostgresRetriever(settings.database_url), llm)
    try:
        return await service.answer(
            question=request.question,
            document_ids=tuple(dict.fromkeys(request.document_ids)),
        )
    except LLMTimeoutError as error:
        raise HTTPException(status_code=504, detail=str(error)) from error
    except LLMQuotaError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (LLMInvalidOutputError, LLMProviderError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

