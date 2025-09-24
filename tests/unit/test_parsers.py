from dug.core.parsers._base import DugElement, DugConcept, DugVariable, DugStudy, DugSection
from dug.core.annotators import DugIdentifier, AnnotateMonarch
# from dug.core.annotators.monarch_annotator import AnnotateMonarch


def test_dug_concept():
    concept = DugConcept(id="concept-1", 
                         name='Concept-1', 
                         description='The first concept',
                        )

    ident_1 = DugIdentifier("ident-1", "Identifier-1")
    ident_2 = DugIdentifier("ident-2", "Identifier-2")

    concept.add_identifier(ident_1)
    concept.add_identifier(ident_2)

    concept.clean()


def test_dug_concept_searchable_dict():

    concept_id = "concept-1"
    concept_name = 'Concept-1'
    concept_description = 'The first concept'
    concept_type = 'secondary'
    concept = DugConcept(
        id=concept_id,
        name=concept_name,
        description=concept_description,
        concept_type=concept_type
    )

    assert concept.get_searchable_dict() == {
        'id': concept_id,
        'name': concept_name,
        'description': concept_description,
        'element_type': 'concept',
        'concept_type': concept_type,
        'search_terms': [],
        'optional_terms': [],
        'action': "",
        'identifiers': [],
        'metadata': {},
        'parents': [],
        'programs': []
    }


def test_dug_element():
    elem_id = "1"
    elem_name = "Element-1"
    elem_desc = "The first element"
    elem_type = "primary"
    element = DugElement(
        id=elem_id, 
        name=elem_name, 
        description=elem_desc, 
        type=elem_type
    )

    assert len(element.concepts) == 0
    element.add_concept(DugConcept(id="concept-1", name='Concept-1', description='The first concept'))
    assert len(element.concepts) == 1
    element.add_concept(DugConcept(id="concept-1", name='Concept-1', description='The first concept'))
    assert len(element.concepts) == 1


def test_dug_element_searchable_dict():
    elem_id = "1"
    elem_name = "Element-1"
    elem_desc = "The first element"
    elem_type = "primary"

    element = DugElement(
        id=elem_id, 
        name=elem_name, 
        description=elem_desc, 
        type=elem_type,
    )
    searchable = element.get_searchable_dict()
    assert searchable == {
        'id': elem_id,
        'name': elem_name,
        'description': elem_desc,
        'element_type': elem_type,
        'search_terms': [],
        'optional_terms': [],
        'action': "",
        'identifiers': [],
        'metadata': {},
        'parents': [],
        'programs': [],
    }


def test_dug_variable():
    variable_id = "var1"
    variable_name = "Variable-1"
    variable_desc = "How much pain do you have?"
    elem_type = "variable"
    data_type = 'str'

    variable = DugVariable(
        id=variable_id, 
        name=variable_name, 
        description=variable_desc, 
        type=elem_type,
        data_type=data_type
    )

    assert len(variable.concepts) == 0
    variable.add_concept(DugConcept(id="concept-1", name='Concept-1', description='The first concept'))
    assert len(variable.concepts) == 1
    variable.add_concept(DugConcept(id="concept-1", name='Concept-1', description='The first concept'))
    assert len(variable.concepts) == 1
    assert variable.is_cde == False
    assert variable.type == 'variable'


def test_dug_variable_searchable_dict():
    variable_id = "var1"
    variable_name = "Variable-1"
    variable_desc = "How much pain do you have?"
    elem_type = "variable"
    data_type = 'str'

    variable = DugVariable(
        id=variable_id, 
        name=variable_name, 
        description=variable_desc, 
        type=elem_type,
        data_type=data_type
    )
    searchable = variable.get_searchable_dict()
    assert searchable == {
        'id': variable_id,
        'name': variable_name,
        'description': variable_desc,
        'element_type': elem_type,
        'search_terms': [],
        'optional_terms': [],
        'action': "",
        'identifiers': [],
        'metadata': {},
        'parents': [],
        'programs': [],
        'data_type': data_type,
        'is_cde': False
    }

def test_dug_study():
    study_id = "study1"
    study_name = "Study-1"
    study_desc = "Short Description of the study"
    study_abstract = "THis is an abstract"

    study = DugStudy(
        id=study_id,
        name=study_name,
        description=study_desc,
        abstract=study_abstract
    )

    assert len(study.concepts) == 0
    study.add_concept(DugConcept(id="concept-1", name='Concept-1', description='The first concept'))
    assert len(study.concepts) == 1
    study.add_concept(DugConcept(id="concept-1", name='Concept-1', description='The first concept'))
    assert len(study.concepts) == 1
    assert study.type == 'study'


def test_dug_study_searchable_dict():
    study_id = "study1"
    study_name = "Study-1"
    study_desc = "Short Description of the study"
    study_abstract = "THis is an abstract"

    study = DugStudy(
        id=study_id,
        name=study_name,
        description=study_desc,
        abstract=study_abstract
    )

    searchable = study.get_searchable_dict()
    assert searchable == {
        'id': study_id,
        'name': study_name,
        'description': study_desc,
        'element_type': 'study',
        'search_terms': [],
        'optional_terms': [],
        'action': "",
        'identifiers': [],
        'metadata': {},
        'parents': [],
        'programs': [],
        'publications': [],
        'variable_list': [],
        'abstract': study_abstract
    }

def test_dug_section():
    section_id = "section1"
    section_name = "Pain Index"
    section_desc = "Pain section"
    is_crf = True

    section = DugSection(
        id=section_id,
        name=section_name,
        description=section_desc,
        is_crf=is_crf
    )

    assert len(section.concepts) == 0
    section.add_concept(DugConcept(id="concept-1", name='Concept-1', description='The first concept'))
    assert len(section.concepts) == 1
    section.add_concept(DugConcept(id="concept-1", name='Concept-1', description='The first concept'))
    assert len(section.concepts) == 1
    assert section.type == 'section'


def test_dug_section_searchable_dict():
    section_id = "section1"
    section_name = "Pain Index"
    section_desc = "Pain section"
    is_crf = True

    section = DugSection(
        id=section_id,
        name=section_name,
        description=section_desc,
        is_crf=is_crf
    )

    searchable = section.get_searchable_dict()
    assert searchable == {
        'id': section_id,
        'name': section_name,
        'description': section_desc,
        'element_type': 'section',
        'search_terms': [],
        'optional_terms': [],
        'action': "",
        'identifiers': [],
        'metadata': {},
        'parents': [],
        'programs': [],
        'variable_list': [],
        'is_crf': is_crf
    }
