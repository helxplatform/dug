"""Implements search methods using async interfaces"""
import asyncio
import logging
from datetime import datetime, timezone
from elasticsearch import AsyncElasticsearch, ApiError, helpers
from elasticsearch.helpers import async_scan
import ssl, json
from dug.config import Config

logger = logging.getLogger('dug')
logger.setLevel(logging.INFO)

class SearchException(Exception):
    def __init__(self, message, details):
        self.message = message
        self.details = details


class Search:
    """ Search -
    1. Lexical fuzziness; (a) misspellings - a function of elastic.
    2. Fuzzy ontologically;
       (a) expand based on core queries
         * phenotype->study
         * phenotype->disease->study
         * disease->study
         * disease->phenotype->study
    """

    # Fields mapped as `nested` in index.py::init_indices. Sorting on a subfield of a
    # nested field requires an explicit nested path or elasticsearch rejects the query.
    NESTED_SORT_PATHS = ("tags",)

    # Present in every v2.0 index mapping, so always safe as a stable tiebreaker.
    DEFAULT_SORT_TIEBREAKER = "id.keyword"

    CDE_STUDY_MAPPING_FIELD = "metadata.study_mappings"
    VARIABLE_CDE_MAPPING_FIELD = "metadata.cde_mapping"

    def __init__(self, cfg: Config):

        indices = {
            'concepts_index': cfg.concepts_index_name, 
            'variables_index': cfg.variables_index_name,
            'studies_index': cfg.studies_index_name,
            'sections_index': cfg.sections_index_name,
            'kg_index': cfg.kg_index_name
        }

        self._cfg = cfg
        logger.debug(f"Connecting to elasticsearch host: "
                     f"{self._cfg.elastic_host} at port: "
                     f"{self._cfg.elastic_port}")

        self.indices = indices
        self.hosts = [{'host': self._cfg.elastic_host,
                       'port': self._cfg.elastic_port,
                       'scheme': self._cfg.elastic_scheme}]

        logger.debug(f"Authenticating as user "
                     f"{self._cfg.elastic_username} "
                     f"to host:{self.hosts}")
        if self._cfg.elastic_scheme == "https":
            # Verify ssl connects disable for dev mode
            if self._cfg.elastic_ca_verify:
                ssl_context = ssl.create_default_context(
                    cafile=self._cfg.elastic_ca_path
                )
                self.es = AsyncElasticsearch(hosts=self.hosts,
                                             basic_auth=(self._cfg.elastic_username,
                                                         self._cfg.elastic_password),
                                             ssl_context=ssl_context)
            else:
                self.es = AsyncElasticsearch(hosts=self.hosts,
                                             basic_auth=(self._cfg.elastic_username,
                                                         self._cfg.elastic_password),
                                             verify_certs=False)
        else:
            self.es = AsyncElasticsearch(hosts=self.hosts,
                                         basic_auth=(self._cfg.elastic_username,
                                                     self._cfg.elastic_password))

    async def dump_concepts(self, query={}, size=None,
                            fuzziness=1, prefix_length=3):
        """
        Get everything from concept index
        """
        query = {
            "match_all": {}
        }
        body = {"query": query}
        await self.es.ping()
        concepts_index = self.indices["concepts_index"]
        total_items = await self.es.count(body=body, index=concepts_index)
        counter = 0
        all_docs = []
        async for doc in async_scan(
                client=self.es,
                query=body,
                index=concepts_index
        ):
            if counter == size and size != 0:
                break
            counter += 1
            all_docs.append(doc)
        return {
            "status": "success",
            "result": {
                "hits": {
                    "hits": all_docs
                },
                "total_items": total_items
            },
            "message": "Search result"
        }

    async def agg_data_type(self):
        aggs = {
            "data_type": {
                "terms": {
                    "field": "data_type.keyword",
                }
            }
        }

        body = {'aggs': aggs}
        results = await self.es.search(
            index=self.indices["variables_index"],
            body=body
        )
        data_type_list = [data_type['key'] for data_type in
                          results['aggregations']['data_type']['buckets']]
        results.update({'data type list': data_type_list})
        return data_type_list

    async def _count(self, index_name, filters=None):
        """Number of documents in `index_name` matching `filters`.

        Goes through _search rather than _count because the `size_*` filters compile to
        runtime fields, which the count API does not accept.
        """
        es_filters, runtime_mappings = Search._convert_filters_to_es(filters)
        body = {
            "query": {"bool": {"filter": es_filters}},
            "track_total_hits": True,
        }
        if runtime_mappings:
            body["runtime_mappings"] = runtime_mappings
        results = await self.es.search(
            index=index_name,
            body=body,
            size=0,
            filter_path=["hits.total.value"],
        )
        return results.get("hits", {}).get("total", {}).get("value", 0)

    async def _get_ingest_dates(self, index_names):
        """ Maps each index name to its (ingested_at, index_created_at) pair. """
        empty = {name: (None, None) for name in index_names}
        try:
            mappings = await self.es.indices.get_mapping(
                index=index_names, ignore_unavailable=True)
            settings = await self.es.indices.get_settings(
                index=index_names, ignore_unavailable=True)
        except ApiError as err:
            logger.warning("Could not read index metadata: %s",
                           Search._extract_es_error_reason(err))
            return empty

        dates = {}
        for name in index_names:
            meta = mappings.get(name, {}).get("mappings", {}).get("_meta", {})
            created = settings.get(name, {}).get(
                "settings", {}).get("index", {}).get("creation_date")
            dates[name] = (
                meta.get("ingested_at"),
                datetime.fromtimestamp(
                    int(created) / 1000, tz=timezone.utc).isoformat() if created else None,
            )
        return dates

    async def get_ingestion_metadata(self):
        """Document counts, cross-reference counts and ingestion dates per index."""
        concepts_index = self.indices["concepts_index"]
        sections_index = self.indices["sections_index"]
        studies_index = self.indices["studies_index"]
        variables_index = self.indices["variables_index"]
        index_names = [concepts_index, sections_index, studies_index, variables_index]

        is_cde = {"field": "is_cde", "operator": "eq", "value": True}
        is_not_cde = {"field": "is_cde", "operator": "eq", "value": False}
        has_study_mapping = {"field": self.CDE_STUDY_MAPPING_FIELD,
                             "operator": "size_gt", "value": 0}
        has_cde_mapping = {"field": self.VARIABLE_CDE_MAPPING_FIELD,
                           "operator": "size_gt", "value": 0}

        (concepts, sections, studies, variables_total, cdes, variables,
         cdes_mapped, variables_mapped, ingest_dates) = await asyncio.gather(
            self._count(concepts_index),
            self._count(sections_index),
            self._count(studies_index),
            self._count(variables_index),
            self._count(variables_index, [is_cde]),
            self._count(variables_index, [is_not_cde]),
            # CDE sets/CRFs, which the API exposes as /cdes, live in the sections index.
            self._count(sections_index, [has_study_mapping]),
            self._count(variables_index, [is_not_cde, has_cde_mapping]),
            self._get_ingest_dates(index_names),
        )

        def described(index_name, doc_count, **extra):
            ingested_at, created_at = ingest_dates.get(index_name, (None, None))
            return {
                "index": index_name,
                "doc_count": doc_count,
                "ingested_at": ingested_at,
                "index_created_at": created_at,
                **extra,
            }

        return {
            "indices": {
                "concepts": described(concepts_index, concepts),
                "sections": described(sections_index, sections),
                "studies": described(studies_index, studies),
                "variables": described(variables_index, variables_total,
                                       variable_count=variables, cde_count=cdes),
            },
            "mappings": {
                "cdes_with_study_mappings": cdes_mapped,
                "variables_with_cde_mappings": variables_mapped,
            },
        }

    @staticmethod
    def _get_concepts_query(query,
                            fuzziness=1,
                            prefix_length=3,
                            filters=None,
                            aggs=None,
                            sort=None,
                            aggregate_size_limit=None):
        "Static data structure populator, pulled for easier testing"
        query_object = {
            "query": {
                "bool": {
                    # this filter ensures that concepts with both name and description are returned.
                    # if one of these are missing the concept won't show up.
                    "filter": {
                        "bool": {
                            "must": [
                                {"wildcard": {"description": "?*"}},
                                {"wildcard": {"name": "?*"}}
                            ]
                        }
                    },
                    "should": [
                        {
                            "match_phrase": {
                                "name": {
                                    "query": query,
                                    "boost": 10
                                }
                            }
                        },
                        {
                            "match_phrase": {
                                "description": {
                                    "query": query,
                                    "boost": 6
                                }
                            }
                        },
                        {
                            "match_phrase": {
                                "search_terms": {
                                    "query": query,
                                    "boost": 8
                                }
                            }
                        },
                        {
                            "match": {
                                "name": {
                                    "query": query,
                                    "fuzziness": fuzziness,
                                    "prefix_length": prefix_length,
                                    "operator": "and",
                                    "boost": 4
                                }
                            }
                        },
                        {
                            "match": {
                                "search_terms": {
                                    "query": query,
                                    "fuzziness": fuzziness,
                                    "prefix_length": prefix_length,
                                    "operator": "and",
                                    "boost": 5
                                }
                            }
                        },
                        {
                            "match": {
                                "description": {
                                    "query": query,
                                    "fuzziness": fuzziness,
                                    "prefix_length": prefix_length,
                                    "operator": "and",
                                    "boost": 3
                                }
                            }
                        },
                        {
                            "match": {
                                "description": {
                                    "query": query,
                                    "fuzziness": fuzziness,
                                    "prefix_length": prefix_length,
                                    "boost": 2
                                }
                            }
                        },
                        {
                            "match": {
                                "search_terms": {
                                    "query": query,
                                    "fuzziness": fuzziness,
                                    "prefix_length": prefix_length,
                                    "boost": 1
                                }
                            }
                        },
                        {
                            "match": {
                                "optional_terms": {
                                    "query": query,
                                    "fuzziness": fuzziness,
                                    "prefix_length": prefix_length
                                }
                            }
                        }
                    ],
                    "minimum_should_match": 1,
                }
            }
        }

        return Search._apply_common_clauses(
            query_object, filters=filters, aggs=aggs, sort=sort,
            aggregate_size_limit=aggregate_size_limit)

    def is_simple_search_query(self, query):
        if not query:
            return False
        return "*" in query or "\"" in query or "+" in query or "-" in query

    async def search_concepts(self, query, simple_search:bool=False, offset=0, size=None, concept_types=None, **kwargs):
        """
        Changed to a long boolean match query to optimize search results
        """
        if self.is_simple_search_query(query) or simple_search:
            search_body = self.get_simple_concept_search_query(query)
        else:
            search_body = self._get_concepts_query(query, **kwargs)
        # Get aggregated counts of biolink types
        search_body['aggs'] = {'type-count': {'terms': {'field': 'concept_type'}}}
        if isinstance(concept_types, list):
            search_body['post_filter'] = {
                "bool": {
                    "should": [
                        {'term': {'concept_type': {'value': t}}} for t in concept_types
                    ],
                    "minimum_should_match": 1
                }
            }
        search_results = await self.es.search(
            index=self.indices["concepts_index"],
            body=search_body,
            filter_path=['hits.hits._id', 'hits.hits._type',
                         'hits.hits._source', 'hits.hits._score',
                         'hits.hits._explanation', 'aggregations'],
            from_=offset,
            size=size,
            explain=True
        )
        # Aggs/post_filter aren't supported by count
        del search_body["aggs"]
        if "post_filter" in search_body:
            # We'll move the post_filter into the actual filter
            search_body["query"]["bool"]["filter"]["bool"].update(
                search_body["post_filter"]["bool"]
            )
            del search_body["post_filter"]
        total_items = await self.es.count(
            body=search_body,
            index=self.indices["concepts_index"]
        )

        # Simplify the data structure we get from aggregations to put into the
        # return value. This should be a count of documents hit for every type
        # in the search results.
        aggregations = search_results.pop('aggregations')
        concept_types = {
            bucket['key']: bucket['doc_count'] for bucket in
            aggregations['type-count']['buckets']
        }

        return search_results, total_items['count'], concept_types

    async def search_variables(self, concept="", query="", simple_search:bool = False, size=None,
                               data_type=None, offset=0, fuzziness=1,
                               prefix_length=3):
        """
        In variable search, the concept MUST match one of the identifiers in the list
        The query can match search_terms (hence, "should") for ranking.

        Results Return
        The search result is returned in JSON format {collection_id:[elements]}

        Filter
        If a data_type is passed in, the result will be filtered to only contain
        the passed-in data type.
        """
        if self.is_simple_search_query(query) or simple_search:
            es_query = self._get_element_simple_search_query(concept, query)
        else:
            es_query = self._get_element_search_query(concept, fuzziness, prefix_length, query)

        index = self.indices["variables_index"]

        total_items = await self.es.count(body=es_query, index=index)
        search_results = await self.es.search(
            index=index,
            body=es_query,
            filter_path=['hits.hits._id', 'hits.hits._type',
                         'hits.hits._source', 'hits.hits._score'],
            from_=offset,
            size=size or total_items['count']
        )

        search_result_hits = self.remove_hits_from_results(search_results)

        return self._make_result(data_type, search_result_hits, total_items, True)

    async def search_elements(self,
                              index_name,
                              concept="",
                              query="",
                              simple_search: bool = False,
                              parent_ids=None,
                              element_ids=None,
                              filters=None,
                              aggs=None,
                              sort=None,
                              size=None,
                              offset=0,
                              fuzziness=1,
                              prefix_length=3,
                              explain=False):
        is_concepts_search = index_name == self.indices["concepts_index"]
        is_simple_search = self.is_simple_search_query(query) or simple_search

        if is_concepts_search:
            if is_simple_search:
                es_query = self.get_simple_concept_search_query(
                    query=query,
                    filters=filters,
                    aggs=aggs,
                    sort=sort,
                    aggregate_size_limit=self._cfg.aggregate_size_limit
                )
            else:
                es_query = self._get_concepts_query(
                    query=query,
                    fuzziness=fuzziness,
                    prefix_length=prefix_length,
                    filters=filters,
                    aggs=aggs,
                    sort=sort,
                    aggregate_size_limit=self._cfg.aggregate_size_limit
                )
        else:
            if is_simple_search:
                es_query = self._get_element_simple_search_query(
                    concept=concept,
                    query=query,
                    parent_ids=parent_ids,
                    element_ids=element_ids,
                    filters=filters,
                    aggs=aggs,
                    sort=sort,
                    aggregate_size_limit=self._cfg.aggregate_size_limit,
                    new_model=True
                )
            else:
                es_query = self._get_element_search_query(
                    concept=concept,
                    parent_ids=parent_ids,
                    element_ids=element_ids,
                    filters=filters,
                    aggs=aggs,
                    sort=sort,
                    aggregate_size_limit=self._cfg.aggregate_size_limit,
                    fuzziness=fuzziness,
                    prefix_length=prefix_length,
                    query=query,
                    new_model=True
                )

        try:
            search_results = await self.es.search(
                index=index_name,
                body=es_query,
                filter_path=['hits.hits._id', 'hits.hits._type',
                            'hits.hits._source', 'hits.hits._score', 'hits.total',
                            'hits.hits._explanation', 'aggregations'],
                explain=explain,
                from_=offset,
                size=size or self._cfg.default_page_size
            )
        except ApiError as err:
            status = getattr(err, "status_code", None)
            if status is None or not 400 <= status < 500:
                raise
            reason = Search._extract_es_error_reason(err)
            logger.warning("Elasticsearch rejected query on %s: %s", index_name, reason)
            raise SearchException(
                message="Elasticsearch rejected the search request. Check that the "
                        "fields named in `sort`, `filters`, and `aggs` exist and are "
                        "sortable/aggregatable (text fields need a '.keyword' subfield).",
                details=reason,
            ) from err

        total_items = search_results["hits"]["total"]["value"]
        search_result_hits = self.remove_hits_from_results(search_results)
        
        formatted_aggs = {}
        if "aggregations" in search_results:
            for field_name, agg_data in search_results["aggregations"].items():
                buckets = agg_data.get("buckets", [])
                formatted_aggs[field_name] = [
                    { "key": str(bucket["key"]), "count": bucket["doc_count"] }
                    for bucket in buckets
                ]

        return search_result_hits, total_items, formatted_aggs

    async def search_vars_unscored(self, concept="", query="",
                                   size=None, data_type=None,
                                   offset=0, fuzziness=1,
                                   prefix_length=3):
        """
        In variable search, the concept MUST match one of the identifiers in the list
        The query can match search_terms (hence, "should") for ranking.

        Results Return
        The search result is returned in JSON format {collection_id:[elements]}

        Filter
        If a data_type is passed in, the result will be filtered to only contain
        the passed-in data type.
        """
        es_query = self._get_element_search_query(concept, fuzziness, prefix_length, query)
        total_items = await self.es.count(body=es_query, index=self.indices["variables_index"])
        search_results = []
        async for r in async_scan(self.es, query=es_query, index=self.indices["variables_index"]):
            search_results.append(r)

        return self._make_result(data_type, search_results, total_items, False)

    def _make_result(self, data_type, search_results, total_items, scored: bool):
        # Reformat Results
        new_results = {}
        if not search_results:
            # we don't want to error on a search not found
            new_results.update({'total_items': total_items['count']})
            return new_results
        for elem in search_results:
            elem_s = elem['_source']
            elem_type = elem_s['data_type']
            if elem_type not in new_results:
                new_results[elem_type] = {}

            # Support both old schema (element_id/collection_id) and
            # DugModel2.0 schema (id/parents)
            elem_id = elem_s.get('element_id') or elem_s.get('id', '')
            parents = elem_s.get('parents', [])
            coll_id = elem_s.get('collection_id') or (parents[0] if parents else elem_id)
            elem_info = {
                "description": elem_s.get('element_desc') or elem_s.get('description', ''),
                "e_link": elem_s.get('element_action') or elem_s.get('action', ''),
                "id": elem_id,
                "name": elem_s.get('element_name') or elem_s.get('name', ''),
                "metadata": elem_s.get('metadata', {})
            }

            if scored:
                elem_info["score"] = round(elem['_score'], 6)

            # Case: collection not in dictionary for given data_type
            if coll_id not in new_results[elem_type]:
                # initialize document
                doc = {
                    'c_id': coll_id,
                    'c_link': elem_s.get('collection_action', ''),
                    'c_name': elem_s.get('collection_name', ''),
                    'elements': [elem_info]
                }
                # save document
                new_results[elem_type][coll_id] = doc

            # Case: collection already in dictionary for given
            # element_type; append elem_info.  Assumes no duplicate
            # elements
            else:
                new_results[elem_type][coll_id]['elements'].append(elem_info)
        # Flatten dicts to list
        for i in new_results:
            new_results[i] = list(new_results[i].values())
        # Return results
        if bool(data_type):
            if data_type in new_results:
                new_results = new_results[data_type]
            else:
                new_results = {}

        # better to update UI to accept optional "total_items" so it does not fail while fetching data for studies tab
        # and remove this if
        if not scored:
            new_results.update({'total_items': total_items['count']})

        return new_results

    async def search_kg(self, unique_id, query, offset=0, size=None,
                        fuzziness=1, prefix_length=3):
        """
        In knowledge graph search the concept MUST match the unique ID
        The query MUST match search_targets.  The updated query allows for
        fuzzy matching and for the default OR behavior for the query.
        """
        query = {
            "bool": {
                "must": [
                    {"term": {
                        "concept_id.keyword": unique_id
                    }
                    },
                    {'query_string': {
                        "query": query,
                        "fuzziness": fuzziness,
                        "fuzzy_prefix_length": prefix_length,
                        "default_field": "search_targets"
                    }
                    }
                ]
            }
        }
        body = {'query': query}
        total_items = await self.es.count(body=body, index=self.indices["kg_index"])
        search_results = await self.es.search(
            index=self.indices["kg_index"],
            body=body,
            filter_path=['hits.hits._id', 'hits.hits._type',
                         'hits.hits._source'],
            from_=offset,
            size=size
        )
        search_results.update({'total_items': total_items['count']})
        return search_results

    async def search_study(self, study_id=None, study_name=None, offset=0, size=None):
        """
        Search for studies by unique_id (ID or name) and/or study_name.
        """
        # Define the base query
        # Define the base query
        query_body = {
            "bool": {
                "must": []
            }
        }

        # Add conditions based on user input
        if study_id:
            query_body["bool"]["must"].append({
                "match": {"collection_id": study_id}
            })

        if study_name:
            query_body["bool"]["must"].append({
                "match": {"collection_name": study_name}
            })

        print("query_body", query_body)
        body = {'query': query_body}
        total_items = await self.es.count(body=body, index=self.indices["variables_index"])
        search_results = await self.es.search(
            index=self.indices["variables_index"],
            body=body,
            filter_path=['hits.hits._id', 'hits.hits._type', 'hits.hits._source'],
            from_=offset,
            size=size
        )
        search_results.update({'total_items': total_items['count']})
        return search_results




    async def get_study_sources(self):
        query_body = {
            "size": 0,
            "aggs": {
                "d1": {
                    "terms": {
                        "field": "programs.keyword"
                    }
                }
            }
        }
        search_results = await self.es.search(
            index=self._cfg.studies_index_name,
            body=query_body
        )
        unique_studies = search_results['aggregations']['d1']['buckets']
        return unique_studies

    async def search_program(self, program_name=None, offset=0, size=None, use_elasticsearch=False):
        """
        Search for studies by unique_id (ID or name) and/or study_name.
        """
        if use_elasticsearch:
            query_body = {
                "query": {
                    "bool": {
                        "must": []
                    }
                },
                "aggs": {
                    "unique_collection_ids": {
                        "terms": {
                            "field": "collection_id.keyword",
                            "size": 1000
                        },
                        "aggs": {
                            "collection_details": {
                                "top_hits": {
                                    "_source": ["collection_id", "collection_name", "collection_action"],
                                    "size": 1
                                }
                            }
                        }
                    }
                }
            }

            if program_name:
                query_body["query"]["bool"]["must"].append({
                    "match": {
                        "data_type": {
                            "query": program_name,
                            "analyzer": "standard"  # for lowercase terms comparision
                        }
                    }
                })
            body = query_body

            search_results = await self.es.search(
                index=self.indices["variables_index"],
                body=body,
                from_=offset,
                size=size
            )

            # The unique collection_ids and their details will be in the 'aggregations' field of the response
            unique_collection_ids = search_results['aggregations']['unique_collection_ids']['buckets']

            # Prepare a list to hold the collection details
            collection_details_list = []

            for bucket in unique_collection_ids:
                collection_details = bucket['collection_details']['hits']['hits'][0]['_source']
                # Append the details to the list in the desired format
                collection_details_list.append(collection_details)

            collection_details_list.sort(key=lambda x: x["collection_id"])

            return collection_details_list
        else:
            with open(self._cfg.studies_path, 'r') as file:
                missing_programs = json.load(file)

            collection_details_list = []
            program_name_lower = program_name.lower() if program_name else None

            for row in missing_programs:
                program = row.get('Program', '')
                study_name = row.get('Study Name', '')
                collection_id = row.get('Accession', '')
                description = row.get('Description', '')

                if not program or not collection_id:
                    continue

                if program_name_lower and program.lower() != program_name_lower:
                    continue

                # Extract base accession for URL to dbgap
                accession_base = collection_id.split('.c')[0] if '.c' in collection_id else collection_id
                collection_action = f"https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id={accession_base}"

                # Add to collection details list
                collection_details_list.append({
                    "collection_id": collection_id,
                    "collection_action": collection_action,
                    "collection_name": study_name
                })

            collection_details_list.sort(key=lambda x: x["collection_id"])

            return collection_details_list

    async def search_program_list(self, use_elasticsearch=False):
        if use_elasticsearch:
            query_body = {
                "size": 0,  # We don't need the documents themselves, so set the size to 0
                "aggs": {
                    "unique_program_names": {
                        "terms": {
                            "field": "data_type.keyword",
                            "size": 10000
                        },
                        "aggs": {
                            "No_of_studies": {
                                "cardinality": {
                                    "field": "collection_id.keyword"
                                }
                            }
                        }
                    }
                }
            }
            search_results = await self.es.search(
                index=self.indices["variables_index"],
                body=query_body
            )
            unique_data_types = search_results['aggregations']['unique_program_names']['buckets']
            data = unique_data_types
            return data
        else:
            with open(self._cfg.studies_path, 'r') as file:
                missing_programs = json.load(file)

            program_studies = {}
            program_descriptions = {}

            for study in missing_programs:
                program = study.get("Program", "")
                description = study.get("Description", "")

                if program not in program_studies:
                    program_studies[program] = []
                    program_descriptions[program] = description
                program_studies[program].append(study)

            program_summary = []
            for program_name, studies in program_studies.items():
                program_summary.append({
                    "key": program_name,
                    "doc_count": len(studies),
                    "No_of_studies": {"value": len(studies)},
                    "description": program_descriptions[program_name],
                    "parent_program": [""]
                })
            # Sort by program name
            program_summary.sort(key=lambda x: x["key"])
            return program_summary

    @staticmethod
    def _get_attr(obj, key, default=None):
        """Reads `key` off either a Pydantic model or an already-dumped dict.

        Note that `getattr(obj, key, obj.get(key))` does not work here: Python
        evaluates the default eagerly, so it raises AttributeError on a model.
        """
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    @staticmethod
    def _extract_es_error_reason(err):
        """Pulls the human-readable reason out of an elasticsearch ApiError."""
        try:
            return err.body["error"]["root_cause"][0]["reason"]
        except (AttributeError, KeyError, IndexError, TypeError):
            return str(err)

    @staticmethod
    def _convert_filters_to_es(filters):
        """
        Converts a list of FilterCriterion dicts into ElasticSearch DSL dicts.
        """
        if not filters:
            return [], {}

        es_filters = []
        runtime_mappings = {}
        for f in filters:
            # Support both Pydantic model and dumped dict format
            field = Search._get_attr(f, "field")
            operator = Search._get_attr(f, "operator")
            value = Search._get_attr(f, "value")

            if operator == "eq":
                es_filters.append({"term": { field: value }})
            elif operator == "neq":
                es_filters.append({
                    "bool": {
                        "must_not": [{ "term": { field: value } }]
                    }
                })
            elif operator == "in":
                val = value if isinstance(value, list) else [value]
                es_filters.append({"terms": { field: val }})
            elif operator in ["gt", "gte", "lt", "lte"]:
                es_filters.append({"range": { field: { operator: value } }})
            elif operator == "exists":
                es_filters.append({"exists": { "field": field }})
            elif operator == "missing":
                es_filters.append({"bool": {
                    "must_not": [
                        {"exists": {"field": field}}
                    ]}
                })
            elif operator.startswith("size"):
                _, es_operator = operator.split("_")
                runtime_field_name = f"{field}_calculated_size"
                script_source = """
                    def path = /\\./.split(params.field);
                    def obj = params._source;
                    for (part in path) {
                        if (obj == null) break;
                        obj = obj[part];
                    }
                    if (obj instanceof Map) {
                        emit(obj.size());
                    } else if (obj instanceof List) {
                        emit(obj.size());
                    } else {
                        emit(0);
                    }
                """
                runtime_mappings[runtime_field_name] = {
                    "type": "long",
                    "script": {
                        "source": script_source,
                        "params": {"field": field}
                    }
                }
                if es_operator == "eq":
                    es_filters.append({
                        "term": {
                            runtime_field_name: int(value)
                        }
                    })
                else:
                    es_filters.append({
                        "range": {
                            runtime_field_name: {
                                es_operator: int(value)
                            }
                        }
                    })
                
        return es_filters, runtime_mappings

    @staticmethod
    def _convert_sort_to_es(sort, tiebreaker_field=None):
        """
        Converts a list of SortCriterion (models or dumped dicts) into an
        ElasticSearch `sort` array.

        Relevance score and a stable tiebreaker are always appended as the final
        keys, so that documents tying on the caller's sort fields stay ranked by
        relevance and paginated results are deterministic across requests.
        """
        if not sort:
            return []

        tiebreaker_field = tiebreaker_field or Search.DEFAULT_SORT_TIEBREAKER
        es_sort = []
        for criterion in sort:
            field = Search._get_attr(criterion, "field")
            if not field:
                continue
            order = Search._get_attr(criterion, "order") or "asc"

            if field in ("_score", "_doc"):
                # These are elasticsearch's own pseudo-fields rather than document
                # fields, so missing/mode/nested don't apply to them.
                es_sort.append({field: {"order": order}})
                continue

            clause = {"order": order}

            missing = Search._get_attr(criterion, "missing")
            # Elasticsearch defaults to _last for asc but _first for desc, which would
            # put every document *lacking* the field at the top of a descending sort.
            clause["missing"] = missing if missing is not None else "_last"

            mode = Search._get_attr(criterion, "mode")
            if mode:
                clause["mode"] = mode

            root = field.split(".", 1)[0]
            if root in Search.NESTED_SORT_PATHS:
                clause["nested"] = {"path": root}

            es_sort.append({field: clause})

        if not es_sort:
            return []

        fields_used = {next(iter(clause)) for clause in es_sort}
        if "_score" not in fields_used:
            es_sort.append({"_score": {"order": "desc"}})
        if tiebreaker_field not in fields_used:
            es_sort.append({tiebreaker_field: {"order": "asc"}})

        return es_sort

    @staticmethod
    def _apply_common_clauses(query_object, filters=None, aggs=None, sort=None,
                              aggregate_size_limit=None):
        """
        Applies the post_filter/runtime_mappings/aggs/sort tail shared by every v2.0
        query builder. Mutates and returns `query_object`.
        """
        if filters:
            post_filter = query_object \
                .setdefault("post_filter", {}) \
                .setdefault("bool", {}) \
                .setdefault("filter", [])
            es_filters, es_rt_mappings = Search._convert_filters_to_es(filters)
            post_filter.extend(es_filters)
            query_object.setdefault("runtime_mappings", {}).update(es_rt_mappings)

        if aggs:
            query_object["aggs"] = {}
            for field, size_limit in aggs.items():
                size = min(size_limit, aggregate_size_limit) if aggregate_size_limit is not None else size_limit
                query_object["aggs"][field] = {
                    "terms": {
                        "field": field,
                        "size": size
                    }
                }

        if sort:
            es_sort = Search._convert_sort_to_es(sort)
            if es_sort:
                query_object["sort"] = es_sort
                # Without this elasticsearch returns a null _score on every hit whenever
                # a sort is present, which the float-typed response models reject.
                query_object["track_scores"] = True

        return query_object

    @staticmethod
    def _get_element_search_query(concept,
                                  fuzziness,
                                  prefix_length,
                                  query,
                                  new_model=False,
                                  element_ids=None,
                                  parent_ids=None,
                                  filters=None,
                                  aggs=None,
                                  sort=None,
                                  aggregate_size_limit=None):
        """Returns ES query for variable search"""
        element_name = "element_name"
        element_desc = "element_desc"

        if new_model:
            element_name = "name"
            element_desc = "description"

        es_query = {
            "query": {
                'bool': {
                    "minimum_should_match": 1,
                    'should': [
                        {
                            "match_phrase": {
                                element_name: {
                                    "query": query,
                                    "boost": 10
                                }
                            }
                        },
                        {
                            "match_phrase": {
                                element_desc: {
                                    "query": query,
                                    "boost": 6
                                }
                            }
                        },
                        {
                            "match_phrase": {
                                "search_terms": {
                                    "query": query,
                                    "boost": 8
                                }
                            }
                        },
                        {
                            "match": {
                                element_name: {
                                    "query": query,
                                    "fuzziness": fuzziness,
                                    "prefix_length": prefix_length,
                                    "operator": "and",
                                    "boost": 4
                                }
                            }
                        },
                        {
                            "match": {
                                "search_terms": {
                                    "query": query,
                                    "fuzziness": fuzziness,
                                    "prefix_length": prefix_length,
                                    "operator": "and",
                                    "boost": 5
                                }
                            }
                        },
                        {
                            "match": {
                                element_desc: {
                                    "query": query,
                                    "fuzziness": fuzziness,
                                    "prefix_length": prefix_length,
                                    "operator": "and",
                                    "boost": 3
                                }
                            }
                        },
                        {
                            "match": {
                                element_desc: {
                                    "query": query,
                                    "fuzziness": fuzziness,
                                    "prefix_length": prefix_length,
                                    "boost": 2
                                }
                            }
                        },
                        {
                            "match": {
                                element_name: {
                                    "query": query,
                                    "fuzziness": fuzziness,
                                    "prefix_length": prefix_length,
                                    "boost": 2
                                }
                            }
                        },
                        {
                            "match": {
                                "search_terms": {
                                    "query": query,
                                    "fuzziness": fuzziness,
                                    "prefix_length": prefix_length,
                                    "boost": 1
                                }
                            }
                        },
                        {
                            "match": {
                                "optional_terms": {
                                    "query": query,
                                    "fuzziness": fuzziness,
                                    "prefix_length": prefix_length
                                }
                            }
                        },
                        {
                            "nested": {
                                "path": "tags",
                                "query": {
                                    "match_phrase": {
                                        "tags.value.text": {
                                            "query": query,
                                            "boost": 8
                                        }
                                    }
                                }
                            }
                        },
                        {
                            "nested": {
                                "path": "tags",
                                "query": {
                                    "match": {
                                        "tags.value.text": {
                                            "query": query,
                                            "fuzziness": fuzziness,
                                            "prefix_length": prefix_length,
                                            "operator": "and",
                                            "boost": 4
                                        }
                                    }
                                }
                            }
                        }
                    ]
                }
            }
        }
        if concept:
            es_query["query"]["bool"]["must"] = {
                "match": {
                    "identifiers": concept
                }
            }
        if parent_ids:
            if query:
                es_query["query"]["bool"]['filter'] = es_query["query"]["bool"].get('filter', [])
                es_query["query"]["bool"]["filter"].append(
                    {
                        "terms": {
                            "parents.keyword": parent_ids
                        }
                    }
                )
            else:
                es_query["query"]["bool"]["should"].append(
                    {
                        "terms": {
                            "parents.keyword": parent_ids
                        }
                    }
                )
        if element_ids:
            if query:
                es_query["query"]["bool"]['filter'] = es_query["query"]["bool"].get('filter', [])
                es_query["query"]["bool"]["filter"].append(
                    {
                        "terms": {
                            "id.keyword": element_ids
                        }
                    }
                )
            else:
                es_query["query"]["bool"]["should"].append(
                    {
                        "terms": {
                            "id.keyword": element_ids
                        }
                    }
                )

        return Search._apply_common_clauses(
            es_query, filters=filters, aggs=aggs, sort=sort,
            aggregate_size_limit=aggregate_size_limit)

    @staticmethod
    def get_simple_concept_search_query(query, filters=None, aggs=None, sort=None,
                                        aggregate_size_limit=None):
        """Returns ES query that allows to use basic operators like AND, OR, NOT...
        More info here https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-simple-query-string-query.html."""
        simple_query_string_search = {
            "query": query,
            "default_operator": "and",
            "flags": "OR|AND|NOT|PHRASE|PREFIX|WHITESPACE"
        }
        search_query = {
            "query": {
                "bool": {
                    "filter": {
                        "bool": {
                            "must": [
                                {"wildcard": {"description": "?*"}},
                                {"wildcard": {"name": "?*"}}
                            ]
                        }
                    },
                    "must": {
                        "function_score": {
                            "query": {
                                "bool": {
                                    "should": [
                                        {
                                            "simple_query_string": {
                                                **simple_query_string_search,
                                                "fields": ["name"]
                                            }
                                        },
                                        {
                                            "simple_query_string": {
                                                **simple_query_string_search,
                                                "fields": ["description"]
                                            }
                                        },
                                        {
                                            "simple_query_string": {
                                                **simple_query_string_search,
                                                "fields": ["search_terms"]
                                            }
                                        }
                                    ]
                                }
                            },
                            "score_mode": "sum"
                        }
                    }
                }
            }
        }

        return Search._apply_common_clauses(
            search_query, filters=filters, aggs=aggs, sort=sort,
            aggregate_size_limit=aggregate_size_limit)

    @staticmethod
    def _get_element_simple_search_query(
        concept,
        query,
        new_model=False,
        parent_ids=None,
        element_ids=None,
        filters=None,
        aggs=None,
        sort=None,
        aggregate_size_limit=None
    ):
        """Returns ES query that allows to use basic operators like AND, OR, NOT...
        More info here https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-simple-query-string-query.html."""
        simple_query_string_search = {
            "query": query,
            "default_operator": "and",
            "flags": "OR|AND|NOT|PHRASE|PREFIX|WHITESPACE"
        }

        element_name = "element_name"
        element_desc = "element_desc"

        if new_model:
            element_name = "name"
            element_desc = "description"

        search_query = {
            "query": {
                "bool": {
                    "must": [
                        {"function_score": {
                            "query": {
                                "bool": {
                                    "minimum_should_match": 1,
                                    "should": [

                                        {
                                            "simple_query_string": {
                                                **simple_query_string_search,
                                                "fields": [element_name]
                                            }
                                        },
                                        {
                                            "simple_query_string": {
                                                **simple_query_string_search,
                                                "fields": [element_desc]
                                            }
                                        },
                                        {
                                            "simple_query_string": {
                                                **simple_query_string_search,
                                                "fields": ["search_terms"]
                                            }
                                        },
                                        {
                                            "nested": {
                                                "path": "tags",
                                                "query": {
                                                    "simple_query_string": {
                                                        **simple_query_string_search,
                                                        "fields": [
                                                            "tags.value.text"
                                                        ]
                                                    }
                                                }
                                            }
                                        }
                                    ]
                                }
                            },
                            "score_mode": "sum"
                        }}
                    ]
                }
            }
        }
        if concept:
            search_query["query"]["bool"]["must"].append({
                "match": {
                    "identifiers": concept
                }
            })

        if parent_ids:
            if query:
                search_query["query"]["bool"]['filter'] = search_query["query"]["bool"].get('filter', [])
                search_query["query"]["bool"]["filter"].append(
                    {
                        "terms": {
                            "parents.keyword": parent_ids
                        }
                    }
                )
            else:
                search_query["query"]["bool"]["should"].append(
                    {
                        "terms": {
                            "parents.keyword": parent_ids
                        }
                    }
                )
        if element_ids:
            if query:
                search_query["query"]["bool"]['filter'] = search_query["query"]["bool"].get('filter', [])
                search_query["query"]["bool"]["filter"].append(
                    {
                        "terms": {
                            "id.keyword": element_ids
                        }
                    }
                )
            else:
                search_query["query"]["bool"]["should"].append(
                    {
                        "terms": {
                            "id.keyword": element_ids
                        }
                    }
                )

        return Search._apply_common_clauses(
            search_query, filters=filters, aggs=aggs, sort=sort,
            aggregate_size_limit=aggregate_size_limit)

    async def get_elements_by_ids(self, ids: [str], index_name=""):
        """Returns variables by ids"""

        if len(ids) == 0:
            return []

        body = {
            "size": self._cfg.max_ids_limit,
            "query": {
                "ids": {
                    "values": ids
                }
            },
            # for scroll optimization
            "sort": [
                "_doc"
            ]
        }

        res = []

        if len(ids) <= self._cfg.max_ids_limit:
            search_results = await self.es.search(
                index=self._cfg.variables_index_name,
                body=body,
                filter_path=['hits.hits._id', 'hits.hits._type', 'hits.hits._source']
            )
            search_results_wo_hits = self.remove_hits_from_results(search_results)
            res.extend(search_results_wo_hits)
        else:
            search_results = helpers.async_scan(client=self.es, index=index_name, query=body)
            async for r in search_results:
                res.append(r)

        return res

    def remove_hits_from_results(self, search_results):
        search_result_hits = []
        if "hits" in search_results and "hits" in search_results["hits"]:
            search_result_hits = search_results['hits']['hits']
        return search_result_hits

    def get_variables_for_response(self, variables):
        res_variables = []

        for variable in variables:
            item = variable['_source']
            if "_score" in variable:
                item["score"] = variable["_score"]
            item["metadata"]["data_type"] = variable["_source"]["data_type"]
            res_variables.append(item)

        return res_variables

    async def get_like_this_elements(self, index_name: str, element_id:str, size:int, offset:int):

        es_query = {
            "query": {
                "dis_max": {
                    "tie_breaker": 0.1,
                    "queries": [
                        {
                            "more_like_this": {
                                "fields": [
                                    "name",
                                    "description",
                                    "search_terms",
                                    "optional_search_terms"
                                ],
                                "like": [
                                    {
                                        "_index": index_name,
                                        "_id": element_id,
                                    }
                                ],
                                "min_term_freq": 1,
                                "max_query_terms": 12,
                                "boost": 10

                            }
                        },
                        {
                            "more_like_this": {
                                "fields": ["search_terms"],
                                "like": [
                                    {
                                        "_index": index_name,
                                        "_id": element_id,
                                    }
                                ],
                                "min_term_freq": 1,
                                "max_query_terms": 8,
                                "boost": 3.0
                            }
                        },
                        {
                            "more_like_this": {
                                "fields": ["optional_search_terms"],
                                "like": [
                                    {
                                        "_index": index_name,
                                        "_id": element_id,
                                    }
                                ],
                                "min_term_freq": 1,
                                "max_query_terms": 6,
                                "boost": 1.0
                            }
                        }
                    ]
                }
            }
        }

        total_items = (await self.es.count(body=es_query, index=index_name))['count']
        search_results = await self.es.search(
            index=index_name,
            body=es_query,
            filter_path=['hits.hits._id', 'hits.hits._type',
                         'hits.hits._source', 'hits.hits._score'],
            from_=offset,
            size=size or total_items
        )

        search_result_hits = self.remove_hits_from_results(search_results)

        return search_result_hits, total_items
