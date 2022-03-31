import pytest
from unittest.mock import patch

from dug.core import DugConcept
from dug.core.parsers import DugElement
from tests.unit.mocks.MockCrawler import *


from dug.core.crawler import Crawler


@pytest.fixture
def crawler(crawler_init_args_no_graph_extraction):
    return Crawler(
        **crawler_init_args_no_graph_extraction
    )


def test_init(crawler):
    assert crawler.crawlspace == "crawl"


def test_annotate_element(crawler):
    element = DugElement(
        "test-id",
        "name",
        "some_desc",
        "test-type",
        "collection-id",
        "collection-name",
        "collection-desc"
    )
    crawler.annotate_element(element)
    AnnotatorMock.annotate.assert_called_with(**{
        "text": element.ml_ready_desc,
        "http_session": HTTPSessionMock
    })
    assert len(crawler.concepts) == len(ANNOTATED_IDS)
    assert len(element.concepts) == len(ANNOTATED_IDS)


def test_annotate_elements(crawler):
    elements = [DugElement(
        "test-1",
        "name",
        "some_desc",
        "test-type",
        "collection-id",
        "collection-name",
        "collection-desc"
    ), DugElement(
        "test-2",
        "name",
        "some_desc",
        "test-type",
        "collection-id",
        "collection-name",
        "collection-desc"
    )]
    crawler.elements = elements
    crawler.annotate_elements()
    # annotate elements mutates the original elements
    for element in elements:
        # assert all elements have the fake concepts added
        assert len(element.concepts) == len(ANNOTATED_IDS)
        # assert concept labels  are set on the element's search terms
        for ANNOTATED_ID in ANNOTATED_IDS:
            assert ANNOTATED_ID.label in element.search_terms


def test_expand_concept(crawler):
    identifier = ANNOTATED_IDS[0]
    concept = DugConcept(concept_id=identifier.id, name="test-concept", desc="" , concept_type=identifier.types[0])
    concept.add_identifier(identifier)
    crawler.expand_concept(concept=concept)
    TranqlizerMock.expand_identifier.assert_called_with(
        identifier.id, TranqlQueriesMock.get("disease"), crawler.crawlspace + '/' + identifier.id + '_disease.json'
    )
    assert len(concept.kg_answers) == len(TRANQL_ANSWERS)

def test_expand_to_dug_element(crawler):
    identifier = ANNOTATED_IDS[0]
    concept = DugConcept(concept_id=identifier.id, name="test-concept", desc="", concept_type=identifier.types[0])
    concept.add_identifier(identifier)
    new_elements = crawler.expand_to_dug_element(
        concept=concept,
        casting_config={
            "node_type": "biolink:Publication",
            "curie_prefix": "HEALCDE",
            "attribute_mapping": {
                "name": "name",
                "desc": "summary",
                "collection_name": "cde_category",
                "collection_id":  "cde_category"
            }
        },
        dug_element_type="test-element",
        tranql_source="test:graph"
    )
    assert len(new_elements) == len(TRANQL_ANSWERS)
