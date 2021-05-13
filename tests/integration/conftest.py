import logging
import os
from pathlib import Path

import redis
from elasticsearch import Elasticsearch

TEST_DATA_DIR = Path(__file__).parent.resolve() / 'data'


logger = logging.getLogger('dug')


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
            http_auth=(username, password)
        )
        return es.ping()
    except Exception as e:
        logger.error(f"Unexpected {e.__class__.__name__}: {e}")
        return False


def is_redis_up():
    redis_client = redis.StrictRedis(
        host=os.environ.get('REDIS_HOST'),
        port=os.environ.get('REDIS_PORT'),
        password=os.environ.get('REDIS_PASSWORD'),
    )
    try:
        return redis_client.ping()
    except Exception as e:
        logger.error(f"Unexpected {e.__class__.__name__}: {e}")
        return False
