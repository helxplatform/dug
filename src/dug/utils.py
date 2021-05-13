from dataclasses import dataclass
from typing import Dict, Optional

import redis
from elasticsearch import Elasticsearch

from dug.config import Config


def complex_handler(obj):
    if hasattr(obj, 'jsonable'):
        return obj.jsonable()
    else:
        raise TypeError(f'Object of type {type(obj)} with value of {type(obj)} is not JSON serializable')


def get_dbgap_var_link(study_id, variable_id):
    base_url = "https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/variable.cgi"
    return f'{base_url}?study_id={study_id}&phv={variable_id}'


def get_dbgap_study_link(study_id):
    base_url = "https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi"
    return f'{base_url}?study_id={study_id}'


@dataclass
class HealthStatus:
    ok: bool
    services: Optional[Dict[str, "HealthStatus"]] = None


@dataclass
class ServiceFactory:
    config: Config

    def build_redis(self) -> redis.Redis:
        return redis.StrictRedis(
            host=self.config.redis_host,
            port=self.config.redis_port,
            password=self.config.redis_password,
        )

    def build_elasticsearch(self) -> Elasticsearch:
        hosts = [{'host': self.config.elastic_host, 'port': self.config.elastic_port}]

        return Elasticsearch(
            hosts=hosts,
            http_auth=(self.config.elastic_username, self.config.elastic_password)
        )


def health_check(service_factory: ServiceFactory) -> HealthStatus:

    redis_status = service_factory.build_redis().ping()

    elasticsearch_status = service_factory.build_elasticsearch().ping()

    api_status = redis_status and elasticsearch_status

    return HealthStatus(
        ok=api_status,
        services={
            'redis': HealthStatus(redis_status),
            'elasticsearch': HealthStatus(elasticsearch_status),
        },
    )
