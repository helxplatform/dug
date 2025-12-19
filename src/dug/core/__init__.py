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
from dug.core.parsers import DugConcept, DugStudy, DugVariable, DugSection, Parser, get_parser
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
    if target_name.startswith("http://") or target_name.startswith("https://"):
        loader = partial(load_from_network, os.getenv("DUG_DATA_DIR", "data"))
    else:
        loader = load_from_filesystem
    return loader(target_name)


class Dug:
    def __init__(self, factory: DugFactory):
        self._factory = factory
        self._search = self._factory.build_search_obj()
        self._index = self._factory.build_indexer_obj()
        self.concepts_index = self._factory.config.concepts_index_name
        self.variables_index = self._factory.config.variables_index_name
        self.studies_index = self._factory.config.studies_index_name
        self.sections_index = self._factory.config.sections_index_name
        self.kg_index = self._factory.config.kg_index_name

    def crawl(self, target_name: str, parser_type: str, annotator_type: str, program_name: str = None):

        pm = get_plugin_manager()
        parser = get_parser(pm.hook, parser_type)
        annotator = get_annotator(pm.hook, annotator_type, self._factory.config)
        targets = get_targets(target_name)

        for target in targets:
            self._crawl(target, parser, annotator, program_name)

    def _crawl(self, target: Path, parser: Parser, annotator: Annotator, program_name):

        # Initialize crawler
        crawler = self._factory.build_crawler(target, parser, annotator, program_name)
        # Read elements, annotate, and expand using tranql queries
        crawler.crawl()

        # Index Annotated Elements
        for element in crawler.elements:
            # Only index DugElements as concepts will be indexed differently in next step
            if isinstance(element, DugVariable):
                self._index.index_element(element, index=self.variables_index)
            if isinstance(element, DugStudy):
                self._index.index_element(element, index=self.studies_index)
            if isinstance(element, DugSection):
                self._index.index_element(element, index=self.sections_index)

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
            #TODO: Add Studies here
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
