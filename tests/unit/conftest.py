import json
import urllib.parse
from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from unittest.mock import patch

import pytest

from dug.config import Config
from dug.utils import ServiceFactory


@dataclass
class MockResponse:
    text: str
    code: int = 200

    def json(self):
        return json.loads(self.text)


class MockApiService:
    def __init__(self, urls: Dict[str, str]):
        self.urls = urls

    def get(self, url, params: dict = None):
        if params:
            qstr = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
            url = f"{url}?{qstr}"

        text = self.urls.get(url)

        if text is None:
            return MockResponse(text="{}", code=404)
        return MockResponse(text)


@pytest.fixture
def annotator_api():
    base_url = "http://annotator.api/?content={query}"

    def _(keyword):
        return base_url.format(
            query=urllib.parse.quote(keyword)
        )

    urls = {
        _("heart attack"): json.dumps({
            "content": "heart attack",
            "spans": [
                {
                    "start": 0,
                    "end": 5,
                    "text": "heart",
                    "token": [
                        {
                            "id": "UBERON:0015230",
                            "category": [
                                "anatomical entity"
                            ],
                            "terms": [
                                "dorsal vessel heart"
                            ]
                        }
                    ]
                },
                {
                    "start": 0,
                    "end": 5,
                    "text": "heart",
                    "token": [
                        {
                            "id": "UBERON:0007100",
                            "category": [
                                "anatomical entity"
                            ],
                            "terms": [
                                "primary circulatory organ"
                            ]
                        }
                    ]
                },
                {
                    "start": 0,
                    "end": 5,
                    "text": "heart",
                    "token": [
                        {
                            "id": "UBERON:0015228",
                            "category": [
                                "anatomical entity"
                            ],
                            "terms": [
                                "circulatory organ"
                            ]
                        }
                    ]
                },
                {
                    "start": 0,
                    "end": 5,
                    "text": "heart",
                    "token": [
                        {
                            "id": "ZFA:0000114",
                            "category": [
                                "anatomical entity"
                            ],
                            "terms": [
                                "heart"
                            ]
                        }
                    ]
                },
                {
                    "start": 0,
                    "end": 5,
                    "text": "heart",
                    "token": [
                        {
                            "id": "UBERON:0000948",
                            "category": [
                                "anatomical entity"
                            ],
                            "terms": [
                                "heart"
                            ]
                        }
                    ]
                },
                {
                    "start": 0,
                    "end": 12,
                    "text": "heart attack",
                    "token": [
                        {
                            "id": "MONDO:0005068",
                            "category": [
                                "disease"
                            ],
                            "terms": [
                                "myocardial infarction (disease)"
                            ]
                        }
                    ]
                },
                {
                    "start": 0,
                    "end": 12,
                    "text": "heart attack",
                    "token": [
                        {
                            "id": "HP:0001658",
                            "category": [
                                "phenotype",
                                "quality"
                            ],
                            "terms": [
                                "Myocardial infarction"
                            ]
                        }
                    ]
                }
            ]
        }),
    }

    return MockApiService(
        urls=urls,
    )


@pytest.fixture
def normalizer_api():
    base_url = "http://normalizer.api/?curie={curie}"

    def _(curie):
        return base_url.format(
            curie=urllib.parse.quote(curie),
        )

    urls = {
        _("UBERON:0007100"): json.dumps(
            {
                "UBERON:0007100": {
                    "id": {
                        "identifier": "UBERON:0007100",
                        "label": "primary circulatory organ"
                    },
                    "equivalent_identifiers": [
                        {
                            "identifier": "UBERON:0007100",
                            "label": "primary circulatory organ"
                        }
                    ],
                    "type": [
                        "biolink:AnatomicalEntity",
                        "biolink:OrganismalEntity",
                        "biolink:BiologicalEntity",
                        "biolink:NamedThing",
                        "biolink:Entity"
                    ]
                }
            },
        ),

    }

    return MockApiService(
        urls=urls,
    )


