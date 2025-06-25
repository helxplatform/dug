import asyncio
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
from dug.core import parsers
from dug.core import annotators
from dug.core.factory import DugFactory
from dug.core.parsers import DugConcept, Parser, get_parser
from dug.core.annotators import DugIdentifier, Annotator, get_annotator

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
    pm.register(annotators)
    return pm


def get_targets(target_name) -> Iterable[Path]:
    print("In get targets")
    if target_name.startswith("http://") or target_name.startswith("https://"):
        loader = partial(load_from_network, os.getenv("DUG_DATA_DIR", "data"))
    else:
        print("Should have gotten the loader here")
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
        self._index = self._factory.build_indexer_obj(
            indices=[
                self.concepts_index, self.variables_index, self.kg_index
            ]
        )

    def crawl(self, target_name: str, parser_type: str, annotator_type: str, element_type: str = None):

        pm = get_plugin_manager()
        parser = get_parser(pm.hook, parser_type)
        annotator = get_annotator(pm.hook, annotator_type, self._factory.config)
        print("Getting targets")
        targets = get_targets(target_name)

        for target in targets:
            print(f"TARGET: {target}")
            self._crawl(target, parser, annotator, element_type)

    def _crawl(self, target: Path, parser: Parser, annotator: Annotator, element_type):

        # Initialize crawler
        crawler = self._factory.build_crawler(target, parser, annotator, element_type)
        # Read elements, annotate, and expand using tranql queries
        crawler.crawl()

        # Index Annotated Elements
        for element in crawler.elements:
            # Only index DugElements as concepts will be indexed differently in next step
            if not isinstance(element, DugConcept):
                self._index.index_element(element, index=self.variables_index)

        # Index Annotated/TranQLized Concepts and associated knowledge graphs
        for concept_id, concept in crawler.concepts.items():
            self._index.index_concept(concept, index=self.concepts_index)

            # Index knowledge graph answers for each concept
            for kg_answer_id, kg_answer in concept.kg_answers.items():
                self._index.index_kg_answer(concept_id=concept_id,
                                             kg_answer=kg_answer,
                                             index=self.kg_index,
                                             id_suffix=kg_answer_id)

    def search(self, target, query, **kwargs):
        event_loop = asyncio.get_event_loop()
        targets = {
            'concepts': partial(
                self._search.search_concepts),
            'variables': partial(
                self._search.search_variables, concept=kwargs.pop('concept', None)),
            'kg': partial(
                self._search.search_kg, unique_id=kwargs.pop('unique_id', None))
        }
        kwargs.pop('index', None)
        func = targets.get(target)
        if func is None:
            raise ValueError(f"Target must be one of {', '.join(targets.keys())}")
        results = event_loop.run_until_complete(func(query=query, **kwargs))
        event_loop.run_until_complete(self._search.es.close())
        return results

    def status(self):
        ...
