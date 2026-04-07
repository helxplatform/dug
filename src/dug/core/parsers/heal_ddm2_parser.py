import logging
import os
from typing import List
import json
from dug import utils as utils
from dug_data_model.v2 import (
    DugVariable, DugStudy, DugSection, FileParser, Indexable, InputFile,
    DugElementParsedList, VARIABLE_TYPE, STUDY_TYPE, CONCEPT_TYPE, SECTION_TYPE,
)

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
        final_elements = [k for k in elements if k.get_id()!='']
        for k in final_elements:
            k.id = k.get_id().replace("HEALCDE:", "").replace("HEALDATAPLATFORM:", "")
            parents = [k.replace("HEALCDE:", "").replace("HEALDATAPLATFORM:", "") for k in k.parents]
            k.parents = parents
        return final_elements
