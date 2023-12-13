"Integration tests for the async_search module"

import asyncio
from unittest import TestCase

from fastapi.testclient import TestClient
from elasticsearch.exceptions import ConnectionError
from dug.config import Config

class APISearchTestCase(TestCase):
    "API search with mocked elasticsearch"

    def test_concepts_types_parameter(self):
        "Test API concepts search with types parameter"
        cfg = Config.from_env()
        if cfg.elastic_password == "changeme":
            # Dummy config is in place, skip the test
            self.skipTest(
                "For the integration test, a populated elasticsearch "
                "instance must be available and configured in the "
                "environment variables. See dug.config for more.")

        from dug.server import APP
        client = TestClient(APP)
        types = ['anatomical entity', 'drug']
        body = {
            "index": "concepts_index",
            "query": "brain",
            "offset": 0,
            "size":20,
            "types": types
        }
        try:
            response = client.post("/search", json=body)
        except ConnectionError:
            self.fail("For the integration test, a populated elasticsearch "
                      "instance must be available and configured in the "
                      "environment variables. See dug.config for more.")
        self.assertEqual(response.status_code, 200)
        response_obj = response.json()
        response_types = set(hit['_source']['type'] for hit in
                 response_obj['result']['hits']['hits'])
        self.assertEqual(response_types, set(types))
