import logging
import os
from typing import List
from xml.etree import ElementTree as ET

from dug import utils as utils
from ._base import DugElement, FileParser, Indexable, InputFile

logger = logging.getLogger('dug')


class HEALDPParser(FileParser):
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
        for variable in root.iter('variable'):
            elem = DugElement(elem_id=f"{variable.attrib['id']}",
                              name=variable.find('name').text,
                              desc=variable.find('description').text.lower(),
                              elem_type=self.get_study_type(),
                              collection_id=f"{study_id}",
                              collection_name=study_name)

            # Create NIDA links as study/variable actions
            elem.collection_action = utils.get_heal_platform_link(study_id=study_id)
            # Add to set of variables
            logger.debug(elem)
            elements.append(elem)

        # You don't actually create any concepts
        return elements
