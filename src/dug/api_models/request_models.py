from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Literal, Union, Any

class GetFromIndex(BaseModel):
    size: int = 0

class SearchConceptQuery(BaseModel):
    query: str
    offset: int = 0
    size: int = 20
    concept_types: list = None

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

FilterOperator = Literal[
    "eq", "neq",
    "gt", "gte",
    "lt", "lte",
    "in", "contains",
    "size_eq",
    "size_gt", "size_gte",
    "size_lt", "size_lte"
]

class FilterCriterion(BaseModel):
    field: str = Field(..., description="The metadata field to filter by (e.g., 'is_cde' or 'data_type')")
    operator: FilterOperator = Field("eq", description="Comparison operator")
    value: Union[str, int, float, bool, List[Any]] = Field(..., description="The value to filter against")

class SearchElementQuery(BaseModel):
    query: str = None
    parent_ids: Optional[List] = None
    element_ids: Optional[List] = None
    concept: Optional[str] = None

    aggs: Optional[Dict[str, int]] = Field(default=None, description="Specify fields to aggregate against and the bucket limit")
    filters: Optional[List[FilterCriterion]] = Field(default_factory=list)

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
