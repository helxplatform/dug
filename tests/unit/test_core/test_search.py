import pytest

from dug.config import Config
from dug.core.search import Search, SearchException

default_indices = ['concepts_index', 'variables_index', 'kg_index']

host = 'localhost'
port = 9200
username = 'elastic'
password = 'hunter2'
nboost_host = 'localhost'
hosts = [{'host': host, 'port': port}]


def test_init(elastic):
    cfg = Config(elastic_host='localhost',
                 elastic_username='elastic',
                 elastic_password='hunter2',
                 nboost_host='localhost')

    search = Search(cfg)

    assert search.indices == default_indices
    assert search.hosts == hosts
    assert search.es is elastic


def test_init_no_ping(elastic):
    elastic.down()
    with pytest.raises(SearchException):
        _search = Search(Config.from_env())


def test_init_indices(elastic):
    search = Search(Config.from_env())
    assert elastic.indices.call_count == 3

    # Should take no action if called again
    search.init_indices()
    assert elastic.indices.call_count == 3


def test_index_doc(elastic):
    search = Search(Config.from_env())

    assert len(elastic.indices.get_index('concepts_index').values) == 0
    search.index_doc('concepts_index', {'name': 'sample'}, "ID:1")
    assert len(elastic.indices.get_index('concepts_index').values) == 1
    assert elastic.indices.get_index('concepts_index').get("ID:1") == {'name': 'sample'}


def test_update_doc(elastic):
    search = Search(Config.from_env())

    search.index_doc('concepts_index', {'name': 'sample'}, "ID:1")
    search.update_doc('concepts_index', {'name': 'new value!'}, "ID:1")
    assert elastic.indices.get_index('concepts_index').get("ID:1") == {'name': 'new value!'}

