from dug_data_model.v2 import DugConcept, DugVariable, DugStudy, DugSection
from pydantic import BaseModel, Field, model_serializer
from typing import Dict, Optional, Any, List


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


class IndexIngestionMetadata(BaseModel):
    index: str = Field(description="Elasticsearch index name")
    doc_count: int = Field(description="Total documents in the index")
    ingested_at: Optional[str] = Field(
        default=None,
        description="When the ingestion pipeline last wrote to this index. Null if the "
                    "index has not been stamped by a pipeline run."
    )
    index_created_at: Optional[str] = Field(
        default=None, description="When the index itself was created"
    )


class VariablesIngestionMetadata(IndexIngestionMetadata):
    variable_count: int = Field(description="Documents with is_cde false")
    cde_count: int = Field(description="Documents with is_cde true")


class IngestionMetadataIndices(BaseModel):
    concepts: IndexIngestionMetadata
    sections: IndexIngestionMetadata
    studies: IndexIngestionMetadata
    variables: VariablesIngestionMetadata


class IngestionMappingCounts(BaseModel):
    cdes_with_study_mappings: int = Field(
        description="CDE sets/CRFs in the sections index carrying a non-empty "
                    "metadata.study_mappings"
    )
    variables_with_cde_mappings: int = Field(
        description="Variables carrying a non-empty metadata.cde_mapping"
    )


class IngestionMetadataResponse(BaseModel):
    indices: IngestionMetadataIndices
    mappings: IngestionMappingCounts


