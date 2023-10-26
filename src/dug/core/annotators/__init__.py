import logging
from typing import Dict

import pluggy

from ._base import DugElement, DugConcept, Indexable, Annotator, FileAnnotator
from .monarch_annotator import AnnotatorMonarch


logger = logging.getLogger('dug')

hookimpl = pluggy.HookimplMarker("dug")

@hookimpl
def define_annotators(annotator_dict: Dict[str, Annotator]):
    annotator_dict["annotator-monarch"] = AnnotatorMonarch()


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