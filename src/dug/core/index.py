"""
This class is used for adding documents to elastic search index
"""
import logging

from elasticsearch import Elasticsearch
import ssl

from dug_data_model.v2 import dedupe_and_sort

import dug.core.index_init
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
        dug.core.index_init.IndexInit.run(self.es, self.replicas, self.indices)

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