import logging
import os
from typing import List
from xml.etree import ElementTree as ET

from dug import utils as utils
from ._base import DugVariable, DugStudy, FileParser, Indexable, InputFile
from .heal_studies_parser import get_study_info_from_mds, HDP_ID_PREFIX

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

        if HDP_ID_PREFIX in study_id:
            mds_study_id = study_id[study_id.find(HDP_ID_PREFIX)+len(HDP_ID_PREFIX) : ]
        study_details = get_study_info_from_mds(mds_study_id)

        if study_details is None:
            # Parse study name from file handle
            study_name = root.get('study_name')
            if study_name is None:
                err_msg = f"Unable to parse study name from data dictionary: {input_file}!"
                logger.error(err_msg)
                raise IOError(err_msg)
                ## Get study information from whatever sources and create a DugStudy element
            study = DugStudy(id=study_id,
                        name=study_name,
                        description="THIS DESCRIPTION WILL COME LATER",
                        program_name_list=[self.get_study_type()],
                        parents=[],
                        action = utils.get_heal_platform_link(study_id=study_id),
                        )
        else:
            ## Get study information from whatever sources and create a DugStudy element
            study = DugStudy(
                            id=study_details['id'],
                            name=study_details['study_name'],
                            description=study_details['description'],
                            program_name_list=[self.get_study_type()],
                            parents=[],
                            action = study_details['action'],
                            abstract=study_details['abstract'],
                            publications = study_details['publication_list'],
                            metadata = {
                                'Project Start Date':study_details['project_start_date'],
                                'Project End Date':study_details['project_end_date'],
                                'Institution': study_details['institution'],
                                'Investigator/s': study_details['pi_list']
                                }
                            )

        elements = []
        for variable in root.iter('variable'):
            # logger.info(variable)
            elem = DugVariable(id=f"{variable.attrib['id']}",
                              name=variable.find('name').text,
                              description=variable.find('description').text.lower(),
                              program_name_list=[self.get_study_type()],
                              parents=[study_id],
                              data_type=variable.find('type').text if variable.find('type') is not None else 'string',
                              is_standardized=False) ## This would be changed to study id
            #if elem.data_type == 'encoded value':

            # Add to set of variables
            logger.debug(elem)
            elements.append(elem)

        study.variable_list = [elem.id for elem in elements]

        elements.append(study)
        # You don't actually create any concepts
        return elements
