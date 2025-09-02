import logging
import os
from typing import List
import json
from dug import utils as utils
from ._base import DugVariable, DugStudy, DugSection, FileParser, Indexable, InputFile, DugElementParsedList
from ._base import VARIABLE_TYPE, STUDY_TYPE, CONCEPT_TYPE, SECTION_TYPE

logger = logging.getLogger('dug')


class HEALDDM2Parser(FileParser):
    # Class for parsers Heal data platform converted Data dictionary into a set of Dug Elements

    def __init__(self, study_type="HEAL Studies"):
        super()
        self.study_type = study_type

    def get_study_type(self):
        return self.study_type
    
    def set_study_type(self, study_type):
        self.study_type = study_type

    def __call__(self, input_file: InputFile) -> List[Indexable]:
        logger.debug(input_file)
        elements = []
        with open(input_file, "r") as f:
            json_obj = json.load(f)
            elements = DugElementParsedList.validate_python(json_obj)

        print("************")
        print(elements)
        print("******************")
        return elements
