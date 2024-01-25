from typing import Dict

import redis
from requests_cache import CachedSession

import dug.core.tranql as tql
from dug.core.concept_expander import ConceptExpander
from dug.config import Config as DugConfig, TRANQL_SOURCE
from dug.core.crawler import Crawler
from dug.core.parsers import Parser
from dug.core.annotators import Annotator
from dug.core.async_search import Search
from dug.core.index import Index


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

    def build_crawler(self, target, parser: Parser, annotator: Annotator, element_type: str, tranql_source=None) -> Crawler:
        crawler = Crawler(
            crawl_file=str(target),
            parser=parser,
            annotator=annotator,
            tranqlizer=self.build_tranqlizer(),
            tranql_queries=self.build_tranql_queries(tranql_source),
            http_session=self.build_http_session(),
            exclude_identifiers=self.config.tranql_exclude_identifiers,
            element_type=element_type,
            element_extraction=self.build_element_extraction_parameters(),
        )

        return crawler

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

    def build_indexer_obj(self, indices) -> Index:
        return Index(self.config, indices=indices)

    def build_element_extraction_parameters(self, source=None):
        # Method reformats the node_to_element_queries object
        # Uses tranql source use for concept crawling
        if source is None:
            source = TRANQL_SOURCE
        queries = self.config.node_to_element_queries
        # reformat config as array , in the crawler this is looped over 
        # to make calls to the expansion logic.
        # casting config will be a set of conditions to perform casting on. 
        # Currently we are casting based on node type returned from the tranql query
        # we might want to filter those based on curie type or other conditions , if 
        # node type is too broad.
        return [
            {
                "output_dug_type": dug_type,
                "casting_config": {
                    "node_type": queries[dug_type]["node_type"],
                    "curie_prefix": queries[dug_type]["curie_prefix"],
                    "attribute_mapping": queries[dug_type]["attribute_mapping"],
                    "list_field_choose_first": queries[dug_type]["list_field_choose_first"]
                    # CDE's are only ones
                    # but if we had two biolink:Publication nodes we want to conditionally
                    # cast to other output_dug_type, we could extend this config
                },
                "tranql_source": source
             } for dug_type in queries
        ]
