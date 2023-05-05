
import json

from unittest.mock import patch, Mock

import pytest
pytest.skip("skipping as dug.api is no longer present", allow_module_level=True)
from pytest import mark

from dug.api import app, main, DugResource



@pytest.fixture
def dug_api_test_client():
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_g_object():
    with patch('dug.api.dug') as g:
        yield g


@pytest.fixture
def mock_search_concepts(mock_g_object):
    mock_g_object().search_concepts.return_value = {'hits': {'hits': [
        {'_type': '_doc',
         '_id': 'UBERON:0001638',
         '_source': {'id': 'UBERON:0001638',
                     'name': 'vein',
                     'description': 'some vessels that carry blood.',
                     'type': 'anatomical entity'
                     }
         }
    ]
    }}


@pytest.fixture
def mock_search_kg(mock_g_object):
    mock_g_object().search_kg.return_value = {'hits': {'hits': [
        {'_type': '_doc', '_id': 'MEDDRA:10047249'}
    ]}}


@pytest.fixture
def mock_search_variables(mock_g_object):
    mock_g_object().search_variables.return_value = {'hits': {'hits': [
        {'_type': '_doc', '_id': 'MEDDRA:10047249'}
    ]}}


@pytest.fixture
def mock_agg_data_types(mock_g_object):
    mock_g_object().agg_data_type.return_value = ["DBGaP"]


def resp_decode(resp):
    resp_data = resp.data
    resp_json = json.loads(resp_data.decode('utf-8'))
    return resp_json


@mark.api
def test_dug_search_resource(dug_api_test_client, mock_search_concepts):
    resp = dug_api_test_client.post('/search',
                                    json={"index": "concepts_index", "query": "heart attack"}
                                    )
    resp_json = resp_decode(resp)

    assert resp_json['status'] == 'success'
    assert len(resp_json['result']) > 0
    assert resp.status_code == 200


@mark.api
def test_dug_search_kg_resource(dug_api_test_client, mock_search_kg):
    resp = dug_api_test_client.post('/search_kg',
                                    json={"index": "concepts", "unique_id": "id_001", "query": "cough"})
    resp_json = resp_decode(resp)

    assert resp_json['status'] == 'success'
    assert len(resp_json['result']) > 0
    assert resp.status_code == 200


@mark.api
def test_dug_search_variable_resource(dug_api_test_client, mock_search_variables):
    resp = dug_api_test_client.post('/search_var',
                                    json={"index": "concepts", "unique_id": "id_001", "query": "cough"})
    resp_json = resp_decode(resp)

    assert resp_json['status'] == 'success'
    assert len(resp_json['result']) > 0
    assert resp.status_code == 200


@mark.api
def test_dug_agg_data_type_resource(dug_api_test_client, mock_agg_data_types):
    resp = dug_api_test_client.post('/agg_data_types',
                                    json={"index": "concepts"})
    resp_json = resp_decode(resp)

    assert resp_json['status'] == 'success'
    assert len(resp_json['result']) > 0
    assert resp.status_code == 200


@mark.api
def test_create_response_raises_exception():
    error_exception = Mock()
    error_exception.side_effect = Exception
    dr = DugResource()
    resp = dr.create_response(exception=error_exception)

    assert resp["status"] == 'error'


@mark.api
@patch('dug.api.app.run')
def test_main(api_app_run):
    api_app_run.side_effect = "I am running!"
    main(["-p", "8000", "-d"])