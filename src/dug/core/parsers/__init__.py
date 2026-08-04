import logging
from typing import Dict

import pluggy

from dug_data_model.v2 import (
    DugElement,
    DugVariable,
    DugStudy,
    DugSection,
    DugConcept,
    Indexable,
    Parser,
    FileParser,
)
from .dbgap_parser import *
from .heal_ddm2_parser import HEALDDM2Parser


logger = logging.getLogger('dug')

hookimpl = pluggy.HookimplMarker("dug")


@hookimpl
def define_parsers(parser_dict: Dict[str, Parser]):
    parser_dict["bdc"] = BDCParser()
    parser_dict["heal-ddm2"] = HEALDDM2Parser(study_type="HEAL Studies")
    parser_dict["biolincc"] = BioLINCCBDCParser()
    parser_dict["covid19"] = Covid19BDCParser()
    parser_dict["dir"] = DIRBDCParser()
    parser_dict["lungmap"] = LungMAPBDCParser()
    parser_dict["nsrr"] = NSRRBDCParser()
    parser_dict["parent"] = ParentDBGaPParser()
    parser_dict["pcgc"] = PCGCBDCParser()
    parser_dict["recover"] = RECOVERDBGaPParser()
    parser_dict["topmeddbgap"] = TopmedDBGaPParser()
    parser_dict["curesc"] = CureSC()
    parser_dict["heartfailure"] = HeartFailure()
    parser_dict["imaging"] = Imaging()
    parser_dict["reds"] = Reds()

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
