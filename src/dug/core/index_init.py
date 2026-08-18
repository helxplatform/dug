"""This file is used to initialize the indices in elasticsearch.
    It is also used as a standalone script.
"""

import logging
import os

from elasticsearch import Elasticsearch


logger = logging.getLogger('dug')


class IndexInit:
    """This class is used to initialize the indices in elasticsearch.
        It is also used for Kubernetes jobs for importing data into elasticsearch.
        If this file is changed, then check if the corresponding job needs to be changed."""

    @staticmethod
    def run(es, replicas, indices):
        # The concepts and variable indices include an analyzer that utilizes the english
        # stopword facility from elastic search.  We also instruct each of the text mappings
        # to use this analyzer. Note that we have not upgraded the kg index, because the fields
        # in that index are primarily dynamic. We could eventually either add mappings so that
        # the fields are no longer dynamic or we could use the dynamic template capabilities
        # described in
        # https://www.elastic.co/guide/en/elasticsearch/reference/current/dynamic-templates.html

        kg_index = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": replicas
            },
            "mappings": {
                "properties": {
                    "name": {
                        "type": "text"
                    },
                    "type": {
                        "type": "text"
                    }
                }
            }
        }
        concepts_index = {
            "settings": {
                "index.mapping.coerce": "false",
                "number_of_shards": 1,
                "number_of_replicas": replicas,
                "analysis": {
                    "analyzer": {
                        "std_with_stopwords": {
                            "type": "standard",
                            "stopwords": "_english_"
                        }
                    }
                }
            },
            "mappings": {
                "dynamic": "strict",
                "properties": {
                    "id": {"type": "text", "analyzer": "std_with_stopwords",
                           "fields": {"keyword": {"type": "keyword"}}},
                    "name": {"type": "text", "analyzer": "std_with_stopwords"},
                    "description": {"type": "text", "analyzer": "std_with_stopwords"},
                    "concept_type": {"type": "keyword"},
                    "search_terms": {"type": "text", "analyzer": "std_with_stopwords"},
                    "identifiers": {
                        "properties": {
                            "id": {"type": "text", "analyzer": "std_with_stopwords",
                                   "fields": {"keyword": {"type": "keyword"}}},
                            "label": {"type": "text", "analyzer": "std_with_stopwords"},
                            "equivalent_identifiers": {"type": "keyword"},
                            "type": {"type": "keyword"},
                            "synonyms": {"type": "text", "analyzer": "std_with_stopwords"}
                        }
                    },
                    "parents": {"type": "text", "analyzer": "std_with_stopwords", 
                                "fields": {"keyword": {"type": "keyword"}}},
                    "programs": {"type": "text", "analyzer": "std_with_stopwords",
                                 "fields": {"keyword": {"type": "keyword"}}},
                    "element_type": {"type": "keyword"},
                    "optional_terms": {"type": "text", "analyzer": "std_with_stopwords"},
                    "action": {"type": "text", "analyzer": "std_with_stopwords"},
                    "metadata": {
                        "type": "object",
                        "dynamic": True
                    },
                    "tags": {
                        "type": "nested",
                        "properties": {
                            "category": {
                                "type": "keyword",
                            },
                            "value": {
                                "type": "keyword",
                                "fields": {
                                    "text": {
                                        "type": "text",
                                        "analyzer": "std_with_stopwords"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        variables_index = {
            "settings": {
                "index.mapping.coerce": "false",
                "number_of_shards": 1,
                "number_of_replicas": replicas,
                "analysis": {
                    "analyzer": {
                        "std_with_stopwords": {
                            "type": "standard",
                            "stopwords": "_english_"
                        }
                    }
                }
            },
            "mappings": {
                "dynamic": "strict",
                "properties": {
                    "id": {"type": "text", "analyzer": "std_with_stopwords",
                                   "fields": {"keyword": {"type": "keyword"}}},
                    "name": {"type": "text", "analyzer": "std_with_stopwords"},
                    "element_type": {"type": "keyword"},
                    "description": {"type": "text", "analyzer": "std_with_stopwords"},
                    "action": {"type": "text", "analyzer": "std_with_stopwords"},
                    "search_terms": {"type": "text", "analyzer": "std_with_stopwords"},
                    "optional_terms": {"type": "text", "analyzer": "std_with_stopwords"},
                    "identifiers": {"type": "keyword"},
                    "parents": {"type": "text", "analyzer": "std_with_stopwords",
                                "fields": {"keyword": {"type": "keyword"}}},
                    "programs": {"type": "text", "analyzer": "std_with_stopwords"},
                    "is_cde": {"type": "boolean"},
                    "data_type": {"type": "text", "analyzer": "std_with_stopwords",
                                  "fields": {"keyword": {"type": "keyword"}}},
                    "metadata": {
                        "type": "flattened"
                    },
                    "tags": {
                        "type": "nested",
                        "properties": {
                            "category": {
                                "type": "keyword",
                            },
                            "value": {
                                "type": "keyword",
                                "fields": {
                                    "text": {
                                        "type": "text",
                                        "analyzer": "std_with_stopwords"
                                    }
                                }
                            }
                        }
                    }
                    # typed as keyword for bucket aggs
                }
            }
        }
        studies_index = {
            "settings": {
                "index.mapping.coerce": "false",
                "number_of_shards": 1,
                "number_of_replicas": replicas,
                "analysis": {
                    "analyzer": {
                        "std_with_stopwords": {
                            "type": "standard",
                            "stopwords": "_english_"
                        }
                    }
                }
            },
            "mappings": {
                "dynamic": "strict",
                "properties": {
                    "id": {"type": "text", "analyzer": "std_with_stopwords",
                                   "fields": {"keyword": {"type": "keyword"}}},
                    "name": {"type": "text", "analyzer": "std_with_stopwords"},
                    "element_type": {"type": "keyword"},
                    "description": {"type": "text", "analyzer": "std_with_stopwords"},
                    "action": {"type": "text", "analyzer": "std_with_stopwords"},
                    "search_terms": {"type": "text", "analyzer": "std_with_stopwords"},
                    "optional_terms": {"type": "text", "analyzer": "std_with_stopwords"},
                    "identifiers": {"type": "keyword"},
                    "parents": {"type": "text", "analyzer": "std_with_stopwords",
                                "fields": {"keyword": {"type": "keyword"}}},
                    "programs": {"type": "text", "analyzer": "std_with_stopwords",
                                 "fields": {"keyword": {"type": "keyword"}}},
                    'publications': {"type": "text", "analyzer": "std_with_stopwords"},
                    'variable_list': {"type": "text", "analyzer": "std_with_stopwords",
                                      "fields": {"keyword": {"type": "keyword"}}},
                    'section_list': {"type": "text", "analyzer": "std_with_stopwords",
                                      "fields": {"keyword": {"type": "keyword"}}},
                    'abstract': {"type": "text", "analyzer": "std_with_stopwords"},
                    "metadata": {
                        "type": "object",
                        "dynamic": True
                    },
                    "tags": {
                        "type": "nested",
                        "properties": {
                            "category": {
                                "type": "keyword",
                            },
                            "value": {
                                "type": "keyword",
                                "fields": {
                                    "text": {
                                        "type": "text",
                                        "analyzer": "std_with_stopwords"
                                    }
                                }
                            }
                        }
                    }
                    # typed as keyword for bucket aggs
                }
            }
        }
        sections_index = {
            "settings": {
                "index.mapping.coerce": "false",
                "number_of_shards": 1,
                "number_of_replicas": replicas,
                "analysis": {
                    "analyzer": {
                        "std_with_stopwords": {
                            "type": "standard",
                            "stopwords": "_english_"
                        }
                    }
                }
            },
            "mappings": {
                "dynamic": "strict",
                "properties": {
                    "id": {"type": "text", "analyzer": "std_with_stopwords",
                                   "fields": {"keyword": {"type": "keyword"}}},
                    "name": {"type": "text", "analyzer": "std_with_stopwords"},
                    "element_type": {"type": "keyword"},
                    "description": {"type": "text", "analyzer": "std_with_stopwords"},
                    "action": {"type": "text", "analyzer": "std_with_stopwords"},
                    "search_terms": {"type": "text", "analyzer": "std_with_stopwords"},
                    "optional_terms": {"type": "text", "analyzer": "std_with_stopwords"},
                    "identifiers": {"type": "keyword"},
                    "parents": {"type": "text", "analyzer": "std_with_stopwords",
                                "fields": {"keyword": {"type": "keyword"}}},
                    "programs": {"type": "text", "analyzer": "std_with_stopwords",
                                 "fields": {"keyword": {"type": "keyword"}}},
                    'variable_list': {"type": "text", "analyzer": "std_with_stopwords",
                                      "fields": {"keyword": {"type": "keyword"}}},
                    "is_crf": {"type": "boolean"},
                    "metadata": {
                        "type": "object",
                        "dynamic": True,
                        "properties": {
                            "study_mappings": {
                                "type": "object",
                                "dynamic": False
                            }
                        }
                    },
                    "tags": {
                        "type": "nested",
                        "properties": {
                            "category": {
                                "type": "keyword",
                            },
                            "value": {
                                "type": "keyword",
                                "fields": {
                                    "text": {
                                        "type": "text",
                                        "analyzer": "std_with_stopwords"
                                    }
                                }
                            }
                        }
                    }
                    # typed as keyword for bucket aggs
                }
            }
        }
        settings = {
            'kg_index': kg_index,
            'concepts_index': concepts_index,
            'variables_index': variables_index,
            'studies_index': studies_index,
            'sections_index': sections_index,
        }

        logger.info(f"creating indices")
        logger.info(indices)
        for index_type in indices: ## This is a dict.
            index_name = indices[index_type]
            try:
                if es.indices.exists(index=index_name):
                    # if index exists check if replication is good 
                    # Fetch the settings for the specific index
                    response = es.indices.get_settings(index=index_name)
                    # Extract the number of replicas from the response dictionary
                    current_index_settings = response[index_name]["settings"]["index"]
                    index_replicas = current_index_settings.get("number_of_replicas")
                    # index_replicas = es.indices.get_settings(index=index)["settings"]["index"]["number_of_replicas"]
                    if index_replicas != replicas:
                        es.indices.put_settings(index=index_name, body={"number_of_replicas": (replicas - 1) or 1 })
                        es.indices.refresh(index=index_name)
                    logger.info(f"Ignoring index {index_name} which already exists.")
                else:
                    result = es.indices.create(
                        index=index_name,
                        body=settings[index_type],
                        ignore=400)
                    logger.info(f"result created index {index_name}: {result}")
            except Exception as e:
                logger.error(f"exception: {e}")
                raise e

#Used for kubernetes import job
if __name__ == '__main__':
    kg_index_name = os.environ.get('IN_kg_index_name', 'test10_kg_index')
    studies_index_name = os.environ.get('IN_studies_index_name', 'test10_studies_index')
    variables_index_name = os.environ.get('IN_variables_index_name', 'test10_variables_index')
    sections_index_name = os.environ.get('IN_sections_index_name', 'test10_sections_index')
    concepts_index_name = os.environ.get('IN_concepts_index_name', 'test10_concepts_index')

    elastic_host = os.environ.get('ELASTIC_API_HOST', 'https://localhost:9200')
    elastic_username = os.environ.get('ELASTIC_USERNAME', "elastic")
    elastic_password = os.environ.get('ELASTIC_PASSWORD', "elastic")
    delete_existing_indices = os.environ.get('IN_delete_existing_indices', 'false') == 'true'

    indices = {
        'concepts_index': concepts_index_name,
        'variables_index': variables_index_name,
        'studies_index': studies_index_name,
        'sections_index':sections_index_name,
        'kg_index': kg_index_name
    }

    es = Elasticsearch(elastic_host, basic_auth=(elastic_username, elastic_password), timeout=300, verify_certs=False)

    replicas = es.nodes.info()["_nodes"]["total"]

    if es.ping():
        logger.info('connected to elasticsearch')

        if delete_existing_indices:
            logger.info('deleting indices')
            for index in indices.values():
                try:
                    es.indices.delete(index=index)
                except Exception as e:
                    logger.error(f"Exception occurred during index delete: {e}")

        IndexInit.run(es, replicas, indices)
    else:
        logger.error(f"Unable to connect to elasticsearch at {elastic_host}")
        raise Exception('failed to connect to elasticsearch')


