import json
from copy import copy
from dataclasses import dataclass
from typing import Dict, List

import pytest
from requests import Session

from dug.annotate import Identifier, Preprocessor, Annotator, Normalizer, SynonymFinder, OntologyHelper
import urllib.parse


class ApiService:

    def __init__(self, url_template: str, session: Session):
        self.url = url_template
        self.session = session

    def __call__(self, **query_args) -> dict:
        url = self.url.format(**query_args)
        return self.session.get(url).json()


@dataclass
class MockResponse:
    text: str
    code: int = 200

    def json(self):
        return json.loads(self.text)


class MockApiService:
    def __init__(self, urls: Dict[str, str]):
        self.urls = urls

    def get(self, url):
        text = self.urls.get(url)
        if text is None:
            return MockResponse(text="{}", code=404)
        return MockResponse(text)


@pytest.fixture
def annotator_api():
    base_url = "http://annotator.api/?query={query}"

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
        },
    ),
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


def test_identifier():

    ident_1 = Identifier(
        "PrimaryIdent:1", "first identifier", types=[], search_text="", description=""
    )

    assert "PrimaryIdent" == ident_1.id_type


@pytest.mark.parametrize(
    "preprocessor,input_text,expected_text",
    [
        (Preprocessor(), "Hello_world", "Hello world"),
        (Preprocessor({"Hello": "Hi"}, ["placeholder"]), "Hello placeholder world", "Hi world"),
    ]

)
def test_preprocessor_preprocess(preprocessor, input_text, expected_text):

    original_text = copy(input_text)
    output_text = preprocessor.preprocess(input_text)

    assert input_text == original_text  # Don't modify in-place
    assert output_text == expected_text


def test_annotator(annotator_api):
    url = "http://annotator.api/?query="

    annotator = Annotator(url)
    text = "heart attack"
    identifiers: List[Identifier] = annotator.annotate(text, annotator_api)

    assert len(identifiers) == 7
    assert isinstance(identifiers[0], Identifier)


def test_normalizer(normalizer_api):
    url = "http://normalizer.api/?curie="

    identifier = Identifier(
        "UBERON:0007100",
        label='primary circulatory organ',
        types=['anatomical entity'],
        description="",
        search_text=['heart'],
    )

    normalizer = Normalizer(url)
    output = normalizer.normalize(identifier, normalizer_api)
    assert isinstance(output, Identifier)
    assert output.id == 'UBERON:0007100'
    assert output.label == "primary circulatory organ"
    assert output.equivalent_identifiers == ['UBERON:0007100']
    assert output.types == [
        'biolink:AnatomicalEntity', 'biolink:OrganismalEntity', 'biolink:BiologicalEntity',
        'biolink:NamedThing', 'biolink:Entity'
    ]


def test_synonym_finder(synonym_api):
    curie = "UBERON:0007100"
    url = f"http://synonyms.api/?curie="

    finder = SynonymFinder(url)
    result = finder.get_synonyms(
        curie,
        synonym_api,
    )
    assert result == ["adult heart"]


def test_ontology_helper(ontology_api):
    curie = "UBERON:0007100"
    url = "http://ontology.api/?curie="

    helper = OntologyHelper(url)
    name, description, ontology_type = helper.get_ontology_info(curie, ontology_api)
    assert name == 'primary circulatory organ'
    assert description == 'A hollow, muscular organ, which, by contracting rhythmically, keeps up the circulation of the blood or analogs[GO,modified].'
    assert ontology_type == 'anatomical entity'