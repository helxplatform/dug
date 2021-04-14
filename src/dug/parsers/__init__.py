import logging
from typing import Dict

import pluggy

from ._base import DugElement, DugConcept, Indexable, Parser, InputFile, FileParser
from .dbgap_parser import DbGaPParser
from .topmed_tag_parser import TOPMedTagParser


logger = logging.getLogger('dug')

hookimpl = pluggy.HookimplMarker("dug")


@hookimpl
def define_parsers(parser_dict: Dict[str, Parser]):
    parser_dict["dbgap"] = DbGaPParser()
    parser_dict["topmedtag"] = TOPMedTagParser()
