from typing import Dict

import redis
from requests_cache import CachedSession

import dug.core.tranql as tql
from dug.core.annotate import DugAnnotator, Annotator, Normalizer, OntologyHelper, Preprocessor, SynonymFinder, \
    ConceptExpander
from dug.config import Config as DugConfig, TRANQL_SOURCE
from dug.core.crawler import Crawler
from dug.core.parsers import Parser
from dug.core.search import Search


class DugFactory:

    def __init__(self, config: DugConfig):
        self.config = config

    def build_http_session(self) -> CachedSession:

        redis_config = {
            'host': self.config.redis_host,
            'port': self.config.redis_port,
            'password': self.config.redis_password,
        }

        return CachedSession(
            cache_name='annotator',
            backend='redis',
            connection=redis.StrictRedis(**redis_config)
        )

    def build_crawler(self, target, parser: Parser, element_type: str, tranql_source=None) -> Crawler:
        crawler = Crawler(
            crawl_file=str(target),
            parser=parser,
            annotator=self.build_annotator(),
            tranqlizer=self.build_tranqlizer(),
            tranql_queries=self.build_tranql_queries(tranql_source),
            http_session=self.build_http_session(),
            exclude_identifiers=self.config.tranql_exclude_identifiers,
            element_type=element_type,
            element_extraction=self.build_element_extraction_parameters(),
        )

        return crawler

    def build_annotator(self) -> DugAnnotator:

        preprocessor = Preprocessor(**self.config.preprocessor)
        annotator = Annotator(**self.config.annotator)
        normalizer = Normalizer(**self.config.normalizer)
        synonym_finder = SynonymFinder(**self.config.synonym_service)
        ontology_helper = OntologyHelper(**self.config.ontology_helper)

        annotator = DugAnnotator(
            preprocessor=preprocessor,
            annotator=annotator,
            normalizer=normalizer,
            synonym_finder=synonym_finder,
            ontology_helper=ontology_helper
        )

        return annotator

    def build_tranqlizer(self) -> ConceptExpander:
        return ConceptExpander(**self.config.concept_expander)

    def build_tranql_queries(self, source=None) -> Dict[str, tql.QueryFactory]:

        if source is None:
            source = TRANQL_SOURCE
        return {
            key: tql.QueryFactory(self.config.tranql_queries[key], source)
            for key
            in self.config.tranql_queries
        }

    def build_search_obj(self, indices) -> Search:
        return Search(self.config, indices=indices)

    def build_element_extraction_parameters(self, source=None):
        if source is None:
            source = TRANQL_SOURCE
        queries = self.config.node_to_element_queries
        return [
            {
                "output_dug_type": dug_type,
                "casting_config": {
                    "node_type": queries[dug_type]['node_type']
                    # CDE's are only ones
                    # but if we had two biolink:Publication nodes we want to conditionally
                    # cast to other output_dug_type, we could extend this config
                },
                "tranql_source": source
             } for dug_type in queries
        ]
