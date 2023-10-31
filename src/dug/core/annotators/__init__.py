import logging
from typing import Dict

import pluggy

from dug.config import Config
from ._base import DugIdentifier, Indexable, Annotator, DefaultNormalizer, DefaultSynonymFinder
from .monarch_annotator import AnnotateMonarch

logger = logging.getLogger('dug')

hookimpl = pluggy.HookimplMarker("dug")

@hookimpl
def define_annotators(annotator_dict: Dict[str, Annotator]):
    annotator_dict["annotator-monarch"] = build_annotator()


class AnnotatorNotFoundException(Exception):
    ...


def get_annotator(hook, annotator_name) -> Annotator:
    """Get the annotator from all annotators registered via the define_annotators hook"""

    available_annotators = {}
    hook.define_annotators(annotator_dict=available_annotators)
    annotator = available_annotators.get(annotator_name.lower())
    if annotator is not None:
        return annotator

    err_msg = f"Cannot find annotator of type '{annotator_name}'\n" \
              f"Supported annotators: {', '.join(available_annotators.keys())}"
    logger.error(err_msg)
    raise AnnotatorNotFoundException(err_msg)

def build_annotator():
    config = Config.from_env()
    annotator = AnnotateMonarch(
        normalizer=DefaultNormalizer(**config.normalizer),
        synonym_finder=DefaultSynonymFinder(**config.synonym_service),
        config=config,
    )

    return annotator
