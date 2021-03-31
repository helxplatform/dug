import os

import pytest
from elasticsearch import Elasticsearch

from dug.core import Search


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
    except Exception as _e:
        return False


@pytest.mark.skipif(not is_elastic_up(), reason="ElasticSearch is down")
def test_search_init():
    """
    Tests if we can create a Search instance without it blowing up :D
    """
    Search(host=os.environ.get('ELASTIC_API_HOST'), port=9200,)
