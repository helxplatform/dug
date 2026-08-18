from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Literal, Union, Any

class GetFromIndex(BaseModel):
    size: int = 0

class SearchConceptQuery(BaseModel):
    query: str
    offset: int = 0
    size: int = 20
    simple_search: bool = False
    concept_types: list = None

class SearchVariablesQuery(BaseModel):
    query: str
    concept: str = ""
    offset: int = 0
    simple_search: bool = False
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
    "in",
    "exists", "missing",
    "size_eq",
    "size_gt", "size_gte",
    "size_lt", "size_lte"
]

class FilterCriterion(BaseModel):
    field: str = Field(..., description="The metadata field to filter by (e.g., 'is_cde' or 'data_type')")
    operator: FilterOperator = Field("eq", description="Comparison operator")
    value: Optional[Union[str, int, float, bool, List[Any]]] = Field(default=None, description="The value to filter against")

SortOrder = Literal["asc", "desc"]
SortMode = Literal["min", "max", "sum", "avg", "median"]
MissingPlacement = Literal["_first", "_last"]

# Guardrail on request complexity, in the spirit of Config.aggregate_size_limit
MAX_SORT_FIELDS = 5

class SortCriterion(BaseModel):
    field: str = Field(..., description=(
        "Elasticsearch field to sort on (e.g. 'metadata.Project End Date'). Must be a "
        "doc_values field (keyword/date/numeric/boolean); 'text' fields are not sortable, "
        "use their '.keyword' subfield."
    ))
    order: SortOrder = Field("asc", description="Sort direction")
    mode: Optional[SortMode] = Field(default=None, description=(
        "Which value to sort on for multi-valued fields (parents, programs, variable_list, "
        "tags...). Defaults to Elasticsearch behavior: min for asc, max for desc."
    ))
    missing: Optional[MissingPlacement] = Field(default=None, description=(
        "Where documents lacking the field are placed. Defaults to '_last' in both directions."
    ))

    @field_validator("field")
    @classmethod
    def validate_field(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("sort field must not be empty")
        # _score and _doc are the only elasticsearch pseudo-fields that can be sorted
        # on; letting other underscore names through just yields a confusing ES error.
        if v.startswith("_") and v not in ("_score", "_doc"):
            raise ValueError(f"'{v}' is not a sortable field")
        return v

class SearchElementQuery(BaseModel):
    query: str = None
    simple_search: bool = False
    parent_ids: Optional[List] = None
    element_ids: Optional[List] = None
    concept: Optional[str] = None

    aggs: Optional[Dict[str, int]] = Field(default=None, description="Specify fields to aggregate against and the bucket limit")
    filters: Optional[List[FilterCriterion]] = Field(default_factory=list)
    sort: Optional[List[SortCriterion]] = Field(default_factory=list, description=(
        "Ordered list of sort keys, applied before relevance score. Note that fields are "
        "ES fields, so subfields like `.keyword` may be required."
    ))

    size: Optional[int] = 100
    offset: Optional[int] = 0

    @field_validator("parent_ids", "element_ids", mode="before")
    @classmethod
    def drop_empty_strings(cls, v):
        if v is None:
            return v
        return [item for item in v if item not in ("", None)]

    @field_validator("sort")
    @classmethod
    def cap_sort_keys(cls, v):
        if v and len(v) > MAX_SORT_FIELDS:
            raise ValueError(f"at most {MAX_SORT_FIELDS} sort keys are supported")
        return v

class VariableIds(BaseModel):
    """
    List of variable IDs
    """
    ids: Optional[List[str]] = []


class MoreLikeThisQuery(BaseModel):
    element_id: str = None
    index_name: str = None
    size: Optional[int] = 100
    offset: Optional[int] = 0

