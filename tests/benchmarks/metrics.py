"""Information retrieval metrics for search quality evaluation."""
from __future__ import annotations

import math

from .models import ActualResult, Expectation


def _build_relevance_map(expectation: Expectation) -> dict[str, int]:
    """Map result ID → relevance grade from curated expectations."""
    return {
        r.id: (r.relevance_grade if r.relevance_grade is not None else 0)
        for r in expectation.expected_results
    }


def dcg_at_k(relevances: list[int], k: int) -> float:
    """Discounted Cumulative Gain at position k."""
    score = 0.0
    for i, rel in enumerate(relevances[:k]):
        score += (2 ** rel - 1) / math.log2(i + 2)  # i+2 because log2(1)=0
    return score


def ndcg_at_k(actual: list[ActualResult], expectation: Expectation, k: int) -> float:
    """Normalized Discounted Cumulative Gain at position k.

    Measures ranking quality: are highly relevant results near the top?
    Returns a value between 0.0 and 1.0 where 1.0 is perfect ranking.
    """
    relevance_map = _build_relevance_map(expectation)
    if not relevance_map:
        return 0.0

    # Actual relevances in the order returned
    actual_rels = [relevance_map.get(r.id, 0) for r in actual[:k]]

    # Ideal relevances (sorted descending)
    ideal_rels = sorted(relevance_map.values(), reverse=True)[:k]

    actual_dcg = dcg_at_k(actual_rels, k)
    ideal_dcg = dcg_at_k(ideal_rels, k)

    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg


def mrr(actual: list[ActualResult], expectation: Expectation) -> float:
    """Mean Reciprocal Rank: 1/position of first relevant result.

    A relevant result is one with relevance_grade >= 2.
    Returns 0.0 if no relevant result is found.
    """
    relevance_map = _build_relevance_map(expectation)
    for r in actual:
        if relevance_map.get(r.id, 0) >= 2:
            return 1.0 / r.position
    return 0.0


def precision_at_k(actual: list[ActualResult], expectation: Expectation, k: int) -> float:
    """Of the top-k results, what fraction are relevant (grade >= 2)?"""
    relevance_map = _build_relevance_map(expectation)
    if k == 0:
        return 0.0
    top_k = actual[:k]
    relevant_count = sum(1 for r in top_k if relevance_map.get(r.id, 0) >= 2)
    return relevant_count / min(k, len(top_k)) if top_k else 0.0


def recall(actual: list[ActualResult], expectation: Expectation) -> float:
    """Of all must_appear IDs, what fraction appeared in results?"""
    if not expectation.must_appear:
        return 1.0
    actual_ids = {r.id for r in actual}
    found = sum(1 for eid in expectation.must_appear if eid in actual_ids)
    return found / len(expectation.must_appear)


def check_must_appear(actual: list[ActualResult], expectation: Expectation) -> list[str]:
    """Return list of must_appear IDs that are missing from results."""
    actual_ids = {r.id for r in actual}
    return [eid for eid in expectation.must_appear if eid not in actual_ids]


def check_must_not_appear(actual: list[ActualResult], expectation: Expectation) -> list[str]:
    """Return list of must_not_appear IDs that showed up in results."""
    actual_ids = {r.id for r in actual}
    return [eid for eid in expectation.must_not_appear if eid in actual_ids]
