import logging
from typing import Dict
from .AnnotatorBase import Annotator
from .MonarchAnnotator import MonarchNLPAnnotator
from .ScigraphAnnotator import ScigraphAnnotator

import pluggy


logger = logging.getLogger('dug')

hookimpl = pluggy.HookimplMarker("dug")


@hookimpl
def define_annotators(annotator_dict: Dict[str, callable]):
    annotator_dict["monarch"] = MonarchNLPAnnotator
    annotator_dict["scigraph"] = ScigraphAnnotator


class ParserNotFoundException(Exception):
    ...


def get_annotator_class(hook, annotator_name) -> Annotator:
    """Get the parser from all parsers registered via the define_parsers hook"""

    available_annotators = {}
    hook.define_annotators(annotator_dict=available_annotators)
    annotator = available_annotators.get(annotator_name.lower())
    if annotator is not None:
        return annotator

    err_msg = f"Cannot find annotator of type '{annotator_name}'\n" \
              f"Supported annotators: {', '.join(available_annotators.keys())}"
    logger.error(err_msg)
    raise ParserNotFoundException(err_msg)
