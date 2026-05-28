import logging
from typing import Dict

import pluggy

from ._base import DugElement, DugVariable, DugStudy, DugSection, DugConcept, Indexable, Parser, FileParser
from .dbgap_parser import *
from .nida_parser import NIDAParser
from .scicrunch_parser import SciCrunchParser
from .topmed_tag_parser import TOPMedTagParser
from .topmed_csv_parser import TOPMedCSVParser
from .sprint_parser import SPRINTParser
from .bacpac_parser import BACPACParser
from .heal_ddm2_parser import HEALDDM2Parser
from .ctn_parser import CTNParser
from .radx_parser import RADxParser


logger = logging.getLogger('dug')

hookimpl = pluggy.HookimplMarker("dug")


@hookimpl
def define_parsers(parser_dict: Dict[str, Parser]):
    parser_dict["bdc"] = BDCParser()
    # parser_dict["nida"] = NIDAParser()
    # parser_dict["topmedtag"] = TOPMedTagParser()
    # parser_dict["topmedcsv"] = TOPMedCSVParser()
    # parser_dict["scicrunch"] = SciCrunchParser()
    # parser_dict["anvil"] = AnvilDbGaPParser()
    # parser_dict["crdc"] = CRDCDbGaPParser()
    # parser_dict["kfdrc"] = KFDRCDbGaPParser()
    # parser_dict["sprint"] = SPRINTParser()
    # parser_dict["bacpac"] = BACPACParser()
    parser_dict["heal-ddm2"] = HEALDDM2Parser(study_type="HEAL Studies")
    parser_dict["ctn"] = CTNParser()
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
    parser_dict["radx"] = RADxParser()
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
