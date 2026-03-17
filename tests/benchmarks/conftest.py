"""Pytest fixtures for search quality benchmarks."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from .client import DugSearchClient
from .config import BASE_URL, EXPECTATIONS_DIR
from .models import Expectation


@pytest.fixture(scope="session")
def dug_client():
    """Shared API client for the benchmark session."""
    return DugSearchClient(base_url=BASE_URL)


def load_expectations(endpoint: str) -> list[Expectation]:
    """Load curated expectations for an endpoint."""
    path = EXPECTATIONS_DIR / f"{endpoint}.json"
    if not path.exists():
        return []
    with open(path) as f:
        raw = json.load(f)
    return [Expectation(**e) for e in raw]


def _collect_test_cases():
    """Collect all curated expectation files and yield (endpoint, expectation) pairs."""
    cases = []
    for endpoint_file in sorted(EXPECTATIONS_DIR.glob("*.json")):
        endpoint = endpoint_file.stem
        expectations = load_expectations(endpoint)
        for exp in expectations:
            # Only include curated expectations (at least one graded result)
            has_grades = any(r.relevance_grade is not None for r in exp.expected_results)
            if has_grades or exp.must_appear:
                case_id = f"{endpoint}:{exp.query}"
                if exp.concept_id:
                    case_id += f"[{exp.concept_id}]"
                cases.append(pytest.param(exp, id=case_id))
    return cases


def pytest_collection_modifyitems(config, items):
    """Skip benchmark tests if no expectations are curated."""
    expectations_exist = any(EXPECTATIONS_DIR.glob("*.json"))
    if not expectations_exist:
        skip = pytest.mark.skip(reason="No curated expectations found in data/expectations/")
        for item in items:
            if "benchmarks" in str(item.fspath):
                item.add_marker(skip)
