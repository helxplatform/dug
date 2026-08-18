"""Unit tests for the /ingestion_metadata endpoint and its search method.

Elasticsearch is stubbed throughout, so these run without a live cluster.
"""

import asyncio
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from dug import server
from dug.config import Config
from dug.core.async_search import Search

# Doc counts keyed by the search body each _count call produces, so a stub can hand
# back a different number per query without depending on call ordering.
CONCEPTS = 11
SECTIONS = 22
STUDIES = 33
VARIABLES_TOTAL = 100
CDES = 40
VARIABLES = 60
CDES_MAPPED = 7
VARIABLES_MAPPED = 9

INGESTED_AT = "2026-08-17T04:00:00+00:00"
# 2026-08-01T00:00:00Z in epoch millis, as elasticsearch reports index creation.
CREATION_DATE = "1785542400000"


def _classify(index, body):
    """Identifies which of the eight counts a search body is asking for."""
    filters = body["query"]["bool"]["filter"]
    terms = {}
    for clause in filters:
        terms.update(clause.get("term", {}))
    is_cde = terms.get("is_cde")
    ranges = [c for c in filters if "range" in c]

    if index == "sections_index":
        # CDE sets/CRFs live here, so the study-mapping count is a sections query.
        return CDES_MAPPED if ranges else SECTIONS
    if index != "variables_index":
        return {"concepts_index": CONCEPTS, "studies_index": STUDIES}[index]
    if ranges:
        return VARIABLES_MAPPED
    if is_cde is True:
        return CDES
    if is_cde is False:
        return VARIABLES
    return VARIABLES_TOTAL


def _es_stub(ingested=True):
    """An AsyncElasticsearch stand-in covering search, get_mapping and get_settings."""
    es = mock.AsyncMock()

    async def search(index=None, body=None, **kwargs):
        return {"hits": {"total": {"value": _classify(index, body)}}}

    async def get_mapping(index=None, **kwargs):
        meta = {"ingested_at": INGESTED_AT} if ingested else {}
        return {name: {"mappings": {"_meta": meta}} for name in index}

    async def get_settings(index=None, **kwargs):
        return {name: {"settings": {"index": {"creation_date": CREATION_DATE}}}
                for name in index}

    es.search = search
    es.indices.get_mapping = get_mapping
    es.indices.get_settings = get_settings
    return es


def _run(ingested=True):
    search = Search(Config())
    search.es = _es_stub(ingested=ingested)
    return asyncio.run(search.get_ingestion_metadata())


def test_document_counts_are_reported_per_index():
    "Each index reports its own doc count, and variables splits into variables and cdes"
    result = _run()
    indices = result["indices"]
    assert indices["concepts"]["doc_count"] == CONCEPTS
    assert indices["sections"]["doc_count"] == SECTIONS
    assert indices["studies"]["doc_count"] == STUDIES

    variables = indices["variables"]
    assert variables["doc_count"] == VARIABLES_TOTAL
    assert variables["variable_count"] == VARIABLES
    assert variables["cde_count"] == CDES
    # The whole point of reporting all three: the split must account for the index.
    assert variables["variable_count"] + variables["cde_count"] == variables["doc_count"]


def test_index_names_come_from_config():
    "Reported index names are the configured ones, not the response keys"
    result = _run()
    assert result["indices"]["concepts"]["index"] == "concepts_index"
    assert result["indices"]["variables"]["index"] == "variables_index"


def _capture_bodies():
    """Runs get_ingestion_metadata, returning (result, [(index, body), ...])."""
    search = Search(Config())
    seen = []

    async def capture(index=None, body=None, **kwargs):
        seen.append((index, body))
        return {"hits": {"total": {"value": _classify(index, body)}}}

    search.es = _es_stub()
    search.es.search = capture
    return asyncio.run(search.get_ingestion_metadata()), seen


