import pytest
from elasticsearch import Elasticsearch
from redis import StrictRedis

from dug.config import Config
from dug.utils import ServiceFactory, health_check
from tests.unit.conftest import MockServiceFactory


@pytest.mark.skip("Implement this test")
def test_complex_handler():
    pass


@pytest.mark.skip("Implement this test")
def test_get_dbgap_var_link():
    pass


@pytest.mark.skip("Implement this test")
def test_get_dbgap_study_link():
    pass


@pytest.mark.skip("Implement this test")
def test_parse_study_name_from_filename():
    pass


def test_service_factory():
    redis_pass = 'dummy-redis-pass'
    redis_port = 6789
    redis_host = 'dummy-redis-host'
    es_password = "dummy-es-password"
    es_user = "dummy-es-user"
    es_port = 1234
    es_host = "dummy-es-host"

    config = Config(
        elastic_host=es_host,
        elastic_port=es_port,
        elastic_username=es_user,
        elastic_password=es_password,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_password=redis_pass,
    )

    factory = ServiceFactory(
        config,
    )

    redis = factory.build_redis()

    es = factory.build_elasticsearch()

    assert isinstance(redis, StrictRedis)
    assert redis.connection_pool.connection_kwargs['password'] == redis_pass
    assert redis.connection_pool.connection_kwargs['port'] == redis_port
    assert redis.connection_pool.connection_kwargs['host'] == redis_host

    assert isinstance(es, Elasticsearch)


def test_health_check(service_factory):
    config = Config()
    factory: MockServiceFactory = service_factory(config)
    redis = factory.build_redis()
    es = factory.build_elasticsearch()

    assert redis.ping()
    assert es.ping()

    result = health_check(factory)
    assert result.ok
    assert result.services['elasticsearch'].ok
    assert result.services['redis'].ok

    factory.bring_down('redis')
    result = health_check(factory)
    assert not result.ok
    assert result.services['elasticsearch'].ok
    assert not result.services['redis'].ok

    factory.bring_down('elasticsearch')
    result = health_check(factory)
    assert not result.ok
    assert not result.services['elasticsearch'].ok
    assert not result.services['redis'].ok

    factory.bring_up('redis')
    result = health_check(factory)
    assert not result.ok
    assert not result.services['elasticsearch'].ok
    assert result.services['redis'].ok
