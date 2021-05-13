import pytest

from dug.config import Config
from dug.utils import ServiceFactory
from tests.integration.conftest import is_elastic_up, is_redis_up


@pytest.mark.skipif(not is_elastic_up(), reason="ElasticSearch is down")
def test_build_elasticsearch():
    config = Config.from_env()
    factory = ServiceFactory(config)
    es = factory.build_elasticsearch()
    assert es.ping()


@pytest.mark.skipif(not is_redis_up(), reason="Redis is down")
def test_build_redis():
    config = Config.from_env()
    factory = ServiceFactory(config)
    redis = factory.build_redis()
    assert redis.ping()
