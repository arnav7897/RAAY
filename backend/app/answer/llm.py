from typing import Protocol, TypeVar

from pydantic import BaseModel

OutputT = TypeVar("OutputT", bound=BaseModel)


class LLM(Protocol):
    async def complete(self, prompt: str, schema: type[OutputT]) -> OutputT: ...


class LLMError(RuntimeError):
    pass


class LLMInvalidOutputError(LLMError):
    pass


class LLMRefusalError(LLMError):
    pass


class LLMTimeoutError(LLMError):
    pass


class LLMQuotaError(LLMError):
    pass


class LLMProviderError(LLMError):
    pass

