from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.answer.ollama import OllamaLLM
from app.api.documents import router as documents_router
from app.api.questions import router as questions_router
from app.config import get_settings


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    application.state.answer_llm = OllamaLLM(
        base_url=settings.ollama_base_url,
        model=settings.ollama_answer_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
    try:
        yield
    finally:
        await application.state.answer_llm.aclose()


app = FastAPI(title="RAAY API", version="0.1.0", lifespan=lifespan)
app.include_router(documents_router)
app.include_router(questions_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
