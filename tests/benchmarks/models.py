"""Data models for search quality benchmarking."""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class SearchTerm(BaseModel):
    """A single search term to benchmark."""
    query: str
    endpoints: list[str] = Field(default_factory=lambda: ["concepts"])
    concept_id: Optional[str] = None


class ExpectedResult(BaseModel):
    """A single expected result with relevance grading."""
    id: str
    name: str
    relevance_grade: Optional[int] = Field(
        default=None,
        description="0=irrelevant, 1=marginal, 2=relevant, 3=highly relevant. null=uncurated"
    )


class Expectation(BaseModel):
    """Curated expectations for a single query+endpoint combination."""
    query: str
    endpoint: str
    concept_id: Optional[str] = None
    curated_at: Optional[date] = None
    expected_results: list[ExpectedResult] = Field(default_factory=list)
    must_appear: list[str] = Field(default_factory=list)
    must_not_appear: list[str] = Field(default_factory=list)
    min_ndcg_at_10: float = Field(default=0.0, description="Minimum acceptable NDCG@10")


class ActualResult(BaseModel):
    """A result returned from the live API."""
    id: str
    name: str
    score: float = 0.0
    position: int = 0


class BenchmarkResult(BaseModel):
    """Metrics for a single query+endpoint benchmark run."""
    query: str
    endpoint: str
    concept_id: Optional[str] = None
    ndcg_at_5: float = 0.0
    ndcg_at_10: float = 0.0
    mrr: float = 0.0
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    recall: float = 0.0
    total_results: int = 0
    missing_must_appear: list[str] = Field(default_factory=list)
    unexpected_must_not_appear: list[str] = Field(default_factory=list)
    actual_results: list[ActualResult] = Field(default_factory=list)
