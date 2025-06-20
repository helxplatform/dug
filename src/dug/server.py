import logging
import os
import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dug.config import Config
from dug.core.async_search import Search
from pydantic import BaseModel
from typing import List, Dict, Set, Any
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
    """
    Searches for variables, groups them by variable ID across studies.
    Filters the variables based on provided criteria for the main results list.
    Calculates faceted aggregation counts: counts for each category are
    calculated based on the dataset as filtered by *all other* active filters.
    Returns the filtered variables along with the faceted aggregation counts.
    """

    # --- 1. Initial Data Fetching ---
    if search_query.query == "":
        results = await search.dump_concepts(search_query.index, size=search_query.size)
        search_result_hits = results['result']['hits']['hits']
        results = search._make_result(None, search_result_hits, {"count": search_query}, False)
    else:
        results = await search.search_variables(**search_query.dict(exclude={"index", "filter"}))

    # --- 2. Flattening the Nested Data Structure ---
    all_elements: List[Dict[str, Any]] = []
    for program_name in filter(lambda x: x != 'total_items', results.keys()):
        studies = results[program_name]
        for s in studies:
            elements = s['elements']
            for e in elements:
                new_element = e.copy()
                new_element.update({k: v for k, v in s.items() if k != 'elements'})
                new_element['program_name'] = program_name
                all_elements.append(new_element)

    # --- 3. Grouping Variables by ID ---
    by_id: Dict[str, List[Dict[str, Any]]] = {}
    for e in all_elements:
        by_id.setdefault(e['id'], []).append(e)

    # --- 4. Consolidating Variable Information and Study Associations ---
    var_info: Dict[str, Any] | None = None
    study_info_keys: List[str] = ['c_id', 'c_link', 'c_name', 'program_name']
    # final_variables represents the *unfiltered* set of variables matching the initial query
    final_variables: List[Dict[str, Any]] = []
    count_keys: Set[str] = set() # Keys suitable for aggregation

    for var_id in by_id:
        var_studies = by_id[var_id]
        first_occurrence = True
        for s in var_studies:
            if first_occurrence:
                var_info = {k: v for k, v in s.items() if k not in study_info_keys}
                if 'metadata' in var_info and isinstance(var_info['metadata'], dict):
                    metadata = var_info.pop('metadata') # Pop metadata first
                    var_info.update(metadata) # Then update var_info with its contents
                    # Identify potential keys for aggregation (string values in metadata)
                    for k, v in metadata.items(): # Iterate over popped metadata
                        if isinstance(v, str):
                            count_keys.add(k)
                var_info['studies'] = []
                first_occurrence = False

            study_data = {k: v for k, v in s.items() if k in study_info_keys}
            if var_info:
                 var_info['studies'].append(study_data)

        if var_info:
            final_variables.append(var_info)

    # --- 5. Filtering Variables Based on Request Criteria (Helper Function) ---
    def filter_variables(vars_to_filter: List[Dict[str, Any]], filters: List[FilterGrouped]) -> List[Dict[str, Any]]:
        """
        Filters a list of variables based on a list of filter criteria.
        Used both for the final result list and for calculating faceted aggregations.
        """
        filtered_vars = vars_to_filter.copy()
        for f_group in filters:
            to_keep: List[Dict[str, Any]] = []
            filter_key_lower = f_group.key.lower()
            filter_values_lower = [str(v).lower() for v in f_group.value]

            for var in filtered_vars:
                if filter_key_lower == "study name":
                    study_names_in_var = [study['c_name'].lower() for study in var.get('studies', [])]
                    if any(s_name in filter_values_lower for s_name in study_names_in_var):
                        to_keep.append(var)
                else:
                    var_keys_lower_map = {key.lower(): key for key in var.keys()}
                    if filter_key_lower in var_keys_lower_map:
                        original_key = var_keys_lower_map[filter_key_lower]
                        # Handle potential non-string values during filtering comparison
                        var_value_str = str(var.get(original_key, '')) # Get value safely and convert to string
                        var_value_lower = var_value_str.lower()
                        if var_value_lower in filter_values_lower:
                            to_keep.append(var)

            filtered_vars = to_keep
            if not filtered_vars:
                break
        return filtered_vars

    # --- 6. Calculate Final Filtered List for Response ---
    # Apply *all* filters to get the list of variables to return in the response
    filtered_variables_for_response = filter_variables(final_variables, filters=search_query.filter)

    # --- 7. Calculating Faceted Aggregation Counts ---
    agg_counts: Dict[str, Dict[str, int]] = {}
    # Define all categories for which we want aggregations
    all_aggregation_keys_original_case = count_keys | {"Study Name"} # Use original case for display keys later

    # Iterate through each potential aggregation category
    for agg_key_orig in all_aggregation_keys_original_case:
        agg_key_lower = agg_key_orig.lower()
        display_key = agg_key_orig.title() # Key used in the response JSON (e.g., "DataType", "Study Name")

        # Determine filters to apply for *this* aggregation calculation
        # Exclude the filter matching the current aggregation key (case-insensitive)
        filters_for_this_agg = [
            f for f in search_query.filter if f.key.lower() != agg_key_lower
        ]

        # Apply these filters to the *original* set of variables (`final_variables`)
        temp_filtered_vars = filter_variables(final_variables, filters=filters_for_this_agg)

        # Calculate counts for the current aggregation key based on the temp_filtered_vars
        current_key_counts: Dict[str, int] = {}
        if agg_key_lower == "study name":
            # Calculate Study Name counts
            for var in temp_filtered_vars:
                studies = var.get('studies', [])
                for s in studies:
                    study_name = s.get('c_name', 'Unknown Study')
                    current_key_counts[study_name] = current_key_counts.get(study_name, 0) + 1
        elif agg_key_orig in count_keys:# Check if it's one of the metadata keys
             # Calculate counts for other metadata keys
             for var in temp_filtered_vars:
                # Check if the variable dictionary actually contains this key
                if agg_key_orig in var:
                    # Handle potential non-string values before title-casing
                    val_raw = var[agg_key_orig]
                    val_str = str(val_raw) if val_raw is not None else ""
                    val = val_str.title() # Title-case the string representation
                    current_key_counts[val] = current_key_counts.get(val, 0) + 1

        # Store the calculated counts for this category if there are any counts
        if current_key_counts:
            agg_counts[display_key] = current_key_counts
        # Optionally: else: agg_counts[display_key] = {} # Include the key even if empty

    # --- 8. Sorting Aggregation Counts ---
    def sort_inner_dicts(data: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
        """Sorts the inner dictionaries of the aggregation counts."""
        sorted_data = {}
        # Sort outer keys alphabetically for consistent order of facets
        for outer_key in sorted(data.keys()):
            inner_dict = data[outer_key]
            if outer_key == "Study Name":
                # Sort studies alphabetically by name (key)
                sorted_inner = dict(sorted(inner_dict.items(), key=lambda item: item[0]))
            else:
                # Sort others by count desc, then name asc
                sorted_inner = dict(sorted(inner_dict.items(), key=lambda item: (-item[1], item[0])))
            sorted_data[outer_key] = sorted_inner
        return sorted_data

    # Sort the calculated aggregations
    sorted_agg_counts = sort_inner_dicts(agg_counts)

    # --- 9. Return Final Response ---
    # Return the *fully filtered* variables and the *faceted* aggregation counts
    return {
        "variables": filtered_variables_for_response if search_query.size > 0 else [],  # Variables filtered by ALL criteria
        "agg_counts": {k: [{"key": i, "doc_count": v}
                           for i, v in sorted_agg_counts[k].items()] for k in sorted_agg_counts},  # Aggregations calculated facet-style
        "total": len(filtered_variables_for_response)
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
