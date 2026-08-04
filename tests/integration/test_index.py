import os

import pytest
from elasticsearch import Elasticsearch

from dug.core.async_search import Search
from dug.config import Config
from dug.core.index import Index, SearchException


def is_elastic_up():
    host = os.environ.get('ELASTIC_API_HOST')
    port = 9200
    hosts = [
        {
            'host': host,
            'port': port
        }
    ]
    username = os.environ.get('ELASTIC_USERNAME')
    password = os.environ.get('ELASTIC_PASSWORD')
    try:
        es = Elasticsearch(
            hosts=hosts,
            basic_auth=(username, password)
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
    try:
        search = Index(_test_config())
    except SearchException:
        pytest.skip("ElasticSearch is down")
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
