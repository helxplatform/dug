import pytest

from dug.annotate import Identifier
from dug.parsers import DugElement, DugConcept, DbGaPParser


def test_dug_concept():
    concept = DugConcept("concept-1", 'Concept-1', 'The first concept', 'secondary')

    ident_1 = Identifier("ident-1", "Identifier-1")
    ident_2 = Identifier("ident-2", "Identifier-2")

    concept.add_identifier(ident_1)
    concept.add_identifier(ident_2)

    concept.clean()


def test_dug_element():
    elem_id = "1"
    elem_name = "Element-1"
    elem_desc = "The first element"
    elem_type = "primary"
    element = DugElement(
        elem_id, elem_name, elem_desc, elem_type, collection_id="", collection_name="", collection_desc=""
    )

    assert len(element.concepts) == 0
    element.add_concept(DugConcept("concept-1", 'Concept-1', 'The first concept', 'secondary'))
    assert len(element.concepts) == 1
    element.add_concept(DugConcept("concept-1", 'Concept-1', 'The first concept', 'secondary'))
    assert len(element.concepts) == 1
