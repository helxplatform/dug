"""
This class is used for adding documents to elastic search index
"""
import logging

from elasticsearch import Elasticsearch
import ssl

from dug_data_model.v2 import dedupe_and_sort

from dug.config import Config

logger = logging.getLogger('dug')


class Index:
    def __init__(self, cfg: Config):

        self._cfg = cfg
        logger.debug(f"******** Connecting to elasticsearch host: {self._cfg.elastic_host} at port: {self._cfg.elastic_port}")

        indices = {
            'concepts_index': self._cfg.concepts_index_name,
            'variables_index': self._cfg.variables_index_name,
            'studies_index': self._cfg.studies_index_name,
            'sections_index': self._cfg.sections_index_name,
            'kg_index': self._cfg.kg_index_name
        }
        self.indices = indices
        self.hosts = [{'host': self._cfg.elastic_host, 'port': self._cfg.elastic_port, 'scheme': self._cfg.elastic_scheme}]

        logger.debug(f"Authenticating as user {self._cfg.elastic_username} to host:{self.hosts}")
        if self._cfg.elastic_scheme == "https":
            if self._cfg.elastic_ca_verify:
                ssl_context = ssl.create_default_context(
                    cafile=self._cfg.elastic_ca_path
                )
                self.es = Elasticsearch(
                    hosts=self.hosts,
                    basic_auth=(self._cfg.elastic_username, self._cfg.elastic_password),
                    ssl_context=ssl_context)
            else:
                self.es = Elasticsearch(
                    hosts=self.hosts,
                    basic_auth=(self._cfg.elastic_username, self._cfg.elastic_password),
                    verify_certs=self._cfg.elastic_ca_verify)
        else:
            self.es = Elasticsearch(
                hosts=self.hosts,
                basic_auth=(self._cfg.elastic_username, self._cfg.elastic_password))
        
        self.replicas = self.get_es_node_count()

        if self.es.ping():
            logger.info('connected to elasticsearch')
            self.init_indices()
        else:
            logger.error(f"Unable to connect to elasticsearch at {self._cfg.elastic_host}:{self._cfg.elastic_port}")
            raise SearchException(
                message='failed to connect to elasticsearch',
                details=f"connecting to host {self._cfg.elastic_host} and port {self._cfg.elastic_port}")
        
    def get_es_node_count(self):
        return self.es.nodes.info()["_nodes"]["total"]
        

    def init_indices(self):
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
                "number_of_replicas": self.replicas
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
                "number_of_replicas": self.replicas,
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
                "number_of_replicas": self.replicas,
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
                "number_of_replicas": self.replicas,
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
                "number_of_replicas": self.replicas,
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
        settings = {
            'kg_index': kg_index,
            'concepts_index': concepts_index,
            'variables_index': variables_index,
            'studies_index': studies_index,
            'sections_index': sections_index,
        }

        logger.info(f"creating indices")
        logger.info(self.indices)
        for index_type in self.indices: ## This is a dict.
            index_name = self.indices[index_type]
            try:
                if self.es.indices.exists(index=index_name):
                    # if index exists check if replication is good 
                    # Fetch the settings for the specific index
                    response = self.es.indices.get_settings(index=index_name)
                    # Extract the number of replicas from the response dictionary
                    current_index_settings = response[index_name]["settings"]["index"]
                    index_replicas = current_index_settings.get("number_of_replicas")
                    # index_replicas = self.es.indices.get_settings(index=index)["settings"]["index"]["number_of_replicas"]
                    if index_replicas != self.replicas:
                        self.es.indices.put_settings(index=index_name, body={"number_of_replicas": (self.replicas - 1) or 1 })
                        self.es.indices.refresh(index=index_name)
                    logger.info(f"Ignoring index {index_name} which already exists.")
                else:
                    result = self.es.indices.create(
                        index=index_name,
                        body=settings[index_type],
                        ignore=400)
                    logger.info(f"result created index {index_name}: {result}")
            except Exception as e:
                logger.error(f"exception: {e}")
                raise e

    def index_doc(self, index, doc, doc_id):
        self.es.index(
            index=index,
            id=doc_id,
            body=doc)

    def update_doc(self, index, doc, doc_id):
        self.es.update(
            index=index,
            id=doc_id,
            body=doc
        )

    def index_concept(self, concept, index):
        # Don't re-index if already in index
        if self.es.exists(index=index, id=concept.id):
            return
        """ Index the document. """
        self.index_doc(
            index=index,
            doc=concept.get_searchable_dict(),
            doc_id=concept.id)

    def index_element(self, elem, index):
        if not self.es.exists(index=index, id=elem.get_id()):
            # If the element doesn't exist, add it directly
            self.index_doc(
                index=index,
                doc=elem.get_searchable_dict(),
                doc_id=elem.get_id())
        else:
            # Otherwise update to add any data that weren't there last time around
            results = self.es.get(index=index, id=elem.get_id())
            update_doc = elem.get_searchable_dict()
            search_terms = results['_source']['search_terms'] + update_doc['search_terms']
            optional_terms = results['_source']['optional_terms'] + update_doc['optional_terms']
            parents = results['_source']['parents'] + update_doc['parents']
            programs = results['_source']['programs'] + update_doc['programs']
            tags = results['_source']['tags'] + update_doc['tags']
            identifiers = results['_source']['identifiers'] + update_doc['identifiers']
            doc = {"doc": {}}
            doc['doc']['search_terms'] = dedupe_and_sort(search_terms)
            doc['doc']['optional_terms'] = dedupe_and_sort(optional_terms)
            doc['doc']['parents'] = dedupe_and_sort(parents)
            doc['doc']['programs'] = dedupe_and_sort(programs)
            doc['doc']['tags'] = [dict(t) for t in {tuple(sorted(d.items())) for d in tags}]
            doc['doc']['identifiers'] = dedupe_and_sort(identifiers)
            self.update_doc(index=index, doc=doc, doc_id=elem.get_id())

    def index_kg_answer(self, concept_id, kg_answer, index, id_suffix=None):

        # Get search targets by extracting names/synonyms from non-curie nodes in answer knoweldge graph
        search_targets = kg_answer.get_node_names(include_curie=False)
        search_targets += kg_answer.get_node_synonyms(include_curie=False)

        # Create the Doc
        doc = {
            'concept_id': concept_id,
            'search_targets': dedupe_and_sort(search_targets),
            'knowledge_graph': kg_answer.get_kg()
        }

        # Create unique ID
        logger.debug("Indexing TranQL query answer...")
        id_suffix = list(kg_answer.nodes.keys()) if id_suffix is None else id_suffix
        unique_doc_id = f"{concept_id}_{id_suffix}"

        """ Index the document. """
        self.index_doc(
            index=index,
            doc=doc,
            doc_id=unique_doc_id)

class SearchException(Exception):
    def __init__(self, message, details):
        self.message = message
        self.details = details