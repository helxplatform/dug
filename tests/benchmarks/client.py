"""Thin HTTP client for Dug v2.0 search endpoints."""
from __future__ import annotations

import httpx

from .config import BASE_URL, DEFAULT_SIZE
from .models import ActualResult


class DugSearchClient:
    """Synchronous client that hits the v2.0 endpoints."""

    def __init__(self, base_url: str = BASE_URL, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def search(
        self,
        endpoint: str,
        query: str,
        concept_id: str | None = None,
        size: int = DEFAULT_SIZE,
        offset: int = 0,
    ) -> list[ActualResult]:
        """Query a v2.0 endpoint and return parsed results.

        Args:
            endpoint: One of "concepts", "variables", "studies", "cdes"
            query: Search text
            concept_id: Optional concept CURIE for filtering
            size: Max results to return
            offset: Pagination offset

        Returns:
            List of ActualResult with id, name, score, position
        """
        url = f"{self.base_url}/{endpoint}"
        payload: dict = {"query": query, "size": size, "offset": offset}
        if concept_id:
            payload["concept"] = concept_id

        with httpx.Client(timeout=self.timeout) as http:
            resp = http.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for i, item in enumerate(data.get("results", [])):
            results.append(ActualResult(
                id=item.get("id", ""),
                name=item.get("name", ""),
                score=item.get("score", 0.0),
                position=i + 1,
            ))
        return results
