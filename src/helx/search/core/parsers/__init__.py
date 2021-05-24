import logging
from typing import Dict

import pluggy

from ._base import SearchElement, SearchConcept, Indexable, Parser, FileParser
from .dbgap_parser import DbGaPParser
from .topmed_tag_parser import TOPMedTagParser

logger = logging.getLogger('helx')

hookimpl = pluggy.HookimplMarker("helx")


@hookimpl
def define_parsers(parser_dict: Dict[str, Parser]):
    parser_dict["dbgap"] = DbGaPParser()
    parser_dict["topmedtag"] = TOPMedTagParser()


class ParserNotFoundException(Exception):
    ...


def get_parser(hook, parser_name) -> Parser:
    """Get the parser from all parsers registered via the define_parsers hook"""

    available_parsers = {}
    hook.define_parsers(parser_dict=available_parsers)
    parser = available_parsers.get(parser_name.lower())
    if parser is not None:
        return parser

    err_msg = f"Cannot find parser of type '{parser_name}'\n" \
              f"Supported parsers: {', '.join(available_parsers.keys())}"
    logger.error(err_msg)
    raise ParserNotFoundException(err_msg)