def test_mapping_counts_use_the_size_runtime_field():
    """Both cross-reference counts are filtered on `size_gt`, not `exists`.

    The variables index maps `metadata` as `flattened`, where `exists` matches only a
    full leaf path -- an exists clause on `metadata.cde_mapping` returns zero.
    """
    result, seen = _capture_bodies()

    assert result["mappings"]["cdes_with_study_mappings"] == CDES_MAPPED
    assert result["mappings"]["variables_with_cde_mappings"] == VARIABLES_MAPPED

    runtime_fields = set()
    for _, body in seen:
        runtime_fields.update(body.get("runtime_mappings", {}))
        assert not [c for c in body["query"]["bool"]["filter"] if "exists" in c]
    assert runtime_fields == {
        "metadata.study_mappings_calculated_size",
        "metadata.cde_mapping_calculated_size",
    }


def test_study_mapping_count_is_taken_from_the_sections_index():
    """CDE sets/CRFs live in the sections index, not among is_cde variables.

    `metadata.study_mappings` exists only on section documents, so querying the
    variables index for it silently returns zero.
    """
    _, seen = _capture_bodies()

    study_mapping_queries = [
        (index, body) for index, body in seen
        if "metadata.study_mappings_calculated_size" in body.get("runtime_mappings", {})
    ]
    assert len(study_mapping_queries) == 1
    index, body = study_mapping_queries[0]
    assert index == "sections_index"
    # Sections have no is_cde field; filtering on it would zero the count.
    terms = {}
    for clause in body["query"]["bool"]["filter"]:
        terms.update(clause.get("term", {}))
    assert "is_cde" not in terms


def test_cde_mapping_count_is_restricted_to_non_cde_variables():
    "The variable-side count runs against the variables index with is_cde false"
    _, seen = _capture_bodies()

    cde_mapping_queries = [
        (index, body) for index, body in seen
        if "metadata.cde_mapping_calculated_size" in body.get("runtime_mappings", {})
    ]
    assert len(cde_mapping_queries) == 1
    index, body = cde_mapping_queries[0]
    assert index == "variables_index"
    terms = {}
    for clause in body["query"]["bool"]["filter"]:
        terms.update(clause.get("term", {}))
    assert terms["is_cde"] is False


def test_ingest_date_is_read_from_index_meta():
    "A pipeline-stamped index reports its ingested_at alongside the creation date"
    indices = _run()["indices"]
    for entry in indices.values():
        assert entry["ingested_at"] == INGESTED_AT
        assert entry["index_created_at"] == "2026-08-01T00:00:00+00:00"


def test_unstamped_index_reports_null_ingest_date():
    """An index no pipeline has stamped reports null rather than its creation date.

    Substituting the creation date would make a never-ingested index look fresh.
    """
    indices = _run(ingested=False)["indices"]
    for entry in indices.values():
        assert entry["ingested_at"] is None
        assert entry["index_created_at"] == "2026-08-01T00:00:00+00:00"


def test_missing_index_metadata_does_not_fail_the_request():
    "Counts are still returned when the index metadata APIs error out"
    from elasticsearch import ApiError

    search = Search(Config())
    search.es = _es_stub()

    async def boom(*args, **kwargs):
        raise ApiError("nope", meta=mock.Mock(status=403), body={})

    search.es.indices.get_mapping = boom
    result = asyncio.run(search.get_ingestion_metadata())

    assert result["indices"]["concepts"]["doc_count"] == CONCEPTS
    assert result["indices"]["concepts"]["ingested_at"] is None
    assert result["indices"]["concepts"]["index_created_at"] is None


def test_endpoint_returns_the_search_payload():
    "The route passes the search result through and it satisfies the response model"
    payload = _run()
    with mock.patch.object(server.search, "get_ingestion_metadata",
                           mock.AsyncMock(return_value=payload)):
        response = TestClient(server.APP).get("/ingestion_metadata")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["indices"]["variables"]["cde_count"] == CDES
    assert body["mappings"]["variables_with_cde_mappings"] == VARIABLES_MAPPED
