from fastapi import FastAPI

from app.api.documents import router as documents_router
from app.api.questions import router as questions_router

app = FastAPI(title="RAAY API", version="0.1.0")
app.include_router(documents_router)
app.include_router(questions_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
