from dug.core.parsers._base import *
from pydantic import BaseModel, model_serializer
from typing import Optional, Any, List


class ElasticResultMetaData(BaseModel):
    total_count: int
    offset: int
    size: int

class ElasticAggregationBucket(BaseModel):
    key: str
    count: int


class ElasticDugElementResult(BaseModel):
    # Class for all entities from elastic search, we are going to have score... optionally explanation
    score: float = Field(default=999)
    explanation: dict = Field(default_factory=dict)
    # we are going to ignore concepts...
    concepts: None = Field(default=None, exclude=True)


class DugAPIResponse(BaseModel):
    results: List[ElasticDugElementResult]
    metadata: Optional[ElasticResultMetaData] = Field(default_factory=dict)
    aggregations: Optional[Dict[str, List[ElasticAggregationBucket]]] = Field(default=None)


class ConceptResponse(ElasticDugElementResult, DugConcept):
    identifiers: List[Any]
    concepts: None = Field(default=None, exclude=True)


class ConceptsAPIResponse(DugAPIResponse):
    results: List[ConceptResponse]


class VariableResponse(ElasticDugElementResult, DugVariable):
    @model_serializer
    def serialize(self):
        response = self.get_response_dict()
        return response


class VariablesAPIResponse(DugAPIResponse):
    results: List[VariableResponse]


class StudyResponse(ElasticDugElementResult, DugStudy):
    @model_serializer
    def serialize(self):
        response = self.get_response_dict()
        response.pop('abstract')
        return response


class StudyAPIResponse(DugAPIResponse):
    results: List[StudyResponse]


class SectionResponse(ElasticDugElementResult, DugSection):
    @model_serializer
    def serialize(self):
        response = self.get_response_dict()
        return response


class SectionAPIResponse(DugAPIResponse):
    results: List[SectionResponse]


