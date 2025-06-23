import logging
import os
from typing import List
from xml.etree import ElementTree as ET

from dug import utils as utils
from ._base import DugVariable, DugStudy, FileParser, Indexable, InputFile

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

        print("******* IN HEALDPPARSER *****")
        if study_name is None:
            err_msg = f"Unable to parse study name from data dictionary: {input_file}!"
            logger.error(err_msg)
            raise IOError(err_msg)

        ## Get study information from whatever sources and create a DugStudy element
        study = DugStudy(id=study_id,
                     name=study_name,
                     description="THIS DESCRIPTION WILL COME LATER",
                     program_name_list=[self.get_study_type()],
                     parents=[]
                     )
        ## elem.collection_action = utils.get_heal_platform_link(study_id=study_id)

        elements = []
        for variable in root.iter('variable'):
            logger.info(variable)
            elem = DugVariable(id=f"{variable.attrib['id']}",
                              name=variable.find('name').text,
                              description=variable.find('description').text.lower(),
                              program_name_list=[self.get_study_type()],
                              parents=[study_id],
                              data_type=variable.find('type').text,
                              is_standardized=False) ## This would be changed to study id
            #if elem.data_type == 'encoded value':

            # Add to set of variables
            logger.debug(elem)
            elements.append(elem)

        #elements.append(study)
        print(len(elements))
        # You don't actually create any concepts
        return elements
