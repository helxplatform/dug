import strawberry
from typing import List

# This type represents the metadata object
@strawberry.type
class MetaData:
    total_count: int
    offset: int
    size: int


# This is the top-level response for a query asking for studies
@strawberry.type
class StudyAPIResponse:
    results: List[Study]
    metadata: Optional[MetaData]


# This is the top-level response for a query asking for variables
@strawberry.type
class VariableAPIResponse:
    results: List[Variable]
    metadata: Optional[MetaData]


# This is the top-level response for a query asking for concepts
@strawberry.type
class ConceptAPIResponse:
    results: List[Concept]
    metadata: MetaData  # This was not Optional in your Pydantic model

    # We use the 'JSON' scalar to handle a generic 'dict' type
    concept_types: JSON