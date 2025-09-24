from __future__ import annotations
import json
from typing import Union, Callable, Any, Iterable, Dict, List, Annotated, Literal

from dug.core.loaders import InputFile

from dug import utils as utils
from pydantic import BaseModel, Field, TypeAdapter, computed_field

VARIABLE_TYPE = 'variable'
STUDY_TYPE = 'study'
CONCEPT_TYPE = 'concept'
SECTION_TYPE= 'section'

class DugElement(BaseModel):
    # Basic class for holding information for an object you want to make searchable via Dug
    # This is supposed to be the base class and hold very basic information for anything that is searchabe via Dug.
    
    # Could be a DbGaP variable, DICOM image, App, or really anything
    # Optionally can hold information pertaining to a containing collection (e.g. dbgap study or dicom image series)
    id: str
    name: str # ELement name (for example variable name)
    description: str # Description for the element
    type: str = "" # Type of the element: Must be one of concept/study/variable
    program_name_list: List[str] = Field(default_factory=list) # List of programs that this element may belong to.
    action: str = "" # URL to the action
    parents: List[str] = Field(default_factory=list) # List of parents
    parent_type: str = "" # Every element can have one type of parent. i.e. variable can either belong to study or crf, and then crf can belong to a study and so on. 
    # parent_type variable will indicate which parent type the parents list is made of.
    concepts: Dict[str, DugConcept] = Field(default_factory=dict)    
    search_terms: List[str] = Field(default_factory=list)
    optional_terms: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @computed_field
    @property
    def ml_ready_desc(self) -> str:
        return self.description

    class Config:
        arbitrary_types_allowed = True

    def add_concept(self, concept: DugConcept):
        self.concepts[concept.id] = concept
    
    def add_metadata(self, metadata: Dict[str, Any]):
        self.metadata = metadata
    
    def add_parent(self, parent_element):
        self.parents.append(parent_element)

    def add_program_name(self, program_name):
        self.program_name_list.append(program_name)

    def jsonable(self):
        """Output a pickleable object"""
        return self.model_dump()

    def get_searchable_dict(self):
        # Translate DugElement to ES-style dict
        es_elem = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'search_terms': self.search_terms,
            'optional_terms': self.optional_terms,
            'action': self.action,
            'element_type': self.type,
            'metadata': self.metadata,
            'parents': self.parents,
            'programs': self.program_name_list,
            'identifiers': (list(self.concepts.keys()) if self.concepts else []),
        }
        return es_elem

    def get_response_dict(self):
        response = self.get_searchable_dict()
        things_to_hide = ['search_terms', 'optional_terms',]
        return {x: response[x] for x in response if x not in things_to_hide}


    def get_id(self) -> str:
        return f'{self.id}'

    def set_search_terms(self):
        search_terms = []
        for concept_id, concept in self.concepts.items():
            concept.set_search_terms()
            search_terms.extend(concept.search_terms)
            search_terms.append(concept.name)
        search_terms = sorted(list(set(search_terms)))
        self.search_terms = search_terms

    def set_optional_terms(self):
        optional_terms = []
        for concept_id, concept in self.concepts.items():
            concept.set_optional_terms()
            optional_terms.extend(concept.optional_terms)
        optional_terms = sorted(list(set(optional_terms)))
        self.optional_terms = optional_terms

    def clean(self):
        self.search_terms = sorted(list(set(self.search_terms)))
        self.optional_terms = sorted(list(set(self.optional_terms)))

    def __str__(self):
        return json.dumps(self.jsonable(), indent=2, default=utils.complex_handler)

class DugConcept(DugElement):
    # Basic class for holding information about concepts that are used to organize elements
    # All Concepts map to at least one element
    type: Literal["concept"]=CONCEPT_TYPE
    identifiers: Dict[str, Any] = Field(default_factory=dict)    
    kg_answers: Dict[str, Any] = Field(default_factory=dict)
    concept_type: str=''
    
    def add_identifier(self, ident):
        if ident.id in self.identifiers:
            for search_text in ident.search_text:
                self.identifiers[ident.id].add_search_text(search_text)
        else:
            self.identifiers[ident.id] = ident

    def add_kg_answer(self, answer, query_name):
        answer_node_ids = list(answer.nodes.keys())
        answer_id = f'{"_".join(answer_node_ids)}_{query_name}'
        if answer_id not in self.kg_answers:
            self.kg_answers[answer_id] = answer

    def set_search_terms(self):
        # Traverse set of identifiers to determine set of search terms
        search_terms = self.search_terms
        for ident_id, ident in self.identifiers.items():
            search_terms.extend(ident.search_text + ident.synonyms)
        self.search_terms = sorted(list(set(search_terms)))

    def set_optional_terms(self):
        # Traverse set of knowledge graph answers to determine set of optional search terms
        optional_terms = self.optional_terms
        for kg_id, kg_answer in self.kg_answers.items():
            optional_terms += kg_answer.get_node_names()
            optional_terms += kg_answer.get_node_synonyms()
        self.optional_terms = sorted(list(set(optional_terms)))

    def get_searchable_dict(self):
        # Translate DugConcept into Elastic-Compatible Concept
        es_elem = super().get_searchable_dict()
        es_conc = {**es_elem, 
                    'identifiers': [ident.get_searchable_dict() for ident_id, ident in self.identifiers.items()],
                    'concept_type': self.concept_type
                   }
        return es_conc

class DugVariable(DugElement):
    type:Literal["variable"]=VARIABLE_TYPE
    data_type:str='text'
    is_cde:bool=False

    def get_searchable_dict(self):
        # Translate DugConcept into Elastic-Compatible Concept
        es_elem = super().get_searchable_dict()
        es_var = {**es_elem, 
                    'data_type': self.data_type,
                    'is_cde': self.is_cde
                   }
        return es_var

class DugStudy(DugElement):
    type:Literal["study"]=STUDY_TYPE
    publications:List[str] = Field(default_factory=list)
    variable_list:List[str] = Field(default_factory=list)
    abstract:str=''

    def get_searchable_dict(self):
        # Translate DugConcept into Elastic-Compatible Concept
        es_elem = super().get_searchable_dict()
        es_study = {**es_elem, 
                    'publications': self.publications,
                    'variable_list': self.variable_list,
                    'abstract': self.abstract
                   }
        return es_study

class DugSection(DugElement):
    type:Literal["section"]=SECTION_TYPE
    is_crf:bool=False
    variable_list:List[str] = Field(default_factory=list)

    def get_searchable_dict(self):
        es_elem =  super().get_searchable_dict()
        es_section = {**es_elem,
                      'variable_list': self.variable_list,
                      'is_crf': self.is_crf
                    }
        return es_section
 
Indexable = Union[DugConcept, DugVariable, DugStudy, DugSection]
Parser = Callable[[Any], Iterable[Indexable]]
FileParser = Callable[[InputFile], Iterable[Indexable]]

DiscriminatedIndexable = Annotated[Indexable, Field(discriminator="type")]
DugElementParsedList = TypeAdapter(List[DiscriminatedIndexable])

DugElement.update_forward_refs()
DugConcept.update_forward_refs()