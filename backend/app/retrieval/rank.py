from collections.abc import Sequence

from app.retrieval.models import ClauseEvidence


def reciprocal_rank_fusion(
    lexical: Sequence[ClauseEvidence],
    semantic: Sequence[ClauseEvidence],
    *,
    limit: int,
    rank_constant: int = 60,
) -> tuple[ClauseEvidence, ...]:
    if limit < 1:
        raise ValueError("limit must be positive")

    evidence: dict[int, ClauseEvidence] = {}
    scores: dict[int, float] = {}
    for ranking in (lexical, semantic):
        for rank, item in enumerate(ranking, start=1):
            evidence.setdefault(item.clause_id, item)
            scores[item.clause_id] = scores.get(item.clause_id, 0.0) + 1.0 / (
                rank_constant + rank
            )

    ordered = sorted(scores, key=lambda clause_id: (-scores[clause_id], clause_id))
    return tuple(
        evidence[clause_id].with_score(scores[clause_id])
        for clause_id in ordered[:limit]
    )

