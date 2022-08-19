import logging
import os
import sys
from functools import partial
from pathlib import Path
from typing import Iterable

import pluggy
from dug.core.loaders.filesystem_loader import load_from_filesystem
from dug.core.loaders.network_loader import load_from_network

from dug import hookspecs
from dug.config import Config
from dug.core import parsers
from dug.core.factory import DugFactory
from dug.core.parsers import DugConcept, Parser, get_parser

logger = logging.getLogger('dug')
stdout_log_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stdout_log_handler.setFormatter(formatter)
logger.addHandler(stdout_log_handler)

logging.getLogger("elasticsearch").setLevel(logging.WARNING)


def get_plugin_manager() -> pluggy.PluginManager:
    pm = pluggy.PluginManager("dug")
    pm.add_hookspecs(hookspecs)
    pm.load_setuptools_entrypoints("dug")
    pm.register(parsers)
    return pm


def get_targets(target_name) -> Iterable[Path]:
    if target_name.startswith("http://") or target_name.startswith("https://"):
        loader = partial(load_from_network, os.getenv("DUG_DATA_DIR", "data"))
    else:
        loader = load_from_filesystem
    return loader(target_name)


class Dug:
    concepts_index = "concepts_index"
    variables_index = "variables_index"
    kg_index = "kg_index"

    def __init__(self, factory: DugFactory):
        self._factory = factory
        self._search = self._factory.build_search_obj(indices=[
            self.concepts_index, self.variables_index, self.kg_index
        ])

    def crawl(self, target_name: str, parser_type: str, element_type: str = None):

        pm = get_plugin_manager()
        parser = get_parser(pm.hook, parser_type)
        targets = get_targets(target_name)

        for target in targets:
            self._crawl(target, parser, element_type)

    def _crawl(self, target: Path, parser: Parser, element_type):

        # Initialize crawler
        crawler = self._factory.build_crawler(target, parser, element_type)
        # Read elements, annotate, and expand using tranql queries
        crawler.crawl()

        # Index Annotated Elements
        for element in crawler.elements:
            # Only index DugElements as concepts will be indexed differently in next step
            if not isinstance(element, DugConcept):
                self._search.index_element(element, index=self.variables_index)

        # Index Annotated/TranQLized Concepts and associated knowledge graphs
        for concept_id, concept in crawler.concepts.items():
            self._search.index_concept(concept, index=self.concepts_index)

            # Index knowledge graph answers for each concept
            for kg_answer_id, kg_answer in concept.kg_answers.items():
                self._search.index_kg_answer(concept_id=concept_id,
                                             kg_answer=kg_answer,
                                             index=self.kg_index,
                                             id_suffix=kg_answer_id)

    def search(self, target, query, **kwargs):
        targets = {
            'concepts': partial(
                self._search.search_concepts, index=kwargs.get('index', self.concepts_index)),
            'variables': partial(
                self._search.search_variables, index=kwargs.get('index', self.variables_index), concept=kwargs.pop('concept', None)),
            'kg': partial(
                self._search.search_kg, index=kwargs.get('index', self.kg_index), unique_id=kwargs.pop('unique_id', None)),
            'nboost': partial(
                self._search.search_nboost, index=kwargs.get('index', None)),
        }
        kwargs.pop('index', None)
        func = targets.get(target)
        if func is None:
            raise ValueError(f"Target must be one of {', '.join(targets.keys())}")

        return func(query=query, **kwargs)

    def summary(self, verbose=False):
        return self._search.summary(verbose=verbose)

    def status(self):
        ...
