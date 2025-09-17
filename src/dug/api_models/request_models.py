from pydantic import BaseModel, field_validator
from typing import List, Optional, Any

class GetFromIndex(BaseModel):
    index: str = "concepts_index"
    size: int = 0

class SearchConceptQuery(BaseModel):
    query: str
    offset: int = 0
    size: int = 20
    concept_types: list = None

class SearchStudiesQuery(BaseModel):
    query: str
    offset: int = 0
    size: int = 1000

class SearchVariablesQuery(BaseModel):
    query: str
    concept: str = ""
    offset: int = 0
    size: int = 1000

class FilterGrouped(BaseModel):
    key: str
    value: List[Any]
class SearchVariablesQueryFiltered(SearchVariablesQuery):
    filter: List[FilterGrouped] = []

class SearchKgQuery(BaseModel):
    query: str
    unique_id: str
    index: str = "kg_index"
    size:int = 100

class SearchStudyQuery(BaseModel):
    #query: str
    study_id: Optional[str] = None
    study_name: Optional[str] = None
    #index: str = "variables_index"
    size:int = 100

class SearchProgramQuery(BaseModel):
    #query: str
    program_id: Optional[str] = None
    program_name: Optional[str] = None
    #index: str = "variables_index"
    size:int = 100


class SearchElementQuery(BaseModel):
    query: str = None
    parent_ids: Optional[List] = None
    element_ids: Optional[List] = None
    concept: Optional[str] = None
    size: Optional[int] = 100
    offset: Optional[int] = 0

    @field_validator("parent_ids", "element_ids", mode="before")
    @classmethod
    def drop_empty_strings(cls, v):
        if v is None:
            return v
        return [item for item in v if item not in ("", None)]

class VariableIds(BaseModel):
    """
    List of variable IDs
    """
    ids: Optional[List[str]] = []

class SearchCdeQuery(BaseModel):
    cde_id: Optional[str] = None
    cde_name: Optional[str] = None
    size:int = 100
