import json
from copy import copy
from dataclasses import dataclass
from typing import Dict, List

import pytest
from requests import Session

from dug.annotate import Identifier, Preprocessor, Annotator, Normalizer, SynonymFinder, OntologyHelper, \
    BioLinkPURLerizer


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
        self._urls = urls

    def get(self, url):
        text = self._urls.get(url)
        if text is None:
            return MockResponse(text="{}", code=404)
        return MockResponse(text)


@pytest.fixture
def annotator_api():

    urls = {
        "http://annotator.api/?query=hello": json.dumps({
                "spans": [
                    {
                        "text": "",
                        "token": [{
                            "id": "id-1",
                            "category": "",
                            "terms": ["label-1"]
                        }]
                    },
                ],
            },
        ),
    }

    return MockApiService(
        urls=urls,
    )


@pytest.fixture
def normalizer_api():
    urls = {

    }

    return MockApiService(
        urls=urls,
    )


@pytest.fixture
def synonym_api():
    return MockApiService(urls={
        "http://synonyms.api/?query=abc": json.dumps([
            {"desc": "synonym-1"},
            {"desc": "synonym-2"},
        ])

    })


@pytest.fixture()
def ontology_api():
    return MockApiService(urls={
        "http://ontology.api/?query=abc": json.dumps({
            "label": "label-1",
            "description": "desc-1",
            "category": ["ontology-1"],

        })
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
    text = "hello"
    identifiers: List[Identifier] = annotator.annotate(text, annotator_api)

    assert len(identifiers) == 1
    assert isinstance(identifiers[0], Identifier)


def test_normalizer(normalizer_api):
    url = "http://normalizer.api"

    identifier = Identifier(
        "id-1",
        "label-1",
    )

    normalizer = Normalizer(url)
    output = normalizer.normalize(identifier, normalizer_api)
    pytest.fail("The normalize method needs to be fixed")


def test_synonym_finder(synonym_api):
    curie = "abc"
    url = f"http://synonyms.api/?query="

    finder = SynonymFinder(url)
    result = finder.get_synonyms(
        curie,
        synonym_api,
    )
    assert result == ['synonym-1', 'synonym-2']


def test_ontology_helper(ontology_api):
    curie = "abc"
    url = "http://ontology.api/?query="

    helper = OntologyHelper(url)
    result = helper.get_ontology_info(curie, ontology_api)
    assert ("label-1", "desc-1", "ontology-1") == result