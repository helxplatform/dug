"""Search quality benchmark tests.

Run with: pytest tests/benchmarks/ -v
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from .client import DugSearchClient
from .config import BASE_URL, SNAPSHOTS_DIR
from .conftest import _collect_test_cases
from .metrics import (
    check_must_appear,
    check_must_not_appear,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall,
)
from .models import BenchmarkResult, Expectation


# Collect all benchmark results for the report
_session_results: list[dict] = []


@pytest.fixture(scope="session")
def client():
    return DugSearchClient(base_url=BASE_URL)


@pytest.fixture(scope="session", autouse=True)
def write_report():
    """Write aggregated results at end of session."""
    yield
    if _session_results:
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = SNAPSHOTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w") as f:
            json.dump({
                "run_at": datetime.now().isoformat(),
                "base_url": BASE_URL,
                "results": _session_results,
            }, f, indent=2)
        print(f"\nBenchmark report saved to {report_path}")


@pytest.mark.parametrize("expectation", _collect_test_cases())
def test_search_quality(client: DugSearchClient, expectation: Expectation):
    """Test search quality for a single query+endpoint against curated expectations."""
    actual = client.search(
        endpoint=expectation.endpoint,
        query=expectation.query,
        concept_id=expectation.concept_id,
        size=max(20, len(expectation.expected_results)),
    )

    # Compute metrics
    result = BenchmarkResult(
        query=expectation.query,
        endpoint=expectation.endpoint,
        concept_id=expectation.concept_id,
        ndcg_at_5=ndcg_at_k(actual, expectation, 5),
        ndcg_at_10=ndcg_at_k(actual, expectation, 10),
        mrr=mrr(actual, expectation),
        precision_at_5=precision_at_k(actual, expectation, 5),
        precision_at_10=precision_at_k(actual, expectation, 10),
        recall=recall(actual, expectation),
        total_results=len(actual),
        missing_must_appear=check_must_appear(actual, expectation),
        unexpected_must_not_appear=check_must_not_appear(actual, expectation),
        actual_results=actual,
    )

    # Store for session report
    _session_results.append(result.model_dump(exclude={"actual_results"}))

    # Print metrics for visibility
    print(f"\n  Query: '{expectation.query}' | Endpoint: /{expectation.endpoint}")
    print(f"  NDCG@5={result.ndcg_at_5:.3f}  NDCG@10={result.ndcg_at_10:.3f}  "
          f"MRR={result.mrr:.3f}  P@5={result.precision_at_5:.3f}  P@10={result.precision_at_10:.3f}  "
          f"Recall={result.recall:.3f}")

    # Assertions
    if expectation.must_appear:
        assert not result.missing_must_appear, (
            f"Missing required results: {result.missing_must_appear}"
        )

    if expectation.must_not_appear:
        assert not result.unexpected_must_not_appear, (
            f"Unexpected results present: {result.unexpected_must_not_appear}"
        )

    if expectation.min_ndcg_at_10 > 0:
        assert result.ndcg_at_10 >= expectation.min_ndcg_at_10, (
            f"NDCG@10 ({result.ndcg_at_10:.3f}) below threshold ({expectation.min_ndcg_at_10:.3f})"
        )
