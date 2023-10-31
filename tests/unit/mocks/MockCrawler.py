from unittest.mock import MagicMock, Mock

import pytest
import os
import json


from dug.core.annotate import Identifier
from dug.core.tranql import QueryFactory, QueryKG

# Makes some simple mokes
ParserMock = MagicMock()
HTTPSessionMock = MagicMock()

# mocking tranql queries
TranqlQueriesMock = {}
for key, query in {
    "disease": ["disease", "phenotypic_feature"],
    "pheno": ["phenotypic_feature", "disease"]
}.items():
    TranqlQueriesMock[key] = QueryFactory(query, source="test")


# for testing no id exclusion
ExcludedIDs = []

ANNOTATED_IDS = [
    Identifier("MONDO:0", "0", ["disease"]),
    Identifier("PUBCHEM.COMPOUND:1", "1", ["chemical"])
    ]
for ids in ANNOTATED_IDS:
    ids.type = ids.types[0]
# annotator with annotate method returning mocked concepts
AnnotatorMock = MagicMock()
AnnotatorMock = Mock(return_value=ANNOTATED_IDS)

# tranqlizer returning mock kg when expanding concepts
TranqlizerMock = MagicMock()

# Get example tranql answer
with open(os.path.join(os.path.dirname(__file__), "data", "tranql_response.json")) as stream:
    tranql_json = json.load(stream)
    kg_answer = QueryKG(kg_json=tranql_json)
    TRANQL_ANSWERS = []
    for answer in kg_answer.answers:
        TRANQL_ANSWERS.append(kg_answer.get_answer_subgraph(answer))

TranqlizerMock.expand_identifier = Mock(return_value=TRANQL_ANSWERS)

#mock a crawler with mock dependencies
@pytest.fixture
def crawler_init_args_no_graph_extraction():
    return {
        "crawl_file": "test",
        "parser": ParserMock,
        "annotator": AnnotatorMock,
        "tranqlizer": TranqlizerMock,
        "tranql_queries": TranqlQueriesMock,
        "http_session": HTTPSessionMock,
        "exclude_identifiers": ExcludedIDs,
        "element_type": "TestElement",
        "element_extraction": None
    }
