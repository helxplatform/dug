from typing import Dict

import pluggy

from helx.search.core.parsers import Parser

hookspec = pluggy.HookspecMarker("dug")


@hookspec
def define_parsers(parser_dict: Dict[str, Parser]):
    """Defines what parsers are available to Dug
    """
    ...
