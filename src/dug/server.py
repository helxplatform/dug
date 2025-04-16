import logging
import os
import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dug.config import Config
from dug.core.async_search import Search
from pydantic import BaseModel
from typing import List
import asyncio
from typing import Optional, Any

logger = logging.getLogger (__name__)

APP = FastAPI(
    title="Dug Search API",
    root_path=os.environ.get("ROOT_PATH", ""),
)

APP.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GetFromIndex(BaseModel):
    index: str = "concepts_index"
    size: int = 0


class SearchConceptQuery(BaseModel):
    query: str
    index: str = "concepts_index"
    offset: int = 0
    size: int = 20
    types: list = None

class SearchVariablesQuery(BaseModel):
    query: str
    index: str = "variables_index"
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

search = Search(Config.from_env())

@APP.on_event("shutdown")
def shutdown_event():
    asyncio.run(search.es.close())


@APP.post('/dump_concepts')
async def dump_concepts(request: GetFromIndex):
    return {
        "message": "Dump result",
        "result": await search.dump_concepts(**request.dict()),
        "status": "success"
    }


@APP.get('/agg_data_types')
async def agg_data_types():
    return {
        "message": "Dump result",
        "result": await search.agg_data_type(),
        "status": "success"
    }


@APP.post('/search')
async def search_concepts(search_query: SearchConceptQuery):
    return {
        "message": "Search result",
        # Although index in provided by the query we will keep it around for backward compatibility, but
        # search concepts should always search against "concepts_index"
        "result": await search.search_concepts(**search_query.dict(exclude={"index"})),
        "status": "success"
    }


@APP.post('/search_kg')
async def search_kg(search_query: SearchKgQuery):
    return {
        "message": "Search result",
        # Although index in provided by the query we will keep it around for backward compatibility, but
        # search concepts should always search against "kg_index"
        "result": await search.search_kg(**search_query.dict(exclude={"index"})),
        "status": "success"
    }


@APP.post('/search_var')
async def search_var(search_query: SearchVariablesQuery):
    return {
        "message": "Search result",
        # Although index in provided by the query we will keep it around for backward compatibility, but
        # search concepts should always search against "variables_index"
        "result": await search.search_variables(**search_query.dict(exclude={"index"})),
        "status": "success"
    }


@APP.post('/search_var_grouped')
async def search_var_grouped(search_query: SearchVariablesQueryFiltered):
    if search_query.query == "":
        results = await search.dump_concepts(search_query.index, size=search_query.size )
        search_result_hits = results['result']['hits']['hits']
        results = search._make_result(None, search_result_hits, {"count": search_query}, False)

    else:
        results = await search.search_variables(**search_query.dict(exclude={"index", "filter"}))
    all_elements = []
    for program_name in filter(lambda x: x != 'total_items', results.keys()):
        studies = results[program_name]
        for s in studies:
            elements = s['elements']
            for e in elements:
                new_element = e
                new_element.update(
                    {k: v for k, v in s.items() if k != 'elements'}
                )
                new_element['program_name'] = program_name
                all_elements.append(new_element)
    # regroup by variables
    by_id = {}
    for e in all_elements:
        by_id[e['id']] = by_id.get(e['id'], [])
        by_id[e['id']].append(e)
    var_info = None
    study_info_keys = [
        'c_id', 'c_link', 'c_name', 'program_name'
    ]
    final_variables = []
    count_keys = set()
    for var_id in by_id:
        var_studies = by_id[var_id]
        for s in var_studies:
            if not var_info:
                var_info = {
                    k: v for k, v in s.items() if k not in study_info_keys
                }
                var_info.update(var_info['metadata'])
                for k in var_info['metadata']:
                    if isinstance(var_info['metadata'][k], str):
                        count_keys.add(k)
                var_info.pop('metadata')
                var_info['studies'] = []
            study_data = {k: v for k, v in s.items() if k in study_info_keys}
            var_info['studies'].append(study_data)
        final_variables.append(var_info)
        var_info = None

    def sort_inner_dicts(data):
        sorted_data = {}
        for outer_key, inner_dict in data.items():
            if outer_key == "Study Name":
                sorted_inner = dict(sorted(inner_dict.items(), key=lambda item: item[0]))
            else:
                sorted_inner = dict(sorted(inner_dict.items(), key=lambda item: (-item[1], item[0])))
            sorted_data[outer_key] = sorted_inner
        return sorted_data

    def filter_variables(final_variables, filters: List[FilterGrouped]):
        filtered_variables = final_variables.copy()
        for filter in filters:
            to_keep = []
            for var in filtered_variables:
                if filter.key.lower() == "study name":
                    # collect all studies per variable
                    study_to_var_id_map = {}
                    studies = var['studies']
                    # create a lookup table for looking up variables by study name
                    for study_name in [x['c_name'].lower() for x in studies]:
                        study_to_var_id_map[study_name] = study_to_var_id_map.get(study_name, set())
                        study_to_var_id_map[study_name].add(var['id'])
                    # do lookup
                    for filter_study_name in filter.value:
                        filter_study_name = filter_study_name.lower()
                        if var['id'] in study_to_var_id_map.get(filter_study_name, []):
                            to_keep.append(var)
                else:
                    var_keys_lower_map = {key.lower(): key for key in var}
                    if filter.key.lower() in var_keys_lower_map.keys() and (
                            str(var[var_keys_lower_map[filter.key.lower()]]).lower()
                            in [str(x).lower() for x in filter.value]):
                        to_keep.append(var)
            filtered_variables = to_keep
        return filtered_variables

    filtered_variables = filter_variables(final_variables, filters=search_query.filter)
    agg_counts = {}
    study_aggs = {}
    for var in final_variables:
        # study agg
        studies = var['studies']
        for s in studies:
            study_aggs[s['c_name']] = study_aggs.get(s['c_name'], 0) + 1
        for key in count_keys:
            if key in var:
                val = var[key]
                val = val.title()
                display_key = key.title()
                agg_counts[display_key] = agg_counts.get(display_key, {})
                agg_counts[display_key][val] = agg_counts[display_key].get(val, 0) + 1

    agg_counts['Study Name'] = study_aggs
    return {
        "variables": filtered_variables,
        "agg_counts": sort_inner_dicts(agg_counts)
    }


@APP.get('/search_study')
async def search_study(study_id: Optional[str] = None, study_name: Optional[str] = None):
    """
    Search for studies by unique_id (ID or name) and/or study_name.
    """
    result = await search.search_study(study_id=study_id, study_name=study_name)
    return {
        "message": "Search result",
        "result": result,
        "status": "success"
    }


@APP.get('/search_program')
async def search_program(program_name: Optional[str] = None, use_elasticsearch: bool = False):
    """
    Search for studies by unique_id (ID or name) and/or study_name.
    """
    result = await search.search_program(program_name=program_name, use_elasticsearch=use_elasticsearch)
    return {
        "message": "Search result",
        "result": result,
        "status": "success"
    }

@APP.get('/program_list')
async def get_program_list(use_elasticsearch: bool = False):
    """
    Search for program by program name.
    By default, uses JSON file. Set use_elasticsearch=true to use Elasticsearch.
    """
    result = await search.search_program_list(use_elasticsearch=use_elasticsearch)
    return {
        "result": result,
        "status": "success"
    }
if __name__ == '__main__':
    uvicorn.run(APP,port=8181)
