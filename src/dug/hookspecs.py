from typing import Dict

import pluggy

from dug.core.parsers import Parser
from dug.core.annotators import Annotator

hookspec = pluggy.HookspecMarker("dug")


@hookspec
def define_parsers(parser_dict: Dict[str, Parser]):
    """Defines what parsers are available to Dug
    """
    ...

@hookspec
def define_annotators(annotator_dict: Dict[str, Annotator]):
    """Defines what Annotators are available to Dug
    """
    ...
