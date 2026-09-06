import asyncio

import pytest
from elasticsearch import Elasticsearch

from dug.core.async_search import Search, SearchException
from dug.config import Config
from dug.core.index import Index


def is_elastic_up():
    # Built from Config so the scheme/port match what dug itself would use --
    # the es8 client rejects host dicts with no 'scheme', which made this
    # return False (and skip) even when a cluster was reachable.
    cfg = Config.from_env()
    try:
        es = Elasticsearch(
            hosts=[{
                'host': cfg.elastic_host,
                'port': cfg.elastic_port,
                'scheme': cfg.elastic_scheme,
            }],
            basic_auth=(cfg.elastic_username, cfg.elastic_password)
        )
        return es.ping()
    except Exception:
        return False


@pytest.mark.skipif(not is_elastic_up(), reason="ElasticSearch is down")
def test_search_init():
    """
    Tests if we can create a Search instance without it blowing up :D
    """
    Search(cfg=Config.from_env())


# Real Elasticsearch coverage for Index.init_indices(). Uses disposable,
# uniquely-prefixed index names (rather than the env-configured ones) so this
# test can't collide with or clobber real data on a shared cluster.
TEST_INDEX_PREFIX = "pytest_dug_index_test"


def _test_config():
    cfg = Config.from_env()
    cfg.concepts_index_name = f"{TEST_INDEX_PREFIX}_concepts"
    cfg.variables_index_name = f"{TEST_INDEX_PREFIX}_variables"
    cfg.studies_index_name = f"{TEST_INDEX_PREFIX}_studies"
    cfg.sections_index_name = f"{TEST_INDEX_PREFIX}_sections"
    cfg.kg_index_name = f"{TEST_INDEX_PREFIX}_kg"
    return cfg


@pytest.fixture
def real_index():
    # Ping before constructing: Index.__init__ calls get_es_node_count() before
    # it reaches its own ping()/SearchException check, so an unreachable cluster
    # escapes as elastic_transport.ConnectionError rather than SearchException.
    if not is_elastic_up():
        pytest.skip("ElasticSearch is down")
    search = Index(_test_config())
    yield search
    for index_name in search.indices.values():
        search.es.indices.delete(index=index_name, ignore_unavailable=True)


def test_init_indices_creates_new_indices(real_index):
    """Index.__init__ takes the 'else' branch (create) for every index the
    first time around, since none of the disposable test indices exist yet."""
    for index_name in real_index.indices.values():
        assert real_index.es.indices.exists(index=index_name)


def test_init_indices_reuses_existing_indices(real_index):
    """Calling init_indices() again hits the 'already exists' branch, which
    reads back settings via get_settings(). This is a regression test for a
    bug where the response (keyed by the real index name, e.g.
    'pytest_dug_index_test_concepts') was looked up using the internal
    index_type label (e.g. 'concepts_index') instead -- which raised a
    KeyError, or worse, silently returned another index's settings on
    clusters where a same-named index happened to exist."""
    real_index.init_indices()

    for index_type, index_name in real_index.indices.items():
        response = real_index.es.indices.get_settings(index=index_name)
        # Elasticsearch keys the settings response by the actual index name
        # that was queried, not by dug's internal index_type label.
        assert set(response.keys()) == {index_name}

        # Readable without KeyError -- proves the "already exists" branch
        # completes end-to-end against a real index.
        assert "number_of_replicas" in response[index_name]["settings"]["index"]


# Sorting against a real cluster. The mocked unit tests pin the shape of the
# generated query body; these prove elasticsearch actually accepts it and orders
# documents the way we claim.

STUDIES = [
    {"id": "STUDY_LATE", "name": "Late study", "description": "d", "action": "",
     "element_type": "study", "parents": [], "programs": ["p1"],
     "metadata": {"Project End Date": "2024-04-30T12:04:00Z"},
     "tags": [{"category": "Research Network", "value": "zeta"}]},
    {"id": "STUDY_EARLY", "name": "Early study", "description": "d", "action": "",
     "element_type": "study", "parents": [], "programs": ["p2"],
     "metadata": {"Project End Date": "2019-07-15T12:07:00Z"},
     "tags": [{"category": "Research Network", "value": "alpha"}]},
    {"id": "STUDY_UNDATED", "name": "Undated study", "description": "d", "action": "",
     "element_type": "study", "parents": [], "programs": ["p3"],
     "metadata": {},
     "tags": [{"category": "Research Network", "value": "mu"}]},
]


@pytest.fixture
def studies_index(real_index):
    """Loads the three fixture studies into the disposable studies index."""
    index_name = real_index.indices["studies_index"]
    for study in STUDIES:
        real_index.index_doc(index=index_name, doc=study, doc_id=study["id"])
    real_index.es.indices.refresh(index=index_name)
    return index_name


def _sorted_ids(index_name, sort, **kwargs):
    search = Search(cfg=_test_config())
    try:
        hits, _total, _aggs = asyncio.run(search.search_elements(
            index_name, query="study", sort=sort, **kwargs))
    finally:
        asyncio.run(search.es.close())
    return [hit["_source"]["id"] for hit in hits], hits


def test_sort_by_project_end_date_desc(studies_index):
    """Descending date sort, with undated studies last.

    Elasticsearch's own default puts missing values *first* on a descending sort,
    which would float every undated study to the top -- the opposite of what a
    'most recently ended' listing means.
    """
    ids, hits = _sorted_ids(
        studies_index, [{"field": "metadata.Project End Date", "order": "desc"}])
    assert ids == ["STUDY_LATE", "STUDY_EARLY", "STUDY_UNDATED"]
    # track_scores keeps the relevance signal alive alongside an explicit sort.
    assert all(hit["_score"] is not None for hit in hits)


def test_sort_by_project_end_date_asc(studies_index):
    "Ascending date sort, still with undated studies last"
    ids, _hits = _sorted_ids(
        studies_index, [{"field": "metadata.Project End Date", "order": "asc"}])
    assert ids == ["STUDY_EARLY", "STUDY_LATE", "STUDY_UNDATED"]


def test_sort_on_nested_tag_value(studies_index):
    "tags is a nested field; sorting on it needs the derived nested path"
    ids, _hits = _sorted_ids(studies_index, [{"field": "tags.value", "order": "asc"}])
    assert ids == ["STUDY_EARLY", "STUDY_UNDATED", "STUDY_LATE"]


def test_sort_on_multivalued_field_with_mode(studies_index):
    "mode picks which value of a multi-valued field to sort on"
    ids, _hits = _sorted_ids(
        studies_index,
        [{"field": "programs.keyword", "order": "desc", "mode": "max"}])
    assert ids == ["STUDY_UNDATED", "STUDY_EARLY", "STUDY_LATE"]


def test_sort_on_unmapped_field_raises_search_exception(studies_index):
    "A bad sort field is the caller's mistake and must name itself in the error"
    with pytest.raises(SearchException) as excinfo:
        _sorted_ids(studies_index, [{"field": "no_such_field", "order": "asc"}])
    assert "no_such_field" in excinfo.value.details


def test_sort_on_text_field_raises_search_exception(studies_index):
    """`name` is mapped as text with no .keyword subfield, so it isn't sortable.

    This is the mistake callers are most likely to make, so the error has to be
    legible rather than a 500.
    """
    with pytest.raises(SearchException) as excinfo:
        _sorted_ids(studies_index, [{"field": "name", "order": "asc"}])
    assert "fielddata" in excinfo.value.details.lower()
