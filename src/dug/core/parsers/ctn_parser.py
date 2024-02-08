import logging
import os
from typing import List
from xml.etree import ElementTree as ET

from dug import utils as utils
from dug.core.parsers._base import DugElement, FileParser, Indexable, InputFile

logger = logging.getLogger('dug')


class CTNParser(FileParser):
    # Class for parsers CTN converted Data dictionary into a set of Dug Elements

    def __init__(self):
        super()
        self.study_type = "ctn"

    def get_study_type(self):
        return self.study_type

    def set_study_type(self, study_type):
        self.study_type = study_type

    def __call__(self, input_file: InputFile) -> List[Indexable]:
        logger.debug(input_file)
        tree = ET.parse(input_file)
        root = tree.getroot()
        study_id = root.attrib['study_id']

        # Parse study name from file handle
        study_name = root.get('study_name')

        if study_name is None:
            err_msg = f"Unable to parse study name from data dictionary: {input_file}!"
            logger.error(err_msg)
            raise IOError(err_msg)

        elements = []
        counter = 0
        for variable in root.iter('variable'):

            if not variable.text:
                continue
            description = variable.find('description').text.lower() if variable.find('description') is not None else ""

            elem = DugElement(elem_id=f"{variable.attrib['id']}",
                              name=variable.find('name').text,
                              desc=description,
                              elem_type=self.get_study_type(),
                              collection_id=f"{study_id}",
                              collection_name=study_name,
                              collection_action=utils.get_ctn_link(study_id=study_id))
            if elem.id=="BSNAUSE":
                print(elem.collection_action)
            counter+=1
            # Add to set of variables
            logger.debug(elem)
            elements.append(elem)

        # You don't actually create any concepts
        return elements





