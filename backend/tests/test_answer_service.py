from collections.abc import Sequence

import pytest

from app.answer.models import AnswerDraft, ClaimDraft
from app.answer.service import INSUFFICIENT_EVIDENCE, AnswerService
from app.retrieval.models import ClauseEvidence


def _evidence() -> ClauseEvidence:
    return ClauseEvidence(
        clause_id=42,
        document_id=8,
        document_title="Review of Qualifying Assets Criteria",
        path="8.1",
        text="Qualifying assets shall constitute a minimum of sixty per cent of total assets.",
        page=None,
        dom_locator="p:nth-of-type(12)",
        source_url="https://www.rbi.org.in/example",
        score=1.0,
    )


class FakeRetriever:
    def __init__(self, evidence: Sequence[ClauseEvidence]) -> None:
        self.evidence = tuple(evidence)
        self.calls: list[tuple[str, tuple[int, ...], int]] = []

    async def search(
        self,
        question: str,
        document_ids: tuple[int, ...],
        *,
        max_hops: int,
    ) -> tuple[ClauseEvidence, ...]:
        self.calls.append((question, document_ids, max_hops))
        return self.evidence


class FakeLLM:
    def __init__(self, result: AnswerDraft) -> None:
        self.result = result
        self.prompts: list[str] = []

    async def complete(self, prompt: str, schema: type[AnswerDraft]) -> AnswerDraft:
        assert schema is AnswerDraft
        self.prompts.append(prompt)
        return self.result


@pytest.mark.asyncio
async def test_answer_returns_claim_with_source_location() -> None:
    retriever = FakeRetriever((_evidence(),))
    llm = FakeLLM(
        AnswerDraft(
            claims=[
                ClaimDraft(
                    text="The minimum is sixty per cent.",
                    clause_id=42,
                    quote="minimum of sixty per cent of total assets",
                )
            ]
        )
    )

    result = await AnswerService(retriever, llm).answer(
        question="What is the qualifying-assets minimum?",
        document_ids=(8,),
    )

    assert result.insufficient_evidence is False
    assert result.claims[0].clause_id == 42
    assert result.claims[0].dom_locator == "p:nth-of-type(12)"
    assert result.claims[0].source_url == "https://www.rbi.org.in/example"
    assert "[Clause 42]" in llm.prompts[0]
    assert retriever.calls == [("What is the qualifying-assets minimum?", (8,), 1)]


@pytest.mark.asyncio
async def test_answer_rejects_claim_when_quote_is_absent() -> None:
    llm = FakeLLM(
        AnswerDraft(
            claims=[
                ClaimDraft(
                    text="The minimum is seventy-five per cent.",
                    clause_id=42,
                    quote="seventy-five per cent",
                )
            ]
        )
    )

    result = await AnswerService(FakeRetriever((_evidence(),)), llm).answer(
        question="What is the minimum?",
        document_ids=(8,),
    )

    assert result.insufficient_evidence is True
    assert result.answer == INSUFFICIENT_EVIDENCE
    assert result.claims == []


@pytest.mark.asyncio
async def test_answer_rejects_claim_citing_unretrieved_clause() -> None:
    llm = FakeLLM(
        AnswerDraft(
            claims=[
                ClaimDraft(text="Unsupported.", clause_id=999, quote="minimum")
            ]
        )
    )

    result = await AnswerService(FakeRetriever((_evidence(),)), llm).answer(
        question="What is the minimum?",
        document_ids=(8,),
    )

    assert result.insufficient_evidence is True
    assert result.answer == INSUFFICIENT_EVIDENCE


@pytest.mark.asyncio
async def test_answer_skips_llm_when_retrieval_has_no_evidence() -> None:
    llm = FakeLLM(AnswerDraft(claims=[]))

    result = await AnswerService(FakeRetriever(()), llm).answer(
        question="Unsupported question",
        document_ids=(8,),
    )

    assert result.insufficient_evidence is True
    assert result.answer == INSUFFICIENT_EVIDENCE
    assert llm.prompts == []

