import logging
from typing import Dict

import pluggy

from dug.config import Config
from ._base import DugIdentifier, Indexable, Annotator
from .monarch_annotator import AnnotateMonarch, PreprocessorMonarch, AnnotatorMonarch, NormalizerMonarch, SynonymFinderMonarch

logger = logging.getLogger('dug')

hookimpl = pluggy.HookimplMarker("dug")

@hookimpl
def define_annotators(annotator_dict: Dict[str, Annotator]):
    annotator_dict["annotator-monarch"] = build_monarch_annotator()


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

def build_monarch_annotator(config: Config) -> AnnotateMonarch:
    print(**config.preprocessor)
    preprocessor = PreprocessorMonarch(**config.preprocessor)
    annotator = AnnotatorMonarch(**config.annotator)
    normalizer = NormalizerMonarch(**config.normalizer)
    synonym_finder = SynonymFinderMonarch(**config.synonym_service)

    annotator = AnnotateMonarch(
        preprocessor=preprocessor,
        annotator=annotator,
        normalizer=normalizer,
        synonym_finder=synonym_finder
    )

    return annotator
