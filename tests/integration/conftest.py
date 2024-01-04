from pathlib import Path

import json
import urllib.parse
from dataclasses import dataclass
from typing import Dict

import pytest_asyncio

TEST_DATA_DIR = Path(__file__).parent.resolve() / "data"


@dataclass
class MockResponse:
    text: str
    status_code: int = 200

    def json(self):
        return json.loads(self.text)


class MockApiService:
    def __init__(self, urls: Dict[str, list]):
        self.urls = urls

    def get(self, url, params: dict = None):
        if params:
            qstr = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
            url = f"{url}?{qstr}"

        text, status_code = self.urls.get(url)

        if text is None:
            return MockResponse(text="{}", status_code=404)
        return MockResponse(text, status_code=status_code)

    def post(self, url, params: dict = None, json: dict = {}):
        if params:
            qstr = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
            url = f"{url}?{qstr}"
        text, status_code = self.urls.get(url)

        if text is None:
            return MockResponse(text="{}", status_code=404)
        return MockResponse(text, status_code=status_code)


@pytest_asyncio.fixture
def monarch_annotator_api():
    base_url = "http://annotator.api/?content={query}"

    def _(keyword):
        return base_url.format(query=urllib.parse.quote(keyword))

    urls = {
        _("heart attack"): [
            json.dumps(
                {
                    "content": "heart attack",
                    "spans": [
                        {
                            "start": 0,
                            "end": 5,
                            "text": "heart",
                            "token": [
                                {
                                    "id": "UBERON:0007100",
                                    "category": ["anatomical entity"],
                                    "terms": ["primary circulatory organ"],
                                }
                            ],
                        },
                        {
                            "start": 0,
                            "end": 5,
                            "text": "heart",
                            "token": [
                                {
                                    "id": "XAO:0000336",
                                    "category": [],
                                    "terms": ["heart primordium"],
                                }
                            ],
                        },
                    ],
                }
            ),
            200,
        ],
    }

    return MockApiService(
        urls=urls,
    )


@pytest_asyncio.fixture
def token_classifier_api():
    return MockApiService(
        urls={
            "https://med-nemo.apps.renci.org/annotate/": [
                json.dumps(
                    {
                        "text": "Have you ever had a heart attack?",
                        "denotations": [
                            {
                                "id": "I5-",
                                "span": {"begin": 20, "end": 32},
                                "obj": "biolink:Disease",
                                "text": "heart attack",
                            }
                        ],
                    }
                ),
                200,
            ]
        }
    )


@pytest_asyncio.fixture
def sapbert_annotator_api():
    return MockApiService(
        urls={
            "https://babel-sapbert.apps.renci.org/annotate/": [
                json.dumps(
                    [
                        {
                            "name": "attack; cardiovascular",
                            "curie": "UBERON:0007100",
                            "category": "biolink:Disease",
                            "score": "0.15857231617",
                        },
                        {
                            "name": "Angina attack",
                            "curie": "XAO:0000336",
                            "category": "biolink:Disease",
                            "score": "0.206502258778",
                        },
                    ]
                ),
                200,
            ]
        }
    )


@pytest_asyncio.fixture
def normalizer_api():
    base_url = "http://normalizer.api/?curie={curie}"

    def _(curie):
        return base_url.format(
            curie=urllib.parse.quote(curie),
        )

    urls = {
        _("UBERON:0007100"): [
            json.dumps(
                {
                    "UBERON:0007100": {
                        "id": {
                            "identifier": "UBERON:0007100",
                            "label": "primary circulatory organ",
                        },
                        "equivalent_identifiers": [
                            {
                                "identifier": "UBERON:0007100",
                                "label": "primary circulatory organ",
                            }
                        ],
                        "type": [
                            "biolink:AnatomicalEntity",
                            "biolink:OrganismalEntity",
                            "biolink:BiologicalEntity",
                            "biolink:NamedThing",
                            "biolink:Entity",
                        ],
                    }
                },
            ),
            200,
        ],
    }

    return MockApiService(
        urls=urls,
    )


@pytest_asyncio.fixture
def null_normalizer_api():
    base_url = "http://normalizer.api/?curie={curie}"

    def _(curie):
        return base_url.format(
            curie=urllib.parse.quote(curie),
        )

    urls = {
        _("XAO:0000336"): [
            json.dumps(
                {"XAO:0000336": None},
            ),
            200,
        ],
    }

    return MockApiService(
        urls=urls,
    )


@pytest_asyncio.fixture
def synonym_api():
    return MockApiService(
        urls={
            "http://synonyms.api": [
                json.dumps(
                    {
                        "UBERON:0007100": {
                            "names": [
                                "primary circulatory organ",
                                "dorsal tube",
                                "adult heart",
                                "heart",
                            ]
                        }
                    }
                ),
                200,
            ]
        }
    )


@pytest_asyncio.fixture
def null_synonym_api():
    return MockApiService(
        urls={"http://synonyms.api": [json.dumps({"XAO:0000336": {"names":[]}}), 200]}
    )
