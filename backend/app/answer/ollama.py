from time import perf_counter

import httpx
import structlog
from pydantic import ValidationError

from app.answer.llm import (
    LLMInvalidOutputError,
    LLMProviderError,
    LLMRefusalError,
    LLMTimeoutError,
    OutputT,
)

logger = structlog.get_logger(__name__)


class OllamaLLM:
    def __init__(self, *, base_url: str, model: str, timeout_seconds: float) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
        )
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def complete(self, prompt: str, schema: type[OutputT]) -> OutputT:
        started = perf_counter()
        try:
            response = await self._client.post(
                "/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Use only the supplied regulatory clauses. Return one cited "
                                "claim per sentence. Never use external knowledge or search."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "format": schema.model_json_schema(),
                    "stream": False,
                    "keep_alive": "10m",
                    "options": {"temperature": 0},
                },
            )
            response.raise_for_status()
        except httpx.TimeoutException as error:
            logger.warning(
                "ollama_timeout",
                elapsed_ms=round((perf_counter() - started) * 1000, 2),
                timeout_seconds=self._timeout_seconds,
                error_type=type(error).__name__,
            )
            raise LLMTimeoutError("Ollama request timed out") from error
        except httpx.HTTPError as error:
            raise LLMProviderError("Ollama request failed") from error

        try:
            result = response.json()
            message = result.get("message") if isinstance(result, dict) else None
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, str):
                raise ValueError("Ollama response has no message content")
        except (AttributeError, TypeError, ValueError) as error:
            raise LLMInvalidOutputError("Ollama returned an invalid response") from error
        if not content:
            raise LLMRefusalError("Ollama returned no answer")
        try:
            return schema.model_validate_json(content)
        except ValidationError as error:
            raise LLMInvalidOutputError("Ollama returned invalid structured output") from error

    async def aclose(self) -> None:
        await self._client.aclose()
