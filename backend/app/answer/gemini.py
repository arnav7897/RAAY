from typing import Protocol, cast

import httpx
from google import genai
from google.genai import errors
from pydantic import ValidationError

from app.answer.llm import (
    LLMInvalidOutputError,
    LLMProviderError,
    LLMQuotaError,
    LLMRefusalError,
    LLMTimeoutError,
    OutputT,
)


class _InteractionResult(Protocol):
    output_text: str | None


class GeminiLLM:
    def __init__(self, *, api_key: str, model: str, timeout_seconds: float) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def complete(self, prompt: str, schema: type[OutputT]) -> OutputT:
        try:
            interaction = await self._client.aio.interactions.create(
                model=self._model,
                input=prompt,
                store=False,
                stream=False,
                response_mime_type="application/json",
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": schema.model_json_schema(),
                },
                system_instruction=(
                    "Use only the supplied regulatory clauses. Return one cited claim per "
                    "sentence. Never use external knowledge or search grounding."
                ),
                # The Interactions API accepts request timeouts in milliseconds.
                timeout=self._timeout_seconds * 1000,
            )
        except (TimeoutError, httpx.TimeoutException) as error:
            raise LLMTimeoutError("Gemini request timed out") from error
        except errors.APIError as error:
            if getattr(error, "code", None) == 429:
                raise LLMQuotaError("Gemini quota exceeded") from error
            raise LLMProviderError("Gemini provider request failed") from error

        result = cast(_InteractionResult, interaction)
        if not result.output_text:
            raise LLMRefusalError("Gemini returned no answer")
        try:
            return schema.model_validate_json(result.output_text)
        except ValidationError as error:
            raise LLMInvalidOutputError("Gemini returned invalid structured output") from error

    async def aclose(self) -> None:
        await self._client.aio.aclose()

