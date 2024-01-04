import logging
from typing import Dict

import pluggy

from dug.config import Config
from dug.core.annotators._base import DugIdentifier, Indexable, Annotator, DefaultNormalizer, DefaultSynonymFinder
from dug.core.annotators.monarch_annotator import AnnotateMonarch
from dug.core.annotators.sapbert_annotator import AnnotateSapbert

logger = logging.getLogger('dug')

hookimpl = pluggy.HookimplMarker("dug")

@hookimpl
def define_annotators(annotator_dict: Dict[str, Annotator], config: Config):
    annotator_dict["annotator-monarch"] = build_monarch_annotator("annotator-monarch", config=config)
    annotator_dict["annotator-sapbert"] = build_sapbert_annotator("annotator-sapbert", config=config)


class AnnotatorNotFoundException(Exception):
    ...


def get_annotator(hook, annotator_name, config: Config) -> Annotator:
    """Get the annotator from all annotators registered via the define_annotators hook"""

    available_annotators = {}
    hook.define_annotators(annotator_dict=available_annotators, config=config)
    annotator = available_annotators.get(annotator_name.lower())
    if annotator is not None:
        logger.info(f'Annotating with {annotator}')
        return annotator

    err_msg = f"Cannot find annotator of type '{annotator_name}'\n" \
              f"Supported annotators: {', '.join(available_annotators.keys())}"
    logger.error(err_msg)
    raise AnnotatorNotFoundException(err_msg)

def build_monarch_annotator(annotate_type: str, config: Config):    
    logger.info(f"Building Monarch annotator with args: {config.annotator_args[annotate_type]}")
    annotator = AnnotateMonarch(
        normalizer=DefaultNormalizer(**config.normalizer),
        synonym_finder=DefaultSynonymFinder(**config.synonym_service),
        config=config,
        **config.annotator_args[annotate_type]
    )
    return annotator

def build_sapbert_annotator(annotate_type, config: Config):
    logger.info(f"Building Sapbert annotator with args: {config.annotator_args[annotate_type]}")
    annotator = AnnotateSapbert(
        normalizer=DefaultNormalizer(**config.normalizer),
        synonym_finder=DefaultSynonymFinder(**config.synonym_service),
        **config.annotator_args[annotate_type]
    )
    return annotator

