import json
import urllib.parse
from dataclasses import dataclass
from typing import Dict

import pytest_asyncio

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
def annotator_api():
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
                                    "id": "UBERON:0015230",
                                    "category": ["anatomical entity"],
                                    "terms": ["dorsal vessel heart"],
                                }
                            ],
                        },
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
                                    "id": "UBERON:0015228",
                                    "category": ["anatomical entity"],
                                    "terms": ["circulatory organ"],
                                }
                            ],
                        },
                        {
                            "start": 0,
                            "end": 5,
                            "text": "heart",
                            "token": [
                                {
                                    "id": "ZFA:0000114",
                                    "category": ["anatomical entity"],
                                    "terms": ["heart"],
                                }
                            ],
                        },
                        {
                            "start": 0,
                            "end": 5,
                            "text": "heart",
                            "token": [
                                {
                                    "id": "UBERON:0000948",
                                    "category": ["anatomical entity"],
                                    "terms": ["heart"],
                                }
                            ],
                        },
                        {
                            "start": 0,
                            "end": 12,
                            "text": "heart attack",
                            "token": [
                                {
                                    "id": "MONDO:0005068",
                                    "category": ["disease"],
                                    "terms": ["myocardial infarction (disease)"],
                                }
                            ],
                        },
                        {
                            "start": 0,
                            "end": 12,
                            "text": "heart attack",
                            "token": [
                                {
                                    "id": "HP:0001658",
                                    "category": ["phenotype", "quality"],
                                    "terms": ["Myocardial infarction"],
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


@pytest_asyncio.fixture()
def ontology_api():
    base_url = "http://ontology.api/?curie={curie}"

    def _(curie):
        return base_url.format(
            curie=urllib.parse.quote(curie),
        )

    return MockApiService(
        urls={
            _("UBERON:0007100"): [
                json.dumps(
                    {
                        "taxon": {"id": None, "label": None},
                        "association_counts": None,
                        "xrefs": ["SPD:0000130", "FBbt:00003154", "TADS:0000147"],
                        "description": "A hollow, muscular organ, which, by contracting rhythmically, keeps up the circulation of the blood or analogs[GO,modified].",
                        "types": None,
                        "synonyms": [
                            {"val": "dorsal tube", "pred": "synonym", "xrefs": None},
                            {"val": "adult heart", "pred": "synonym", "xrefs": None},
                            {"val": "heart", "pred": "synonym", "xrefs": None},
                        ],
                        "deprecated": None,
                        "replaced_by": None,
                        "consider": None,
                        "id": "UBERON:0007100",
                        "label": "primary circulatory organ",
                        "iri": "http://purl.obolibrary.org/obo/UBERON_0007100",
                        "category": ["anatomical entity"],
                    }
                ),
                200,
            ]
        }
    )
