from app.retrieval.models import ClauseEvidence
from app.retrieval.rank import reciprocal_rank_fusion


def _clause(clause_id: int) -> ClauseEvidence:
    return ClauseEvidence(
        clause_id=clause_id,
        document_id=1,
        document_title="Test direction",
        path=str(clause_id),
        text=f"Clause {clause_id}",
        page=clause_id,
        dom_locator=None,
        source_url="https://www.rbi.org.in/test",
        score=0.0,
    )


def test_rrf_combines_lexical_and_semantic_ranks_without_duplicates() -> None:
    lexical = (_clause(1), _clause(2), _clause(3))
    semantic = (_clause(3), _clause(2), _clause(4))

    ranked = reciprocal_rank_fusion(lexical, semantic, limit=4)

    assert [item.clause_id for item in ranked] == [3, 2, 1, 4]
    assert all(item.score > 0 for item in ranked)