@pytest.fixture
def synonym_api():
    base_url = "http://synonyms.api/?curie={curie}"

    def _(curie):
        return base_url.format(
            curie=urllib.parse.quote(curie),
        )
    return MockApiService(urls={
        _("UBERON:0007100"): json.dumps([
            {
                "desc": "adult heart",
                "scope": "RELATED",
                "syn_type": None,
                "xref": ""
            }
        ])
    })


@pytest.fixture()
def ontology_api():
    base_url = "http://ontology.api/?curie={curie}"

    def _(curie):
        return base_url.format(
            curie=urllib.parse.quote(curie),
        )

    return MockApiService(urls={
        _("UBERON:0007100"): json.dumps(
            {
                "taxon": {
                    "id": None,
                    "label": None
                },
                "association_counts": None,
                "xrefs": [
                    "SPD:0000130",
                    "FBbt:00003154",
                    "TADS:0000147"
                ],
                "description": "A hollow, muscular organ, which, by contracting rhythmically, keeps up the circulation of the blood or analogs[GO,modified].",
                "types": None,
                "synonyms": [
                    {
                        "val": "dorsal tube",
                        "pred": "synonym",
                        "xrefs": None
                    },
                    {
                        "val": "adult heart",
                        "pred": "synonym",
                        "xrefs": None
                    },
                    {
                        "val": "heart",
                        "pred": "synonym",
                        "xrefs": None
                    }
                ],
                "deprecated": None,
                "replaced_by": None,
                "consider": None,
                "id": "UBERON:0007100",
                "label": "primary circulatory organ",
                "iri": "http://purl.obolibrary.org/obo/UBERON_0007100",
                "category": [
                    "anatomical entity"
                ]
            }
        )
    })



@dataclass
class MockIndex:
    settings: dict
    mappings: dict
    values: dict = field(default_factory=dict)

    def index(self, id, body):
        self.values[id] = body

    def update(self, id, body):
        return self.index(id, body)

    def get(self, id):
        return self.values.get(id)

    def count(self, body):
        return len(self.values)


class MockIndices:

    def __init__(self):
        self._indices = {}
        self.call_count = 0

    def exists(self, index):
        return index in self._indices

    def create(
            self,
            index,
            body,
            **_kwargs
    ):
        self.call_count += 1
        self._indices[index] = MockIndex(**body)

    def get_index(self, index) -> MockIndex:
        return self._indices.get(index)


class MockService:
    def __init__(self):
        self._is_up = True

    def ping(self):
        return self._is_up

    def up(self):
        self._is_up = True

    def down(self):
        self._is_up = False


class MockElastic(MockService):

    def __init__(self, indices: MockIndices):
        super().__init__()
        self.indices = indices

    def index(self, index, id=None, body=None):
        self.indices.get_index(index).index(id, body)

    def update(self, index, id=None, body=None):
        self.indices.get_index(index).update(id, body)

    def ping(self):
        return self._is_up

    def count(self, body, index):
        return {
            'count': self.indices.get_index(index).count(body)
        }

    def search(self, index, body, **kwargs):
        values = self.indices.get_index(index).values
        return {
            'results': {
                k: v
                for k, v in values.items()
                if body in v
            }
        }


class MockRedis(MockService):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config


class MockServiceFactory(ServiceFactory):
    def __init__(self, config: Config):
        super().__init__(config)
        self.disconnects = set()

    def bring_down(self, service_name: str):
        self.disconnects.add(service_name)

    def bring_up(self, service_name: str):
        self.disconnects.remove(service_name)

    def build_redis(self):
        redis = MockRedis(self.config)
        if 'redis' in self.disconnects:
            redis.down()
        return redis

    def build_elasticsearch(self):
        es = MockElastic(indices=MockIndices())
        if 'elasticsearch' in self.disconnects:
            es.down()
        return es


@pytest.fixture
def elastic():
    with patch('dug.core.search.Elasticsearch') as es_class:
        es_instance = MockElastic(indices=MockIndices())
        es_class.return_value = es_instance
        yield es_instance


@pytest.fixture
def service_factory():
    return MockServiceFactory
