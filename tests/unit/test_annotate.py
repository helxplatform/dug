from copy import copy
from typing import List

import pytest

from dug import config
from dug.annotate import Identifier, Preprocessor, Annotator, Normalizer, SynonymFinder, OntologyHelper


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


def test_annotator_init():
    url = config.annotator["url"]

    annotator = Annotator(**config.annotator)
    assert annotator.url == url


def test_annotator_handle_response():
    annotator = Annotator('foo')

    response = {
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
        }

    identifiers: List[Identifier] = annotator.handle_response(None, response)

    assert len(identifiers) == 7
    assert isinstance(identifiers[0], Identifier)


def test_annotator_call(annotator_api):
    url = "http://annotator.api/?content="

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
