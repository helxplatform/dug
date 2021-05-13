import pytest

from dug.config import Config
from dug.core.search import Search
from tests.integration.conftest import is_elastic_up


@pytest.mark.skipif(not is_elastic_up(), reason="ElasticSearch is down")
def test_search_init():
    """
    Tests if we can create a Search instance without it blowing up :D
    """
    Search(cfg=Config.from_env())
