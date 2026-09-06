"""Unit tests for the v2.0 search endpoints.

`search.search_elements` is stubbed throughout, so these run without elasticsearch.
"""

from unittest import mock

import pytest
from fastapi.testclient import TestClient

from dug import server
from dug.core.async_search import SearchException

V2_ROUTES = ("/concepts", "/variables", "/studies", "/cdes")

# Routes that surface `score` on each result. /studies does not.
SCORED_ROUTES = ("/concepts", "/variables", "/cdes")


@pytest.fixture(name="client")
def _client():
    return TestClient(server.APP)


def _hit(score=1.0):
    """A minimal elasticsearch hit that satisfies every v2.0 response model."""
    return {
        "_id": "HDP00166",
        "_score": score,
        "_explanation": {},
        "_source": {
            "id": "HDP00166",
            "name": "A study",
            "description": "A description",
            "action": "https://example.org/HDP00166",
            "identifiers": [],
        },
    }


def _stub_search_elements(hits=None, total=1):
    """Patches search.search_elements, returning the mock so calls can be inspected."""
    stub = mock.AsyncMock(
        return_value=(hits if hits is not None else [_hit()], total, {}))
    return mock.patch.object(server.search, "search_elements", stub), stub


def test_sort_is_forwarded_to_search_elements(client):
    "A sort in the request body reaches search_elements on every v2.0 route"
    sort = [{"field": "metadata.Project End Date", "order": "desc"}]
    for route in V2_ROUTES:
        patcher, stub = _stub_search_elements()
        with patcher:
            response = client.post(route, json={"query": "opioid", "sort": sort})
        assert response.status_code == 200, (route, response.text)
        # Routes splat the whole request model, so a new field here is only safe
        # if search_elements accepts a matching keyword argument.
        assert stub.call_args.kwargs["sort"] == [
            {"field": "metadata.Project End Date", "order": "desc",
             "mode": None, "missing": None}
        ]


def test_sort_is_optional(client):
    "Omitting sort still works and passes an empty list through"
    for route in V2_ROUTES:
        patcher, stub = _stub_search_elements()
        with patcher:
            response = client.post(route, json={"query": "opioid"})
        assert response.status_code == 200, (route, response.text)
        assert stub.call_args.kwargs["sort"] == []


def test_null_score_does_not_break_the_response(client):
    """Elasticsearch returns a null _score when sorting, but `score` is a non-nullable
    float on every response model, so an unguarded assignment is a 500."""
    for route in SCORED_ROUTES:
        patcher, _ = _stub_search_elements(hits=[_hit(score=None)])
        with patcher:
            response = client.post(route, json={"query": "opioid"})
        assert response.status_code == 200, (route, response.text)

    # Only /concepts serializes score back out; the others drop it in
    # get_response_dict() but still have to validate it.
    patcher, _ = _stub_search_elements(hits=[_hit(score=None)])
    with patcher:
        response = client.post("/concepts", json={"query": "opioid"})
    assert response.json()["results"][0]["score"] == 0


@pytest.mark.parametrize("sort", [
    [{"field": "name.keyword", "order": "sideways"}],
    [{"field": "name.keyword", "mode": "stddev"}],
    [{"field": "name.keyword", "missing": "_middle"}],
    [{"field": "   "}],
    [{"field": "_id"}],
    [{"order": "asc"}],
    [{"field": f"f{i}"} for i in range(6)],
])
def test_invalid_sort_is_rejected(client, sort):
    "Bad sort input is a validation error, not something elasticsearch has to catch"
    patcher, stub = _stub_search_elements()
    with patcher:
        response = client.post("/studies", json={"query": "opioid", "sort": sort})
    assert response.status_code == 422, response.text
    stub.assert_not_called()


def test_max_sort_fields_is_allowed(client):
    "The cap is inclusive"
    patcher, _ = _stub_search_elements()
    with patcher:
        response = client.post("/studies", json={
            "query": "opioid", "sort": [{"field": f"f{i}"} for i in range(5)]})
    assert response.status_code == 200, response.text


def test_score_and_doc_are_sortable(client):
    "_score and _doc are the two underscore-prefixed fields that are legal"
    for field in ("_score", "_doc"):
        patcher, _ = _stub_search_elements()
        with patcher:
            response = client.post("/studies", json={
                "query": "opioid", "sort": [{"field": field}]})
        assert response.status_code == 200, (field, response.text)


def test_search_exception_returns_400(client):
    "A query elasticsearch rejects is the caller's fault, not a 500"
    stub = mock.AsyncMock(side_effect=SearchException(
        message="Elasticsearch rejected the search request.",
        details="No mapping found for [nope] in order to sort on"))
    with mock.patch.object(server.search, "search_elements", stub):
        response = client.post("/studies", json={
            "query": "opioid", "sort": [{"field": "nope"}]})
    assert response.status_code == 400, response.text
    assert "No mapping found for [nope]" in response.json()["details"]
